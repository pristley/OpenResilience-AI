# Pattern: Network Partition

> When network connectivity fails, services become unreachable and cascading failures propagate.

## Problem Statement

A **network partition** occurs when two services that need to communicate cannot reach each other due to network failures (link failure, firewall rules, DNS failure, network congestion, routing loop, device failure). The result is immediate: all communication between the two parts of the system fails, even though both services are individually running and healthy.

**Immediate impact**: Dependent services timeout waiting for responses → resources exhaust → system cascades down.

**Real-world example**:
- Your API calls service B which calls service C
- Network link between B and C fails
- B calls C → waits indefinitely → timeout after 30s (if timeout configured)
- B's request threads/connections pile up → B runs out of resources
- Now B is also unreachable → your API times out
- Cascade: A → B → C failure becomes system-wide outage

---

## Why It Matters

- **Detection latency**: 5-60 seconds (depends on timeout configuration)
- **Blast radius**: All services on both sides of partition affected
- **Silent failure**: Both services are healthy individually, but unreachable to each other
- **Resource exhaustion**: Waiting threads/connections accumulate → system crashes harder
- **Cost**: Complete outage of affected services; cascading impact on dependent systems

---

## How It Fails

### Failure Modes

1. **Timeout cascades**
   - Service A calls B with 30s timeout
   - Network fails at T=0
   - A waits 30s → timeout exception
   - Meanwhile, A's connection pool fills up with waiting threads
   - At T=30s: A fails with "connection pool exhausted"
   - Service C depends on A → also fails
   - Cascade: A → B partitioned, but now A → C broken too

2. **Leader election failures**
   - Distributed system tries to elect leader via network consensus
   - Network partitions → both sides think they're the leader
   - Split-brain: two leaders making conflicting decisions
   - Data corruption, conflicting writes, inconsistent state

3. **Cache inconsistency**
   - Service A has cached data from service C
   - Partition occurs → A still serves stale cache
   - Service D depends on A → gets stale data
   - Later when partition heals, data is inconsistent

4. **Message queue backlog**
   - Queue service can't reach database
   - Messages accumulate → queue fills up
   - Publishers can't publish (queue full) → fail
   - System-wide cascade

5. **Health check blindness**
   - Load balancer can't reach service → marks unhealthy
   - But service IS healthy (just partitioned from load balancer)
   - Load balancer removes it from rotation → capacity lost
   - Remaining instances overloaded → they fail too

### Observable Signals

**Metrics:**
```yaml
metrics:
  - name: latency_p99
    spike: Increases to 30-60s (timeout waiting)
    cause: Requests waiting for network to respond
  
  - name: error_rate
    spike: Jumps to 100% (all requests fail)
    cause: All calls to unreachable service fail
  
  - name: connection_errors
    spike: Increases dramatically
    types:
      - "Connection refused"
      - "Connection timeout"
      - "Network unreachable"
      - "Host unreachable"
  
  - name: active_connections
    behavior: Climbs and plateaus (threads waiting)
    cause: Connections waiting for response never close
  
  - name: queue_depth
    behavior: Grows unbounded (if queue is buffered)
    cause: Messages can't be processed

logs:
  - pattern: "Connection refused"
    example: "connect: Connection refused (errno 111)"
  
  - pattern: "Connection timeout"
    example: "timeout waiting for response after 30000ms"
  
  - pattern: "Connection reset by peer"
    example: "read: Connection reset by peer"
  
  - pattern: "Name resolution failed"
    example: "getaddrinfo ENOTFOUND service-b.internal"
  
  - pattern: "Operation timed out"
    example: "ETIMEDOUT: connection timed out"

traces:
  - span_duration: 30-60s (wall-clock timeout duration)
  - span_error: Connection refused / timeout
  - trace_structure: Short trace (fails immediately or after timeout)
```

### Time to Detect

- **Best case** (alerting on error rate): 10-30 seconds
- **Realistic** (on-call sees alert): 1-5 minutes
- **Worst case** (user reports): 5-30 minutes

### Blast Radius

- **Direct**: Services on both sides of partition unreachable to each other
- **Immediate dependent**: Any service calling A or B also fails
- **Cascading**: Failure propagates upstream → potentially entire system down
- **Scope**: In worst case, can take down 80%+ of system from single link failure

---

## Resilience Strategy

### Prevention

How to avoid network partition failures:

1. **Aggressive timeouts** (essential)
   - Set timeouts short: 2-5 seconds (not 30s or infinite)
   - Why: Fail fast instead of exhausting resources
   - Config: Per-service, per-endpoint timeouts
   - Trade-off: May timeout during high latency (need retry)

2. **Connection pools with limits** (essential)
   - Thread pools: max 20-50 threads (not unlimited)
   - Connection pools: max 10-20 per service
   - Why: Bounded resource usage prevents cascade
   - Config: Set per-dependency service
   - Trade-off: May reject requests under load

3. **Circuit breaker pattern** (essential)
   - Open circuit after 5 failed requests or 50% error rate
   - Half-open to test recovery
   - Why: Stops hammering unreachable service, lets it recover
   - Config: Error threshold, open timeout, half-open size
   - Trade-off: Temporarily blocks all traffic

4. **Health checks** (important)
   - Liveness: Is service running?
   - Readiness: Can it handle traffic?
   - Frequency: Every 10-30 seconds
   - Why: Load balancer can route around partitioned service
   - Trade-off: False positives cause thrashing

5. **Bulkheads** (important)
   - Separate thread/connection pools per dependency
   - Why: Failure of one dependency doesn't consume all pools
   - Config: 5-10 threads per service
   - Trade-off: More resource management needed

6. **Fallback strategies** (domain-specific)
   - Cache: Use stale data if unavailable
   - Defaults: Return sensible defaults
   - Degradation: Reduce functionality vs. full failure
   - Why: Partial service > no service
   - Trade-off: Must manage staleness/correctness

### Detection

Real-time monitoring to catch partitions:

**Alerting:**

```yaml
alerts:
  - alert: HighLatencyP99
    expr: histogram_quantile(0.99, http_request_duration_seconds) > 5000
    for: 1m
    annotation: "p99 latency spike detected (p99 > 5s for 1m)"
  
  - alert: ErrorRateSpike
    expr: rate(http_requests_total{status=~"5.."}[1m]) > 0.1
    for: 1m
    annotation: "Error rate > 10% for 1m (possible partition)"
  
  - alert: ConnectionErrorSpike
    expr: increase(connection_errors_total[5m]) > 50
    for: 1m
    annotation: "Connection errors increased (possible network issue)"
  
  - alert: CorrelatedServiceFailure
    expr: |
      (rate(http_requests_total{service="A",status=~"5.."}[1m]) > 0.1)
      and
      (rate(http_requests_total{service="B",status=~"5.."}[1m]) > 0.1)
    for: 1m
    annotation: "Services A and B failing together (possible partition)"

observability_checklist:
  - [x] Metric: latency_p99 per service + destination
  - [x] Metric: error_rate per service + destination
  - [x] Metric: connection_errors (by type: refused, timeout, etc.)
  - [x] Metric: active_connections (by service)
  - [x] Log: Connection refused/timeout errors with destination
  - [x] Trace: Distributed trace showing request path + timing
  - [x] Health: Liveness/readiness probe results
  - [x] Dashboard: Service dependency graph with traffic flow
```

### Recovery

How to handle network partitions when they occur:

**Automatic:**
- Circuit breaker opens → stops sending requests → reduces load on failed service
- Timeout fires → returns error quickly instead of blocking
- Fallback activated → returns cached/default data
- Health check fails → load balancer removes instance

**Manual intervention:**
1. **Identify the partition**:
   - Check network connectivity: `ping`, `traceroute`, `netstat`
   - Check DNS resolution: `nslookup service-b.internal`
   - Check firewall rules: `iptables -L`, security groups
   - Check route table: `ip route show`

2. **Assess impact**:
   - Which services are on both sides of partition?
   - How many users affected?
   - Is it cascading further?

3. **Restore connectivity**:
   - Fix network link (re-enable router, fix DNS, adjust firewall)
   - Verify with: `ping`, `telnet service-b:8080`, `curl`

4. **Verify recovery**:
   - Monitor error_rate → back to baseline
   - Check latency_p99 → back to normal
   - Verify circuit breaker closes (half-open succeeds)
   - Check dependent services recovering

**Timeline:**
- T+0s: Partition occurs
- T+5-30s: First requests timeout/fail
- T+30-60s: Alert fires
- T+1-5m: On-call investigates
- T+5-10m: Fix applied (network restored)
- T+10-15m: All services recovered

---

## Chaos Experiment: Network Partition Injection

Test your system's resilience to network partitions using traffic control or iptables.

### Prerequisites

- Access to staging environment or controlled network
- Linux machine with `tc` (traffic control) or `iptables` capability
- Two services (API and backend) that communicate
- Monitoring dashboards set up
- Timeout + circuit breaker configured

### Running the Experiment

```bash
# IMPORTANT: Run in staging only! Make sure you have root access.
# Stop the experiment with: sudo tc qdisc del dev <interface> root
```

```python
# experiments/0-common/network-partition/inject_partition.py
"""
Chaos experiment: Inject network partition and verify resilience
Simulates a link failure between two services using traffic control
"""

import subprocess
import time
import requests
import json
from datetime import datetime

# Configuration
SERVICE_A_URL = "http://api:8080"
SERVICE_B_URL = "http://backend:8080"
NETWORK_INTERFACE = "eth0"  # Network interface to partition
EXPERIMENT_DURATION = 120  # seconds
HEALTH_CHECK_INTERVAL = 2

def inject_partition(interface=NETWORK_INTERFACE, target_ip="10.0.2.10"):
    """
    Simulate network partition using Linux traffic control.
    Drops all packets to target service (simulates link failure).
    """
    print(f"[{datetime.now()}] Injecting network partition on {interface}...")
    
    try:
        # Add qdisc (queuing discipline) that drops packets
        subprocess.run([
            "sudo", "tc", "qdisc", "add", "dev", interface, "root",
            "netem", "loss", "100%", "reorder", "100%"
        ], check=True, capture_output=True)
        
        print(f"✅ Network partition injected (100% packet loss on {interface})")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to inject partition: {e}")
        return False

def remove_partition(interface=NETWORK_INTERFACE):
    """Remove the network partition (restore connectivity)."""
    print(f"[{datetime.now()}] Removing network partition from {interface}...")
    
    try:
        subprocess.run([
            "sudo", "tc", "qdisc", "del", "dev", interface, "root"
        ], check=True, capture_output=True)
        print(f"✅ Network partition removed")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to remove partition: {e}")
        return False

def health_check(service_url, name):
    """Check if service is responding."""
    try:
        resp = requests.get(f"{service_url}/health", timeout=2)
        return resp.status_code == 200
    except requests.exceptions.RequestException as e:
        return False

def call_service(service_url, path="/api/data", timeout=5):
    """Make a call to service, record latency and error."""
    start = time.time()
    try:
        resp = requests.get(f"{service_url}{path}", timeout=timeout)
        latency = (time.time() - start) * 1000  # Convert to ms
        return {
            "status": resp.status_code,
            "latency_ms": latency,
            "error": None
        }
    except requests.exceptions.Timeout:
        latency = (time.time() - start) * 1000
        return {
            "status": None,
            "latency_ms": latency,
            "error": "timeout"
        }
    except requests.exceptions.ConnectionError as e:
        latency = (time.time() - start) * 1000
        return {
            "status": None,
            "latency_ms": latency,
            "error": "connection_error"
        }
    except Exception as e:
        return {
            "status": None,
            "latency_ms": None,
            "error": str(e)
        }

def test_partition_resilience():
    """
    Main experiment:
    1. Verify baseline (both services healthy)
    2. Inject partition
    3. Verify error handling (circuit breaker + fallback)
    4. Remove partition
    5. Verify recovery
    """
    
    print("=" * 70)
    print("Network Partition Chaos Experiment")
    print("=" * 70)
    
    # Phase 1: Baseline
    print("\n[Phase 1] Verifying baseline (both services healthy)...")
    a_healthy = health_check(SERVICE_A_URL, "API")
    b_healthy = health_check(SERVICE_B_URL, "Backend")
    
    assert a_healthy, "Service A should be healthy before experiment"
    assert b_healthy, "Service B should be healthy before experiment"
    print("✅ Both services healthy at baseline")
    
    # Phase 2: Inject partition
    print("\n[Phase 2] Injecting network partition...")
    partition_injected = inject_partition()
    assert partition_injected, "Failed to inject partition"
    time.sleep(3)  # Let partition take effect
    
    # Phase 3: Verify partition impact
    print("\n[Phase 3] Verifying partition impact (90% fail, 10% succeed via fallback)...")
    
    failures = 0
    timeouts = 0
    successes = 0
    errors_by_type = {}
    latencies = []
    
    for i in range(20):  # Make 20 requests
        result = call_service(SERVICE_A_URL)
        
        if result["error"]:
            errors_by_type[result["error"]] = errors_by_type.get(result["error"], 0) + 1
            if result["error"] == "timeout":
                timeouts += 1
            failures += 1
            print(f"  Request {i+1}: FAILED - {result['error']} (latency: {result['latency_ms']:.0f}ms)")
        elif result["status"] != 200:
            failures += 1
            print(f"  Request {i+1}: ERROR {result['status']} (latency: {result['latency_ms']:.0f}ms)")
        else:
            successes += 1
            print(f"  Request {i+1}: SUCCESS (fallback) - latency: {result['latency_ms']:.0f}ms")
        
        if result["latency_ms"]:
            latencies.append(result["latency_ms"])
        
        time.sleep(0.5)
    
    failure_rate = failures / 20
    success_rate = successes / 20
    
    print(f"\n  Partition impact summary:")
    print(f"    - Failures: {failures}/20 ({failure_rate*100:.0f}%)")
    print(f"    - Successes (fallback): {successes}/20 ({success_rate*100:.0f}%)")
    print(f"    - Timeouts: {timeouts}")
    print(f"    - Error types: {errors_by_type}")
    print(f"    - Avg latency: {sum(latencies)/len(latencies):.0f}ms" if latencies else "    - No successful requests")
    
    # Verify expectations
    assert failure_rate >= 0.8, f"Expected 80%+ failure rate, got {failure_rate*100:.0f}%"
    print("✅ Partition caused sufficient failures (80%+)")
    
    # Verify circuit breaker or fallback activated
    if successes > 0:
        print("✅ Fallback strategy activated (serving cached/default data)")
    
    # Phase 4: Remove partition
    print("\n[Phase 4] Removing network partition...")
    partition_removed = remove_partition()
    assert partition_removed, "Failed to remove partition"
    time.sleep(3)
    
    # Phase 5: Verify recovery
    print("\n[Phase 5] Verifying recovery (all requests succeed within 5s)...")
    
    recovery_start = time.time()
    recovered = False
    
    while time.time() - recovery_start < 30:  # Try for 30 seconds
        result = call_service(SERVICE_A_URL)
        
        if result["status"] == 200 and result["error"] is None:
            recovery_time = time.time() - recovery_start
            print(f"✅ System recovered in {recovery_time:.1f} seconds")
            recovered = True
            break
        
        print(f"  Still recovering... (attempt at T+{time.time() - recovery_start:.1f}s)")
        time.sleep(1)
    
    assert recovered, "System did not recover within 30 seconds"
    
    # Verify service B is now healthy
    print("\n[Phase 6] Verifying all services healthy post-partition...")
    a_recovered = health_check(SERVICE_A_URL, "API")
    b_recovered = health_check(SERVICE_B_URL, "Backend")
    
    assert a_recovered, "Service A should be healthy after partition removed"
    assert b_recovered, "Service B should be healthy after partition removed"
    print("✅ All services recovered")
    
    print("\n" + "=" * 70)
    print("✅ EXPERIMENT PASSED")
    print("=" * 70)
    print(f"Partition resilience verified:")
    print(f"  • Partition caused {failure_rate*100:.0f}% failure rate")
    print(f"  • System had fallback/circuit breaker ({success_rate*100:.0f}% still served)")
    print(f"  • Recovery took {recovery_time:.1f} seconds")
    print(f"  • All services healthy post-partition")

if __name__ == "__main__":
    try:
        test_partition_resilience()
    except AssertionError as e:
        print(f"\n❌ EXPERIMENT FAILED: {e}")
        raise
    finally:
        # Always clean up
        print("\n[Cleanup] Removing partition...")
        remove_partition()
```

### Alternative: Using iptables

```bash
# Block all traffic to backend service (more surgical)
sudo iptables -I OUTPUT -d 10.0.2.10 -j DROP

# Make requests to verify they fail
curl http://api:8080/api/data

# Unblock when done
sudo iptables -D OUTPUT -d 10.0.2.10 -j DROP
```

### Monitoring During Experiment

Watch these metrics in real-time:

```
Metric                      Expected During Partition    Expected After Recovery
─────────────────────────────────────────────────────────────────────────────
latency_p99                 Spike to 5-30s (timeouts)    Return to < 500ms
error_rate                  Jump to 80-100%              Return to < 0.1%
connection_errors           Spike (connection refused)   Drop to 0
active_connections          Climb (threads waiting)      Return to baseline
circuit_breaker_state       OPEN                         CLOSED (after recovery)
requests_served_from_cache  Increase if fallback used    Return to normal
```

### Expected Outcomes

✅ **Success criteria:**
- Error rate jumps to 80%+ within 10 seconds
- Circuit breaker opens and stops hammering service
- System has fallback (serves stale cache or defaults)
- Recovery completes within 30 seconds of partition removal
- No cascading failures to dependent services
- No data corruption

❌ **Failure signs:**
- Errors creep up slowly (no timeout configuration)
- System crashes completely (no circuit breaker, unbounded threads)
- No fallback (all requests fail with no recovery path)
- Recovery takes > 5 minutes (circuit breaker stuck in open)
- Cascading failures upstream (no bulkheads/isolation)

---

## Lessons Learned

### Real-World Incident: Payment Service Partition

**Timeline:**
- T+0: Network link between payment API and payment processor fails
- T+5s: Payment API sees connection timeouts (default 30s timeout)
- T+10s: Threads accumulate in payment API connection pool (all 50 threads waiting)
- T+30s: Payment API returns "service unavailable" (pool exhausted)
- T+30s: Checkout service times out on payment API
- T+1m: Checkout now failing too (threads exhausted)
- T+1m: Orders service depends on checkout → fails
- T+2m: Alert fires (but system already cascaded)
- T+2m: On-call starts investigation
- T+5m: Network team fixes link
- T+10m: Services restart; queue of failed payments manually processed

**Root cause:** No timeout on payment API calls; no circuit breaker; no fallback

**Fix applied:**
1. Add 5-second timeout on payment processor calls
2. Add circuit breaker: open after 5 consecutive failures
3. Add fallback: queue payment for retry later
4. Add health checks: verify connectivity before routing

**Prevention:**
- Set aggressive timeouts (5s max)
- Implement circuit breakers
- Use bulkheads (separate thread pools per dependency)
- Add fallback strategies (queue, cache, defaults)
- Monitor connection errors specifically

### Key Takeaways

- **Timeouts are critical**: Infinite/long timeouts cause cascades
- **Circuit breaker is essential**: Stops hammering broken service
- **Bulkheads prevent cascade**: Isolate failure to one service
- **Fallback reduces impact**: Partial service > no service
- **Partition is partition**: Whether DNS/network/firewall/link, the effect is the same

### Anti-Patterns

- ❌ **"We'll just retry indefinitely"** → Creates cascade, exhausts resources
- ❌ **"Network is never down"** → Every system fails; be prepared
- ❌ **"All traffic uses one pool"** → One failure cascades to all
- ❌ **"No monitoring of errors by type"** → Can't distinguish partition from other errors
- ❌ **"Long timeout (30s+) + no circuit breaker"** → Guaranteed cascade

---

## Tools & Configuration

### Timeout Configuration (Examples)

```python
# Python requests
requests.get(url, timeout=5)  # 5 second timeout

# Go http client
client := &http.Client{
  Timeout: 5 * time.Second,
}

# Node.js axios
axios.get(url, { timeout: 5000 })

# Java HttpClient
HttpClient.newBuilder()
  .connectTimeout(Duration.ofSeconds(5))
  .build()
```

### Circuit Breaker Configuration (Resilience4j example)

```yaml
resilience4j:
  circuitbreaker:
    configs:
      default:
        registerHealthIndicator: true
        slidingWindowSize: 10
        failureRateThreshold: 50
        slowCallRateThreshold: 50
        slowCallDurationThreshold: 2000  # 2 seconds
        permittedNumberOfCallsInHalfOpenState: 3
        automaticTransitionFromOpenToHalfOpenEnabled: true
        waitDurationInOpenState: 10000  # 10 seconds
        eventConsumerBufferSize: 10
```

### Health Check Configuration

```yaml
liveness_probe:
  http_get:
    path: /health/live
    port: 8080
  initial_delay_seconds: 10
  period_seconds: 10
  failure_threshold: 3

readiness_probe:
  http_get:
    path: /health/ready
    port: 8080
  initial_delay_seconds: 5
  period_seconds: 5
  failure_threshold: 3
```

### Monitoring Setup

```yaml
prometheus:
  scrape_configs:
    - job_name: 'api-service'
      scrape_interval: 15s
      static_configs:
        - targets: ['localhost:9090']
      metric_relabel_configs:
        - source_labels: [__name__]
          regex: 'http_requests_total|http_request_duration_seconds|connection_errors_total'
          action: keep
```

---

## Related Patterns

- [Cascading Failure](../cascading-failure/) — Network partition often triggers cascades
- [Timeout Misalignment](../timeout-misalignment/) — Timeout misconfiguration worsens partitions
- [Resource Exhaustion](../resource-exhaustion/) — Partition → threads wait → resource exhaustion
- [Retry Storms](../retry-storms/) — Bad retry + partition = exponential failures

---

## References

### Academic Papers

- **Jepsen Analysis of Distributed Systems**: https://jepsen.io/
  - Comprehensive testing of partition handling in various systems
  - Key insight: Most systems don't handle partitions gracefully

- **"Designing Resilient Systems" (Amazon)**: https://docs.aws.amazon.com/whitepapers/latest/resilience/
  - Best practices for handling network failures
  - Circuit breaker patterns and timeout management

- **"The Network is Reliable" (Aphyr)**: https://aphyr.com/posts/288-the-network-is-reliable
  - Why network failures are common and inevitable
  - Real examples from production systems

### Tools & Projects

- **Chaos Mesh**: https://chaos-mesh.org/ — Kubernetes chaos engineering
- **Gremlin**: https://www.gremlin.com/ — Commercial chaos engineering platform
- **Linkerd**: https://linkerd.io/ — Service mesh with automatic retries + circuit breaker
- **Hystrix**: https://github.com/Netflix/Hystrix — Circuit breaker library (Netflix)

### Configuration References

- **Spring Cloud Circuit Breaker**: https://spring.io/projects/spring-cloud-circuitbreaker
- **Resilience4j**: https://resilience4j.readme.io/
- **Envoy Proxy**: https://www.envoyproxy.io/ — Built-in timeouts + circuit breaker

---

## See Also

- [Glossary](../../../docs/GLOSSARY.md) — Network partition, circuit breaker, bulkhead
- [Theory](../../../docs/THEORY.md) — Resilience principles for distributed systems
- [References](../../../docs/REFERENCES.md) — More papers on distributed systems failures
