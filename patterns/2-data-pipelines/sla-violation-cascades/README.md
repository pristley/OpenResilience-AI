# Pattern: SLA Violation Cascades

> When one data pipeline misses its SLA (latency, availability, quality), dependent pipelines are starved of data, amplifying failures throughout the system.

## Quick Summary

**Problem**: Pipeline A misses SLA → Pipeline B has no input → Pipeline B misses SLA → cascades downstream  
**Impact**: Cascading failures across multiple systems, extended outage, business impact multiplied  
**Detection Time**: Cascade takes 5-30 minutes to propagate (not immediate)  
**Solution**: SLA enforcement, resource isolation (bulkheads), dependency management, fallback data

---

## Problem Statement

Modern data systems are DAGs (directed acyclic graphs):
- Pipeline A computes user features (SLA: 2 hours)
- Pipeline B uses features + orders to compute recommendations (SLA: 4 hours)
- Pipeline C publishes recommendations to API (SLA: 5 hours)
- User queries recommendations (SLA: 500ms)

If Pipeline A misses SLA:
- T=2h: Features should be ready. Are they? No, still computing.
- T=2:30h: Pipeline B starts, but has no input. What now?
  - Option A: Wait (blocks) → Pipeline B will miss its SLA
  - Option B: Use stale data → Recommendations poor
  - Option C: Skip → No recommendations available
- T=4h+: Pipeline B misses SLA because waited for A
- T=5h+: Pipeline C gets delayed, misses SLA
- T=now: User queries API, gets stale/missing recommendations, poor experience

One failure cascades through the entire system.

### Real Scenarios

**Scenario 1: Direct Cascade**
- Data source A → Aggregation B → ML Model C → Serving D
- A delays by 1 hour
- B waits for A (SLA target: 2 hours) → B finishes at 3 hours (SLA miss)
- C waits for B (SLA target: 1 hour) → C starts at 3 hours, finishes at 4 hours (SLA miss)
- D was supposed to serve at 4 hours, now ready at 4 hours (just barely)
- All downstream systems cascade delayed

**Scenario 2: Resource Contention**
- Pipeline A (high priority, critical) has SLA: 1 hour
- Pipeline B (low priority) has SLA: 4 hours
- Both compete for same cluster resources
- If A and B run simultaneously, both compete for compute
- Either A misses SLA (bad) or B gets starved (acceptable but still cascade)
- Downstream of B (even if less critical) still affected

**Scenario 3: Dependency Explosion**
- 20 data pipelines feed into ML feature store
- Feature store SLA: 2 hours
- If ANY of 20 pipelines are late, feature store misses SLA
- Probability of cascade: 1 - (1-P_late)^20 (high!)
- Example: If each pipeline has 99% on-time rate, feature store has ~18% on-time rate

**Scenario 4: Shared Infrastructure Failure**
- Pipelines A, B, C all depend on shared database
- Database slows down
- All three pipelines slow down
- All three miss SLA simultaneously (cascade amplified)
- But it looks like "our code is slow" not "database is slow"

**Scenario 5: Fallback Data Corruption**
- Pipeline A misses SLA
- Pipeline B switches to fallback (yesterday's data)
- Fallback is corrupted (not cleaned up)
- Pipeline B produces garbage based on corrupted fallback
- Quality degrades for all downstream

---

## Why It Matters

### Impact Metrics

**SLA Cascade Cost:**
| Depth | Probability of Cascade | Business Impact |
|-------|----------------------|------------------|
| **1 pipeline** | 1% miss → 1% cascade | Limited |
| **3 pipelines** | 1% each → 3% cascade | Noticeable |
| **5 pipelines** | 1% each → 5% cascade | Significant |
| **20 pipelines** | 1% each → 18% cascade | Critical |

**Cascade Amplification:**
- 1 hour delay in A → 1 hour delay in B → 1 hour delay in C → 3 hour total delay (compound!)
- Exponential effect on downstream systems

---

## How It Fails

```
1. Pipeline A misses SLA (any reason: slow, crashed, late input)
   ↓
2. Pipeline B (depends on A) waits for A's output
   ↓
3. B's SLA window closes before A finishes
   ↓
4. B is now behind schedule (SLA miss)
   ↓
5. Pipeline C (depends on B) waits for B's output
   ↓
6. C also misses SLA
   ↓
7. Cascade continues downstream
   ↓
8. Business impact multiplies (not just 1 failure, now N failures)
```

---

## Resilience Strategy

### Prevention

#### **1. Resource Isolation (Bulkheads)**

```python
# Separate resource pools for critical vs non-critical pipelines

critical_pipeline_config = {
    "cluster": "critical-pool",
    "cpu": 32,
    "memory": 128,
    "guaranteed_quota": True,  # Never starved
}

non_critical_pipeline_config = {
    "cluster": "shared-pool",
    "cpu": 8,
    "memory": 32,
    "guaranteed_quota": False,  # Can be preempted
}

# Kubernetes ResourceQuota example
resource_quota = {
    "apiVersion": "v1",
    "kind": "ResourceQuota",
    "metadata": {"name": "critical-quota"},
    "spec": {
        "hard": {
            "requests.cpu": "32",
            "requests.memory": "128Gi"
        },
        "scopeSelector": {
            "matchExpressions": [
                {"operator": "In", "scopeName": "PriorityClass", "values": ["critical"]}
            ]
        }
    }
}
```

#### **2. SLA-Aware Scheduling**

```python
def schedule_pipeline_with_sla(pipeline_name: str, sla_minutes: int, 
                              dependencies: list):
    """Schedule pipeline to meet SLA given dependencies."""
    
    # Calculate required start time
    required_finish = datetime.now() + timedelta(minutes=sla_minutes)
    pipeline_duration = get_pipeline_duration(pipeline_name)
    required_start = required_finish - pipeline_duration
    
    # Check if dependencies will be ready in time
    dependency_finish_times = {}
    for dep in dependencies:
        dep_duration = get_pipeline_duration(dep)
        dep_finish = datetime.now() + dep_duration
        dependency_finish_times[dep] = dep_finish
        
        if dep_finish > required_start:
            print(f"⚠️ Dependency {dep} may cause SLA miss")
            print(f"   {dep} finishes at {dep_finish}, need input by {required_start}")
            print(f"   Gap: {(dep_finish - required_start).total_seconds() / 60:.0f} minutes")
    
    # Take action
    latest_dependency_finish = max(dependency_finish_times.values())
    if latest_dependency_finish > required_start:
        # We'll miss SLA if we wait for dependencies
        print(f"🚨 ALERT: SLA miss likely for {pipeline_name}")
        # Option 1: Use fallback data
        # Option 2: Accelerate dependencies
        # Option 3: Reduce pipeline scope
    else:
        print(f"✅ Scheduling {pipeline_name} at {required_start}")
        schedule_job(pipeline_name, required_start)
```

#### **3. Fallback Data Management**

```python
class FallbackDataManager:
    """Manage fallback data for pipeline dependencies."""
    
    def __init__(self):
        self.fallback_cache = {}  # pipeline -> latest_good_data
    
    def get_data_with_fallback(self, pipeline_name: str, timeout_sec: int = 600):
        """Get pipeline data, fallback if timeout."""
        
        try:
            # Try to get fresh data
            data = wait_for_pipeline_output(pipeline_name, timeout=timeout_sec)
            
            # Cache as fallback for next time
            self.fallback_cache[pipeline_name] = {
                "data": data,
                "timestamp": datetime.now(),
                "is_fresh": True
            }
            
            return data
        
        except TimeoutError:
            print(f"⚠️ {pipeline_name} timeout, using fallback")
            
            # Use cached fallback
            if pipeline_name in self.fallback_cache:
                cached = self.fallback_cache[pipeline_name]
                age = (datetime.now() - cached["timestamp"]).total_seconds() / 3600
                
                print(f"   Using fallback from {age:.1f} hours ago")
                cached["is_fresh"] = False
                
                return cached["data"]
            else:
                print(f"   No fallback available, returning empty")
                return {}
```

#### **4. Dependency Monitoring & Alerting**

```yaml
monitoring:
  critical_slas:
    - name: "user_features_pipeline"
      sla_minutes: 120
      alert_threshold_minutes: 20  # Alert 20 min before SLA miss
    
    - name: "recommendations_pipeline"
      sla_minutes: 60
      dependencies: ["user_features_pipeline"]
      alert_threshold_minutes: 15
  
  alerts:
    - name: "SLAMissLikely"
      condition: "current_elapsed > (sla_target - alert_threshold)"
      severity: "high"
      action: "Escalate, prepare fallback, notify stakeholders"
    
    - name: "DependencyDelayed"
      condition: "dependency not ready by required_time"
      severity: "high"
      action: "Activate fallback, reduce scope, or skip dependent pipeline"
```

---

### Detection & Recovery

```python
def monitor_and_respond_to_sla_cascade():
    """Detect SLA violations and stop cascade."""
    
    while True:
        time.sleep(60)
        
        # Check each pipeline's SLA
        pipelines = get_all_pipelines()
        
        for pipeline in pipelines:
            sla_target = pipeline["sla_minutes"]
            current_duration = pipeline.get_current_duration_minutes()
            dependencies = pipeline.get_dependencies()
            
            # Check dependencies first
            for dep in dependencies:
                if dep.is_delayed():
                    print(f"🚨 Dependency {dep} delayed, activating fallback for {pipeline}")
                    fallback_mgr.activate_fallback_for(pipeline)
            
            # Check own SLA
            sla_buffer = 20  # minutes
            if current_duration > (sla_target - sla_buffer):
                print(f"⚠️ {pipeline} approaching SLA miss")
                
                # Take action
                if can_parallelize(pipeline):
                    print(f"   Parallelizing computation...")
                    scale_up_resources(pipeline)
                
                if can_reduce_scope(pipeline):
                    print(f"   Reducing scope (approximate results)...")
                    reduce_pipeline_scope(pipeline)
                
                if dependencies_not_ready(pipeline):
                    print(f"   Dependencies not ready, using fallback...")
                    fallback_mgr.activate_fallback_for(pipeline)
```

---

## Case Study: Streaming Analytics Platform - Cascade Failure

**Incident**: "All reports for 2 hours. What happened?"

**Root Cause**:
- Data ingest from Kafka (SLA: 5 min) → delayed 15 min
- 20 downstream aggregations dependent on ingest
- Each aggregation has SLA: 15 min
- When ingest is 15 min late, each aggregation becomes 15 min late
- Cascade: 5 levels × 15 min delay = 75 minutes total
- All reports missed SLA

**Prevention Implemented**:
1. ✅ Resource isolation (dedicate Kafka cluster)
2. ✅ SLA-aware scheduling
3. ✅ Fallback data caching (hourly snapshots)
4. ✅ Dependency-aware alerting
5. ✅ Reduced scope mode (when SLA at risk)

**Impact**: Reduced cascade failures by 95%, average SLA miss time from 90 min to < 5 min (when occurs).

---

## References
- [Bulkhead Pattern](https://docs.microsoft.com/en-us/azure/architecture/patterns/bulkhead)
- [Kubernetes Resource Quotas](https://kubernetes.io/docs/concepts/policy/resource-quotas/)
- [Priority-based Scheduling](https://kubernetes.io/docs/concepts/scheduling-eviction/pod-priority-preemption/)
