# Glossary: Chaos & Resilience Terms

## Core Concepts

### Chaos Engineering
The practice of intentionally injecting failures into systems to discover weaknesses before they happen in production.

### Resilience
The ability of a system to:
- **Prevent** failures from occurring
- **Detect** failures quickly when they do
- **Recover** gracefully with minimal blast radius

### Failure Mode
A specific way a system can fail (e.g., "network partition", "database timeout", "model drift").

### Blast Radius
The scope of impact when a failure occurs (e.g., "affects 5% of users", "breaks recommendation engine").

---

## System Types

### Traditional Systems
Stateless or stateful services: APIs, databases, queues, caches, load balancers, etc.

**Key failures**: network partitions, cascading failures, timeouts, cascades, resource exhaustion

### Data Pipelines
ETL, streaming, batch processing systems that transform and move data.

**Key failures**: data quality degradation, schema evolution breaks, SLA violations, late-arriving data

### ML Models
Machine learning systems: inference, training, feature stores, model serving.

**Key failures**: model drift, feature distribution shift, inference latency, cold-start problems

### GenAI Models
Large language models and applications: LLMs, RAG systems, embeddings, multi-modal models.

**Key failures**: hallucinations, token limit exhaustion, prompt injection, RAG poisoning

### Personalization Systems
Recommendation engines, A/B testing, user segmentation.

**Key failures**: cold-start gaps, feedback loop divergence, segment corruption, bucketing inconsistency

---

## Failure Detection & Recovery

### MTTR (Mean Time To Recovery)
Average time from failure detection to system restoration.

Breakdown:
- **Detection**: Time to notice something is wrong
- **Diagnosis**: Time to identify root cause
- **Fix**: Time to implement solution
- **Verification**: Time to confirm system is healthy

### MTTF (Mean Time To Failure)
Average time between failures.

**Goal**: Reduce frequency of failures (increase MTTF) + reduce recovery time (decrease MTTR).

### Graceful Degradation
When a system cannot operate normally, it reduces functionality in a controlled way rather than failing completely.

**Example**: Model serving system falls back to cached predictions instead of crashing.

### Circuit Breaker
A pattern that stops sending requests to a failing service to prevent cascading failures.

States:
- **Closed**: Normal operation (requests pass through)
- **Open**: Service is failing (requests are rejected immediately)
- **Half-open**: Testing if service has recovered (limited requests allowed)

### Bulkhead Pattern
Isolate resources so a failure in one component doesn't cascade to others.

**Example**: Database connection pool limits prevent one query from exhausting all connections.

---

## Data-Specific Terms

### Data Quality
Accuracy, completeness, timeliness, and consistency of data.

**Metrics**:
- Null rate (% missing values)
- Duplicate rate
- Freshness (how recent is the data?)
- Schema adherence (does it match expected structure?)

### Schema Evolution
Planned changes to data structure (add/remove/rename columns, change types).

**Problem**: Downstream systems (models, dashboards) may break if not updated together.

### Data Lineage
The flow of data from source to consumption.

**Breakage**: When intermediate transformations fail, downstream systems get stale/wrong data.

### SLA (Service Level Agreement)
Contract for data availability/freshness.

**Example**: "Reports must be available by 8 AM each day with data no older than 24 hours."

### Late-Arriving Data
Data that arrives after expected time window, breaking downstream SLAs.

**Example**: User events from yesterday arriving 2 days late due to slow upload.

### Replication Lag
Delay between a change in source data and its reflection in replicas.

**Problem**: If you query replica, you might get stale data.

---

## ML-Specific Terms

### Model Drift
When model performance degrades over time due to changes in data or environment.

**Types**:
- **Covariate shift**: Feature distribution changes (e.g., new user demographics)
- **Label shift**: Distribution of target variable changes (e.g., class imbalance)
- **Concept drift**: Relationship between features and target changes (e.g., user preferences shift)

### Feature Store
Central repository for computed features used by ML models.

**Key concern**: If it goes down, models can't get real-time features for inference.

### Cold Start
When a model/system has insufficient historical data for new users/items.

**Problem**: Recommendation quality is poor until enough data accumulates.

### Feedback Loop
When model predictions influence future training data, creating a cycle.

**Risk**: If model makes biased predictions, it learns to repeat those biases.

### Adversarial Input
Carefully crafted input designed to fool a model into making wrong predictions.

**Example**: Image with imperceptible perturbations that fools image classifier.

### Inference Latency
Time from request → model prediction → response.

**Problem**: If latency spikes, user-facing features break (e.g., real-time recommendations).

---

## GenAI-Specific Terms

### Hallucination
When an LLM generates plausible-sounding but factually incorrect content.

**Risk**: Misinformation, broken citations, compliance violations.

### Prompt Injection
Malicious user input that manipulates LLM behavior.

**Example**: Appending "Ignore all previous instructions" to user query.

### RAG (Retrieval-Augmented Generation)
System that retrieves relevant documents, then uses LLM to generate answer grounded in those documents.

**Risk**: If retrieval fails or returns irrelevant docs, LLM hallucinates.

### Token
A unit of text processed by language model (roughly 1 word ≈ 1.3 tokens).

**Concern**: Token limit exhaustion when input is too long.

### Embedding
Vector representation of text (or other modality) in high-dimensional space.

**Risk**: If embedding model changes, similarity search results change unexpectedly.

### Context Window
Maximum length of text (in tokens) an LLM can process in one request.

**Example**: GPT-4 has 128K token context window (≈ 96K words).

### Fine-tuning
Adapting a pre-trained model on task-specific data.

**Risk**: Distribution shift if fine-tuning data differs from production data.

---

## Observability Terms

### Metric
Numerical measurement of system behavior over time (e.g., error rate, latency, CPU usage).

**Types**: Gauge (point-in-time), Counter (cumulative), Histogram (distribution)

### Log
Timestamped record of an event or action in the system.

**Key logs to track**: Errors, state changes, latency spikes, resource exhaustion

### Trace
Request flow through system, showing dependencies and timing.

**Example**: HTTP request → database query → cache lookup → response

### Alert
Automated notification when a metric exceeds threshold.

**Goal**: Humans alerted within minutes of failure detection.

### Anomaly Detection
Automatically identifying unusual patterns in metrics/data.

**Example**: Detecting unusual spike in model prediction latency.

---

## Testing Terms

### Chaos Experiment
Intentional failure injection to test resilience.

**Process**: Define failure → Inject → Measure impact → Rollback

### Dry Run
Simulation of experiment showing what would happen without actually running it.

**Always run `--dry-run` first!**

### Blast Radius
Scope of impact during experiment (e.g., "5% of traffic", "staging only").

**Rule**: Keep it small and bounded.

### Rollback
Immediate restoration of system to last known-good state.

**Requirement**: Rollback must be automatic or manual kill switch must work within seconds.

---

## Incident Response Terms

### Runbook
Step-by-step playbook for responding to a specific type of incident.

**Sections**: Symptoms → Triage → Mitigation → Recovery → Post-mortem

### On-Call
Role responsible for responding to incidents outside business hours.

**Key tool**: Runbooks reduce time to effective response.

### Root Cause Analysis (RCA)
Post-incident investigation to identify why a failure occurred.

**Goal**: Prevent same failure from happening again.

### Blameless Post-Mortem
RCA process focused on systems/processes, not individual blame.

**Outcome**: Documented lessons and action items.

---

## See Also

- [Theory & Principles](THEORY.md) — Deeper context
- [References](REFERENCES.md) — Papers and tools
- [Patterns](../patterns/) — Real examples using these concepts
