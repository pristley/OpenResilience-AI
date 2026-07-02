# Pattern: API Rate Limiting & Quota Exhaustion

> When rate limits are exceeded, the API rejects legitimate requests causing cascading failures.

## Problem Statement

**Rate limit exhaustion** occurs when API clients exceed configured rate limits, either due to:
- Aggressive retry storms flooding the API
- Load spikes overwhelming configured quotas
- Downstream services making more requests than expected
- DDoS attacks or rogue clients consuming all available quota

**Immediate impact**: Legitimate requests rejected with 429 Too Many Requests → downstream services fail → cascading failures.

**Real-world example**:
- Payment API rate limit: 1000 req/s per customer
- Checkout service retrying 10x per failed request
- During database slowdown: 500 failed requests/s × 10 retries = 5000 req/s
- Rate limit exceeded → all checkout requests rejected → no orders can complete

## Why It Matters

- **Revenue impact**: Requests rejected = customers can't check out
- **Cascade effect**: Blocking legitimate traffic, not just attackers
- **Detection latency**: Often invisible until business metrics drop
- **Blast radius**: Affects all clients sharing same API or quota pool
- **Cost**: Wasted retry traffic; increased load on already-struggling system

---

## How It Fails

### Mechanism

1. Client makes requests normally
2. Downstream service slows down
3. Client retries aggressively (no exponential backoff)
4. Retry rate exceeds API quota
5. API rejects requests with 429 status
6. Client interprets 429 as error, retries harder
7. More rejections → more retries → exponential amplification
8. API becomes unreachable for all clients

### Observable Signals

```yaml
metrics:
  - name: http_429_rate
    spike: Suddenly increases from 0% to 20%+ of traffic
    indicates: Rate limit being hit
  
  - name: rate_limit_remaining
    behavior: Decreases rapidly, hits 0
    example: 1000 → 500 → 100 → 0 (in seconds)
  
  - name: request_rate_per_client
    spike: Specific client making 10-100x normal traffic
    indicates: Retry storm or DDoS
  
  - name: latency_distribution
    pattern: Bimodal - either fast (200 OK) or instant (429)
    indicates: Some requests accepted, many rejected
  
  - name: client_error_rate
    spike: Errors increase when rate limited
    example: 0.1% → 5% in seconds

logs:
  - "429 Too Many Requests"
  - "Rate limit exceeded"
  - "Quota exhausted for customer"
  - "X-RateLimit-Remaining: 0"
  - "Retry-After: 60"

traces:
  - http_status: 429
  - response_header: X-RateLimit-Remaining (0)
  - response_header: Retry-After (seconds to wait)
```

### Time to Detect

- **Best case** (alerting on 429 rate): 10-30 seconds
- **Realistic** (on-call notices spike): 2-5 minutes
- **Worst case** (customer reports orders failing): 5-30 minutes

### Blast Radius

- **Direct**: Affected client gets 429 errors
- **Cascading**: Client retries → more 429s → upstream failures
- **Multiplied**: Each layer of service retries amplifies traffic
- **Scope**: All clients sharing same quota pool affected

---

## Resilience Strategy

### Prevention

1. **Exponential backoff + jitter** (essential)
   - Don't retry immediately on 429
   - Wait 100ms, 200ms, 400ms, ..., max 30s
   - Add random jitter: ±20%
   - Why: Prevents thundering herd
   - Trade-off: Higher latency for retries

2. **Circuit breaker** (essential)
   - If 429 rate > 10%: open circuit
   - Return error immediately instead of queuing
   - Why: Fail fast instead of queuing useless requests
   - Trade-off: Temporary unavailability

3. **Adequate rate limit quota** (important)
   - Set quota based on peak expected load
   - Typically: baseline × 2-3× for spikes
   - Review quarterly or on traffic changes
   - Why: Prevent legitimate traffic from hitting limits
   - Trade-off: Higher infrastructure costs

4. **Per-client rate limits** (important)
   - Set individual client quotas
   - Allocate generously to trusted clients
   - Restrict untrusted/new clients
   - Why: Isolate noisy neighbors
   - Trade-off: More complex quota management

5. **Graceful degradation** (important)
   - Queue requests with backoff instead of failing
   - Return cached responses if available
   - Reduce feature set under rate limit
   - Why: Some requests better than none
   - Trade-off: Stale data or degraded features

### Detection

**Alerting:**

```yaml
alerts:
  - alert: HighRateLimitErrors
    expr: (rate(http_requests_total{status="429"}[1m]) / rate(http_requests_total[1m])) > 0.05
    for: 1m
    annotation: "429 errors > 5% of traffic (rate limit being hit)"
  
  - alert: RateLimitQuotaExhausted
    expr: rate_limit_remaining < 100
    for: 30s
    annotation: "Rate limit quota nearly exhausted"
  
  - alert: ClientRateLimitHammer
    expr: |
      (rate(http_requests_total{client_id=~".*"}[1m]) / 
      avg(rate(http_requests_total[1m])) by (client_id)) > 50
    for: 30s
    annotation: "Single client making 50x normal traffic (possible retry storm)"
  
  - alert: RetryStormDetected
    expr: |
      rate(http_requests_total{status="429"}[30s]) > 1000
      and
      rate(http_requests_total{status="429"}[30s]) > 
      rate(http_requests_total{status="429"}[5m])
    for: 30s
    annotation: "Retry storm: 429 rate accelerating"
```

### Recovery

1. **Immediate**: Enable circuit breaker (stop amplifying traffic)
2. **Short-term**: Increase rate limit quota by 2-3x temporarily
3. **Root cause**: Identify what triggered the spike (failed dependency? retry storm?)
4. **Fix**: Add exponential backoff if missing, adjust timeout, fix downstream service
5. **Monitor**: Watch for recurrence

---

## Chaos Experiment: Rate Limit Exhaustion

```python
# experiments/traditional/api-rate-limiting/rate_limit_test.py
import requests
import time
from concurrent.futures import ThreadPoolExecutor

API_URL = "http://api:8080/api/endpoint"
RATE_LIMIT = 1000  # req/s
RETRY_FACTOR = 10  # simulate 10x retries

def make_request_with_naive_retry():
    """Make request and retry immediately on failure (naive approach)"""
    for attempt in range(5):
        try:
            resp = requests.get(API_URL, timeout=5)
            if resp.status_code == 200:
                return {"status": 200, "attempts": attempt + 1}
            elif resp.status_code == 429:  # Rate limited
                # Naive: retry immediately (no backoff!)
                continue
            else:
                return {"status": resp.status_code, "attempts": attempt + 1}
        except Exception as e:
            continue
    return {"status": None, "error": "all_retries_failed", "attempts": 5}

def make_request_with_exponential_backoff():
    """Make request and retry with exponential backoff (smart approach)"""
    backoff = 0.1  # 100ms initial
    for attempt in range(5):
        try:
            resp = requests.get(API_URL, timeout=5)
            if resp.status_code == 200:
                return {"status": 200, "attempts": attempt + 1}
            elif resp.status_code == 429:  # Rate limited
                # Smart: wait with exponential backoff
                time.sleep(backoff)
                backoff = min(backoff * 2, 10)  # Cap at 10s
                continue
            else:
                return {"status": resp.status_code, "attempts": attempt + 1}
        except Exception as e:
            continue
    return {"status": None, "error": "all_retries_failed", "attempts": 5}

def test_rate_limit_exhaustion():
    print("=" * 70)
    print("Rate Limit Exhaustion Experiment")
    print("=" * 70)
    
    print(f"\n[Phase 1] Naive retry (no backoff)...")
    naive_429s = 0
    with ThreadPoolExecutor(max_workers=100) as executor:
        futures = [executor.submit(make_request_with_naive_retry) for _ in range(100)]
        for future in futures:
            result = future.result()
            if result["status"] == 429:
                naive_429s += 1
    
    print(f"  429 errors: {naive_429s}/100 (naive retry exhausted quota)")
    
    print(f"\n[Phase 2] Smart retry (exponential backoff)...")
    smart_429s = 0
    with ThreadPoolExecutor(max_workers=100) as executor:
        futures = [executor.submit(make_request_with_exponential_backoff) for _ in range(100)]
        for future in futures:
            result = future.result()
            if result["status"] == 429:
                smart_429s += 1
    
    print(f"  429 errors: {smart_429s}/100 (exponential backoff reduced errors)")
    
    assert naive_429s > smart_429s, "Exponential backoff should reduce 429 errors"
    print(f"\n✅ Exponential backoff reduced 429 errors by {100 * (naive_429s - smart_429s) / naive_429s:.0f}%")

if __name__ == "__main__":
    test_rate_limit_exhaustion()
```

---

## Lessons Learned

### Case Study: Black Friday Checkout Crash

**Timeline**: 
- 9am: Traffic increases 5x
- 9:02am: Database slows (queries take 10s instead of 100ms)
- 9:03am: Checkout service retries immediately (no backoff)
- 9:04am: API rate limit exhausted
- 9:04am-9:30am: No orders can complete
- Loss: $500K in revenue

**Root cause**: Naive retry + no exponential backoff + low rate limit quota

**Fix**: 
1. Added exponential backoff
2. Increased rate limit quota 3x
3. Added circuit breaker

**Prevention**: Now quota automatically scales with traffic

### Key Takeaways

- Always use exponential backoff (never retry immediately)
- Circuit breaker stops amplifying traffic
- Rate limit quota should be generous (3x baseline)
- Per-client quotas isolate noisy neighbors
- Monitor 429 rate as leading indicator

---

## Tools & Setup

```bash
# Run experiment
python experiments/traditional/api-rate-limiting/rate_limit_test.py

# Monitor rate limits
prometheus -c observability/prometheus.yml &
grafana-server &
open http://localhost:3000/d/rate-limit-dashboard
```

---

## Related Patterns

- [Retry Storms](../../0-common/retry-storms/) — Exponential backoff prevents storms
- [Resource Exhaustion](../../0-common/resource-exhaustion/) — Rate limits exhaust resources
- [Cascading Failure](../../0-common/cascading-failure/) — Rate limits cascade

---

## See Also

- [Glossary](../../../docs/GLOSSARY.md) — Rate limiting, quota, throttling
- [References](../../../docs/REFERENCES.md) — Rate limiting strategies
