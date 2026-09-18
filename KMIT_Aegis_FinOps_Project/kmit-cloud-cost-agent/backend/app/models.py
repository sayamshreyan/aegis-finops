from __future__ import annotations
from enum import Enum
from typing import Any
from pydantic import BaseModel, Field, ConfigDict

class ActionType(str, Enum):
    scale_up = "scale_up"
    scale_down = "scale_down"
    resize = "resize"
    stop_idle_service = "stop_idle_service"
    delay_batch = "delay_batch"
    no_action = "no_action"

class LifecycleStatus(str, Enum):
    proposed = "PROPOSED"
    authorized = "AUTHORIZED"
    executing = "EXECUTING"
    executed = "EXECUTED"
    verified = "VERIFIED"
    failed = "FAILED"
    blocked = "BLOCKED"
    partial = "PARTIAL"
    unknown = "UNKNOWN"

class Service(BaseModel):
    model_config = ConfigDict(extra="allow")
    service_id: str
    display_name: str | None = None
    service_type: str = "api"
    cpu_percent: float = 0
    memory_percent: float = 0
    requests_per_minute: float = 0
    previous_requests_per_minute: float | None = None
    latency_ms: float = 0
    instances: int = 1
    cost_per_hour: float = 0
    min_instances: int = 1
    max_instances: int = 10
    max_latency_ms: float = 1000
    healthy: bool = True
    available: bool = True
    timestamp: str
    stoppable_when_idle: bool = False
    resource_size: str = "standard"

class ActionProposal(BaseModel):
    service_id: str
    action: ActionType
    requested_instances: int | None = None
    requested_size: str | None = None
    reason: str = ""
    evidence: list[str] = Field(default_factory=list)
    requires_fresh_check: bool = False

class SafetyCheck(BaseModel):
    name: str
    passed: bool
    message: str

class SafetyDecision(BaseModel):
    allowed: bool
    reason_code: str | None = None
    checks: list[SafetyCheck] = Field(default_factory=list)

class ActionExecution(BaseModel):
    action_id: str
    service_id: str
    action: ActionType
    requested_instances: int | None = None
    status: LifecycleStatus
    error: str | None = None
    requested_at: str
    completed_at: str | None = None

class VerificationResult(BaseModel):
    action_id: str
    status: LifecycleStatus
    verified: bool
    summary: str
    before: dict[str, Any]
    after: dict[str, Any]
    checks: list[SafetyCheck] = Field(default_factory=list)
    cost_delta_per_hour: float = 0

class AgentRunRequest(BaseModel):
    prompt: str
    scenario_id: str | None = None

class ActionRequest(BaseModel):
    service_id: str
    target_instances: int | None = None
    target_size: str | None = None

class AgentRunResponse(BaseModel):
    run_id: str
    provider: str
    summary: str
    proposal: ActionProposal
    safety: SafetyDecision
    execution: ActionExecution | None = None
    verification: VerificationResult | None = None
    tool_trace: list[dict[str, Any]] = Field(default_factory=list)
