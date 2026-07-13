import logging
from fastapi import FastAPI, Depends, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.database import get_db
from app.llm_service import ask_copilot
from app.data_service import get_tenant_context

# Configure professional Python logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def verify_tenant_isolation(x_tenant_id: str = Header(...)):
    if x_tenant_id not in ("Tenant_A", "Tenant_B"):
        raise HTTPException(status_code=403, detail="Invalid Tenant Scope")
    return x_tenant_id

@app.post("/api/chat")
def chat(
    payload: dict,
    tenant_id: str = Depends(verify_tenant_isolation),
    db: Session = Depends(get_db)
):
    user_message = payload.get("message", "")
    data_context = get_tenant_context(tenant_id)
    logging.info("LOADED CONTEXT: %s", data_context)
    ai_response = ask_copilot(user_message, tenant_id, data_context)
    return {"tenant": tenant_id, "response": ai_response}

@app.get("/api/insights")
def get_insights(tenant_id: str):
    data_context = get_tenant_context(tenant_id=tenant_id)
    return {"insights": data_context.get("structured_insights", [])}
