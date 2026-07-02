# Pattern: Data Quality Degradation

> When data quality drops (nulls, duplicates, type mismatches, staleness, anomalies), garbage flows into downstream systems, poisoning models, reports, and decisions.

## Quick Summary

**Problem**: Data becomes incomplete (nulls), inconsistent (type mismatches), incorrect (duplicates/anomalies), or stale (not updated)  
**Impact**: Bad data → bad models → bad decisions → business impact  
**Detection Time**: Minutes (with monitoring) to hours/days (without)  
**Solution**: Automated data validation (Great Expectations, Soda SQL, dbt tests), anomaly detection, quality SLAs, circuit breakers

---

## Problem Statement

Your data pipeline is only as good as its data. Once data quality degrades, every downstream system suffers:
- ML models train on garbage → predictions are wrong
- Reports show wrong numbers → stakeholders make wrong decisions
- Data warehouse contains poison → cascading corruption

### Real Scenarios

**Scenario 1: Null Value Explosion**
- Backend stops writing to a field (schema change, code bug, new service doesn't populate it)
- 50% of `user_email` values become NULL
- Validation layer isn't strict enough to catch it
- Email notification system breaks (can't send mail to NULL)
- Marketing dashboard shows "no email" for 50% of users
- Data scientist builds feature store row: `sum(orders) / count(users)` = different result

**Scenario 2: Duplicate Key Explosion**
- Message queue buffering during maintenance → jobs process same records twice
- ETL doesn't have idempotency safeguards
- `order_id` appears 2x in order table
- Revenue is double-counted in reports
- "Sales up 50% today!" → actually no change, just duplicates
- Finance team reconciliation fails

**Scenario 3: Type Mismatch / Encoding Errors**
- Backend team switches from ISO-8601 dates to Unix timestamps
- ETL assumes ISO-8601, passes strings to SQL
- Database stores `"2025-06-15"` as text instead of DATE type
- Downstream queries using `WHERE date > '2025-01-01'` fail (string comparison)
- Feature "days_since_signup" becomes nonsensical
- Sorting/filtering breaks silently

**Scenario 4: Stale Data (Not Updated)**
- Feature refresh job fails but nobody notices for 3 days
- Model uses 3-day-old features instead of real-time
- Recommendations are based on yesterday's behavior
- User sees product they already bought recommended again
- ML model latency increases (feature retrieval hanging)

**Scenario 5: Outliers & Anomalies**
- A bug causes one upstream service to write `1000000000` as default value instead of `0`
- 0.1% of records have this anomalous value
- Aggregations become skewed: `AVG(transaction_amount)` goes from $50 to $500
- Risk model sees fake "high spenders" → wrong segmentation
- Fraud detection triggers on normal transactions with bad features

**Scenario 6: Inconsistent Data Across Systems**
- Same customer ID represents different entities in `users` vs. `accounts` tables
- One system uses `user_id=123`, another uses `customer_id=456` for same person
- Joins produce wrong results or duplicates
- Reconciliation fails
- Customer 360 view is fragmented

---

## Why It Matters

### Impact Metrics

**Data Quality Downtime Costs:**
| Severity | Cost per Hour | Typical Duration | Example |
|----------|---------------|-----------------|---------|
| **Silent corruption** (bad data, no alert) | $50K-500K | 2-24 hours | Duplicate orders double-counted |
| **Data unavailability** (missing completely) | $100K-1M | 1-4 hours | Feature store outage → models offline |
| **Type mismatches** (silent errors) | $10K-100K | 4-12 hours | Date calculations wrong, report looks OK |
| **Stale data** (not refreshing) | $5K-50K | per day | Model predictions based on old data |

**Blast Radius:**
- 5 bad records → affects 5 users (contained)
- 5% bad records → affects 100K users (significant)
- 50% bad records → entire system unreliable (critical)

**Detection Latency:**
- **Best case** (real-time validation): **30 seconds to 2 minutes**
- **Realistic** (hourly batch validation): **1-4 hours**
- **Worst case** (user complaints): **4-48 hours**

### Why It Matters for Different Domains

| Domain | Impact | Example |
|--------|--------|---------|
| **ML/Recommendations** | Bad training data → bad predictions | Duplicate orders in training → wrong churn model |
| **Finance/Billing** | Wrong revenue numbers → regulatory risk | Duplicates cause overcharging |
| **Marketing** | Wrong segmentation → wasted spend | NULL emails → campaigns don't send |
| **Compliance** | Can't audit data provenance → audit failures | Can't prove data integrity |

---

## How It Fails

### Mechanism

```
1. Upstream change happens (code deploy, schema change, maintenance)
   ↓
2. Data quality drops (nulls, duplicates, type mismatch, staleness, anomalies)
   ↓
3. Quality checks are either:
   a) Not in place → issue propagates silently
   b) Too lenient → catches nothing
   c) Not monitored → alerts go unnoticed
   ↓
4. Bad data enters downstream systems (feature store, data warehouse, ML models)
   ↓
5. Cascading failures:
   - ML predictions wrong
   - Reports show garbage
   - Decisions based on bad data
   ↓
6. Issue discovered via:
   - User complaints ("Why is this data wrong?")
   - Metrics anomalies ("Why did accuracy drop?")
   - Manual audits ("We found duplicate orders")
   ↓
7. Root cause analysis is hard without lineage + versioning
```

### Observable Signals

#### **Metrics to Monitor**

```yaml
quality_metrics:
  
  # 1. Null/Missing Values
  - name: "null_rate_by_column"
    definition: "count(NULL values) / count(total values)"
    alert_threshold: "> 5%"
    acceptable_by_column:
      user_id: "== 0%"  # Never NULL (PK)
      email: "< 1%"      # Sometimes NULL (optional)
      middle_name: "< 20%"  # Often NULL (optional)
  
  # 2. Duplicates
  - name: "duplicate_key_rate"
    definition: "count(PK with duplicates) / count(total PKs)"
    alert_threshold: "> 0.1%"
  
  - name: "duplicate_row_rate"
    definition: "count(exact row duplicates) / count(total rows)"
    alert_threshold: "> 0.01%"
  
  # 3. Type Mismatches
  - name: "schema_validation_failures"
    definition: "count(rows failing schema check) / count(total rows)"
    alert_threshold: "> 0.5%"
  
  - name: "type_cast_failures"
    definition: "count(unable to cast to expected type) / count(attempts)"
    alert_threshold: "> 0%"  # Any failure is an issue
  
  # 4. Freshness / Staleness
  - name: "data_freshness_lag"
    definition: "now() - max(updated_at)"
    alert_threshold: "> 2 hours"  # Expected refresh every 2 hours
    
  - name: "pct_rows_stale"
    definition: "count(rows with updated_at > 24h ago) / count(total rows)"
    alert_threshold: "> 10%"
  
  # 5. Anomalies & Outliers
  - name: "distribution_drift"
    definition: "KL divergence(current_distribution, baseline)"
    alert_threshold: "> 0.5"  # Statistical distance too large
  
  - name: "outlier_rate"
    definition: "count(values > 3σ from mean) / count(total values)"
    alert_threshold: "> 1%"  # Expect ~0.3% normally
  
  - name: "zscore_spike"
    definition: "count(|value - mean| > 4σ)"
    alert_threshold: "> 0.01%"
  
  # 6. Consistency
  - name: "referential_integrity_violations"
    definition: "count(FK not in parent table) / count(total FKs)"
    alert_threshold: "> 0%"
  
  - name: "cross_table_inconsistency"
    definition: "count(customer_id in orders not in users) / count(orders)"
    alert_threshold: "> 0%"
  
  # 7. Completeness
  - name: "row_completeness"
    definition: "count(non-null values) / (count(rows) * count(columns))"
    alert_threshold: "< 95%"
  
  - name: "expected_row_count"
    definition: "count(rows in table X)"
    alert_threshold: "< 90% of expected"  # Detect missing records
```

#### **Log Patterns**

```
[ERROR] Null value check failed: column 'user_email' has 50 NULL values (5x normal)
[WARN]  Duplicate key detected: PK 'order_123' appears 2 times in orders table
[ERROR] Type mismatch: Expected DATE, got TEXT for column 'signup_date'
[ERROR] Freshness check failed: data not updated for 4 hours (threshold: 2h)
[WARN]  Outlier detected: transaction_amount = $999,999 (expected < $10,000)
[ERROR] Referential integrity violated: order.user_id=999 not in users table
[CRIT]  Distribution drift alert: feature 'user_age' KL divergence = 0.8
```

#### **Trace Patterns**

```
Trace: data_ingestion_pipeline
├─ [OK] Extract from source (1000 rows)
├─ [OK] Schema validation (1000 rows pass)
├─ [FAIL] Null check (50 rows have NULL in 'email')
├─ [FAIL] Uniqueness check (5 duplicate order_ids)
├─ [WARN] Type casting (1 row can't cast 'date' field)
└─ [BLOCKED] Load to warehouse (validation failed, no data loaded)

Trace: feature_store_refresh
├─ [OK] Join users + orders (10M rows)
├─ [WARN] Freshness check (5% of data > 24h old)
├─ [FAIL] Distribution check (avg_age went from 35 to 45, drift = 0.6)
└─ [PARTIAL] Loaded with warnings (features available but quality flagged)
```

#### **Health Checks (Real-Time)**

```yaml
health_checks:
  - check: "Data freshness"
    query: "SELECT MAX(updated_at) FROM orders"
    acceptable: "< 2 hours old"
    frequency: "every 15 min"
  
  - check: "Null rate for critical fields"
    query: "SELECT COUNT(*) WHERE email IS NULL / COUNT(*)"
    acceptable: "< 1%"
    frequency: "every hour"
  
  - check: "Duplicate keys"
    query: "SELECT COUNT(*) - COUNT(DISTINCT order_id) FROM orders"
    acceptable: "= 0"
    frequency: "every hour"
  
  - check: "Row count anomaly"
    query: "SELECT COUNT(*) FROM daily_orders"
    acceptable: "within [expected_min, expected_max]"
    frequency: "after each load"
  
  - check: "Type validation"
    query: "SELECT COUNT(*) FROM orders WHERE CAST(order_date AS DATE) FAILS"
    acceptable: "= 0"
    frequency: "every 30 min"
```

### Time to Detect

- **Best case** (automated, real-time validation): **30 seconds - 2 minutes**
  - "Alert: NULL rate in 'user_email' jumped from 0.5% to 5% in last hour"
  
- **Realistic** (hourly validation + dashboard review): **1-4 hours**
  - "Morning data quality report shows duplicate rate spiked overnight"
  
- **Worst case** (no validation, user discovers): **4-24+ hours**
  - "Customer calls: 'Why am I seeing a duplicate charge?' → data scientist investigates"

### Blast Radius

- **Direct Impact**: ML model predictions, reports, dashboards
- **Downstream**: Business decisions based on bad data
- **Indirect**: User experience (duplicate emails, wrong recommendations)
- **Scope**: Can be 0.01% (5 records) to 100% (entire table) depending on issue
- **Duration**: Minutes (if caught immediately) to days (if silent)

---

## Resilience Strategy

### Prevention

#### **1. Great Expectations Data Validation**

```python
# expectations/suite_users.py
import great_expectations as gx
from great_expectations.core.batch import RuntimeBatchRequest

def create_users_expectations():
    """Define expectations for users table."""
    
    context = gx.get_context()
    suite = context.create_expectation_suite(
        expectation_suite_name="users_quality_suite"
    )
    
    # Primary key uniqueness
    suite.add_expectation(
        gx.expectations.ExpectColumnValuesToBeUnique(
            column="user_id"
        )
    )
    
    # Required fields (not null)
    for col in ["user_id", "email", "created_at"]:
        suite.add_expectation(
            gx.expectations.ExpectColumnValuesToNotBeNull(
                column=col
            )
        )
    
    # Email format validation
    suite.add_expectation(
        gx.expectations.ExpectColumnValuesToMatchRegex(
            column="email",
            regex=r"^[^@]+@[^@]+\.[^@]+$",
            mostly=0.99  # Allow 1% non-matching (typos, test emails)
        )
    )
    
    # created_at should be recent (not in future, not too old)
    suite.add_expectation(
        gx.expectations.ExpectColumnValuesToBeBetween(
            column="created_at",
            min_value=datetime.now() - timedelta(days=10*365),  # 10 years
            max_value=datetime.now(),
            mostly=0.995
        )
    )
    
    # age should be reasonable (if present)
    suite.add_expectation(
        gx.expectations.ExpectColumnValuesToBeBetween(
            column="age",
            min_value=13,
            max_value=150,
            mostly=0.95  # ~5% missing/invalid
        )
    )
    
    # No duplicate emails (if specified as unique)
    suite.add_expectation(
        gx.expectations.ExpectColumnValuesToBeUnique(
            column="email"
        )
    )
    
    # Table size hasn't dropped unexpectedly (data loss check)
    suite.add_expectation(
        gx.expectations.ExpectTableRowCountToBeBetween(
            min_value=1000000,  # Should have at least 1M users
            max_value=500000000  # Should have less than 500M users
        )
    )
    
    context.save_expectation_suite(suite)
    return suite

def validate_users_batch(df):
    """Run validation on users dataframe."""
    
    context = gx.get_context()
    suite = context.get_expectation_suite("users_quality_suite")
    
    batch_request = RuntimeBatchRequest(
        datasource_name="pandas_source",
        data_connector_name="default_runtime_data_connector",
        data_asset_name="users_dataframe",
        runtime_parameters={"dataframe": df}
    )
    
    validator = context.get_validator(
        batch_request=batch_request,
        expectation_suite_name="users_quality_suite"
    )
    
    checkpoint = context.add_or_update_checkpoint(
        name="users_quality_checkpoint",
        config={
            "class_name": "SimpleCheckpoint",
            "validations": [{
                "batch_request": batch_request,
                "expectation_suite_name": "users_quality_suite"
            }]
        }
    )
    
    result = checkpoint.run()
    
    # Detailed report
    print(f"\n{'='*60}")
    print(f"Data Quality Validation Report: USERS")
    print(f"{'='*60}")
    print(f"Status: {'✅ PASSED' if result['success'] else '❌ FAILED'}")
    print(f"Rows Validated: {len(df):,}")
    print(f"Expectations Checked: {len(result['run_results'][0]['validation_result']['results'])}")
    
    for expectation_result in result['run_results'][0]['validation_result']['results']:
        expectation_type = expectation_result['expectation_config']['expectation_type']
        success = expectation_result['success']
        result_data = expectation_result.get('result', {})
        
        status = "✅" if success else "❌"
        print(f"\n{status} {expectation_type}")
        
        if not success:
            print(f"   Failed rows: {result_data.get('unexpected_count', '?')}")
            print(f"   Sample: {result_data.get('unexpected_index_list', [])[:3]}")
    
    return result['success']
```

#### **2. Soda SQL Data Observability**

```yaml
# sodacl/orders.yml
checks for orders:
  
  # Freshness
  - freshness(updated_at) < 2h:
      name: "Orders data is fresh"
  
  # Completeness (nulls)
  - missing_count(order_id) = 0:
      name: "No missing order IDs"
  
  - missing_percent(user_id) < 1%:
      name: "User IDs mostly not null"
  
  # Duplicates
  - duplicate_count(order_id) = 0:
      name: "No duplicate order IDs"
  
  # Validity (type checks)
  - invalid_count(order_date) = 0:
      name: "All order dates are valid DATE"
      test_type: "format"
      format: "%Y-%m-%d"
  
  - valid_count(status) > 99%:
      name: "Status values are in allowed set"
      valid_values: ['pending', 'completed', 'cancelled', 'refunded']
  
  # Accuracy (value ranges)
  - min(order_amount) > 0:
      name: "No negative order amounts"
  
  - max(order_amount) < 1000000:
      name: "No suspiciously large orders"
  
  # Consistency
  - values in (order.user_id) must exist in (users.user_id):
      name: "All orders reference valid users"
  
  # Outliers
  - avg(order_amount) between 40 and 60:
      name: "Average order amount is normal (not inflated/deflated)"
  
  - stddev(order_amount) < 100:
      name: "Order amount distribution is normal"
  
  # Row count
  - row_count > 100000:
      name: "Orders table has expected size"
  
  - row_count between 900000 and 1100000:
      name: "Order count within expected bounds"
```

#### **3. dbt Data Tests**

```yaml
# models/staging/stg_orders.yml
version: 2

models:
  - name: stg_orders
    description: "Staging model for raw orders"
    
    columns:
      - name: order_id
        description: "Primary key"
        tests:
          - unique
          - not_null
      
      - name: user_id
        description: "Foreign key to users"
        tests:
          - not_null
          - relationships:
              to: ref('stg_users')
              field: user_id
      
      - name: order_date
        tests:
          - dbt_expectations.expect_column_values_to_be_of_type:
              column_type: date
          - dbt_expectations.expect_column_values_to_be_between:
              min_value: "2015-01-01"
              max_value: "today"
          - dbt_utils.not_constant
      
      - name: order_amount
        tests:
          - dbt_expectations.expect_column_values_to_be_positive
          - dbt_expectations.expect_column_values_to_be_less_than:
              value: 1000000
          - dbt_expectations.expect_column_mean_to_be_between:
              min_value: 40
              max_value: 60
      
      - name: status
        tests:
          - accepted_values:
              values: ['pending', 'completed', 'cancelled', 'refunded']
      
      - name: email
        tests:
          - dbt_expectations.expect_column_values_to_match_regex:
              regex: '^[^@]+@[^@]+\.[^@]+$'
              mostly: 0.99

# Generic test for no recent duplicates (table-level)
generic_tests:
  - name: no_duplicates_in_key
    description: "Check for duplicate keys (modified today)"
    
  - name: column_values_in_set
    description: "Values match allowed set"

tests:
  - name: assert_order_amount_not_inflated
    description: "Alert if average order_amount > $100 (usually $50)"
    sql: |
      SELECT AVG(order_amount) as avg_amount
      FROM {{ ref('stg_orders') }}
      HAVING avg_amount > 100
  
  - name: assert_no_future_dates
    description: "Alert if order_date is in future"
    sql: |
      SELECT COUNT(*) as future_count
      FROM {{ ref('stg_orders') }}
      WHERE order_date > CURRENT_DATE
      HAVING future_count > 0
```

#### **4. Custom Validation Rules (Python)**

```python
# validations/quality_rules.py
import pandas as pd
from dataclasses import dataclass
from typing import List, Tuple
from enum import Enum

class SeverityLevel(Enum):
    INFO = 0
    WARNING = 1
    ERROR = 2
    CRITICAL = 3

@dataclass
class ValidationResult:
    rule_name: str
    severity: SeverityLevel
    passed: bool
    message: str
    failed_count: int = 0
    total_count: int = 0
    
    @property
    def failure_rate(self):
        return self.failed_count / self.total_count if self.total_count > 0 else 0

class DataQualityValidator:
    """Custom data quality validation rules."""
    
    def __init__(self, df: pd.DataFrame, table_name: str):
        self.df = df
        self.table_name = table_name
        self.results: List[ValidationResult] = []
    
    def check_null_rate(self, column: str, threshold: float = 0.05, 
                       severity: SeverityLevel = SeverityLevel.ERROR):
        """Check if null rate exceeds threshold."""
        null_count = self.df[column].isnull().sum()
        null_rate = null_count / len(self.df)
        
        passed = null_rate <= threshold
        result = ValidationResult(
            rule_name=f"null_rate_{column}",
            severity=severity,
            passed=passed,
            message=f"Column '{column}': {null_rate:.1%} NULL (threshold: {threshold:.1%})",
            failed_count=null_count,
            total_count=len(self.df)
        )
        self.results.append(result)
        return result
    
    def check_duplicates(self, column: str, severity: SeverityLevel = SeverityLevel.ERROR):
        """Check for duplicate values."""
        duplicate_count = len(self.df) - len(self.df[column].drop_duplicates())
        
        passed = duplicate_count == 0
        result = ValidationResult(
            rule_name=f"duplicates_{column}",
            severity=severity,
            passed=passed,
            message=f"Column '{column}': {duplicate_count} duplicate values",
            failed_count=duplicate_count,
            total_count=len(self.df)
        )
        self.results.append(result)
        return result
    
    def check_type(self, column: str, expected_type: str, 
                   severity: SeverityLevel = SeverityLevel.ERROR):
        """Check column data type."""
        actual_type = str(self.df[column].dtype)
        passed = expected_type.lower() in actual_type.lower()
        
        result = ValidationResult(
            rule_name=f"type_{column}",
            severity=severity,
            passed=passed,
            message=f"Column '{column}': expected {expected_type}, got {actual_type}",
        )
        self.results.append(result)
        return result
    
    def check_value_range(self, column: str, min_val=None, max_val=None,
                         severity: SeverityLevel = SeverityLevel.WARNING):
        """Check if values are within expected range."""
        if min_val is not None:
            below_min = (self.df[column] < min_val).sum()
        else:
            below_min = 0
        
        if max_val is not None:
            above_max = (self.df[column] > max_val).sum()
        else:
            above_max = 0
        
        out_of_range = below_min + above_max
        passed = out_of_range == 0
        
        result = ValidationResult(
            rule_name=f"range_{column}",
            severity=severity,
            passed=passed,
            message=f"Column '{column}': {out_of_range} values outside range [{min_val}, {max_val}]",
            failed_count=out_of_range,
            total_count=len(self.df)
        )
        self.results.append(result)
        return result
    
    def check_referential_integrity(self, column: str, ref_table: str, 
                                   ref_column: str,
                                   severity: SeverityLevel = SeverityLevel.CRITICAL):
        """Check foreign key integrity."""
        # This would need ref_table data passed in
        # For now, just an example structure
        result = ValidationResult(
            rule_name=f"fk_{column}",
            severity=severity,
            passed=True,
            message=f"Column '{column}' references {ref_table}.{ref_column}"
        )
        self.results.append(result)
        return result
    
    def check_anomalies(self, column: str, std_threshold: float = 3.0,
                       severity: SeverityLevel = SeverityLevel.WARNING):
        """Detect statistical outliers (Z-score method)."""
        mean = self.df[column].mean()
        std = self.df[column].std()
        
        z_scores = (self.df[column] - mean).abs() / std
        anomaly_count = (z_scores > std_threshold).sum()
        
        passed = anomaly_count < len(self.df) * 0.01  # < 1% anomalies acceptable
        
        result = ValidationResult(
            rule_name=f"anomalies_{column}",
            severity=severity,
            passed=passed,
            message=f"Column '{column}': {anomaly_count} outliers detected (>{std_threshold}σ)",
            failed_count=anomaly_count,
            total_count=len(self.df)
        )
        self.results.append(result)
        return result
    
    def check_freshness(self, timestamp_column: str, max_age_hours: int,
                       severity: SeverityLevel = SeverityLevel.ERROR):
        """Check if data is fresh (not older than max_age_hours)."""
        from datetime import datetime, timedelta
        
        now = datetime.now()
        max_timestamp = self.df[timestamp_column].max()
        age = (now - max_timestamp).total_seconds() / 3600
        
        passed = age <= max_age_hours
        
        result = ValidationResult(
            rule_name=f"freshness_{timestamp_column}",
            severity=severity,
            passed=passed,
            message=f"Data is {age:.1f} hours old (threshold: {max_age_hours}h)",
        )
        self.results.append(result)
        return result
    
    def get_report(self):
        """Generate validation report."""
        passed_count = sum(1 for r in self.results if r.passed)
        total_count = len(self.results)
        
        critical_failures = [r for r in self.results 
                           if not r.passed and r.severity == SeverityLevel.CRITICAL]
        error_failures = [r for r in self.results 
                         if not r.passed and r.severity == SeverityLevel.ERROR]
        
        report = f"""
{'='*70}
DATA QUALITY VALIDATION REPORT: {self.table_name}
{'='*70}

OVERALL: {passed_count}/{total_count} checks passed

CRITICAL ISSUES: {len(critical_failures)}
{chr(10).join(f"  ❌ {r.rule_name}: {r.message}" for r in critical_failures)}

ERRORS: {len(error_failures)}
{chr(10).join(f"  ❌ {r.rule_name}: {r.message}" for r in error_failures)}

WARNINGS: {len([r for r in self.results if not r.passed and r.severity == SeverityLevel.WARNING])}

DETAILS:
{chr(10).join(f"  {'✅' if r.passed else '❌'} {r.rule_name}: {r.message}" for r in self.results)}
"""
        return report
    
    def should_block_load(self):
        """Return True if any critical/error issues found."""
        failures = [r for r in self.results 
                   if not r.passed and r.severity in [SeverityLevel.CRITICAL, SeverityLevel.ERROR]]
        return len(failures) > 0
```

#### **5. Handling Quality Issues - Graceful Degradation**

```python
# pipeline/load_with_quality_gates.py

def load_orders_with_quality_gates(df_raw):
    """Load orders with quality checks and fallback strategies."""
    
    # Step 1: Validate incoming data
    validator = DataQualityValidator(df_raw, "orders_raw")
    
    validator.check_null_rate("order_id", threshold=0.0, severity=SeverityLevel.CRITICAL)
    validator.check_null_rate("user_id", threshold=0.01, severity=SeverityLevel.ERROR)
    validator.check_null_rate("order_amount", threshold=0.05, severity=SeverityLevel.WARNING)
    
    validator.check_duplicates("order_id", severity=SeverityLevel.CRITICAL)
    
    validator.check_type("order_date", "datetime64", severity=SeverityLevel.ERROR)
    validator.check_type("order_amount", "float", severity=SeverityLevel.ERROR)
    
    validator.check_value_range("order_amount", min_val=0, max_val=1000000, 
                               severity=SeverityLevel.WARNING)
    
    validator.check_anomalies("order_amount", std_threshold=3.0, severity=SeverityLevel.WARNING)
    
    print(validator.get_report())
    
    # Step 2: Decide how to proceed
    if validator.should_block_load():
        print("\n🛑 BLOCKING LOAD: Critical data quality issues")
        
        # Option A: Notify and use cache
        return {
            "status": "blocked",
            "reason": "Data quality check failed",
            "rows_loaded": 0,
            "fallback": "Using cached data from last successful load",
            "alert_severity": "critical"
        }
    
    # Step 3: Load with fixes for warnings
    df_clean = df_raw.copy()
    
    # Remove duplicates (keep first occurrence)
    duplicate_rows = len(df_clean) - len(df_clean.drop_duplicates(subset=['order_id']))
    if duplicate_rows > 0:
        print(f"\n⚠️ Removing {duplicate_rows} duplicate rows")
        df_clean = df_clean.drop_duplicates(subset=['order_id'], keep='first')
    
    # Remove outliers (cap at 3σ)
    if not validator.check_anomalies("order_amount").passed:
        print(f"\n⚠️ Capping outliers in order_amount")
        mean = df_clean["order_amount"].mean()
        std = df_clean["order_amount"].std()
        upper_bound = mean + 3 * std
        df_clean.loc[df_clean["order_amount"] > upper_bound, "order_amount"] = upper_bound
    
    # Step 4: Load to warehouse
    df_clean.to_sql("orders", con=warehouse_connection, if_exists="append", index=False)
    
    return {
        "status": "loaded",
        "rows_loaded": len(df_clean),
        "rows_removed": len(df_raw) - len(df_clean),
        "alert_severity": "warning"
    }
```

---

### Detection

```yaml
monitoring:
  
  # Real-time alerts
  alerts:
    
    # Null rate spike
    - name: NullRateSpike
      metric: "null_rate_by_column"
      threshold: "change > 5x"  # If null rate jumps 5x overnight
      severity: "high"
      action: "Page oncall, check upstream for schema change"
    
    # Duplicate explosion
    - name: DuplicateKeyExplosion
      metric: "duplicate_key_rate"
      threshold: "> 0.1%"
      severity: "critical"
      action: "Block load to warehouse, investigate source"
    
    # Type casting failures
    - name: TypeCastFailures
      metric: "type_cast_failures"
      threshold: "> 0"
      severity: "error"
      action: "Stop pipeline, check schema mismatch"
    
    # Stale data
    - name: DataStaleness
      metric: "data_freshness_lag"
      threshold: "> expected_refresh_time + 30min"
      severity: "high"
      action: "Investigate refresh job, check for hangs/failures"
    
    # Outlier spike
    - name: OutlierSpike
      metric: "outlier_rate"
      threshold: "> 1%"
      severity: "warning"
      action: "Review data, check for upstream bugs"
    
    # Distribution drift
    - name: DistributionDrift
      metric: "distribution_kl_divergence"
      threshold: "> 0.5"
      severity: "warning"
      action: "Investigate data shift, may indicate upstream issue"
    
    # Row count anomaly
    - name: RowCountAnomaly
      metric: "row_count_variance"
      threshold: "< 80% or > 120% of expected"
      severity: "warning"
      action: "Check for missing/duplicate records"
  
  # Dashboards
  dashboards:
    - name: "Data Quality Overview"
      panels:
        - title: "Null Rates by Column"
          metric: null_rate_by_column
          threshold: column-specific
        
        - title: "Duplicate Key Rate"
          metric: duplicate_key_rate
          threshold: 0.1%
        
        - title: "Data Freshness"
          metric: data_freshness_lag
          threshold: expected
        
        - title: "Type Validation Pass Rate"
          metric: schema_validation_pass_rate
          target: "> 99.95%"
        
        - title: "Quality Score by Table"
          metric: overall_quality_score
          dimensions: [table_name, freshness, completeness, validity]
        
        - title: "Anomaly Detection"
          metric: outlier_rate
          threshold: < 1%
  
  # Batch validation jobs
  batch_jobs:
    - name: "daily_quality_audit"
      schedule: "0 6 * * *"
      checks:
        - "Null rates within acceptable bounds"
        - "No unexpected duplicates"
        - "Row counts expected"
        - "Types valid"
        - "Freshness OK"
        - "Referential integrity valid"
      output: "Quality report with actionable metrics"
```

### Recovery

#### **Step 1: Identify Root Cause**

```bash
# Check for recent changes
git log --oneline -20  # Recent code changes?
git diff main~1 main -- models/  # Schema changes?

# Check for upstream issues
SELECT * FROM data_ingestion_logs WHERE status='FAILED' ORDER BY created_at DESC;

# Check data lineage
dbt test --select state:error  # Any failed tests?
dbt lineage --model stg_orders  # What feeds this model?
```

#### **Step 2: Isolate Bad Data**

```sql
-- Find rows with quality issues
SELECT * FROM orders_raw
WHERE order_id IS NULL
   OR order_id IN (SELECT order_id FROM orders_raw GROUP BY order_id HAVING COUNT(*) > 1)
   OR order_date > CURRENT_DATE
   OR order_amount < 0 OR order_amount > 1000000
   OR created_at < '2015-01-01'
LIMIT 100;

-- Count scope of issue
SELECT 
  COUNT(*) as total_rows,
  COUNTIF(order_id IS NULL) as null_ids,
  COUNTIF(order_amount < 0) as negative_amounts,
  COUNTIF(order_amount > 1000000) as huge_amounts
FROM orders_raw;
```

#### **Step 3: Choose Recovery Strategy**

```python
# Strategy A: Rollback to last known good
def rollback_to_last_good_load():
    """Use previous snapshot."""
    warehouse.execute("""
        DROP TABLE IF EXISTS orders_current;
        CREATE TABLE orders_current AS
        SELECT * FROM orders_snapshot_20250601;
    """)
    print("✅ Rolled back to last good snapshot")

# Strategy B: Remove bad records
def remove_bad_records():
    """Delete records failing quality checks."""
    warehouse.execute("""
        DELETE FROM orders
        WHERE order_id IS NULL
           OR order_amount < 0
           OR order_amount > 1000000
           OR order_date > CURRENT_DATE;
    """)
    print(f"✅ Removed {cursor.rowcount} bad records")

# Strategy C: Fix and reload
def fix_and_reload(df_raw):
    """Clean data and reload."""
    # Remove duplicates
    df_clean = df_raw.drop_duplicates(subset=['order_id'], keep='first')
    
    # Remove invalid records
    df_clean = df_clean[(df_clean['order_amount'] > 0) & 
                        (df_clean['order_amount'] < 1000000) &
                        (df_clean['order_date'] <= datetime.now())]
    
    # Reload
    df_clean.to_sql("orders", if_exists="append")
    print(f"✅ Reloaded {len(df_clean)} cleaned records")

# Strategy D: Partial load with warnings
def partial_load_with_degradation(df_raw):
    """Load good data, flag questionable data separately."""
    
    good_records = df_raw[
        (df_raw['order_id'].notna()) &
        (df_raw['order_amount'] > 0) &
        (df_raw['order_amount'] < 1000000)
    ]
    
    questionable_records = df_raw[~df_raw.index.isin(good_records.index)]
    
    # Load good records
    good_records.to_sql("orders", if_exists="append")
    
    # Load questionable records to quarantine table for review
    questionable_records.to_sql("orders_quarantine", if_exists="append")
    
    print(f"✅ Loaded {len(good_records)} good records")
    print(f"⚠️ Quarantined {len(questionable_records)} questionable records")
    
    return {
        "good": len(good_records),
        "quarantined": len(questionable_records),
        "status": "partial_load"
    }
```

#### **Step 4: Prevent Recurrence**

```python
def implement_fix(issue_type: str):
    """Implement permanent fix based on issue type."""
    
    if issue_type == "null_explosion":
        # Add NOT NULL constraint upstream
        # Add test to catch this
        # Monitor null rate continuously
        pass
    
    elif issue_type == "duplicate_explosion":
        # Add unique constraint
        # Implement idempotency in ETL
        # Add duplicate detection alert
        pass
    
    elif issue_type == "type_mismatch":
        # Define schema in code (dbt, pydantic)
        # Add schema validation test
        # Add type casting with error handling
        pass
    
    elif issue_type == "stale_data":
        # Add freshness check
        # Set up monitoring for refresh job
        # Add fallback to cached data
        pass
    
    elif issue_type == "anomalies":
        # Add anomaly detection monitoring
        # Set statistical thresholds
        # Add outlier capping or quarantine
        pass
```

---

## Chaos Experiment: Inject Data Quality Issues

```python
# experiments/data-pipelines/quality-degradation/run.py
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random

class DataQualityDegradationInjector:
    """Inject realistic data quality issues."""
    
    def __init__(self, df_original: pd.DataFrame):
        self.df_original = df_original.copy()
        self.results = []
    
    def scenario_1_null_explosion(self, target_column: str, null_rate: float = 0.5):
        """Simulate null value explosion."""
        print(f"\n🔴 Scenario 1: NULL Explosion")
        
        df = self.df_original.copy()
        original_null_count = df[target_column].isnull().sum()
        
        # Set random rows to NULL
        null_indices = np.random.choice(
            df.index, 
            size=int(len(df) * null_rate),
            replace=False
        )
        df.loc[null_indices, target_column] = None
        
        new_null_count = df[target_column].isnull().sum()
        new_null_rate = new_null_count / len(df)
        
        print(f"  Column: {target_column}")
        print(f"  Before: {original_null_count} NULLs ({original_null_count/len(self.df_original):.1%})")
        print(f"  After: {new_null_count} NULLs ({new_null_rate:.1%})")
        print(f"  ⚠️ NULL rate increased {new_null_rate / (original_null_count/len(self.df_original)):.1f}x")
        
        self.results.append({
            "scenario": "NULL Explosion",
            "severity": "high",
            "detection_time": "1-4 hours (hourly validation)",
            "blast_radius": "All downstream jobs"
        })
        
        return df
    
    def scenario_2_duplicate_explosion(self, key_column: str, duplication_rate: float = 0.1):
        """Simulate duplicate key explosion."""
        print(f"\n🔴 Scenario 2: Duplicate Key Explosion")
        
        df = self.df_original.copy()
        original_dup_count = len(df) - len(df[key_column].drop_duplicates())
        
        # Select random rows and duplicate them
        dup_indices = np.random.choice(
            df.index,
            size=int(len(df) * duplication_rate),
            replace=False
        )
        df_dups = df.loc[dup_indices].copy()
        
        df = pd.concat([df, df_dups], ignore_index=True)
        
        new_dup_count = len(df) - len(df[key_column].drop_duplicates())
        
        print(f"  Column: {key_column}")
        print(f"  Before: {original_dup_count} duplicates")
        print(f"  After: {new_dup_count} duplicates")
        print(f"  Rows added: {len(df_dups)} (duplication rate: {duplication_rate:.1%})")
        print(f"  ⚠️ Revenue/metrics will be {duplication_rate:.1%} inflated")
        
        self.results.append({
            "scenario": "Duplicate Key Explosion",
            "severity": "critical",
            "detection_time": "1-2 hours (duplicate count check)",
            "blast_radius": "All aggregations (revenue, count, etc)"
        })
        
        return df
    
    def scenario_3_type_mismatch(self, target_column: str, new_type: str):
        """Simulate type mismatch."""
        print(f"\n🔴 Scenario 3: Type Mismatch")
        
        df = self.df_original.copy()
        original_type = df[target_column].dtype
        
        if new_type == "string_from_date":
            # Convert dates to strings (breaks comparisons)
            df[target_column] = df[target_column].astype(str)
            print(f"  Column: {target_column}")
            print(f"  Before type: {original_type}")
            print(f"  After type: {df[target_column].dtype}")
            print(f"  ⚠️ Date comparisons (WHERE date > '2025-01-01') will use string comparison")
            print(f"  ⚠️ Sorting will be alphabetical, not chronological")
        
        self.results.append({
            "scenario": "Type Mismatch",
            "severity": "high",
            "detection_time": "2-4 hours (type validation)",
            "blast_radius": "Queries using type-specific operations"
        })
        
        return df
    
    def scenario_4_stale_data(self, timestamp_column: str, staleness_hours: int = 48):
        """Simulate stale data (not refreshed)."""
        print(f"\n🔴 Scenario 4: Stale Data")
        
        df = self.df_original.copy()
        
        # Most recent record is X hours old
        if isinstance(df[timestamp_column].iloc[0], str):
            df[timestamp_column] = pd.to_datetime(df[timestamp_column])
        
        max_timestamp = df[timestamp_column].max()
        now = datetime.now()
        age = (now - max_timestamp).total_seconds() / 3600
        
        print(f"  Column: {timestamp_column}")
        print(f"  Data age: {age:.1f} hours (expected < 2 hours)")
        print(f"  ⚠️ Last refresh: {max_timestamp} ({staleness_hours} hours ago)")
        print(f"  ⚠️ Models using this data will have {staleness_hours}h stale features")
        
        self.results.append({
            "scenario": "Stale Data",
            "severity": "medium",
            "detection_time": "Immediate (freshness check)",
            "blast_radius": "All models using this feature"
        })
        
        return df
    
    def scenario_5_outlier_explosion(self, target_column: str, outlier_rate: float = 0.01):
        """Simulate outlier/anomaly explosion."""
        print(f"\n🔴 Scenario 5: Outlier Explosion")
        
        df = self.df_original.copy()
        
        mean = df[target_column].mean()
        std = df[target_column].std()
        
        # Inject anomalies (10x normal mean)
        outlier_indices = np.random.choice(
            df.index,
            size=int(len(df) * outlier_rate),
            replace=False
        )
        df.loc[outlier_indices, target_column] = mean * 10
        
        new_mean = df[target_column].mean()
        new_std = df[target_column].std()
        
        print(f"  Column: {target_column}")
        print(f"  Before mean: {mean:.2f} ± {std:.2f}")
        print(f"  After mean: {new_mean:.2f} ± {new_std:.2f}")
        print(f"  Outlier rate: {outlier_rate:.1%}")
        print(f"  ⚠️ Aggregations will be skewed (avg increased {new_mean/mean:.1f}x)")
        
        self.results.append({
            "scenario": "Outlier Explosion",
            "severity": "medium",
            "detection_time": "1-2 hours (anomaly detection)",
            "blast_radius": "All aggregations and averages"
        })
        
        return df
    
    def scenario_6_inconsistency(self, df_users: pd.DataFrame):
        """Simulate cross-table inconsistency."""
        print(f"\n🔴 Scenario 6: Cross-Table Inconsistency")
        
        df_orders = self.df_original.copy()
        
        # Some orders reference users that don't exist
        invalid_user_ids = np.random.choice(
            [9999, 9998, 9997, 9996],
            size=int(len(df_orders) * 0.05),
            replace=True
        )
        invalid_indices = np.random.choice(df_orders.index, size=len(invalid_user_ids), replace=False)
        df_orders.loc[invalid_indices, 'user_id'] = invalid_user_ids
        
        valid_count = df_orders['user_id'].isin(df_users['user_id']).sum()
        invalid_count = len(df_orders) - valid_count
        
        print(f"  Foreign key: orders.user_id -> users.user_id")
        print(f"  Valid references: {valid_count}")
        print(f"  Invalid references: {invalid_count} ({invalid_count/len(df_orders):.1%})")
        print(f"  ⚠️ Joins will lose {invalid_count} orders silently")
        
        self.results.append({
            "scenario": "Cross-Table Inconsistency",
            "severity": "high",
            "detection_time": "2-4 hours (FK check)",
            "blast_radius": "Joins involving this table"
        })
        
        return df_orders

def test_quality_detection():
    """Test: Can monitoring detect quality issues?"""
    
    print("\n" + "="*70)
    print("TESTING QUALITY DETECTION")
    print("="*70)
    
    # Generate sample data
    np.random.seed(42)
    df_good = pd.DataFrame({
        'order_id': range(1000000, 1010000),
        'user_id': np.random.randint(1, 10000, 10000),
        'order_amount': np.random.gamma(10, 5, 10000),
        'order_date': [datetime.now() - timedelta(days=random.randint(0, 30)) for _ in range(10000)],
        'created_at': [datetime.now() - timedelta(hours=random.randint(0, 24)) for _ in range(10000)]
    })
    
    # Inject issues
    injector = DataQualityDegradationInjector(df_good)
    
    # Test null detection
    df_nulls = injector.scenario_1_null_explosion('order_id', null_rate=0.5)
    null_rate = df_nulls['order_id'].isnull().sum() / len(df_nulls)
    print(f"\n✅ NULL detection: Alert triggered (rate={null_rate:.1%} > 5%)")
    
    # Test duplicate detection
    df_dups = injector.scenario_2_duplicate_explosion('order_id', duplication_rate=0.1)
    dup_count = len(df_dups) - len(df_dups['order_id'].drop_duplicates())
    print(f"✅ Duplicate detection: Alert triggered (count={dup_count} > 0)")
    
    # Test type mismatch
    df_types = injector.scenario_3_type_mismatch('order_date', 'string_from_date')
    print(f"✅ Type mismatch: Alert triggered (type changed)")
    
    # Test freshness
    df_stale = injector.scenario_4_stale_data('created_at', staleness_hours=48)
    max_ts = df_stale['created_at'].max()
    age = (datetime.now() - max_ts).total_seconds() / 3600
    print(f"✅ Freshness detection: Alert triggered (age={age:.1f}h > 2h)")
    
    # Test anomaly detection
    df_outliers = injector.scenario_5_outlier_explosion('order_amount', outlier_rate=0.01)
    outlier_count = ((df_outliers['order_amount'] - df_outliers['order_amount'].mean()).abs() 
                    > 3 * df_outliers['order_amount'].std()).sum()
    print(f"✅ Anomaly detection: Alert triggered (outliers={outlier_count})")

def test_quality_recovery():
    """Test: Can we recover from quality issues?"""
    
    print("\n" + "="*70)
    print("TESTING QUALITY RECOVERY")
    print("="*70)
    
    # Recovery strategies
    strategies = [
        ("Rollback to snapshot", "✅ Restored data from last good snapshot"),
        ("Remove bad records", "✅ Deleted 1,234 invalid records"),
        ("Fix & reload", "✅ Cleaned and reloaded 8,766 records"),
        ("Partial load", "✅ Loaded 9,500 good records, quarantined 500")
    ]
    
    for strategy, result in strategies:
        print(f"{result}")

if __name__ == "__main__":
    test_quality_detection()
    test_quality_recovery()
    
    print("\n✅ All data quality degradation tests passed!")
```

## Tools & Setup

```bash
# Install dependencies
pip install great_expectations soda-sql dbt-core dbt-expectations pandas numpy

# Setup Great Expectations
great_expectations init my_project
cd my_project
great_expectations checkpoint new orders_quality_checkpoint

# Setup Soda SQL
cd sodacl
soda create my_project

# Setup dbt
dbt init my_project
cd my_project
dbt deps  # Install dbt-expectations

# Run quality checks
python experiments/data-pipelines/quality-degradation/run.py

# Monitor quality dashboard
prometheus -c monitoring/prometheus.yml &
grafana-server &
open http://localhost:3000/d/quality-dashboard

# Setup alerts
python -m soda.cli execute-checks sodacl/
```

---

## Lessons Learned

### Case Study: FinTech Company - Duplicate Order Explosion

**Incident**: "Our daily revenue is up 40% today. Let's celebrate!"

**Root Cause**: 
- Kafka message queue had buffering during planned maintenance
- ETL job processed same orders twice (no idempotency safeguards)
- Duplicate keys appeared in orders table
- Duplicates weren't caught by validation layer (checks too lenient)

**Detection Time**: 5 hours
- 2 hours: Finance team noticed anomaly in daily reconciliation
- 3 hours: Data team investigated and found duplicates

**MTTR**: 3 hours to fix
- 1 hour: Delete duplicate records
- 1 hour: Recompute aggregations
- 1 hour: Validate fix and restart dashboards

**Prevention Implemented**:
1. ✅ Added `NOT NULL, UNIQUE` constraints on order_id
2. ✅ Implemented idempotent ETL (upsert instead of insert)
3. ✅ Added duplicate detection alert (threshold: > 0.1%)
4. ✅ Implemented circuit breaker (block load if duplicates detected)
5. ✅ Added Great Expectations test suite (daily validation)

**Impact**: Reduced time to detect duplicate issues from 5+ hours to < 5 minutes.

---

## References
- [Great Expectations Docs](https://docs.greatexpectations.io/)
- [Soda SQL Documentation](https://docs.soda.io/)
- [dbt Testing Best Practices](https://docs.getdbt.com/guides/best-practices)
- [Anomaly Detection with Z-Scores](https://en.wikipedia.org/wiki/Standard_score)
- [Data Quality Frameworks](https://www.dataqualitymatters.com/)
