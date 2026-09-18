from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models import AppConfig, DomainRenew
from backend.dnshe_api import DnsheClient
import datetime

router = APIRouter()

def get_client(db: Session):
    key_row = db.query(AppConfig).filter(AppConfig.key == "dnshe_api_key").first()
    secret_row = db.query(AppConfig).filter(AppConfig.key == "dnshe_api_secret").first()
    if not key_row or not secret_row or not key_row.value or not secret_row.value:
        return None
    return DnsheClient(key_row.value, secret_row.value)

@router.get("/list")
def renew_list(db: Session = Depends(get_db)):
    cli = get_client(db)
    if not cli:
        return {"success": False, "data": []}
    res = cli.list_subdomains()
    domains = res.get("subdomains", [])
    out = []
    for d in domains:
        sub_id = d.get("id")
        expire_str = d.get("expires_at", "")
        left_days = None
        can_renew_in = None
        in_renew_window = False
        if expire_str:
            try:
                expire = datetime.datetime.strptime(expire_str, "%Y-%m-%d %H:%M:%S")
                left_days = (expire - datetime.datetime.now()).days
                can_renew_in = left_days - 180
                if can_renew_in <= 0:
                    in_renew_window = True
            except:
                pass
        # 查续期开关
        cfg = db.query(DomainRenew).filter(DomainRenew.subdomain_id == sub_id).first()
        auto_renew = cfg.auto_renew if cfg else False
        last_renewed = cfg.last_renewed_at.strftime("%Y-%m-%d %H:%M:%S") if cfg and cfg.last_renewed_at else None
        out.append({
            "subdomain_id": sub_id,
            "domain": d.get("full_domain"),
            "expires_at": expire_str,
            "left_days": left_days,
            "can_renew_in": can_renew_in,
            "in_renew_window": in_renew_window,
            "auto_renew": auto_renew,
            "last_renewed_at": last_renewed
        })
    return {"success": True, "data": out}

class ToggleRenewReq(BaseModel):
    subdomain_id: int
    auto_renew: bool

@router.post("/toggle")
def toggle_renew(req: ToggleRenewReq, db: Session = Depends(get_db)):
    cfg = db.query(DomainRenew).filter(DomainRenew.subdomain_id == req.subdomain_id).first()
    if not cfg:
        cfg = DomainRenew(subdomain_id=req.subdomain_id, auto_renew=req.auto_renew)
        db.add(cfg)
    else:
        cfg.auto_renew = req.auto_renew
    db.commit()
    return {"success": True, "message": "设置已保存"}

class TestRenewReq(BaseModel):
    subdomain_id: int

@router.post("/test_now")
def test_renew_now(req: TestRenewReq, db: Session = Depends(get_db)):
    """立即对指定域名调用一次续期接口，跳过时间限制，用于验证功能"""
    cli = get_client(db)
    if not cli:
        return {"success": False, "message": "未配置API"}
    r = cli.renew_subdomain(req.subdomain_id)
    if r.get("success"):
        cfg = db.query(DomainRenew).filter(DomainRenew.subdomain_id == req.subdomain_id).first()
        if cfg:
            cfg.last_renewed_at = datetime.datetime.now()
            db.commit()
    return r
