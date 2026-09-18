from apscheduler.schedulers.background import BackgroundScheduler
from backend.dnshe_api import DnsheClient
from backend.database import SessionLocal
from backend.models import AppConfig, OperationLog, DomainRenew
import requests
import datetime

_scheduler = None

def get_credentials():
    db = SessionLocal()
    key_row = db.query(AppConfig).filter(AppConfig.key == "dnshe_api_key").first()
    secret_row = db.query(AppConfig).filter(AppConfig.key == "dnshe_api_secret").first()
    db.close()
    if key_row and secret_row and key_row.value and secret_row.value:
        return key_row.value, secret_row.value
    return None, None

def log_op(action, detail, success=True):
    db = SessionLocal()
    log = OperationLog(action=action, detail=detail, success=success)
    db.add(log)
    db.commit()
    db.close()

def send_notify(content):
    """根据配置的通知渠道推送消息"""
    db = SessionLocal()
    def get_val(key, default=""):
        row = db.query(AppConfig).filter(AppConfig.key == key).first()
        return row.value if row else default
    ntype = get_val("notify_type", "dingtalk")
    webhook = get_val("notify_webhook")
    bark_key = get_val("bark_key")
    serverchan_key = get_val("serverchan_key")
    tg_token = get_val("telegram_token")
    tg_chat_id = get_val("telegram_chat_id")
    tg_proxy = get_val("telegram_proxy")
    db.close()

    proxies = None
    if tg_proxy:
        proxies = {"http": tg_proxy, "https": tg_proxy}

    try:
        if ntype in ["dingtalk", "wechat", "feishu"] and webhook:
            requests.post(webhook, json={"msgtype":"text","text":{"content": content}}, timeout=10)
        elif ntype == "bark" and bark_key:
            requests.post(f"https://api.day.app/{bark_key}/DNSHE通知/{content}", timeout=10)
        elif ntype == "serverchan" and serverchan_key:
            requests.post(f"https://sctapi.ftqq.com/{serverchan_key}.send",
                          data={"title": "DNSHE通知", "desp": content}, timeout=10)
        elif ntype == "telegram" and tg_token and tg_chat_id:
            requests.post(f"https://api.telegram.org/bot{tg_token}/sendMessage",
                          json={"chat_id": tg_chat_id, "text": content},
                          proxies=proxies, timeout=15)
    except Exception as e:
        print(f"通知发送失败: {e}")

def auto_renew_job():
    api_key, api_secret = get_credentials()
    if not api_key:
        log_op("自动续期", "未配置API Key/Secret", False)
        return
    cli = DnsheClient(api_key, api_secret)
    res = cli.list_subdomains()
    if not res.get("success"):
        log_op("自动续期", f"获取域名列表失败:{res}", False)
        return
    domains = res.get("subdomains", [])
    db = SessionLocal()
    cnt = 0
    for d in domains:
        try:
            sub_id = d.get("id")
            renew_cfg = db.query(DomainRenew).filter(DomainRenew.subdomain_id == sub_id).first()
            if not renew_cfg or not renew_cfg.auto_renew:
                continue
            expire_str = d.get("expires_at")
            if not expire_str:
                continue
            expire = datetime.datetime.strptime(expire_str, "%Y-%m-%d %H:%M:%S")
            now = datetime.datetime.now()
            delta = expire - now
            if delta.days <= 180:
                rr = cli.renew_subdomain(sub_id)
                if rr.get("success"):
                    renew_cfg.last_renewed_at = datetime.now()
                    db.commit()
                    cnt += 1
                    log_op("自动续期", f"域名 {d.get('full_domain')} 续期成功", True)
                    send_notify(f"✅ DNSHE域名续期成功\n域名: {d.get('full_domain')}\n新到期时间: {rr.get('new_expires_at', expire_str)}")
                else:
                    log_op("自动续期", f"域名 {d.get('full_domain')} 续期失败: {rr.get('message')}", False)
                    send_notify(f"❌ DNSHE域名续期失败\n域名: {d.get('full_domain')}\n错误: {rr.get('message')}")
        except Exception as e:
            log_op("自动续期", f"域名{d.get('full_domain','?')}异常:{str(e)}", False)
            send_notify(f"❌ DNSHE续期异常\n域名: {d.get('full_domain','?')}\n错误: {str(e)}")
    db.close()
    log_op("自动续期", f"扫描{len(domains)}个域名，成功续期{cnt}个")

def register_jobs(scheduler: BackgroundScheduler):
    global _scheduler
    _scheduler = scheduler
    refresh_scheduler_jobs()

def refresh_scheduler_jobs():
    global _scheduler
    if not _scheduler:
        return
    if "auto_renew" not in [j.id for j in _scheduler.get_jobs()]:
        _scheduler.add_job(auto_renew_job, "cron", hour=3, id="auto_renew", replace_existing=True)
