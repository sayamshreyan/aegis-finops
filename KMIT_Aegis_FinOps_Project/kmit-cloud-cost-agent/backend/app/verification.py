from __future__ import annotations
from .models import VerificationResult, LifecycleStatus, SafetyCheck

class Verifier:
    def __init__(self, sim): self.sim=sim
    def verify(self, action_id: str, service_id: str, before: dict, execution: dict):
        after=self.sim.fresh_state(service_id)
        checks=[
            SafetyCheck(name="actual_state_retrieved",passed=True,message="Fresh state retrieved after action."),
            SafetyCheck(name="health",passed=bool(after["healthy"]),message="Healthy after action" if after["healthy"] else "Unhealthy after action"),
            SafetyCheck(name="availability",passed=bool(after["available"]),message="Available after action" if after["available"] else "Unavailable after action"),
            SafetyCheck(name="latency",passed=after["latency_ms"]<=after["max_latency_ms"],message=f"{after['latency_ms']}ms / {after['max_latency_ms']}ms"),
            SafetyCheck(name="capacity",passed=after["instances"]>=after["min_instances"] or after["instances"]==0 and after.get("stoppable_when_idle"),message=f"Instances={after['instances']}")
        ]
        before_cost=float(before.get("cost_per_hour",0)); after_cost=float(after.get("cost_per_hour",0))
        delta=round(after_cost-before_cost,2)
        if execution["status"] != "success":
            return VerificationResult(action_id=action_id,status=LifecycleStatus.failed,verified=False,summary=f"Execution failed: {execution.get('error','unknown')}",before=before,after=after,checks=checks,cost_delta_per_hour=delta)
        verified=all(c.passed for c in checks)
        status=LifecycleStatus.verified if verified else LifecycleStatus.partial
        summary="Action executed and verified against fresh state." if verified else "Action executed, but one or more post-action checks did not pass."
        return VerificationResult(action_id=action_id,status=status,verified=verified,summary=summary,before=before,after=after,checks=checks,cost_delta_per_hour=delta)
