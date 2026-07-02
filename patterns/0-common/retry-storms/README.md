# Pattern: Retry Storms

> When retry logic has no exponential backoff or circuit breaker, failures are amplified exponentially, overwhelming the system.

## Problem Statement

**Retry storms** occur when multiple services or components implement naive retry logic without exponential backoff, rate limiting, or circuit breakers. A single failure triggers retries, which trigger more retries, which trigger even more retries—creating an exponential explosion of requests that overwhelms both the failed service and the retry-ing systems.

**Immediate impact**: Single failed request → 10 retries → 100 total requests → 1000 total requests across all services → system meltdown.

**Real-world example**:
- API service fails (database down)
- Payment service calls API, gets error, immediately retries (5 times)
- Checkout service calls Payment, gets errors, retries (5 times each)
- Orders service calls Checkout, gets errors, retries (5 times each)
- Total: 1 failed request becomes 5 × 5 × 5 = 125 requests to API in seconds
- API still down → all 125 fail → each retries → 625 requests → ...exponential explosion

## Why It Matters

- **Amplification factor**: Single failure → exponential load increase
- **Blast radius**: Affects all layers of system (downstream and upstream)
- **Detection latency**: Often invisible until traffic spike observed
- **Resource exhaustion**: Retries consume threads, memory, connections
- **Cost**: What was 1 failed service becomes cascading failure across all services

---

## How It Fails

### Failure Modes

1. **Naive retry without backoff**
   - Service A calls B
   - B returns error (500)
   - A immediately retries (no delay)
   - B still failing → A retries again (no delay)
   - Result: A hammers B with requests immediately

2. **Retry at each layer**
   - A → B (retries 3x)
   - B → C (retries 3x)
   - C → D (retries 3x)
   - Single A request becomes 3 × 3 × 3 = 27 requests to D
   - If D fails: 27 requests fail, each retries 3x → 81 requests → ...

3. **Thundering herd after downtime**
   - Service B is down for 5 minutes
   - 1000 requests accumulate in retry queues (all expecting failure)
   - B comes back up
   - All 1000 requests fire immediately (thundering herd)
   - B gets hammered by retry traffic → goes down again

4. **Retry amplification from timeouts**
   - Service A calls B with 30s timeout (no timeout configured)
   - Request waits 30s → timeout → A retries
   - Retry waits 30s → timeout → A retries
   - After 5 retries: 150 seconds of waiting on single request
   - Threads accumulate → resource exhaustion

5. **No maximum retry attempts**
   - Code: `while (true) { try { call(); break; } catch { } }`
   - If permanent failure: infinite retry loop
   - Eventually resource exhaustion

### Observable Signals

**Metrics:**
```yaml
metrics:
  - name: request_rate
    pattern: Exponential increase during failures
    example: 100 req/s → 1000 req/s (10x spike) during retry storm
  
  - name: error_rate
    pattern: Stays high during storm (all retries failing too)
    example: 50% errors × 5 retries = 500% of baseline traffic
  
  - name: retry_count
    spike: Increases dramatically
    example: Normal 0-10 retries → 1000s during failure
  
  - name: latency_p99
    behavior: Increases due to queue backing up
    example: 100ms → 5000ms (queued behind retries)
  
  - name: thread_pool_usage
    spike: Climbs to 100% (threads waiting for retries)
    indicates: Resources being consumed by retry storms
  
  - name: active_connections
    spike: Increases (connection pools exhausted by retries)

logs:
  - "Retry attempt 1/5"
  - "Retry attempt 2/5"
  - "Request failed, retrying..."
  - "Thread pool full"
  - "Connection pool exhausted"
  - "Timeout waiting for response"

traces:
  - trace_depth: Deeply nested (many retries)
  - trace_duration: Long (each retry adds latency)
  - span_count: Hundreds of spans from single user request
```

### Time to Detect

- **Best case** (alerting on error rate spike): 10-30 seconds
- **Realistic** (on-call notices high traffic): 1-5 minutes
- **Worst case** (system crashes): 5-30 minutes

### Blast Radius

- **Direct**: Service being called (hammered by retries)
- **Cascading**: All services in the call chain affected
- **Multiplicative**: Each layer multiplies the traffic
- **Scope**: Exponential growth means entire system affected quickly

---

## Resilience Strategy

### Prevention

How to avoid retry storms:

1. **Exponential backoff** (essential)
   - Retry 1: Wait 100ms
   - Retry 2: Wait 200ms
   - Retry 3: Wait 400ms
   - Retry 4: Wait 800ms
   - Retry 5: Give up
   - Why: Spacing prevents thundering herd
   - Trade-off: Higher latency for retries

2. **Jitter** (essential)
   - Add random delay: wait (backoff ± random(0, backoff/2))
   - Why: Prevents synchronized retries from multiple sources
   - Example: All services don't retry at same time
   - Trade-off: Harder to test deterministically

3. **Circuit breaker** (essential)
   - After 5 consecutive failures, open circuit
   - Stop retrying (fail fast instead)
   - Half-open after 30s to test recovery
   - Why: Prevents retries to permanently broken service
   - Trade-off: Temporarily returns error

4. **Maximum retry attempts** (important)
   - Max 3-5 retries (not infinite)
   - Why: Limits amplification factor
   - Trade-off: May fail on transient errors

5. **Timeout on retry attempts** (important)
   - Set timeout on individual retry attempt (e.g., 5s)
   - Set total timeout for all retries (e.g., 15s)
   - Why: Prevents hanging indefinitely
   - Trade-off: May timeout legitimate slow requests

6. **Bulkheads** (important)
   - Use separate thread pool per dependency
   - Limit retries to per-pool threads
   - Why: One service's retry storm doesn't exhaust all resources
   - Trade-off: More complex resource management

### Detection

Real-time monitoring to catch retry storms:

**Alerting:**

```yaml
alerts:
  - alert: RetryStorm
    expr: |
      increase(http_requests_total[1m]) > 1000
      and
      increase(http_requests_total{retry="true"}[1m]) > 500
    for: 1m
    annotation: "Retry storm detected (50%+ of traffic is retries)"
  
  - alert: HighErrorRateCorrelatedWithHighTraffic
    expr: |
      (rate(http_requests_total{status=~"5.."}[1m]) > 0.5)
      and
      (rate(http_requests_total[1m]) > 2000)
    for: 1m
    annotation: "High error rate with high traffic (possible retry storm)"
  
  - alert: ExponentialRequestGrowth
    expr: rate(http_requests_total[1m]) / rate(http_requests_total[5m]) > 5
    for: 30s
    annotation: "Request rate increasing exponentially (retry storm?)"
```

### Recovery

How to handle retry storms when they occur:

1. **Identify the root cause**: Which service initially failed?
2. **Stop the retries**: Enable circuit breaker or drain retry queues
3. **Fix the root cause**: Restart the service, fix the bug
4. **Let retries drain**: Wait for retry queues to empty
5. **Verify recovery**: Check error rates and traffic return to baseline

---

## Chaos Experiment: Retry Storm Injection

Test your system's retry logic and exponential backoff.

```python
# experiments/0-common/retry-storms/retry_storm_test.py
import requests
import time
from datetime import datetime

SERVICE_URL = "http://api:8080/api/call-downstream"
BROKEN_SERVICE_URL = "http://broken:8080"

def simulate_downstream_failure():
    """
    Make downstream service unreachable
    This will trigger retries in the calling service
    """
    # Simulate by disabling the service (in real scenario)
    # For this test, assume broken:8080 is unreachable
    pass

def verify_retry_storm_mitigated():
    """
    Verify that retries use exponential backoff + circuit breaker
    """
    print("=" * 70)
    print("Retry Storm Experiment")
    print("=" * 70)
    
    print("\n[Phase 1] Simulating downstream service failure...")
    # In real scenario, stop the downstream service
    # simulate_downstream_failure()
    
    print("\n[Phase 2] Making request that will trigger retries...")
    start = time.time()
    
    try:
        resp = requests.get(SERVICE_URL, timeout=30)
    except requests.exceptions.Timeout:
        total_time = time.time() - start
        print(f"  ✅ Request failed after {total_time:.1f}s (indicates retries with backoff)")
        
        # If no backoff: would fail immediately (< 1s)
        # If exponential backoff: 100ms + 200ms + 400ms + 800ms = 1.5s
        assert total_time > 1.0, "Request failed too fast (might be no retry?"
        assert total_time < 30, "Request took too long (might be no backoff?)"
        
        print("✅ Exponential backoff verified")
    
    print("\n[Phase 3] Verify circuit breaker opened...")
    # Make rapid requests and verify they fail immediately (circuit open)
    latencies = []
    for i in range(5):
        req_start = time.time()
        try:
            requests.get(SERVICE_URL, timeout=1)
        except Exception as e:
            latency = time.time() - req_start
            latencies.append(latency)
    
    # Circuit breaker should cause subsequent requests to fail immediately
    avg_latency = sum(latencies) / len(latencies)
    print(f"  Average latency across 5 requests: {avg_latency*1000:.0f}ms")
    assert avg_latency < 0.5, "Circuit breaker might not be open (requests taking too long)"
    print("✅ Circuit breaker mitigated retry storm")
    
    print("\n" + "=" * 70)
    print("✅ EXPERIMENT PASSED: Retry storm mitigated")
    print("=" * 70)

if __name__ == "__main__":
    verify_retry_storm_mitigated()
```

---

## Lessons Learned

### Real Incident: Database Connection Pool Exhaustion

**Timeline**: DB goes down → retries start → connection pools exhausted → entire system cascades

**Root cause**: No exponential backoff, each retry immediate

**Impact**: 100 users × 5 retries per second × 10 seconds = 5000+ failed requests

**Fix**: Add exponential backoff (100ms, 200ms, 400ms, ...) + circuit breaker

### Key Takeaways

- Exponential backoff is essential (prevents thundering herd)
- Circuit breaker stops retries to broken services
- Jitter prevents synchronized retries
- Max retry attempts limit amplification
- Each layer should have independent retry logic

---

## Related Patterns

- [Cascading Failure](../cascading-failure/) — Retries cascade failures
- [Resource Exhaustion](../resource-exhaustion/) — Retries exhaust resources
- [Timeout Misalignment](../timeout-misalignment/) — Long timeouts + retries = slow recovery

---

## See Also

- [Glossary](../../../docs/GLOSSARY.md) — Exponential backoff, circuit breaker, jitter
- [Theory](../../../docs/THEORY.md) — Resilience patterns
- [References](../../../docs/REFERENCES.md) — Retry strategies and references
