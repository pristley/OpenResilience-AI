# Pattern: Database Failover & Replica Lag

> When database fails over, replica lag and cascading timeouts cascade through the system.

## Problem Statement

**Database failover** occurs when the primary database fails and the system automatically switches to a replica. However:
- Replica lag causes reads to see stale data
- Application code expects strong consistency
- Failover takes 10-30 seconds (service down)
- Retries overwhelm the replica
- Cascading failures in dependent services

**Immediate impact**: Primary fails → 10s downtime → retries spike → replica gets hammered → cascade.

**Real-world example**:
- Primary database fails (disk full)
- Failover to replica (takes 20 seconds)
- Replica has 5-minute replication lag (stale data)
- Application expects fresh data → uses stale data → bugs
- User updates profile, read back stale profile (lost update)
- Retries spike during failover → replica gets overloaded
- Cascade to dependent services

## Why It Matters

- **Downtime**: Failover takes 10-30 seconds (unacceptable)
- **Data freshness**: Replication lag = stale reads
- **Consistency**: Strong consistency assumptions break
- **Lost updates**: Writes on failed primary not replicated
- **Cascading**: Stale reads cause bugs in downstream systems

---

## How It Fails

### Mechanism

1. Primary database fails (crash, disk full, network partition)
2. Health checks detect failure
3. Failover process starts (promote replica)
4. Failover takes 10-30 seconds → service down
5. Application retries start
6. Replica receives 10x traffic (all the retries)
7. Replica has 5-minute replication lag (stale data)
8. Reads return stale state
9. Application logic breaks (expects fresh data)

### Observable Signals

```yaml
metrics:
  - name: database_connection_errors
    spike: Increases from 0 to 100% during failover
    duration: 10-30 seconds
  
  - name: replication_lag_seconds
    spike: Increases to 300+ (5 minutes)
    indicates: Replica is far behind primary
  
  - name: application_error_rate
    spike: Increases during replication lag
    example: 0.1% → 10% (stale data causing bugs)
  
  - name: replica_query_latency
    spike: Increases as replay catches up
    example: 100ms → 5000ms
  
  - name: database_failover_duration
    metric: 10-30 seconds for automatic failover
  
  - name: lost_write_count
    pattern: Writes to failed primary not replicated
    indicates: Data loss on failover

logs:
  - "Primary database connection lost"
  - "Promoting replica to primary"
  - "Replica lag: 300 seconds"
  - "Writes lost: 1000 transactions"
  - "Connection: read from replica (may be stale)"

traces:
  - stale_read_detected: Query returns old data
  - write_loss_detected: Update didn't make it to replica
  - replication_catchup_time: Takes 5+ min to become current
```

### Time to Detect

- **Best case** (alerting on failed connection): 5-10 seconds
- **Realistic** (on-call sees spike): 20-60 seconds
- **Worst case** (customer reports data loss): 5+ minutes

### Blast Radius

- **Direct**: Database unavailable, reads stale data
- **Cascading**: Application logic breaks on stale data
- **Data loss**: Writes not replicated are lost
- **Scope**: Entire application affected

---

## Resilience Strategy

### Prevention

1. **Minimize replication lag** (essential)
   - Use synchronous replication (master waits for replica ACK)
   - Why: Ensures replica has latest writes
   - Trade-off: Slower writes (network latency)

2. **Faster failover** (essential)
   - Automated health checks (sub-second detection)
   - Automated promotion (no manual intervention)
   - Target: < 5 second failover
   - Why: Minimize downtime
   - Trade-off: Risk of false failovers

3. **Application-level consistency** (important)
   - Mark reads as "must be fresh" vs "stale OK"
   - Route fresh reads to primary
   - Route stale reads to replica
   - Why: Preserve consistency where needed
   - Trade-off: Application complexity

4. **Monitoring & alerting** (important)
   - Alert on replication lag > 1 second
   - Alert on failed replica
   - Alert on failover events
   - Why: Visibility into state
   - Trade-off: Alert fatigue if not tuned

5. **Circuit breaker for stale reads** (important)
   - If replica lag > 30s: fail reads instead of returning stale
   - Why: Prevent data corruption from stale reads
   - Trade-off: Some requests fail

### Detection

**Alerting:**

```yaml
alerts:
  - alert: ReplicationLagHigh
    expr: replication_lag_seconds > 5
    for: 1m
    annotation: "Replication lag > 5s (replica falling behind)"
  
  - alert: DatabaseFailoverDetected
    expr: database_role_change
    for: 10s
    annotation: "Database failover occurred (replica promoted)"
  
  - alert: PrimaryDatabaseDown
    expr: primary_database_up == 0
    for: 5s
    annotation: "Primary database unavailable"
  
  - alert: ApplicationReadStaleError
    expr: stale_read_consistency_violations > 10
    for: 1m
    annotation: "Application detecting stale reads (consistency broken)"
```

### Recovery

1. **During failover**: Accept stale reads temporarily
2. **Immediately**: Redirect traffic to replica
3. **Monitor**: Watch replication lag decrease
4. **Investigation**: Why did primary fail?
5. **Recovery**: Investigate failed primary, determine if salvageable
6. **Restore**: Bring primary back online (secondary position)

---

## Chaos Experiment: Database Failover

```python
# experiments/traditional/database-failover/failover_test.py
import psycopg2
import time
import threading
from datetime import datetime

PRIMARY_DB = "postgresql://user@primary:5432/test"
REPLICA_DB = "postgresql://user@replica:5432/test"
REPLICATION_LAG_CHECK_INTERVAL = 1  # second

def get_replication_lag(replica_conn):
    """Get current replication lag in seconds"""
    cursor = replica_conn.cursor()
    cursor.execute("""
        SELECT EXTRACT(EPOCH FROM (now() - pg_last_xact_replay_timestamp())) as lag
    """)
    lag = cursor.fetchone()[0] or 0
    cursor.close()
    return lag

def test_database_failover():
    print("=" * 70)
    print("Database Failover Experiment")
    print("=" * 70)
    
    primary = psycopg2.connect(PRIMARY_DB)
    replica = psycopg2.connect(REPLICA_DB)
    
    try:
        print("\n[Phase 1] Baseline - primary working...")
        cursor = primary.cursor()
        cursor.execute("INSERT INTO test_table VALUES ('baseline')")
        primary.commit()
        
        lag = get_replication_lag(replica)
        print(f"  Replication lag: {lag:.2f}s")
        assert lag < 1, "Baseline lag should be < 1s"
        print("  ✅ Baseline OK")
        
        print("\n[Phase 2] Simulate primary failure...")
        print("  (In real scenario: primary database goes down)")
        # In real test: disconnect from primary
        
        print("\n[Phase 3] Failover to replica...")
        failover_start = time.time()
        # Simulate detection + promotion delay
        time.sleep(5)  # Health check + promotion time
        failover_duration = time.time() - failover_start
        print(f"  Failover took {failover_duration:.1f}s")
        
        print("\n[Phase 4] Monitor replica lag during catch-up...")
        for i in range(10):
            lag = get_replication_lag(replica)
            print(f"  [{i}] Replication lag: {lag:.2f}s")
            time.sleep(1)
        
        print("\n[Phase 5] Verify data consistency...")
        replica_cursor = replica.cursor()
        replica_cursor.execute("SELECT * FROM test_table WHERE value = 'baseline'")
        row = replica_cursor.fetchone()
        assert row is not None, "Data from primary should be on replica"
        print("  ✅ Data replicated successfully")
        
    finally:
        primary.close()
        replica.close()

if __name__ == "__main__":
    test_database_failover()
```

---

## Lessons Learned

### Case Study: PayPal Database Failover

**Timeline**:
- Primary DB crashes
- Health check detects (2 seconds)
- Failover starts (5 seconds)
- Replica lag: 30 seconds
- Writes not replicated are lost
- Application sees stale account balances
- Customers report inconsistencies

**Root cause**: Async replication + writes not replicated

**Fix**: 
1. Switch to synchronous replication
2. Reduce failover time (< 2 seconds)
3. Application-level consistency marking

### Key Takeaways

- Minimize replication lag (sync replication)
- Automate failover (sub-5 second)
- Monitor lag continuously
- Application must handle stale reads
- Circuit breaker on high lag

---

## Tools & Setup

```bash
# Monitor replication
psql -c "SELECT now() - pg_last_xact_replay_timestamp() as lag;"

# Run experiment
python experiments/traditional/database-failover/failover_test.py

# Monitor failover
prometheus -c observability/prometheus.yml &
grafana-server &
open http://localhost:3000/d/database-failover-dashboard
```

---

## Related Patterns

- [Resource Exhaustion](../../0-common/resource-exhaustion/) — Failover exhausts resources
- [Cascading Failure](../../0-common/cascading-failure/) — Failover cascades
- [Timeout Misalignment](../../0-common/timeout-misalignment/) — Failover causes timeouts

---

## See Also

- [Glossary](../../../docs/GLOSSARY.md) — Failover, replication lag, consistency
- [References](../../../docs/REFERENCES.md) — Database resilience patterns
