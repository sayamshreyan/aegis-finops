# Requirements Traceability

| Source requirement | Implementation | Test | UI |
|---|---|---|---|
| Natural-language request | `backend/app/agent_orchestrator.py` | scenario tests | AI Agent Console |
| Inspect metrics/traffic/events through tools | `backend/app/tools.py` | scenario tests | Agent Activity |
| Choose actions/no action | `backend/app/agent.py` | A/B/C/D | Proposal panel |
| Deterministic safety | `backend/app/safety.py` | safety tests | Safety Gate |
| Stale observations | simulator fresh state + safety | Test C | Stale → refresh → reassess |
| Failed actions | simulator failure map + audit | Test D | Failed execution panel |
| Post-action verification | `backend/app/verification.py` | scenario tests | Verification Center |
| Final explanation/audit | DB audit + frontend | integration smoke tests | Audit Log |
