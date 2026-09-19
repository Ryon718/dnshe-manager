from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models import DnsheAccount
from backend.dnshe_api import DnsheClient

router = APIRouter()

class AccountReq(BaseModel):
    name: str
    api_key: str
    api_secret: str

@router.get("/list")
def list_accounts(db: Session = Depends(get_db)):
    accounts = db.query(DnsheAccount).all()
    return {
        "success": True,
        "accounts": [
            {"id": a.id, "name": a.name, "is_active": a.is_active}
            for a in accounts
        ]
    }

@router.post("/add")
def add_account(req: AccountReq, db: Session = Depends(get_db)):
    # 验证API是否有效
    try:
        api = DnsheClient(req.api_key, req.api_secret)
        api.list_subdomains()
    except Exception as e:
        return {"success": False, "message": f"API验证失败: {str(e)}"}
    account = DnsheAccount(name=req.name, api_key=req.api_key, api_secret=req.api_secret)
    # 第一个账号自动设为当前激活
    if db.query(DnsheAccount).count() == 0:
        account.is_active = 1
    db.add(account)
    db.commit()
    return {"success": True, "message": "账号添加成功"}

@router.post("/switch/{account_id}")
def switch_account(account_id: int, db: Session = Depends(get_db)):
    db.query(DnsheAccount).update({"is_active": 0})
    account = db.get(DnsheAccount, account_id)
    account.is_active = 1
    db.commit()
    return {"success": True, "message": "切换成功"}

@router.delete("/delete/{account_id}")
def delete_account(account_id: int, db: Session = Depends(get_db)):
    account = db.get(DnsheAccount, account_id)
    if not account:
        return {"success": False, "message": "账号不存在"}
    was_active = account.is_active
    db.delete(account)
    # 如果删的是当前激活账号，找剩下的第一个账号自动激活
    if was_active:
        rest = db.query(DnsheAccount).first()
        if rest:
            rest.is_active = 1
    db.commit()
    return {"success": True, "message": "账号已删除"}

# 工具函数：获取当前激活账号的API实例
def get_current_api(db: Session):
    account = db.query(DnsheAccount).filter(DnsheAccount.is_active == 1).first()
    if not account:
        return None, None
    return DnsheClient(account.api_key, account.api_secret), account
