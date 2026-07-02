# Pattern: Resource Exhaustion

> When threads, memory, connections, or file descriptors run out, the entire system stops accepting new requests.

## Problem Statement

**Resource exhaustion** occurs when a service consumes all available resources (threads, memory, connections, file descriptors, CPU, disk space) faster than they can be released, causing the service to stop accepting new requests and eventually crash.

**Immediate impact**: Service becomes unresponsive → new requests rejected or queued → dependent services timeout → cascading failures.

**Real-world examples**:
- Thread pool exhaustion: 200 threads all waiting for slow database → new requests get "Thread pool full" → service unreachable
- Memory leak: Service leaks 10MB per request → runs out of heap after 1,000 requests → OutOfMemoryError → crash
- Connection pool exhaustion: Database connections not returned → pool full → new requests fail
- File descriptor exhaustion: Logs not rotated → accumulate 1000s of open files → "too many open files" error → can't open network sockets

## Why It Matters

- **Detection latency**: Immediate (service stops responding) or gradual (slow memory leak)
- **Blast radius**: Entire service affected; cascades to dependent services
- **Silent death**: Resource exhaustion often goes undetected until it causes a crash
- **Difficult debugging**: Long-running systems can exhaust resources weeks or months after deployment
- **Cost**: Service unavailability; wasted compute resources due to high memory/CPU usage

---

## How It Fails

### Failure Modes

1. **Thread pool exhaustion**
   - Service configured with 200 threads
   - Each thread processes request → calls slow database (10s query)
   - 200 slow requests arrive → all threads busy waiting
   - Request 201 arrives → no threads available → queued/rejected
   - Meanwhile, slow database requests are creating cascading timeouts
   - Result: Service can't handle new traffic

2. **Memory leak (application)**
   - Each request allocates 1MB object, forgets to release
   - Service processes 100 requests/second → 6GB leaked per minute
   - After 5 minutes: 30GB leaked → heap exhausted → OutOfMemoryError → crash
   - On restart: Same leak pattern → crashes again in 5 minutes

3. **Memory leak (system)**
   - OS keeps accumulating zombie processes
   - Containers not properly releasing allocated RAM
   - Host system memory fills up → new containers can't start
   - Eventually: entire cluster becomes unschedulable

4. **Connection pool exhaustion**
   - Service opens connection to database
   - Connection left open (forgot to close in exception handler)
   - After 100 requests: 100 connections open, max pool size exceeded
   - New requests can't get connection → timeout/fail

5. **File descriptor exhaustion**
   - Application opens files but doesn't close them
   - Logs accumulate without rotation → inode table fills
   - After 65536 files: "too many open files" error
   - Can't open new network sockets → service unreachable

6. **CPU exhaustion (tight loop)**
   - Bug in code: infinite loop without sleep
   - Thread spins at 100% CPU
   - If only 1 core, service effectively stopped
   - If multiple cores, other threads still run but system overloaded

### Observable Signals

**Metrics:**
```yaml
metrics:
  - name: thread_pool_usage
    spike: Climbs to 100% (all threads busy)
    indicates: Thread exhaustion imminent
  
  - name: memory_usage
    patterns:
      - steady_climb: Memory leak (10-100MB/min)
      - sudden_spike: Large object allocation
      - crash: OutOfMemoryError
  
  - name: connection_pool_active
    behavior: Climbs and stays high (connections not released)
    indicates: Connection leak
  
  - name: file_descriptor_count
    steady_climb: Files opened, not closed
    max_limit: OS dependent (usually 1024-65536)
  
  - name: garbage_collection_time
    behavior: GC pauses get longer as heap fills
    example: 100ms → 500ms → 2s → OOM
  
  - name: request_queue_depth
    behavior: Requests queue up when threads exhausted
    indicates: System overloaded
  
  - name: cpu_usage
    patterns:
      - steady_high: Busy processing
      - 100_percent_on_one_core: Tight loop / infinite loop

logs:
  - "Thread pool full / All threads are busy"
  - "java.lang.OutOfMemoryError: Java heap space"
  - "Too many open files"
  - "Cannot allocate memory"
  - "Connection pool timeout waiting for connection"
  - "Resource quota exceeded"
  - "Cannot create new thread"

traces:
  - trace_duration: Gets longer over time (GC pauses increase)
  - gc_pause_time: Increases as heap fills
  - request_latency: Increases as queuing happens
```

### Time to Detect

- **Best case** (alerting on memory trend): Minutes to hours
- **Realistic** (on-call sees alert): 5-30 minutes
- **Worst case** (user reports): Service is down/crashing

### Blast Radius

- **Direct**: Service becomes unresponsive
- **Cascading**: All dependent services timeout waiting for responses
- **Correlated**: Other services on same host may be affected (shared memory)
- **Scope**: Entire service affected; potentially entire cluster if widespread

---

## Resilience Strategy

### Prevention

How to avoid resource exhaustion:

1. **Resource limits** (essential)
   - Set thread pool sizes: 10-50 threads (not unlimited)
   - Set memory limits: -Xmx1g (not unlimited)
   - Set connection pool sizes: 5-20 per service
   - Set file descriptor limits: Monitor and rotate logs
   - Why: Bounded resources = bounded failure
   - Trade-off: May reject requests under extreme load

2. **Monitor resource trends** (essential)
   - Track memory usage over time (catch leaks early)
   - Alert on CPU sustained > 80%
   - Alert on thread pool > 70% utilization
   - Why: Detect problems before crash
   - Trade-off: Requires good monitoring setup

3. **Circuit breaker + timeouts** (important)
   - Don't let slow downstream services consume all threads
   - Timeout after 5-10s, return error instead of waiting
   - Why: Threads released quickly, not held indefinitely
   - Trade-off: May return errors instead of succeeding

4. **Connection/resource pooling** (important)
   - Always use connection pools (don't create new per request)
   - Return connections in finally block or try-with-resources
   - Why: Connections reused, not exhausted
   - Trade-off: Must manage pool size correctly

5. **Load shedding** (important for extreme load)
   - Reject requests with 503 "Service Unavailable" if queue too deep
   - Why: Better to reject fast than timeout slowly
   - Trade-off: Some requests rejected

6. **Graceful degradation** (domain-specific)
   - Reduce feature set under load (disable expensive features)
   - Cache aggressively
   - Use simpler algorithms
   - Why: Stay responsive under load
   - Trade-off: Reduced functionality

### Detection

Real-time monitoring to catch exhaustion:

**Alerting:**

```yaml
alerts:
  - alert: HighMemoryUsage
    expr: process_resident_memory_bytes > 800_000_000
    for: 2m
    annotation: "Memory usage > 800MB (potential leak)"
  
  - alert: MemoryTrendingUp
    expr: rate(process_resident_memory_bytes[5m]) > 5_000_000
    for: 10m
    annotation: "Memory leaking at ~5MB/min"
  
  - alert: ThreadPoolFull
    expr: (tomcat_threads_busy / tomcat_threads_max) > 0.9
    for: 1m
    annotation: "Thread pool 90% full (requests may queue)"
  
  - alert: ConnectionPoolExhausted
    expr: (hikaricp_connections_active / hikaricp_connections_max) > 0.95
    for: 1m
    annotation: "Connection pool 95% full"
  
  - alert: FileDescriptorsHigh
    expr: process_open_fds > 800
    for: 5m
    annotation: "Open file descriptors > 800 (limit usually 1024)"
  
  - alert: GCPauseLong
    expr: increase(jvm_gc_pause_seconds[5m]) > 0.5
    for: 2m
    annotation: "GC pauses > 500ms (heap filling)"
```

### Recovery

How to handle resource exhaustion when it occurs:

1. **Identify the resource**: Check metrics for memory, threads, connections, FDs
2. **Short-term fix**: Increase limit, restart service, or scale horizontally
3. **Root cause**: Memory leak? Thread leak? Connection leak? Infinite loop?
4. **Long-term fix**: Fix the leak, add resource limits, improve monitoring

---

## Chaos Experiment: Resource Exhaustion Injection

Test your system's handling of thread, memory, connection exhaustion.

### Experiment: Thread Pool Exhaustion

```python
import concurrent.futures
import requests
import time

SERVICE_URL = "http://api:8080/api/slow-endpoint"
THREAD_POOL_SIZE = 200
CONCURRENT_REQUESTS = 250

def make_slow_request():
    try:
        resp = requests.get(SERVICE_URL, timeout=35)
        return {"status": resp.status_code, "error": None}
    except requests.exceptions.Timeout:
        return {"status": None, "error": "timeout"}
    except Exception as e:
        return {"status": None, "error": str(e)}

def test_thread_pool_exhaustion():
    print(f"Making {CONCURRENT_REQUESTS} concurrent requests (pool size: {THREAD_POOL_SIZE})...")
    
    successes = 0
    rejections = 0
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=CONCURRENT_REQUESTS) as executor:
        futures = [executor.submit(make_slow_request) for _ in range(CONCURRENT_REQUESTS)]
        
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            if result["status"] == 200:
                successes += 1
            else:
                rejections += 1
    
    assert successes < CONCURRENT_REQUESTS, "Thread pool should be exhausted"
    print(f"✅ Thread pool exhaustion verified: {successes}/{CONCURRENT_REQUESTS} succeeded")
```

### Monitoring During Experiment

Watch: thread pool %, memory %, connection pool %, request latency, error rate, queue depth

### Expected Outcomes

✅ Thread pool exhaustion prevents new requests  
✅ System recovers after load reduces  
✅ Monitoring alerts on resource exhaustion

---

## Lessons Learned

### Real Incident: Production Memory Leak

**Timeline**: Deploy with leak → Day 3 memory trends up → Day 4 alert → Day 5 crashes → Fix deployed

**Root cause**: Each request allocates connection, forgets to close

**Fix**: Wrap in try-with-resources

**Cost**: 2 outages, 500+ users affected, 8 hours investigation

### Key Takeaways

- Resource limits are essential
- Monitor trends (catch gradual leaks early)
- Test your limits (know what happens at 100%)
- Graceful degradation beats crashes
- Circuit breakers save resources

---

## Tools & References

- **Prometheus**: Metrics collection and alerting
- **Grafana**: Metrics visualization
- **Java Flight Recorder**: JVM profiling
- **New Relic**: APM with resource monitoring

---

## See Also

- [Cascading Failure](../cascading-failure/) — Resource exhaustion cascades
- [Retry Storms](../retry-storms/) — Retries exhaust resources
- [Glossary](../../../docs/GLOSSARY.md) — Thread pool, memory leak, connection pool
