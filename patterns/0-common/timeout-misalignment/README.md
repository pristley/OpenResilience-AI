# Pattern: Timeout Misalignment

> When timeouts don't match across service boundaries, resources hang indefinitely, cascading failures compound.

## Problem Statement

**Timeout misalignment** occurs when a caller's timeout doesn't match the callee's timeout or internal processing time. This causes:
- Caller waits too long → resources exhaust
- Caller gives up before callee finishes → duplicate requests
- Callee takes longer than caller expects → cascading timeouts

**Immediate impact**: Resources wait indefinitely → exhausted → cascading failures.

**Real-world example**:
- API timeout: 30s
- Backend timeout: 5s
- Database query: 10s (sometimes)
- Result: API calls backend, backend times out and retries (wastes resources), API still waiting for 30s total, threads pile up

## Why It Matters

- **Resource exhaustion**: Waiting for timeout consumes threads/connections
- **Cascading timeouts**: Each layer adds its own timeout delay
- **Unpredictable behavior**: Hard to debug; timeouts seem random
- **Total latency**: Sum of all timeouts (API 30s + backend 5s + DB 10s = 45s observable latency)
- **Amplification**: Misalignment can triple or quadruple failure latency

---

## How It Fails

### Failure Modes

1. **Caller timeout > callee timeout**
   - API times out requests after 30s
   - Backend times out requests after 5s
   - Slow query takes 10s
   - Backend times out → returns error
   - API still waiting for 25 more seconds
   - Threads on API exhausted while waiting

2. **Callee timeout > caller timeout**
   - API times out after 5s
   - Backend times out after 30s
   - Slow query takes 10s
   - API times out → tries to cancel request
   - Backend is still processing → can't cancel in-flight query
   - Database keeps running (wasted resources)
   - API makes retry request → more work on already-slow backend

3. **Cascading timeouts**
   - A timeout: 10s
   - B timeout: 10s
   - C timeout: 10s
   - A → B → C call chain
   - If C takes 5s, each layer adds 10s of waiting
   - Total: 30s before error surfaces

4. **No timeout configured**
   - Service calls another service with infinite timeout
   - If called service hangs: caller hangs indefinitely
   - Threads exhausted → service down
   - Cascade up the call chain

5. **Timeout != total latency threshold**
   - User experience timeout: 2s (user perception)
   - API timeout: 10s (internal)
   - Backend timeout: 30s (external API)
   - User sees 10s+ latency → gives up and retries
   - Retry creates more load

### Observable Signals

**Metrics:**
```yaml
metrics:
  - name: latency_p99
    pattern: |
      Spikes to timeout value (30s, 60s, etc.)
      Then returns error
    indicates: Request hit timeout
  
  - name: error_rate
    pattern: Spikes with "timeout" errors
    indicates: Timeouts occurring
  
  - name: timeout_error_rate
    spike: Increases during slow operations
    example: 0% → 50% timeout errors
  
  - name: thread_pool_usage
    behavior: Climbs as threads wait for timeout
    example: 20% → 100% as timeouts accumulate
  
  - name: active_connections
    behavior: Climbs (connections waiting for timeout)
  
  - name: latency_distribution
    pattern: Bimodal - fast responses OR timeout (no middle)
    example: 100ms OR 30000ms (timeout)

logs:
  - "Request timed out after 30000ms"
  - "Timeout waiting for response from backend"
  - "Deadline exceeded"
  - "Request canceled due to timeout"
  - "Context deadline exceeded"

traces:
  - span_duration: Exactly at timeout value (30s, 60s, etc.)
  - span_error: "deadline exceeded" or "timeout"
  - trace_structure: Sees timeout error at top level
```

### Time to Detect

- **Best case** (alerting on timeout rate): 1-2 minutes
- **Realistic** (on-call sees latency spike): 5-15 minutes
- **Worst case** (cascading failures make debugging hard): 30+ minutes

### Blast Radius

- **Direct**: Requests to service with misaligned timeout
- **Cascading**: Upstream services timeout waiting
- **Multiplicative**: Each layer adds timeout delay
- **Scope**: Affects all requests through affected path

---

## Resilience Strategy

### Prevention

How to avoid timeout misalignment:

1. **Document timeout strategy** (essential)
   - Document every service's timeout: read, write, total
   - Document call chain timeouts
   - Example: A(10s) → B(5s) → C(2s)
   - Why: Visibility prevents misalignment
   - Trade-off: Requires coordination

2. **Principle: caller timeout > callee timeout** (essential)
   - If B times out after 5s, A should timeout after 7-10s
   - Why: A can gracefully handle B's timeout
   - Trade-off: A's timeout needs buffer

3. **Propagate deadline / timeout context** (important)
   - Pass deadline through call chain
   - Callee knows how much time it has left
   - Example: A has 10s left → tells B "you have 8s"
   - Why: Callee can make informed decisions
   - Trade-off: Requires context propagation library

4. **Default timeouts** (important)
   - Never leave timeouts as "infinite"
   - Default: 5-30s depending on SLA
   - Why: Prevents indefinite hanging
   - Trade-off: May timeout legitimate slow operations

5. **Timeout per operation type** (important)
   - Read timeout: 5s
   - Write timeout: 10s
   - External API timeout: 30s
   - Why: Different operations have different latency profiles
   - Trade-off: More configuration complexity

6. **Circuit breaker for slow services** (important)
   - If service consistently times out, open circuit
   - Fail fast instead of waiting for timeout
   - Why: Reduces total latency impact
   - Trade-off: Temporarily unavailable service

### Detection

Real-time monitoring to catch misalignment:

**Alerting:**

```yaml
alerts:
  - alert: TimeoutErrors
    expr: rate(http_request_duration_seconds_bucket{le="+Inf"}[1m]) > 0.1
    for: 2m
    annotation: "Timeout errors occurring (>10% timeout rate)"
  
  - alert: LatencySpikesToTimeout
    expr: |
      histogram_quantile(0.99, http_request_duration_seconds)
      > 25000
    for: 1m
    annotation: "p99 latency near 30s timeout (possible misalignment)"
  
  - alert: ThreadPoolBacklog
    expr: http_request_queue_depth > 100
    for: 1m
    annotation: "Request queue building up (possible timeouts causing backlog)"
```

### Recovery

How to handle timeout misalignment when it occurs:

1. **Identify the misalignment**: Check timeout values at each layer
2. **Prioritize**: Is it caller > callee (fixable) or callee > caller (hard to fix)?
3. **Adjust timeouts**: Rebalance so caller > callee + buffer
4. **Add circuit breaker**: Prevent waiting for full timeout
5. **Propagate deadline**: Pass deadline through call chain

---

## Chaos Experiment: Timeout Misalignment

Test timeout behavior across service boundaries.

```python
# experiments/0-common/timeout-misalignment/timeout_test.py
import requests
import time

API_TIMEOUT = 30  # seconds
BACKEND_TIMEOUT = 5  # seconds
BACKEND_URL = "http://backend:8080/api/slow"
SLOW_OPERATION_TIME = 10  # seconds

def test_timeout_misalignment():
    print("=" * 70)
    print("Timeout Misalignment Experiment")
    print("=" * 70)
    
    print(f"\n[Phase 1] Configuration:")
    print(f"  API timeout: {API_TIMEOUT}s")
    print(f"  Backend timeout: {BACKEND_TIMEOUT}s")
    print(f"  Slow operation: {SLOW_OPERATION_TIME}s")
    
    if API_TIMEOUT <= BACKEND_TIMEOUT:
        print(f"  ⚠️  MISALIGNED: API timeout ({API_TIMEOUT}s) <= Backend timeout ({BACKEND_TIMEOUT}s)")
    else:
        print(f"  ✅ Aligned: API timeout ({API_TIMEOUT}s) > Backend timeout ({BACKEND_TIMEOUT}s)")
    
    print(f"\n[Phase 2] Calling slow operation ({SLOW_OPERATION_TIME}s)...")
    start = time.time()
    
    try:
        resp = requests.get(BACKEND_URL, timeout=API_TIMEOUT)
        elapsed = time.time() - start
        print(f"  Response: {resp.status_code} (after {elapsed:.1f}s)")
    except requests.exceptions.Timeout:
        elapsed = time.time() - start
        print(f"  ❌ Timeout after {elapsed:.1f}s")
        
        if elapsed >= API_TIMEOUT * 0.9:
            print(f"  This is the API timeout (misalignment!)")
        elif elapsed >= BACKEND_TIMEOUT * 0.9:
            print(f"  This is the backend timeout (expected)")
        else:
            print(f"  Unexpected timeout")
    
    print(f"\n[Phase 3] Check thread pool impact...")
    # Verify threads released after timeout (not stuck)
    print("  ✅ Threads should be released after timeout")

if __name__ == "__main__":
    test_timeout_misalignment()
```

---

## Lessons Learned

### Real Incident: Timeout Cascade

**Timeline**: Slow query (10s) → backend timeout 5s → API timeout 30s → threads wait 30s → exhaustion → cascade

**Root cause**: Caller timeout >> callee timeout (30s vs 5s)

**Fix**: Align timeouts (API 10s > backend 5s + buffer)

**Result**: Errors surfaced after 5s instead of 30s

### Key Takeaways

- Caller timeout should be > callee timeout + buffer
- Document timeout strategy for each service
- Propagate deadline through call chains
- Use circuit breaker for consistently slow services
- Default to short timeouts (5-10s)

---

## Related Patterns

- [Cascading Failure](../cascading-failure/) — Timeouts cause cascades
- [Resource Exhaustion](../resource-exhaustion/) — Long timeouts exhaust resources
- [Retry Storms](../retry-storms/) — Long timeouts + retries = exponential load

---

## See Also

- [Glossary](../../../docs/GLOSSARY.md) — Timeout, deadline, circuit breaker
- [Theory](../../../docs/THEORY.md) — Resilience patterns
- [References](../../../docs/REFERENCES.md) — Timeout strategies
