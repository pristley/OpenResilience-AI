# Getting Started with Resilience Patterns

Welcome! This guide will help you navigate and use this repository effectively.

## For Different Roles

### I'm a **Platform/SRE Engineer**

You're responsible for system reliability. Start here:

1. **Read**: [Foundational Patterns](../patterns/0-common/) — network failures, cascading failures, timeouts
2. **Read**: [Traditional Systems Patterns](../patterns/1-traditional/) — databases, caches, queues
3. **Do**: Pick one pattern and run the corresponding chaos experiment
4. **Monitor**: Set up observability using [Observability Checklist](../templates/observability-checklist.md)
5. **Contribute**: Document failures you've seen in [case-studies/](../case-studies/)

### I'm a **Data Engineer**

You own data pipelines. Start here:

1. **Read**: [Data Pipeline Patterns](../patterns/2-data-pipelines/)
2. **Do**: Run data quality chaos experiments
3. **Implement**: Great Expectations validations for each pattern
4. **Monitor**: Track SLA violations and lineage breaks
5. **Contribute**: Share pipeline incidents

### I'm an **ML Engineer**

You build and deploy models. Start here:

1. **Read**: [ML Model Patterns](../patterns/3-ml-models/)
2. **Do**: Simulate model drift with feature staleness experiments
3. **Implement**: Model monitoring and fallback strategies
4. **Test**: Run adversarial input injection tests
5. **Contribute**: Share model failures and recovery strategies

### I'm a **GenAI/LLM Engineer**

You work with large language models. Start here:

1. **Read**: [GenAI Patterns](../patterns/4-genai-models/)
2. **Do**: Test hallucination detection with provided experiments
3. **Test**: RAG pipeline robustness under adversarial inputs
4. **Implement**: Confidence scoring and graceful degradation
5. **Contribute**: Share GenAI-specific failure modes

### I'm a **Manager/Architect**

You need system-wide resilience. Start here:

1. **Read**: [Theory](THEORY.md) — principles of resilience
2. **Review**: [Cross-System Patterns](../patterns/6-cross-system/) — cascading failures
3. **Discuss**: [Case Studies](../case-studies/) — real incidents and lessons
4. **Plan**: Use [Runbooks](../runbooks/) for incident response
5. **Allocate**: Time for chaos engineering and observability work

---

## Understanding the Repository Structure

```
resilience-patterns/
├── patterns/              ← Documented failure patterns (START HERE)
│   ├── 0-common/         ← Foundational (applies everywhere)
│   ├── 1-traditional/    ← APIs, databases, caches, queues
│   ├── 2-data-pipelines/ ← ETL, streaming, batch, feature stores
│   ├── 3-ml-models/      ← Model inference, training, drift
│   ├── 4-genai-models/   ← LLMs, RAG, hallucinations
│   ├── 5-personalization/← Recommendations, A/B tests
│   └── 6-cross-system/   ← Multi-layer failures
├── experiments/          ← Runnable chaos experiments
│   └── tools/            ← Chaos tools (Chaos Mesh, Terraform, etc.)
├── runbooks/             ← Incident response playbooks
├── templates/            ← Boilerplate for new patterns
├── tools/                ← Utility scripts (metric collection, etc.)
└── case-studies/         ← Real incidents (anonymized)
```

---

## How to Read a Pattern

Each pattern follows this structure:

```markdown
# Pattern: [Name]

## Problem Statement
What goes wrong? Why should you care?

## Why It Matters
Business impact, metrics to watch, blast radius

## How It Fails
Mechanism, observable signals, detection time

## Resilience Strategy
Prevention, Detection, Recovery approaches

## Chaos Experiment
Executable code to safely trigger the failure

## Lessons Learned
War stories and real data

## Tools & References
Specific links and resources
```

**Example: Read [Model Drift Detection](../patterns/3-ml-models/model-drift-detection/README.md)**

---

## Running Your First Chaos Experiment

### Safety First

```bash
# ALWAYS use --dry-run first
python experiments/3-ml-models/feature-staleness-sim/run.py --dry-run

# Review what will happen
cat /tmp/experiment-plan.txt

# Then run in isolated environment
python experiments/3-ml-models/feature-staleness-sim/run.py --env=staging
```

### Example: Feature Store Outage

```bash
cd experiments/2-data-pipelines/

# Simulate feature store latency spike
python feature-store-outage/run.py \
  --latency-ms=5000 \
  --duration=60 \
  --dry-run

# Monitor impact on model serving
# Watch: Model inference latency, fallback rates, error rates
```

---

## Setting Up Observability

Use the [Observability Checklist](../templates/observability-checklist.md) to instrument your system.

**Key metrics to track:**

- **System**: CPU, memory, network latency, error rates
- **Data**: Quality scores, schema violations, SLA breaches
- **Models**: Prediction latency, confidence, drift detection
- **Queries**: Response time, cache hit rate, timeouts

---

## Contributing Your First Pattern

1. **Pick a failure you've experienced** (or studied)
2. **Copy the template**: `cp templates/pattern-template.md patterns/[category]/[name]/README.md`
3. **Fill in the sections** with your learnings
4. **Add a chaos experiment** (optional)
5. **Open a PR** and we'll review!

See [CONTRIBUTING.md](../CONTRIBUTING.md) for details.

---

## FAQ

### Q: How do I know which pattern applies to my system?

**A**: Look at the folder structure (`0-common/`, `1-traditional/`, etc.). Your system likely spans multiple categories:
- Traditional API backend? → 0-common + 1-traditional
- Data pipeline feeding ML model? → 0-common + 2-data-pipelines + 3-ml-models
- LLM-based chatbot? → 0-common + 4-genai-models + potentially 2-data-pipelines (for RAG)

Start with 0-common (applies everywhere), then pick your system type.

### Q: Can I run experiments in production?

**A**: Not recommended. Use `--env=staging` or `--env=test`. All experiments should have:
- Blast radius limits (affect small % of traffic)
- Duration limits (run for minutes, not hours)
- Rollback capabilities (kill switch)
- Observability (detailed logging)

Read [Experiments Guide](../experiments/README.md#safety) for details.

### Q: How do I measure resilience improvement?

**A**: Track these metrics before and after applying resilience strategies:
- **MTTR**: Mean time to recovery (how fast you detect + fix)
- **Blast radius**: How many users/systems affected
- **Cost**: Economic impact (downtime, compute, manual work)
- **Frequency**: How often failures occur

### Q: What if I don't see a pattern for my failure mode?

**A**: Great! You've found a gap. 
1. Read [CONTRIBUTING.md](../CONTRIBUTING.md)
2. Use [Pattern Template](../templates/pattern-template.md)
3. Open a PR with your pattern
4. We'll help refine it

---

## Next Steps

1. ✅ **Read**: Pick your role above and start reading patterns
2. ✅ **Explore**: Spend 30 minutes browsing patterns relevant to your system
3. ✅ **Run**: Try one chaos experiment in a safe environment
4. ✅ **Monitor**: Set up observability for that pattern
5. ✅ **Contribute**: Share learnings or incidents

---

## Resources

- **Concepts**: [Theory & Principles](THEORY.md)
- **Terminology**: [Glossary](GLOSSARY.md)
- **Tools & Papers**: [References](REFERENCES.md)
- **Templates**: [Pattern](../templates/pattern-template.md), [Experiment](../templates/experiment-template.py), [Runbook](../templates/runbook-template.md)

---

**Questions?** Open a [GitHub Discussion](https://github.com/pristley/OpenResilience/discussions) or file an [Issue](https://github.com/pristley/OpenResilience/issues).
