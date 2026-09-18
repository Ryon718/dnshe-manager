from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models import AdminUser
import bcrypt
import secrets
import time
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

router = APIRouter()
security = HTTPBearer()

# 简单内存存token，重启就重新登录
valid_tokens = {}  # token -> 过期时间戳
login_fail_counts = {}  # IP -> 失败次数
MAX_FAIL = 5
BLOCK_SECONDS = 600  # 失败5次封10分钟
TOKEN_EXPIRE = 7 * 86400  # token 7天过期

def hash_password(password: str) -> str:
    # 10轮bcrypt，公网部署安全性足够，VPS上响应<100ms
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=10)).decode()

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())

async def get_current_user(creds: HTTPAuthorizationCredentials = Depends(security)):
    token = creds.credentials
    now = time.time()
    if token not in valid_tokens:
        raise HTTPException(status_code=401, detail="未登录或登录已过期")
    if valid_tokens[token] < now:
        del valid_tokens[token]
        raise HTTPException(status_code=401, detail="登录已过期，请重新登录")
    return token

class LoginReq(BaseModel):
    username: str
    password: str

class ChangePwdReq(BaseModel):
    old_password: str
    new_password: str

class ChangeUsernameReq(BaseModel):
    new_username: str
    password: str

@router.post("/login")
def login(req: LoginReq, request: Request, db: Session = Depends(get_db)):
    client_ip = request.client.host
    now = time.time()
    # 检查是否被封
    if client_ip in login_fail_counts and login_fail_counts[client_ip]["until"] > now:
        return {"success": False, "message": "尝试次数过多，请10分钟后再试"}
    user = db.query(AdminUser).filter(AdminUser.username == req.username).first()
    if not user or not verify_password(req.password, user.password_hash):
        # 记录失败次数
        if client_ip not in login_fail_counts:
            login_fail_counts[client_ip] = {"count": 0, "until": 0}
        login_fail_counts[client_ip]["count"] += 1
        if login_fail_counts[client_ip]["count"] >= MAX_FAIL:
            login_fail_counts[client_ip]["until"] = now + BLOCK_SECONDS
            login_fail_counts[client_ip]["count"] = 0
        return {"success": False, "message": "用户名或密码错误"}
    # 登录成功，清失败次数
    if client_ip in login_fail_counts:
        del login_fail_counts[client_ip]
    token = secrets.token_hex(32)
    valid_tokens[token] = now + TOKEN_EXPIRE
    return {"success": True, "token": token}

@router.post("/change_username")
def change_username(req: ChangeUsernameReq, db: Session = Depends(get_db), token: str = Depends(get_current_user)):
    user = db.query(AdminUser).first()
    if not user or not verify_password(req.password, user.password_hash):
        return {"success": False, "message": "密码错误"}
    # 检查新用户名是否已存在
    exist = db.query(AdminUser).filter(AdminUser.username == req.new_username).first()
    if exist and exist.id != user.id:
        return {"success": False, "message": "该用户名已被占用"}
    user.username = req.new_username
    db.commit()
    return {"success": True, "message": "用户名修改成功"}

@router.post("/change_pwd")
def change_pwd(req: ChangePwdReq, db: Session = Depends(get_db), token: str = Depends(get_current_user)):
    user = db.query(AdminUser).first()
    if not user or not verify_password(req.old_password, user.password_hash):
        return {"success": False, "message": "原密码错误"}
    user.password_hash = hash_password(req.new_password)
    db.commit()
    valid_tokens.clear()
    return {"success": True, "message": "密码修改成功，请重新登录"}

@router.get("/check")
def check_login(token: str = Depends(get_current_user)):
    return {"success": True}

@router.post("/logout")
def logout(token: str = Depends(get_current_user)):
    if token in valid_tokens:
        del valid_tokens[token]
    return {"success": True}
