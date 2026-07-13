import logging
from functools import lru_cache
import pandas as pd
import os

# Configure professional Python logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

@lru_cache(maxsize=10)
def get_tenant_context(tenant_id: str) -> dict:
    normalized_tenant = tenant_id.lower().replace(' ', '_')
    filename = f"data/{normalized_tenant}.csv"

    try:
        df = pd.read_csv(filename)
        if df.empty:
            return {}

        # --- 1. CORE METRICS CALCULATION ---
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

        # --- 2. DETERMINISTIC ANALYTICS (ANOMALY DETECTION) ---
        anomalies = []

        # A. Null/Missing Data Check
        if total_kvah == 0:
            anomalies.append("Zero energy consumption recorded; sensor may be offline.")

        # B. PF Drops (Power Factor Anomalies)
        if 0 < avg_pf < 0.85:
            anomalies.append(f"PF Drop Detected: Power Factor is low at {round(avg_pf, 2)}. Penalty risk active.")
        elif avg_pf < 0:
            anomalies.append(f"Critical PF Drop: Negative Power Factor ({round(avg_pf, 2)}) indicates reactive power backflow.")

        # C. Demand Violations (Assuming a contract limit of 500 kVA)
        contract_demand_limit = 500.0
        if peak_kva > contract_demand_limit:
            anomalies.append(f"Demand Violation: Peak demand ({round(peak_kva, 2)} kVA) exceeded contract limit of {contract_demand_limit} kVA.")

        # D. Imbalance (Voltage Phase Imbalance > 2%)
        v_unbal_cols = ['V_Unbal_R', 'V_Unbal_Y', 'V_Unbal_B']
        for col in v_unbal_cols:
            if col in df.columns:
                series = pd.to_numeric(df[col], errors='coerce')
                if series.abs().max() > 2.0:
                    anomalies.append(f"Imbalance Alert: {col} exceeded the 2% safe threshold.")
                    break

        # E. THD Excursions (Total Harmonic Distortion > 5%)
        thd_cols = ['V_R_THD_Pct', 'V_Y_THD_Pct', 'V_B_THD_Pct']
        for col in thd_cols:
            if col in df.columns:
                series = pd.to_numeric(df[col], errors='coerce')
                if series.max() > 5.0:
                    anomalies.append(f"THD Excursion: {col} exceeded the 5% limit. Risk of equipment overheating.")
                    break

        anomaly_string = " | ".join(anomalies) if anomalies else "None detected."

        # --- 3. CACHING & FINANCIAL ANALYTICS (PROACTIVE INSIGHTS) ---
        structured_insights = []

        # Demand Violation Insight
        if peak_kva > 500.0:
            impact_demand = (peak_kva - 500.0) * 600.0
            structured_insights.append({
                "type": "danger",
                "title": "Demand Violation",
                "description": f"Peak demand hit {round(peak_kva, 2)} kVA, exceeding the 500 kVA contract limit.",
                "impact_inr": round(impact_demand, 2)
            })

        # PF Drop Insight
        if 0 < avg_pf < 0.90:
            impact_pf = energy_charge * 0.01
            structured_insights.append({
                "type": "warning",
                "title": "Low Power Factor",
                "description": f"Average Power Factor dropped to {round(avg_pf, 2)}, creating a penalty risk.",
                "impact_inr": round(impact_pf, 2)
            })

        # THD Excursion Insight
        max_v_thd = 0.0
        for col in ['V_R_THD_Pct', 'V_Y_THD_Pct', 'V_B_THD_Pct']:
            if col in df.columns:
                series = pd.to_numeric(df[col], errors='coerce')
                m_val = series.max()
                if pd.notna(m_val) and m_val > max_v_thd:
                    max_v_thd = float(m_val)
        
        if max_v_thd > 5.0:
            structured_insights.append({
                "type": "danger",
                "title": "THD Excursion",
                "description": "Total Harmonic Distortion exceeded the 5% IEEE safe limit. High risk of equipment overheating.",
                "impact_inr": 5000.00
            })

        # Success State
        if len(structured_insights) == 0:
            structured_insights.append({
                "type": "success",
                "title": "Optimal Performance",
                "description": "All system parameters operating within safe limits this billing cycle.",
                "impact_inr": 0
            })

        # --- 4. RETURN STRUCTURED CONTEXT ---
        return {
            "estimated_bill_inr": round(total_bill, 2),
            "energy_charge_inr": round(energy_charge, 2),
            "total_kvah": round(total_kvah, 2),
            "demand_charge_inr": round(demand_charge, 2),
            "max_demand_kva": round(peak_kva, 2),
            "avg_power_factor": round(avg_pf, 4),
            "system_anomalies": anomaly_string,
            "structured_insights": structured_insights
        }

    except Exception as e:
        logging.error("Error processing tenant context: %s", e)
        return {}