# Aegis FinOps — Autonomous Cloud Cost Optimization Agent

Aegis FinOps is a competition-ready simulated cloud-operations platform built around the KMIT problem statement **“The Cloud Bill That Wouldn’t Stop Growing.”**

It demonstrates an agentic workflow:

**Natural-language request → tool-based investigation → structured proposal → deterministic safety gate → controlled simulator action → fresh-state verification → audit trail**

## Features

- Agent orchestration with explicit read/action/verification tools
- Deterministic Safety / Policy Engine
- Stale-observation protection
- Simulated cloud with controllable success/failure modes
- Cost-impact calculations
- Post-action verification
- Test A/B/C/D scenario runner
- Adversarial tests
- Premium Cloud Operations Command Center UI
- Agent activity timeline
- Safety Gate visualization
- Service detail page
- Action Center
- Scenario Lab
- Audit log
- Optional Anthropic/OpenAI provider adapters
- Local deterministic mock provider so the full application runs without an API key

## Quick start

```bash
python -m venv .venv
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
# macOS/Linux
# source .venv/bin/activate

pip install -r backend/requirements.txt
uvicorn backend.app.main:app --reload --port 8000
```

Open http://127.0.0.1:8000

API docs: http://127.0.0.1:8000/docs

## Optional real LLM mode

By default the app uses a deterministic local agent provider for demos/tests.

To use an LLM, set one of:

```env
AGENT_PROVIDER=anthropic
ANTHROPIC_API_KEY=...
ANTHROPIC_MODEL=claude-sonnet-5
```

or

```env
AGENT_PROVIDER=openai
OPENAI_API_KEY=...
OPENAI_MODEL=gpt-5.6
```

The action/safety layer is unchanged regardless of provider.

## Scenarios

The Scenario Lab implements the supplied problem statement cases:

- **A — Cost optimization**: reports-worker is an optimization candidate.
- **B — Rising traffic**: orders-api traffic doubles while latency approaches its limit.
- **C — Stale observation**: checkout-api has an old metric snapshot and newer traffic.
- **D — Failed action**: payment-api scale-up returns `capacity_unavailable`.

## Testing

```bash
pytest -q
```

## Safety philosophy

The LLM never writes directly to infrastructure state. The AI proposes; deterministic code authorizes; the simulator executes; fresh state verifies.

## Notes

The project is intentionally local-first. The simulator is not a real cloud control plane and does not require AWS/Azure/GCP credentials.

### Windows one-command start

PowerShell:

```powershell
.\run.ps1
```

Command Prompt:

```bat
run.bat
```
