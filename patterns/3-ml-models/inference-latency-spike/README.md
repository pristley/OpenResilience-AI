# Pattern: Inference Latency Spike & Performance Degradation

> Model inference becomes 5-10x slower unexpectedly; predictions timeout, cascade failures, SLA breaches.

## Quick Summary

**Problem**: Inference latency spikes (50ms → 500ms+); requests timeout and miss SLA  
**Impact**: 30% timeout rate, cascading failures, engagement drop (3% per incident)  
**Detection Time**: Seconds to 1 minute (latency threshold alert)  
**Solution**: Capacity planning, model optimization, batch tuning, horizontal scaling

---

## Problem Statement

ML inference suddenly becomes slower—sometimes much slower:

- **Deployment regression**: New model version slower (60KB vs. 20KB)
- **Resource contention**: Other processes consume GPU/CPU; inference starved
- **Batch size increase**: Larger batches improve throughput but increase latency per request
- **Cold start**: Model not warmed up; first requests hit cold caches
- **Feature computation**: Feature engineering step becomes bottleneck

**Typical progression**:
1. Deployment or traffic surge occurs
2. Latency increases by 5-10x (50ms → 500ms)
3. Requests begin timing out (SLA usually 100-500ms)
4. Downstream services timeout waiting for predictions
5. Cascading failures: Timeout → retry → more load → more timeouts
6. System degradation: 10-30% of traffic affected within minutes

## Why It Matters

- **Immediate Impact**: Users experience slow responses, timeouts
- **Cascade Failures**: Downstream services timeout, cascade up the stack
- **Revenue**: Slow predictions → user abandonment → revenue loss
- **Reputation**: Visible performance degradation damages trust
- **Rapid Detection**: Seconds matter; need automated alerts

## Resilience Strategy

### Detection

1. **Latency Monitoring**:
   ```python
   # Alert on latency thresholds
   p99_latency = np.percentile(latency_samples, 99)
   if p99_latency > sla_ms * 0.8:  # Alert if 80% of SLA
       alert(f"High latency: {p99_latency}ms")
   ```

2. **Error Rate**:
   ```python
   timeout_rate = timeouts / total_requests
   if timeout_rate > 0.01:  # Alert if > 1%
       alert(f"Timeout rate: {timeout_rate:.2%}")
   ```

3. **Resource Monitoring**:
   ```python
   # Alert on resource constraints
   if gpu_utilization > 0.9:
       alert("GPU at capacity; inference may degrade")
   ```

### Recovery

1. **Immediate**:
   - Autoscale: Add more replicas/workers
   - Load shed: Reject lowest-priority requests
   - Fallback: Use cached predictions from previous cycle

2. **Short-term**:
   - Reduce batch size (lower latency)
   - Roll back to previous model if regression
   - Investigate root cause

3. **Long-term**:
   - Optimize model (quantization, pruning)
   - Upgrade hardware (faster GPU, more CPU)
   - Implement serving optimization (caching, batching)

## Key Metrics

### Monitoring

```yaml
InferenceLatency:
  - name: inference_latency_p99
    description: "P99 inference latency in milliseconds"
    threshold: {
      warning: "> 200ms",
      critical: "> 500ms"
    }
  
  - name: timeout_rate
    description: "Percentage of requests timing out"
    threshold: {
      warning: "> 0.01",
      critical: "> 0.05"
    }
  
  - name: inference_throughput
    description: "Predictions per second"
    threshold: {
      warning: "< expected * 0.8",
      critical: "< expected * 0.5"
    }
  
  - name: resource_utilization
    description: "GPU/CPU utilization"
    threshold: {
      warning: "> 0.80",
      critical: "> 0.95"
    }
```

## References

- Li et al. (2019): "DejaVu: Accelerating Deep Learning"
- Ansor MLCommons Benchmarks
- NVIDIA TensorRT Optimization Guide

## See Also

- [Batch Prediction Backlog](../batch-prediction-backlog/)
- [Cold Start Failure](../cold-start-failure/)
- [Model Drift Detection](../model-drift-detection/)
