from __future__ import annotations
from typing import Any, Callable
from .simulator import CloudSimulator

class ToolRegistry:
    def __init__(self, sim: CloudSimulator, audit):
        self.sim=sim
        self.audit=audit
        self.tools: dict[str, Callable[..., Any]] = {
            "get_all_services": self.get_all_services,
            "get_service": self.get_service,
            "get_service_metrics": self.get_service_metrics,
            "get_service_traffic": self.get_service_traffic,
            "get_recent_events": self.get_recent_events,
            "get_pricing": self.get_pricing,
            "get_service_health": self.get_service_health,
            "get_current_service_state": self.get_current_service_state,
            "request_scale": self.request_scale,
            "request_resize": self.request_resize,
            "request_stop_idle_service": self.request_stop_idle_service,
            "request_delay_batch": self.request_delay_batch,
            "get_action_result": lambda action_id: {"action_id":action_id,"status":"looked_up"},
            "get_fresh_service_state": self.get_fresh_service_state,
            "verify_service_health": self.verify_service_health,
            "verify_latency": self.verify_latency,
            "verify_capacity": self.verify_capacity,
            "calculate_cost_impact": self.calculate_cost_impact,
        }

    def call(self, name: str, args: dict[str, Any]):
        if name not in self.tools:
            raise KeyError(name)
        result = self.tools[name](**args)
        return result

    def get_all_services(self): return self.sim.services()
    def get_service(self, service_id): return self.sim.service(service_id)
    def get_service_metrics(self, service_id):
        s=self.sim.service(service_id)
        return {k:s[k] for k in ["cpu_percent","memory_percent","requests_per_minute","latency_ms","instances","timestamp"]}
    def get_service_traffic(self, service_id): return self.sim.traffic(service_id)
    def get_recent_events(self, service_id): return self.sim.events(service_id)
    def get_pricing(self):
        total=round(sum(float(s["cost_per_hour"]) for s in self.sim.state["services"].values()),2)
        return {"currency":"USD","hourly_total":total,"daily_total":round(total*24,2),"monthly_total":round(total*24*30,2)}
    def get_service_health(self, service_id):
        s=self.sim.service(service_id); return {"healthy":s["healthy"],"available":s["available"],"timestamp":s["timestamp"]}
    def get_current_service_state(self, service_id): return self.sim.service(service_id)
    def get_fresh_service_state(self, service_id): return self.sim.fresh_state(service_id)
    def verify_service_health(self, service_id):
        s=self.sim.fresh_state(service_id); return {"healthy":s["healthy"],"available":s["available"]}
    def verify_latency(self, service_id):
        s=self.sim.fresh_state(service_id); return {"latency_ms":s["latency_ms"],"max_latency_ms":s["max_latency_ms"],"within_target":s["latency_ms"]<=s["max_latency_ms"]}
    def verify_capacity(self, service_id):
        s=self.sim.fresh_state(service_id); return {"instances":s["instances"],"min_instances":s["min_instances"],"max_instances":s["max_instances"]}
    def calculate_cost_impact(self, service_id):
        s=self.sim.service(service_id); return {"hourly_cost":s["cost_per_hour"],"daily_cost":round(s["cost_per_hour"]*24,2),"monthly_cost":round(s["cost_per_hour"]*24*30,2)}
    def request_scale(self, service_id, target_instances):
        return self.audit.execute_action(service_id,"scale_up" if target_instances>self.sim.service(service_id)["instances"] else "scale_down",target_instances=target_instances)
    def request_resize(self, service_id, target_size):
        return self.audit.execute_action(service_id,"resize",target_size=target_size)
    def request_stop_idle_service(self, service_id):
        return self.audit.execute_action(service_id,"stop_idle_service")
    def request_delay_batch(self, service_id):
        return self.audit.execute_action(service_id,"delay_batch")
