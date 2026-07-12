import ollama

def ask_copilot(user_query: str, tenant_id: str, data_context: dict) -> str:
    system_prompt = (
        f"You are Cortex Copilot, an industrial intelligence assistant for '{tenant_id}'.\n"
        f"RULES:\n"
        f"1. Answer ONLY using the Grounded Context below. \n"
        f"2. If asked about data outside this context (like 2023 data or other factories), say: 'Data unavailable.'\n"
        f"3. Explain THD limits based on the IEEE-519 standard (limit is 5%).\n"
        f"\n"
        f"GROUNDED CONTEXT:\n"
        f"- Estimated Monthly Bill: ₹{data_context.get('estimated_bill_inr')}\n"
        f"- Energy Charges: ₹{data_context.get('energy_charge_inr')} (Total Consumption: {data_context.get('total_kvah')} kVAh)\n"
        f"- Demand Charges: ₹{data_context.get('demand_charge_inr')} \n"
        f"- Peak Demand: {data_context.get('max_demand_kva')} kVA (Contract: 1501 kVA). Violation: {data_context.get('demand_violation')}\n"
        f"- Power Factor: Average {data_context.get('avg_power_factor')}. Anomalous drops below 0.9: {data_context.get('pf_drop_events')} events.\n"
        f"- Current THD: Max {data_context.get('max_current_thd_pct')}%. IEEE-519 Violations (>5%): {data_context.get('thd_violations')} events.\n"
        f"- To reduce energy consumption: Recommend shifting heavy loads from Peak (06-10, 18-22) to Off-Peak (22-06) to leverage Time-of-Day tariff arbitrage."
    )

    response = ollama.chat(
        model='phi3',
        messages=[
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': user_query}
        ]
    )
    
    return response['message']['content']
