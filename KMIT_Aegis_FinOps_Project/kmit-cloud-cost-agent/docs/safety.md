# Safety

The deterministic safety engine is the final authorization layer. It checks service existence, freshness, health, availability, capacity bounds, trend/headroom risk, idle-stop rules, and latency targets before mutations.

A failed action is never represented as successful. A fresh post-action state is retrieved and verified.
