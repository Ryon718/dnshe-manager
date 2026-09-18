from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.dnshe_api import DnsheClient
from backend.models import AppConfig
from backend.scheduler import log_op

router = APIRouter()

class RecAddReq(BaseModel):
    subdomain_id: int
    type: str
    name: str
    content: str
    ttl: int = 600

class RecEditReq(BaseModel):
    id: int
    type: str
    name: str
    content: str
    ttl: int = 600

class RecDelReq(BaseModel):
    id: int

def get_client(db: Session):
    key_row = db.query(AppConfig).filter(AppConfig.key == "dnshe_api_key").first()
    secret_row = db.query(AppConfig).filter(AppConfig.key == "dnshe_api_secret").first()
    if not key_row or not secret_row or not key_row.value or not secret_row.value:
        return None
    return DnsheClient(key_row.value, secret_row.value)

@router.get("/list")
def list_record(subdomain_id: int, db: Session = Depends(get_db)):
    cli = get_client(db)
    if not cli:
        return {"success": False, "msg": "未配置API Key/Secret"}
    res = cli.list_dns_records(subdomain_id)
    return res

@router.post("/add")
def add_record(req: RecAddReq, db: Session = Depends(get_db)):
    cli = get_client(db)
    if not cli:
        return {"success": False, "msg": "未配置API Key/Secret"}
    res = cli.create_dns_record(req.subdomain_id, req.type, req.name, req.content, req.ttl)
    if res.get("success"):
        log_op("添加DNS记录", f"{req.name} {req.type} -> {req.content}")
    else:
        log_op("添加DNS记录", f"失败: {res.get('message')}", False)
    return res

@router.post("/edit")
def edit_record(req: RecEditReq, db: Session = Depends(get_db)):
    cli = get_client(db)
    if not cli:
        return {"success": False, "msg": "未配置API Key/Secret"}
    res = cli.update_dns_record(req.id, req.type, req.name, req.content, req.ttl)
    if res.get("success"):
        log_op("修改DNS记录", f"{req.name} {req.type} -> {req.content}")
    else:
        log_op("修改DNS记录", f"失败: {res.get('message')}", False)
    return res

@router.post("/del")
def del_record(req: RecDelReq, db: Session = Depends(get_db)):
    cli = get_client(db)
    if not cli:
        return {"success": False, "msg": "未配置API Key/Secret"}
    res = cli.delete_dns_record(req.id)
    if res.get("success"):
        log_op("删除DNS记录", f"记录ID {req.id}")
    else:
        log_op("删除DNS记录", f"失败: {res.get('message')}", False)
    return res
