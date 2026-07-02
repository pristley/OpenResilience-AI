# Pattern: Cascading Failure

> When one service fails, can you prevent it from taking down others?

## Problem Statement

Cascading failure occurs when a single point of failure propagates through dependent services, causing a chain reaction of outages. Instead of isolating the problem, the failure spreads like dominoes.

**Example:**
- **Traditional**: "Payment API timeout → checkout service waits indefinitely → frontend stops responding → users can't complete purchases"
- **AI/Data**: "Feature store goes down → real-time inference pipeline hangs → recommendation service timeout → entire recommendation feature unavailable for millions of users"
- **ML Ops**: "Model serving container OOM → queue backs up → upstream data pipeline stops consuming messages → data becomes stale → downstream analytics broken"

---

## Why It Matters

- **Impact metric**: Single service failure → system-wide outage (100% of dependent services fail, not just 1%)
- **Detection latency**: Seconds to minutes if you know what to look for; hours if discovered by user reports
- **Blast radius**: Exponential growth—failure of service A → fails services B, C, D → which fail E, F, G, H
- **Cost**: Compound impact. Five services at 99.9% uptime can cascade to 95% combined availability
- **Common outcome**: "We're down" instead of "Feature X is degraded"

---

## How It Fails

### Mechanism

1. **Service A fails** (e.g., database connection pool exhausted, memory leak, deployment bug)
2. **Service B calls A** and gets no response (or slow response)
3. **B doesn't know A is broken**, so it waits/retries indefinitely, consuming its own resources
4. **B's resource pools drain** (threads, connections, memory)
5. **B becomes slow/unresponsive**, now it's failing too
6. **Service C depends on B**, sees the same degradation
7. **Chain reaction continues** until the entire system is down

**Key enabler**: Services were designed assuming dependencies always work.

### Observable Signals

Watch for:

- **Metric**: `error_rate` or `timeout_rate` spikes in multiple services at once
- **Metric**: `latency_p99` increases across the call chain (A → B → C)
- **Metric**: `resource_utilization` (threads, connections, memory) maxes out on dependent services
- **Log**: "Connection timeout", "Queue full", "Thread pool exhausted" messages appearing in cascade
- **Trace**: Request traces show increasing latency at each hop (service A = 100ms, B = 1s, C = 5s)
- **Alert**: Circuit breaker opens (if you have them) after too many failures
- **Symptom**: Manual report: "Everything is slow" or "Can't load anything"

### Time to Detect

- **Best case** (you're watching the right metric): 5-10 seconds (alert fires immediately)
- **Realistic** (metric → alert → human → page): 1-2 minutes
- **Worst case** (user reports it): 5-15 minutes or until someone notices errors

### Blast Radius

- **Direct**: Service A is down → users of A are affected
- **Immediate downstream**: Services B, C that call A → their users also affected
- **Secondary cascade**: D, E, F that call B/C → cascade widens
- **Scope**: In distributed systems, can affect 80% of the system from a single failure
- **Indirect**: Monitoring systems may become slow if they depend on failed services → blind spot

---

## Resilience Strategy

### Prevention

How to avoid cascading failures:

1. **Timeouts** (essential)
   - Set aggressive read timeouts on all external calls (e.g., 2-5 seconds max)
   - Why it helps: B stops waiting for A after 5s, instead of blocking indefinitely
   - Trade-off: May fail fast instead of waiting for recovery; needs graceful degradation

2. **Circuit Breaker** (essential)
   - Open circuit after N consecutive failures or error_rate > threshold
   - Why it helps: Stops hammering a failing service; saves its resources for recovery
   - Trade-off: Adds complexity; needs fallback behavior

3. **Bulkheads** (important for resource isolation)
   - Separate thread pools/connection pools for each downstream dependency
   - Why it helps: If A exhausts its connections, only B's pool is full (C and D are unaffected)
   - Trade-off: More resource overhead; harder to share resources

4. **Rate Limiting & Backpressure** (important)
   - Shed excess load before it cascades
   - Why it helps: If you can't handle it, fail fast for some requests rather than slow for all
   - Trade-off: Fairness issues; need clear SLA about which requests to drop

5. **Graceful Degradation** (AI/data specific)
   - Use cached/stale features if feature store is down
   - Use simpler model if inference service is slow
   - Use default recommendation if personalization is unavailable
   - Why it helps: Partial service >> no service
   - Trade-off: Feature/quality tradeoff; complexity managing fallbacks

6. **Health Checks** (monitoring foundation)
   - Liveness: Is the service up?
   - Readiness: Can it handle traffic?
   - Why it helps: Load balancer can route around failing instances
   - Trade-off: False positives can cause thrashing

### Detection

Set up observability to catch cascading failures early:

**Alerting:**
- Alert on error_rate spike in multiple services simultaneously (pattern: correlated failures)
- Alert on latency increase in call chain (service A latency ↑ → service B latency ↑)
- Alert on resource exhaustion (thread pool, connection pool, memory)

**Observability checklist:**
- [ ] **Metric**: Histogram or counter tracking response time per service + dependency
- [ ] **Metric**: Error rate per service + endpoint
- [ ] **Metric**: Resource utilization (threads, connections, memory, queue depth)
- [ ] **Log**: Structured logs with service name, caller, duration, status code
- [ ] **Trace**: Distributed trace showing call chain and timing at each hop
- [ ] **Health check**: Regular liveness/readiness probes (every 10-30 seconds)
- [ ] **Dashboard**: Dependency graph showing which services call which (service map)

**Example Prometheus alert:**
```yaml
# Alert when latency increases in a dependency chain
- alert: ServiceLatencyCascade
  expr: |
    (histogram_quantile(0.95, http_request_duration_seconds{service="payment"}) > 1)
    and
    (histogram_quantile(0.95, http_request_duration_seconds{service="checkout"}) > 2)
  for: 2m
  annotations:
    summary: "Latency cascade detected: payment slow → checkout slower"

# Alert on correlated failures
- alert: CorrelatedServiceFailures
  expr: |
    count(increase(http_requests_total{status=~"5.."}[1m]) > 10) > 2
  for: 1m
  annotations:
    summary: "Multiple services failing simultaneously (possible cascade)"
```

### Recovery

How to stop the cascade and restore service:

**Automatic:**
- Circuit breaker opens → stops sending requests to failing service → A recovers faster
- Request queue drains → downstream services recover
- Auto-rollback if recent deployment caused it (if monitoring detected regression)
- Automatic failover to backup service/region

**Manual intervention:**
1. **Identify the root cause**: Which service failed first?
   - Look at logs for earliest errors
   - Check recent deployments/changes
   - Review metrics spike timeline

2. **Stop the cascade**:
   - Kill traffic to the failing service (drain connections)
   - Increase timeouts on dependent services (buy time for recovery)
   - Enable circuit breaker if not already open

3. **Recover the root cause**:
   - Restart the service
   - Roll back recent deployment
   - Scale up if resource-constrained
   - Check external dependencies (database, cache)

4. **Verify recovery**:
   - Check error rates returning to baseline
   - Verify latency normalizing
   - Monitor dependent services for cascading effects

**Timeline example:**
- T+0s: Service A fails (internal error or external dependency down)
- T+5-10s: Circuit breaker opens on service B → stops hammering A
- T+15s: Alert fires → on-call engineer paged
- T+2m: Engineer investigates, identifies root cause
- T+3m: Manual fix applied (restart A, scale up, rollback, etc.)
- T+5m: Error rates return to baseline
- T+10m: Dependent services fully recovered

---

## Chaos Experiment

Test your cascading failure defenses.

### Prerequisites

- Access to staging environment (or production with careful controls)
- Observability set up: dashboards, alerts, logs
- Kill switch: way to stop the experiment quickly
- Dependency graph: know which services call which

### Setup

```bash
# Install chaos engineering tools
pip install chaos-toolkit chaos-toolkit-kubernetes

# Or use Docker/Kubernetes native disruption:
# kubectl apply -f chaos-experiments/

# Verify baseline metrics
# - Error rate < 0.1%
# - Latency p99 < 500ms
# - All health checks passing
```

### Running the Experiment (Scenario 1: Database Timeout)

```python
# experiments/cascading-failure/inject_db_timeout.py
"""
Chaos experiment: Inject database timeout to test cascading failure
"""
import time
import logging
import requests
from datetime import datetime

logging.basicConfig(level=logging.INFO)

# Configuration
DB_SERVICE_URL = "http://database-service:5432"
TIMEOUT_DURATION_SECONDS = 120  # 2 minutes
DEPENDENT_SERVICES = [
    "http://user-service:8080/health",
    "http://recommendation-service:8080/health", 
    "http://payment-service:8080/health",
]

def inject_database_failure():
    """
    Simulate database timeout by:
    1. Injecting chaos rule (iptables, tc, or via chaos toolkit)
    2. Or: mock database service to not respond
    """
    logging.info(f"[{datetime.now()}] Injecting database timeout...")
    
    # Option A: Use Linux tc (traffic control) to add latency + packet loss
    import subprocess
    subprocess.run([
        "sudo", "tc", "qdisc", "add", "dev", "eth0", "root", 
        "netem", "delay", "5000ms", "loss", "100%"
    ], capture_output=True)
    
    # Or Option B: Call chaos toolkit or Kubernetes disruption
    # chaos run chaos_experiments/database_timeout.json
    
    return True

def verify_cascade_begins(interval_seconds=5, duration_seconds=60):
    """
    Verify that failure cascades to dependent services
    Check: Error rates should increase across call chain
    """
    start_time = time.time()
    errors_by_service = {svc: [] for svc in DEPENDENT_SERVICES}
    
    while time.time() - start_time < duration_seconds:
        for service_url in DEPENDENT_SERVICES:
            try:
                response = requests.get(service_url, timeout=2)
                error = 1 if response.status_code >= 500 else 0
                errors_by_service[service_url].append(error)
                logging.info(f"{service_url}: {response.status_code}")
            except requests.exceptions.Timeout:
                logging.warning(f"{service_url}: TIMEOUT")
                errors_by_service[service_url].append(1)
            except Exception as e:
                logging.error(f"{service_url}: {e}")
                errors_by_service[service_url].append(1)
        
        time.sleep(interval_seconds)
    
    # Verify cascade: all services should have errors, not just DB
    for service, errors in errors_by_service.items():
        error_rate = sum(errors) / len(errors) if errors else 0
        assert error_rate > 0.5, f"{service} should have >50% error rate, got {error_rate*100:.1f}%"
        logging.info(f"✅ {service} correctly affected: {error_rate*100:.1f}% error rate")

def verify_circuit_breaker_opens():
    """
    Verify circuit breaker opens to stop cascading requests
    Expected: Error rate spikes, then circuit breaker stops requests
    """
    logging.info("Checking if circuit breaker opened...")
    
    # Query metrics: circuit breaker state should be OPEN
    response = requests.get("http://metrics-server:9090/api/v1/query",
        params={"query": 'circuitbreaker_state{state="open"}'}
    )
    results = response.json()['data']['result']
    
    assert len(results) > 0, "Circuit breaker should have opened"
    logging.info(f"✅ Circuit breaker opened: {len(results)} breakers")

def verify_graceful_degradation():
    """
    Verify that system degrades gracefully instead of failing completely
    Expected: Error rates spike but some requests succeed with fallback
    """
    logging.info("Checking graceful degradation...")
    
    # Query error rate from recommendations
    response = requests.get("http://localhost:8080/api/recommendations?user_id=123", timeout=5)
    
    if response.status_code == 200:
        data = response.json()
        if data.get('source') == 'cached':
            logging.info("✅ Graceful degradation working: serving cached recommendations")
        elif data.get('source') == 'default':
            logging.info("✅ Graceful degradation working: serving default recommendations")
    else:
        logging.error(f"❌ Service failed completely: {response.status_code}")
        return False
    
    return True

def recover_system():
    """Remove the chaos injection"""
    logging.info(f"[{datetime.now()}] Recovering system...")
    
    import subprocess
    subprocess.run([
        "sudo", "tc", "qdisc", "del", "dev", "eth0", "root"
    ], capture_output=True)
    
    # Wait for recovery
    time.sleep(10)
    
    # Verify services healthy again
    for service_url in DEPENDENT_SERVICES:
        try:
            response = requests.get(service_url, timeout=2)
            assert response.status_code < 500, f"{service_url} still returning errors"
        except Exception as e:
            logging.error(f"{service_url} not recovered: {e}")
            raise

if __name__ == "__main__":
    try:
        logging.info("=" * 60)
        logging.info("Cascading Failure Chaos Experiment")
        logging.info("=" * 60)
        
        inject_database_failure()
        time.sleep(5)  # Let cascade propagate
        
        verify_cascade_begins()
        logging.info("✅ Cascade confirmed")
        
        verify_circuit_breaker_opens()
        verify_graceful_degradation()
        
        logging.info("\n" + "=" * 60)
        logging.info("Experiment Success! System has defenses against cascade.")
        logging.info("=" * 60)
        
    except AssertionError as e:
        logging.error(f"❌ Experiment Failed: {e}")
        raise
    finally:
        recover_system()
```

### Monitoring During Experiment

**Watch these metrics:**
- `http_requests_total{status=~"5.."}` — Should spike across multiple services
- `http_request_duration_seconds` — Latency should increase in call chain
- `circuitbreaker_state` — Should transition to OPEN
- `thread_pool_active_threads` — Should max out on dependent services
- `feature_store_cache_hits` — Should increase if using fallback cache

**Expected dashboard behavior:**
1. T+0s: Database service error rate spikes to 100%
2. T+5s: Error rate in user-service increases (calls DB)
3. T+10s: Error rate in recommendation-service increases (calls user-service)
4. T+15s: Circuit breaker opens (stops cascading requests)
5. T+20s: Error rates stabilize (circuit prevents further cascade)
6. T+3m: After recovery, all services return to normal

### Cleanup

```bash
# Remove network chaos
sudo tc qdisc del dev eth0 root

# Or with Kubernetes:
kubectl delete -f chaos-experiments/cascading-failure.yaml

# Verify system is healthy
curl http://localhost:8080/health
```

### Expected Outcomes

✅ **Success criteria:**
- Error spike is detected within 10 seconds (alerting works)
- Circuit breaker opens, preventing N+1 cascades (protection works)
- System gracefully degrades (serves partial functionality)
- Recovery is automatic and completes within 2 minutes (resilience works)
- No data loss (cascading doesn't corrupt state)

❌ **Failure signs:**
- Cascade spreads to services that don't depend on root cause
- System remains down after removing chaos (poor recovery)
- No circuit breaker activation (unprotected)
- Monitoring itself becomes unavailable (blind spot)

---

## Lessons Learned

### Real-World Examples

**Example 1: AWS DynamoDB Outage (2020)**
- **Root cause**: Database throttling during traffic spike
- **Cascade**: Users → API → database; API backlog → memory spike → crashes
- **Detection**: 5-10 minutes (discovered via user reports)
- **Impact**: Multiple AWS services unavailable for hours
- **Fix**: Improved throttling + timeouts + circuit breakers
- **Lesson**: Automatic resource protection != application-level protection

**Example 2: Cache Stampede → Cascade**
- **Root cause**: Cache expires for popular item (e.g., featured product)
- **Cascade**: All users request same item → database overwhelmed → other queries slow → cascade
- **Prevention**: Probabilistic early expiration, cache warming, rate limiting
- **Lesson**: Single shared resource failures can have multiplicative effects

**Example 3: Model Serving Cascade in ML System**
- **Root cause**: New model deployed, inference latency increased 10x
- **Cascade**: Inference requests timeout → feature store requests timeout → data pipeline backs up
- **Detection**: 1-2 minutes
- **Fix**: A/B test new model with traffic limit, canary deployment, automatic rollback
- **Lesson**: Performance regressions can cascade as quickly as outages

### Key Takeaways

- **Isolation is key**: Bulkheads, timeouts, circuit breakers prevent spread
- **Assume dependencies fail**: Don't wait indefinitely; fail fast
- **Monitor cascades**: Watch for correlated failures across services
- **Degrade gracefully**: Partial service > no service
- **Detect early**: First alert is usually in the root cause service, not dependents

### Anti-Patterns

- ❌ **"Everything's critical, increase timeout"**: Creates longer cascade
- ❌ **"Just add retry logic"**: Amplifies cascading requests
- ❌ **"One big circuit breaker"**: Fails entire system instead of isolating
- ❌ **"Monitoring is separate"**: Monitoring cascade = blind to the actual failure
- ❌ **"In-memory cache = no fallback"**: Single point of failure for performance

---

## Tools & References

### Specific Tools for This Pattern

- **Circuit Breaker Libraries**
  - Hystrix (Java) — [Netflix Hystrix Docs](https://github.com/Netflix/Hystrix)
  - Polly (.NET) — [Polly Resilience](https://github.com/App-vNext/Polly)
  - PyBreaker (Python) — [PyBreaker GitHub](https://github.com/danielfm/pybreaker)
  - Spring Cloud (Java) — Built-in circuit breaker

- **Bulkhead/Isolation**
  - Kubernetes resource requests/limits
  - Thread pool configuration (Hystrix, Spring, etc.)
  - Connection pool sizing

- **Chaos Engineering**
  - Chaos Toolkit — [Chaos Community](https://chaosengineering.org/)
  - Gremlin — [Chaos as a Service](https://www.gremlin.com/)
  - Kubernetes Chaos — [ChaosMesh](https://chaos-mesh.org/)
  - Netflix Chaos Monkey — [Simian Army](https://github.com/Netflix/SimianArmy)

### Observability Setup

**Prometheus + Grafana:**
```yaml
# Recommended metrics to scrape
scrape_configs:
  - job_name: 'cascade-monitoring'
    static_configs:
      - targets: ['localhost:9090']
    metric_relabel_configs:
      - source_labels: [__name__]
        regex: 'http_requests_total|http_request_duration_seconds|circuitbreaker.*'
        action: keep
```

**Dashboard panels:**
- Service dependency graph (service map)
- Error rate time series (all services)
- Latency percentiles per service
- Circuit breaker state
- Resource utilization (threads, connections, memory)

### Configuration

Recommended values (adjust for your SLA):

- **Timeout**: 2-5 seconds (fail fast)
- **Circuit breaker open threshold**: 5 consecutive errors or 50% error rate over 10 requests
- **Circuit breaker half-open timeout**: 30 seconds
- **Bulkhead size**: 10-20 threads per dependency
- **Max retries**: 2-3 (with exponential backoff)
- **Backoff multiplier**: 2x (100ms → 200ms → 400ms)

---

## Related Patterns

- [Network Partition](../network-partition/) — One aspect of cascading failures
- [Resource Exhaustion](../../patterns/) — Often the root cause
- [Retry Storm](../../patterns/) — Amplifies cascading effects

---

## See Also

- [Glossary](../../../docs/GLOSSARY.md) — Bulkhead, Circuit Breaker, Graceful Degradation
- [Theory](../../../docs/THEORY.md) — Resilience engineering principles
- [Contributing](../../../CONTRIBUTING.md) — Share your experiences with cascading failures

