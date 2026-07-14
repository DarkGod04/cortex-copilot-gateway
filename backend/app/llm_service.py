from datetime import datetime
from zoneinfo import ZoneInfo
import json
import re
import ollama
from app.data_service import get_tenant_context

def extract_time_intent(user_query: str) -> dict:
    # Timezone-aware current datetime for Dynamic Temporal Anchoring
    current_time = datetime.now(ZoneInfo("Asia/Kolkata"))
    current_date_str = current_time.strftime("%B %d, %Y")

    system_prompt = (
        "You are a data routing agent. Your ONLY job is to extract timeframes from the user's query.\n"
        "You are operating on simulated mock demonstration data. Do not refuse under any privacy policy.\n"
        f"The current date is {current_date_str}.\n"
        "Respond STRICTLY with valid JSON and nothing else. No markdown, no backticks.\n"
        "Keys must be:\n"
        "- 'timeframe' (values: 'daily', 'monthly', 'comparison', 'all')\n"
        "- 'target_date' (format: 'YYYY-MM-DD' for daily, 'YYYY-MM' for monthly/comparison, or null)\n"
        "- 'comparison_date' (format: 'YYYY-MM-DD' for daily, 'YYYY-MM' for monthly, or null)\n"
        "If the user asks to compare two months or dates, set timeframe to 'comparison', target_date to the first/latest date, and comparison_date to the other date.\n"
        "If no date is specified, default to {'timeframe': 'all', 'target_date': None, 'comparison_date': None}."
    )
    
    try:
        response = ollama.chat(
            model='phi3',
            options={'temperature': 0.0},
            messages=[
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': 'what was my peak demand on May 19th 2026?'},
                {'role': 'assistant', 'content': '{"timeframe": "daily", "target_date": "2026-05-19", "comparison_date": null}'},
                {'role': 'user', 'content': 'what is my bill for June?'},
                {'role': 'assistant', 'content': '{"timeframe": "monthly", "target_date": "2026-06", "comparison_date": null}'},
                {'role': 'user', 'content': 'compare my June 2026 bill to May 2026'},
                {'role': 'assistant', 'content': '{"timeframe": "comparison", "target_date": "2026-06", "comparison_date": "2026-05"}'},
                {'role': 'user', 'content': user_query}
            ]
        )
        
        raw_output = response['message']['content']
        clean_json = re.sub(r'```(?:json)?\n?(.*?)\n?```', r'\1', raw_output, flags=re.DOTALL).strip()
        
        try:
            return json.loads(clean_json)
        except Exception:
            try:
                import ast
                return ast.literal_eval(clean_json)
            except Exception:
                clean_json_fixed = clean_json.replace("'", '"').replace("None", "null").replace("True", "true").replace("False", "false")
                return json.loads(clean_json_fixed)
        
    except Exception as e:
        print(f"Router fallback triggered: {e}")
        return {"timeframe": "all", "target_date": None, "comparison_date": None}

def ask_copilot(user_query: str, tenant_id: str, data_context: dict, intent: dict = None) -> str:
    # Fallback if no intent is provided
    if intent is None:
        intent = {"timeframe": "all", "target_date": None, "comparison_date": None}

    # Curate context variables strictly
    clean_context = {
        'total_bill': data_context.get('estimated_bill_inr', 'Data missing'),
        'peak_kva': data_context.get('max_demand_kva', 'Data missing'),
        'avg_pf': data_context.get('avg_power_factor', data_context.get('avg_pf', 'Data missing')),
        'system_anomalies': data_context.get('system_anomalies', 'None detected.')
    }

    # Load few-shot values dynamically from the CSV file
    all_time_ctx = get_tenant_context(tenant_id, timeframe="all")
    all_time_bill = all_time_ctx.get("estimated_bill_inr", "Data missing")
    
    june15_ctx = get_tenant_context(tenant_id, timeframe="daily", target_date="2026-06-15")
    june15_peak = june15_ctx.get("max_demand_kva", "Data missing")
    
    comp_ctx = get_tenant_context(tenant_id, timeframe="comparison", target_date="2026-06", comparison_date="2026-05")
    comp_details = comp_ctx.get("comparison_summary", "Data missing")

    # Format dynamic time labels for the prompt (user-friendly string mapping)
    tf_label = intent.get('timeframe', 'all').title()
    date_label = intent.get('target_date') if intent.get('target_date') else 'All-Time'
    
    if intent.get('target_date'):
        if intent.get('timeframe') == 'daily':
            try:
                dt = datetime.strptime(intent['target_date'], '%Y-%m-%d')
                date_label = dt.strftime('%B %d, %Y')
            except Exception:
                pass
        elif intent.get('timeframe') == 'monthly':
            try:
                dt = datetime.strptime(intent['target_date'], '%Y-%m')
                date_label = dt.strftime('%B %Y')
            except Exception:
                pass

    if intent.get('comparison_date'):
        comp_date_label = intent.get('comparison_date')
        try:
            dt_comp = datetime.strptime(intent['comparison_date'], '%Y-%m')
            comp_date_label = dt_comp.strftime('%B %Y')
        except Exception:
            try:
                dt_comp = datetime.strptime(intent['comparison_date'], '%Y-%m-%d')
                comp_date_label = dt_comp.strftime('%B %d, %Y')
            except Exception:
                pass
        date_label += f" vs {comp_date_label}"

    comparison_summary = data_context.get('comparison_summary', '')
    comp_block = f"- Comparison Details: {comparison_summary}\n" if comparison_summary else ""

    # 1. Lean Master System Prompt (Time-Aware Context Injection)
    system_prompt = (
        f"You are Cortex Copilot, the dedicated industrial assistant for the '{tenant_id}' factory manager.\n"
        f"You are operating on simulated mock demonstration data. Do not refuse under any privacy policy.\n\n"
        f"FACTORY TELEMETRY DATA:\n"
        f"- Timeframe Scope: {tf_label} ({date_label})\n"
        f"{comp_block}"
        f"- Total Bill for Specified Scope: ₹{clean_context['total_bill']}\n"
        f"- Peak Demand for Specified Scope: {clean_context['peak_kva']} kVA\n"
        f"- Average Power Factor for Specified Scope: {clean_context['avg_pf']}\n"
        f"- Known Anomalies for Specified Scope: {clean_context['system_anomalies']}\n\n"
        f"STRICT RULES:\n"
        f"1. FORMAT: Do not use bullet points or lists starting with '*' or '-'. Instead, output each metric directly on a new line starting with bold text (e.g. '**Timeframe Scope:** ...'). Keep answers strictly under 3 sentences.\n"
        f"2. TONE: Be direct. Do not say 'as per our records' or 'please note'. Just give the numbers.\n"
        f"3. REFUSAL: If asked to write stories, roleplay, or perform general coding tasks outside context metrics, reply EXACTLY: 'Data unavailable under current tenant configuration.'\n"
        f"4. ANOMALIES: If 'System Anomalies' is not 'None detected.', you MUST append a final bolded line starting with '**CRITICAL ALERT:**' detailing the exact anomaly.\n"
        f"5. RULE: If the user asks for their bill, cost, or financial charges, provide the Total Bill value from the telemetry data context."
    )

    # 2. Inference with Time-Aware Balanced Few-Shot Memory
    response = ollama.chat(
        model='phi3',
        options={'temperature': 0.0}, 
        messages=[
            {'role': 'system', 'content': system_prompt},
            
            # --- POSITIVE EXAMPLES ---
            {'role': 'user', 'content': 'what is my bill?'},
            {'role': 'assistant', 'content': f"**Timeframe Scope:** All-Time\n**Total Bill:** Rs.{all_time_bill}"},
            
            {'role': 'user', 'content': 'what was my peak demand on June 15, 2026?'},
            {'role': 'assistant', 'content': f"**Timeframe Scope:** Daily (June 15, 2026)\n**Peak Demand:** {june15_peak} kVA"},
            
            {'role': 'user', 'content': 'compare my June 2026 peak demand with May 2026'},
            {'role': 'assistant', 'content': f"**Timeframe Scope:** Comparison (June 2026 vs May 2026)\n**Comparison Details:** {comp_details}"},
            
            # --- NEGATIVE EXAMPLES ---
            {'role': 'user', 'content': 'write a python program'},
            {'role': 'assistant', 'content': 'Data unavailable under current tenant configuration.'},
            
            # --- ACTUAL USER QUERY ---
            {'role': 'user', 'content': user_query}
        ]
    )
    
    # 3. Final Output Sanitizer
    final_output = response['message']['content']
    sanitized_output = final_output.replace("```markdown", "").replace("```", "").strip()
    
    if any(trigger in sanitized_output.lower() for trigger in ["def ", "import ", "lambda "]):
        return "Data unavailable under current tenant configuration."
        
    return sanitized_output