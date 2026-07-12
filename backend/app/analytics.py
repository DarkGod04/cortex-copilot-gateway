import pandas as pd
from app.models import TelemetryData

def get_tenant_summary(db, tenant_id: str) -> dict:
    df = pd.read_sql(db.query(TelemetryData).filter(TelemetryData.tenant_id == tenant_id).statement, db.bind)
    if df.empty:
        return {"error": f"No data found for tenant {tenant_id}"}
        
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df['kva'] = df['va_total'] / 1000.0
    df['kvah'] = df['kva'] / 4.0

    hours = df['timestamp'].dt.hour
    off_peak_mask = (hours >= 22) | (hours < 6)
    normal_mask = (hours >= 10) & (hours < 18)
    peak_mask = ~(off_peak_mask | normal_mask)

    off_peak = df.loc[off_peak_mask, 'kvah'].sum()
    normal = df.loc[normal_mask, 'kvah'].sum()
    peak = df.loc[peak_mask, 'kvah'].sum()

    energy_charge = (off_peak * 6.65) + (normal * 7.15) + (peak * 8.65)

    max_demand = df['kva'].max()
    billable_demand = max(max_demand, 1201.0)
    
    if max_demand > 1501.0:
        normal_demand_charge = 1501.0 * 500.0
        penal_demand_charge = (max_demand - 1501.0) * 1000.0
    else:
        normal_demand_charge = billable_demand * 500.0
        penal_demand_charge = 0.0
        
    total_demand_charge = normal_demand_charge + penal_demand_charge

    total_kvah = df['kvah'].sum()
    electricity_duty = total_kvah * 0.06
    customer_charges = 3500.0
    total_bill = energy_charge + total_demand_charge + electricity_duty + customer_charges

    avg_pf = df['true_pf_avg'].mean()
    pf_drops = len(df[df['true_pf_avg'] < 0.9])
    max_thd = df['i_r_thd_pct'].max()
    thd_violations = len(df[df['i_r_thd_pct'] > 5.0])

    return {
        "tenant_id": tenant_id,
        "estimated_bill_inr": round(float(total_bill), 2),
        "energy_charge_inr": round(float(energy_charge), 2),
        "demand_charge_inr": round(float(total_demand_charge), 2),
        "total_kvah": round(float(total_kvah), 2),
        "max_demand_kva": round(float(max_demand), 2),
        "demand_violation": bool(max_demand > 1501.0),
        "avg_power_factor": round(float(avg_pf), 3),
        "pf_drop_events": int(pf_drops),
        "max_current_thd_pct": round(float(max_thd), 2),
        "thd_violations": int(thd_violations)
    }
