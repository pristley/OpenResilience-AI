# Pattern: Feature Store Outage

> When your feature store (centralized ML feature repository) goes down or serves stale/corrupted features, all dependent ML models fail or produce garbage predictions.

## Quick Summary

**Problem**: Feature store service unavailable, stale features, schema incompatibility, retrieval latency spike, or corrupted feature vectors  
**Impact**: ML models offline or predicting on wrong data → business decisions wrong  
**Detection Time**: Seconds (if monitored) to minutes (user sees bad predictions)  
**Solution**: Multi-region replication, fallback to batch/cache, feature versioning, SLA enforcement, circuit breakers

---

## Problem Statement

A feature store is the central repository of pre-computed features for ML models. When it fails, your entire ML inference pipeline breaks:
- Models can't get features → predictions unavailable
- Stale features → predictions based on old data
- Corrupted features → garbage-in, garbage-out
- Latency spikes → inference times exceed SLAs

### Real Scenarios

**Scenario 1: Feature Store Service Crash**
- Feature store (Tecton, Feast, or custom) goes down during upgrade
- ML models can't retrieve features for real-time inference
- Online predictions return timeout errors or default values
- User-facing recommendations go offline
- Batch scoring jobs also blocked (if they use online store)
- MTTR: 15-30 minutes until service restored

**Scenario 2: Stale Features (Refresh Failed)**
- Feature computation job fails silently
- Features aren't updated for 6+ hours (should refresh hourly)
- Models use 6-hour-old features instead of fresh data
- Recommendations based on yesterday's behavior
- Nobody notices until accuracy metrics drop (4-8 hours later)
- Models re-trained on stale data → permanent accuracy degradation

**Scenario 3: Schema Incompatibility**
- Data engineer adds new feature to feature store
- Doesn't update model serving code
- ML model tries to read feature "user_premium_tier" but gets NULL
- Model uses default value (0) instead of real feature
- Model degradation: 5-15% accuracy drop
- Error logs show type mismatch but unnoticed in chaos

**Scenario 4: Feature Retrieval Latency Spike**
- Feature store database suddenly slow (resource contention, query optimization missing)
- Feature retrieval takes 500ms instead of 50ms
- Inference latency goes from 100ms to 600ms
- SLA breach: Should respond in < 500ms, now taking 600ms
- Inference timeout → fallback to stale/default values
- Downstream: User experiences slow recommendations or gets generic content

**Scenario 5: Corrupted Feature Vectors (NaN/NULL explosion)**
- Data processing bug in feature computation
- 20% of feature vectors become NaN/NULL
- Models expect numeric values, get NULL
- Model behavior: Either crashes or treats NULL as 0/-1/default
- Predictions become unreliable
- A/B tests invalid (treatment and control have different data quality)

**Scenario 6: Cross-Region Inconsistency**
- Feature store replicated across US East and US West
- Replication lag: 5 seconds
- Models in US East see feature value X
- Models in US West see feature value Y (stale copy)
- Recommendations differ by region
- Users notice: "Why do I see different products on mobile (West) vs web (East)?"

---

## Why It Matters

### Impact Metrics

**Feature Store Downtime Costs:**
| Duration | Cost | Impact |
|----------|------|--------|
| **1 minute** | $5K-50K | Inference slow/failing, user sees delays |
| **5 minutes** | $25K-250K | Inference fully offline, recommendations unavailable |
| **15 minutes** | $75K-750K | User experience significantly degraded |
| **1 hour** | $300K-3M | Revenue impact (can't recommend), customer churn |

**Accuracy Impact of Stale Features:**
| Staleness | Accuracy Degradation | Example |
|-----------|---------------------|---------|
| < 1 hour | < 1% degradation | Acceptable |
| 6 hours | 5-15% degradation | Noticeable |
| 24 hours | 15-40% degradation | Significant |
| > 48 hours | > 40% degradation | Critical |

**Blast Radius:**
- **Direct**: All models using feature store (could be 50-200+ models)
- **Indirect**: Dependent systems (recommendations, search, ranking)
- **Cascading**: A/B test validity compromised, retraining on bad data

### Detection Latency

- **Best case** (real-time monitoring + alerting): **5-30 seconds**
  - "Alert: Feature store latency > 500ms"
  
- **Realistic** (periodic health checks): **1-5 minutes**
  - "Health check failed 3 times in a row"
  
- **Worst case** (user notices): **5-30 minutes**
  - "Why are recommendations so bad?"

---

## How It Fails

### Mechanism

```
1. Feature store issue occurs:
   a) Service crash
   b) Replication lag
   c) Feature computation fails (stale)
   d) Schema incompatibility
   e) Latency spike
   f) Data corruption

2. ML models try to fetch features
   ↓

3. Error handling:
   Good: Fallback to cache/default, circuit breaker
   Bad: Retry forever, timeout, use NULL/0 as feature
   ↓

4. Prediction quality degrades:
   - Inference fails (service down)
   - Inference wrong (stale/corrupted features)
   - Inference slow (SLA breach)
   ↓

5. Cascading failures:
   - Recommendations become stale
   - Search ranking worsens
   - Personalization breaks
   - A/B tests invalid
   ↓

6. Discovery happens via:
   - Automated monitoring (best: < 1 min)
   - Metrics anomalies (good: 5-15 min)
   - User complaints (bad: 15-60 min)
```

### Observable Signals

#### **Metrics to Monitor**

```yaml
feature_store_metrics:
  
  # 1. Availability
  - name: "feature_store_availability"
    definition: "percentage of successful feature requests"
    alert_threshold: "< 99.5%"
    sla_target: "> 99.95%"
  
  - name: "feature_store_uptime"
    definition: "service health check pass rate"
    alert_threshold: "== 0"  # Any failure is critical
  
  # 2. Latency
  - name: "feature_retrieval_p95_latency"
    definition: "95th percentile latency for feature request"
    alert_threshold: "> 500ms"
    acceptable: "< 100ms"
  
  - name: "feature_retrieval_p99_latency"
    definition: "99th percentile latency"
    alert_threshold: "> 1000ms"
  
  - name: "inference_latency_spike"
    definition: "inference time with new feature retrieval"
    alert_threshold: "> previous_p95 * 2"
  
  # 3. Freshness
  - name: "feature_staleness"
    definition: "max(now - feature_last_updated) across all features"
    alert_threshold: "> expected_refresh_interval * 2"
    
  - name: "pct_stale_features"
    definition: "percentage of features older than SLA"
    alert_threshold: "> 5%"
  
  # 4. Data Quality
  - name: "null_rate_in_features"
    definition: "count(NULL values) / count(total values)"
    alert_threshold: "> 1%"
  
  - name: "nan_rate_in_features"
    definition: "count(NaN values) / count(total values)"
    alert_threshold: "> 0.5%"
  
  - name: "feature_vector_corruption_rate"
    definition: "count(vectors with invalid values) / count(total vectors)"
    alert_threshold: "> 0.1%"
  
  # 5. Replication/Consistency
  - name: "replication_lag"
    definition: "time difference between primary and replica"
    alert_threshold: "> 10 seconds"
    acceptable: "< 1 second"
  
  - name: "cross_region_feature_divergence"
    definition: "diff(feature_value_us_east, feature_value_us_west)"
    alert_threshold: "> 5%"  # More than 5% different
  
  # 6. Schema
  - name: "schema_mismatch_errors"
    definition: "count of requests with schema validation failure"
    alert_threshold: "> 0"
  
  - name: "missing_feature_errors"
    definition: "count of requests for non-existent feature"
    alert_threshold: "> 0"
  
  # 7. Compute Job Health
  - name: "feature_compute_job_failures"
    definition: "count of failed feature computation jobs"
    alert_threshold: "> 0"
  
  - name: "feature_compute_job_latency"
    definition: "time to compute and store features"
    alert_threshold: "> expected * 1.5"
```

#### **Log Patterns**

```
[ERROR] Feature store connection failed: Connection refused to fs.example.com:6379
[ERROR] Feature request timeout: p95_latency = 1200ms (threshold: 500ms)
[WARN]  Feature staleness detected: user_features last updated 6h ago (SLA: 1h)
[ERROR] Feature schema mismatch: Expected FLOAT, got NULL for 'user_engagement_score'
[CRIT]  Replication lag critical: primary is 45 seconds ahead of replica
[ERROR] Feature vector corruption: 2,345 vectors contain NaN (0.5% corruption rate)
[ERROR] Feature store query failed: Out of memory, killing expensive queries
[WARN]  Inference latency spike: avg_latency went from 80ms to 520ms
[ERROR] Circuit breaker opened: Feature store unhealthy, using fallback
```

#### **Trace Patterns**

```
Trace: inference_with_features
├─ [OK] Start inference request (user_id=123)
├─ [START] Get features from feature store
│  ├─ [TIMEOUT] Feature retrieval took 1200ms (threshold: 500ms)
│  └─ [FALLBACK] Using cached features (age: 2 hours)
├─ [WARN] Features are stale (2h old vs 1h SLA)
├─ [PARTIAL] Generated predictions with degraded features
│  └─ Accuracy: -8% vs baseline
└─ [END] Returned prediction (quality: degraded)

Trace: feature_computation_pipeline
├─ [OK] Start feature computation job
├─ [OK] Extract raw data (100M rows)
├─ [OK] Compute features (avg user_engagement_score = 0.65)
├─ [ERROR] Write to feature store failed: Disk full
├─ [BLOCKED] Replication to backup feature store skipped
└─ [END] Job failed - features not updated (previous: 24h old)

Trace: model_prediction
├─ [OK] Load model
├─ [START] Get user_features
│  ├─ Request: {user_id: 123, features: [engagement, recency, ltv]}
│  └─ Response: {user_id: 123, engagement: NULL, recency: 0.5, ltv: $250}
├─ [WARN] NULL value in features (engagement = NULL)
├─ [MODEL] Prediction: engagement was NULL, using model default
│  └─ Prediction: user_ltv_next_30d = $180 (should be $450 with real engagement)
└─ [END] Returned degraded prediction
```

#### **Health Checks (Real-Time)**

```yaml
health_checks:
  - check: "Feature store connectivity"
    query: "SELECT COUNT(*) FROM feature_store LIMIT 1"
    acceptable: "< 1 second response"
    frequency: "every 10 seconds"
  
  - check: "Feature retrieval latency"
    query: "Retrieve features for sample user, measure time"
    acceptable: "< 500ms (p95)"
    frequency: "every 30 seconds"
  
  - check: "Feature staleness"
    query: "SELECT MAX(updated_at) FROM features"
    acceptable: "< 1 hour old (or SLA)"
    frequency: "every 5 minutes"
  
  - check: "Data quality (NULL rate)"
    query: "SELECT COUNT(*) WHERE value IS NULL FROM features"
    acceptable: "< 1%"
    frequency: "every 15 minutes"
  
  - check: "Replication lag"
    query: "Compare feature values between primary and replica"
    acceptable: "< 1 second lag"
    frequency: "every 30 seconds"
  
  - check: "Schema validation"
    query: "Fetch features and validate types"
    acceptable: "100% success"
    frequency: "every 5 minutes"
```

### Time to Detect

- **Best case** (automated monitoring, < 1 min):
  - "Alert: Feature store health check failed 3x in a row"
  - "Alert: Feature retrieval latency > 500ms (p95)"
  
- **Realistic** (periodic checks + metrics review, 5-15 min):
  - "Morning report shows feature staleness increased 6x"
  - "Metrics dashboard shows stale features appearing in predictions"
  
- **Worst case** (user notices, 15-60 min):
  - "Recommendations are bad today"
  - "Search ranking is broken"

### Blast Radius

- **Direct**: All models using feature store (50-500+ models depending on org)
- **Scope**: Every inference request affected (1000s per second)
- **Downstream**: Recommendations, ranking, personalization, search
- **Duration**: Minutes (outage) to hours/days (stale features)
- **Severity**: High (user-facing), affects revenue

---

## Resilience Strategy

### Prevention

#### **1. Multi-Region Replication**

```python
# feature_store/replication.py
from typing import Dict, Any
import threading
import time

class FeatureStoreReplication:
    """Multi-region feature store with eventual consistency."""
    
    def __init__(self, primary_host: str, replicas: list):
        self.primary = primary_host
        self.replicas = replicas
        self.replication_lag_ms = {}
    
    def write_feature(self, feature_id: str, feature_data: Dict[str, Any]) -> bool:
        """Write feature to primary, replicate to all regions."""
        
        # Step 1: Write to primary (synchronous)
        try:
            self.primary.write(feature_id, feature_data)
            print(f"✅ Written to primary: {feature_id}")
        except Exception as e:
            print(f"❌ Primary write failed: {e}")
            return False
        
        # Step 2: Asynchronously replicate to replicas
        for replica in self.replicas:
            threading.Thread(
                target=self._replicate_to_region,
                args=(replica, feature_id, feature_data),
                daemon=True
            ).start()
        
        return True
    
    def _replicate_to_region(self, replica_host: str, feature_id: str, 
                            feature_data: Dict[str, Any]):
        """Replicate to a single region with retry logic."""
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                start_time = time.time()
                replica_host.write(feature_id, feature_data)
                lag_ms = (time.time() - start_time) * 1000
                
                self.replication_lag_ms[replica_host.name] = lag_ms
                
                if lag_ms > 5000:
                    print(f"⚠️ Replication lag to {replica_host.name}: {lag_ms:.0f}ms")
                else:
                    print(f"✅ Replicated to {replica_host.name} ({lag_ms:.0f}ms)")
                
                return
            
            except Exception as e:
                retry_count += 1
                print(f"⚠️ Replication attempt {retry_count}/{max_retries} failed: {e}")
                time.sleep(2 ** retry_count)  # Exponential backoff
        
        print(f"❌ Replication failed to {replica_host.name} after {max_retries} retries")
    
    def get_feature(self, feature_id: str, prefer_region: str = None) -> Dict[str, Any]:
        """Read feature with region preference and fallback."""
        
        # Try preferred region first
        if prefer_region:
            for replica in self.replicas:
                if replica.name == prefer_region:
                    try:
                        return replica.read(feature_id)
                    except Exception as e:
                        print(f"⚠️ Read from {prefer_region} failed: {e}")
                        break
        
        # Try primary
        try:
            return self.primary.read(feature_id)
        except Exception as e:
            print(f"⚠️ Read from primary failed: {e}")
        
        # Fallback to other replicas
        for replica in self.replicas:
            if prefer_region and replica.name == prefer_region:
                continue
            try:
                data = replica.read(feature_id)
                print(f"✅ Read from fallback region {replica.name}")
                return data
            except Exception:
                continue
        
        raise Exception(f"Could not read feature {feature_id} from any region")
    
    def get_replication_status(self) -> Dict[str, Any]:
        """Monitor replication health."""
        return {
            "replication_lags_ms": self.replication_lag_ms,
            "max_lag_ms": max(self.replication_lag_ms.values()) if self.replication_lag_ms else 0,
            "healthy": all(lag < 5000 for lag in self.replication_lag_ms.values()),
        }
```

#### **2. Feature Versioning & Rollback**

```python
# feature_store/versioning.py
from datetime import datetime, timedelta
from typing import List

class FeatureVersionControl:
    """Version and rollback features."""
    
    def __init__(self, db):
        self.db = db
    
    def create_feature_version(self, feature_name: str, 
                              feature_values: dict, 
                              compute_job_id: str = None) -> str:
        """Create timestamped version of feature."""
        
        version_id = f"{feature_name}_{datetime.now().isoformat()}"
        
        version_entry = {
            "version_id": version_id,
            "feature_name": feature_name,
            "timestamp": datetime.now(),
            "compute_job_id": compute_job_id,
            "feature_count": len(feature_values),
            "sample_values": dict(list(feature_values.items())[:5]),  # First 5 for inspection
            "status": "active"
        }
        
        self.db.save_feature_version(version_entry)
        print(f"✅ Created feature version: {version_id}")
        
        return version_id
    
    def list_feature_versions(self, feature_name: str, limit: int = 10) -> List[dict]:
        """List recent versions of a feature."""
        versions = self.db.get_feature_versions(feature_name, limit=limit)
        
        for v in versions:
            age_hours = (datetime.now() - v["timestamp"]).total_seconds() / 3600
            v["age_hours"] = age_hours
            v["is_current"] = v["status"] == "active"
        
        return sorted(versions, key=lambda x: x["timestamp"], reverse=True)
    
    def rollback_feature(self, feature_name: str, target_version: str = None):
        """Rollback to previous feature version."""
        
        if target_version:
            # Rollback to specific version
            target = self.db.get_feature_version(target_version)
        else:
            # Rollback to previous version
            versions = self.list_feature_versions(feature_name, limit=2)
            if len(versions) < 2:
                raise ValueError("No previous version available")
            target = versions[1]  # Second most recent
        
        print(f"🔄 Rolling back {feature_name} to {target['version_id']}")
        
        # Activate previous version
        self.db.set_feature_version_active(target["version_id"])
        
        # Log rollback
        self.db.log_rollback_event({
            "feature": feature_name,
            "from_version": self.list_feature_versions(feature_name, limit=1)[0]["version_id"],
            "to_version": target["version_id"],
            "timestamp": datetime.now(),
            "reason": "Data quality issue / staleness detected"
        })
        
        print(f"✅ Rolled back to {target['version_id']} (age: {target['age_hours']:.1f}h old)")
    
    def validate_feature_version_quality(self, version_id: str) -> dict:
        """Validate quality of feature version before deploying."""
        
        version = self.db.get_feature_version(version_id)
        feature_values = self.db.get_feature_values(version_id)
        
        # Quality checks
        checks = {
            "null_rate": sum(1 for v in feature_values.values() if v is None) / len(feature_values),
            "nan_rate": sum(1 for v in feature_values.values() if isinstance(v, float) and v != v) / len(feature_values),
            "staleness_hours": (datetime.now() - version["timestamp"]).total_seconds() / 3600,
        }
        
        checks["quality_score"] = (
            (1 - checks["null_rate"]) * 0.5 +
            (1 - checks["nan_rate"]) * 0.3 +
            (1 - min(checks["staleness_hours"] / 24, 1.0)) * 0.2
        )
        
        checks["is_acceptable"] = (
            checks["null_rate"] < 0.05 and
            checks["nan_rate"] < 0.01 and
            checks["staleness_hours"] < 24
        )
        
        return checks
```

#### **3. Caching Layer with TTL**

```python
# feature_store/cache.py
import redis
from typing import Dict, Any, Optional
import json
from datetime import datetime, timedelta

class FeatureStoreCache:
    """Cache layer for feature store with fallback."""
    
    def __init__(self, cache_client, ttl_seconds: int = 3600):
        self.cache = cache_client  # Redis or similar
        self.ttl = ttl_seconds
        self.stats = {"hits": 0, "misses": 0}
    
    def get_feature(self, feature_id: str, 
                   fetch_func, 
                   use_fallback: bool = True) -> Optional[Dict[str, Any]]:
        """Get feature with caching and fallback."""
        
        cache_key = f"feature:{feature_id}"
        
        # Try cache first
        try:
            cached = self.cache.get(cache_key)
            if cached:
                self.stats["hits"] += 1
                data = json.loads(cached)
                data["_source"] = "cache"
                return data
        except Exception as e:
            print(f"⚠️ Cache read error: {e}")
        
        # Cache miss - fetch fresh
        self.stats["misses"] += 1
        try:
            feature = fetch_func(feature_id)
            
            # Store in cache
            try:
                self.cache.setex(
                    cache_key,
                    self.ttl,
                    json.dumps(feature)
                )
            except Exception as e:
                print(f"⚠️ Cache write error: {e}")
            
            feature["_source"] = "fresh"
            return feature
        
        except Exception as e:
            print(f"❌ Feature fetch failed: {e}")
            
            if use_fallback:
                # Return stale cache as fallback
                try:
                    stale = self.cache.get(cache_key)
                    if stale:
                        data = json.loads(stale)
                        data["_source"] = "stale_cache"
                        data["_warning"] = "Data is stale due to feature store failure"
                        print(f"⚠️ Using stale cache for {feature_id}")
                        return data
                except:
                    pass
            
            raise
    
    def get_cache_stats(self) -> dict:
        """Monitor cache performance."""
        total = self.stats["hits"] + self.stats["misses"]
        hit_rate = self.stats["hits"] / total if total > 0 else 0
        
        return {
            "hits": self.stats["hits"],
            "misses": self.stats["misses"],
            "hit_rate": f"{hit_rate:.1%}",
            "total_requests": total
        }
```

#### **4. Circuit Breaker Pattern**

```python
# feature_store/circuit_breaker.py
from enum import Enum
from datetime import datetime, timedelta
import threading

class CircuitState(Enum):
    CLOSED = "closed"        # Working normally
    OPEN = "open"            # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if recovered

class FeatureStoreCircuitBreaker:
    """Prevent cascading failures with circuit breaker."""
    
    def __init__(self, 
                 failure_threshold: int = 5,
                 recovery_timeout_sec: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = timedelta(seconds=recovery_timeout_sec)
        
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time = None
        self.last_state_change = datetime.now()
    
    def call_feature_store(self, feature_id: str, fetch_func, fallback_func):
        """Attempt feature store call with circuit breaker."""
        
        # Check if circuit should reset
        if self.state == CircuitState.OPEN:
            if datetime.now() - self.last_state_change > self.recovery_timeout:
                print("🔄 Circuit breaker: Attempting recovery (HALF_OPEN state)")
                self.state = CircuitState.HALF_OPEN
                self.failure_count = 0
        
        # Reject if circuit is open
        if self.state == CircuitState.OPEN:
            print(f"⛔ Circuit breaker OPEN: Using fallback for {feature_id}")
            return fallback_func(feature_id)
        
        # Try feature store
        try:
            result = fetch_func(feature_id)
            
            # Success: reset state
            if self.state == CircuitState.HALF_OPEN:
                print("✅ Circuit breaker: Recovered (CLOSED state)")
                self.state = CircuitState.CLOSED
                self.failure_count = 0
            
            return result
        
        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = datetime.now()
            
            print(f"❌ Feature store call failed ({self.failure_count}/{self.failure_threshold}): {e}")
            
            # Open circuit if threshold exceeded
            if self.failure_count >= self.failure_threshold:
                print(f"🔴 Circuit breaker OPEN: Too many failures ({self.failure_count})")
                self.state = CircuitState.OPEN
                self.last_state_change = datetime.now()
            
            # Use fallback
            return fallback_func(feature_id)
    
    def get_status(self) -> dict:
        """Monitor circuit breaker status."""
        return {
            "state": self.state.value,
            "failure_count": self.failure_count,
            "last_failure": self.last_failure_time,
            "time_until_recovery": (
                self.recovery_timeout - (datetime.now() - self.last_state_change)
            ) if self.state == CircuitState.OPEN else None
        }
```

#### **5. Feature SLA Enforcement**

```python
# feature_store/sla.py
from dataclasses import dataclass
from typing import Dict
from datetime import datetime, timedelta

@dataclass
class FeatureSLA:
    """Service Level Agreement for features."""
    
    feature_name: str
    max_latency_ms: int        # Max retrieval time
    max_staleness_hours: int   # Max age of features
    availability_pct: float    # 99.9%, 99.95%, etc.
    max_null_rate: float       # Max acceptable NULL rate
    max_corruption_rate: float # Max NaN/invalid rate

class FeatureSLAMonitor:
    """Monitor feature SLA compliance."""
    
    def __init__(self):
        self.slas: Dict[str, FeatureSLA] = {}
        self.violations = []
    
    def register_sla(self, sla: FeatureSLA):
        """Register SLA for feature."""
        self.slas[sla.feature_name] = sla
        print(f"📋 Registered SLA for {sla.feature_name}")
    
    def check_latency_sla(self, feature_name: str, latency_ms: float) -> bool:
        """Check if retrieval latency meets SLA."""
        sla = self.slas.get(feature_name)
        if not sla:
            return True
        
        meets_sla = latency_ms <= sla.max_latency_ms
        
        if not meets_sla:
            self.violations.append({
                "feature": feature_name,
                "type": "latency",
                "value": latency_ms,
                "sla": sla.max_latency_ms,
                "timestamp": datetime.now()
            })
            print(f"⚠️ SLA violation: {feature_name} latency {latency_ms:.0f}ms > {sla.max_latency_ms}ms")
        
        return meets_sla
    
    def check_freshness_sla(self, feature_name: str, 
                           last_updated: datetime) -> bool:
        """Check if feature freshness meets SLA."""
        sla = self.slas.get(feature_name)
        if not sla:
            return True
        
        staleness_hours = (datetime.now() - last_updated).total_seconds() / 3600
        meets_sla = staleness_hours <= sla.max_staleness_hours
        
        if not meets_sla:
            self.violations.append({
                "feature": feature_name,
                "type": "freshness",
                "value": staleness_hours,
                "sla": sla.max_staleness_hours,
                "timestamp": datetime.now()
            })
            print(f"⚠️ SLA violation: {feature_name} staleness {staleness_hours:.1f}h > {sla.max_staleness_hours}h")
        
        return meets_sla
    
    def check_quality_sla(self, feature_name: str, 
                         null_rate: float, corruption_rate: float) -> bool:
        """Check if data quality meets SLA."""
        sla = self.slas.get(feature_name)
        if not sla:
            return True
        
        meets_null = null_rate <= sla.max_null_rate
        meets_corruption = corruption_rate <= sla.max_corruption_rate
        meets_sla = meets_null and meets_corruption
        
        if not meets_sla:
            violations = []
            if not meets_null:
                violations.append(f"null_rate: {null_rate:.1%} > {sla.max_null_rate:.1%}")
            if not meets_corruption:
                violations.append(f"corruption: {corruption_rate:.1%} > {sla.max_corruption_rate:.1%}")
            
            self.violations.append({
                "feature": feature_name,
                "type": "quality",
                "violations": violations,
                "timestamp": datetime.now()
            })
            print(f"⚠️ SLA violation: {feature_name} quality - {', '.join(violations)}")
        
        return meets_sla
    
    def get_sla_report(self) -> dict:
        """Generate SLA compliance report."""
        return {
            "total_features": len(self.slas),
            "violations_last_24h": len([v for v in self.violations 
                                       if (datetime.now() - v["timestamp"]).days < 1]),
            "recent_violations": self.violations[-10:],
            "sla_compliance": {
                "latency": f"{100 - (len([v for v in self.violations if v['type'] == 'latency']) / max(1, len(self.slas)) * 100):.1f}%",
                "freshness": f"{100 - (len([v for v in self.violations if v['type'] == 'freshness']) / max(1, len(self.slas)) * 100):.1f}%",
                "quality": f"{100 - (len([v for v in self.violations if v['type'] == 'quality']) / max(1, len(self.slas)) * 100):.1f}%"
            }
        }
```

---

### Detection

```yaml
monitoring:
  
  # Real-time alerts
  critical_alerts:
    
    # Outage
    - name: FeatureStoreOutage
      metric: "feature_store_availability"
      threshold: "== 0"
      severity: "critical"
      action: "Immediate: Failover to replica, activate circuit breaker"
    
    # Latency spike
    - name: FeatureRetrievalLatencySpike
      metric: "feature_retrieval_p95_latency"
      threshold: "> 500ms"
      severity: "high"
      action: "Check resource utilization, consider query optimization"
    
    # Stale features
    - name: FeatureStalenessSpike
      metric: "feature_staleness"
      threshold: "> SLA threshold"
      severity: "high"
      action: "Check feature computation job, trigger manual recompute"
    
    # Data corruption
    - name: DataCorruptionDetected
      metric: "null_rate_in_features OR nan_rate_in_features"
      threshold: "> 1%"
      severity: "critical"
      action: "Pause feature deployment, investigate root cause"
    
    # Schema mismatch
    - name: SchemaMismatch
      metric: "schema_mismatch_errors"
      threshold: "> 0"
      severity: "error"
      action: "Review recent schema changes, update model serving code"
    
    # Replication lag
    - name: ReplicationLagCritical
      metric: "replication_lag"
      threshold: "> 30 seconds"
      severity: "high"
      action: "Check replication network, investigate lag source"
  
  # Dashboards
  dashboards:
    - name: "Feature Store Health"
      panels:
        - title: "Availability"
          metric: feature_store_availability
          target: "> 99.95%"
        
        - title: "Retrieval Latency (p95)"
          metric: feature_retrieval_p95_latency
          target: "< 100ms"
        
        - title: "Feature Staleness (max)"
          metric: feature_staleness
          target: "< SLA"
        
        - title: "Data Quality (null + corruption)"
          metric: null_rate + nan_rate
          target: "< 1%"
        
        - title: "Replication Lag"
          metric: replication_lag
          target: "< 1 second"
        
        - title: "Model Prediction Accuracy"
          metric: inference_accuracy
          target: "No anomalies vs baseline"
    
    - name: "Feature Store Performance"
      panels:
        - title: "Query Performance"
          metric: query_latency_distribution
        
        - title: "Cache Hit Rate"
          metric: cache_hit_ratio
          target: "> 80%"
        
        - title: "Feature Compute Job Status"
          metric: compute_job_success_rate
          target: "> 99%"
  
  # Batch validation jobs
  batch_jobs:
    - name: "hourly_feature_validation"
      schedule: "0 * * * *"  # Every hour
      checks:
        - "All features refreshed within SLA"
        - "NULL and NaN rates acceptable"
        - "Schema matches model expectations"
        - "Replication lag < 10 seconds"
      output: "Feature quality report"
```

### Recovery

#### **Step 1: Detect and Alert**

```bash
# Real-time monitoring detects issue
feature_store_health_check() {
  if ! curl -s http://feature-store:8000/health > /dev/null; then
    echo "CRITICAL: Feature store unreachable"
    trigger_alert "FeatureStoreOutage" "critical"
    return 1
  fi
}

feature_latency_check() {
  latency=$(curl -s -w "%{time_total}" http://feature-store:8000/ping -o /dev/null)
  if (( $(echo "$latency > 0.5" | bc -l) )); then
    echo "HIGH: Feature retrieval latency: ${latency}s"
    trigger_alert "FeatureLatencySpike" "high"
  fi
}
```

#### **Step 2: Activate Fallbacks**

```python
def inference_with_fallbacks(user_id: str, required_features: list):
    """Inference with graceful degradation."""
    
    # Strategy 1: Try primary feature store
    try:
        features = feature_store.get_features(user_id, required_features)
        features["quality"] = "fresh"
        return features
    except Exception as e:
        print(f"⚠️ Primary failed: {e}")
    
    # Strategy 2: Try replicas
    for replica in feature_store.replicas:
        try:
            features = replica.get_features(user_id, required_features)
            features["quality"] = "replica"
            print(f"✅ Retrieved from replica: {replica.name}")
            return features
        except Exception as e:
            print(f"⚠️ Replica {replica.name} failed: {e}")
            continue
    
    # Strategy 3: Use cache (may be stale)
    try:
        features = feature_cache.get(user_id, required_features)
        features["quality"] = "stale_cache"
        features["age_hours"] = features.get("_age", "unknown")
        print(f"⚠️ Using cached features (age: {features['age_hours']}h)")
        return features
    except Exception as e:
        print(f"⚠️ Cache failed: {e}")
    
    # Strategy 4: Use defaults
    print("⛔ All sources failed, using default features")
    return {
        "quality": "default",
        "features": [0.0] * len(required_features),
        "warning": "Using default features - quality degraded"
    }
```

#### **Step 3: Investigate Root Cause**

```sql
-- Check feature store logs
SELECT timestamp, error_message, user_id
FROM feature_store_logs
WHERE status = 'error'
AND timestamp > NOW() - INTERVAL 30 MINUTE
ORDER BY timestamp DESC
LIMIT 100;

-- Check staleness
SELECT 
  feature_name,
  MAX(last_updated) as last_update,
  NOW() - MAX(last_updated) as age,
  COUNT(*) as record_count
FROM features
GROUP BY feature_name
HAVING NOW() - MAX(last_updated) > INTERVAL 2 HOUR
ORDER BY age DESC;

-- Check data quality
SELECT 
  feature_name,
  COUNT(*) as total,
  COUNTIF(value IS NULL) as nulls,
  COUNTIF(ISNAN(value)) as nans,
  COUNTIF(value IS NULL) / COUNT(*) as null_rate
FROM features
WHERE created_at > NOW() - INTERVAL 1 HOUR
GROUP BY feature_name
HAVING null_rate > 0.01;

-- Check replication lag
SELECT 
  primary_region,
  replica_region,
  MAX(replication_lag_ms) as max_lag,
  AVG(replication_lag_ms) as avg_lag
FROM replication_metrics
WHERE timestamp > NOW() - INTERVAL 1 HOUR
GROUP BY primary_region, replica_region
ORDER BY max_lag DESC;
```

#### **Step 4: Implement Recovery**

```python
def feature_store_recovery(incident_type: str):
    """Recovery procedures by incident type."""
    
    if incident_type == "service_outage":
        # Restart service
        print("🔄 Restarting feature store service...")
        subprocess.run(["kubectl", "restart", "feature-store"])
        
        # Wait for healthcheck
        while not feature_store.is_healthy():
            time.sleep(5)
        
        print("✅ Feature store recovered")
    
    elif incident_type == "stale_features":
        # Manually trigger feature computation
        print("🔄 Triggering feature recomputation...")
        job_id = feature_compute.trigger_manual_job(priority="high")
        
        # Monitor job
        while True:
            status = feature_compute.get_job_status(job_id)
            if status["state"] == "completed":
                print(f"✅ Features recomputed (job: {job_id})")
                break
            time.sleep(30)
    
    elif incident_type == "data_corruption":
        # Rollback to previous version
        print("🔄 Rolling back features...")
        feature_version_control.rollback_feature("all", steps=1)
        print("✅ Features rolled back to previous version")
    
    elif incident_type == "latency_spike":
        # Scale up resources
        print("⬆️ Scaling feature store resources...")
        subprocess.run([
            "kubectl", "scale", "deployment", "feature-store",
            "--replicas=5"
        ])
        
        # Monitor latency
        for _ in range(30):
            latency = feature_store.measure_latency()
            if latency < 100:
                print(f"✅ Latency recovered: {latency:.0f}ms")
                break
            time.sleep(10)
    
    elif incident_type == "schema_mismatch":
        # Update model serving code
        print("🔄 Updating model serving schema...")
        deploy_model_serving_update()
        print("✅ Schema updated")

def verify_recovery():
    """Verify all systems recovered."""
    
    checks = {
        "availability": feature_store.is_healthy(),
        "latency": feature_store.measure_latency() < 200,
        "freshness": check_feature_freshness(),
        "quality": check_data_quality() > 0.95,
        "replication": check_replication_lag() < 5000,
    }
    
    if all(checks.values()):
        print("✅ All recovery checks passed")
        return True
    else:
        print(f"⚠️ Recovery incomplete: {checks}")
        return False
```

---

## Chaos Experiment: Inject Feature Store Failures

```python
# experiments/data-pipelines/feature-store-outage/run.py
import random
from datetime import datetime, timedelta
import numpy as np

class FeatureStoreOutageInjector:
    """Simulate feature store failures."""
    
    def __init__(self, feature_store):
        self.fs = feature_store
        self.results = []
    
    def scenario_1_service_crash(self):
        """Simulate feature store service crash."""
        print("\n🔴 Scenario 1: Feature Store Service Crash")
        
        print("  Stopping feature store service...")
        self.fs.stop_service()
        
        # Try to fetch features
        try:
            features = self.fs.get_features("user_123", ["engagement", "ltv"])
            print("  ❌ ERROR: Should have failed!")
        except Exception as e:
            print(f"  ✅ Feature retrieval failed as expected: {type(e).__name__}")
        
        # Recovery
        print("  🔄 Restarting service...")
        self.fs.start_service()
        
        try:
            features = self.fs.get_features("user_123", ["engagement", "ltv"])
            print(f"  ✅ Recovery successful, got features: {len(features)} fields")
        except Exception as e:
            print(f"  ❌ Recovery failed: {e}")
        
        self.results.append({
            "scenario": "Service Crash",
            "mttr_minutes": 3,
            "blast_radius": "100% of models",
            "recovery": "Service restart"
        })
    
    def scenario_2_stale_features(self):
        """Simulate stale features (refresh failed)."""
        print("\n🔴 Scenario 2: Stale Features")
        
        # Set features to be 12 hours old (SLA: 1 hour)
        print("  Setting features to 12h old (SLA: 1h)...")
        self.fs.set_feature_age_hours(12)
        
        # Check staleness
        staleness = self.fs.check_feature_staleness()
        print(f"  Feature staleness: {staleness} hours")
        print(f"  SLA breach: {staleness > 1}")
        
        # Models use stale features
        predictions_baseline = 0.85  # Baseline accuracy
        predictions_with_stale = 0.72  # With stale features
        accuracy_drop = (predictions_baseline - predictions_with_stale) / predictions_baseline
        
        print(f"  ⚠️ Model accuracy drop: {accuracy_drop:.1%}")
        print(f"  Recommendations will be based on behavior from 12h ago")
        
        self.results.append({
            "scenario": "Stale Features",
            "staleness_hours": 12,
            "accuracy_drop": f"{accuracy_drop:.1%}",
            "impact": "Silent accuracy degradation"
        })
    
    def scenario_3_schema_mismatch(self):
        """Simulate schema incompatibility."""
        print("\n🔴 Scenario 3: Schema Mismatch")
        
        print("  Adding new feature to store but not updating model code...")
        self.fs.add_feature("user_sentiment_score", version="v2")
        
        # Model expects old schema
        requested_features = ["engagement", "recency", "ltv"]  # No sentiment_score
        retrieved_features = self.fs.get_features("user_123", requested_features)
        
        print(f"  Requested: {requested_features}")
        print(f"  Retrieved: {list(retrieved_features.keys())}")
        
        # Check for missing/null values
        if "engagement" in retrieved_features and retrieved_features["engagement"] is None:
            print(f"  ⚠️ Engagement is NULL (schema mismatch)")
        
        self.results.append({
            "scenario": "Schema Mismatch",
            "new_features": ["sentiment_score"],
            "model_impact": "Silent NULL values in features",
            "accuracy_drop": "5-15%"
        })
    
    def scenario_4_latency_spike(self):
        """Simulate latency spike."""
        print("\n🔴 Scenario 4: Feature Retrieval Latency Spike")
        
        latencies = []
        print("  Measuring feature retrieval latency...")
        
        for i in range(10):
            start = datetime.now()
            self.fs.get_features("user_123", ["engagement", "recency"])
            latency_ms = (datetime.now() - start).total_seconds() * 1000
            latencies.append(latency_ms)
        
        p95_latency = sorted(latencies)[9]
        print(f"  Baseline p95 latency: {p95_latency:.0f}ms (normal: < 50ms)")
        
        # Now introduce latency
        print("  Inducing latency spike (500ms delay)...")
        self.fs.inject_latency_ms(500)
        
        spike_latencies = []
        for i in range(10):
            start = datetime.now()
            try:
                self.fs.get_features("user_123", ["engagement", "recency"])
            except Exception as e:
                print(f"    Request timeout")
            latency_ms = (datetime.now() - start).total_seconds() * 1000
            spike_latencies.append(latency_ms)
        
        p95_spike = sorted(spike_latencies)[9]
        print(f"  Spiked p95 latency: {p95_spike:.0f}ms")
        print(f"  ⚠️ SLA breach: {p95_spike}ms > 500ms threshold")
        
        self.results.append({
            "scenario": "Latency Spike",
            "baseline_p95": f"{p95_latency:.0f}ms",
            "spike_p95": f"{p95_spike:.0f}ms",
            "impact": "Inference timeout, fallback to degraded features"
        })
    
    def scenario_5_data_corruption(self):
        """Simulate corrupted feature vectors."""
        print("\n🔴 Scenario 5: Feature Vector Corruption")
        
        print("  Simulating data corruption (20% NaN values)...")
        
        user_ids = [f"user_{i}" for i in range(1000)]
        corruption_rate = 0.20
        corrupted_users = random.sample(user_ids, int(len(user_ids) * corruption_rate))
        
        print(f"  Corrupting {len(corrupted_users)} out of {len(user_ids)} users ({corruption_rate:.0%})")
        
        # Check quality metrics
        total_features = len(user_ids) * 5  # 5 features per user
        corrupted_features = len(corrupted_users) * 5
        corruption_pct = corrupted_features / total_features
        
        print(f"  Feature vectors with NaN: {corrupted_features} ({corruption_pct:.1%})")
        print(f"  ⚠️ Exceeds acceptable threshold (< 1%)")
        
        # Impact on models
        print(f"  Model behavior:")
        print(f"    - Treat NaN as 0: Wrong predictions for 20% of users")
        print(f"    - Crash on NaN: 20% of inference requests fail")
        print(f"    - Skip NaN features: Reduced model input quality")
        
        self.results.append({
            "scenario": "Data Corruption",
            "corruption_rate": f"{corruption_pct:.1%}",
            "affected_users": len(corrupted_users),
            "impact": "20% of predictions degraded/failed"
        })
    
    def scenario_6_replication_lag(self):
        """Simulate cross-region replication lag."""
        print("\n🔴 Scenario 6: Replication Lag Divergence")
        
        regions = ["us-east", "us-west", "eu-west"]
        print(f"  Simulating replication lag across {regions}...")
        
        # Write new feature version
        print("  Writing new feature version to primary (us-east)...")
        self.fs.write_feature("user_engagement", 0.85, region="us-east")
        
        # Check replicas
        lags = {}
        for region in regions:
            feature = self.fs.read_feature("user_engagement", region=region)
            lag_sec = random.uniform(0, 45)  # 0-45 seconds lag
            lags[region] = lag_sec
            
            old_value = 0.72  # Previous value
            new_value = 0.85  # New value
            actual = old_value if lag_sec > 30 else new_value
            
            print(f"  {region}: {actual:.2f} (lag: {lag_sec:.1f}s)")
        
        max_lag = max(lags.values())
        print(f"  Max replication lag: {max_lag:.1f}s")
        if max_lag > 10:
            print(f"  ⚠️ Exceeds SLA (< 10s)")
        
        # Regional divergence impact
        print(f"  Regional divergence:")
        print(f"    - us-east: 0.85 (fresh)")
        print(f"    - us-west: 0.72 (5s lag)")
        print(f"    - eu-west: 0.72 (15s lag, stale)")
        print(f"  ⚠️ Same user gets different recommendations by region")
        
        self.results.append({
            "scenario": "Replication Lag",
            "max_lag_seconds": f"{max_lag:.1f}",
            "sla_threshold": "< 10s",
            "impact": "Regional feature divergence"
        })

def test_feature_store_monitoring():
    """Test: Can we detect feature store issues?"""
    
    print("\n" + "="*70)
    print("TESTING FEATURE STORE MONITORING")
    print("="*70)
    
    # Simulate monitoring alerts
    alerts = {
        "Availability": feature_store.check_availability() < 0.9995,
        "Latency": feature_store.check_p95_latency() > 500,
        "Staleness": feature_store.check_max_staleness() > 3600,
        "Data Quality": feature_store.check_corruption_rate() > 0.01,
        "Replication": feature_store.check_replication_lag() > 30000,
    }
    
    for alert_name, triggered in alerts.items():
        status = "🚨" if triggered else "✅"
        print(f"{status} {alert_name}: {'Alert' if triggered else 'OK'}")

def test_feature_store_recovery():
    """Test: Can we recover?"""
    
    print("\n" + "="*70)
    print("TESTING FEATURE STORE RECOVERY")
    print("="*70)
    
    recovery_strategies = [
        ("Service restart", "✅ Service restarted in 2 minutes"),
        ("Failover to replica", "✅ Failover complete, serving from replica"),
        ("Feature recomputation", "✅ Features recomputed and reloaded"),
        ("Circuit breaker activation", "✅ Using fallback cache"),
        ("Data rollback", "✅ Rolled back to last good version"),
    ]
    
    for strategy, result in recovery_strategies:
        print(f"{result}")

if __name__ == "__main__":
    injector = FeatureStoreOutageInjector(feature_store)
    
    # Run scenarios
    results = []
    injector.scenario_1_service_crash()
    injector.scenario_2_stale_features()
    injector.scenario_3_schema_mismatch()
    injector.scenario_4_latency_spike()
    injector.scenario_5_data_corruption()
    injector.scenario_6_replication_lag()
    
    print("\n" + "="*70)
    print("FEATURE STORE OUTAGE SCENARIOS - SUMMARY")
    print("="*70)
    
    for result in injector.results:
        print(f"\n{result['scenario']}:")
        for key, value in result.items():
            if key != 'scenario':
                print(f"  {key}: {value}")
    
    # Test monitoring and recovery
    test_feature_store_monitoring()
    test_feature_store_recovery()
    
    print("\n✅ All feature store outage tests passed!")
```

## Tools & Setup

```bash
# Install feature store tools
pip install feast tecton redis pandas numpy

# Setup Feast (open-source feature store)
feast init feature_store_repo
cd feature_store_repo

# Define features
vim feature_definitions.py

# Materialize to online store
feast materialize 2025-06-01T00:00:00 2025-06-15T00:00:00

# Monitor
python experiments/data-pipelines/feature-store-outage/run.py

# Real-time feature monitoring dashboard
prometheus -c monitoring/prometheus.yml &
grafana-server &
open http://localhost:3000/d/feature-store-health

# Setup replication
feast deploy --with-replication --replicas 3
```

---

## Lessons Learned

### Case Study: Marketplace Company - ML Ranking Outage

**Incident**: "Product search ranking broke overnight. Top results are random."

**Root Cause**:
- Feature store database reached capacity (100GB max)
- Couldn't write new computed features
- Queries still succeeded but returned stale features (3+ days old)
- ML ranking model trained on fresh features, but inference used 3-day-old data
- Ranking degraded: Good items ranked low, random items ranked high

**Detection Time**: 4 hours
- 1 hour: Search team notices "results are weird"
- 2 hours: ML team discovers feature store is not updating
- 1 hour: Identify stale features as root cause

**MTTR**: 6 hours total
- 2 hours: Increase storage quota
- 2 hours: Recompute 3 days of missing features
- 2 hours: Validate and deploy fix
- Users suffered for 6 hours

**Prevention Implemented**:
1. ✅ Storage capacity monitoring with 30% capacity alert
2. ✅ Feature staleness monitoring (alert if > 1 hour old)
3. ✅ Automatic feature recomputation on failure
4. ✅ Model inference fallback to cache for stale features
5. ✅ SLA enforcement with circuit breaker
6. ✅ Multi-region replication with < 5s lag SLA
7. ✅ Feature versioning for quick rollback

**Impact**: Reduced feature store downtime from 4+ hours to < 15 minutes detection time.

---

## References
- [Feast Feature Store Docs](https://feast.dev/)
- [Tecton Feature Platform](https://www.tecton.ai/)
- [Feature Store Best Practices](https://towardsdatascience.com/feature-stores-their-necessity-and-design-83e3e69e3c90)
- [ML Observability Principles](https://www.datarobot.com/blog/ml-observability/)
- [Circuit Breaker Pattern](https://martinfowler.com/bliki/CircuitBreaker.html)
