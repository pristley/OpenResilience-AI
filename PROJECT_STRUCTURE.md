# OpenResilience-AI Project Structure

Complete overview of the resilience patterns framework for traditional systems, data pipelines, ML models, and GenAI applications.

## 📁 Directory Organization

```
OpenResilience-AI/
├── README.md                              # Main overview
├── CONTRIBUTING.md                        # How to contribute
├── LICENSE                                # MIT/Apache 2.0
├── PROJECT_STRUCTURE.md                   # This file
│
├── docs/
│   ├── GETTING_STARTED.md                # Quick start guide
│   ├── GLOSSARY.md                       # Resilience + ML/Data terminology
│   ├── THEORY.md                         # Principles and concepts
│   └── REFERENCES.md                     # Papers, tools, talks
│
├── patterns/                              # 50 failure patterns across domains
│   │
│   ├── 0-common/                         # Foundational patterns (applies everywhere)
│   │   ├── cascading-failure/            # One service failure → system-wide outage
│   │   ├── network-partition/            # Services can't reach each other
│   │   ├── resource-exhaustion/          # CPU, memory, connections, threads depleted
│   │   ├── retry-storms/                 # Infinite retry loops cascade
│   │   └── timeout-misalignment/         # Timeouts don't match call chains
│   │
│   ├── 1-traditional/                    # API, stateful services, queues, batch
│   │   ├── api-rate-limiting/            # Rate limit mismatch
│   │   ├── batch-job-timeout/            # Long-running jobs timeout
│   │   ├── cache-stampede/               # Cache expiry causes thundering herd
│   │   ├── database-failover/            # DB replica inconsistency
│   │   ├── queue-backpressure/           # Queue backs up → producer blocked
│   │   └── service-mesh-misconfiguration/# Istio/Linkerd config bugs
│   │
│   ├── 2-data-pipelines/                 # ETL, Streaming, Real-time, Batch
│   │   ├── data-quality-degradation/     # Quality metrics degrade silently
│   │   ├── data-lineage-breakage/        # Lineage tracking fails
│   │   ├── feature-store-outage/         # Feature serving unavailable
│   │   ├── late-arriving-data/           # Late data breaks FIFO assumptions
│   │   ├── late-binding-resolution/      # Schema resolution fails at runtime
│   │   ├── replication-lag-divergence/   # Read replicas diverge from source
│   │   ├── schema-evolution-breaks/      # Schema change breaks consumers
│   │   └── sla-violation-cascades/       # SLA miss → downstream failures
│   │
│   ├── 3-ml-models/                      # Prediction, classification, detection
│   │   ├── adversarial-input-injection/  # Crafted inputs fool the model
│   │   ├── batch-prediction-backlog/     # Batch scoring queue backs up
│   │   ├── cold-start-failure/           # No training data for new items
│   │   ├── feature-distribution-shift/   # Feature distribution changes
│   │   ├── feedback-loop-collapse/       # Feedback loop creates bias spiral
│   │   ├── inference-latency-spike/      # Model inference becomes slow
│   │   ├── model-drift-detection/        # Model accuracy degrades
│   │   ├── model-poisoning-detection/    # Training data is corrupted
│   │   └── retraining-degradation/       # Retraining produces worse model
│   │
│   ├── 4-genai-models/                   # LLMs, text generation, vision, audio
│   │   ├── context-window-loss/          # Lose context in long conversations
│   │   ├── embedding-model-failure/      # Embedding service down
│   │   ├── fine-tune-distribution-shift/ # Fine-tuned model degradation
│   │   ├── hallucination-injection/      # Model generates false information
│   │   ├── moderation-bypass-detection/  # Safety filters bypassed
│   │   ├── multi-modal-desync/           # Vision + text + audio out of sync
│   │   ├── output-parsing-cascades/      # Structured output parsing fails
│   │   ├── prompt-injection-detection/   # Malicious prompts bypass safety
│   │   ├── rag-source-poisoning/         # Retrieval corpus is corrupted
│   │   ├── token-limit-exhaustion/       # Request exceeds token limit
│   │   └── token-probability-collapse/   # Model stops generating tokens
│   │
│   ├── 5-personalization/                # Recommendations, profiles, A/B tests
│   │   ├── bucketing-consistency-loss/   # User buckets inconsistent
│   │   ├── cache-invalidation-lag/       # Stale user cache
│   │   ├── canary-deployment-failure/    # Canary experiment breaks
│   │   ├── cold-start-data-gaps/         # No user history
│   │   ├── feedback-loop-divergence/     # Implicit feedback goes wrong
│   │   ├── implicit-feedback-poisoning/  # Click data is corrupted
│   │   └── user-segment-corruption/      # User segments become invalid
│   │
│   └── 6-cross-system/                   # Multi-layer failures
│       ├── cascade-feature-store-to-model/  # Feature store → model inference cascade
│       ├── data-to-inference-inconsistency/ # Training ≠ serving
│       ├── model-serving-pipeline-mismatch/ # Pipeline versioning mismatch
│       └── rag-pipeline-end-to-end/        # RAG source → retrieval → LLM cascade
│
├── experiments/                           # 22 runnable chaos scenarios
│   ├── README.md                          # How to safely run experiments
│   │
│   ├── tools/                             # Chaos engineering tooling
│   │   ├── chaos-mesh/                    # Kubernetes chaos injection
│   │   ├── locust/                        # Load testing configs
│   │   ├── pytest-chaos/                  # Python test harness
│   │   └── terraform/                     # IaC for staging environments
│   │
│   ├── traditional-systems/               # API, DB, queue experiments
│   │   ├── kafka-broker-failure/          # Kafka broker crash
│   │   ├── load-balancer-asymmetry/       # Unbalanced traffic distribution
│   │   └── postgres-failover/             # PostgreSQL replica failure
│   │
│   ├── data-pipelines/                    # ETL, streaming experiments
│   │   ├── airflow-dag-failure/           # DAG task fails
│   │   ├── dbt-test-override/             # dbt test skipped
│   │   ├── schema-collision/              # Schema mismatch at runtime
│   │   └── spark-partition-skew/          # Spark partitions unevenly distributed
│   │
│   ├── ml-models/                         # Model failure experiments
│   │   ├── batch-scoring-backlog/         # Batch job queue backs up
│   │   ├── feature-staleness-sim/         # Features become stale
│   │   ├── model-inference-latency-spike/ # Model inference gets slow
│   │   └── training-data-poisoning/       # Training data corrupted
│   │
│   ├── genai-models/                      # GenAI failure experiments
│   │   ├── embedding-drift-simulation/    # Embedding model drifts
│   │   ├── llm-hallucination-test/        # LLM generates false info
│   │   ├── rag-retrieval-failure/         # RAG retrieval breaks
│   │   └── token-limit-stress-test/       # Token limit exceeded
│   │
│   └── personalization/                   # Personalization experiments
│       ├── ab-test-data-corruption/       # A/B test data corrupted
│       ├── rec-engine-cold-start/         # New users have no recommendations
│       └── user-segment-divergence/       # User segments split
│
├── runbooks/                              # 5 incident response playbooks
│   ├── README.md                          # Incident response framework
│   ├── data-quality-incident/             # Data quality degradation
│   ├── genai-hallucination-response/      # LLM hallucination mitigation
│   ├── model-serving-latency/             # Model inference latency spike
│   ├── multi-layer-cascade/               # Multi-system cascade recovery
│   └── pipeline-sla-breach/               # Data pipeline SLA violation
│
├── templates/                             # Boilerplate for new patterns/experiments
│   ├── pattern-template.md                # Pattern documentation template
│   ├── experiment-template.py             # Python chaos experiment template
│   ├── runbook-template.md                # Incident runbook template
│   └── observability-checklist.md         # Monitoring/alerting checklist
│
├── tools/                                 # 6 utility scripts
│   ├── README.md                          # Tools overview
│   ├── data-quality-faker/                # Generate corrupted test data
│   ├── failure-simulator/                 # Synthetic chaos injection
│   ├── metric-collector/                  # Unified metrics (system + ML + data)
│   ├── model-drift-generator/             # Simulate feature shift
│   ├── observability-dashboard/           # Grafana/Prometheus queries
│   └── report-generator/                  # Auto-document findings
│
└── case-studies/                          # Real-world incidents (anonymized)
    ├── incident-template.md               # Incident writeup template
    ├── 2024-data-pipeline-schema-break.md # Schema evolution gone wrong
    ├── 2024-genai-rag-hallucination.md    # RAG hallucination incident
    ├── 2024-ml-model-drift-cascade.md     # Model drift → cascade
    └── 2024-recommendation-feedback-loop.md # Feedback loop collapse
```

## 📊 Pattern Statistics

| Category | Count | Examples |
|----------|-------|----------|
| **0-common** | 5 | Cascading failure, network partition, resource exhaustion |
| **1-traditional** | 6 | API rate limiting, cache stampede, DB failover |
| **2-data-pipelines** | 8 | Schema evolution, data quality, feature store outage |
| **3-ml-models** | 9 | Model drift, adversarial inputs, feedback loops |
| **4-genai-models** | 11 | Hallucination, prompt injection, RAG poisoning |
| **5-personalization** | 7 | Cold start, bucketing, feedback loops |
| **6-cross-system** | 4 | Multi-layer cascades, train/serve mismatches |
| | |
| **Total Patterns** | **50** | Cross-domain resilience library |
| **Experiments** | **22** | Runnable chaos scenarios |
| **Runbooks** | **5** | Incident response guides |
| **Tools** | **6** | Utility scripts |

## 🚀 Quick Start

### 1. Explore Patterns
```bash
# Browse all patterns
ls -la patterns/*/

# Read a specific pattern
cat patterns/0-common/cascading-failure/README.md
```

### 2. Run an Experiment
```bash
# Traditional systems
python experiments/traditional-systems/kafka-broker-failure/run.py

# ML models
python experiments/ml-models/feature-staleness-sim/run.py

# GenAI
python experiments/genai-models/llm-hallucination-test/run.py
```

### 3. Use a Runbook
```bash
# During an incident
cat runbooks/model-serving-latency/README.md
```

### 4. Use Tools
```bash
# Collect metrics
python tools/metric-collector/metric_collector.py --system --model --data

# Generate test data
python tools/data-quality-faker/data_quality_faker.py --corruption=0.3
```

## 📚 Documentation

| File | Purpose |
|------|---------|
| [GETTING_STARTED.md](docs/GETTING_STARTED.md) | Setup, first patterns, how to contribute |
| [GLOSSARY.md](docs/GLOSSARY.md) | Resilience + ML/Data terminology |
| [THEORY.md](docs/THEORY.md) | Principles: chaos, resilience, observability |
| [REFERENCES.md](docs/REFERENCES.md) | Papers, blogs, talks, tools |

## 🔧 How to Use This Repository

### For Learning
1. Start with [docs/THEORY.md](docs/THEORY.md) for background
2. Browse [GLOSSARY.md](docs/GLOSSARY.md) for domain terminology
3. Pick a pattern from your domain (1-traditional, 3-ml-models, etc.)
4. Read the full pattern description

### For Incident Response
1. Identify the type of failure
2. Find the matching pattern
3. Check the corresponding runbook
4. Follow recovery steps

### For Testing Resilience
1. Pick a pattern you want to test
2. Find the corresponding experiment
3. Run it in staging with safety guardrails
4. Validate your system's resilience controls

### For Contributing
1. Review [CONTRIBUTING.md](../CONTRIBUTING.md)
2. Use [templates/pattern-template.md](templates/pattern-template.md) for new patterns
3. Use [templates/experiment-template.py](templates/experiment-template.py) for experiments
4. Document with observability checklists

## 🎯 Pattern Selection By Domain

**Building Traditional APIs?**
→ Start with [1-traditional](patterns/1-traditional/)

**Running Data Pipelines?**
→ Start with [2-data-pipelines](patterns/2-data-pipelines/)

**Training ML Models?**
→ Start with [3-ml-models](patterns/3-ml-models/)

**Using LLMs or GenAI?**
→ Start with [4-genai-models](patterns/4-genai-models/)

**Building Personalization?**
→ Start with [5-personalization](patterns/5-personalization/)

**Multi-layer System?**
→ Check [6-cross-system](patterns/6-cross-system/)

**Foundational concerns?**
→ Always review [0-common](patterns/0-common/)

## 🤝 Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for:
- How to add a new pattern
- How to submit an experiment
- Writing observability checklists
- Sharing incident case studies

## 📄 License

This project is licensed under MIT or Apache 2.0 (see [LICENSE](LICENSE)).

---

**Last Updated**: 2026-07-02  
**Total Items**: 50 patterns + 22 experiments + 5 runbooks + 6 tools = **83 resilience resources**
