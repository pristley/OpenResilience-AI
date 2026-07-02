# Pattern: Hallucination Injection & Recovery

## Problem Statement

LLMs occasionally generate factually incorrect outputs ("hallucinations")—plausible-sounding responses that contradict ground truth. Your system must detect these and gracefully degrade when they occur, preventing misinformation from reaching users or downstream systems.

**Example Scenario:**
- Customer support chatbot recommends "restart the server" when docs say "restart the application"
- Financial advisory LLM cites incorrect historical stock prices
- Medical LLM fabricates symptom-treatment relationships not in training data

---

## Why It Matters

- **Impact**: Wrong recommendations erode trust, compliance violations, financial losses, reputational damage
- **Detection latency**: Often invisible—users don't complain about facts they believe are true until independent verification
- **Blast radius**: Depends on downstream usage (advisory vs. binding decisions)
  - *Direct*: User reads hallucination
  - *Downstream*: Hallucination fed into recommendation engine, flagged as "customer feedback" for retraining
  - *Systemic*: Bad corrections create new hallucinations in future models

- **Real Cost**: 2-hour detection delay × high-touch customer interactions = reputation damage

---

## How It Fails

### Mechanism

1. **LLM generation**: Model generates plausible-sounding but factually wrong content
   - High confidence score despite low factuality
   - Fills knowledge gaps with fabrications rather than refusing
2. **Validation gap**: Application doesn't validate output against ground truth
   - No fact-checking layer
   - Assumes LLM outputs are reliable
3. **Propagation**: Hallucinated output reaches user or downstream system
   - User sees it in UI
   - Passed to recommendation engine
   - Stored in database as "verified" fact
4. **Feedback loop**: User "corrects" hallucination or model retrains on bad data
   - System learns hallucination was acceptable
   - Next model inherits pattern

### Observable Signals

- **Metric anomalies**:
  - Confidence score ≥ 0.9 but factuality ≤ 0.5
  - Citation-backed claims have zero matching sources
  - Same prompt returns contradictory facts across runs
- **Log patterns**:
  - "Source validation failed" entries spike
  - Schema/constraint violation warnings
  - User feedback flagged as "contradiction"
- **Trace patterns**:
  - Retrieval relevance scores very low but LLM proceeds
  - Token probability distribution shows uncertain choices
  - No retrieval sources used despite grounding requirement
- **Business signals**:
  - Customer complaints about accuracy
  - QA team reports inconsistent responses
  - Downstream model accuracy drops suddenly

### Time to Detect

- **Best case** (human review of sample): seconds to minutes
- **Realistic** (automated sampling + validation): minutes to hours
- **Worst case** (user complaints, social media): hours to days

### Blast Radius

- **Direct**: Single user sees wrong recommendation
- **Downstream**: 
  - Hallucination used as training signal → propagates to new models
  - Passed to recommendation engine → affects multiple users
  - Stored as "ground truth" → corrupts data warehouse
- **Indirect**:
  - Compliance audit finds hallucinated claims
  - Upstream system trusts output, fails downstream
- **Reputational**: Public-facing errors erode trust permanently

---

## Resilience Strategy

### Prevention

1. **Prompt Engineering**
   - Add explicit guardrails: "If you're unsure, respond with 'I don't know'"
   - Include domain constraints: "Output must conform to schema: {stock_price: float, date: YYYY-MM-DD}"
   - Require citations: "For each claim, cite the source document"
   - *Trade-off*: Longer prompts, slight latency increase

2. **Retrieval Augmentation (RAG)**
   - Ground responses in known-good sources
   - Validate retrieval relevance before passing to LLM
   - Require minimum semantic similarity (e.g., cosine ≥ 0.8)
   - *Trade-off*: Depends on external knowledge base availability; stale sources introduce new risks

3. **Confidence Thresholding**
   - Return "unknown" if confidence < threshold (e.g., 0.85)
   - Monitor confidence calibration (is model well-calibrated?)
   - *Trade-off*: May return "unknown" too often, reducing usefulness

4. **Constraint Validation**
   - Check output against schema/business rules before serving
   - Examples: date ranges, numerical bounds, referential integrity
   - Use tools like Pydantic to enforce types
   - *Trade-off*: Requires domain knowledge to define constraints

5. **Ensemble Approaches**
   - Query multiple LLM versions/providers, flag disagreements
   - Cross-check claims against vector DB of facts
   - *Trade-off*: Cost increases; latency increases

### Detection

**Alerting thresholds:**
```yaml
metrics:
  - name: hallucination_rate
    definition: (flagged_contradictions / total_outputs) × 100
    alert_threshold: > 5%
    window: 15min
    severity: critical
  
  - name: confidence_vs_factuality_drift
    definition: abs(predicted_confidence - validation_accuracy)
    alert_threshold: > 0.2
    window: hourly
    severity: warning
  
  - name: unvalidated_source_rate
    definition: (outputs_without_retrieval / outputs_requiring_grounding) × 100
    alert_threshold: > 10%
    window: 15min
    severity: warning

  - name: citation_verification_failure
    definition: (cited_sources_not_found / total_citations) × 100
    alert_threshold: > 15%
    window: hourly
    severity: warning

logs:
  - pattern: "source_validation_failed"
    action: "Log context, flag for review"
  - pattern: "constraint_violation"
    action: "Alert on-call, trigger fallback"
  - pattern: "user_contradiction_feedback"
    action: "Increment hallucination_rate metric"

traces:
  - check: "retrieval_source_relevance < 0.7 AND confidence > 0.8"
    action: "Flag as potential hallucination"
  - check: "token_entropy > threshold at generation start"
    action: "Monitor uncertainty propagation"
```

**Observability checklist:**
- [ ] Metric: hallucination_rate, confidence_vs_factuality_drift, unvalidated_source_rate
- [ ] Log: source_validation_failed, constraint_violation, user_contradiction
- [ ] Trace: retrieval source relevance, token probability distribution
- [ ] Health check: Can validator quickly validate sample outputs?
- [ ] Dashboard: Real-time hallucination rate by model version, LLM provider

### Recovery

1. **Graceful Degradation**
   - Return "I don't know" instead of serving hallucination
   - Explain why to user: "Insufficient confidence (0.72 < threshold 0.85)"
   - Trade-off: Better for user trust; reduces feature utility

2. **Fallback to Conservative Model**
   - Switch to older, more reliable LLM version
   - Use smaller model with lower hallucination tendency
   - Trade-off: Reduced capabilities; may be slower

3. **Human Review Flag**
   - Send to review queue before serving to customers
   - Use ML classifier to prioritize review (most likely hallucinators first)
   - Trade-off: Introduces latency; requires human resources

4. **Circuit Breaker**
   - If hallucination_rate > 10% for 5 min → disable LLM feature entirely
   - Switch to cached responses or stub API
   - Trade-off: Feature unavailability; better than misinformation

5. **Rollback to Prior Model Version**
   - If hallucination rate spikes > 2x baseline after deployment
   - Automated rollback trigger
   - Trade-off: Lost improvements from new version; manual investigation needed

6. **Feedback Loop Correction**
   - Don't automatically trust user corrections as ground truth
   - Require multi-source validation before using as training signal
   - Exclude flagged hallucinations from retraining dataset
   - Trade-off: More complex ML pipeline

---

## Chaos Experiment: Inject Hallucinations

**Objective**: Verify system can detect and gracefully degrade when LLM outputs become unreliable.

```python
# experiments/genai-models/hallucination-injection/run.py
import re
import random
import anthropic
from datetime import datetime, timedelta
from typing import Dict, List
import requests
import json

class HallucinationInjector:
    """Inject realistic hallucinations into LLM responses for chaos testing."""
    
    def __init__(self):
        self.client = anthropic.Anthropic()
    
    def inject_date_hallucination(self, response: str) -> str:
        """Replace actual dates with plausible wrong dates."""
        pattern = r'\b(202[0-9]|202[4-9]|203[0-5])\b'
        wrong_year = random.randint(2020, 2035)
        return re.sub(pattern, str(wrong_year), response)
    
    def inject_number_hallucination(self, response: str) -> str:
        """Replace percentages/metrics with wrong values."""
        # Replace percentages
        response = re.sub(
            r'(\d+)%',
            lambda m: f"{random.randint(1, 99)}%",
            response
        )
        # Replace prices
        response = re.sub(
            r'\$(\d+)',
            lambda m: f"${random.randint(10, 9999)}",
            response
        )
        return response
    
    def inject_entity_hallucination(self, response: str) -> str:
        """Swap named entities (people, companies, places)."""
        swaps = {
            "Apple": "Microsoft",
            "Microsoft": "Google",
            "Google": "Amazon",
            "Tesla": "Ford",
            "OpenAI": "Anthropic",
            "January": "February",
            "March": "April",
            "Monday": "Tuesday",
        }
        result = response
        for original, replacement in swaps.items():
            result = re.sub(rf'\b{original}\b', replacement, result)
        return result
    
    def inject_schema_violation(self, response: str, schema: Dict) -> str:
        """Inject data that violates expected schema constraints."""
        # Example: If schema expects temp_celsius < 100, inject 500
        if "temperature" in response.lower():
            response = re.sub(r'(\d+)\s*°?C', "500°C", response)
        return response
    
    def test_hallucination_detection(self):
        """Test if system detects injected hallucinations."""
        test_cases = [
            {
                "prompt": "What was Apple's stock price on January 15, 2024?",
                "type": "date",
                "validator_url": "http://localhost:8000/validate"
            },
            {
                "prompt": "What percentage of the US population uses smartphones?",
                "type": "number",
                "validator_url": "http://localhost:8000/validate"
            },
            {
                "prompt": "Who is the CEO of Microsoft?",
                "type": "entity",
                "validator_url": "http://localhost:8000/validate"
            }
        ]
        
        results = {"passed": 0, "failed": 0, "details": []}
        
        for test_case in test_cases:
            try:
                # Get real LLM response
                message = self.client.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=256,
                    messages=[
                        {"role": "user", "content": test_case["prompt"]}
                    ]
                )
                real_response = message.content[0].text
                
                # Inject hallucination
                if test_case["type"] == "date":
                    hallucinated = self.inject_date_hallucination(real_response)
                elif test_case["type"] == "number":
                    hallucinated = self.inject_number_hallucination(real_response)
                else:
                    hallucinated = self.inject_entity_hallucination(real_response)
                
                # Send to validator
                validation_response = requests.post(
                    test_case["validator_url"],
                    json={
                        "response": hallucinated,
                        "prompt": test_case["prompt"]
                    }
                )
                
                validator_result = validation_response.json()
                
                # Check: Was hallucination flagged?
                if validator_result.get("flagged"):
                    results["passed"] += 1
                    results["details"].append({
                        "test": test_case["type"],
                        "status": "✅ PASS",
                        "reason": "Validator correctly flagged hallucination"
                    })
                else:
                    results["failed"] += 1
                    results["details"].append({
                        "test": test_case["type"],
                        "status": "❌ FAIL",
                        "reason": "Validator missed hallucination",
                        "real": real_response[:100],
                        "hallucinated": hallucinated[:100]
                    })
            
            except Exception as e:
                results["failed"] += 1
                results["details"].append({
                    "test": test_case["type"],
                    "status": "❌ ERROR",
                    "error": str(e)
                })
        
        return results
    
    def test_graceful_degradation(self):
        """Test if app gracefully degrades when hallucination detected."""
        test_prompt = "Provide financial advice on cryptocurrency"
        
        # This is high-hallucination domain
        message = self.client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=256,
            messages=[{"role": "user", "content": test_prompt}]
        )
        response = message.content[0].text
        
        # Send to app
        try:
            app_response = requests.post(
                "http://localhost:8000/process",
                json={"response": response}
            )
            app_result = app_response.json()
            
            # Check: Did app degrade gracefully?
            if app_result.get("status") in ["degraded", "fallback", "flagged_for_review"]:
                return {
                    "status": "✅ PASS",
                    "reason": "App correctly degraded on high-risk domain"
                }
            else:
                return {
                    "status": "❌ FAIL",
                    "reason": f"App served unfiltered response: {app_result.get('status')}"
                }
        except Exception as e:
            return {
                "status": "❌ ERROR",
                "error": str(e)
            }

if __name__ == "__main__":
    injector = HallucinationInjector()
    
    print("=" * 60)
    print("HALLUCINATION INJECTION CHAOS TEST")
    print("=" * 60)
    
    print("\n[1/2] Testing hallucination detection...")
    detection_results = injector.test_hallucination_detection()
    print(f"Detection: {detection_results['passed']} passed, {detection_results['failed']} failed")
    for detail in detection_results["details"]:
        print(f"  {detail['status']} {detail['test']}: {detail.get('reason', detail.get('error'))}")
    
    print("\n[2/2] Testing graceful degradation...")
    degradation_result = injector.test_graceful_degradation()
    print(f"  {degradation_result['status']}: {degradation_result.get('reason', degradation_result.get('error'))}")
    
    # Exit code: fail if any test failed
    if detection_results["failed"] > 0 or degradation_result["status"] != "✅ PASS":
        print("\n❌ CHAOS TEST FAILED")
        exit(1)
    else:
        print("\n✅ ALL CHAOS TESTS PASSED")
        exit(0)
```

**Tools & Setup:**

```bash
# Install dependencies
pip install anthropic pydantic great-expectations requests

# Run hallucination detector service
python experiments/genai-models/hallucination-injection/validator_service.py &

# Run chaos test
python experiments/genai-models/hallucination-injection/run.py

# Monitor metrics
prometheus -c observability/prometheus.yml &
grafana-server &
open http://localhost:3000/d/hallucination-dashboard
```

---

## Lessons Learned

### Case Study: Support Chatbot RAG Hallucination

**Incident Summary:**
- LLM-powered support chatbot told customer to "restart the server" when documentation said "restart the application"
- Customer followed advice, restarted production database server instead of admin UI
- 15-minute service outage, $50K estimated impact

**Root Cause Analysis:**
1. Retrieval system returned tangentially related docs (containing "restart" and "server")
2. Relevance filtering absent (no cosine similarity check)
3. LLM filled knowledge gap with plausible-sounding but wrong guidance
4. No validation layer before serving to customer

**Detection:**
- **Time**: 2 hours (customer support ticket → escalation → investigation)
- **Indicator**: Customer feedback loop flagged as "user contradiction"

**Fix Implemented:**
1. Added semantic relevance check (cosine similarity > 0.8) before passing retrieval results to LLM
2. Implemented confidence thresholding: response confidence must exceed 0.85
3. Added validation: check output against FAQ knowledge graph
4. Circuit breaker: disable chatbot if validation failures > 10%

**Prevention for Future:**
- Validation of retrieval sources now mandatory in RAG pipeline
- Query intent classification: high-risk domains (medical, financial, infrastructure) require human review
- Baseline metric: 0.5% hallucination rate → alert if > 1% in 15 min window

---

## References

- [Survey: Hallucinations in LLMs](https://arxiv.org/abs/2309.01219)
- [Anthropic: Constitutional AI](https://www.anthropic.com/research/constitutional-ai)
- [Confidence Calibration in NLP](https://aclanthology.org/2020.findings-acl.76/)
- [RAG Best Practices](https://weaviate.io/blog/retrieval-augmented-generation)
- [Great Expectations Data Docs](https://greatexpectations.io/)
