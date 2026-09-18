from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models import OperationLog
from backend.scheduler import log_op

router = APIRouter()

@router.get("/list")
def log_list(db: Session = Depends(get_db), limit: int = 100):
    logs = db.query(OperationLog).order_by(OperationLog.created_at.desc()).limit(limit).all()
    return {
        "success": True,
        "data": [
            {
                "time": log.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                "action": log.action,
                "detail": log.detail,
                "success": log.success
            } for log in logs
        ]
    }
