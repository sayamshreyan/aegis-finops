from __future__ import annotations
from datetime import datetime, timezone
from .models import ActionProposal, SafetyDecision, SafetyCheck, ActionType
from .config import settings

class SafetyEngine:
    def __init__(self, sim):
        self.sim=sim

    def _age_seconds(self, timestamp: str) -> float:
        ts=datetime.fromisoformat(timestamp.replace('Z','+00:00'))
        now = getattr(self.sim, "clock", datetime.now(timezone.utc))
        return (now-ts).total_seconds()

    def validate(self, p: ActionProposal) -> SafetyDecision:
        try:
            s=self.sim.service(p.service_id)
        except KeyError:
            return SafetyDecision(allowed=False,reason_code="service_not_found",checks=[SafetyCheck(name="service_exists",passed=False,message="Service does not exist")])
        checks=[]
        age=self._age_seconds(s["timestamp"])
        fresh=age <= settings.max_observation_age_seconds
        checks.append(SafetyCheck(name="freshness",passed=fresh,message=f"Observation age {age:.0f}s"))
        checks.append(SafetyCheck(name="health",passed=bool(s["healthy"]),message="Service is healthy" if s["healthy"] else "Service unhealthy"))
        checks.append(SafetyCheck(name="availability",passed=bool(s["available"]),message="Service available" if s["available"] else "Service unavailable"))
        if p.action == ActionType.no_action:
            return SafetyDecision(allowed=True,checks=checks)
        if not fresh: return SafetyDecision(allowed=False,reason_code="stale_observation",checks=checks)
        if not s["healthy"]: return SafetyDecision(allowed=False,reason_code="unhealthy_service",checks=checks)
        if not s["available"]: return SafetyDecision(allowed=False,reason_code="availability_risk",checks=checks)
        if p.action in (ActionType.scale_up, ActionType.scale_down):
            if p.requested_instances is None:
                checks.append(SafetyCheck(name="target",passed=False,message="Target instances required"))
                return SafetyDecision(allowed=False,reason_code="invalid_target",checks=checks)
            ok_min=p.requested_instances>=s["min_instances"]
            ok_max=p.requested_instances<=s["max_instances"]
            checks.append(SafetyCheck(name="min_capacity",passed=ok_min,message=f"Target {p.requested_instances} >= min {s['min_instances']}"))
            checks.append(SafetyCheck(name="max_capacity",passed=ok_max,message=f"Target {p.requested_instances} <= max {s['max_instances']}"))
            if not ok_min: return SafetyDecision(allowed=False,reason_code="below_min_capacity",checks=checks)
            if not ok_max: return SafetyDecision(allowed=False,reason_code="above_max_capacity",checks=checks)
            # Simple deterministic risk guard: never scale down if traffic is clearly rising or latency is close to target.
            if p.requested_instances < s["instances"]:
                traffic = self.sim.traffic(p.service_id)
                prev = traffic.get("previous_requests_per_minute") or s.get("previous_requests_per_minute")
                rising = prev is not None and traffic.get("requests_per_minute",0) > prev*1.2
                latency_risk = s["latency_ms"] >= s["max_latency_ms"]*0.85
                checks.append(SafetyCheck(name="traffic_trend",passed=not rising,message="Traffic is stable/non-rising" if not rising else "Traffic is rising"))
                checks.append(SafetyCheck(name="latency_headroom",passed=not latency_risk,message="Latency headroom acceptable" if not latency_risk else "Latency is close to limit"))
                if rising: return SafetyDecision(allowed=False,reason_code="latency_risk",checks=checks)
                if latency_risk: return SafetyDecision(allowed=False,reason_code="latency_risk",checks=checks)
        if p.action == ActionType.stop_idle_service:
            idle = s["requests_per_minute"] == 0 and s.get("stoppable_when_idle",False)
            checks.append(SafetyCheck(name="idle_and_stoppable",passed=idle,message="Idle and marked stoppable" if idle else "Not safely stoppable"))
            if not idle: return SafetyDecision(allowed=False,reason_code="service_not_idle",checks=checks)
        # latency target must remain satisfied for current snapshot; action may affect future state.
        within = s["latency_ms"] <= s["max_latency_ms"]
        checks.append(SafetyCheck(name="latency_target",passed=within,message=f"Latency {s['latency_ms']}ms / max {s['max_latency_ms']}ms"))
        if not within and p.action in (ActionType.scale_down, ActionType.stop_idle_service):
            return SafetyDecision(allowed=False,reason_code="latency_risk",checks=checks)
        return SafetyDecision(allowed=True,checks=checks)
