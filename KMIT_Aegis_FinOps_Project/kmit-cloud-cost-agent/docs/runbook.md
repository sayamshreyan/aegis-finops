# Demo Runbook

## Start

Windows PowerShell:

```powershell
.\run.ps1
```

Then open:

- http://127.0.0.1:8000
- http://127.0.0.1:8000/docs

## Best judge sequence

1. Overview → explain the anomaly and service portfolio.
2. Scenario Lab → Test A.
3. Return to Overview → show AI tool trace, Safety Gate, verification and cost delta.
4. Scenario Lab → Test C.
5. Highlight stale observation handling.
6. Scenario Lab → Test D.
7. Highlight `capacity_unavailable` and failed verification.
8. Open Audit Log.

## Real LLM mode

Set `AGENT_PROVIDER` and provider API key in `.env`.

The simulator and safety engine remain local and deterministic.
