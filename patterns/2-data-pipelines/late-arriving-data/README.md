# Pattern: Late-Arriving Data

> Data arrives after processing windows close or SLAs expire, causing incomplete results, missing records in analysis, and wrong decision-making on incomplete information.

## Quick Summary

**Problem**: Expected data arrives too late (after window closed, after model ran, after report generated)  
**Impact**: Incomplete results, missing records, wrong decisions based on partial data, reconciliation required  
**Detection Time**: Minutes to hours (depends on window boundaries)  
**Solution**: Windowing strategies (tumbling/sliding/session), late data handling policies, watermarks, allowed lateness, restatement mechanisms

---

## Problem Statement

Data pipelines operate on time windows: "Give me all orders from 00:00-01:00", "Compute daily features from yesterday's data". But real-world data doesn't arrive perfectly on time. Network delays, upstream job failures, and clock skew cause data to trickle in late. If your pipeline discards it, results are incomplete. If you reprocess, you waste compute.

### Real Scenarios

**Scenario 1: Mobile App Events Late Arrival**
- Mobile app queues events when offline, syncs when online
- User's purchase event should arrive at 15:00 UTC
- Network is slow, event arrives at 15:47 UTC (47 minutes late)
- Hourly aggregation already ran at 15:05 UTC
- Metrics: "Orders in hour 15:00-16:00" are missing this order
- Report shows 99 orders when actually 100
- Finance reconciliation fails: "Why are revenue numbers different?"

**Scenario 2: Batch Data Late from Upstream System**
- Depends on upstream Hadoop job that processes at 23:00 UTC
- Job runs successfully but takes 4 hours instead of 2 hours
- Downstream job expected the data at 02:00 UTC, started processing
- Data finally arrives at 04:30 UTC
- Downstream job already finished with incomplete data
- Daily report published at 06:00 UTC with partial data
- Corrections published at 14:00 UTC: "Data was incomplete, actual numbers different"

**Scenario 3: Database Replication Lag**
- Analytics DB is a replica of transactional DB
- Replication lag: 2-3 minutes normally
- Spike in transaction volume, replication falls behind: 15 minute lag
- Analytics query runs at 10:15 UTC but replica is at 10:00 UTC state
- Query results are 15 minutes stale
- ML model trained on stale data (yesterday's "today" feature is 1 day + 15 min old)

**Scenario 4: Time Zone / Clock Skew Issues**
- Client sends event timestamp without UTC conversion
- Event generated in PST (14:00 PST = 22:00 UTC)
- Client code has bug, sends local time (14:00) without timezone info
- Pipeline assumes UTC, buckets into wrong hour: 14:00 UTC instead of 22:00 UTC
- Event appears "8 hours early" relative to real time
- Hourly bucket gets event before window actually opens
- Result: Event counts are wrong (hour 14 gets morning events, hour 22 missing evening events)

**Scenario 5: Out-of-Order Arrival with Status Updates**
- Event sequence: Order created → Paid → Shipped
- Normal: Events arrive in order within 1 second
- Late arrival: Shipped event arrives 6 hours late
- Timeline: Create (10:00) + Paid (10:01) process, then Shipped (16:01) arrives
- Window 10:00-11:00 already closed
- System thinks order is Paid but never Shipped → wrong inventory tracking
- Actual state: Order is Shipped (the late Shipped event is the truth)

**Scenario 6: Multi-Source Join with Misaligned Arrivals**
- Need to join orders (arrives fast) with payments (arrives slow)
- Join window: 10:00-11:00 UTC, close at 11:01 UTC
- Order arrives at 10:30, immediately joined with payment
- Payment arrives at 11:05 (4 minutes too late)
- Result: Order in final output WITHOUT payment info (incomplete join)
- Downstream system thinks order has no payment → tries to collect payment again (duplicate charge)

---

## Why It Matters

### Impact Metrics

**Late Data Cost:**
| Scenario | Cost per Minute | Duration | Total Impact |
|----------|-----------------|----------|--------------|
| **Incomplete hourly report** | $1K-10K | 1-6 hours | Wrong decisions, reconciliation |
| **Duplicate charges** (order-payment join failed) | $10K-100K | 1-24 hours | Customer churn, refunds |
| **Stale analytics DB** | $5K-50K | per hour | Bad ML models trained |
| **Wrong time buckets** (timezone bug) | $50K-500K | 1-3 days | Systematic undercounting |

**Blast Radius:**
- **Direct**: Reports incomplete, need restatement
- **Cascading**: Dependent analyses/models use incomplete data
- **Business**: Decisions made on incomplete information
- **Compliance**: Audit trails show incomplete data as "final"

### Detection Latency

- **Best case** (real-time watermark monitoring): **30 seconds to 2 minutes**
  - "Alert: Watermark not advancing, likely late data backlog"
  
- **Realistic** (periodic completeness checks): **10-30 minutes**
  - "Morning report shows 5% fewer records than expected"
  
- **Worst case** (user discovers during reconciliation): **Hours to days**
  - "Finance: Our daily reconciliation doesn't match"

---

## How It Fails

### Mechanism

```
1. Data source generates event with timestamp T
   ↓

2. Event network delay / queuing / buffering
   Time: T + delta (delta = 5 min, 1 hour, etc)
   ↓

3. Data arrives at pipeline processing window at time Now
   ↓

4. Pipeline checks: "Is T within my current window?"
   
   Option A (Rigid window): "No, window closed 10 min ago, DISCARD"
     → Result: Incomplete counts/aggregations
   
   Option B (No limit): "Accept all data"
     → Result: Need to constantly recompute, latency spikes
   
   Option C (Allowed lateness): "Yes, up to 15 min late, accept"
     → Result: Emit correction/restatement after watermark moves
   
   ↓

5. Decision: Discard vs. Accept vs. Buffer
   ↓

6. Cascading failures:
   - Incomplete results published
   - Dependent systems use incomplete data
   - Reconciliation discovered the issue (hours later)
   - Correction/restatement required
   - Uncertainty: Is this the "final" answer or will it change again?
```

### Observable Signals

#### **Metrics to Monitor**

```yaml
late_data_metrics:
  
  # 1. Arrival Latency
  - name: "data_arrival_latency"
    definition: "now() - event_timestamp"
    alert_threshold: "> expected_latency * 2"
    acceptable_by_source:
      mobile_events: "< 5 minutes"
      batch_hadoop: "< 2 hours"
      database_replication: "< 5 minutes"
      api_webhooks: "< 30 seconds"
  
  - name: "p95_arrival_latency"
    definition: "95th percentile of (arrival_time - event_time)"
    alert_threshold: "> 30 minutes"
  
  # 2. Completeness Over Time
  - name: "pct_records_received_by_time_window"
    definition: "count(records in window W) at times [0min, 5min, 15min, 1hour, 24hour]"
    alert_threshold: "Expected growth curve broken"
    
  - name: "missing_records_after_window_close"
    definition: "count(records arriving after window closed)"
    alert_threshold: "> 5% of normal volume"
  
  # 3. Watermark Movement
  - name: "event_time_watermark"
    definition: "max(event_timestamp) that pipeline has seen"
    alert_threshold: "Not advancing (stuck)"
    
  - name: "watermark_lag"
    definition: "now() - event_time_watermark"
    alert_threshold: "> SLA threshold"
  
  # 4. Restatements
  - name: "count_of_corrections_issued"
    definition: "count of times aggregation was corrected"
    alert_threshold: "> 2 per day"
  
  - name: "magnitude_of_corrections"
    definition: "max((original_value - corrected_value) / original_value)"
    alert_threshold: "> 5%"
  
  # 5. Time Skew
  - name: "event_timestamp_vs_arrival_time_drift"
    definition: "events where (arrival_time - event_time) < 0 (clock skew)"
    alert_threshold: "> 0%"
  
  - name: "out_of_order_event_rate"
    definition: "count(events arriving out of sequence) / total events"
    alert_threshold: "> 1%"
  
  # 6. Join Incompleteness
  - name: "join_record_count_variance"
    definition: "actual_joined_records vs expected"
    alert_threshold: "< 95%"
  
  - name: "join_timeout_rate"
    definition: "% of records that exit join before match arrives"
    alert_threshold: "> 2%"
```

#### **Log Patterns**

```
[WARN]  Late-arriving event: event_timestamp=10:00:00, arrival_time=10:47:32 (47m late)
[WARN]  Out-of-order event: event_id=123 arrived after newer event_id=456
[WARN]  Time skew detected: event_timestamp > arrival_time (clock not synced)
[WARN]  Watermark stalled: Not advanced in 30 minutes (backlog detected)
[ERROR] Dropped late event: timestamp=10:00:00, window=10:00-11:00, now=11:05 (5m late, exceeds grace period)
[WARN]  Restatement issued: Hour 15 record count changed from 1000 to 1015 (1.5% correction)
[ERROR] Join timeout: Order event without payment after 5 min grace period
```

#### **Trace Patterns**

```
Trace: hourly_order_aggregation
├─ [OK] Process events for window 10:00-11:00
│  ├─ [OK] Received 1000 events on time
│  └─ [OK] Emit result: count=1000 at 11:01
├─ [OK] Grace period: 11:01-11:05 (allow 4 min late events)
│  ├─ [OK] Received 12 late events
│  └─ [RESTATEMENT] Emit correction: count=1012 (change: +12, +1.2%)
├─ [OK] Grace period closed at 11:05
│  └─ [BLOCK] Drop all further events for window 10:00-11:00
└─ [END] Final result: 1012 orders

Trace: order_payment_join
├─ [OK] Received order at 10:30:15
│  └─ Feature extracted: order_id=123
├─ [JOIN_WAIT] Looking for payment matching order_id=123
│  └─ Grace period: 5 minutes (until 10:35:15)
├─ [TIMEOUT] Payment not received before grace period closed
│  └─ Join timeout at 10:35:15 (payment never arrived)
├─ [OK] Emit incomplete join at 10:35:15
│  └─ Result: {order_id=123, payment=NULL} ← WRONG!
├─ [LATE] Payment arrives at 10:37:45 (2m30s late)
│  └─ Too late, join already emitted, payment is ignored
└─ [END] Final result: order without payment (should have payment)

Trace: timezone_bug
├─ [OK] Mobile app generates event at 14:00 PST
│  └─ Unix timestamp: 2025-06-15 22:00:00 UTC
├─ [BUG] App sends: {timestamp: "14:00", timezone: null}
│  └─ App forgot to convert to UTC
├─ [PARSE] Pipeline parses timestamp as UTC: 14:00:00 UTC
│  └─ Actual: 14:00 UTC instead of 22:00 UTC (8 hours off)
├─ [BUCKET] Event goes to hour bucket: 14:00-15:00 UTC
│  └─ Should go to: 22:00-23:00 UTC
└─ [END] Event in wrong time bucket (8 hour discrepancy)
```

#### **Health Checks (Real-Time)**

```yaml
health_checks:
  - check: "Watermark advancing"
    query: "SELECT MAX(event_time_watermark) from metrics"
    acceptable: "Advancing by at least 1s every 10 seconds"
    frequency: "every 10 seconds"
  
  - check: "Late arrival rate"
    query: "SELECT COUNT(*) WHERE (arrival_time - event_time) > SLA / COUNT(*)"
    acceptable: "< 2%"
    frequency: "every minute"
  
  - check: "Data completeness after window"
    query: "SELECT COUNT(*) in hourly window at times [T+5min, T+30min, T+24hr]"
    acceptable: "Growth curve expected (75% by 5min, 95% by 30min, 99.9% by 24hr)"
    frequency: "hourly"
  
  - check: "Clock skew detection"
    query: "SELECT COUNT(*) WHERE event_timestamp > NOW() (future events)"
    acceptable: "< 0.1%"
    frequency: "every minute"
  
  - check: "Out-of-order event rate"
    query: "Events not in monotonically increasing timestamp order"
    acceptable: "< 1%"
    frequency: "every 5 minutes"
```

### Time to Detect

- **Best case** (automated watermark + completeness monitoring): **1-5 minutes**
  - "Alert: Watermark stalled for 5 minutes, likely late data backlog"
  
- **Realistic** (periodic data completeness audit): **30 minutes to 2 hours**
  - "Morning audit: Yesterday's data is 5% incomplete, likely late arrivals"
  
- **Worst case** (finance reconciliation): **1-3 days**
  - "Monthly reconciliation: Revenue is $1.5M less, where's the missing data?"

### Blast Radius

- **Direct**: Results for affected time window(s) incomplete
- **Scope**: Could affect 1 window (1 hour) to multiple windows (days)
- **Cascading**: Dependent analyses/models use incomplete data
- **Duration**: Until restatement issued and republished (could be days)
- **Severity**: Medium to high (depending on business impact)

---

## Resilience Strategy

### Prevention

#### **1. Watermarking & Windowing Strategy**

```python
# pipeline/windowing_strategy.py
from typing import List, Tuple
from datetime import datetime, timedelta
import enum

class WindowType(enum.Enum):
    TUMBLING = "tumbling"      # Fixed, non-overlapping
    SLIDING = "sliding"        # Overlapping windows
    SESSION = "session"        # Event-driven, close on inactivity
    GLOBAL = "global"          # No windowing, all data

class LatenessPolicy(enum.Enum):
    DISCARD = "discard"        # Drop late data
    ACCUMULATE = "accumulate"  # Buffer and recompute
    ALLOWED_LATENESS = "allowed_lateness"  # Allow grace period

class WindowingStrategy:
    """Define windowing and lateness handling."""
    
    def __init__(self,
                 window_type: WindowType,
                 window_size_sec: int,
                 allowed_lateness_sec: int = 0,
                 laten_emit_trigger: bool = False):
        self.window_type = window_type
        self.window_size = timedelta(seconds=window_size_sec)
        self.allowed_lateness = timedelta(seconds=allowed_lateness_sec)
        self.on_late_emit = laten_emit_trigger
    
    def assign_window(self, event_timestamp: datetime) -> List[Tuple[datetime, datetime]]:
        """Assign event to window(s) based on event timestamp."""
        
        if self.window_type == WindowType.TUMBLING:
            # Each event goes to exactly one window
            window_start = (event_timestamp.replace(second=0, microsecond=0) 
                           - timedelta(seconds=event_timestamp.second))
            window_end = window_start + self.window_size
            return [(window_start, window_end)]
        
        elif self.window_type == WindowType.SLIDING:
            # Event may belong to multiple overlapping windows
            windows = []
            # Sliding window, e.g., every 10 sec, window size 60 sec
            window_start = event_timestamp.replace(microsecond=0)
            for i in range(int(self.window_size.total_seconds() / 10)):
                ws = window_start - timedelta(seconds=i*10)
                we = ws + self.window_size
                if ws <= event_timestamp < we:
                    windows.append((ws, we))
            return windows
        
        else:
            return []
    
    def is_on_time(self, event_timestamp: datetime, 
                  window_close_time: datetime) -> bool:
        """Check if event is on time relative to window close."""
        return event_timestamp <= window_close_time
    
    def is_allowed_late(self, event_timestamp: datetime, 
                       window_close_time: datetime) -> bool:
        """Check if late event is within allowed lateness grace period."""
        time_since_close = datetime.now() - window_close_time
        time_before_emit = self.allowed_lateness - time_since_close
        
        return time_before_emit > timedelta(0)
    
    def should_emit_result(self, event_arrival: datetime, 
                          window_close: datetime,
                          is_late_event: bool) -> bool:
        """Decide when to emit aggregation result."""
        
        if not is_late_event:
            # On-time event: emit after window closes
            return datetime.now() >= window_close
        
        else:
            # Late event: decide based on policy
            if self.on_late_emit:
                # Emit update immediately (causes restatement)
                return True
            else:
                # Suppress updates to avoid frequent restates
                return False

class WatermarkTracker:
    """Track event-time watermark (how far we've processed)."""
    
    def __init__(self, name: str, max_late_sec: int = 3600):
        self.name = name
        self.watermark = datetime.now() - timedelta(seconds=max_late_sec)
        self.max_late = timedelta(seconds=max_late_sec)
        self.history = []
    
    def update(self, event_timestamp: datetime):
        """Update watermark based on new event."""
        if event_timestamp > self.watermark:
            old_watermark = self.watermark
            self.watermark = event_timestamp - self.max_late
            
            age_sec = (datetime.now() - self.watermark).total_seconds()
            print(f"✅ Watermark updated: {self.watermark} (age: {age_sec:.0f}s)")
            
            self.history.append({
                "old": old_watermark,
                "new": self.watermark,
                "timestamp": datetime.now()
            })
    
    def is_dropped(self, event_timestamp: datetime) -> bool:
        """Check if event is too late (older than watermark)."""
        return event_timestamp < self.watermark
    
    def get_lag_sec(self) -> float:
        """How far behind real time is the watermark?"""
        return (datetime.now() - self.watermark).total_seconds()
    
    def get_status(self) -> dict:
        """Monitor watermark health."""
        return {
            "current_watermark": self.watermark,
            "lag_seconds": self.get_lag_sec(),
            "max_allowed_lateness": self.max_late.total_seconds(),
            "is_advancing": len(self.history) > 1 and self.history[-1]["new"] > self.history[-2]["new"]
        }
```

#### **2. Handling Late Data with Restatements**

```python
# pipeline/late_data_handler.py
from typing import Dict, Any, List
from datetime import datetime, timedelta
import json

class AggregationBuffer:
    """Buffer aggregations to handle late-arriving data."""
    
    def __init__(self, restatement_policy: str = "none"):
        """
        restatement_policy: 
            "none" = discard late data
            "update" = emit update immediately (frequent restates)
            "collect" = collect updates, emit once after grace period
        """
        self.policy = restatement_policy
        self.windows: Dict[Tuple, Dict] = {}  # window_key -> {aggregation, metadata}
    
    def add_to_aggregation(self, window_key: Tuple, 
                          event: Dict, is_late: bool = False) -> Dict:
        """Add event to window aggregation."""
        
        if window_key not in self.windows:
            self.windows[window_key] = {
                "value": 0,
                "count": 0,
                "on_time_count": 0,
                "late_count": 0,
                "created_at": datetime.now(),
                "emit_count": 0,
                "restatements": []
            }
        
        # Update aggregation
        old_value = self.windows[window_key]["value"]
        self.windows[window_key]["value"] += event.get("amount", 0)
        self.windows[window_key]["count"] += 1
        
        if is_late:
            self.windows[window_key]["late_count"] += 1
        else:
            self.windows[window_key]["on_time_count"] += 1
        
        # Decide if we should emit update
        should_emit_update = False
        restatement = None
        
        if is_late and self.policy == "update":
            # Immediate emission for every late event (causes frequent restates)
            should_emit_update = True
            restatement = {
                "timestamp": datetime.now(),
                "old_value": old_value,
                "new_value": self.windows[window_key]["value"],
                "change": self.windows[window_key]["value"] - old_value,
                "change_pct": (self.windows[window_key]["value"] - old_value) / max(old_value, 1),
                "reason": "Late event"
            }
            self.windows[window_key]["restatements"].append(restatement)
            self.windows[window_key]["emit_count"] += 1
            
            print(f"⚠️ Restatement for {window_key}: {old_value} → {self.windows[window_key]['value']} ({restatement['change_pct']:+.1%})")
        
        return {
            "should_emit": should_emit_update,
            "is_restatement": restatement is not None,
            "restatement": restatement
        }
    
    def finalize_aggregation(self, window_key: Tuple) -> Dict:
        """Finalize aggregation after grace period closed."""
        
        agg = self.windows[window_key]
        
        # Count on-time vs late
        total_count = agg["count"]
        on_time_pct = agg["on_time_count"] / max(total_count, 1)
        late_pct = agg["late_count"] / max(total_count, 1)
        
        return {
            "window": window_key,
            "final_value": agg["value"],
            "total_records": total_count,
            "on_time_records": agg["on_time_count"],
            "late_records": agg["late_count"],
            "completeness_pct": on_time_pct,
            "late_arrivals_pct": late_pct,
            "emit_count": agg["emit_count"],
            "restatement_count": len(agg["restatements"]),
            "restatements": agg["restatements"]
        }

class EarlyAndLateResults:
    """Emit results early (incomplete) and late (complete)."""
    
    def __init__(self, grace_period_sec: int = 600):
        self.grace_period = timedelta(seconds=grace_period_sec)
        self.emitted_early = {}
        self.final_results = {}
    
    def emit_early_result(self, window_key: Tuple, value: Dict) -> Dict:
        """Emit early result (before grace period, incomplete)."""
        
        print(f"📊 EARLY RESULT (incomplete): {window_key} = {value}")
        
        self.emitted_early[window_key] = {
            "value": value,
            "timestamp": datetime.now(),
            "status": "provisional"
        }
        
        return {
            "window": window_key,
            "value": value,
            "status": "provisional",
            "note": "Data may be incomplete, final result to follow"
        }
    
    def emit_final_result(self, window_key: Tuple, value: Dict,
                         early_value: Dict = None) -> Dict:
        """Emit final result after grace period."""
        
        if early_value and early_value != value:
            change = value - early_value
            change_pct = change / max(early_value, 1)
            print(f"📊 FINAL RESULT (restatement): {window_key} = {value} (was {early_value}, change: {change_pct:+.1%})")
        else:
            print(f"📊 FINAL RESULT: {window_key} = {value}")
        
        self.final_results[window_key] = {
            "value": value,
            "timestamp": datetime.now(),
            "status": "final"
        }
        
        return {
            "window": window_key,
            "value": value,
            "status": "final",
            "is_restatement": early_value is not None and early_value != value
        }
```

#### **3. Join with Side Inputs / Temporal Joins**

```python
# pipeline/temporal_joins.py
from typing import Dict, List, Optional
from datetime import datetime, timedelta

class TemporalJoinBuffer:
    """Buffer for temporal joins handling late arrivals."""
    
    def __init__(self, ttl_sec: int = 3600, grace_period_sec: int = 300):
        self.ttl = timedelta(seconds=ttl_sec)
        self.grace_period = timedelta(seconds=grace_period_sec)
        self.left_buffer: Dict = {}    # user_id -> {events, last_join_attempt}
        self.right_buffer: Dict = {}   # user_id -> {events, last_join_attempt}
    
    def join_left_stream(self, left_event: Dict, left_key: str):
        """Process left stream event (e.g., order)."""
        
        key = left_event[left_key]
        
        if key not in self.left_buffer:
            self.left_buffer[key] = {
                "events": [],
                "join_attempts": []
            }
        
        self.left_buffer[key]["events"].append({
            "event": left_event,
            "arrival_time": datetime.now()
        })
        
        # Try to join with buffered right events
        matched = False
        for i, right_entry in enumerate(self.right_buffer.get(key, {}).get("events", [])):
            # Temporal condition: right event should be close to left event
            time_diff = abs((right_entry["arrival_time"] - left_event.get("timestamp", datetime.now())).total_seconds())
            
            if time_diff < 30:  # Within 30 seconds
                # Join successful
                result = {
                    "left": left_event,
                    "right": right_entry["event"],
                    "join_time": datetime.now()
                }
                matched = True
                self.left_buffer[key]["join_attempts"].append({
                    "status": "matched",
                    "timestamp": datetime.now()
                })
                return result
        
        if not matched:
            # Unmatched left event, store and wait for right
            self.left_buffer[key]["join_attempts"].append({
                "status": "waiting",
                "timestamp": datetime.now()
            })
        
        return None
    
    def join_right_stream(self, right_event: Dict, right_key: str):
        """Process right stream event (e.g., payment)."""
        
        key = right_event[right_key]
        
        if key not in self.right_buffer:
            self.right_buffer[key] = {
                "events": [],
                "join_attempts": []
            }
        
        self.right_buffer[key]["events"].append({
            "event": right_event,
            "arrival_time": datetime.now()
        })
        
        # Try to join with buffered left events
        results = []
        for left_entry in self.left_buffer.get(key, {}).get("events", []):
            time_diff = abs((left_entry["arrival_time"] - right_event.get("timestamp", datetime.now())).total_seconds())
            
            if time_diff < 30:
                result = {
                    "left": left_entry["event"],
                    "right": right_event,
                    "join_time": datetime.now()
                }
                results.append(result)
                self.right_buffer[key]["join_attempts"].append({
                    "status": "matched",
                    "timestamp": datetime.now()
                })
        
        if not results:
            self.right_buffer[key]["join_attempts"].append({
                "status": "waiting",
                "timestamp": datetime.now()
            })
        
        return results
    
    def expire_old_events(self):
        """Remove stale buffered events."""
        
        now = datetime.now()
        
        for key in list(self.left_buffer.keys()):
            self.left_buffer[key]["events"] = [
                e for e in self.left_buffer[key]["events"]
                if now - e["arrival_time"] < self.ttl
            ]
            
            if not self.left_buffer[key]["events"]:
                del self.left_buffer[key]
        
        for key in list(self.right_buffer.keys()):
            self.right_buffer[key]["events"] = [
                e for e in self.right_buffer[key]["events"]
                if now - e["arrival_time"] < self.ttl
            ]
            
            if not self.right_buffer[key]["events"]:
                del self.right_buffer[key]

```

#### **4. Detecting and Fixing Time Skew**

```python
# pipeline/timezone_skew_detection.py
from datetime import datetime, timezone, timedelta
import pytz

class TimeSkewDetector:
    """Detect and correct timezone/clock skew issues."""
    
    def __init__(self, expected_timezone: str = "UTC"):
        self.expected_tz = pytz.timezone(expected_timezone)
        self.skew_samples = []
    
    def detect_skew(self, event_timestamp, arrival_time: datetime) -> dict:
        """Detect if event timestamp looks wrong."""
        
        # Calculate drift (arrival - event time)
        if isinstance(event_timestamp, str):
            try:
                event_dt = datetime.fromisoformat(event_timestamp)
            except:
                return {"skew": None, "likely_skew": False}
        else:
            event_dt = event_timestamp
        
        # Ensure both are timezone-aware
        if event_dt.tzinfo is None:
            event_dt = event_dt.replace(tzinfo=timezone.utc)
        if arrival_time.tzinfo is None:
            arrival_time = arrival_time.replace(tzinfo=timezone.utc)
        
        drift_sec = (arrival_time - event_dt).total_seconds()
        
        # Record sample
        self.skew_samples.append(drift_sec)
        if len(self.skew_samples) > 10000:
            self.skew_samples = self.skew_samples[-10000:]
        
        # Detect patterns
        import statistics
        median_drift = statistics.median(self.skew_samples[-100:]) if len(self.skew_samples) >= 100 else drift_sec
        
        analysis = {
            "drift_seconds": drift_sec,
            "median_drift": median_drift,
            "likely_future_event": drift_sec < -60,  # Event is in future
            "likely_past_event": drift_sec > 3600,   # Event is > 1 hour old
            "likely_timezone_bug": abs(drift_sec % 3600) < 60,  # Drift is multiple of 1 hour (timezone)
            "likely_clock_skew": 60 < abs(drift_sec) < 600  # 1-10 minutes
        }
        
        if analysis["likely_timezone_bug"]:
            hours_off = int(drift_sec / 3600)
            print(f"⚠️ Likely timezone skew: {hours_off} hours off")
        
        return analysis
    
    def correct_timezone_skew(self, event_timestamp, detected_skew_hours: int) -> datetime:
        """Correct timezone skew."""
        
        if isinstance(event_timestamp, str):
            event_dt = datetime.fromisoformat(event_timestamp)
        else:
            event_dt = event_timestamp
        
        # Adjust timestamp by detected skew
        corrected = event_dt + timedelta(hours=detected_skew_hours)
        
        print(f"🔧 Corrected timestamp: {event_dt} → {corrected} (offset: +{detected_skew_hours}h)")
        
        return corrected
    
    def is_future_event(self, event_timestamp) -> bool:
        """Check if event timestamp is in the future (impossible)."""
        
        if isinstance(event_timestamp, str):
            event_dt = datetime.fromisoformat(event_timestamp)
        else:
            event_dt = event_timestamp
        
        if event_dt.tzinfo is None:
            event_dt = event_dt.replace(tzinfo=timezone.utc)
        
        now = datetime.now(timezone.utc)
        
        is_future = event_dt > now
        
        if is_future:
            print(f"⚠️ Future event detected: {event_dt} > {now}")
        
        return is_future
```

---

### Detection

```yaml
monitoring:
  
  # Real-time alerts
  critical_alerts:
    
    # Watermark stalled
    - name: WatermarkStalled
      metric: "event_time_watermark"
      threshold: "Not advancing for 10 minutes"
      severity: "high"
      action: "Check for late data backlog, large buffered events"
    
    # High late arrival rate
    - name: LateArrivalSpike
      metric: "pct_records_received_late"
      threshold: "> 5%"
      severity: "high"
      action: "Check upstream system health"
    
    # Large restatements
    - name: LargeRestatement
      metric: "magnitude_of_corrections"
      threshold: "> 10%"
      severity: "medium"
      action: "Investigate reason for large correction"
    
    # Clock/timezone skew
    - name: TimeSkewDetected
      metric: "pct_future_events OR pct_events_off_by_hours"
      threshold: "> 0.1%"
      severity: "high"
      action: "Check client timezone handling, clock sync"
    
    # Out-of-order events
    - name: OutOfOrderEventRate
      metric: "out_of_order_event_rate"
      threshold: "> 1%"
      severity: "medium"
      action: "Out-of-order events detected, may affect join correctness"
    
    # Join incompleteness
    - name: JoinTimeoutRate
      metric: "join_timeout_rate"
      threshold: "> 2%"
      severity: "high"
      action: "Late events missing from join, increase grace period or investigate"
  
  # Dashboards
  dashboards:
    - name: "Late Data Monitoring"
      panels:
        - title: "Event-Time Watermark"
          metric: event_time_watermark
          target: "No more than 1h behind current time"
        
        - title: "Arrival Latency Distribution"
          metric: "percentiles of (arrival_time - event_time)"
          target: "p50 < 1min, p95 < 5min, p99 < 1hour"
        
        - title: "Completeness Curve"
          metric: "record count by time since window close"
          target: "75% by 5min, 95% by 30min, 99.9% by 24hr"
        
        - title: "Restatement Frequency"
          metric: count_of_corrections_issued
          target: "< 2 per day"
        
        - title: "Restatement Magnitude"
          metric: magnitude_of_corrections
          target: "< 5%"
        
        - title: "Clock Skew Detection"
          metric: future_events_or_timezone_bugs
          target: "< 0.1%"
    
    - name: "Join Health"
      panels:
        - title: "Join Timeout Rate"
          metric: join_timeout_rate
          target: "< 2%"
        
        - title: "Join Record Count"
          metric: join_record_count_variance
          target: "> 95% expected"
  
  # Batch validation jobs
  batch_jobs:
    - name: "hourly_completeness_check"
      schedule: "0 * * * *"
      checks:
        - "Watermark advancing"
        - "Late arrival rate acceptable"
        - "Restatements within bounds"
        - "Clock skew not detected"
      output: "Completeness report with late arrival analysis"
```

### Recovery

```python
def handle_late_data_recovery():
    """Recover from late-arriving data issues."""
    
    # Strategy 1: Restatement
    print("📊 Restatement: Aggregate includes late-arriving data")
    original_count = 1000
    late_count = 15
    new_count = original_count + late_count
    print(f"  Original: {original_count}")
    print(f"  Late arrivals: +{late_count}")
    print(f"  Final: {new_count} ({late_count/original_count:+.1%})")
    
    # Strategy 2: Early and late results
    print("\n📊 Early result (incomplete): 1000 records")
    print("📊 Late result (after grace period): 1015 records")
    
    # Strategy 3: Increase grace period
    print("\n⏱️  Increasing grace period from 5 min to 15 min")
    print("   Trade-off: Results available later, but more complete")
    
    # Strategy 4: Fix time skew
    print("\n🔧 Correcting timezone skew: UTC-8 hours detected")
    print("   Adjusted all affected event timestamps")
    
    # Strategy 5: Recompute aggregation
    print("\n🔄 Recomputing aggregation with corrected timestamps")
    print("   Final result: 1015 records (includes late and corrected events)")
```

---

## Chaos Experiment: Inject Late Arrival Scenarios

```python
# experiments/data-pipelines/late-arriving-data/run.py
import random
from datetime import datetime, timedelta

class LateArrivingDataInjector:
    """Simulate late-arriving data scenarios."""
    
    def __init__(self):
        self.results = []
    
    def scenario_1_mobile_event_late(self):
        """Mobile app queued event arriving late."""
        print("\n🔴 Scenario 1: Mobile App Event Late Arrival")
        
        event_timestamp = datetime(2025, 6, 15, 15, 0, 0)
        expected_arrival = event_timestamp + timedelta(seconds=5)
        actual_arrival = event_timestamp + timedelta(minutes=47)
        
        lateness = (actual_arrival - expected_arrival).total_seconds()
        
        print(f"  Event timestamp: {event_timestamp}")
        print(f"  Expected arrival: {expected_arrival}")
        print(f"  Actual arrival: {actual_arrival}")
        print(f"  Lateness: {lateness/60:.0f} minutes")
        
        # Window already closed at 15:05, event arrives at 15:47
        window_close = datetime(2025, 6, 15, 15, 5, 0)
        print(f"  Window closed at: {window_close}")
        print(f"  ⚠️ Event is {(actual_arrival - window_close).total_seconds()/60:.0f}min too late for window")
        
        self.results.append({
            "scenario": "Mobile Late Event",
            "lateness_minutes": 47,
            "impact": "Hourly aggregation incomplete by 1 record"
        })
    
    def scenario_2_batch_job_late(self):
        """Upstream batch job runs slowly."""
        print("\n🔴 Scenario 2: Upstream Batch Job Late")
        
        upstream_start = datetime(2025, 6, 14, 23, 0, 0)
        expected_duration = timedelta(hours=2)
        actual_duration = timedelta(hours=4)
        
        expected_end = upstream_start + expected_duration
        actual_end = upstream_start + actual_duration
        
        print(f"  Job started: {upstream_start}")
        print(f"  Expected end: {expected_end}")
        print(f"  Actual end: {actual_end}")
        print(f"  Delay: {(actual_end - expected_end).total_seconds()/3600:.1f}h")
        
        # Downstream job expected data at expected_end
        downstream_start = datetime(2025, 6, 15, 2, 0, 0)
        print(f"\n  Downstream job started: {downstream_start}")
        print(f"  Data wasn't ready (still processing upstream)")
        print(f"  ⚠️ Downstream ran with incomplete/stale data")
        
        self.results.append({
            "scenario": "Batch Job Delay",
            "delay_hours": 2,
            "impact": "Downstream aggregation incomplete"
        })
    
    def scenario_3_replication_lag(self):
        """DB replication lag causes stale analytics."""
        print("\n🔴 Scenario 3: Replication Lag")
        
        transactional_time = datetime(2025, 6, 15, 10, 15, 0)
        normal_replication_lag = timedelta(minutes=2)
        actual_replication_lag = timedelta(minutes=15)
        
        analytics_time = transactional_time + actual_replication_lag
        
        print(f"  Transaction written at: {transactional_time}")
        print(f"  Normal replication lag: {normal_replication_lag.total_seconds()/60:.0f} min")
        print(f"  Actual replication lag: {actual_replication_lag.total_seconds()/60:.0f} min")
        print(f"  Analytics query at: {datetime(2025, 6, 15, 10, 15, 0)}")
        print(f"  Analytics sees data from: {analytics_time}")
        print(f"  ⚠️ Analytics is seeing 15-minute-old data (3x normal)")
        
        self.results.append({
            "scenario": "Replication Lag",
            "lag_minutes": 15,
            "impact": "Analytics queries return stale data"
        })
    
    def scenario_4_timezone_skew(self):
        """Client sends time without UTC conversion."""
        print("\n🔴 Scenario 4: Timezone/Clock Skew")
        
        real_time_utc = datetime(2025, 6, 15, 22, 0, 0)  # 22:00 UTC
        real_time_pst = datetime(2025, 6, 15, 14, 0, 0)  # 14:00 PST (same moment)
        
        # Client bug: sends PST time without timezone info
        event_sent = {"timestamp": "14:00:00"}  # No timezone!
        
        # Pipeline assumes UTC
        pipeline_parses_as = datetime(2025, 6, 15, 14, 0, 0)  # 14:00 UTC (WRONG!)
        
        print(f"  Real time: {real_time_utc} UTC")
        print(f"  Real time: {real_time_pst} PST")
        print(f"  Client sends: {event_sent}")
        print(f"  Pipeline assumes: 14:00 UTC")
        print(f"  ⚠️ Event is 8 hours early (should be 22:00 UTC, parsed as 14:00 UTC)")
        
        # Impact: event goes to wrong hourly bucket
        wrong_bucket = "14:00-15:00 UTC"
        right_bucket = "22:00-23:00 UTC"
        print(f"  Event goes to: {wrong_bucket}")
        print(f"  Should go to: {right_bucket}")
        
        self.results.append({
            "scenario": "Timezone Skew",
            "hours_off": 8,
            "impact": "Event goes to wrong time bucket"
        })
    
    def scenario_5_out_of_order_status_update(self):
        """Status updates arrive out of order."""
        print("\n🔴 Scenario 5: Out-of-Order Status Updates")
        
        events = [
            ("order.created", datetime(2025, 6, 15, 10, 0, 0)),
            ("order.paid", datetime(2025, 6, 15, 10, 1, 0)),
            ("order.shipped", datetime(2025, 6, 15, 16, 1, 0)),  # 6h late!
        ]
        
        # Events arrive out of order
        arrival_order = [
            ("order.created", datetime(2025, 6, 15, 10, 0, 5)),
            ("order.paid", datetime(2025, 6, 15, 10, 1, 3)),
            ("order.shipped", datetime(2025, 6, 15, 10, 5, 0)),  # ARRIVES EARLY!
        ]
        
        print(f"  Actual sequence: {[e[0] for e in events]}")
        print(f"  Arrival sequence: {[e[0] for e in arrival_order]}")
        
        # Process in arrival order
        state = "unknown"
        for event_type, arrival_time in arrival_order:
            if event_type == "order.created":
                state = "created"
            elif event_type == "order.paid" and state == "created":
                state = "paid"
            elif event_type == "order.shipped" and state == "paid":
                state = "shipped"
        
        print(f"  Processing in arrival order:")
        print(f"    Created → Paid → Shipped → State: {state}")
        print(f"  ⚠️ If Shipped arrives too early, state may be incomplete")
        
        self.results.append({
            "scenario": "Out-of-Order Events",
            "impact": "Wrong state, incorrect downstream logic"
        })
    
    def scenario_6_join_timeout(self):
        """Join event missing because other stream is late."""
        print("\n🔴 Scenario 6: Join Timeout (Missing Match)")
        
        print("  Order-Payment Join (5 min grace period)")
        
        order_timestamp = datetime(2025, 6, 15, 10, 30, 15)
        order_arrival = datetime(2025, 6, 15, 10, 30, 15)
        
        grace_period_end = order_arrival + timedelta(minutes=5)
        
        print(f"  Order arrives: {order_arrival}")
        print(f"  Grace period until: {grace_period_end}")
        
        payment_timestamp = datetime(2025, 6, 15, 10, 30, 0)
        payment_arrival = datetime(2025, 6, 15, 10, 37, 45)  # 7:45 min late
        
        print(f"  Payment event time: {payment_timestamp}")
        print(f"  Payment arrives: {payment_arrival}")
        print(f"  ⚠️ Payment is {(payment_arrival - grace_period_end).total_seconds()/60:.1f}min too late")
        
        print(f"\n  Result: Order emitted without payment info")
        print(f"  System thinks: Order=complete, no payment needed")
        print(f"  Reality: Order has payment (but late)")
        print(f"  Consequence: Downstream system tries to collect payment again (duplicate charge)")
        
        self.results.append({
            "scenario": "Join Timeout",
            "grace_period_min": 5,
            "lateness_min": 7.75,
            "impact": "Incomplete join, duplicate charge attempt"
        })

def test_late_arrival_detection():
    """Test: Can we detect late arrivals?"""
    
    print("\n" + "="*70)
    print("TESTING LATE ARRIVAL DETECTION")
    print("="*70)
    
    checks = {
        "Watermark monitoring": True,
        "Completeness tracking": True,
        "Time skew detection": True,
        "Join timeout monitoring": True,
        "Out-of-order detection": True,
    }
    
    for check, status in checks.items():
        print(f"✅ {check}: {'✓' if status else '✗'}")

if __name__ == "__main__":
    injector = LateArrivingDataInjector()
    
    print("="*70)
    print("LATE-ARRIVING DATA SCENARIOS")
    print("="*70)
    
    injector.scenario_1_mobile_event_late()
    injector.scenario_2_batch_job_late()
    injector.scenario_3_replication_lag()
    injector.scenario_4_timezone_skew()
    injector.scenario_5_out_of_order_status_update()
    injector.scenario_6_join_timeout()
    
    print("\n" + "="*70)
    print("SCENARIO SUMMARY")
    print("="*70)
    
    for result in injector.results:
        print(f"\n{result['scenario']}:")
        for key, value in result.items():
            if key != 'scenario':
                print(f"  {key}: {value}")
    
    test_late_arrival_detection()
    
    print("\n✅ All late-arriving data tests completed!")
```

## Tools & Setup

```bash
# Install streaming tools
pip install apache-beam pyspark flink pandas

# Setup Apache Beam (Google Cloud Dataflow)
python -m pip install apache-beam[gcp]

# Setup Spark Structured Streaming
python -m pip install pyspark

# Run late arrival simulation
python experiments/data-pipelines/late-arriving-data/run.py

# Monitor watermarks
prometheus -c monitoring/prometheus.yml &
grafana-server &
open http://localhost:3000/d/late-data-monitoring
```

---

## Lessons Learned

### Case Study: Ride-Share Company - Incomplete Hourly Metrics

**Incident**: "Daily revenue report shows $2M, but by next day shows $2.15M. Why?"

**Root Cause**:
- Mobile app queues ride events when offline
- 10-15% of events arrive 2-10 minutes late
- Hourly aggregation window closes at :01 past hour
- Late events were dropped (no grace period)
- Events arrived between :01 and :15 were discarded
- $150K in daily revenue going unrecorded

**Detection Time**: 24 hours
- Hourly report published at :15 past hour (incomplete)
- Next day reconciliation: Revenue is 7.5% lower

**MTTR**: 8 hours
- Discovered during reconciliation
- Implemented grace period (5 min)
- Recomputed all 30 days of missing revenue

**Prevention Implemented**:
1. ✅ Added 5-minute grace period to all hourly windows
2. ✅ Watermark monitoring (alert if stalled)
3. ✅ Restatement handling (emit correction after grace period)
4. ✅ Early and late results (provisional + final)
5. ✅ Completeness tracking (95% by 5min, 99.9% by 1 hour)
6. ✅ Timezone/skew detection (all events UTC with validation)

**Impact**: Reduced unrecorded revenue from 7.5% to < 0.1%.

---

## References
- [Apache Beam Windowing](https://beam.apache.org/documentation/programming-guide/#windowing)
- [Flink Event Time Processing](https://nightlies.apache.org/flink/flink-docs-master/docs/concepts/time/)
- [Spark Structured Streaming Late Data](https://spark.apache.org/docs/latest/structured-streaming-programming-guide.html#handling-late-data-and-watermarking)
- [Watermarking in Streaming](https://www.oreilly.com/library/view/streaming-systems/9781491951751/ch02.html)
- [Temporal Join Patterns](https://www.confluent.io/blog/stream-processing-with-temporal-joins/)
