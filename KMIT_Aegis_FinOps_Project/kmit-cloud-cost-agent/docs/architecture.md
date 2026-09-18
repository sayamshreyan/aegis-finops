# Architecture

User → Agent Orchestrator → Tool Registry → Simulator observations → Structured proposal → Safety Engine → Action Executor → Fresh State → Verification → Audit/UI.

The AI provider is replaceable. `MockAgent` is the deterministic local demo provider; `AnthropicAgent` provides real tool-calling when an API key is configured.
