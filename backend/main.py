from fastapi import FastAPI, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from backend.routers import domain, record, setting, renew, log, auth, account
from backend.scheduler import register_jobs
from backend.database import init_db, SessionLocal
from backend.models import AdminUser, DnsheAccount, AppConfig
from backend.routers.auth import hash_password
from apscheduler.schedulers.background import BackgroundScheduler

app = FastAPI(title="DNSHE Manager")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(account.router, prefix="/api/account", tags=["account"], dependencies=[Depends(auth.get_current_user)])
# 除了auth之外的所有路由都需要登录校验
app.include_router(domain.router, prefix="/api/domain", tags=["domain"], dependencies=[Depends(auth.get_current_user)])
app.include_router(record.router, prefix="/api/record", tags=["record"], dependencies=[Depends(auth.get_current_user)])
app.include_router(setting.router, prefix="/api/setting", tags=["setting"], dependencies=[Depends(auth.get_current_user)])
app.include_router(renew.router, prefix="/api/renew", tags=["renew"], dependencies=[Depends(auth.get_current_user)])
app.include_router(log.router, prefix="/api/log", tags=["log"], dependencies=[Depends(auth.get_current_user)])

@app.on_event("startup")
def startup():
    init_db()
    # 初始化默认admin账号
    db = SessionLocal()
    if not db.query(AdminUser).first():
        admin = AdminUser(username="admin", password_hash=hash_password("admin123"))
        db.add(admin)
        db.commit()
    # 自动迁移旧版单账号配置
    if db.query(DnsheAccount).count() == 0:
        old_key = db.query(AppConfig).filter(AppConfig.key == "dnshe_api_key").first()
        old_secret = db.query(AppConfig).filter(AppConfig.key == "dnshe_api_secret").first()
        if old_key and old_secret and old_key.value and old_secret.value:
            acc = DnsheAccount(name="默认账号", api_key=old_key.value, api_secret=old_secret.value, is_active=1)
            db.add(acc)
            db.commit()
    db.close()
    scheduler = BackgroundScheduler()
    scheduler.start()
    register_jobs(scheduler)

app.mount("/", StaticFiles(directory="/app/frontend", html=True), name="frontend")
