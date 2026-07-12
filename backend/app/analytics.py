from sqlalchemy import func
from app.models import TelemetryData

def get_tenant_summary(db, tenant_id: str) -> dict:
    result = db.query(
        func.max(TelemetryData.va_total),
        func.avg(TelemetryData.true_pf_avg),
        func.max(TelemetryData.i_r_thd_pct)
    ).filter(TelemetryData.tenant_id == tenant_id).first()

    max_va_total_val, avg_pf_val, max_thd_i_val = result or (None, None, None)

    max_va_total = max_va_total_val if max_va_total_val is not None else 0.0
    avg_pf = avg_pf_val if avg_pf_val is not None else 1.0
    max_thd_i = max_thd_i_val if max_thd_i_val is not None else 0.0

    max_demand_kva = max_va_total / 1000.0
    demand_violation = max_demand_kva > 1501.0

    return {
        "max_demand_kva": round(max_demand_kva, 2),
        "avg_power_factor": round(avg_pf, 4),
        "max_current_thd_pct": round(max_thd_i, 2),
        "demand_violation": demand_violation
    }
