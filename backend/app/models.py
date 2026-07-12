from sqlalchemy import Column, Integer, String, Float, DateTime
from .database import Base

class TenantConfig(Base):
    __tablename__ = "tenant_configs"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String, unique=True, index=True)
    contracted_demand_kva = Column(Float, default=1501.0)

class TelemetryData(Base):
    __tablename__ = "telemetry_records"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String, index=True)
    timestamp = Column(DateTime, index=True)
    watts_total = Column(Float)
    va_total = Column(Float)
    var_total = Column(Float)
    true_pf_avg = Column(Float)
    frequency = Column(Float)
    v_r_thd_pct = Column(Float)
    i_r_thd_pct = Column(Float)
    v_r = Column(Float)
    v_y = Column(Float)
    v_b = Column(Float)
    i_r = Column(Float)
    i_y = Column(Float)
    i_b = Column(Float)
