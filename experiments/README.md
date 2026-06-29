# Experiments: Runnable Chaos Scenarios

This directory contains executable chaos engineering experiments.

⚠️ **Safety First**: Always use `--dry-run` before running experiments.

---

## Quick Start

```bash
# See what would happen (no changes)
python experiments/ml-models/feature-staleness-sim/run.py --dry-run

# Run in staging environment
python experiments/ml-models/feature-staleness-sim/run.py --env=staging

# Run with verbose output
python experiments/ml-models/feature-staleness-sim/run.py --env=staging --verbose
```

---

## Safety Guidelines

### Before Running ANY Experiment

- [ ] Understand what the experiment does (read the README)
- [ ] Run `--dry-run` first
- [ ] Get approval from team lead / on-call engineer
- [ ] Use staging/test environment (never production)
- [ ] Have a rollback plan
- [ ] Have monitoring dashboards open
- [ ] Know how to kill the experiment immediately

### Required Experiment Features

Every experiment MUST have:

```python
--dry-run          # Show what would happen without doing it
--env=staging      # Specify target environment
--timeout=60       # Kill experiment after N seconds
--blast-radius=5   # Affect only 5% of traffic (example)
--verbose          # Show detailed output
```

### Blast Radius Limits

- Staging/test: Can be 100% (no real users)
- Pre-production: Max 25%
- Production: Max 5% (requires special approval)

### Automatic Rollback

Every experiment should have a kill switch:

```python
if __name__ == "__main__":
    import signal
    import sys
    
    def cleanup(sig, frame):
        print("Rolling back...")
        # Restore system to baseline
        sys.exit(0)
    
    signal.signal(signal.SIGINT, cleanup)
    run_experiment()
```

---

## Experiment Structure

Each experiment directory contains:

```
experiments/[category]/[experiment-name]/
├── README.md           # What, why, how
├── run.py              # Main chaos injection script
├── requirements.txt    # Python dependencies
├── observability/
│   ├── prometheus-alerts.yaml
│   ├── grafana-dashboard.json
│   └── log-patterns.md
└── results/            # Output from runs (git-ignored)
    └── 2024-01-15-run-1/
        ├── metrics.csv
        ├── logs.txt
        └── analysis.md
```

---

## By System Type

### Traditional Systems

```
experiments/traditional-systems/
├── kafka-broker-failure/        # Simulate broker down
├── postgres-failover/           # Test database failover
├── load-balancer-asymmetry/     # Asymmetric load distribution
└── ...
```

### Data Pipelines

```
experiments/data-pipelines/
├── airflow-dag-failure/         # DAG execution failure
├── schema-collision/            # Schema mismatch
├── dbt-test-override/           # Data quality test failure
├── spark-partition-skew/        # Uneven data distribution
└── ...
```

### ML Models

```
experiments/ml-models/
├── feature-staleness-sim/       # Stale features in inference
├── model-inference-latency-spike/
├── training-data-poisoning/
├── batch-scoring-backlog/
└── ...
```

### GenAI Models

```
experiments/genai-models/
├── llm-hallucination-test/      # Inject hallucinations
├── embedding-drift-simulation/  # Change embeddings
├── rag-retrieval-failure/       # Broken RAG pipeline
├── token-limit-stress-test/     # Very long inputs
└── ...
```

### Personalization

```
experiments/personalization/
├── rec-engine-cold-start/       # New user with no history
├── ab-test-data-corruption/     # Bad experiment data
├── user-segment-divergence/     # Segment definition changed
└── ...
```

---

## Running Experiments Safely

### Single Experiment

```bash
# Check what it does
less experiments/data-pipelines/airflow-dag-failure/README.md

# Dry run
cd experiments/data-pipelines/airflow-dag-failure/
python run.py --dry-run

# Staging run
python run.py --env=staging --blast-radius=10
```

### Full Suite (Careful!)

```bash
# Run all experiments in sequence (very long!)
bash run-all-experiments.sh --env=staging

# Run category (e.g., all data pipeline experiments)
bash run-all-experiments.sh --category=data-pipelines --env=staging
```

### With Monitoring

```bash
# Terminal 1: Start monitoring
open http://localhost:3000/grafana-chaos-dashboard

# Terminal 2: Run experiment
python experiments/ml-models/feature-staleness-sim/run.py --env=staging

# Watch metrics in Grafana as experiment runs
```

---

## Tools

### Chaos Tools Configuration

- **Chaos Mesh** (Kubernetes): [tools/chaos-mesh/](tools/chaos-mesh/)
  - For containerized systems
  - Network, pod, storage failures

- **Locust** (Load testing): [tools/locust/](tools/locust/)
  - Generate traffic at scale
  - Simulate connection failures

- **Pytest-Chaos** (Python): [tools/pytest-chaos/](tools/pytest-chaos/)
  - Unit/integration test harness
  - Inject failures during tests

- **Terraform** (Infrastructure): [tools/terraform/](tools/terraform/)
  - Provision test environments
  - Cleanup after experiments

### Using Chaos Mesh

```bash
# Install
kubectl apply -f https://mirrors.chaos-mesh.org/v2.5.1/chaosctl

# Deploy experiment
kubectl apply -f experiments/tools/chaos-mesh/network-partition.yaml

# Monitor
kubectl logs -n chaos-testing -l app=chaos-daemon

# Clean up
kubectl delete -f experiments/tools/chaos-mesh/network-partition.yaml
```

### Using Locust

```bash
# Install
pip install locust

# Run load test
locust -f experiments/tools/locust/locustfile.py \
  --host=http://api-staging.example.com \
  --users=100 \
  --spawn-rate=10
```

---

## Experiment Results

Each experiment saves results to `results/[timestamp]/`:

```
results/2024-01-15-run-1/
├── metrics.csv         # Prometheus metrics during run
├── logs.txt            # Captured logs
├── alerts.json         # Alerts that fired
├── traces.json         # Distributed traces
├── analysis.md         # Auto-generated analysis
└── video.mp4           # Screen recording (optional)
```

### Analyzing Results

```bash
# View results from latest run
less results/$(ls -t | head -1)/analysis.md

# Compare multiple runs
python tools/compare-experiments.py results/run-1/ results/run-2/

# Generate report
python tools/report-generator.py results/latest
```

---

## Common Experiments

### 1. Feature Store Outage

```bash
cd experiments/data-pipelines/feature-store-outage/
python run.py --env=staging --duration=300
# Simulates 5-minute feature store downtime
# Watches: Model inference latency, error rate, fallback effectiveness
```

### 2. Model Drift Injection

```bash
cd experiments/ml-models/feature-staleness-sim/
python run.py --env=staging --drift-magnitude=0.5
# Injects 50% distribution shift in features
# Watches: Model accuracy, confidence, data quality metrics
```

### 3. LLM Hallucination Test

```bash
cd experiments/genai-models/llm-hallucination-test/
python run.py --env=staging --hallucination-rate=0.1
# Injects hallucinations in 10% of responses
# Watches: Citation validation, user feedback, detection time
```

### 4. Data Pipeline SLA Breach

```bash
cd experiments/data-pipelines/sla-violation-cascades/
python run.py --env=staging --delay=3600
# Delays data pipeline by 1 hour
# Watches: Downstream model serving, freshness metrics, alerts
```

---

## Troubleshooting

### Experiment Won't Start

```bash
# Check prerequisites
python run.py --check-prereqs

# Install missing dependencies
pip install -r requirements.txt

# Check environment setup
python run.py --validate-env
```

### Experiment Stuck

```bash
# Kill it immediately
ctrl-c

# Or in another terminal
pkill -f "python run.py"

# Rollback manually
terraform destroy -var="environment=staging"
```

### Results Missing

```bash
# Check if results were saved
ls -la results/

# Check logs
tail -100f results/latest/logs.txt

# Check if experiment actually ran
python run.py --dry-run --verbose
```

---

## Contributing Experiments

Want to add a new experiment?

1. Pick a pattern: [patterns/](../patterns/)
2. Copy template: [templates/experiment-template.py](../templates/experiment-template.py)
3. Implement the chaos injection
4. Add observability setup
5. Document expected results
6. Test in staging
7. Open a PR!

See [CONTRIBUTING.md](../CONTRIBUTING.md) for details.

---

## Next Steps

1. **Start with**: One experiment from your system type (staging only!)
2. **Build observability**: Get dashboards working before chaos
3. **Document findings**: What did you learn?
4. **Contribute**: Share your results!

---

⚠️ **Remember**: The goal is learning, not breaking. Start small, scale up carefully.
