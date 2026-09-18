from __future__ import annotations
from datetime import datetime, timezone
from uuid import uuid4
from .models import ActionProposal, ActionExecution, LifecycleStatus

class ActionAudit:
    def __init__(self, sim, safety, verifier, db):
        self.sim=sim; self.safety=safety; self.verifier=verifier; self.db=db; self.last_verification=None; self.last_execution=None
    def now(self): return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
    def execute_action(self, service_id, action, target_instances=None, target_size=None):
        before=self.sim.service(service_id)
        proposal=ActionProposal(service_id=service_id,action=action,requested_instances=target_instances,requested_size=target_size)
        decision=self.safety.validate(proposal)
        run_id=getattr(self,'run_id',None)
        self.db.log_event(run_id,'safety_decision',decision.model_dump(),self.now())
        action_id='act-'+uuid4().hex[:8]
        if not decision.allowed:
            execution=ActionExecution(action_id=action_id,service_id=service_id,action=action,requested_instances=target_instances,status=LifecycleStatus.blocked,error=decision.reason_code,requested_at=self.now())
            self.db.save_action(execution.model_dump(mode='json'),run_id)
            self.db.log_event(run_id,'action_blocked',execution.model_dump(mode='json'),self.now())
            self.last_execution=execution
            self.last_verification=None
            return {'status':'blocked','action_id':action_id,'reason':decision.reason_code,'checks':[c.model_dump() for c in decision.checks]}
        self.db.log_event(run_id,'action_authorized',proposal.model_dump(mode='json'),self.now())
        result=self.sim.execute(service_id,action,target_instances=target_instances,target_size=target_size)
        status=LifecycleStatus.executed if result['status']=='success' else LifecycleStatus.failed
        execution=ActionExecution(action_id=action_id,service_id=service_id,action=action,requested_instances=target_instances,status=status,error=result.get('error'),requested_at=self.now(),completed_at=self.now())
        self.db.save_action(execution.model_dump(mode='json'),run_id)
        self.db.log_event(run_id,'action_execution',execution.model_dump(mode='json')|result,self.now())
        self.last_execution=execution
        self.last_verification=self.verifier.verify(action_id,service_id,before,result)
        self.db.save_verification(self.last_verification.model_dump(mode='json'),run_id,self.now())
        self.db.log_event(run_id,'verification',self.last_verification.model_dump(mode='json'),self.now())
        return {'status':result['status'],'action_id':action_id,'error':result.get('error'),'execution':execution.model_dump(mode='json'),'verification':self.last_verification.model_dump(mode='json')}
