# Case Studies: Real Incidents (Anonymized)

This directory contains real-world incident case studies to learn from.

---

## Why Case Studies Matter

Production incidents are the best teachers. By analyzing what went wrong, we learn:

- What failure modes actually occur (not just theoretical)
- How long detection and recovery take
- Which strategies worked and which didn't
- How to prevent similar incidents

---

## Reading a Case Study

Each case study follows this structure:

1. **Timeline**: When did things break?
2. **Root Cause**: What actually failed?
3. **Detection**: How fast was it spotted?
4. **Impact**: Users/systems/revenue affected
5. **Resolution**: What was the fix?
6. **Prevention**: How to avoid next time?

---

## Contributing a Case Study

Have an incident to share? We'd love to learn from it!

**How to submit:**

1. Anonymize sensitive details (company, user counts, revenue)
2. Copy [incident-template.md](incident-template.md)
3. Fill in all sections
4. Indicate **Incident Type** (Network/Data/ML/GenAI/Personalization/Other)
5. Link to relevant [patterns](../patterns/)
6. Open a PR via [CONTRIBUTING.md](../CONTRIBUTING.md)

**Example:**
- ❌ "Acme Corp lost $1M revenue" 
- ✅ "Enterprise customer lost access to core feature for 2 hours"

---

## Case Study Archive

*Coming Soon:*
- 2024-01: Recommendation feedback loop divergence
- 2024-02: GenAI RAG hallucination cascade
- 2024-03: Data pipeline schema evolution break
- 2024-04: ML model drift detection failure

---

## Learning from Incidents

When reviewing a case study:

- [ ] **What failed**: Infrastructure? Application? Data?
- [ ] **Why it failed**: Code bug? Configuration? External dependency?
- [ ] **Why we didn't catch it**: Monitoring gap? Test coverage?
- [ ] **Time breakdown**: Detection + Diagnosis + Fix + Verification
- [ ] **What we learned**: How to prevent next time

---

## Related Resources

- [Patterns](../patterns/) — Detailed failure mode analysis
- [Runbooks](../runbooks/) — How to respond to incidents
- [Theory](../docs/THEORY.md) — Why distributed systems fail
- [References](../docs/REFERENCES.md) — Papers on incident analysis

---

## Blameless Post-Mortems

When analyzing incidents, remember:

- **Goal**: Prevent recurrence, not assign blame
- **Focus**: Systems and processes, not individuals
- **Tone**: Curious, not judgmental
- **Outcome**: Actionable improvements

**Anti-patterns:**
- ❌ "Engineer X made a mistake"
- ✅ "System allowed misconfiguration without validation"

---

See also: [CONTRIBUTING.md](../CONTRIBUTING.md), [Incident Template](incident-template.md)
