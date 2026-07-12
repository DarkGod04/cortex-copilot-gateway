import ollama

def ask_copilot(user_query: str, tenant_id: str, data_context: dict) -> str:
    system_prompt = (
        f"You are Cortex Copilot, an industrial intelligence assistant.\n"
        f"You are explicitly serving context for '{tenant_id}'.\n"
        f"CRITICAL SAFETY RULES:\n"
        f"1. Base your numeric answers ONLY on the Grounded Context provided below.\n"
        f"2. If the user asks for data outside this context, you MUST explicitly state: 'Data unavailable under current tenant configuration.' Do NOT fabricate numbers.\n"
        f"Grounded Context for {tenant_id}:\n"
        f"- Contracted Demand: 1501 kVA\n"
        f"- Peak Demand Observed: {data_context['max_demand_kva']} kVA\n"
        f"- Average Power Factor: {data_context['avg_power_factor']}\n"
        f"- Max Current THD Spike: {data_context['max_current_thd_pct']}%\n"
        f"- Contracted Demand Exceeded: {data_context['demand_violation']}"
    )

    response = ollama.chat(
        model='phi3',
        messages=[
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': user_query}
        ]
    )
    
    return response['message']['content']
