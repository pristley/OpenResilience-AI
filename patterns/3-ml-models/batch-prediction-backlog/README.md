# Pattern: Batch Prediction Backlog & Queue Overflow

## Problem Statement

When serving ML predictions in batch mode, the system may encounter a backlog where prediction requests queue up faster than the model can process them. This causes unbounded queue growth, memory exhaustion, dropped predictions, and degraded latency for all users.

**Example Scenarios:**
- End-of-month financial forecasting: 10K prediction requests arrive in 30 minutes, model processes 100/min → queue grows to 9K items
- Recommendation scoring: New features deployed, model latency increases 2x, upstream requests continue at normal rate → queue backing up
- Scheduled batch job: Runs nightly on 1M records, model crashes at record 500K → job retries from start, queue fills again
- Cold start after deployment: Model initializing, requests queue up faster than processing → backlog of 50K items

---

## Why It Matters

- **Impact**: User-facing latency increases; predictions arrive too late to be useful; some requests dropped entirely
- **Resource exhaustion**: Queue memory grows unbounded; can crash entire service (OOM kill)
- **Cascade**: Backed-up predictions block downstream systems; recommendations stale by time they're served
- **Detection latency**: May not be obvious until queue is already massive and latency is unacceptable
- **Real Cost**: $10K-100K per hour (if batch predictions are revenue-critical)

---

## How It Fails

### Mechanism

1. **Input spike**: Prediction request rate exceeds model processing rate
   - Seasonal surge (year-end, holidays)
   - New features deployed → higher latency
   - Upstream system misconfigured → sends requests faster
2. **Queue accumulation**: Requests queue up faster than they're processed
   - Queue size = request_rate × processing_time
   - If request_rate > throughput, queue grows unbounded
3. **Resource exhaustion**: Queue consumes memory
   - 1M requests × 10KB per request = 10GB memory
   - Eventually process runs out of memory → crash
4. **Dropped/stale predictions**: 
   - Requests dropped when queue exceeds max capacity
   - Predictions that finally process are too late to be useful (user already acted)
5. **Cascading slowdown**: As backlog grows, queue processing slows further
   - Disk I/O contention (requests spilled to disk)
   - Network saturation (responses slower)
   - GC pauses (cleaning up queued objects)

### Observable Signals

- **Metric anomalies**:
  - Queue depth increases linearly (not oscillating)
  - Processing latency increases as queue grows (tail latency especially)
  - Prediction latency p99 > SLA (e.g., SLA 5s, p99 now 30s)
  - Request acceptance rate plateaus (hitting concurrency limits)
- **Log patterns**:
  - "Queue full, dropping request" messages spike
  - "Processing timeout" entries increase
  - "Memory allocation failed" or OOM killer invoked
- **Trace patterns**:
  - Requests stuck in queue for minutes
  - Model initialization/inference time constant but queue wait dominates
  - Batch sizes shrinking (hitting memory limits)
- **Business signals**:
  - Predictions arrive after user has already acted
  - Recommendation scores stale by delivery time
  - Batch job not finishing by next scheduled run

### Time to Detect

- **Best case** (explicit queue depth alert): seconds to minutes
- **Realistic** (latency degradation noticed): 5-15 minutes
- **Worst case** (user complains, or OOM crash): 30+ minutes

### Blast Radius

- **Direct**: Single batch job delayed; predictions slower
- **Downstream**:
  - Recommendations served are stale/cold
  - Dashboard queries blocked waiting for predictions
  - Real-time features delayed downstream
- **Systemic**:
  - Queue backlog spills to disk → service restart slow (must replay queue)
  - Memory pressure causes GC pauses → all latencies spike
  - Crash → all in-flight predictions lost
- **Scale**: Affects all batch/batch-realtime predictions until queue drains

---

## Resilience Strategy

### Prevention

1. **Capacity Planning**
   - Calculate required throughput: peak_request_rate × SLA_latency_bound
   - Provision model replicas/resources for 2× peak rate
   - Monitor current_throughput < max_throughput; alert if approaching limit
   - Trade-off: Over-provisioning cost; may sit idle during off-peak

2. **Load Shedding**
   - Reject requests when queue depth > threshold (graceful rejection, not silent drop)
   - Return HTTP 503 to upstream ("service temporarily unavailable")
   - Backpressure communicates problem to upstream
   - Trade-off: Some requests fail; upstream must handle retry/fallback

3. **Adaptive Batching**
   - Adjust batch size based on queue depth
   - When queue small: batch_size = 64 (maximize throughput)
   - When queue large: batch_size = 256 (prioritize latency)
   - Trade-off: More complex logic; may cause unpredictable batching

4. **Model Optimization**
   - Reduce inference latency: quantization, pruning, distillation
   - Faster inference → higher throughput → smaller queue
   - Trade-off: Accuracy loss; development effort

5. **Queue Prioritization**
   - Serve urgent predictions first (e.g., user-facing vs. background)
   - Low-priority batch jobs queued separately
   - Trade-off: Background jobs starved; fairness issues

6. **Circuit Breaker**
   - If queue_depth > critical_threshold for duration → reject all new requests
   - Gives system time to drain queue without adding more load
   - Trade-off: Feature unavailability; queue takes time to drain

### Detection

**Alerting thresholds:**
```yaml
metrics:
  - name: prediction_queue_depth
    definition: current_queued_requests
    alert_threshold: > max_queue_capacity × 0.7
    window: 5min
    severity: warning
  
  - name: prediction_queue_growth_rate
    definition: (queue_depth_now - queue_depth_5min_ago) / 5
    alert_threshold: > 100 requests/min
    window: 5min
    severity: warning
  
  - name: prediction_latency_p99
    definition: 99th percentile of request_to_result_latency
    alert_threshold: > SLA × 2
    window: 5min
    severity: critical
  
  - name: prediction_drop_rate
    definition: (dropped_requests / total_requests) × 100
    alert_threshold: > 5%
    window: 5min
    severity: critical
  
  - name: model_throughput
    definition: predictions_completed_per_minute
    alert_threshold: < expected_throughput × 0.8
    window: 10min
    severity: warning

  - name: queue_memory_pressure
    definition: memory_used_by_queue_percent
    alert_threshold: > 80%
    window: 5min
    severity: critical

logs:
  - pattern: "queue_depth_exceeds_threshold"
    action: "Log queue statistics, alert on-call"
  - pattern: "request_dropped|rejected"
    action: "Increment drop metric, log reason"
  - pattern: "out_of_memory|oom_killer"
    action: "CRITICAL alert, trigger incident"

traces:
  - check: "request_queue_wait_time > 60s"
    action: "Flag as backlog candidate"
  - check: "queue_depth increasing monotonically > 10min"
    action: "Trigger escalation"
```

**Observability checklist:**
- [ ] Metric: queue_depth, queue_growth_rate, prediction_latency_p99, drop_rate, throughput
- [ ] Log: queue_depth_exceeds, request_dropped, oom_killer
- [ ] Trace: Queue wait time, request arrival rate vs. completion rate
- [ ] Health check: Queue status endpoint (current depth, max capacity, growth trend)
- [ ] Dashboard: Queue depth over time, latency percentiles, throughput vs. requested rate

### Recovery

1. **Emergency Request Shedding**
   - Reject all new requests during backlog crisis
   - Focus on draining queue
   - Restore requests once queue_depth < 50% capacity
   - Trade-off: Feature unavailability; best of bad options

2. **Increase Batch Size (Risk-aware)**
   - Temporarily increase batch size to process more predictions per inference call
   - Trade-off: May OOM if batches too large; must monitor memory carefully

3. **Scale Horizontally (if available)**
   - Spin up additional model replicas
   - Distribute load across replicas
   - Trade-off: May not be fast enough; requires infrastructure support

4. **Fallback to Cached Predictions**
   - Serve stale predictions from cache instead of queuing new ones
   - User gets old recommendation rather than none
   - Trade-off: User sees stale data; may be acceptable for non-critical queries

5. **Drain Queue to Persistent Storage**
   - Spill queue to disk/database to reclaim memory
   - Process from storage later at higher throughput
   - Trade-off: Adds latency; predictions much slower to complete

6. **Restart with Queue Persistence**
   - If crash is imminent (OOM): persist queue to storage, restart clean
   - Replay queue after restart
   - Trade-off: Service interruption; queue reprocessing adds complexity

See [CONTRIBUTING.md](../../../CONTRIBUTING.md) for adding detailed experiment and tooling examples.
