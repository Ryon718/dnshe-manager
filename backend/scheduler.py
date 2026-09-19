from apscheduler.schedulers.background import BackgroundScheduler
from backend.dnshe_api import DnsheClient
from backend.database import SessionLocal
from backend.models import AppConfig, OperationLog, DomainRenew, DnsheAccount
import requests
import datetime

_scheduler = None

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
    # 先判断总开关
    if get_val("notify_enabled", "true") != "true":
        db.close()
        return
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
    db = SessionLocal()
    accounts = db.query(DnsheAccount).all()
    if not accounts:
        log_op("自动续期", "未配置任何DNSHE账号", False)
        db.close()
        return
    total_cnt = 0
    for acc in accounts:
        cli = DnsheClient(acc.api_key, acc.api_secret)
        res = cli.list_subdomains()
        if not res.get("success"):
            log_op("自动续期", f"账号{acc.name}获取域名列表失败:{res}", False)
            continue
        domains = res.get("subdomains", [])
        cnt = 0
        for d in domains:
            try:
                sub_id = d.get("id")
                renew_cfg = db.query(DomainRenew).filter(
                    DomainRenew.subdomain_id == sub_id,
                    DomainRenew.account_id == acc.id
                ).first()
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
                        renew_cfg.last_renewed_at = datetime.datetime.now()
                        db.commit()
                        cnt += 1
                        log_op("自动续期", f"账号{acc.name} 域名 {d.get('full_domain')} 续期成功", True)
                        send_notify(f"✅ DNSHE域名续期成功\n账号: {acc.name}\n域名: {d.get('full_domain')}\n新到期时间: {rr.get('new_expires_at', expire_str)}")
                    else:
                        log_op("自动续期", f"账号{acc.name} 域名 {d.get('full_domain')} 续期失败: {rr.get('message')}", False)
                        send_notify(f"❌ DNSHE域名续期失败\n账号: {acc.name}\n域名: {d.get('full_domain')}\n错误: {rr.get('message')}")
            except Exception as e:
                log_op("自动续期", f"账号{acc.name} 域名{d.get('full_domain','?')}异常:{str(e)}", False)
                send_notify(f"❌ DNSHE续期异常\n账号: {acc.name}\n域名: {d.get('full_domain','?')}\n错误: {str(e)}")
        total_cnt += cnt
        log_op("自动续期", f"账号{acc.name} 扫描{len(domains)}个域名，成功续期{cnt}个")
    db.close()
    log_op("自动续期", f"全部账号扫描完成，总共成功续期{total_cnt}个")

def expire_remind_job():
    """到期提醒：扫描所有账号下剩余天数小于阈值的域名，推送提醒"""
    db = SessionLocal()
    def get_val(key, default=""):
        row = db.query(AppConfig).filter(AppConfig.key == key).first()
        return row.value if row else default
    enabled = get_val("notify_enabled", "true") == "true"
    if not enabled:
        db.close()
        return
    days_threshold = int(get_val("notify_expire_days", "30"))
    accounts = db.query(DnsheAccount).all()
    messages = []
    for acc in accounts:
        cli = DnsheClient(acc.api_key, acc.api_secret)
        res = cli.list_subdomains()
        if not res.get("success"):
            continue
        for d in res.get("subdomains", []):
            expire_str = d.get("expires_at")
            if not expire_str:
                continue
            try:
                expire = datetime.datetime.strptime(expire_str, "%Y-%m-%d %H:%M:%S")
                left = (expire - datetime.datetime.now()).days
                if 0 < left <= days_threshold:
                    messages.append(f"账号:{acc.name} 域名:{d.get('full_domain')} 剩余{left}天到期")
            except:
                pass
    db.close()
    if messages:
        content = "⚠️ 域名即将到期提醒\n" + "\n".join(messages)
        send_notify(content)
        log_op("到期提醒", f"推送{len(messages)}个即将到期域名", True)

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
    if "expire_remind" not in [j.id for j in _scheduler.get_jobs()]:
        _scheduler.add_job(expire_remind_job, "cron", hour=3, minute=30, id="expire_remind", replace_existing=True)
