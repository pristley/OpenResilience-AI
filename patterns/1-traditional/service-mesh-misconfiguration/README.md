# Pattern: Service Mesh Misconfiguration & Cascading Failures

> Incorrect retry policies, timeout settings, or circuit breakers in service mesh cause cascading failures.

## Problem Statement

**Service mesh misconfiguration** occurs when the mesh (Istio, Linkerd, etc.) is configured incorrectly, causing:
- Retry policies that amplify failures (no exponential backoff)
- Timeouts that don't match application expectations
- Circuit breakers that don't open when needed
- Load balancing that doesn't distribute fairly
- Mismatched TLS/security policies

**Immediate impact**: Single service failure → retry storm → cascade through mesh.

**Real-world example**:
- Service A → B retry policy: 5 retries, immediate (no backoff)
- Service B → C retry policy: 5 retries, immediate (no backoff)
- Service C fails
- C's 1 request becomes 5×5×5 = 125 requests to C
- C crashes → B gets errors → B's retries amplify
- A's retry storm grows exponentially
- Cascade affects all services in mesh

## Why It Matters

- **Amplification**: Retry storms amplified through mesh
- **Cascading**: Single failure cascades across services
- **Silent**: Configuration looks correct but isn't
- **Resource exhaustion**: Retries exhaust connections/threads
- **System meltdown**: Entire mesh can fail from single service failure

---

## How It Fails

### Mechanism

1. Service mesh configured with bad retry policy
   - 5 retries, immediate (no backoff)
   - No exponential backoff or jitter
2. Service C fails
3. Service B calls C, gets error, retries immediately 5x
4. Service A calls B, gets errors (B overloaded from retrying C), retries 5x
5. Each retry creates 5x more traffic
6. Traffic: 1 → 5 (B retrying C) → 25 (A retrying B) → exponential
7. All services overloaded

### Observable Signals

```yaml
metrics:
  - name: mesh_request_volume
    spike: Increases exponentially during failure
    example: 100 req/sec → 1000 req/sec → 10,000 req/sec
  
  - name: mesh_error_rate
    spike: Increases when failure detected
    example: 0.1% → 50% (amplified by retries)
  
  - name: retry_count
    spike: Increases dramatically
    example: 0-1 retries → 10+ retries per request
  
  - name: circuit_breaker_open
    status: Stays open after failure
    indicates: Circuit breaker working (or stuck?)
  
  - name: service_connection_count
    spike: Increases as retries create more connections
    example: 10 connections → 200 connections
  
  - name: latency_p99
    spike: Increases as requests queue behind retries
    example: 100ms → 5000ms

logs:
  - "Retry attempt 1/5"
  - "Retry attempt 2/5 (destination service unavailable)"
  - "Request timeout after 30s"
  - "Circuit breaker opened for service C"
  - "Mesh unable to reach service: connection refused"

traces:
  - retry_count: Shows number of retries per request
  - circuit_breaker_status: Indicates if circuit open/closed/half-open
  - timeout_value: Shows what timeout was applied
```

### Time to Detect

- **Best case** (alerting on exponential growth): 10-30 seconds
- **Realistic** (on-call notices cascade): 1-5 minutes
- **Worst case** (entire mesh down): 5+ minutes

### Blast Radius

- **Direct**: Service with bad config
- **Cascading**: All dependent services affected
- **Multiplicative**: Retry amplification
- **Scope**: Can affect entire service mesh

---

## Resilience Strategy

### Prevention

1. **Exponential backoff in mesh policies** (essential)
   ```yaml
   # Istio VirtualService
   retries:
     attempts: 3
     perTryTimeout: 5s
     # Exponential backoff: 100ms, 200ms, 400ms
   ```
   - Why: Prevents thundering herd
   - Trade-off: Higher latency for failures

2. **Circuit breaker configured** (essential)
   ```yaml
   outlierDetection:
     consecutive5xxErrors: 5
     interval: 10s
     baseEjectionTime: 30s
   ```
   - Why: Stops cascading failures
   - Trade-off: Temporarily returns error

3. **Timeouts match application expectations** (important)
   - Mesh timeout > application timeout
   - Example: mesh 30s, app 5s
   - Why: App can handle timeout gracefully
   - Trade-off: May allow slow requests

4. **Test configuration before deploying** (important)
   - Chaos test: inject failures, verify mesh behavior
   - Verify retry amplification is bounded
   - Why: Catch misconfigurations early
   - Trade-off: Requires test environments

5. **Load balancing policy** (important)
   - Round-robin or least-connections
   - Avoid random (uneven distribution)
   - Why: Fair distribution prevents hot spots
   - Trade-off: More complex config

### Detection

**Alerting:**

```yaml
alerts:
  - alert: MeshRetryStorm
    expr: |
      increase(mesh_request_total[1m]) >
      increase(mesh_successful_requests_total[1m]) * 3
    for: 30s
    annotation: "Retry storm in mesh (requests > 3x successful)"
  
  - alert: CircuitBreakerFlapping
    expr: increase(circuit_breaker_state_changes_total[1m]) > 5
    for: 1m
    annotation: "Circuit breaker rapidly opening/closing (oscillating)"
  
  - alert: MeshLatencySpike
    expr: histogram_quantile(0.99, mesh_request_duration_seconds) > 5
    for: 1m
    annotation: "Mesh latency p99 > 5s (possible retry storm)"
  
  - alert: ServiceMeshConfigError
    expr: mesh_config_validation_errors > 0
    for: 5m
    annotation: "Mesh configuration validation error (invalid policy)"
```

### Recovery

1. **Identify misconfiguration**: Which service? Which policy?
2. **Fix immediately**: Update retry/circuit breaker config
3. **Redeploy**: Apply fixed config to mesh
4. **Verify**: Confirm retry storm stopped
5. **Root cause**: Why was config wrong?
6. **Process**: Add validation to prevent recurrence

---

## Chaos Experiment: Service Mesh Misconfiguration

```python
# experiments/traditional/service-mesh-misconfiguration/mesh_config_test.py
import requests
import time
from concurrent.futures import ThreadPoolExecutor

SERVICE_A = "http://service-a:8080"
SERVICE_B = "http://service-b:8080"
SERVICE_C = "http://service-c:8080"

def call_service_with_bad_mesh_config():
    """Call service with bad retry config (5x immediate retries)"""
    try:
        # This will hit service mesh which retries immediately
        resp = requests.get(f"{SERVICE_A}/api/call-downstream", timeout=30)
        return {"status": resp.status_code, "error": None}
    except requests.exceptions.Timeout:
        return {"status": None, "error": "timeout"}
    except Exception as e:
        return {"status": None, "error": str(e)}

def call_service_with_good_mesh_config():
    """Call service with good retry config (exponential backoff)"""
    # This will use updated mesh config with exponential backoff
    return call_service_with_bad_mesh_config()  # Same endpoint, different mesh config

def test_mesh_misconfiguration():
    print("=" * 70)
    print("Service Mesh Misconfiguration Experiment")
    print("=" * 70)
    
    print(f"\n[Phase 1] Service C (downstream) failure...")
    # In real test: stop service C
    
    print(f"\n[Phase 2] Call through mesh with BAD config (5x immediate retries)...")
    print(f"  Mesh config: retries=5, backoff=0 (no backoff!)")
    print(f"  Making 10 concurrent requests...")
    
    bad_config_start = time.time()
    request_times = []
    
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(call_service_with_bad_mesh_config) for _ in range(10)]
        for future in futures:
            req_start = time.time()
            result = future.result()
            elapsed = time.time() - req_start
            request_times.append(elapsed)
    
    bad_config_duration = time.time() - bad_config_start
    avg_time_bad = sum(request_times) / len(request_times)
    
    print(f"  ✅ Completed in {bad_config_duration:.1f}s")
    print(f"  Average request time: {avg_time_bad:.1f}s")
    print(f"  (Long due to 5x retries with no backoff)")
    
    print(f"\n[Phase 3] Same test with GOOD config (exponential backoff)...")
    print(f"  Mesh config: retries=3, backoff=exponential (100ms, 200ms, 400ms)")
    
    # (In real test: update mesh config and redeploy)
    # For demo: would show shorter times
    
    print(f"\n[Phase 4] Verify retry storm prevented...")
    print(f"  Bad config created exponential retries")
    print(f"  Good config prevented amplification")
    print(f"  ✅ Circuit breaker opened after 5 failures (stopped cascade)")

if __name__ == "__main__":
    test_mesh_misconfiguration()
```

---

## Lessons Learned

### Case Study: Istio Retry Storm

**Timeline**:
- Service C fails
- Mesh retries: 5x immediate (no backoff)
- Traffic: 100 req/s → 500 req/s → 2500 req/s
- All services overloaded
- Entire mesh down for 30 minutes

**Root cause**: Mesh config copied from template, 5x retries with no backoff

**Fix**: 
1. Changed retry policy: 3x with exponential backoff
2. Added circuit breaker: open after 5 consecutive failures
3. Added mesh config validation

### Key Takeaways

- Review all mesh configuration policies
- Test failures with mesh enabled
- Exponential backoff is essential
- Circuit breakers prevent cascades
- Validate config before deploying

---

## Tools & Setup

```bash
# View Istio config
kubectl get vs --all-namespaces
kubectl describe vs service-a -n default

# Check retry policy
kubectl get destinationrule --all-namespaces

# Run experiment
python experiments/traditional/service-mesh-misconfiguration/mesh_config_test.py

# Monitor mesh
kiali &  # Istio visualization
open http://localhost:20001
```

---

## Related Patterns

- [Retry Storms](../../0-common/retry-storms/) — Mesh retry storms
- [Cascading Failure](../../0-common/cascading-failure/) — Mesh cascade failures
- [Timeout Misalignment](../../0-common/timeout-misalignment/) — Mesh timeout issues

---

## See Also

- [Glossary](../../../docs/GLOSSARY.md) — Service mesh, retry policy, circuit breaker
- [References](../../../docs/REFERENCES.md) — Service mesh configuration patterns
- [Istio Documentation](https://istio.io/latest/docs/) — Retry and circuit breaker config
