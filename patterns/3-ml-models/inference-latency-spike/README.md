# Pattern: Inference Latency Spike & Performance Degradation

> Model inference becomes 5-10x slower unexpectedly; predictions timeout and miss SLA.

## Quick Summary

**Problem**: Model inference latency increases suddenly (GPU saturation, resource contention, deployment)  
**Impact**: Predictions timeout; user-facing features break; cascading timeouts  
**Detection Time**: Seconds to minutes (if alert on latency threshold)  
**Solution**: Capacity planning, model optimization, batch size tuning, horizontal scaling

---

**Detailed Pattern**: See [CONTRIBUTING.md](../../../CONTRIBUTING.md) for full documentation including detection thresholds, recovery strategies, chaos experiments, and performance optimization techniques.
