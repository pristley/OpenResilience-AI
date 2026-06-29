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

- **50+ documented patterns** covering traditional, AI, data, and GenAI systems
- **20+ runnable chaos experiments** with safety guardrails
- **10+ real incident case studies** (anonymized)
- **Unified observability checklist** for monitoring resilience
- **Cross-system cascade scenarios** for complex failures

---

### 🚀 Getting Started

```bash
# Clone the repo
git clone https://github.com/pristley/OpenResilience
cd OpenResilience

# Pick a pattern to read
less patterns/3-ml-models/model-drift-detection/README.md

# Browse all patterns by category
ls patterns/
# 0-common/          (foundational)
# 1-traditional/    (APIs, databases, queues)
# 2-data-pipelines/ (ETL, streaming, batch)
# 3-ml-models/      (inference, training, features)
# 4-genai-models/   (LLMs, RAG, multi-modal)
# 5-personalization/(recs, A/B tests)
# 6-cross-system/   (multi-layer failures)

# Run a chaos experiment (with proper approvals!)
cd experiments/
# See README.md for safety guidelines
```

---

### 📖 By System Type

| System Type | Patterns | Experiments | Status |
|---|---|---|---|
| **Foundational** | [Network failures, cascades, timeouts](patterns/0-common/) | ✅ Ready | 5 patterns |
| **Traditional Systems** | [APIs, databases, caches, queues](patterns/1-traditional/) | ✅ Ready | 6 patterns |
| **Data Pipelines** | [ETL, streaming, schema, SLA](patterns/2-data-pipelines/) | 📋 In progress | 8 patterns |
| **ML Models** | [Drift, adversarial, inference latency](patterns/3-ml-models/) | 📋 In progress | 9 patterns |
| **GenAI Models** | [Hallucinations, token limits, RAG](patterns/4-genai-models/) | 📋 Planned | 11 patterns |
| **Personalization** | [Cold-start, feedback loops, A/B tests](patterns/5-personalization/) | 📋 Planned | 7 patterns |
| **Cross-System** | [Multi-layer cascades, mismatches](patterns/6-cross-system/) | 📋 Planned | 4 patterns |

---

### 📚 Documentation

- [Getting Started](docs/GETTING_STARTED.md) — First time? Start here
- [Glossary](docs/GLOSSARY.md) — Chaos/ML/Data terminology
- [Theory](docs/THEORY.md) — Resilience principles & frameworks
- [References](docs/REFERENCES.md) — Papers, tools, talks
- [Templates](templates/) — Boilerplate for new patterns

---

### 🤝 Contributing

Have a pattern, experiment, or incident to share? We'd love it!

See [CONTRIBUTING.md](CONTRIBUTING.md) for submission guidelines.

---

### 📄 License

Licensed under the Apache License 2.0. See [LICENSE](LICENSE) for details.
