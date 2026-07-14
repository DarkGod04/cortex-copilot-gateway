import logging
from functools import lru_cache
import pandas as pd
import os

# Configure professional Python logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def calculate_metrics_for_df(df: pd.DataFrame) -> dict:
    if df.empty:
        return {
            "total_kvah": 0.0,
            "peak_kva": 0.0,
            "avg_pf": 0.0,
            "energy_charge": 0.0,
            "demand_charge": 0.0,
            "total_bill": 0.0,
            "anomaly_string": "No telemetry recorded.",
            "structured_insights": []
        }
        
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

    # Anomalies
    anomalies = []
    if total_kvah == 0:
        anomalies.append("Zero energy consumption recorded; sensor may be offline.")
    if 0 < avg_pf < 0.85:
        anomalies.append(f"PF Drop Detected: Power Factor is low at {round(avg_pf, 2)}. Penalty risk active.")
    elif avg_pf < 0:
        anomalies.append(f"Critical PF Drop: Negative Power Factor ({round(avg_pf, 2)}) indicates reactive power backflow.")
    
    contract_demand_limit = 500.0
    if peak_kva > contract_demand_limit:
        anomalies.append(f"Demand Violation: Peak demand ({round(peak_kva, 2)} kVA) exceeded contract limit of {contract_demand_limit} kVA.")
    
    # Imbalances & THD
    v_unbal_cols = ['V_Unbal_R', 'V_Unbal_Y', 'V_Unbal_B']
    for col in v_unbal_cols:
        if col in df.columns:
            series = pd.to_numeric(df[col], errors='coerce')
            if series.abs().max() > 2.0:
                anomalies.append(f"Imbalance Alert: {col} exceeded the 2% safe threshold.")
                break
                
    thd_cols = ['V_R_THD_Pct', 'V_Y_THD_Pct', 'V_B_THD_Pct']
    for col in thd_cols:
        if col in df.columns:
            series = pd.to_numeric(df[col], errors='coerce')
            if series.max() > 5.0:
                anomalies.append(f"THD Excursion: {col} exceeded the 5% limit. Risk of equipment overheating.")
                break

    anomaly_string = " | ".join(anomalies) if anomalies else "None detected."

    # Structured Insights
    structured_insights = []
    if peak_kva > 500.0:
        impact_demand = (peak_kva - 500.0) * 600.0
        structured_insights.append({
            "type": "danger",
            "title": "Demand Violation",
            "description": f"Peak demand hit {round(peak_kva, 2)} kVA, exceeding the 500 kVA contract limit.",
            "impact_inr": round(impact_demand, 2)
        })
    if 0 < avg_pf < 0.90:
        impact_pf = energy_charge * 0.01
        structured_insights.append({
            "type": "warning",
            "title": "Low Power Factor",
            "description": f"Average Power Factor dropped to {round(avg_pf, 2)}, creating a penalty risk.",
            "impact_inr": round(impact_pf, 2)
        })
        
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
        
    if len(structured_insights) == 0:
        structured_insights.append({
            "type": "success",
            "title": "Optimal Performance",
            "description": "All system parameters operating within safe limits this billing cycle.",
            "impact_inr": 0
        })

    return {
        "total_kvah": total_kvah,
        "peak_kva": peak_kva,
        "avg_pf": avg_pf,
        "energy_charge": energy_charge,
        "demand_charge": demand_charge,
        "total_bill": total_bill,
        "anomaly_string": anomaly_string,
        "structured_insights": structured_insights
    }

@lru_cache(maxsize=10)
def get_tenant_context(tenant_id: str, timeframe: str = "all", target_date: str = None, comparison_date: str = None) -> dict:
    normalized_tenant = tenant_id.lower().replace(' ', '_')
    filename = f"data/{normalized_tenant}.csv"

    try:
        df = pd.read_csv(filename)
        if df.empty:
            return {}

        # Normalize Date column to strict string format (YYYY-MM-DD)
        df['Date'] = pd.to_datetime(df['Date']).dt.strftime('%Y-%m-%d')
        
        # Check comparison vs normal timeframe
        if timeframe == "comparison" and comparison_date:
            df_t = df[df['Date'].str.startswith(target_date)]
            df_c = df[df['Date'].str.startswith(comparison_date)]
            
            t_metrics = calculate_metrics_for_df(df_t)
            c_metrics = calculate_metrics_for_df(df_c)
            
            # Compute deltas
            peak_diff_pct = 0.0
            if c_metrics["peak_kva"] > 0:
                peak_diff_pct = ((t_metrics["peak_kva"] - c_metrics["peak_kva"]) / c_metrics["peak_kva"]) * 100.0
            
            bill_diff_pct = 0.0
            if c_metrics["total_bill"] > 0:
                bill_diff_pct = ((t_metrics["total_bill"] - c_metrics["total_bill"]) / c_metrics["total_bill"]) * 100.0
                
            comp_summary = (
                f"Peak demand changed from {round(c_metrics['peak_kva'], 2)} kVA ({comparison_date}) "
                f"to {round(t_metrics['peak_kva'], 2)} kVA ({target_date}) ({'+' if peak_diff_pct >= 0 else ''}{round(peak_diff_pct, 2)}%). "
                f"Total bill changed from Rs.{round(c_metrics['total_bill'], 2)} "
                f"to Rs.{round(t_metrics['total_bill'], 2)} ({'+' if bill_diff_pct >= 0 else ''}{round(bill_diff_pct, 2)}%)."
            )
            
            return {
                "estimated_bill_inr": round(t_metrics["total_bill"], 2),
                "energy_charge_inr": round(t_metrics["energy_charge"], 2),
                "total_kvah": round(t_metrics["total_kvah"], 2),
                "demand_charge_inr": round(t_metrics["demand_charge"], 2),
                "max_demand_kva": round(t_metrics["peak_kva"], 2),
                "avg_power_factor": round(t_metrics["avg_pf"], 4),
                "system_anomalies": t_metrics["anomaly_string"],
                "structured_insights": t_metrics["structured_insights"],
                "comparison_summary": comp_summary,
                "timeseries_data": []
            }

        # Otherwise, standard timeframe filtering
        if timeframe == "daily" and target_date:
            df_filtered = df[df['Date'] == target_date]
        elif timeframe == "monthly" and target_date:
            df_filtered = df[df['Date'].str.startswith(target_date)]
        else:
            df_filtered = df
            
        if df_filtered.empty:
            return {
                "estimated_bill_inr": "0.00", 
                "max_demand_kva": "0.00", 
                "avg_pf": "0.00", 
                "system_anomalies": f"No telemetry recorded for {target_date if target_date else 'All-Time'}.",
                "structured_insights": [],
                "timeseries_data": []
            }
            
        # Calculate main metrics
        m = calculate_metrics_for_df(df_filtered)
        
        # Calculate timeseries data
        timeseries_data = []
        if timeframe == "daily":
            df_filtered = df_filtered.copy()
            df_filtered['Hour'] = df_filtered['Time'].str.split(':').str[0]
            grouped = df_filtered.groupby('Hour')
            for hour, group in grouped:
                hour_peak = 0.0
                if 'VA_Max' in group.columns:
                    val = pd.to_numeric(group['VA_Max'], errors='coerce').max()
                    if pd.notna(val):
                        hour_peak = float(val) / 1000.0
                hour_pf = 0.0
                if 'True_PF_Avg' in group.columns:
                    val = pd.to_numeric(group['True_PF_Avg'], errors='coerce').mean()
                    if pd.notna(val):
                        hour_pf = float(val)
                timeseries_data.append({
                    "label": f"{hour}:00",
                    "Demand": round(hour_peak, 2),
                    "PF": round(hour_pf, 3)
                })
        elif timeframe == "monthly":
            grouped = df_filtered.groupby('Date')
            for date_str, group in grouped:
                day_label = date_str.split('-')[-1]
                day_peak = 0.0
                if 'VA_Max' in group.columns:
                    val = pd.to_numeric(group['VA_Max'], errors='coerce').max()
                    if pd.notna(val):
                        day_peak = float(val) / 1000.0
                day_pf = 0.0
                if 'True_PF_Avg' in group.columns:
                    val = pd.to_numeric(group['True_PF_Avg'], errors='coerce').mean()
                    if pd.notna(val):
                        day_pf = float(val)
                timeseries_data.append({
                    "label": day_label,
                    "Demand": round(day_peak, 2),
                    "PF": round(day_pf, 3)
                })
        else:
            df_copy = df_filtered.copy()
            df_copy['Month'] = df_copy['Date'].str.slice(0, 7)
            grouped = df_copy.groupby('Month')
            for month_str, group in grouped:
                month_peak = 0.0
                if 'VA_Max' in group.columns:
                    val = pd.to_numeric(group['VA_Max'], errors='coerce').max()
                    if pd.notna(val):
                        month_peak = float(val) / 1000.0
                month_pf = 0.0
                if 'True_PF_Avg' in group.columns:
                    val = pd.to_numeric(group['True_PF_Avg'], errors='coerce').mean()
                    if pd.notna(val):
                        month_pf = float(val)
                timeseries_data.append({
                    "label": month_str,
                    "Demand": round(month_peak, 2),
                    "PF": round(month_pf, 3)
                })
                
        return {
            "estimated_bill_inr": round(m["total_bill"], 2),
            "energy_charge_inr": round(m["energy_charge"], 2),
            "total_kvah": round(m["total_kvah"], 2),
            "demand_charge_inr": round(m["demand_charge"], 2),
            "max_demand_kva": round(m["peak_kva"], 2),
            "avg_power_factor": round(m["avg_pf"], 4),
            "system_anomalies": m["anomaly_string"],
            "structured_insights": m["structured_insights"],
            "timeseries_data": timeseries_data
        }

    except Exception as e:
        logging.error("Error processing tenant context: %s", e)
        return {}