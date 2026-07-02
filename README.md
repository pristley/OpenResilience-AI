# Resilience Patterns
## Chaos Engineering for Traditional, AI, and Data Systems

**Safety, Security and Reliability engineering for non-deterministic systems**

---

### 🎯 Why This Repo?

- **Traditional chaos**: Plenty of resources (Gremlin, Chaos Mesh, Netflix Chaos Engineering)
- **AI chaos**: Scattered. No unified playbook for model drift, adversarial inputs, hallucinations
- **Data chaos**: Underexplored. How do you test your data pipeline for failure modes?

This repo bridges that gap with **50+ documented patterns**, **20+ runnable experiments**, and **real incident case studies**.

---

### 📚 Quick Navigation

- 🆕 **New to chaos?** Start with [Getting Started](docs/GETTING_STARTED.md)
- 🔍 **Looking for a pattern?** Browse by [System Type](#-by-system-type)
- 🧪 **Want to run experiments?** See [Experiments Guide](experiments/README.md)
- 🚨 **Incident happened?** Jump to [Runbooks](runbooks/)
- 📖 **Learn the theory?** Read [Resilience Principles](docs/THEORY.md)

---

### ✨ Highlights

- **50 documented patterns** across 7 categories (foundational, traditional, data, ML, GenAI, personalization, cross-system)
- **22 runnable chaos experiments** with safety guardrails and integration with Chaos Mesh, Locust, Terraform
- **Real incident case studies** (anonymized) with lessons learned
- **Unified observability checklist** for monitoring resilience across all domains
- **Cross-system cascade scenarios** for complex multi-layer failures
- **Complete runbooks** for incident response (5 documented playbooks)
- **Utility tools** for metrics collection, data generation, drift simulation

---

### 🚀 Getting Started

```bash
# Clone the repo
git clone https://github.com/pristley/OpenResilience-AI
cd OpenResilience-AI

# Read the project structure guide
cat PROJECT_STRUCTURE.md

# Pick a pattern to read (cascading-failure is fully detailed)
cat patterns/0-common/cascading-failure/README.md
cat patterns/4-genai-models/hallucination-injection/README.md

# Browse all patterns by category
ls patterns/
# 0-common/          (foundational: 5 patterns)
# 1-traditional/     (APIs, databases, queues: 6 patterns)
# 2-data-pipelines/  (ETL, streaming, quality: 8 patterns)
# 3-ml-models/       (drift, inference, feedback: 9 patterns)
# 4-genai-models/    (hallucination, RAG, tokens: 11 patterns)
# 5-personalization/ (cold start, bucketing, loops: 7 patterns)
# 6-cross-system/    (multi-layer cascades: 4 patterns)

# Run a chaos experiment (with proper approvals!)
cd experiments/genai-models/llm-hallucination-test/
python run.py

# See incident response runbooks
ls runbooks/
# data-quality-incident/
# model-serving-latency/
# genai-hallucination-response/
# pipeline-sla-breach/
# multi-layer-cascade/
```

---

### 📖 By System Type

| System Type | Patterns | Experiments | Status |
|---|---|---|---|
| **0-Common** | [Network, cascading, resources, retries, timeouts](patterns/0-common/) | ✅ Ready | 5 patterns |
| **1-Traditional** | [APIs, databases, caches, queues, rate limiting, failover](patterns/1-traditional/) | ✅ Ready | 6 patterns |
| **2-Data Pipelines** | [ETL, streaming, schema evolution, SLA, quality, lineage, feature store](patterns/2-data-pipelines/) | ✅ Ready | 8 patterns |
| **3-ML Models** | [Drift detection, adversarial injection, inference latency, feedback loops, retraining](patterns/3-ml-models/) | ✅ Ready | 9 patterns |
| **4-GenAI Models** | [Hallucinations, token limits, RAG poisoning, prompt injection, embedding drift](patterns/4-genai-models/) | ✅ Ready | 11 patterns |
| **5-Personalization** | [Cold-start, feedback loops, bucketing, cache invalidation, A/B tests](patterns/5-personalization/) | ✅ Ready | 7 patterns |
| **6-Cross-System** | [Multi-layer cascades, train/serve mismatches, feature store → model](patterns/6-cross-system/) | ✅ Ready | 4 patterns |

---

### 📚 Documentation

- [Project Structure](PROJECT_STRUCTURE.md) — Complete directory overview and navigation
- [Getting Started](docs/GETTING_STARTED.md) — First time? Start here
- [Glossary](docs/GLOSSARY.md) — Chaos/ML/Data terminology
- [Theory](docs/THEORY.md) — Resilience principles & frameworks
- [References](docs/REFERENCES.md) — Papers, tools, talks
- [Templates](templates/) — Boilerplate for new patterns (pattern-template.md, experiment-template.py, runbook-template.md)
- [Experiments Guide](experiments/README.md) — How to safely run chaos tests
- [Contributing Guide](CONTRIBUTING.md) — How to submit patterns and experiments

---

### 🤝 Contributing

Have a pattern, experiment, or incident to share? We'd love it!

See [CONTRIBUTING.md](CONTRIBUTING.md) for submission guidelines.

---

### 📄 License

Licensed under the Apache License 2.0. See [LICENSE](LICENSE) for details.
