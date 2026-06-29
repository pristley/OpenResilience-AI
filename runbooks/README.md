# Runbooks: Incident Response Playbooks

This directory contains runbooks for responding to specific incident types.

---

## What is a Runbook?

A runbook is a step-by-step guide for responding to a specific type of incident.

**Structure:**
1. **Symptoms**: What alerts/signals indicate this incident?
2. **Triage**: How to confirm the problem and understand scope
3. **Mitigation**: Immediate steps to reduce impact
4. **Recovery**: How to fully restore normal operation
5. **Post-Mortem**: Investigation and prevention steps

---

## Using Runbooks

When an alert fires:

```
Alert: "API_ERROR_RATE_HIGH"
    ↓
Find runbook: "api-error-rate.md"
    ↓
Follow: Symptoms → Triage → Mitigation → Recovery
    ↓
Document: What you found and fixed
    ↓
Post-mortem: Prevent next time
```

---

## Creating a Runbook

1. Copy [../templates/runbook-template.md](../templates/runbook-template.md)
2. Fill in each section based on your system
3. Test it (run through steps in staging)
4. Submit PR via [CONTRIBUTING.md](../CONTRIBUTING.md)

---

## Quick Links

### By System Type

**Traditional Systems:**
- API latency spike
- Database failover
- Cache miss storm
- Queue backlog
- Service restart failure

**Data Pipelines:**
- Data quality alert
- SLA breach
- Schema validation failure
- Replication lag
- Pipeline stalled

**ML Systems:**
- Model serving latency
- Model accuracy drop
- Feature store outage
- Training failure
- Inference error spike

**GenAI Systems:**
- LLM timeout
- Hallucination detection
- RAG retrieval failure
- Token limit exhaustion
- Rate limit exceeded

---

## Checklist for On-Call

When you get paged:

- [ ] Find the alert name
- [ ] Locate corresponding runbook
- [ ] Follow triage steps (first 5 minutes)
- [ ] Notify team if P1/P2
- [ ] Execute mitigation (next 10 minutes)
- [ ] Execute recovery (may be parallel with mitigation)
- [ ] Verify system is healthy
- [ ] Document everything
- [ ] Schedule post-mortem

**Goal:** P1 from alert to recovery < 30 minutes

---

## Examples

Want to see how runbooks are used?

- [Incident Case Studies](../case-studies/) — Real examples
- [Theory & Principles](../docs/THEORY.md) — Background

---

## Contributing

Have a runbook to share? Follow [CONTRIBUTING.md](../CONTRIBUTING.md).

**Structure for new runbooks:**

```
runbooks/
├── [system-type]-[incident-type].md
├── Example: api-timeout-cascade.md
├── Example: model-drift-detected.md
└── Example: data-pipeline-sla-breach.md
```

---

See also: [Patterns](../patterns/), [Case Studies](../case-studies/), [Templates](../templates/)
