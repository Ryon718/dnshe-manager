from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models import AppConfig
from backend.scheduler import refresh_scheduler_jobs, send_notify

router = APIRouter()

class SettingSaveReq(BaseModel):
    api_key: str
    api_secret: str
    auto_renew: bool
    auto_ddns: bool

class NotifySaveReq(BaseModel):
    type: str = "dingtalk"
    webhook: str = ""
    bark_key: str = ""
    serverchan_key: str = ""
    telegram_token: str = ""
    telegram_chat_id: str = ""
    telegram_proxy: str = ""
    enabled: bool = True
    expire_days: int = 30

@router.get("/get")
def get_setting(db: Session = Depends(get_db)):
    def get_val(key, default=""):
        row = db.query(AppConfig).filter(AppConfig.key == key).first()
        return row.value if row else default
    return {
        "success": True,
        "data": {
            "api_key": get_val("dnshe_api_key"),
            "api_secret": get_val("dnshe_api_secret"),
            "auto_renew": get_val("auto_renew", "false") == "true",
            "auto_ddns": get_val("auto_ddns", "false") == "true",
            "notify_webhook": get_val("notify_webhook"),
            "notify_type": get_val("notify_type", "dingtalk"),
            "bark_key": get_val("bark_key"),
            "serverchan_key": get_val("serverchan_key"),
            "telegram_token": get_val("telegram_token"),
            "telegram_chat_id": get_val("telegram_chat_id"),
            "telegram_proxy": get_val("telegram_proxy"),
            "notify_enabled": get_val("notify_enabled", "true") == "true",
            "notify_expire_days": int(get_val("notify_expire_days", "30"))
        }
    }

@router.post("/save")
def save_setting(req: SettingSaveReq, db: Session = Depends(get_db)):
    def upsert(key, val):
        row = db.query(AppConfig).filter(AppConfig.key == key).first()
        if row:
            row.value = val
        else:
            db.add(AppConfig(key=key, value=val))
    upsert("dnshe_api_key", req.api_key)
    upsert("dnshe_api_secret", req.api_secret)
    upsert("auto_renew", str(req.auto_renew).lower())
    upsert("auto_ddns", str(req.auto_ddns).lower())
    db.commit()
    refresh_scheduler_jobs()
    return {"success": True, "message": "设置保存成功"}

@router.post("/save_notify")
def save_notify(req: NotifySaveReq, db: Session = Depends(get_db)):
    def upsert(key, val):
        row = db.query(AppConfig).filter(AppConfig.key == key).first()
        if row:
            row.value = val
        else:
            db.add(AppConfig(key=key, value=val))
    upsert("notify_type", req.type)
    upsert("notify_webhook", req.webhook)
    upsert("bark_key", req.bark_key)
    upsert("serverchan_key", req.serverchan_key)
    upsert("telegram_token", req.telegram_token)
    upsert("telegram_chat_id", req.telegram_chat_id)
    upsert("telegram_proxy", req.telegram_proxy)
    upsert("notify_enabled", str(req.enabled).lower())
    upsert("notify_expire_days", str(req.expire_days))
    db.commit()
    return {"success": True, "message": "通知设置保存成功"}

@router.post("/clear")
def clear_setting(db: Session = Depends(get_db)):
    db.query(AppConfig).filter(AppConfig.key.in_(["dnshe_api_key", "dnshe_api_secret"])).delete(synchronize_session=False)
    db.commit()
    refresh_scheduler_jobs()
    return {"success": True, "message": "配置已清空"}

@router.post("/test_notify")
def test_notify():
    send_notify("🔔 DNSHE Manager 测试通知\n这是一条测试消息，说明通知配置成功！")
    return {"success": True, "message": "测试通知已发送，请检查你的手机"}
