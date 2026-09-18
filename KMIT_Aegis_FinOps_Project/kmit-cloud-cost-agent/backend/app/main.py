from __future__ import annotations
from pathlib import Path
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from .config import settings
from .db import Database
from .simulator import CloudSimulator
from .safety import SafetyEngine
from .verification import Verifier
from .audit import ActionAudit
from .tools import ToolRegistry
from .agent_orchestrator import AgentOrchestrator
from .models import AgentRunRequest, ActionRequest

app=FastAPI(title='Aegis FinOps API',version='1.0.0',description='Autonomous cloud cost optimization simulator and agent.')
app.add_middleware(CORSMiddleware,allow_origins=['*'],allow_methods=['*'],allow_headers=['*'])

db=Database(settings.database_path)
sim=CloudSimulator()
safety=SafetyEngine(sim)
verifier=Verifier(sim)
audit=ActionAudit(sim,safety,verifier,db)
tools=ToolRegistry(sim,audit)
agent=AgentOrchestrator(tools,audit,db)

@app.get('/api/system/health')
def system_health(): return {'status':'ok','provider':agent.provider_name,'scenario':sim._scenario}

@app.get('/api/services')
def services(): return sim.services()

@app.get('/api/services/{service_id}')
def service(service_id: str):
    try:return sim.service(service_id)
    except KeyError: raise HTTPException(404,'Service not found')

@app.get('/api/services/{service_id}/metrics')
def metrics(service_id: str): return tools.get_service_metrics(service_id)

@app.get('/api/services/{service_id}/traffic')
def traffic(service_id: str): return tools.get_service_traffic(service_id)

@app.get('/api/services/{service_id}/events')
def events(service_id: str): return tools.get_recent_events(service_id)

@app.get('/api/services/{service_id}/health')
def health(service_id: str): return tools.get_service_health(service_id)

@app.get('/api/pricing')
def pricing(): return tools.get_pricing()

@app.get('/api/audit')
def audit_log(limit: int = Query(100, ge=1, le=500)): return db.recent_audit(limit)

@app.get('/api/actions/{action_id}')
def action_status(action_id: str):
    action = db.get_action(action_id)
    if not action:
        raise HTTPException(404, 'Action not found')
    verification = db.get_verification(action_id)
    return {"action": action, "verification": verification}

@app.get('/api/verifications/{action_id}')
def verification_status(action_id: str):
    verification = db.get_verification(action_id)
    if not verification:
        raise HTTPException(404, 'Verification not found')
    return verification

@app.post('/api/actions/scale')
def scale_action(req: ActionRequest):
    if req.target_instances is None:
        raise HTTPException(400, 'target_instances is required')
    before = sim.service(req.service_id)
    action = 'scale_up' if req.target_instances > before['instances'] else 'scale_down'
    result = audit.execute_action(req.service_id, action, target_instances=req.target_instances)
    return {"action": result, "execution": audit.last_execution, "verification": audit.last_verification}

@app.post('/api/actions/resize')
def resize_action(req: ActionRequest):
    if not req.target_size:
        raise HTTPException(400, 'target_size is required')
    result = audit.execute_action(req.service_id, 'resize', target_size=req.target_size)
    return {"action": result, "execution": audit.last_execution, "verification": audit.last_verification}

@app.post('/api/actions/stop')
def stop_action(req: ActionRequest):
    result = audit.execute_action(req.service_id, 'stop_idle_service')
    return {"action": result, "execution": audit.last_execution, "verification": audit.last_verification}

@app.post('/api/actions/delay-batch')
def delay_batch_action(req: ActionRequest):
    result = audit.execute_action(req.service_id, 'delay_batch')
    return {"action": result, "execution": audit.last_execution, "verification": audit.last_verification}

@app.post('/api/simulator/reset')
def simulator_reset():
    sim.reset()
    return {"status":"ok","scenario":sim._scenario}


@app.get('/api/scenarios')
def scenarios():
    return [
        {'id':'scenario_a_cost_optimization','name':'Test A — Cost Optimization','prompt':'Review the current services and reduce unnecessary cost without breaking the latency or availability requirements.','focus':'Idle capacity and cost evidence'},
        {'id':'scenario_b_rising_traffic','name':'Test B — Rising Traffic','prompt':'Orders traffic is increasing. Keep the service within its latency target.','focus':'Traffic trend and latency headroom'},
        {'id':'scenario_c_stale_observation','name':'Test C — Stale Observation','prompt':'Reduce cost if it is safe.','focus':'Freshness and contradiction detection'},
        {'id':'scenario_d_failed_action','name':'Test D — Failed Action','prompt':'Scale the payment service only if the current state requires it.','focus':'Action failure and verification'},
    ]

@app.post('/api/scenarios/{scenario_id}/run')
def run_scenario(scenario_id: str):
    mapping={x['id']:x for x in scenarios()}
    if scenario_id not in mapping: raise HTTPException(404,'Scenario not found')
    return agent.run(mapping[scenario_id]['prompt'],scenario_id)

@app.post('/api/agent/run')
def run_agent(req: AgentRunRequest):
    try:return agent.run(req.prompt,req.scenario_id)
    except Exception as e: raise HTTPException(500,str(e))

frontend=Path(__file__).resolve().parents[2]/'frontend'
app.mount('/assets',StaticFiles(directory=frontend),name='assets')

@app.get('/')
def index(): return FileResponse(frontend/'index.html')
