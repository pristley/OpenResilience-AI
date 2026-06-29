# References: Papers, Tools, and Resources

## Core Papers

### Foundational

- **"The Fallacies of Distributed Computing Explained"** — Rosenthal, Deutsch, et al.
  - Essential reading for understanding why distributed systems are hard
  - Explains 8 false assumptions that cause failures

- **"Designing Data-Intensive Applications"** — Martin Kleppmann
  - Comprehensive guide to distributed systems, consensus, replication
  - Chapter 8 (Distributed Systems) is must-read

- **"Out of the Tar Pit"** — Moseley & Marks
  - Argues complexity is main enemy of systems
  - Strategies to manage it

### Chaos Engineering

- **"Chaos Engineering: System Resiliency in Practice"** — Rosenthal et al.
  - O'Reilly book defining the discipline
  - Principles: observability, hypothesis-driven, automation

- **"Principles of Chaos Engineering"** — https://principlesofchaos.org/
  - Community-driven principles for chaos engineering
  - Short, practical, widely adopted

- **"Chaos Engineering in the Age of Microservices"** — Eckert et al.
  - How chaos applies to microservices specifically

### SRE & Operations

- **"Site Reliability Engineering"** — Google
  - Free book: https://sre.google/
  - Error budgets, SLOs, postmortems, oncall

- **"The DevOps Handbook"** — Gene Kim et al.
  - Practices for continuous delivery and resilience

### Data Systems

- **"Big Data: Principles, Practices, and Promises"** — McHugh et al.
  - Challenges in large-scale data systems

- **"The Watermarks and the Wall: The Architecture of Pub/Sub Systems"** — Dean & Ghemawat
  - How to build reliable data pipelines

### ML Resilience

- **"Machine Learning: The High-Interest Credit Card of Technical Debt"** — Sculley et al.
  - Hidden costs and risks of ML systems

- **"Hidden Technical Debt in Machine Learning Systems"** — Sculley et al.
  - Data dependencies, model degradation, feedback loops

- **"On the Dangers of Stochastic Parrots"** — Bender et al.
  - Limitations and risks of large language models

---

## Recommended Books

| Title | Author | Focus | Level |
|---|---|---|---|
| Designing Data-Intensive Applications | Kleppmann | Distributed systems, data | Intermediate |
| Site Reliability Engineering | Google | Operations, SRE | Intermediate |
| The DevOps Handbook | Kim et al. | Continuous delivery | Intermediate |
| Chaos Engineering | Rosenthal et al. | Chaos, resilience | Beginner |
| Release It! | Michael Nygard | Production readiness | Intermediate |
| Building Microservices | Sam Newman | Microservices | Intermediate |

---

## Tools

### Chaos Injection

- **Chaos Mesh** (https://chaos-mesh.org/)
  - Kubernetes-native chaos engineering framework
  - Supports network, pod, and storage faults
  - Open source

- **Gremlin** (https://www.gremlin.com/)
  - Commercial chaos platform
  - Works with VMs, containers, Kubernetes
  - GUI + API

- **Chaos Toolkit** (https://chaostoolkit.org/)
  - Open source, extensible chaos framework
  - Python-based

- **Locust** (https://locust.io/)
  - Load testing tool
  - Python-based, open source
  - Great for simulating traffic failures

### Observability

- **Prometheus** (https://prometheus.io/)
  - Metrics collection and alerting
  - Open source, widely adopted
  - Time-series database

- **Grafana** (https://grafana.com/)
  - Dashboard and visualization
  - Works with Prometheus, many backends
  - Open source

- **Jaeger** (https://www.jaegertracing.io/)
  - Distributed tracing
  - Visualize request flow through system
  - Open source

- **ELK Stack** (Elasticsearch, Logstash, Kibana)
  - Log aggregation and visualization
  - Open source

- **Datadog** (https://www.datadoghq.com/)
  - Commercial observability platform
  - Metrics, traces, logs, error tracking

### Data Quality

- **Great Expectations** (https://greatexpectations.io/)
  - Data quality framework
  - Define expectations, validate, document
  - Python-based, open source

- **Soda** (https://www.soda.io/)
  - Data quality monitoring
  - Automated testing for data pipelines

- **Freshness Audit** 
  - Track data age / staleness
  - Generic concept, various implementations

### ML Monitoring

- **MLflow** (https://mlflow.org/)
  - Experiment tracking, model registry, serving
  - Open source

- **Evidently** (https://www.evidentlyai.com/)
  - Model and data drift detection
  - Python-based

- **Arize** (https://arize.com/)
  - Commercial ML monitoring platform
  - Production model observability

### Feature Stores

- **Tecton** (https://www.tecton.ai/)
  - Commercial feature store
  - Real-time + batch features

- **Feast** (https://feast.dev/)
  - Open source feature store
  - Materialization for inference

- **Hopsworks** (https://www.hopsworks.ai/)
  - Feature store + ML platform

---

## Talks & Videos

### Conference Talks

- "Chaos Engineering" series at various conferences (KubeCon, QCon, etc.)
- Netflix talks on chaos: https://www.youtube.com/results?search_query=netflix+chaos+engineering
- Google SRE talks: https://sre.google/talks/

### Podcasts

- **CaSE (Chaos as a Service Engineering)**: https://www.case-podcast.org/
- **Software Engineering Daily**: Frequent episodes on SRE, chaos, reliability

### Online Resources

- **Chaos Engineering on Coursera**: https://www.coursera.org/learn/chaos-engineering/
- **Linux Academy / A Cloud Guru**: Various SRE and chaos courses
- **YouTube**: Search "chaos engineering tutorial", "distributed systems failure modes"

---

## Community

- **Chaos Engineering Community**: https://www.chaosexperience.org/
- **Cloud Native Computing Foundation (CNCF)**: https://www.cncf.io/
- **Site Reliability Engineering (SRE) Slack Community**
- **Reddit**: r/devops, r/sre, r/machinelearning

---

## Related Topics to Study

- **Distributed consensus**: Raft, Paxos (understand why they're hard)
- **Load balancing**: Algorithms, failure modes, health checks
- **Database replication**: Multi-master, leader-follower, consistency models
- **Circuit breakers & bulkheads**: Design patterns for resilience
- **Graceful degradation**: How to serve reduced functionality
- **Feature flags**: How to safely roll out changes
- **Observability**: Metrics, logs, traces, alerting

---

## Pattern-Specific References

### Network Failures
- "Timeout and Retry Logic" — AWS Architecture Blog
- "Circuit Breaker Pattern" — Martin Fowler

### Data Pipelines
- "Exactly-Once Semantics in Streaming" — Confluent blog
- "Schema Management in Data Pipelines" — dbt + Great Expectations

### ML Systems
- "Model Drift Detection" — Evidently blog posts
- "Feature Store Design" — various MLOPS conference talks

### GenAI Systems
- "RAG Best Practices" — LangChain documentation
- "Prompt Injection Attacks" — OWASP

---

## Next Steps

1. **Start with**: Principles of Chaos Engineering (short, accessible)
2. **Then read**: One chapter from Designing Data-Intensive Applications
3. **Pick a topic**: Choose one area (data pipelines, ML, GenAI) and dive deeper
4. **Watch talks**: 2-3 conference talks on your chosen topic
5. **Explore tools**: Experiment with Chaos Mesh or Locust in staging

---

**Contributing**: Have a paper or resource to add? Open a PR!
