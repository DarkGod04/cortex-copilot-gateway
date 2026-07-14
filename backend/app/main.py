import logging
import asyncio
from fastapi import FastAPI, Depends, Header, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.database import get_db
from app.llm_service import ask_copilot, extract_time_intent
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

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []
        
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        
    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            
    async def send_personal_message(self, message: dict, websocket: WebSocket):
        await websocket.send_json(message)
        
manager = ConnectionManager()

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
    
    # Step 1: LLM determines the time intent
    intent = extract_time_intent(user_message)
    logging.info("--- ROUTER INTENT: %s ---", intent)
    
    # Step 2: Pandas slices the dataset to the exact timeframe
    data_context = get_tenant_context(
        tenant_id=tenant_id, 
        timeframe=intent.get("timeframe", "all"), 
        target_date=intent.get("target_date"),
        comparison_date=intent.get("comparison_date")
    )
    logging.info("--- CONTEXT LOADED FOR TIMEFRAME: %s ---", intent.get("timeframe", "all").upper())
    
    # Step 3: LLM generates the formatted human response with full intent awareness
    ai_response = ask_copilot(user_message, tenant_id, data_context, intent)
    
    return {
        "tenant": tenant_id, 
        "response": ai_response,
        "timeseries_data": data_context.get("timeseries_data", [])
    }

@app.get("/api/insights")
def get_insights(tenant_id: str):
    # Insights load the default all-time context to populate the UI banner
    data_context = get_tenant_context(tenant_id=tenant_id)
    
    # Generate suggested prompts dynamically based on active anomalies in context
    anomalies_str = data_context.get("system_anomalies", "").lower()
    prompts = []
    
    if "demand violation" in anomalies_str:
        prompts.append("Why is my Peak Demand exceeding limits?")
        prompts.append("What was my peak demand on May 20, 2026?")
    if "pf drop" in anomalies_str or "power factor" in anomalies_str:
        prompts.append("What caused the low Power Factor?")
        prompts.append("Show my average Power Factor trend.")
    if "thd" in anomalies_str:
        prompts.append("Explain my THD excursion alerts.")
        
    # General default suggested prompts
    prompts.append("What is my estimated bill for June 2026?")
    prompts.append("Compare June 2026 peak demand to May 2026.")
    
    # De-duplicate and take top 4
    unique_prompts = list(dict.fromkeys(prompts))[:4]
    
    return {
        "insights": data_context.get("structured_insights", []),
        "suggested_prompts": unique_prompts
    }

@app.websocket("/ws/alerts/{tenant_id}")
async def websocket_alerts(websocket: WebSocket, tenant_id: str):
    await manager.connect(websocket)
    logging.info("WebSocket client connected for tenant: %s", tenant_id)
    
    try:
        # Send a system active message
        await manager.send_personal_message({
            "type": "info",
            "title": "System Active",
            "description": f"Connected to live alert feed for {tenant_id}."
        }, websocket)
        
        # Periodic check to push simulated real-time anomalies for testing
        await asyncio.sleep(4)
        
        # Retrieve the tenant context to fetch any real active alerts
        ctx = get_tenant_context(tenant_id)
        anomalies = ctx.get("system_anomalies", "").split(" | ")
        
        for anomaly in anomalies:
            if anomaly and anomaly != "None detected.":
                await manager.send_personal_message({
                    "type": "alert",
                    "title": "Real-Time Excursion",
                    "description": anomaly
                }, websocket)
                await asyncio.sleep(2)
                
        while True:
            # Keep connection alive
            await websocket.receive_text()
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logging.info("WebSocket client disconnected for tenant: %s", tenant_id)
    except Exception as e:
        logging.error("WebSocket error: %s", e)
        manager.disconnect(websocket)

# Serve production React assets and index.html (Single Page App routing)
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

dist_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../frontend/dist"))

if os.path.exists(dist_dir):
    app.mount("/assets", StaticFiles(directory=os.path.join(dist_dir, "assets")), name="assets")
    
    @app.get("/{fallback_path:path}")
    def serve_frontend(fallback_path: str):
        # Exclude API endpoints from routing to frontend fallback
        if fallback_path.startswith("api/") or fallback_path.startswith("ws/"):
            raise HTTPException(status_code=404, detail="API route not found")
        return FileResponse(os.path.join(dist_dir, "index.html"))
