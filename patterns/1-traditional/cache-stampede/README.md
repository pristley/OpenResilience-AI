# Pattern: Cache Stampede & Thundering Herd

> When a cache key expires, thousands of requests simultaneously hit the database.

## Problem Statement

**Cache stampede** (thundering herd) occurs when a frequently-accessed cache key expires or is invalidated. All pending requests that were waiting for that key simultaneously attempt to recompute or fetch from the database, overwhelming it.

**Immediate impact**: Cache miss → 1000s concurrent requests hit database → database slows → timeouts → cascading failures.

**Real-world example**:
- Homepage data cached with 1-hour TTL
- 10,000 requests/minute hitting cache
- Cache expires → all 10,000 requests hit database simultaneously
- Database overloaded → queries take 30s instead of 100ms
- Requests timeout → users see errors
- Timeouts trigger retries → more database load

## Why It Matters

- **Amplification**: 1 cache miss → 10,000x load spike
- **Predictable**: Always happens at predictable intervals (TTL expiration)
- **Invisible**: No obvious cause; looks like database failure
- **Resource exhaustion**: Database connections/threads exhausted
- **Cascading**: Database slowdown cascades to all dependent services

---

## How It Fails

### Mechanism

1. Cache key has 1-hour TTL
2. 10,000 requests/min cached
3. Hour passes → key expires
4. All 10,000 requests waiting for key simultaneously try to recompute
5. All 10,000 hit database concurrently
6. Database connection pool exhausted (max 50 connections)
7. Requests timeout → errors
8. Retries amplify load → more timeouts

### Observable Signals

```yaml
metrics:
  - name: cache_miss_rate
    spike: Suddenly increases from 0% to 100% at regular intervals
    example: 5% baseline → 100% at every hour mark
  
  - name: database_query_rate
    spike: 10x increase at cache expiration time
    example: 100 queries/sec → 1000 queries/sec
  
  - name: database_query_latency
    spike: 100ms → 5000ms during cache stampede
    indicates: Database overloaded
  
  - name: connection_pool_active
    spike: Climbs to max during stampede
    example: 10 connections → 50 (max) in seconds
  
  - name: timeout_rate
    spike: Increases during stampede
    example: 0% → 20% at cache expiration
  
  - name: queue_depth
    spike: Requests queue up waiting for connections
    example: 0 → 1000+ queued requests

logs:
  - "Connection pool full"
  - "Query timeout after 30000ms"
  - "Unable to acquire connection from pool"
  - "Cache miss (rebuilding from source)"
  - "Too many concurrent queries"

traces:
  - latency_spike: Exactly at cache TTL expiration
  - concurrent_requests: 1000s hitting database simultaneously
  - lock_contention: "SELECT ... FOR UPDATE" locks held
```

### Time to Detect

- **Best case** (alerting on 100% cache miss): 10-30 seconds
- **Realistic** (noticing query latency spike): 1-5 minutes
- **Worst case** (customer complaint): 5-30 minutes

### Blast Radius

- **Direct**: Database overloaded
- **Cascading**: All services depending on database affected
- **Multiplicative**: Each service's retry amplifies load
- **Scope**: Entire application affected

---

## Resilience Strategy

### Prevention

1. **Cache warming / proactive refresh** (essential)
   - Before key expires (at 50 min): start refresh in background
   - New value ready before old key expires
   - Why: No cache miss at all
   - Trade-off: Requires predictable access patterns

2. **Probabilistic early expiration (XFetch)** (essential)
   - Instead of hard TTL: expire key early with probability
   - Example: After 50 min, 10% of requests refresh key
   - Spreads load, no sudden spike
   - Why: Smooth load instead of thundering herd
   - Trade-off: More cache misses overall

3. **Locking mechanism** (important)
   - When cache misses: first request locks & computes value
   - Other requests wait for lock (not recompute)
   - Why: Only 1 expensive computation
   - Trade-off: Other requests must wait

4. **Larger cache TTL** (important)
   - TTL = 1 day instead of 1 hour
   - Reduces frequency of misses
   - Why: Fewer expiration events
   - Trade-off: Stale data for longer

5. **Circuit breaker** (important)
   - If database latency > 1s: fail requests instead of waiting
   - Return stale cache or degraded response
   - Why: Prevent cascading timeouts
   - Trade-off: Some requests fail

### Detection

**Alerting:**

```yaml
alerts:
  - alert: CacheStampede
    expr: |
      (rate(cache_hits_total[1m]) == 0) and
      (rate(database_queries_total[1m]) > 1000)
    for: 30s
    annotation: "Cache miss with high database load (possible stampede)"
  
  - alert: CyclicalCacheMiss
    expr: |
      (hour == 0 or hour == 1 or hour == 2) and
      (cache_miss_rate > 0.5)
    for: 10m
    annotation: "Cyclical cache misses at regular intervals (possible stampede)"
  
  - alert: DatabaseLoadSpike
    expr: |
      rate(database_connections_active[1m]) / database_connections_max > 0.8
    for: 1m
    annotation: "Database connection pool > 80% (possible cache stampede)"
```

### Recovery

1. **Immediately**: Enable circuit breaker (return stale cache)
2. **Short-term**: Manually refresh cache key
3. **Root cause**: Why did all requests miss simultaneously?
4. **Fix**: Implement cache warming or probabilistic refresh
5. **Prevent**: Set earlier TTL for refresh vs. expiration

---

## Chaos Experiment: Cache Stampede

```python
# experiments/traditional/cache-stampede/cache_stampede_test.py
import redis
import time
import concurrent.futures
from datetime import datetime

REDIS = redis.Redis(host='localhost', port=6379)
CACHE_KEY = "homepage_data"
CACHE_TTL = 5  # seconds (short for test)
NUM_CONCURRENT_REQUESTS = 1000

def expensive_database_query():
    """Simulate slow database query (1 second)"""
    time.sleep(1)
    return f"data_{int(time.time())}"

def fetch_data_naive():
    """Naive: no locking, all requests recompute on miss"""
    data = REDIS.get(CACHE_KEY)
    if data is None:
        # Cache miss - recompute
        data = expensive_database_query()
        REDIS.setex(CACHE_KEY, CACHE_TTL, data)
    return data

def fetch_data_with_lock():
    """Smart: use lock, only first request computes"""
    data = REDIS.get(CACHE_KEY)
    if data is None:
        # Try to acquire lock
        lock_key = f"{CACHE_KEY}:lock"
        if REDIS.setnx(lock_key, "locked"):
            try:
                # We have lock - compute value
                REDIS.expire(lock_key, 10)
                data = expensive_database_query()
                REDIS.setex(CACHE_KEY, CACHE_TTL, data)
            finally:
                REDIS.delete(lock_key)
        else:
            # Someone else is computing - wait and retry
            for _ in range(50):
                time.sleep(0.1)
                data = REDIS.get(CACHE_KEY)
                if data:
                    break
    return data

def test_cache_stampede():
    print("=" * 70)
    print("Cache Stampede Experiment")
    print("=" * 70)
    
    # Set initial cache
    REDIS.setex(CACHE_KEY, CACHE_TTL, "initial_data")
    
    print(f"\n[Phase 1] Naive approach (no locking)...")
    print(f"  Simulating {NUM_CONCURRENT_REQUESTS} concurrent requests")
    print(f"  Cache expires in {CACHE_TTL}s...")
    time.sleep(CACHE_TTL + 1)  # Wait for cache to expire
    
    naive_start = time.time()
    with concurrent.futures.ThreadPoolExecutor(max_workers=100) as executor:
        futures = [executor.submit(fetch_data_naive) for _ in range(NUM_CONCURRENT_REQUESTS)]
        for future in concurrent.futures.as_completed(futures):
            future.result()
    naive_duration = time.time() - naive_start
    
    print(f"  ✅ Completed in {naive_duration:.1f}s")
    print(f"  ~1000 concurrent DB queries (expensive!)")
    
    # Reset cache
    REDIS.delete(CACHE_KEY)
    REDIS.setex(CACHE_KEY, CACHE_TTL, "initial_data")
    
    print(f"\n[Phase 2] Smart approach (with lock)...")
    time.sleep(CACHE_TTL + 1)  # Wait for cache to expire
    
    smart_start = time.time()
    with concurrent.futures.ThreadPoolExecutor(max_workers=100) as executor:
        futures = [executor.submit(fetch_data_with_lock) for _ in range(NUM_CONCURRENT_REQUESTS)]
        for future in concurrent.futures.as_completed(futures):
            future.result()
    smart_duration = time.time() - smart_start
    
    print(f"  ✅ Completed in {smart_duration:.1f}s")
    print(f"  Only 1 DB query (much better!)")
    print(f"\n  ✅ Lock mechanism reduced time by {100 * (naive_duration - smart_duration) / naive_duration:.0f}%")

if __name__ == "__main__":
    test_cache_stampede()
```

---

## Lessons Learned

### Case Study: Homepage Cache Stampede

**Timeline**:
- Cache: 1 hour TTL, refreshed at hour boundaries
- Every hour: 10,000 req/min all miss cache
- All 10,000 hit database → 30s query latency
- Requests timeout → users see errors
- Fix: Implemented probabilistic early refresh

**Root cause**: Hard TTL with no locking mechanism

**Result**: Smooth load, no more spikes

### Key Takeaways

- Cache stampede is predictable (happens at TTL boundaries)
- Use locking mechanism for cache misses
- Probabilistic early refresh spreads load
- Monitor for cyclical cache misses
- Set circuit breaker for downstream protection

---

## Tools & Setup

```bash
# Run experiment
python experiments/traditional/cache-stampede/cache_stampede_test.py

# Monitor cache performance
redis-cli --stat
prometheus -c observability/prometheus.yml &
grafana-server &
open http://localhost:3000/d/cache-dashboard
```

---

## Related Patterns

- [Resource Exhaustion](../../0-common/resource-exhaustion/) — Stampede exhausts resources
- [Cascading Failure](../../0-common/cascading-failure/) — Stampede cascades
- [Retry Storms](../../0-common/retry-storms/) — Stampede triggers retries

---

## See Also

- [Glossary](../../../docs/GLOSSARY.md) — Cache, stampede, thundering herd
- [References](../../../docs/REFERENCES.md) — Cache invalidation and refresh patterns
