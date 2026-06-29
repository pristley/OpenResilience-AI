# Pattern Template

Copy this template when creating a new pattern. Fill in each section based on your learnings.

---

# Pattern: [Name]

## Problem Statement

What goes wrong? Describe a scenario where this failure occurs in real systems.

**Example:**
- Traditional: "API timeout cascades to dependent service, bringing down user-facing dashboard"
- AI/Data: "Model drift causes stale features in real-time inference, degrading recommendation quality"

---

## Why It Matters

Why should teams care about this pattern?

- **Impact metric**: What breaks? (e.g., "5% of inference requests fail")
- **Detection latency**: How fast can you spot it? (seconds/minutes/hours)
- **Blast radius**: How many users/systems affected?
- **Cost**: Economic impact (downtime, compute, manual work)

---

## How It Fails

### Mechanism

The physical chain of events:

1. First thing goes wrong
2. This causes second thing
3. Which triggers third thing
4. Until...

### Observable Signals

Metrics, logs, and traces to watch for:

- Metric: `error_rate` spikes above threshold
- Log: "Connection timeout" entries
- Trace: Request latency increases at specific service
- Anomaly: Unusual pattern detected by monitoring

### Time to Detect

- **Best case** (you know what to look for): X seconds
- **Realistic** (human review + alerting): Y minutes
- **Worst case** (user reports): Z hours

### Blast Radius

- **Direct**: What breaks immediately? (e.g., "API service becomes unresponsive")
- **Downstream**: What depends on it? (e.g., "Dashboard calls API, also fails")
- **Indirect**: What else breaks as a result? (e.g., "Monitoring system can't fetch metrics")
- **Scope**: How many users/systems affected?

---

## Resilience Strategy

### Prevention

How to avoid this failure:

- **Strategy 1**: Description + why it helps
- **Strategy 2**: Description + why it helps
- **Trade-offs**: What's the downside? (complexity, cost, latency?)

**Examples:**
- Add retry logic with exponential backoff
- Implement circuit breaker pattern
- Validate input before processing
- Separate resource pools (bulkhead)

### Detection

How to know it's happening:

- **Alerting**: What metric threshold should trigger alert?
- **Observability checklist**: 
  - [ ] Metric: _______
  - [ ] Log pattern: _______
  - [ ] Trace pattern: _______
  - [ ] Health check: _______

- **Detection latency goal**: Should detect within X seconds/minutes

**Example Prometheus alert:**
```yaml
alert: APILatencySpike
expr: histogram_quantile(0.95, api_request_duration) > 1000
for: 5m
```

### Recovery

How to restore normal operation:

- **Automatic**: What can the system do without human help?
  - Auto-rollback
  - Fail-over to replica
  - Shed load / degrade gracefully
  
- **Manual**: What should ops do?
  - Check logs for root cause
  - Kill misbehaving component
  - Restore from backup
  - Restart service

- **Timeline**: How long does each step take?

**Graceful degradation example:**
- If feature store is down, fall back to cached features
- If model is slow, serve stale prediction instead of timing out
- If recommendation engine fails, show popular items

---

## Chaos Experiment

Show how to safely trigger this failure to test your resilience strategy.

### Prerequisites

- Access to staging/test environment
- Observability setup (dashboards, alerts)
- Kill switch (way to stop the experiment)

### Setup

```bash
# Required setup steps
python install_dependencies.py
terraform apply -var="environment=staging"
```

### Running the Experiment

```python
# experiments/[category]/[pattern-name]/run.py
"""
Chaos experiment for [Pattern Name]
"""
import time
import logging

def inject_failure():
    """Inject the failure condition"""
    # Implementation here
    pass

def verify_detection():
    """Verify that system detects the failure"""
    # Check metrics, logs, alerts
    # Assert failure is detected within X seconds
    pass

def verify_recovery():
    """Verify that system recovers gracefully"""
    # Check if auto-recovery worked
    # Or if manual intervention succeeded
    pass

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    try:
        inject_failure()
        time.sleep(5)  # Let it propagate
        
        verify_detection()
        logging.info("✅ Failure detected as expected")
        
        verify_recovery()
        logging.info("✅ Recovery successful")
        
    except AssertionError as e:
        logging.error(f"❌ Experiment failed: {e}")
        raise
```

### Monitoring During Experiment

Watch these dashboards/metrics:

- Dashboard 1: [link to Grafana dashboard]
- Metric 1: `error_rate` should spike then recover
- Metric 2: `latency_p99` should increase then normalize
- Alert: `AlertName` should fire then clear

### Cleanup

```bash
# Restore system to baseline
terraform destroy
```

### Expected Outcome

- ✅ Failure is detected within 30 seconds
- ✅ System gracefully degrades (serves reduced functionality)
- ✅ Recovery completes within 5 minutes
- ✅ No data loss occurs

---

## Lessons Learned

### Real-World Examples

Have you seen this failure? What happened?

**Example incident:**
- **Timeline**: When did it happen? (date/time)
- **Root cause**: What actually failed?
- **Detection**: How fast was it spotted?
- **Impact**: How many users/systems affected?
- **Resolution**: What was the fix?
- **Duration**: MTTR (mean time to recovery)
- **Prevention**: How to avoid next time?

### Key Takeaways

- Lesson 1: _______
- Lesson 2: _______
- Lesson 3: _______

### Anti-Patterns

What NOT to do:

- ❌ Mistake 1: Why this doesn't work
- ❌ Mistake 2: Why this backfires

---

## Tools & Setup

### Specific Tools for This Pattern

- Tool 1: Why it helps (link)
- Tool 2: Configuration (link to example)

### Observability Setup

What monitoring/alerting needs to be in place?

**Prometheus:**
```yaml
# alerts.yaml
groups:
  - name: pattern_name
    rules:
      - alert: _______
        expr: _______
```

**Grafana:**
- Dashboard: [link or screenshot]
- Key panels: [list]

### Configuration

What needs to be configured in your system?

- Circuit breaker timeout: recommended value
- Retry policy: max retries, backoff
- Resource limits: bulkhead size
- Monitoring thresholds: alert triggers

---

## Related Patterns

What other patterns are related?

- [Pattern 1](../other-pattern/) — Why related
- [Pattern 2](../other-pattern/) — Why related

---

## References

### Academic Papers

- Title — Authors
  - [Link](https://example.com)
  - Key insight: _______

### Blog Posts

- Title — Author/Publication
  - [Link](https://example.com)
  - Practical takeaway: _______

### Tools & Documentation

- Tool Name — [Link](https://example.com)
  - How to use for this pattern: _______

### Talks

- "Talk Title" — Speaker, Conference/Year
  - [Video](https://example.com)
  - Key points: _______

---

## See Also

- [Glossary](../docs/GLOSSARY.md) — Terminology
- [Theory](../docs/THEORY.md) — Deeper concepts
- [Other patterns in this category](../patterns/)
