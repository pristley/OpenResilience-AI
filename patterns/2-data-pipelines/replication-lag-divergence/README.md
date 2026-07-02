# Pattern: Replication Lag Divergence

> When data replicated across regions/shards has different lag times, queries see inconsistent state: Same record has different values in different locations, causing split-brain scenarios and analytics divergence.

## Quick Summary

**Problem**: Replication lag varies by region/shard; primary updates before replicas; queries read different values from different replicas  
**Impact**: Inconsistent analytics (same metric different per region), split-brain decisions, failed joins  
**Detection Time**: Minutes (if monitored) to hours (if not)  
**Solution**: Bounded staleness, read-your-write consistency, consistent hashing, region-locked queries

---

## Problem Statement

Modern systems replicate data for availability and performance:
- Primary in US-East
- Replica 1 in US-West (cross-region)
- Replica 2 in EU-West
- Analytics queries read from replicas

Problem: Replication lag is not uniform. At T=0, all replicas are synced. At T=5s:
- US-East: Latest value (just updated)
- US-West: Lagging 2s (slight network delay)
- EU-West: Lagging 30s (high latency route)

Queries see different values depending on which replica they hit!

### Real Scenarios

**Scenario 1: Analytics Query Divergence**
- Metric: "Total revenue today"
- Query hits US-East replica: $1,000,000
- Query hits EU-West replica: $999,500 (30s out of sync)
- Report A (US-East): "Revenue is $1M"
- Report B (EU-West): "Revenue is $999.5K"
- Discrepancy: Reconciliation required, stakeholder confusion

**Scenario 2: Join on Misaligned Replicas**
- Query: "Orders with customer details" (join orders + customers)
- Order exists in all replicas (synced)
- Customer record only recently updated in primary
- Reads from US-East: Customer found (latest version)
- Reads from EU-West: Old customer version (30s lag)
- Join result: Different customer details depending on replica
- Report shows inconsistent customer info

**Scenario 3: A/B Test Split Results**
- Control group data on US-East replica
- Treatment group data on US-West replica
- Replication lag: US-West is 10s behind
- Results analysis: Treatment seems better, but was it just measuring different time windows?
- Decision made on bad data

**Scenario 4: Cascade Failure Due to Divergence**
- Primary fails unexpectedly
- Failover to "best" replica (EU-West, was most synced before failure)
- But EU-West was 60s behind primary
- Analytics suddenly jump backward: "Revenue decreased by $10K"
- Actually just reverted to stale state
- Decisions made based on wrong state

**Scenario 5: Cross-Shard Join Complexity**
- Data sharded by user_id
- Shard 1 has lag 2s
- Shard 2 has lag 8s
- Shard 3 has lag 1s
- Query joins across shards
- Results depend on timing of which shard's data arrives first
- Non-deterministic query results

---

## Why It Matters

### Impact Metrics

**Replication Divergence Cost:**
| Scenario | Cost | Duration |
|----------|------|----------|
| **Wrong decision from stale replica** | $10K-100K | Until corrected |
| **A/B test invalid** | $50K-500K | Lost experiment + re-test |
| **Cross-region analytics mismatch** | $5K-50K | Reconciliation required |
| **Failed failover** (using stale replica) | $100K-1M | Extended downtime |

---

## How It Fails

```
1. Primary database receives update
   ↓
2. Replication starts to all replicas
   ↓
3. Lag varies by region:
   - US-West: 2s lag
   - EU-West: 30s lag
   ↓
4. During lag window, queries see inconsistent data
   ↓
5. If queries read from different replicas, results diverge
   ↓
6. Analytics/decisions based on inconsistent data
```

### Observable Signals

```yaml
metrics:
  - name: "replication_lag_by_region"
    alert_threshold: "> 10 seconds for any region"
  
  - name: "max_lag_spread"
    definition: "max_lag - min_lag across replicas"
    alert_threshold: "> 30 seconds"
  
  - name: "query_result_divergence"
    definition: "Same query, different replicas, different results"
    alert_threshold: "> 0 divergence cases"
```

---

## Resilience Strategy

### Prevention

#### **1. Bounded Staleness**

```python
def query_with_bounded_staleness(query: str, max_lag_sec: int = 5):
    """Ensure query reads data no older than max_lag_sec."""
    
    # Check replication lag for each replica
    replicas = [
        {"name": "us-east", "lag": 1},
        {"name": "us-west", "lag": 3},
        {"name": "eu-west", "lag": 45},  # Too lagged!
    ]
    
    # Select only replicas within lag bound
    fresh_replicas = [
        r for r in replicas
        if r["lag"] <= max_lag_sec
    ]
    
    if not fresh_replicas:
        # Fall back to primary if all replicas too lagged
        print(f"⚠️ All replicas lagged > {max_lag_sec}s, reading from primary")
        return query_primary(query)
    
    # Round-robin among fresh replicas
    replica = random.choice(fresh_replicas)
    print(f"✅ Reading from {replica['name']} (lag: {replica['lag']}s)")
    return query_replica(query, replica["name"])
```

#### **2. Read-Your-Write Consistency**

```python
def query_with_read_after_write(user_id: str, query: str):
    """Ensure user sees their own writes immediately."""
    
    # Track which replica each user last wrote to
    user_write_version = get_user_write_version(user_id)
    
    # Only read from replicas that have caught up to that version
    
    # Check replica versions
    replica_versions = {
        "us-west": 1000,
        "eu-west": 995,  # Behind!
    }
    
    for replica, version in replica_versions.items():
        if version >= user_write_version:
            # This replica has the user's write
            print(f"✅ Reading from {replica} (has version {version})")
            return query_replica(query, replica)
    
    # No replica caught up yet, read from primary
    print("⚠️ No replica caught up to write, reading from primary")
    return query_primary(query)
```

#### **3. Region-Locked Queries**

```python
def query_in_region(region: str, query: str):
    """Execute query and all dependent queries in same region."""
    
    # Route to primary in that region
    # Then all reads hit local replicas (minimal lag)
    
    print(f"🔒 Locking query to region: {region}")
    
    # Execute in that region's database
    result = execute_in_region(query, region)
    
    return result
```

#### **4. Consistent Hashing + Version Tracking**

```python
def route_query_to_consistent_replica(data_id: str, query: str):
    """Route query for same data to same replica (consistent hashing)."""
    
    # Hash data_id to replica
    replica_name = hash_to_replica(data_id)
    
    print(f"✅ Routing query for {data_id} to {replica_name}")
    
    # Always query same replica for same data
    # Reduces divergence (same replica has same lag)
    
    return query_replica(query, replica_name)
```

---

### Detection

```yaml
monitoring:
  alerts:
    - name: ReplicationLagHigh
      metric: "replication_lag_by_region"
      threshold: "> 10 seconds"
      severity: "high"
    
    - name: LagSpreadWide
      metric: "max_lag - min_lag"
      threshold: "> 30 seconds"
      severity: "high"
      action: "Investigate replication network, may impact consistency"
    
    - name: QueryDivergence
      query: "Execute same query on multiple replicas, compare results"
      threshold: "Results differ"
      severity: "critical"
```

### Recovery

```python
def recover_from_divergence():
    # 1. Identify which replica is authoritative
    print("Determining authoritative replica...")
    
    # 2. Resync lagged replicas from authoritative
    print("Forcing resync of lagged replicas")
    
    # 3. Verify consistency
    print("Verifying all replicas now match")
    
    # 4. Rerun affected queries
    print("Rerunning analytics queries for correctness")
```

---

## References
- [Bounded Staleness](https://www.microsoft.com/en-us/research/publication/probabilistically-bounded-staleness-pbs-practical-probabilistic-consistency-guarantees-for-large-scale-distributed-databases/)
- [Replication Consistency Models](https://en.wikipedia.org/wiki/Consistency_model)
- [CRDT: Conflict-Free Replicated Data Types](https://crdt.tech/)
