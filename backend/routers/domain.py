from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.dnshe_api import DnsheClient
from backend.models import AppConfig
from backend.scheduler import log_op
import datetime

router = APIRouter()

class DomainCreateReq(BaseModel):
    subdomain: str
    root_domain: str

class DomainRenewReq(BaseModel):
    subdomain_id: int

class DomainDeleteReq(BaseModel):
    subdomain_id: int

def get_client(db: Session):
    key_row = db.query(AppConfig).filter(AppConfig.key == "dnshe_api_key").first()
    secret_row = db.query(AppConfig).filter(AppConfig.key == "dnshe_api_secret").first()
    if not key_row or not secret_row or not key_row.value or not secret_row.value:
        return None
    return DnsheClient(key_row.value, secret_row.value)

@router.get("/list")
def list_domain(db: Session = Depends(get_db)):
    cli = get_client(db)
    if not cli:
        return {"success": True, "data": []}
    res = cli.list_subdomains()
    raw_list = res.get("subdomains", [])
    out = []
    now = datetime.datetime.utcnow()
    for item in raw_list:
        sub_id = item.get("id")
        full_domain = item.get("full_domain")
        expire_str = item.get("expires_at", "")
        left_days = -1
        if expire_str:
            try:
                exp = datetime.datetime.strptime(expire_str, "%Y-%m-%d %H:%M:%S")
                left_days = (exp - now).days
            except:
                pass
        out.append({
            "id": sub_id,
            "domain": full_domain,
            "expire_at": expire_str,
            "created_at": item.get("created_at", ""),
            "left_days": left_days,
            "status": item.get("status", "")
        })
    return {"success": True, "data": out}

@router.post("/create")
def create_domain(req: DomainCreateReq, db: Session = Depends(get_db)):
    cli = get_client(db)
    if not cli:
        return {"success": False, "msg": "未配置API Key/Secret"}
    r = cli.register_subdomain(req.subdomain, req.root_domain)
    if r.get("success"):
        log_op("申请域名", f"新域名 {req.subdomain}.{req.root_domain}")
    else:
        log_op("申请域名", f"失败: {r.get('message')}", False)
    return r

@router.post("/renew")
def renew_domain(req: DomainRenewReq, db: Session = Depends(get_db)):
    cli = get_client(db)
    if not cli:
        return {"success": False, "msg": "未配置API Key/Secret"}
    r = cli.renew_subdomain(req.subdomain_id)
    if r.get("success"):
        log_op("手动续期", f"域名ID {req.subdomain_id}")
    else:
        log_op("手动续期", f"失败: {r.get('message')}", False)
    return r

@router.post("/delete")
def delete_domain(req: DomainDeleteReq, db: Session = Depends(get_db)):
    cli = get_client(db)
    if not cli:
        return {"success": False, "msg": "未配置API Key/Secret"}
    try:
        r = cli.delete_subdomain(req.subdomain_id)
        return r
    except Exception as e:
        return {"success": False, "error": str(e)}

@router.get("/available_roots")
def available_roots(db: Session = Depends(get_db)):
    roots = []
    cli = get_client(db)
    if cli:
        try:
            res = cli.list_subdomains()
            for item in res.get("subdomains", []):
                rd = item.get("rootdomain")
                if rd and rd not in roots:
                    roots.append(rd)
        except:
            pass
    default_roots = ["cc.cd", "us.ci", "de5.net", "ccwu.cc", "cn.mt", "xyz.ws", "topweeb.xyz"]
    for r in default_roots:
        if r not in roots:
            roots.append(r)
    return {"success": True, "data": roots}

@router.get("/quota")
def get_quota(db: Session = Depends(get_db)):
    cli = get_client(db)
    if not cli:
        return {"success": False, "data": {}}
    res = cli.get_quota()
    return res

@router.post("/test_renew")
def test_auto_renew():
    from backend.scheduler import auto_renew_job
    auto_renew_job()
    return {"success": True, "message": "已手动触发一次自动续期扫描"}
