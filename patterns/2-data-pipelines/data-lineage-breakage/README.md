# Pattern: Data Lineage Breakage

> When metadata tracking of data transformations goes out of sync with reality, you lose visibility into dependencies and blast radius of failures.

## Quick Summary

**Problem**: Lineage graph diverges from actual pipeline code (jobs renamed, undocumented transformations, schema changes, tool failures)  
**Impact**: Hidden dependencies → cascading failures → slow root cause analysis  
**Detection Time**: Hours to days (silent until downstream failure occurs)  
**Solution**: Declarative lineage tracking (dbt), automated metadata sync, schema validation, active lineage monitoring

---

## Problem Statement

Your data pipeline is a complex DAG: raw data → transformations → feature store → ML models → user-facing decisions. If you can't see the connections (lineage), you can't predict what breaks when something goes wrong.

### Real Scenarios

**Scenario 1: Job Renamed Without Metadata Update**
- Engineer renames Airflow DAG from `user_features_v1` → `user_features_v2`
- dbt or Atlas metadata isn't updated
- Downstream job still tries to read from `user_features_v1` (stale/missing table)
- Data engineer spends 3 hours debugging "missing table" before discovering the rename

**Scenario 2: Column-Level Changes Not Tracked**
- Backend team adds a new column to `users` table
- Lineage tool only tracks table-level dependencies (not columns)
- ETL transformation expects old schema, gets new schema
- Downstream feature breaks silently (null values misinterpreted as 0)

**Scenario 3: Undocumented Manual Transformations**
- Data analyst writes a SQL script to "fix" data directly in prod
- Not registered in Airflow/dbt/Atlas
- ML team thinks data comes from pipeline, actually from manual script
- When analyst leaves, nobody knows how that transformation works

**Scenario 4: Lineage Tool Outage**
- Atlas metadata service goes down
- Lineage queries fail, but pipelines keep running
- You can't see what's breaking during incident
- Recovery is blind: "just restart the DAG and hope"

---

## Why It Matters

### Impact Metric
- **100+ jobs** depend on lineage visibility in typical org
- **5+ hour** MTTR (mean time to recovery) when lineage is broken vs. **30 minutes** when it's good
- **20-50% blast radius** uncertainty when you can't trace dependencies

### Detection Latency
- **Best case** (real-time lineage monitoring): **1-5 minutes**
- **Realistic** (daily lineage validation): **4-24 hours**
- **Worst case** (user reports**: **hours to days**

### Blast Radius
- **Direct**: All downstream jobs fail or produce garbage
- **Indirect**: Reports/dashboards show stale data
- **Data quality**: Bad data enters training pipeline → bad ML models
- **Compliance**: Can't audit data provenance → regulatory risk

---

## How It Fails

### Mechanism

```
1. Lineage metadata source is out of sync with actual code
   ↓
2. Query lineage graph → get incomplete/wrong dependency list
   ↓
3. Downstream system fails (job missing input, schema mismatch, etc.)
   ↓
4. Engineer can't trace back: "Is this job still running? What depends on it?"
   ↓
5. Root cause analysis is slow/blind → longer MTTR
   ↓
6. Data quality cascades worsen while you search
```

### Observable Signals

**Metrics:**
- `lineage_sync_lag` (metadata age vs. actual code): > 1 hour
- `lineage_query_failures`: Any failure to fetch dependencies
- `job_dependency_mismatch`: Declared vs. actual upstream jobs
- `schema_version_drift`: Expected vs. actual column schema

**Logs:**
- "Job X expects table schema {a, b, c} but got {a, b}"
- "Lineage entry for Job Y is stale (last updated 7 days ago)"
- "No upstream dependency found for table Z"
- "Atlas metadata service unreachable"

**Traces:**
- ETL transformation fails at schema validation step
- dbt model fails on `ref()` lookup
- Airflow sensor times out waiting for upstream table
- Column references in downstream job are not in lineage graph

**Health Checks:**
```yaml
- check: "Lineage metadata freshness"
  acceptable: "< 1 hour old"
  
- check: "Lineage service availability"
  acceptable: "> 99.5% uptime"
  
- check: "Schema validation pass rate"
  acceptable: "> 99.9%"
```

### Time to Detect

- **Best case** (automated lineage tests + real-time monitoring): **1-5 min**
  - "Alert: Job X hasn't registered new table in 10 min (should be auto-registered by dbt)"
  
- **Realistic** (daily validation + manual review): **4-24 hours**
  - "Found 3 jobs with missing upstream dependencies in morning lineage audit"
  
- **Worst case** (user reports "my report is broken"): **Hours to days**
  - "I don't know what happened. Can you trace where my data comes from?"

### Blast Radius

- **Immediate**: Downstream job fails on missing input or schema mismatch
- **Cascading**: Dependent report/dashboard becomes stale
- **Training**: Poisoned data enters ML training if you don't catch it
- **Compliance**: Can't produce data lineage audit for regulated system
- **Scope**: Could affect 10s to 100s of downstream jobs

---

## Resilience Strategy

### Prevention

#### 1. **Declarative Lineage (dbt)**
Source-of-truth lineage from code, not from a separate tool:

```yaml
# models/features/user_features.yml
version: 2

models:
  - name: user_features
    description: "User-level aggregated features for ML"
    columns:
      - name: user_id
        description: "PK"
        tests:
          - not_null
          - unique
      - name: signup_date
        description: "When user registered"
        tests:
          - not_null
    
    # Lineage is declared here via refs
    # dbt generates DAG automatically
```

```sql
-- models/features/user_features.sql
{{
  config(
    materialized='table',
    tags=['daily', 'critical']
  )
}}

select
  u.user_id,
  u.signup_date,
  count(o.order_id) as order_count
from {{ ref('stg_users') }} u
left join {{ ref('stg_orders') }} o
  on u.user_id = o.user_id
group by 1, 2
```

**Why it helps:**
- ✅ Lineage lives in version control (Git history)
- ✅ Renaming a model updates lineage automatically
- ✅ Column-level lineage from `ref()` and `source()` calls
- ✅ Tests validate schema at runtime

#### 2. **Automated Metadata Sync**
Register job lineage automatically as code changes:

```python
# scripts/sync_lineage_to_atlas.py
import os
from apache_atlas.client import AtlasClient
import yaml

def sync_airflow_to_atlas():
    """Read Airflow DAGs, register in Atlas."""
    atlas = AtlasClient("http://atlas:21000", ("admin", "admin"))
    
    dags_dir = "/opt/airflow/dags"
    for dag_file in os.listdir(dags_dir):
        if dag_file.endswith(".py"):
            # Parse DAG definition
            dag_name = dag_file.replace(".py", "")
            upstream_table = get_upstream_table_from_dag(dag_file)
            downstream_table = get_downstream_table_from_dag(dag_file)
            
            # Register lineage in Atlas
            lineage_entity = {
                "attributes": {
                    "name": dag_name,
                    "qualifiedName": f"airflow.dag.{dag_name}",
                    "inputs": [upstream_table],
                    "outputs": [downstream_table],
                }
            }
            atlas.entity_post(lineage_entity)
            print(f"✅ Registered {dag_name} in Atlas")

if __name__ == "__main__":
    sync_airflow_to_atlas()
```

**Why it helps:**
- ✅ Metadata stays in sync as jobs change
- ✅ Run on every Git commit → always up-to-date
- ✅ Central source of truth (Atlas/OpenMetadata)

#### 3. **Schema Validation at Every Stage**
Detect schema drift early:

```python
# tasks/validate_schema.py
import great_expectations as ge

def validate_incoming_schema(table_name, expected_schema):
    """Check table schema before transformation."""
    df = ge.read_csv(f"/data/{table_name}.csv")
    
    # Define expected schema
    expectations = {
        "user_id": {"type": "integer", "nullable": False},
        "email": {"type": "string", "nullable": False},
        "created_at": {"type": "datetime", "nullable": False},
    }
    
    for col, spec in expectations.items():
        df.expect_column_to_exist(col)
        df.expect_column_values_to_not_be_null(col)
        df.expect_column_values_to_be_of_type(col, spec["type"])
    
    # Run validation
    validation = df.validate()
    if not validation["success"]:
        raise ValueError(f"Schema validation failed: {validation}")
    
    print(f"✅ Schema valid for {table_name}")
```

**Why it helps:**
- ✅ Catch schema mismatches before transformation breaks
- ✅ Early warning on upstream changes
- ✅ Prevents garbage data from propagating

#### 4. **Undocumented Transformation Registry**
Require all transformations to be registered:

```yaml
# transforms/registry.yml
transforms:
  - name: "fix_user_duplicates"
    description: "Remove duplicate user IDs (v2 duplicate key bug)"
    source_table: "users_raw"
    target_table: "users_cleaned"
    owner: "data-eng-team"
    created_date: "2025-06-15"
    status: "active"
    lineage:
      inputs:
        - table: "users_raw"
          columns: ["user_id", "email"]
      outputs:
        - table: "users_cleaned"
          columns: ["user_id", "email"]
    
  - name: "enrich_orders_with_customer_segment"
    description: "Join orders with customer segment (manual lookup table)"
    source_table: "orders"
    lookup_table: "customer_segments_manual"
    target_table: "orders_enriched"
    owner: "analytics-team"
    created_date: "2025-05-20"
```

**Why it helps:**
- ✅ All manual transformations are documented
- ✅ Ownership is clear → know who to ask
- ✅ Lineage includes undocumented steps

---

### Detection

```yaml
monitoring:
  
  # 1. Lineage Freshness
  alerts:
    - name: LineageStale
      metric: "lineage_metadata_age_seconds"
      threshold: "> 3600"  # 1 hour
      severity: "warning"
      action: "Trigger lineage sync job"
    
    - name: LineageServiceDown
      metric: "atlas_service_up"
      threshold: "== 0"
      severity: "critical"
      action: "Page oncall, fall back to version-control lineage"
  
  # 2. Dependency Validation
  alerts:
    - name: MissingUpstreamDependency
      metric: "job_upstream_missing_count"
      threshold: "> 0"
      severity: "critical"
      action: "Check if upstream job was deleted/renamed"
    
    - name: SchemaVersionMismatch
      metric: "schema_validation_failures"
      threshold: "> 5"
      severity: "high"
      action: "Review schema changes in upstream table"
  
  # 3. Lineage Completeness
  dashboards:
    - name: "Lineage Coverage"
      metric: "pct_jobs_with_lineage"
      target: "> 95%"
    
    - name: "Column-Level Lineage"
      metric: "pct_columns_traced_end_to_end"
      target: "> 80%"

  # 4. Health Checks (Daily)
  batch_jobs:
    - job: "validate_lineage_graph"
      schedule: "0 6 * * *"  # 6 AM daily
      checks:
        - "All registered jobs have upstream/downstream entries"
        - "No circular dependencies in DAG"
        - "All table schemas match lineage expectations"
        - "Lineage metadata age < 1 hour"
```

### Recovery

#### Step 1: Restore Lineage Visibility
```bash
# If Atlas is down, fall back to Git-based lineage
# Re-register all dbt models from version control
dbt parse > manifest.json

# Extract lineage from dbt manifest
python -m scripts.extract_lineage_from_manifest \
  --manifest manifest.json \
  --output lineage.json
```

#### Step 2: Find Root Cause
```bash
# Query lineage history: "Show me all jobs that depend on X"
python -c "
from lineage_query import LineageStore
store = LineageStore('atlas')

# Backward: What created this table?
sources = store.find_sources('orders_with_segment')
print('Sources:', sources)

# Forward: What consumes this table?
consumers = store.find_consumers('orders_with_segment')
print('Consumers:', consumers)
"
```

#### Step 3: Validate Before Proceeding
```bash
# Run all downstream schema validations
dbt test --select "state:modified+ state:new+"

# If schema mismatches, hold jobs until fixed
if dbt test fails; then
  echo "Schema validation failed. Not running downstream jobs."
  exit 1
fi
```

#### Step 4: Declare Emergency Lineage
```yaml
# For undocumented transformations discovered during incident
emergency_lineage:
  - name: "user_segments_manual_fix"
    inputs: ["users_raw"]
    outputs: ["ml_training_features"]
    description: "TEMPORARY: Direct SQL fix by John Q. on 2025-06-15 14:30 UTC"
    expires: "2025-06-22"
    status: "REQUIRES_DOCUMENTATION"
    root_cause: "Atlas was down during data refresh"
```

---

## Chaos Experiment: Inject Lineage Breakage

```python
# experiments/data-pipelines/lineage-breakage/run.py
import os
import random
from typing import Dict, List

class LineageBreakageInjector:
    """Simulate lineage breakage scenarios."""
    
    def __init__(self, airflow_dags_dir: str, atlas_client):
        self.dags_dir = airflow_dags_dir
        self.atlas = atlas_client
    
    def scenario_1_rename_job_without_metadata_update(self):
        """Rename Airflow DAG but don't update Atlas."""
        print("\n🔴 Scenario 1: Job renamed without metadata sync")
        
        # Rename DAG file
        old_dag = os.path.join(self.dags_dir, "user_features_v1.py")
        new_dag = os.path.join(self.dags_dir, "user_features_v2.py")
        
        with open(old_dag) as f:
            content = f.read()
        
        with open(new_dag, 'w') as f:
            f.write(content.replace("dag_id='user_features_v1'", "dag_id='user_features_v2'"))
        
        # BUT: Don't update Atlas
        # (Simulate engineer forgetting to sync)
        print(f"✅ Renamed {old_dag} → {new_dag}")
        print("❌ Atlas still has old lineage: user_features_v1")
        
        # Downstream job tries to find old table
        downstream_job = """
        SELECT * FROM user_features_v1  -- This doesn't exist anymore!
        """
        print(f"\n⚠️ Downstream job fails:\n{downstream_job}")
        
        return {
            "scenario": "Job renamed",
            "lineage_lag": "∞ (completely broken)",
            "time_to_detect": "When job fails (30+ min)",
            "recovery_time": "MTTR 3 hours (searching for renamed job)",
        }
    
    def scenario_2_schema_change_not_tracked(self):
        """Backend adds column, lineage tool doesn't track it."""
        print("\n🔴 Scenario 2: Column added upstream, not in lineage")
        
        old_schema = ["user_id", "email", "created_at"]
        new_schema = ["user_id", "email", "created_at", "country"]
        
        # Lineage tool only tracks table-level, not columns
        print(f"Old schema in users table: {old_schema}")
        print(f"New schema in users table (actual): {new_schema}")
        print("⚠️ Lineage tool still shows: columns = {user_id, email, created_at}")
        
        # Downstream transformation assumes old schema
        downstream_transform = """
        SELECT user_id, email, signup_date FROM users
        WHERE LENGTH(email) > 5
        GROUP BY country  -- Column doesn't exist in old schema!
        """
        print(f"\n❌ Downstream transform fails:\n{downstream_transform}")
        
        return {
            "scenario": "Column added, not tracked",
            "lineage_lag": "Column-level mismatch",
            "time_to_detect": "When transformation runs (varies)",
            "recovery_time": "MTTR 1-2 hours (schema debugging)",
        }
    
    def scenario_3_undocumented_transformation(self):
        """Data analyst manually fixes data, nobody registers it."""
        print("\n🔴 Scenario 3: Undocumented manual SQL transformation")
        
        manual_sql = """
        -- Direct SQL fix in production (2025-06-15 14:30)
        -- Analyst: John Q.
        UPDATE users
        SET email = LOWER(email)
        WHERE email IS NOT NULL;
        """
        
        print(f"Manual transformation applied:\n{manual_sql}")
        print("⚠️ NOT registered in Airflow, dbt, or Atlas")
        print("❌ ML team thinks data comes from automated pipeline")
        
        lineage_query = "SELECT * FROM dbt manifest WHERE output='users'"
        print(f"\nLineage query shows: uses raw 'users' table, no mention of manual fix")
        
        return {
            "scenario": "Undocumented transformation",
            "lineage_lag": "100% incomplete",
            "time_to_detect": "When analyst leaves or data breaks (days)",
            "recovery_time": "MTTR unknown (nobody knows the transformation)",
        }
    
    def scenario_4_lineage_service_outage(self):
        """Atlas goes down during incident."""
        print("\n🔴 Scenario 4: Atlas metadata service outage")
        
        print("Atlas service status: DOWN")
        print("Lineage queries: ❌ FAILED")
        print("Can you see dependencies? NO")
        print("Can you trace blast radius? NO")
        
        # Incident happens while Atlas is down
        print("\n🚨 Meanwhile: A job fails in production")
        print("You try to find what broke: atlas_client.get_lineage('job_x')")
        print("Error: Connection timeout to Atlas (service down)")
        
        return {
            "scenario": "Lineage service outage",
            "lineage_lag": "Unable to query",
            "time_to_detect": "MTTR increases by 2-3x",
            "recovery_time": "Blind recovery (restart and pray)",
        }

def test_lineage_breakage_detection():
    """Test: Can monitoring detect lineage breakage?"""
    from lineage_monitor import LineageMonitor
    
    monitor = LineageMonitor()
    
    # Simulate lineage metadata lag
    lineage_age_seconds = 3610  # 1 hour 10 minutes
    alert = monitor.check_lineage_freshness(lineage_age_seconds)
    assert alert["triggered"] == True, "Should alert when lineage > 1 hour old"
    assert alert["severity"] == "warning"
    
    print("✅ Lineage freshness alert triggered")
    
    # Simulate missing upstream dependency
    job_graph = {
        "job_x": {"upstream": ["table_a", "table_b"]},
        "table_a": {"exists": False},  # Deleted but not in lineage yet
    }
    
    missing = monitor.find_missing_dependencies(job_graph)
    assert len(missing) > 0, "Should detect missing upstream"
    
    print("✅ Missing dependency alert triggered")

def test_lineage_recovery():
    """Test: Can we recover lineage?"""
    from lineage_restore import LineageRestorer
    
    restorer = LineageRestorer()
    
    # Restore from Git (dbt manifest)
    restored = restorer.restore_from_git_history(
        repo_path="/data/dbt-project",
        branch="main"
    )
    
    assert restored["status"] == "ok", "Should restore lineage from Git"
    assert len(restored["models"]) > 100, "Should find all dbt models"
    
    print(f"✅ Restored lineage for {len(restored['models'])} models")
    
    # Validate restored lineage is complete
    coverage = restorer.calculate_lineage_coverage(restored)
    assert coverage["pct_jobs_with_lineage"] > 0.90, "Should cover > 90% of jobs"
    
    print(f"✅ Lineage coverage: {coverage['pct_jobs_with_lineage']:.1%}")

if __name__ == "__main__":
    import sys
    from apache_atlas.client import AtlasClient
    
    # Setup
    injector = LineageBreakageInjector(
        airflow_dags_dir="/opt/airflow/dags",
        atlas_client=AtlasClient("http://atlas:21000")
    )
    
    # Run scenarios
    results = []
    results.append(injector.scenario_1_rename_job_without_metadata_update())
    results.append(injector.scenario_2_schema_change_not_tracked())
    results.append(injector.scenario_3_undocumented_transformation())
    results.append(injector.scenario_4_lineage_service_outage())
    
    print("\n" + "="*60)
    print("LINEAGE BREAKAGE SCENARIOS - SUMMARY")
    print("="*60)
    for i, result in enumerate(results, 1):
        print(f"\n{i}. {result['scenario']}")
        print(f"   Lineage Lag: {result['lineage_lag']}")
        print(f"   Time to Detect: {result['time_to_detect']}")
        print(f"   Recovery Time: {result['recovery_time']}")
    
    # Test detection
    print("\n" + "="*60)
    print("TESTING DETECTION & RECOVERY")
    print("="*60)
    test_lineage_breakage_detection()
    test_lineage_recovery()
    
    print("\n✅ All lineage breakage tests passed!")
```

## Tools & Setup

```bash
# Install dependencies
pip install apache-atlas dbt-core great-expectations pydantic

# Setup dbt lineage tracking
dbt init my_project
cd my_project

# Generate dbt manifest (source of truth for lineage)
dbt parse
dbt docs generate

# Setup Apache Atlas for centralized lineage
docker run -d \
  -p 21000:21000 \
  -e ATLAS_SERVER_PORT=21000 \
  apache/atlas:latest

# Setup OpenMetadata (alternative to Atlas)
docker run -d \
  -p 8585:8585 \
  openmetadata/server:latest

# Sync lineage to Atlas
python scripts/sync_lineage_to_atlas.py

# Run validation
python experiments/data-pipelines/lineage-breakage/run.py

# Monitor lineage health (daily)
0 6 * * * /opt/scripts/validate_lineage_graph.sh
```

---

## Lessons Learned

### Case Study: E-Commerce Company Data Lake

**Incident**: ML recommendations team says "Our model accuracy dropped 15% overnight. What changed in the data pipeline?"

**Root Cause**: 
- Data engineering team refactored Airflow DAGs
- Renamed `compute_user_features` → `features_v2` 
- Forgot to update dbt model `ref()` calls
- Column `user_lifetime_value` went missing (not in renamed output)
- ML model started using default value (0) instead of real value
- Recommendations became garbage

**Detection Time**: 4 hours (ML team noticed accuracy drop in morning metrics review)

**MTTR**: 6 hours total
- 2 hours: "Where did the data go?"
- 2 hours: "Found the renamed DAG, now what broke downstream?"
- 2 hours: "Re-ran pipeline with correct lineage, validation passed"

**Prevention Implemented**:
1. ✅ Declared all Airflow lineage in dbt (single source of truth)
2. ✅ Column-level lineage tracking in dbt manifest
3. ✅ Automated lineage sync to Atlas on every Git commit
4. ✅ Automated schema validation in pre-commit hooks
5. ✅ Daily lineage coverage dashboard (alert if < 95%)
6. ✅ Lineage service SLA: 99.95% uptime with fallback to Git-based lineage

**Impact**: Reduced incident response time for data issues from 4-6 hours to < 30 minutes.

---

## References
- [dbt Metadata Guide](https://docs.getdbt.com/docs/guides/dbt-metadata)
- [Apache Atlas Lineage](https://atlas.apache.org/)
- [OpenMetadata Lineage](https://openmetadata.io/)
- [Great Expectations Schema Validation](https://greatexpectations.io/expectations/)
- [Data Lineage Best Practices](https://www.eckerson.com/articles/data-lineage)
