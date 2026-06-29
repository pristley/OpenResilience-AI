# Observability Checklist

Use this checklist when implementing observability for a pattern.

---

## System Health Metrics

- [ ] **CPU Usage**: `node_cpu_seconds_total`
- [ ] **Memory Usage**: `node_memory_MemAvailable_bytes`
- [ ] **Disk Usage**: `node_filesystem_avail_bytes`
- [ ] **Network In/Out**: `node_network_receive_bytes_total`
- [ ] **Swap Usage**: `node_memory_SwapFree_bytes`

**Alert Thresholds:**
- CPU > 80% for 5 minutes
- Memory > 85% for 5 minutes
- Disk > 90% for 1 hour
- Network errors > 100/sec

---

## Application Metrics

### Request/Response

- [ ] **Request Rate**: Requests per second (broken down by endpoint)
- [ ] **Error Rate**: Errors as % of total requests
- [ ] **Latency**: P50, P95, P99 percentiles
- [ ] **Response Size**: Average, min, max

**Prometheus Example:**
```yaml
request_duration_seconds_bucket
request_total{path="/api/users"}
request_errors_total
response_size_bytes
```

### Availability

- [ ] **Uptime**: % of time service is responding
- [ ] **Health Check**: Endpoint returning 200 OK
- [ ] **Dependencies**: % of time dependencies are available
- [ ] **Circuit Breaker State**: open/closed/half-open

### Resource Usage

- [ ] **Database Connections**: Active, idle, queued
- [ ] **Connection Pool**: In-use, available, rejected
- [ ] **Cache Hit Rate**: % of requests served from cache
- [ ] **Thread Pool**: Active, queued, rejected

---

## Data Quality Metrics

### Freshness

- [ ] **Data Age**: How old is the newest data?
- [ ] **Update Frequency**: How often is data refreshed?
- [ ] **SLA Compliance**: % of updates meeting freshness SLA

**Example:**
```sql
-- Data age in minutes
SELECT MAX(CURRENT_TIMESTAMP - last_updated) as max_age_minutes
FROM data_table;
```

### Completeness

- [ ] **Null Rate**: % of missing values per column
- [ ] **Row Count**: Is count as expected?
- [ ] **Partition Coverage**: Are all expected partitions present?

### Accuracy

- [ ] **Schema Validation**: % of rows matching expected schema
- [ ] **Type Validation**: % of values matching expected type
- [ ] **Range Validation**: % of values in expected range
- [ ] **Uniqueness**: Duplicate key count

### Consistency

- [ ] **Replication Lag**: Delay between source and replica
- [ ] **Join Integrity**: Referential integrity violations
- [ ] **Cross-Table Consistency**: Consistency between related tables

---

## ML Model Metrics

### Performance

- [ ] **Accuracy**: Correct predictions / total predictions
- [ ] **Precision**: True positives / (true positives + false positives)
- [ ] **Recall**: True positives / (true positives + false negatives)
- [ ] **F1 Score**: Harmonic mean of precision and recall

### Serving

- [ ] **Inference Latency**: P50, P95, P99 response time
- [ ] **Model Load Time**: Time to load model into memory
- [ ] **Batch Size**: Number of predictions per batch
- [ ] **Throughput**: Predictions per second

### Data

- [ ] **Feature Missing Rate**: % of missing feature values
- [ ] **Feature Distribution**: Is distribution as expected?
- [ ] **Feature Correlation**: Are correlations stable?
- [ ] **Prediction Distribution**: Is output distribution as expected?

### Drift

- [ ] **Covariate Shift**: Feature distribution change
- [ ] **Label Shift**: Target variable distribution change
- [ ] **Concept Drift**: Model performance degradation
- [ ] **Feature Importance Change**: Are top features still important?

---

## GenAI Metrics

### Output Quality

- [ ] **Confidence Score**: Model's confidence in output
- [ ] **Hallucination Rate**: % of outputs with factual errors
- [ ] **Citation Validity**: % of citations that support claim
- [ ] **Consistency**: Same question → similar answer

### Input Safety

- [ ] **Prompt Injection**: % of inputs attempting injection
- [ ] **Toxic Input Rate**: % of inappropriate inputs
- [ ] **Token Count**: Distribution of input lengths

### Token Usage

- [ ] **Tokens Used**: Input + output tokens
- [ ] **Token Limit Violations**: % of requests hitting limit
- [ ] **Cost**: Total API cost (if using external LLM)

---

## Logging

### Required Log Levels

- [ ] **DEBUG**: Detailed diagnostic info (function params, returns)
- [ ] **INFO**: General milestones (service started, batch complete)
- [ ] **WARN**: Unusual but handled (retry count exceeded, slow query)
- [ ] **ERROR**: Something failed (exception, failed validation)
- [ ] **FATAL**: Unrecoverable error (service can't start)

### Log Fields

Every log entry should include:

```json
{
  "timestamp": "2024-01-15T14:30:45.123Z",
  "level": "ERROR",
  "service": "api-gateway",
  "instance": "api-gateway-abc123",
  "message": "Failed to fetch user data",
  "error": "connection timeout",
  "request_id": "req-12345",
  "user_id": "user-456",
  "duration_ms": 5000,
  "stack_trace": "..."
}
```

### Key Log Patterns to Alert On

```
# Errors
ERROR|FATAL|Exception|Timeout|ConnectionRefused

# Performance
duration > 5000ms
timeout
slow_query

# Data
validation error|schema mismatch|null value
data quality alert

# Deployment
deployment started|rollback|scale event
```

---

## Tracing

### Trace Requirements

- [ ] **Service Name**: Which service is this?
- [ ] **Operation Name**: What operation? (e.g., "GET /api/users")
- [ ] **Span ID**: Unique ID for this operation
- [ ] **Parent Span ID**: What called this?
- [ ] **Trace ID**: Unique ID for entire request flow
- [ ] **Duration**: How long did this take?
- [ ] **Tags**: Additional context (user_id, status_code, etc.)

### Trace Sampling

- [ ] **Error Requests**: 100% sampling (always trace errors)
- [ ] **Slow Requests**: Sample if P99 latency exceeded
- [ ] **Normal Requests**: Sample 1-5% (don't trace everything)
- [ ] **Test Requests**: Don't trace (avoid cluttering)

---

## Alerting Strategy

### Alert Naming Convention

```
[SEVERITY]_[COMPONENT]_[CONDITION]

Examples:
CRITICAL_API_ERROR_RATE_HIGH
WARNING_DATABASE_REPLICATION_LAG_HIGH
CRITICAL_ML_MODEL_DRIFT_DETECTED
```

### Alert Routing

- [ ] **P1 (Critical)**: Immediate pages on-call
- [ ] **P2 (High)**: Slack + email within 5 minutes
- [ ] **P3 (Medium)**: Daily digest + dashboard
- [ ] **P4 (Low)**: Dashboard only

### Alert Criteria

Each alert should define:

```
Name: API_ERROR_RATE_HIGH
Condition: error_rate > 5% for 5 minutes
Severity: P1
Runbook: /runbooks/api-error-rate.md
Notify: #api-on-call (Slack)
```

---

## Dashboards

### SRE Dashboard (for on-call)

- [ ] Error rate (last hour)
- [ ] P99 latency (last hour)
- [ ] Active alerts
- [ ] Deployment history
- [ ] Dependency health

### Engineering Dashboard (for team)

- [ ] Request volume by endpoint
- [ ] Error breakdown (by error type)
- [ ] Latency distribution
- [ ] Resource usage (CPU, memory, connections)
- [ ] Feature performance (for ML)

### Business Dashboard (for stakeholders)

- [ ] Availability %
- [ ] User impact (# affected)
- [ ] Revenue impact
- [ ] SLA compliance %
- [ ] Incident count

---

## Setup Checklist

- [ ] **Metrics**: Export metrics in Prometheus format
- [ ] **Scraping**: Configure Prometheus to scrape endpoints
- [ ] **Storage**: Retention policy (14 days minimum)
- [ ] **Alerting**: Alert rules configured
- [ ] **Notification**: Routes to Slack/PagerDuty
- [ ] **Dashboards**: Grafana dashboards created
- [ ] **Logging**: Logs aggregated (ELK, Splunk, etc.)
- [ ] **Tracing**: Trace collection configured (Jaeger, etc.)
- [ ] **Runbooks**: Linked to alerts
- [ ] **Testing**: Alerts tested with chaos experiments

---

## Testing Your Observability

```bash
# Simulate alert condition
python -c "
import requests
# Send error payload to app
# Verify alert fires within 5 minutes
"

# Verify metric collection
curl http://prometheus:9090/api/v1/query?query=up

# Verify logs are collected
curl http://elasticsearch:9200/_search?q=service:myapp

# Verify traces work
# Send request and look in Jaeger UI
```

---

## Resources

- [Prometheus Metrics](https://prometheus.io/docs/concepts/data_model/)
- [Grafana Dashboard Builder](https://grafana.com/docs/grafana/latest/dashboards/build-dashboards/)
- [Jaeger Tracing](https://www.jaegertracing.io/)
- [ELK Stack](https://www.elastic.co/what-is/elk-stack)

---

See also: [Theory](../docs/THEORY.md), [References](../docs/REFERENCES.md)
