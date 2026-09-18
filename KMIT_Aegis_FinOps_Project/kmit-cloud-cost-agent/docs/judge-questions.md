# Likely Judge Questions

## Why AI?
AI interprets natural-language goals, decides which evidence to inspect, and produces a structured proposal. Deterministic policy code still has final authorization.

## Can the AI bypass the safety engine?
No. Mutations are executed only through backend action services, and the safety engine runs independently.

## What happens with stale data?
The system detects stale/inconsistent timestamps, fetches fresh state, and reassesses before any risky change.

## What happens if the cloud action fails?
The actual API/simulator error is preserved; the system does not claim success and then performs fresh verification.

## Is this connected to a real cloud?
No. The competition build uses a simulated cloud so actions are safe, deterministic, reproducible, and judge-friendly. The provider abstraction can later support real adapters.
