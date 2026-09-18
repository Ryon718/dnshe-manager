from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from backend.routers import domain, record, setting, renew, log
from backend.scheduler import register_jobs
from backend.database import init_db
from apscheduler.schedulers.background import BackgroundScheduler

app = FastAPI(title="DNSHE Manager")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(domain.router, prefix="/api/domain", tags=["domain"])
app.include_router(record.router, prefix="/api/record", tags=["record"])
app.include_router(setting.router, prefix="/api/setting", tags=["setting"])
app.include_router(renew.router, prefix="/api/renew", tags=["renew"])
app.include_router(log.router, prefix="/api/log", tags=["log"])

@app.on_event("startup")
def startup():
    init_db()
    scheduler = BackgroundScheduler()
    scheduler.start()
    register_jobs(scheduler)

app.mount("/", StaticFiles(directory="/app/frontend", html=True), name="frontend")
