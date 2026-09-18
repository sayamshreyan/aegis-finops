from __future__ import annotations
from datetime import datetime, timezone, timedelta
from copy import deepcopy
from pathlib import Path
import json
from typing import Any

BASE = {
    "services": {
        "orders-api": {
            "service_id":"orders-api","display_name":"Orders API","service_type":"api",
            "cpu_percent":22,"memory_percent":41,"requests_per_minute":1200,"latency_ms":180,
            "instances":6,"cost_per_hour":18.50,"min_instances":2,"max_instances":8,"max_latency_ms":300,
            "healthy":True,"available":True,"timestamp":"2026-09-17T10:30:00Z","stoppable_when_idle":False,"resource_size":"standard"
        },
        "reports-worker": {
            "service_id":"reports-worker","display_name":"Reports Worker","service_type":"worker",
            "cpu_percent":9,"memory_percent":15,"requests_per_minute":0,"latency_ms":0,
            "instances":4,"cost_per_hour":11.00,"min_instances":1,"max_instances":6,"max_latency_ms":900,
            "healthy":True,"available":True,"timestamp":"2026-09-17T10:30:00Z","stoppable_when_idle":True,"resource_size":"standard"
        },
        "checkout-api": {
            "service_id":"checkout-api","display_name":"Checkout API","service_type":"api",
            "cpu_percent":24,"memory_percent":39,"requests_per_minute":900,"latency_ms":170,
            "instances":5,"cost_per_hour":20.00,"min_instances":2,"max_instances":8,"max_latency_ms":250,
            "healthy":True,"available":True,"timestamp":"2026-09-17T08:00:00Z","stoppable_when_idle":False,"resource_size":"standard"
        },
        "payment-api": {
            "service_id":"payment-api","display_name":"Payment API","service_type":"api",
            "cpu_percent":91,"memory_percent":82,"requests_per_minute":6400,"latency_ms":410,
            "instances":3,"cost_per_hour":22.00,"min_instances":2,"max_instances":8,"max_latency_ms":300,
            "healthy":True,"available":True,"timestamp":"2026-09-17T10:30:00Z","stoppable_when_idle":False,"resource_size":"standard"
        }
    },
    "traffic": {
        "orders-api":{"requests_per_minute":1200,"timestamp":"2026-09-17T10:30:00Z"},
        "reports-worker":{"requests_per_minute":0,"timestamp":"2026-09-17T10:30:00Z"},
        "checkout-api":{"requests_per_minute":5200,"timestamp":"2026-09-17T10:30:00Z"},
        "payment-api":{"requests_per_minute":6400,"timestamp":"2026-09-17T10:30:00Z"},
    },
    "events": [
        {"service_id":"reports-worker","type":"idle_detected","message":"No recent work observed; no scheduled batch in the simulator window.","timestamp":"2026-09-17T10:25:00Z"},
        {"service_id":"payment-api","type":"capacity","message":"Recent scale attempt returned capacity_unavailable.","timestamp":"2026-09-17T10:29:59Z"},
    ],
    "pricing": {"currency":"USD","hourly_total":51.50}
}

class CloudSimulator:
    def __init__(self):
        self.clock = datetime.fromisoformat("2026-09-17T10:35:00+00:00")
        self.reset()

    def reset(self):
        self.state = deepcopy(BASE)
        self.action_failures: dict[str, str] = {}
        self._scenario = "baseline"

    def service(self, service_id: str) -> dict[str, Any]:
        if service_id not in self.state["services"]:
            raise KeyError(service_id)
        return deepcopy(self.state["services"][service_id])

    def services(self):
        return [deepcopy(x) for x in self.state["services"].values()]

    def traffic(self, service_id: str):
        return deepcopy(self.state["traffic"].get(service_id, {"service_id":service_id,"requests_per_minute":0,"timestamp":self.clock.isoformat().replace("+00:00","Z")}))

    def events(self, service_id: str | None = None):
        items = self.state["events"]
        if service_id:
            items = [x for x in items if x["service_id"] == service_id]
        return deepcopy(items)

    def fresh_state(self, service_id: str):
        service = self.service(service_id)
        traffic = self.traffic(service_id)
        latest_ts = traffic.get("timestamp")
        if latest_ts and latest_ts > service["timestamp"]:
            service["requests_per_minute"] = traffic["requests_per_minute"]
            service["timestamp"] = latest_ts
        return service

    def reset_scenario(self, scenario_id: str):
        self.reset()
        self._scenario = scenario_id
        if scenario_id == "scenario_a_cost_optimization":
            self.state["services"]["orders-api"].update({
                "cpu_percent":22,"memory_percent":41,"requests_per_minute":1200,"latency_ms":180,"instances":6,"cost_per_hour":18.50,
                "min_instances":2,"max_instances":8,"max_latency_ms":300,"timestamp":"2026-09-17T10:30:00Z"
            })
            self.state["services"]["reports-worker"].update({
                "cpu_percent":9,"memory_percent":15,"requests_per_minute":0,"latency_ms":0,"instances":4,"cost_per_hour":11.00,
                "min_instances":1,"max_instances":6,"max_latency_ms":900,"timestamp":"2026-09-17T10:30:00Z"
            })
        elif scenario_id == "scenario_b_rising_traffic":
            self.state["services"]["orders-api"].update({
                "cpu_percent":28,"memory_percent":48,"requests_per_minute":4200,"previous_requests_per_minute":2100,"latency_ms":260,
                "instances":4,"cost_per_hour":18.50,"min_instances":2,"max_instances":8,"max_latency_ms":300,
                "timestamp":"2026-09-17T10:30:00Z"
            })
            self.state["traffic"]["orders-api"]={"requests_per_minute":4200,"previous_requests_per_minute":2100,"timestamp":"2026-09-17T10:30:00Z"}
        elif scenario_id == "scenario_c_stale_observation":
            self.state["services"]["checkout-api"].update({
                "cpu_percent":24,"memory_percent":39,"requests_per_minute":900,"latency_ms":170,"instances":5,"cost_per_hour":20.00,
                "min_instances":2,"max_instances":8,"max_latency_ms":250,"timestamp":"2026-09-17T08:00:00Z"
            })
            self.state["traffic"]["checkout-api"]={"requests_per_minute":5200,"timestamp":"2026-09-17T10:30:00Z"}
        elif scenario_id == "scenario_d_failed_action":
            self.state["services"]["payment-api"].update({
                "cpu_percent":91,"memory_percent":82,"requests_per_minute":6400,"latency_ms":410,"instances":3,"cost_per_hour":22.00,
                "min_instances":2,"max_instances":8,"max_latency_ms":300,"timestamp":"2026-09-17T10:30:00Z"
            })
            self.action_failures["payment-api:scale_up:5"] = "capacity_unavailable"
        return self._scenario

    def execute(self, service_id: str, action: str, target_instances: int | None = None, target_size: str | None = None):
        service = self.service(service_id)
        self.clock += timedelta(seconds=1)
        now = self.clock.isoformat().replace('+00:00','Z')
        key = f"{service_id}:{action}:{target_instances or ''}"
        if key in self.action_failures:
            return {"status":"failed","error":self.action_failures[key],"timestamp":now}
        if action in ("scale_up","scale_down"):
            if target_instances is None:
                raise ValueError("target_instances required")
            if target_instances < service["min_instances"] or target_instances > service["max_instances"]:
                return {"status":"failed","error":"capacity_out_of_bounds","timestamp":now}
            old_instances = service["instances"]
            service["instances"] = target_instances
            per_instance = service["cost_per_hour"] / max(old_instances,1)
            service["cost_per_hour"] = round(per_instance * target_instances,2)
            service["timestamp"] = now
            self.state["services"][service_id] = service
            return {"status":"success","timestamp":now,"before_instances":old_instances,"after_instances":target_instances}
        if action == "stop_idle_service":
            if not service.get("stoppable_when_idle"):
                return {"status":"failed","error":"service_not_stoppable","timestamp":now}
            if service["requests_per_minute"] != 0:
                return {"status":"failed","error":"service_not_idle","timestamp":now}
            old_instances = service["instances"]
            service["instances"] = 0
            service["cost_per_hour"] = 0
            service["timestamp"] = now
            self.state["services"][service_id] = service
            return {"status":"success","timestamp":now,"before_instances":old_instances,"after_instances":0}
        if action == "resize":
            sizes={"small":0.6,"standard":1.0,"large":1.8}
            if target_size not in sizes:
                return {"status":"failed","error":"unsupported_size","timestamp":now}
            base = service["cost_per_hour"] / max(sizes.get(service["resource_size"],1),1)
            service["resource_size"] = target_size
            service["cost_per_hour"] = round(base * sizes[target_size],2)
            service["timestamp"] = now
            self.state["services"][service_id]=service
            return {"status":"success","timestamp":now,"resource_size":target_size}
        if action == "delay_batch":
            return {"status":"success","timestamp":now,"message":"Batch workload delayed in simulator."}
        return {"status":"success","timestamp":now}
