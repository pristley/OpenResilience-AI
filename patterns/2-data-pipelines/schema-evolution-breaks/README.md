# Pattern: Schema Evolution Breaks

> When data schema changes (new columns, type changes, removals) without proper versioning and migration, downstream systems fail because they expect old schema but get new one (or vice versa).

## Quick Summary

**Problem**: Schema changes not backward compatible; old code expects old schema, gets new; new code expects new schema, gets old  
**Impact**: Deserialization errors, type mismatches, silent data loss, pipeline breaks  
**Detection Time**: Deployment time (if tested) or runtime (if not)  
**Solution**: Schema versioning, backward/forward compatibility, gradual migration, schema registry

---

## Problem Statement

Example evolution:
- **V1**: {user_id, email, created_at}
- **V2**: {user_id, email, phone, created_at}  (added phone)
- **V3**: {user_id, email, phone, country, plan}  (added country, plan)

Problems:
1. V1 producer + V2 consumer: Consumer tries to read `phone` field, gets error
2. V2 producer + V1 consumer: Producer adds `country`, V1 consumer ignores it (OK, but fragile)
3. V1 producer + V3 consumer: Consumer expects `country, plan`, gets NULL (surprise)
4. Removing column: V2 had {email}, V3 removes email. Old code crashes on missing field.

### Real Scenarios

**Scenario 1: Breaking Schema Change**
- Rename column: `email` → `email_address`
- Producer starts sending `email_address` (code updated)
- Consumer still expects `email` (code not yet updated)
- Deserialization fails: Missing required field `email`
- Pipeline crashes, data loss

**Scenario 2: Type Change Incompatibility**
- Change `user_id` from STRING to INT
- Old records in Kafka: `user_id = "12345"` (string)
- New consumer: Expects INT, tries to parse
- Parse error: `"12345"` can't convert to INT (invalid format)
- Consumer crashes on old messages

**Scenario 3: Silent Data Loss**
- Column removed: `address` field deleted
- Producer stops sending `address`
- Downstream job expects address: `SELECT address FROM events`
- Silently returns NULL or uses default
- Reports missing address, analytics wrong

**Scenario 4: Enum Value Removed**
- `status` enum was: [PENDING, ACTIVE, INACTIVE]
- New version removes INACTIVE (outdated)
- Old data has `status='INACTIVE'`
- New consumer: Tries to parse INACTIVE, fails (invalid enum)
- Can't process old data

**Scenario 5: Required Field Added (No Default)**
- New field added as NOT NULL: `plan` (no default)
- Old producer doesn't send `plan`
- New consumer: Expects `plan`, field is NULL
- Downstream uses NULL where value expected
- Query breaks or shows wrong data

**Scenario 6: Nested Schema Change**
- Object `user` had {id, name}
- New version: `user` has {id, name, email}
- Old producer sends `user` without `email`
- New consumer expects `email` in user object
- Causes issues if consumer assumes email always present

---

## Why It Matters

### Impact Metrics

**Schema Break Cost:**
| Issue | Cost | Duration |
|-------|------|----------|
| **Pipeline crash** (deserialization error) | $50K-500K | Until rolled back/fixed |
| **Silent data loss** (NULL field used) | $10K-100K | Until discovered |
| **Type conversion failure** | $25K-250K | Until resolved |
| **A/B test invalid** (data corrupted) | $100K-1M | Entire experiment invalid |

---

## How It Fails

```
1. Producer code updated with schema V2
   ↓
2. Consumer code still on V1 (not yet deployed)
   ↓
3. Producer sends V2 data
   ↓
4. Consumer expects V1, gets V2
   ↓
5. Deserialization fails or silently corrupts data
   ↓
6. Pipeline crashes or produces garbage
```

### Observable Signals

```yaml
metrics:
  - name: "deserialization_errors"
    definition: "count of JSON/Avro parse failures"
    alert_threshold: "> 0"
  
  - name: "schema_mismatch_errors"
    definition: "count of missing field / type mismatch errors"
    alert_threshold: "> 0"
  
  - name: "null_rate_spike"
    definition: "unexpected increase in NULL values"
    alert_threshold: "> 5%"

logs:
  - "ERROR: Missing required field 'plan' at position 5"
  - "ERROR: Cannot deserialize '12345' as INT (got STRING)"
  - "WARN: Unknown field 'country' in schema, ignoring"
```

---

## Resilience Strategy

### Prevention

#### **1. Schema Versioning with Compatibility**

```python
# Define schemas with versioning
user_schema_v1 = {
    "type": "record",
    "name": "User",
    "namespace": "com.example",
    "fields": [
        {"name": "user_id", "type": "string"},
        {"name": "email", "type": "string"},
        {"name": "created_at", "type": "long"},
    ]
}

user_schema_v2 = {
    "type": "record",
    "name": "User",
    "namespace": "com.example",
    "fields": [
        {"name": "user_id", "type": "string"},
        {"name": "email", "type": "string"},
        {"name": "phone", "type": ["null", "string"], "default": None},  # NEW: optional with default
        {"name": "created_at", "type": "long"},
    ]
}

# Key rules for compatibility:
# 1. Add fields with defaults (backward compatible)
# 2. Never remove required fields
# 3. Never change types of existing fields
# 4. Use optional/union types for new fields
```

#### **2. Schema Registry**

```python
from confluent_kafka import avro

# Register schema
schema_registry = SchemaRegistry("http://schema-registry:8081")

# Register new version
schema_id = schema_registry.register_schema(
    subject="user-events",
    schema=user_schema_v2,
    references=[],
    version=2
)

# Producer uses schema
producer = AvroProducer(
    schema_registry_client=schema_registry,
    schema_subject="user-events",
)

# Consumer gets schema automatically
consumer = AvroConsumer(
    schema_registry_client=schema_registry,
    schema_subject="user-events",
)
```

#### **3. Gradual Migration**

```python
# Phase 1: Add new field to producer (with default)
user_v2 = {
    "user_id": "123",
    "email": "test@example.com",
    "phone": None,  # NEW: Always set, even if None
    "created_at": 1234567890
}

# Phase 2: Deploy consumer update to handle new field
# Phase 3: Start populating phone (if available)
# Phase 4: Old producer versions still running? Handled by default
# Phase 5: Eventually remove old producer code (after full migration)
```

#### **4. Validation During Serialization**

```python
def validate_schema_compat(old_schema, new_schema):
    """Check if schema change is backward compatible."""
    
    # Rule 1: Old fields can't be removed
    old_fields = {f["name"]: f for f in old_schema["fields"]}
    new_fields = {f["name"]: f for f in new_schema["fields"]}
    
    removed = set(old_fields.keys()) - set(new_fields.keys())
    if removed:
        raise Exception(f"Removed fields not allowed: {removed}")
    
    # Rule 2: New required fields must have defaults
    for new_field in new_schema["fields"]:
        if new_field["name"] not in old_fields:
            # New field
            if "default" not in new_field:
                raise Exception(f"New field '{new_field['name']}' must have default")
    
    # Rule 3: Existing field types can't change
    for field_name in old_fields:
        old_type = old_fields[field_name]["type"]
        new_type = new_fields[field_name]["type"]
        if old_type != new_type:
            raise Exception(f"Type change not allowed for '{field_name}': {old_type} → {new_type}")
    
    print("✅ Schema change is backward compatible")
```

---

### Detection

```yaml
monitoring:
  alerts:
    - name: DeserializationErrors
      metric: "deserialization_error_rate"
      threshold: "> 0"
      severity: "critical"
      action: "Check schema compatibility, may need to rollback"
    
    - name: NullRateSpike
      metric: "null_rate"
      threshold: "> 5% increase"
      severity: "high"
      action: "May indicate schema change with missing fields"
```

### Recovery

```python
def recover_from_schema_break():
    # 1. Identify incompatible version
    print("Finding schema mismatch...")
    
    # 2. Rollback to previous compatible version
    print("Rolling back to last compatible schema")
    
    # 3. Reprocess failed data with correct schema
    print("Reprocessing failed batches")
    
    # 4. Fix producer/consumer to be compatible
    print("Updating code to be schema compatible")
    
    # 5. Re-deploy with validation
    print("Validating schema compatibility before deploy")
```

---

## References
- [Avro Schema Compatibility](https://docs.confluent.io/kafka/schema-registry/schema_reference/avro_schema_reference.html#schema-compatibility)
- [Schema Registry Best Practices](https://www.confluent.io/blog/how-to-manage-schemas-subjects-topics-in-kafka/)
- [Protobuf Wire Format](https://developers.google.com/protocol-buffers/docs/encoding)
