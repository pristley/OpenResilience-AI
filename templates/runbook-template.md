# Runbook Template

Copy this when creating a new incident response runbook. Replace [INCIDENT] with the incident type.

---

# Runbook: [INCIDENT TYPE]

## Symptoms

What alerts/signals indicate this incident is happening?

- **Alert 1**: `error_rate` > 5% for >5 minutes
- **Alert 2**: `model_inference_latency_p99` > 5 seconds
- **Observable sign**: Users report slow/broken feature
- **Log pattern**: `"ConnectionTimeout"` entries spiking

### How to Verify

Confirm it's really this incident:

```bash
# Check metric
curl http://prometheus:9090/api/v1/query?query=error_rate

# Check logs
grep "ConnectionTimeout" /var/log/service.log | tail -20

# Check dependent services
curl http://api-service/health
curl http://database:5432/health
```

---

## Triage

**Time goal**: 5 minutes to identify root cause

### Step 1: Gather Information

```bash
# What service is affected?
kubectl get pods -l service=api-gateway -o wide

# Recent deployments?
kubectl rollout history deployment/api-gateway | head -5

# Recent config changes?
git log --oneline -10 -- config/

# Is it zone/region specific?
grep -c "zone-us-west" logs.txt
grep -c "zone-us-east" logs.txt
```

### Step 2: Isolate the Problem

Is this:
- [ ] **Service failure** (service crashed or is slow)
- [ ] **Dependency failure** (database, cache, external API)
- [ ] **Resource exhaustion** (CPU, memory, connections)
- [ ] **Data corruption** (bad data flowing through)
- [ ] **Configuration error** (wrong settings)

**Checklist:**
- [ ] Service is running: `kubectl get pods service-name`
- [ ] Service is healthy: `curl service-name/health`
- [ ] Dependencies are reachable: `curl dependent-service/health`
- [ ] Resource usage is normal: `kubectl top pods service-name`
- [ ] Recent changes: `git log --since="1 hour ago"`

### Step 3: Determine Severity

- **P1 (Critical)**: User-facing feature down, >10% of users affected
- **P2 (High)**: Degraded performance, >1% of users affected
- **P3 (Medium)**: Occasional errors, <1% of users affected
- **P4 (Low)**: Minor issues, no user impact

---

## Mitigation

**Time goal**: 10-15 minutes to reduce impact

### Immediate Actions (First 2-3 minutes)

Do these first to minimize blast radius:

```bash
# Option 1: Restart service
kubectl rollout restart deployment/api-gateway

# Option 2: Scale down to force reload
kubectl scale deployment/api-gateway --replicas=0
sleep 10
kubectl scale deployment/api-gateway --replicas=3

# Option 3: Kill unhealthy pods
kubectl delete pod api-gateway-abc123 api-gateway-def456

# Option 4: Drain load (if not resource exhaustion)
kubectl cordon node-1
# New traffic routes to other nodes
```

### Circuit Breaker Actions

If problem cascades to other services:

```bash
# Close circuit breaker
curl -X POST http://service/admin/circuit-breaker/close

# Rate limit incoming traffic
kubectl set env deployment/api-gateway \
  RATE_LIMIT_RPS=100 \
  RATE_LIMIT_BURST=150

# Shed non-essential traffic
# (e.g., stop processing non-priority requests)
```

### Graceful Degradation

If can't fully recover, degrade gracefully:

```bash
# Serve cached data instead of fresh
kubectl set env deployment/api-gateway \
  CACHE_STRATEGY=serve-stale \
  CACHE_TTL=3600

# Use fallback endpoint
kubectl set env deployment/api-gateway \
  FALLBACK_API=legacy-api.example.com
```

### If Nothing Works: Rollback

```bash
# Rollback to last known-good deployment
kubectl rollout undo deployment/api-gateway

# Verify rollback
kubectl rollout status deployment/api-gateway
kubectl logs -l deployment=api-gateway --tail=50
```

---

## Recovery

**Time goal**: Fully restore within 30 minutes

### Root Cause Analysis

Now that incident is mitigated, find root cause:

```bash
# What changed?
git log -1 HEAD

# What was deployed?
kubectl describe deployment/api-gateway | grep Image

# Are there errors in logs?
kubectl logs -l deployment=api-gateway --tail=100 | grep ERROR

# Check resource usage
kubectl top pods -l deployment=api-gateway
```

### Fix Steps

Based on root cause:

**If deployment issue:**
```bash
# Rebuild image with fix
docker build -t api-gateway:v2.1 .
docker push registry/api-gateway:v2.1

# Deploy fixed version
kubectl set image deployment/api-gateway \
  api-gateway=registry/api-gateway:v2.1

# Monitor rollout
kubectl rollout status deployment/api-gateway
```

**If database issue:**
```bash
# Check database connection
psql -h postgres-primary.default.svc.cluster.local -U admin -d mydb -c "SELECT 1"

# Check connection pool
# (depends on database)

# Restart database if needed
kubectl rollout restart statefulset/postgres
```

**If configuration issue:**
```bash
# Fix config
vim config/api-gateway.yaml

# Apply change
kubectl apply -f config/api-gateway.yaml

# Restart service to pick up config
kubectl rollout restart deployment/api-gateway
```

### Verification

Confirm system is healthy:

```bash
# Service is up
kubectl get pods -l deployment=api-gateway

# Metrics are normal
# (check Prometheus/Grafana)

# No errors in logs
kubectl logs -l deployment=api-gateway | grep -i error | wc -l

# Sample requests work
curl -v http://api-gateway/api/endpoint
```

---

## Post-Mortem

**Time goal**: Complete within 24-48 hours

### Timeline

Document exactly what happened:

| Time | What Happened | Impact |
|------|---------------|--------|
| 14:05 | Deployment of v2.0 | None (successful) |
| 14:12 | Error rate spikes to 15% | Users see errors |
| 14:15 | On-call alerted | Response begins |
| 14:20 | Root cause identified: memory leak | None |
| 14:25 | Rollback to v1.9 | Service recovers |
| 14:30 | Error rate returns to normal | Issue resolved |

### Root Cause

What actually happened?

1. Primary cause: _______
2. Contributing factors: _______
3. Why did we miss this?

### Impact

- **Users affected**: ~5000
- **Duration**: 25 minutes
- **Services affected**: API Gateway, dependent services
- **Revenue impact**: $X

### What Went Wrong

**Detection:**
- ✅ Alert fired quickly (2 minutes to spike)
- ❌ We didn't have alert for memory leak
- ❌ We should have canary testing

**Response:**
- ✅ On-call was fast
- ❌ Documentation was unclear
- ✅ Rollback worked smoothly

### Action Items

Things to do to prevent recurrence:

- [ ] Add memory usage alert: "Threshold > 80% for 2 minutes"
- [ ] Add unit test for memory leak scenario
- [ ] Implement canary deployment (5% traffic first)
- [ ] Document service architecture (who depends on API?)
- [ ] Incident response training for new team members

**Owners**: Who will implement each?

| Action | Owner | Target Date |
|--------|-------|-------------|
| Memory alert | @devops-team | 2024-01-20 |
| Unit tests | @backend-team | 2024-01-25 |
| Canary deployment | @devops-team | 2024-02-01 |

---

## References

### Related Patterns

- [Pattern 1](../patterns/some-pattern/)
- [Pattern 2](../patterns/other-pattern/)

### Monitoring

- **Dashboard**: [Grafana link](http://localhost:3000/d/abc123)
- **Logs**: [ELK link](http://elk.example.com)
- **Traces**: [Jaeger link](http://jaeger.example.com)

### Tools

- **Kubectl**: `kubectl cheat sheet`
- **Prometheus**: Common queries
- **Grafana**: Dashboard links

---

## Questions?

- **Escalation**: Contact @on-call-lead or #incident-response Slack
- **Help**: @devops-team in Slack
- **Resources**: [Runbook Index](../runbooks/)

---

## See Also

- [All Runbooks](../runbooks/)
- [Incident Response Guide](../docs/)
- [Patterns](../patterns/)
