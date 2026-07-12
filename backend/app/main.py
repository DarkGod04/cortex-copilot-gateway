from fastapi import FastAPI, Depends, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.database import get_db
from app.analytics import get_tenant_summary
from app.llm_service import ask_copilot

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
    context_data = get_tenant_summary(db, tenant_id)
    ai_response = ask_copilot(user_message, tenant_id, context_data)
    return {"tenant": tenant_id, "response": ai_response}
