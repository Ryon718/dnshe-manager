from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.dnshe_api import DnsheClient
from backend.models import DnsheAccount
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
    account = db.query(DnsheAccount).filter(DnsheAccount.is_active == 1).first()
    if not account:
        return None
    return DnsheClient(account.api_key, account.api_secret)

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
