# Pattern: Cold Start Failure & Model Initialization

## Problem Statement

When an ML model service starts or restarts, it requires initialization time to load weights, compile code, and warm up caches. During this "cold start" window, the service cannot serve predictions, causing timeouts and errors for requests arriving during startup.

**Example Scenarios:**
- Kubernetes pod restart: deployment updates, pod scales to 0 then 1, during restart no predictions served
- Model service crash: service restarts automatically, 30-second cold start, requests timeout while loading model (50GB weights)
- Lazy initialization: model loaded on first request, user experiences 5-10 second latency on first call, then normal latency on subsequent calls
- Serverless/FaaS cold start: AWS Lambda model inference, new container spin-up takes 10-30 seconds before model loaded

---

## Why It Matters

- **Impact**: Requests timeout and fail during cold start; user sees errors or degraded experience
- **Detection latency**: Often caught by monitoring (pod restart detected), but impact window is narrow and hard to alert on
- **Cascade**: Upstream load balancers may route traffic to restarting instance, causing cascading timeouts
- **Blast radius**: Single pod restart affects 5-20 in-flight requests; affects 100s if multiple pods rolling restart
- **Real Cost**: Restart + cold start = 30-60 seconds of unavailability; at 100 req/s = 3000-6000 failed requests

---

## How It Fails

### Mechanism

1. **Cold start trigger**: Service starts or pod restarts
   - Deployment rollout
   - Node failure → pod rescheduled
   - Manual restart for debugging
   - Out-of-memory crash → automatic restart
2. **Initialization phase**: Model weights loaded into memory
   - Read from disk/network (slow): 10-100GB weights
   - Compile optimizations (CUDA, TensorRT): 5-30 seconds
   - Warm up caches: inference on dummy data
   - Establish connections (to feature store, cache layer)
3. **Service unavailability**: During initialization, model endpoint not ready
   - Readiness probe not passing (model not initialized)
   - Requests timeout (no backend available)
   - Kubernetes: pod status "Running" but service not ready; requests routed anyway
4. **Cascading failures**: 
   - Upstream LB doesn't know service not ready; sends requests
   - Requests timeout after N seconds
   - Client sees timeout, retries → adds more load
   - Retry storm delays cold start completion

### Observable Signals

- **Metric anomalies**:
  - Latency spikes at pod startup (p99/p999 very high)
  - Error rate spike coinciding with pod restart
  - Request timeouts during cold start window
  - Model load time increases (restarted pod is slower than normal)
- **Log patterns**:
  - Model initialization start/end timestamps visible
  - "Service not ready" or "model not loaded" errors
  - Connection failures to external services during init
- **Trace patterns**:
  - Requests queued until model initialization completes
  - Request spans show long "waiting for service ready" phase
  - First few requests after restart have much higher latency
- **Infrastructure signals**:
  - Pod restart/restart count increasing
  - Readiness probe failing during initialization
  - Container startup time > 30 seconds

### Time to Detect

- **Best case** (monitoring pod restart and latency spike): seconds to 1 minute
- **Realistic** (slowdown noticed by users): 1-5 minutes
- **Worst case** (user complains): 5-15 minutes

### Blast Radius

- **Direct**: Requests arriving during cold start fail (timeout)
- **Downstream**:
  - Predictions unavailable → downstream systems fail
  - Cache invalidation during restart → cold cache until warmed
  - Load spike on other replicas (traffic rerouted during restart)
- **Systemic**:
  - If multiple pods restarting (rolling deployment), cold start cascades across fleet
  - Retry storms slow overall recovery
  - Memory pressure during concurrent cold starts (if multiple pods boot at same time)
- **Scale**: 
  - Single pod restart: affects 1-10% of traffic
  - Rolling deployment: affects 20-50% of traffic during rollout (50% of nodes restarting)

---

## Resilience Strategy

### Prevention

1. **Pre-warming**
   - Load model during container initialization (not on first request)
   - Warm up model with dummy inference calls before marking as ready
   - Keep "standby" replicas ready to serve traffic
   - Trade-off: Higher resource usage (standby replicas not serving); complex orchestration

2. **Async Initialization**
   - Start accepting requests immediately (return stubs or cached predictions)
   - Initialize model in background thread
   - Serve real predictions once initialization complete
   - Trade-off: Complexity increases; stub responses may be unacceptable for users

3. **Optimize Model Loading**
   - Use memory-mapped I/O (mmap) to load weights lazily
   - Compress model weights; decompress on-load
   - Use TensorRT/ONNX Runtime for compiled inference (pre-compiled = faster)
   - Distribute model across multiple files; load in parallel
   - Trade-off: Development effort; may be incompatible with some frameworks

4. **Readiness Probe Configuration**
   - Define custom readiness probe that checks model initialized (not just HTTP 200)
   - Set initialDelaySeconds high enough for cold start (e.g., 60s)
   - Set periodSeconds low (check every 5s) to detect readiness quickly
   - Trade-off: Overly conservative probes delay traffic routing; too aggressive breaks pods

5. **Graceful Shutdown**
   - Don't start new requests during shutdown
   - Complete in-flight requests before terminating
   - Pre-warm model weights in memory (on startup, before accepting traffic)
   - Trade-off: Shutdown time increases; delays pod termination

6. **Blue-Green Deployment**
   - Deploy new version alongside old; switch traffic atomically
   - No rolling restart; avoids cold start windows
   - Trade-off: Requires 2x resources; more infrastructure complexity

### Detection

**Alerting thresholds:**
```yaml
metrics:
  - name: model_initialization_latency
    definition: time from pod start to model_ready = true
    alert_threshold: > 60 seconds
    severity: warning
  
  - name: cold_start_error_rate
    definition: error_rate during cold_start_window (5min after pod restart)
    alert_threshold: > 10%
    window: 5min
    severity: critical
  
  - name: readiness_probe_failures
    definition: (failed_probes / total_probes) × 100
    alert_threshold: > 5%
    window: 5min
    severity: warning
  
  - name: latency_spike_at_restart
    definition: p99_latency during cold_start vs. baseline
    alert_threshold: > baseline × 5
    severity: critical

  - name: pod_restart_rate
    definition: number_of_restarts_in_1hour
    alert_threshold: > 3
    severity: warning

logs:
  - pattern: "model_initialization_started|completed"
    action: "Log timestamps for cold_start latency calculation"
  - pattern: "readiness_probe_failed"
    action: "Log reason, check model status"
  - pattern: "initialization_timeout|oom_during_init"
    action: "CRITICAL alert, investigate"

traces:
  - check: "request_arrival_during_cold_start_window"
    action: "Tag request, track latency separately"
  - check: "model_initialization_blocking_requests"
    action: "Log initialization duration, check if exceeds SLA"
```

**Observability checklist:**
- [ ] Metric: model_initialization_latency, cold_start_error_rate, readiness_probe_failures
- [ ] Log: model_initialization_started, model_initialization_completed, readiness_probe_failed
- [ ] Trace: Request arrival during cold start, request latency split (waiting vs. inference)
- [ ] Health check: /ready endpoint returns true only after model initialized
- [ ] Dashboard: Pod restart rate, cold start latency distribution, error rate during restarts

### Recovery

1. **Circuit Breaker During Cold Start**
   - If model_initialization_latency > 60s, don't route traffic to restarting pod
   - Return HTTP 503 "service unavailable" until ready
   - Prevents timeout cascade
   - Trade-off: Requires smart load balancer; some requests still fail

2. **Graceful Degradation**
   - Serve stale cached predictions if model still initializing
   - Better than error/timeout from user perspective
   - Trade-off: User gets old data; may be unacceptable for time-critical predictions

3. **Prevent Concurrent Cold Starts**
   - Don't trigger multiple pod restarts at same time
   - Stagger rolling deployments (1 pod at a time instead of 50%)
   - Trade-off: Deployment takes longer

4. **Increase Cold Start Timeout**
   - Extend readiness probe timeout during deployments
   - Prevents health check from assuming pod is unhealthy during init
   - Trade-off: Masks actual failures (unhealthy pods marked as ready)

5. **Pre-stage Model Weights**
   - Store model in Persistent Volume (not loaded each restart)
   - Reduces cold start from 30s to 5s (skip download)
   - Trade-off: Requires PV infrastructure; complex storage setup

6. **Canary Deployment**
   - Route 5% traffic to new version during init
   - If error_rate < threshold, increase percentage
   - Limits blast radius of cold start issues
   - Trade-off: More complex deployment; longer rollout time

See [CONTRIBUTING.md](../../../CONTRIBUTING.md) for adding detailed experiment and tooling examples.
