import pandas as pd
import os

def get_tenant_context(tenant_id: str) -> dict:
    filename = f"{tenant_id.lower()}.csv"
    file_path = os.path.join("data", filename)

    try:
        df = pd.read_csv(file_path)
        if df.empty:
            return {}

        total_kvah = 0.0
        if 'VAh_Received' in df.columns:
            series = pd.to_numeric(df['VAh_Received'], errors='coerce')
            val = series.max()
            if pd.notna(val):
                total_kvah = float(val) / 1000.0

        peak_kva = 0.0
        if 'VA_Max' in df.columns:
            series = pd.to_numeric(df['VA_Max'], errors='coerce')
            val = series.max()
            if pd.notna(val):
                peak_kva = float(val) / 1000.0

        avg_pf = 0.0
        if 'True_PF_Avg' in df.columns:
            series = pd.to_numeric(df['True_PF_Avg'], errors='coerce')
            val = series.mean()
            if pd.notna(val):
                avg_pf = float(val)

        energy_charge = total_kvah * 7.5
        demand_charge = peak_kva * 500
        total_bill = energy_charge + demand_charge

        return {
            "estimated_bill_inr": round(total_bill, 2),
            "energy_charge_inr": round(energy_charge, 2),
            "total_kvah": round(total_kvah, 2),
            "demand_charge_inr": round(demand_charge, 2),
            "max_demand_kva": round(peak_kva, 2),
            "avg_power_factor": round(avg_pf, 4)
        }

    except Exception as e:
        print(f"Error processing tenant context: {e}")
        return {}