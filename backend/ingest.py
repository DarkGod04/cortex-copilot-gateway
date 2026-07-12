import pandas as pd
from datetime import datetime
from app.database import engine, SessionLocal, Base
from app.models import TelemetryData, TenantConfig

Base.metadata.create_all(bind=engine)

def load_tenant_data(file_path: str, tenant_name: str):
    db = SessionLocal()
    try:
        tenant = db.query(TenantConfig).filter(TenantConfig.tenant_id == tenant_name).first()
        if not tenant:
            tenant = TenantConfig(tenant_id=tenant_name, contracted_demand_kva=1501.0)
            db.add(tenant)
            db.commit()
            
        df = pd.read_csv(file_path)
        records = []
        for index, row in df.iterrows():
            dt_str = f"{row['Date']} {row['Time']}"
            timestamp = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
            
            telemetry = TelemetryData(
                tenant_id=tenant_name,
                timestamp=timestamp,
                watts_total=float(row['Watts_Total']),
                va_total=float(row['VA_Total']),
                var_total=float(row['VAR_Total']),
                true_pf_avg=float(row['True_PF_Avg']),
                frequency=float(row['Frequency_Hz']),
                v_r_thd_pct=float(row['V_R_THD_Pct']),
                i_r_thd_pct=float(row['I_R_THD_Pct']),
                v_r=float(row['V_R']),
                v_y=float(row['V_Y']),
                v_b=float(row['V_B']),
                i_r=float(row['I_R']),
                i_y=float(row['I_Y']),
                i_b=float(row['I_B'])
            )
            records.append(telemetry)
            if len(records) >= 1000:
                db.bulk_save_objects(records)
                db.commit()
                records = []
                
        if records:
            db.bulk_save_objects(records)
            db.commit()
    finally:
        db.close()

if __name__ == "__main__":
    load_tenant_data("data/tenant_a.csv", "Tenant_A")
    load_tenant_data("data/tenant_b.csv", "Tenant_B")
