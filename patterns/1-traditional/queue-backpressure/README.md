# Pattern: Queue Backpressure & Consumer Lag

> When producers outpace consumers, queues overflow causing cascading failures.

## Problem Statement

**Queue backpressure** occurs when message producers add items to a queue faster than consumers can process them, causing:
- Queue depth increases indefinitely
- Memory fills up (queue stored in memory)
- Message retention exceeds disk capacity
- Old messages lost or dropped
- Consumer lag increases (recovery time increases)
- Cascading failures if queue becomes unavailable

**Immediate impact**: Producer flood → queue fills → memory exhausted → queue crashes → cascade.

**Real-world example**:
- Order processing queue: 100 orders/second normally
- During flash sale: 1000 orders/second
- Consumer processes: 100 orders/second (no scaling)
- Queue depth: 100 → 1000 → 10,000 → out of memory
- Queue crashes → orders lost or service down
- Backup queue starts filling → cascade

## Why It Matters

- **Message loss**: Queue fills → oldest messages dropped
- **Resource exhaustion**: Memory/disk filled by queue
- **Consumer lag**: Backlog takes hours to process
- **System instability**: Queue crashes affects entire pipeline
- **Cascading**: Backup queues also fill → cascade

---

## How It Fails

### Mechanism

1. Producers add messages to queue: 1000 msg/sec
2. Consumers process: 100 msg/sec
3. Net: +900 msg/sec accumulate in queue
4. Queue depth grows: 100 → 1000 → 10,000
5. Queue memory fills
6. If in-memory: crash
7. If disk-backed: fill disk → system crash
8. Queue becomes unavailable
9. Producers can't add messages → cascade upstream

### Observable Signals

```yaml
metrics:
  - name: queue_depth
    spike: Increases steadily over time
    example: 100 → 1000 → 10,000 messages
  
  - name: producer_rate
    pattern: Exceeds consumer rate
    example: 1000 msg/sec produced, 100 msg/sec consumed
  
  - name: consumer_lag
    spike: Increases as queue fills
    example: 0 seconds lag → 300+ seconds to catch up
  
  - name: queue_memory_usage
    spike: Fills up as queue depth increases
    example: 100MB → 1000MB → out of memory
  
  - name: oldest_message_age
    spike: Increases (messages sitting in queue longer)
    example: 1 second → 300 seconds
  
  - name: message_loss_rate
    spike: Increases if queue needs to drop messages
    indicates: Queue overflow

logs:
  - "Queue depth: 10000 (high!)"
  - "Consumer lag: 300 seconds"
  - "Message dropped (queue full)"
  - "Out of memory, cannot queue message"
  - "Producer blocked: queue full"

traces:
  - message_latency: Time from produce to consume
    example: 1ms → 300 seconds (in queue that long)
  - queue_latency: Time spent in queue
  - throughput: Messages per second
```

### Time to Detect

- **Best case** (alerting on queue depth): 10-30 seconds
- **Realistic** (on-call sees lag increasing): 1-5 minutes
- **Worst case** (queue crashes): 5+ minutes

### Blast Radius

- **Direct**: Queue backing up, messages delayed
- **Cascading**: Producers blocked, upstream services affected
- **Multiplicative**: If multiple queues: cascade through pipeline
- **Scope**: Entire asynchronous processing pipeline affected

---

## Resilience Strategy

### Prevention

1. **Scale consumers with producers** (essential)
   - Auto-scale consumers when lag > 10 seconds
   - Target: lag < 1 second
   - Why: Prevents queue from filling
   - Trade-off: Higher infrastructure cost

2. **Queue depth alerting** (essential)
   - Alert when depth > 10,000 messages
   - Alert when depth growing > 1000/min
   - Why: Early warning before crash
   - Trade-off: Need alerting setup

3. **Producer rate limiting** (important)
   - If consumer lag > 30s: reject new messages with backpressure
   - Why: Prevent queue from growing unbounded
   - Trade-off: Some requests rejected

4. **Message TTL / expiration** (important)
   - Don't keep messages in queue > 1 hour
   - Drop old messages if queue full
   - Why: Bounded queue size
   - Trade-off: Messages may be lost

5. **Multiple queue instances** (important)
   - Shard messages across multiple queue instances
   - Prevents single queue from bottleneck
   - Why: Distributes load
   - Trade-off: More complex management

### Detection

**Alerting:**

```yaml
alerts:
  - alert: HighQueueDepth
    expr: queue_depth_messages > 10000
    for: 1m
    annotation: "Queue depth > 10k messages (backpressure)"
  
  - alert: QueueDepthGrowing
    expr: rate(queue_depth_messages[5m]) > 1000
    for: 5m
    annotation: "Queue depth growing > 1000 msg/min (producers > consumers)"
  
  - alert: HighConsumerLag
    expr: consumer_lag_seconds > 60
    for: 1m
    annotation: "Consumer lag > 60s (queue backing up)"
  
  - alert: QueueMemoryHigh
    expr: queue_memory_bytes / queue_memory_max > 0.8
    for: 1m
    annotation: "Queue memory > 80% (approaching limit)"
  
  - alert: MessageLossDetected
    expr: increase(messages_dropped_total[1m]) > 0
    for: 1m
    annotation: "Messages being dropped (queue overflow)"
```

### Recovery

1. **Immediate**: Auto-scale consumers (add more instances)
2. **Short-term**: Reject new produce requests (backpressure)
3. **Root cause**: Why are producers outpacing consumers?
4. **Fix**: Optimize consumer throughput or reduce producer rate
5. **Monitor**: Watch lag decrease back to normal

---

## Chaos Experiment: Queue Backpressure

```python
# experiments/traditional/queue-backpressure/backpressure_test.py
import time
import threading
import queue
from datetime import datetime

PRODUCER_RATE = 1000  # msg/sec
CONSUMER_RATE = 100   # msg/sec
TEST_DURATION = 10    # seconds

def producer(q, rate, duration):
    """Produce messages at fixed rate"""
    produced = 0
    start = time.time()
    while time.time() - start < duration:
        try:
            q.put(f"msg_{produced}", timeout=0.01)
            produced += 1
            time.sleep(1.0 / rate)  # Space messages
        except queue.Full:
            print(f"  Producer: queue full, blocking...")
    return produced

def consumer(q, rate, duration):
    """Consume messages at fixed rate"""
    consumed = 0
    start = time.time()
    while time.time() - start < duration:
        try:
            msg = q.get(timeout=0.1)
            consumed += 1
            time.sleep(1.0 / rate)  # Space consumption
        except queue.Empty:
            pass
    return consumed

def test_queue_backpressure():
    print("=" * 70)
    print("Queue Backpressure Experiment")
    print("=" * 70)
    
    # Create queue with limited capacity
    q = queue.Queue(maxsize=1000)
    
    print(f"\n[Phase 1] Baseline - balanced load...")
    # Producer and consumer at same rate
    q_balanced = queue.Queue(maxsize=1000)
    
    prod_t = threading.Thread(target=producer, args=(q_balanced, 100, 5))
    cons_t = threading.Thread(target=consumer, args=(q_balanced, 100, 5))
    prod_t.start()
    cons_t.start()
    prod_t.join()
    cons_t.join()
    
    print(f"  Queue depth at end: {q_balanced.qsize()}")
    assert q_balanced.qsize() < 100, "Queue should stay small with balanced rates"
    print("  ✅ Balanced load OK")
    
    print(f"\n[Phase 2] Overload - producer >> consumer...")
    print(f"  Producer: {PRODUCER_RATE} msg/sec")
    print(f"  Consumer: {CONSUMER_RATE} msg/sec")
    
    q_overload = queue.Queue(maxsize=1000)
    
    prod_t = threading.Thread(target=producer, args=(q_overload, PRODUCER_RATE, TEST_DURATION))
    cons_t = threading.Thread(target=consumer, args=(q_overload, CONSUMER_RATE, TEST_DURATION))
    prod_t.start()
    cons_t.start()
    
    # Monitor queue depth
    for i in range(TEST_DURATION):
        time.sleep(1)
        depth = q_overload.qsize()
        print(f"  [{i}] Queue depth: {depth}")
    
    prod_t.join()
    cons_t.join()
    
    final_depth = q_overload.qsize()
    print(f"\n  Final queue depth: {final_depth}")
    assert final_depth > 0, "Queue should have accumulated messages"
    print(f"  ✅ Backpressure verified (queue filled to {final_depth} messages)")

if __name__ == "__main__":
    test_queue_backpressure()
```

---

## Lessons Learned

### Case Study: Order Queue Overflow (Flash Sale)

**Timeline**:
- Normal: 100 orders/sec
- Flash sale: 1000 orders/sec
- Consumers: still 100/sec (no auto-scaling)
- Queue fills: 1000 → 10,000 → out of memory
- Queue crashes
- Orders lost or delayed 2+ hours

**Root cause**: No auto-scaling, no backpressure

**Fix**: 
1. Auto-scale consumers on lag
2. Producer backpressure on queue full
3. Message TTL to prevent indefinite accumulation

### Key Takeaways

- Queue depth is leading indicator
- Consumer lag must be monitored continuously
- Auto-scale consumers with queue depth
- Producer backpressure prevents cascade
- Message TTL prevents memory exhaustion

---

## Tools & Setup

```bash
# Run experiment
python experiments/traditional/queue-backpressure/backpressure_test.py

# Monitor queue
redis-cli -p 6379 info stats
kafka-consumer-groups.sh --group my-group --bootstrap-server localhost:9092
rabbitmqctl status

# Monitor with Prometheus
prometheus -c observability/prometheus.yml &
grafana-server &
open http://localhost:3000/d/queue-dashboard
```

---

## Related Patterns

- [Resource Exhaustion](../../0-common/resource-exhaustion/) — Queues exhaust memory
- [Cascading Failure](../../0-common/cascading-failure/) — Queue overflow cascades
- [Retry Storms](../../0-common/retry-storms/) — Retries fill queues

---

## See Also

- [Glossary](../../../docs/GLOSSARY.md) — Queue, backpressure, consumer lag
- [References](../../../docs/REFERENCES.md) — Message queue and streaming patterns
