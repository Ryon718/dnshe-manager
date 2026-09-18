from sqlalchemy import Column, Integer, String, Boolean, DateTime
from datetime import datetime
from backend.database import Base

class AppConfig(Base):
    __tablename__ = "app_config"
    id = Column(Integer, primary_key=True, index=True)
    key = Column(String, unique=True, index=True)
    value = Column(String)

class DomainRenew(Base):
    __tablename__ = "domain_renew"
    id = Column(Integer, primary_key=True, index=True)
    subdomain_id = Column(Integer, unique=True, index=True)
    auto_renew = Column(Boolean, default=False)
    last_renewed_at = Column(DateTime, nullable=True)

class OperationLog(Base):
    __tablename__ = "operation_log"
    id = Column(Integer, primary_key=True, index=True)
    action = Column(String)
    detail = Column(String)
    success = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)
