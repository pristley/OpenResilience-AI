# Data Pipeline Resilience Patterns

This directory contains comprehensive patterns for handling failure modes in data pipelines, ETL systems, streaming platforms, and batch data processing.

## Patterns

### 1. **Data Lineage Breakage** 📊
[Full Documentation](data-lineage-breakage/)

**Problem**: Metadata diverges from actual pipeline code, breaking downstream queries and analysis.
- **Impact**: Queries return wrong data, ML models retrained on incorrect features
- **Detection**: 30 min - several hours (via reconciliation)
- **Solution**: Lineage validation, automated sync, schema versioning

**Key Scenarios**:
- Job renamed in Airflow but DAG definition not updated
- Column transformations not reflected in lineage metadata
- Atlas/Great Expectations metadata service outage
- Undocumented transforms causing silent data errors

**Code Examples**:
- LineageBreakageInjector (chaos testing)
- dbt manifest validation
- Atlas lineage sync automation
- Schema validation framework

---

### 2. **Data Quality Degradation** 🔍
[Full Documentation](data-quality-degradation/)

**Problem**: Cascading data quality issues (nulls, duplicates, type errors, staleness) break downstream pipelines and ML models.
- **Impact**: Revenue drop, wrong decisions, ML models degrade
- **Cost**: $50K-500K per hour (depending on system)
- **Root Causes**: 6 real scenarios with full impact breakdown

**Key Scenarios**:
- Null rate spikes in critical columns
- Duplicate records appearing mid-pipeline
- Type mismatches breaking joins
- Stale data causing staleness-sensitive metrics
- Statistical anomalies (outliers, distribution shift)
- Referential integrity violations

**Code Examples**:
- Great Expectations validation suite (20+ expectation types)
- Soda SQL observability rules
- DataQualityValidator class (8 methods)
- dbt model tests with cost impact

---

### 3. **Feature Store Outage** 🚀
[Full Documentation](feature-store-outage/)

**Problem**: Feature store unavailability or data issues prevent ML inference, causing model predictions to fail or degrade.
- **Impact**: ML inference stops, stale features used, 15-40% accuracy drop
- **Scenarios**: 6 real-world failures with accuracy impact table

**Key Scenarios**:
- Complete feature store outage (network/hardware failure)
- 3+ day feature staleness from upstream delays
- Schema mismatch between feature definition and stored data
- High latency blocking inference
- Data corruption making features unusable
- Replication lag causing read inconsistency

**Code Examples**:
- FeatureStoreReplication (multi-region with fallback)
- FeatureVersionControl (rollback mechanism)
- FeatureStoreCache (TTL + stale fallback)
- FeatureStoreCircuitBreaker (CLOSED/OPEN/HALF_OPEN states)
- FeatureSLAMonitor (latency + availability tracking)

---

### 4. **Late-Arriving Data** ⏰
[Full Documentation](late-arriving-data/)

**Problem**: Data arrives after processing windows close, causing incomplete results, missing records, and reconciliation failures.
- **Impact**: Incomplete metrics, reconciliation required, $150K+ daily revenue unrecorded (real case)
- **Detection**: 1-5 min (watermark monitoring) to 1-3 days (reconciliation)

**Key Scenarios**:
- Mobile app events queued offline, arrive 45+ minutes late
- Upstream batch job runs slow, delays dependent pipelines by 4+ hours
- Database replication lag (2-3 min normal, 15 min spikes)
- Timezone/clock skew causing events to appear wrong time bucket
- Out-of-order status updates breaking state machines
- Join timeouts when payment event arrives 2+ minutes late

**Code Examples**:
- WindowingStrategy (TUMBLING/SLIDING/SESSION with allowed_lateness)
- WatermarkTracker (event-time watermark management)
- AggregationBuffer (restatement handling)
- EarlyAndLateResults (provisional + final emission)
- TemporalJoinBuffer (grace period joins)
- TimeSkewDetector (timezone correction)

---

### 5. **Late-Binding Resolution** 🔗
[Full Documentation](late-binding-resolution/)

**Problem**: Reference lookups deferred to query time return NULL or stale data when dimensions change or get deleted.
- **Impact**: Queries show NULL, wrong analytics, lost historical context
- **Root Cause**: Deleted user/campaign, dimension updates in place, slow joins

**Key Scenarios**:
- User deleted from dimension table, queries show NULL
- Stale dimension (Type 1 SCD) loses historical user state
- Dimension lookup too slow, query times out
- Type 1 overwrite loses change history needed for analysis
- Temporal join complexity (need AS OF semantics)
- Orphaned references (FK not in dimension)

**Code Examples**:
- Eager enrichment (denormalization) at ingestion
- Type 2 Slowly Changing Dimensions (full history)
- Dimension snapshots (point-in-time accuracy)
- Reference validation (orphaned FK detection)
- Temporal joins (AS OF fact timestamp)

---

### 6. **Replication Lag Divergence** 🌍
[Full Documentation](replication-lag-divergence/)

**Problem**: Cross-region/cross-shard replication lag varies, causing queries to see different values from different replicas (split-brain).
- **Impact**: Analytics divergence, A/B test invalidated, wrong business decisions
- **Scenario**: US-East shows latest, EU-West shows 30s stale, report values diverge

**Key Scenarios**:
- Analytics query divergence (same metric, different per region)
- Join on misaligned replicas returns different results
- A/B test split across regions with different lags
- Cascade failure due to divergence (failover to stale replica)
- Cross-shard join non-determinism

**Code Examples**:
- Bounded staleness queries
- Read-your-write consistency
- Region-locked queries
- Consistent hashing + version tracking

---

### 7. **Schema Evolution Breaks** 🔄
[Full Documentation](schema-evolution-breaks/)

**Problem**: Schema changes (new fields, type changes, removals) break compatibility, causing deserialization errors or silent data loss.
- **Impact**: Pipeline crashes, silent NULL values, wrong analytics
- **Root Cause**: Non-backward-compatible changes deployed

**Key Scenarios**:
- Column renamed (email → email_address)
- Type changed (user_id STRING → INT)
- Column removed (address field deleted)
- Enum value removed (INACTIVE removed from status enum)
- Required field added without default
- Nested schema change (new field added to object)

**Code Examples**:
- Schema versioning with compatibility rules
- Schema Registry integration (Confluent)
- Gradual migration phases
- Backward/forward compatibility validation

---

### 8. **SLA Violation Cascades** 📉
[Full Documentation](sla-violation-cascades/)

**Problem**: One pipeline missing SLA cascades failures downstream, amplifying the business impact across the entire system.
- **Impact**: 1 miss → N downstream misses, exponential failure amplification
- **Probability**: 20 pipelines × 1% each = 18% cascade probability (not 1%!)

**Key Scenarios**:
- Direct cascade (A delays → B delays → C delays)
- Resource contention (critical and non-critical compete)
- Dependency explosion (N pipelines → 1 store, any late breaks SLA)
- Shared infrastructure failure (all slow simultaneously)
- Fallback data corruption (switch to bad backup)

**Code Examples**:
- Resource isolation (Kubernetes bulkheads)
- SLA-aware scheduling with dependency lookahead
- Fallback data management + cache
- Dependency monitoring + alerting

---

## Quick Reference

| Pattern | Key Metric | Priority | Complexity |
|---------|-----------|----------|------------|
| Data Lineage | Lineage-to-code drift | Medium | Low |
| Data Quality | NULL/dupe rate | High | Medium |
| Feature Store | Feature availability | Critical | High |
| Late Arrivals | Watermark lag | High | Medium |
| Late Binding | NULL rate in joins | Medium | Low |
| Replication Lag | Max-min lag spread | Medium | Medium |
| Schema Evolution | Deserialization errors | High | Low |
| SLA Cascades | Cascade depth | Critical | High |

---

## Prevention Checklist

- [ ] Data quality: Great Expectations + Soda SQL rules
- [ ] Lineage: Automated sync (Atlas/dbt manifest)
- [ ] Features: Multi-region replication + cache
- [ ] Late data: Watermark monitoring + grace periods
- [ ] Binding: Type 2 SCD + reference validation
- [ ] Replication: Bounded staleness + region locking
- [ ] Schema: Registry + compatibility testing
- [ ] SLA: Bulkheads + dependency scheduling

---

## Tools & Examples

- **Chaos Experiments**: Inject failures for each pattern
- **Monitoring Dashboards**: Prometheus + Grafana configs
- **Real Case Studies**: Actual incidents + resolutions
- **Production Code**: Ready-to-use implementations

---

## References

- [Apache Beam Windowing](https://beam.apache.org/documentation/programming-guide/#windowing)
- [dbt Lineage](https://docs.getdbt.com/docs/docs-overview)
- [Great Expectations](https://greatexpectations.io/)
- [Feature Store Design](https://www.featurestore.org/)
- [Slowly Changing Dimensions](https://en.wikipedia.org/wiki/Slowly_changing_dimension)
- [Schema Registry](https://docs.confluent.io/kafka/schema-registry/)

---

**Status**: ✅ All 8 patterns complete with code examples, case studies, and monitoring guidance
