# Pattern: Batch Job Timeout & Cascading Failures

> When long-running batch jobs timeout, cascading failures prevent recovery and data consistency.

## Problem Statement

**Batch job timeout** occurs when long-running jobs (data processing, exports, backups) exceed configured timeouts, causing:
- Job interruption mid-process
- Partial data corruption or inconsistency
- Resource locks held indefinitely
- Cascading failures in dependent jobs
- Retry storms triggered by timeouts

**Immediate impact**: Job timeout → partial state → dependent jobs fail → data pipeline stalls.

**Real-world example**:
- Daily data export job: configured timeout 1 hour
- Data volume grows 2x unexpectedly
- Job takes 90 minutes
- Timeout kills job after 60 minutes
- Job killed mid-export → corrupted output file
- Downstream analytics job tries to read corrupted file → fails
- Next day's export can't start (lock held) → data pipeline stalled

## Why It Matters

- **Data consistency**: Partial writes create corruption
- **Resource locks**: Timeouts don't release locks → deadlocks
- **Cascading failures**: One timeout cascades to dependent jobs
- **Silent failures**: Timeout doesn't always surface as error
- **Recovery complexity**: Manual intervention needed to clean up locks

---

## How It Fails

### Mechanism

1. Batch job starts (data export, backup, model training)
2. Data volume/complexity increases unexpectedly
3. Job takes longer than timeout
4. System kills job to prevent runaway processes
5. Job terminated mid-transaction
6. Partial state: some data written, some not
7. Resource locks held (file lock, database transaction, lock file)
8. Dependent jobs start, try to access resource, get locked
9. Dependent jobs timeout → cascade up

### Observable Signals

```yaml
metrics:
  - name: batch_job_duration
    pattern: Slowly increasing over time
    example: 30m → 40m → 50m → 60m (timeout!) → restart
  
  - name: batch_job_timeout_rate
    spike: Jobs timing out instead of completing
    example: 0% → 100% when data volume increases
  
  - name: job_processing_rate
    decrease: Drops as data volume increases
    example: 1000 records/sec → 500 records/sec (job slowing)
  
  - name: resource_lock_wait_time
    spike: Increases when locks held from timeouts
    indicates: Cascade effect
  
  - name: dependent_job_failure_rate
    spike: Increases when upstream job times out
    indicates: Cascade from timeout

logs:
  - "Job timeout after 3600s"
  - "Job terminated, cleaning up resources..."
  - "Lock file still present (stale lock?)"
  - "Cannot acquire lock: resource busy"
  - "Transaction rolled back due to timeout"
  - "Dependent job waiting for resource..."

traces:
  - trace_duration: Increases to exactly timeout value
  - lock_acquired_time: Shows how long lock is held
  - dependent_job_latency: Increases due to waiting for locks
```

### Time to Detect

- **Best case** (alerting on timeout rate): 1-2 minutes
- **Realistic** (next job fails, on-call notices): 5-30 minutes
- **Worst case** (data corruption discovered): hours to days

### Blast Radius

- **Direct**: Batch job fails
- **Cascading**: All dependent jobs blocked
- **Data**: Partial corruption in output
- **Scope**: Entire data pipeline affected

---

## Resilience Strategy

### Prevention

1. **Monitor job duration trends** (essential)
   - Track how long jobs take each run
   - Alert if trending up
   - Investigate before timeout hits
   - Why: Catch growth before timeout
   - Trade-off: Requires historical tracking

2. **Set generous timeouts** (essential)
   - Timeout = 95th percentile duration × 1.5-2x
   - Never timeout on p50 or p99
   - Review quarterly
   - Why: Prevents legitimate long-running jobs
   - Trade-off: Runaway jobs run longer

3. **Implement checkpoints** (important)
   - Save progress at intervals (every 10 minutes)
   - On restart: resume from last checkpoint
   - Why: Enables graceful restart
   - Trade-off: Adds complexity

4. **Resource cleanup on timeout** (important)
   - Release locks immediately
   - Rollback transactions
   - Delete partial output files
   - Why: Prevents cascade to dependent jobs
   - Trade-off: Requires explicit cleanup code

5. **Circuit breaker for cascading timeouts** (important)
   - If timeout rate > 10%: skip dependent jobs
   - Wait for manual investigation
   - Why: Stops cascade
   - Trade-off: Delays pipeline

### Detection

**Alerting:**

```yaml
alerts:
  - alert: BatchJobTimeout
    expr: batch_job_timeout_seconds > 3600
    for: 1m
    annotation: "Batch job exceeded 1 hour timeout"
  
  - alert: BatchJobDurationTrending
    expr: rate(batch_job_duration_seconds[5m]) > 600
    for: 10m
    annotation: "Batch job duration trending up (may hit timeout soon)"
  
  - alert: StaleJobLockFile
    expr: time() - stale_lock_file_age > 7200
    for: 5m
    annotation: "Lock file > 2 hours old (possible stale lock from timeout)"
  
  - alert: DependentJobBlocked
    expr: batch_job_wait_for_dependency_time > 300
    for: 2m
    annotation: "Batch job waiting > 5 min for dependency (cascade?)"
```

### Recovery

1. **Identify the timeout**: Which job? Which step?
2. **Clean up resources**: Release locks, delete partial files
3. **Root cause**: Why did it take so long? Data growth? Bad query?
4. **Fix**: Increase timeout, optimize job, add checkpoints
5. **Restart**: Resume from checkpoint or restart pipeline

---

## Chaos Experiment: Batch Job Timeout

```python
# experiments/traditional/batch-job-timeout/batch_timeout_test.py
import time
import signal
import tempfile
import os

JOB_TIMEOUT = 5  # seconds (short for test)
DATA_VOLUME = 1_000_000  # records
PROCESS_RATE = 100_000  # records/sec
CHECKPOINT_INTERVAL = 1  # second

class TimeoutError(Exception):
    pass

def timeout_handler(signum, frame):
    raise TimeoutError("Job timeout")

def batch_job_with_checkpoints(data_volume, process_rate, timeout):
    """
    Simulate batch job with checkpoints
    If timeout hits, should be resumable from checkpoint
    """
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(timeout)
    
    output_file = tempfile.NamedTemporaryFile(delete=False)
    checkpoint_file = tempfile.NamedTemporaryFile(delete=False)
    
    try:
        records_processed = 0
        start_time = time.time()
        
        while records_processed < data_volume:
            # Process batch
            batch_size = min(process_rate, data_volume - records_processed)
            time.sleep(batch_size / process_rate)  # Simulate processing
            records_processed += batch_size
            
            # Write checkpoint every CHECKPOINT_INTERVAL seconds
            if int(time.time() - start_time) % CHECKPOINT_INTERVAL == 0:
                with open(checkpoint_file.name, 'w') as f:
                    f.write(str(records_processed))
            
            # Write output
            output_file.write(f"record_{records_processed}\n".encode())
        
        signal.alarm(0)  # Cancel timeout
        return {"status": "completed", "records": records_processed}
    
    except TimeoutError:
        # Job timed out - read checkpoint to resume
        try:
            with open(checkpoint_file.name, 'r') as f:
                checkpoint = int(f.read())
            return {"status": "timeout", "checkpoint": checkpoint, "records": checkpoint}
        except:
            return {"status": "timeout", "checkpoint": 0, "records": 0}
    
    finally:
        signal.alarm(0)  # Ensure timeout is cleared
        os.unlink(output_file.name)
        os.unlink(checkpoint_file.name)

def test_batch_job_timeout():
    print("=" * 70)
    print("Batch Job Timeout Experiment")
    print("=" * 70)
    
    print(f"\n[Phase 1] Run job with timeout {JOB_TIMEOUT}s...")
    result1 = batch_job_with_checkpoints(DATA_VOLUME, PROCESS_RATE, JOB_TIMEOUT)
    print(f"  Result: {result1}")
    
    if result1["status"] == "timeout":
        print(f"  ✅ Job timed out at {result1['checkpoint']} records")
        print(f"\n[Phase 2] Resume from checkpoint...")
        
        # Resume with longer timeout
        timeout_needed = int((DATA_VOLUME - result1['checkpoint']) / PROCESS_RATE) + 2
        result2 = batch_job_with_checkpoints(DATA_VOLUME, PROCESS_RATE, timeout_needed)
        print(f"  Result: {result2}")
        
        if result2["status"] == "completed":
            print(f"  ✅ Job completed from checkpoint ({result2['records']} records)")
        else:
            print(f"  ❌ Job failed again")
    else:
        print(f"  Job completed: {result1['records']} records")

if __name__ == "__main__":
    test_batch_job_timeout()
```

---

## Lessons Learned

### Case Study: Daily Export Timeout Cascade

**Timeline**:
- Day 1: Export takes 45 min (timeout 60 min, OK)
- Day 2: Export takes 55 min (warning trend)
- Day 3: Export takes 65 min (TIMEOUT at 60 min)
- Day 3: Lock held → dependent analytics job waits
- Day 4: Both jobs skip (cascade)
- Day 5: 72 hours of data not exported

**Root cause**: No checkpoint system, database grew 2x

**Fix**: 
1. Added checkpoints every 5 min
2. Increased timeout to 90 min
3. Optimized slow query

### Key Takeaways

- Monitor duration trends (don't wait for timeout)
- Set generous timeouts (not p50)
- Implement checkpoints for resume-ability
- Clean up locks immediately on timeout
- Test timeout scenarios

---

## Tools & Setup

```bash
# Run experiment
python experiments/traditional/batch-job-timeout/batch_timeout_test.py

# Monitor job durations
prometheus -c observability/prometheus.yml &
grafana-server &
open http://localhost:3000/d/batch-jobs-dashboard
```

---

## Related Patterns

- [Resource Exhaustion](../../0-common/resource-exhaustion/) — Timeouts exhaust resources
- [Timeout Misalignment](../../0-common/timeout-misalignment/) — Cascading timeouts
- [Cascading Failure](../../0-common/cascading-failure/) — Batch timeouts cascade

---

## See Also

- [Glossary](../../../docs/GLOSSARY.md) — Timeout, checkpoint, cascade
- [References](../../../docs/REFERENCES.md) — Job scheduling and recovery patterns
