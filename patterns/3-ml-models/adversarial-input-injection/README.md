# Pattern: Adversarial Input Injection

> ML models fooled by imperceptible adversarial perturbations; security breach with systematic mispredictions.

## Quick Summary

**Problem**: Input data modified by imperceptible perturbations (pixels, characters, features) causes model misclassification  
**Impact**: Security breach, fraudulent transactions ($500K+), trust violation  
**Detection Time**: Milliseconds (robustness test) to hours (runtime detection)  
**Solution**: Adversarial training, ensemble defense, input validation, certified robustness

---

## Problem Statement

Adversarial examples are inputs designed to cause ML models to make incorrect predictions. These perturbations are often imperceptible to humans but fool models systematically. In production:
- **Image classification**: Stop sign misclassified as speed limit
- **Fraud detection**: Legitimate transaction marked as fraud via feature manipulation
- **Recommendation**: Negative review artificially boosted via adversarial embedding
- **NLP**: Spam detector bypassed via character substitution

## Why It Matters

- **Security Risk**: Attackers can manipulate system behavior without detection
- **Financial Impact**: Fraudulent transactions approved ($500K+ before detection)
- **Trust Erosion**: When discovered, damages model credibility
- **Cascade Failure**: Compromised predictions trigger downstream errors
- **Regulatory**: Security breach may trigger compliance violations

## How It Fails

### Failure Mode

1. **Attack Vectors**:
   - FGSM (Fast Gradient Sign Method): Small gradient-based perturbations
   - Character substitution: l → 1, O → 0 in spam detection
   - Feature manipulation: Scale outliers, modify top-k features
   - Universal perturbations: Single noise pattern fools model on any input

2. **Detection Difficulty**:
   - Perturbations imperceptible (ΔL∞ < 0.05 in pixel space)
   - Model confidence unchanged (still predicts with high confidence)
   - Runtime detection requires reference validator or statistical test

### Observable Signals

- Sudden accuracy spike on specific input patterns
- Confidence scores disconnected from correctness
- Clustered misclassifications on semantically similar inputs
- Performance degradation against adversarial test set

### Detection Time

- **Pre-deployment**: Milliseconds (robustness test suite)
- **Runtime**: Hours to days (requires monitoring + manual review)
- **Post-incident**: Days to weeks (forensic analysis)

### Blast Radius

- **Partial**: Specific input types exploited (e.g., images at edge)
- **System-wide**: Universal perturbation affects all inputs
- **Cascade**: Malicious actor creates feedback loop (fraud → flagged → appeals → model training poisoning)

## Resilience Strategy

### Prevention

1. **Adversarial Training**:
   ```python
   # Train model robust to perturbations
   adversarial_examples = [x + 0.3 * sign(∇_x L(model, x, y)) for x, y in data]
   model.train(adversarial_examples + original_examples)
   ```

2. **Input Validation**:
   - Sanity checks: Value ranges, data types, statistical properties
   - Anomaly detection: Outlier detection on feature distributions
   - Constraint enforcement: Business logic validation

3. **Ensemble Defense**:
   - Combine multiple diverse models (different architectures, training)
   - Require consensus (all models must agree to execute action)
   - Reduces probability adversarial example fools all models

### Detection

1. **Robustness Testing**:
   ```python
   # Pre-deployment: Generate adversarial examples, verify model resists
   for attack in [fgsm, pgd, carlini_wagner]:
       adv_examples = attack(model, clean_data)
       accuracy = model.evaluate(adv_examples)
       assert accuracy > 0.8, f"Model vulnerable to {attack}"
   ```

2. **Runtime Monitoring**:
   - Prediction confidence distribution (alert if confidence drops unexpectedly)
   - Input gradient monitoring (if input gradient spikes, likely adversarial)
   - Shadow model comparison (simpler model disagrees → investigate)

3. **Statistical Tests**:
   - Kolmogorov-Smirnov test on prediction distribution
   - Track model's robustness metric over time

### Recovery

1. **Immediate**:
   - Route suspicious inputs to human review
   - Execute conservative fallback (reject/defer decision)
   - Alert security team

2. **Short-term**:
   - Retrain model with adversarial examples
   - Add input constraints based on incident patterns
   - Deploy ensemble if robustness insufficient

3. **Long-term**:
   - Implement certified robustness guarantees
   - Regular adversarial red-teaming
   - Security monitoring dashboard

## Chaos Experiment

### Setup

```python
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.datasets import load_iris

class AdversarialInjector:
    def __init__(self, model):
        self.model = model
        self.benign_accuracy = None
        self.adversarial_accuracy = None
    
    def fgsm_attack(self, X, y, epsilon=0.3):
        """Fast Gradient Sign Method attack."""
        X_adv = X.copy()
        for i, (x, label) in enumerate(zip(X, y)):
            # Compute gradient (simplified for tree-based models)
            x_perturb = x + np.random.normal(0, epsilon, x.shape)
            X_adv[i] = x_perturb
        return X_adv
    
    def character_substitution_attack(self, text):
        """Bypass spam detection via character substitution."""
        substitutions = {'a': '@', 'e': '3', 'i': '1', 'o': '0', 's': '5'}
        result = text
        for char, sub in substitutions.items():
            result = result.replace(char, sub)
        return result
    
    def test_robustness(self, X, y):
        """Test model robustness to adversarial examples."""
        self.benign_accuracy = self.model.score(X, y)
        print(f"Benign accuracy: {self.benign_accuracy:.3f}")
        
        # Generate adversarial examples
        X_adv = self.fgsm_attack(X, y)
        self.adversarial_accuracy = self.model.score(X_adv, y)
        print(f"Adversarial accuracy: {self.adversarial_accuracy:.3f}")
        
        robustness_ratio = self.adversarial_accuracy / self.benign_accuracy
        print(f"Robustness ratio: {robustness_ratio:.3f}")
        
        return {
            'benign_accuracy': self.benign_accuracy,
            'adversarial_accuracy': self.adversarial_accuracy,
            'robustness_ratio': robustness_ratio,
            'vulnerable': robustness_ratio < 0.7
        }
```

### Execution

```bash
# Test image classification model
python -c "
from experiments.genai_models import AdversarialInjector
from sklearn.datasets import load_iris
from sklearn.ensemble import RandomForestClassifier

X, y = load_iris(return_X_y=True)
model = RandomForestClassifier().fit(X, y)
injector = AdversarialInjector(model)
result = injector.test_robustness(X, y)
print(f'Vulnerable: {result[\"vulnerable\"]}')
"
```

## Case Study: E-Commerce Fraud Detection Bypass

**Incident**: Attacker manipulated transaction features (amount, merchant category, time) to bypass fraud detection model.

**Timeline**:
- **T+0**: Attacker discovers model vulnerable to adversarial perturbations
- **T+1hr**: 500 fraudulent transactions approved ($150K total)
- **T+4hr**: Pattern detection alerts trigger; investigation begins
- **T+8hr**: Root cause identified (adversarial features)
- **T+24hr**: Model retrained with adversarial examples; deployed
- **T+48hr**: Financial liability assessed ($500K+ refunds + chargeback fees)

**Resolution**:
- Added input constraints (reject transactions outside statistical bounds)
- Deployed ensemble model (fraud detection + rule-based system)
- Implemented robustness testing in CI/CD pipeline
- Quarterly adversarial red-teaming

## Key Metrics

### Monitoring

```yaml
AdversarialRobustness:
  - name: model_adversarial_accuracy
    description: "Accuracy on adversarial test set"
    threshold: {
      warning: "< 0.85",
      critical: "< 0.75"
    }
  
  - name: prediction_confidence_distribution
    description: "Distribution of confidence scores; alert if bimodal"
    threshold: {
      warning: "kurtosis > 3"
    }
  
  - name: input_feature_anomaly_score
    description: "Anomaly score for each input; alert if > 3σ"
    threshold: {
      warning: "mean_anomaly_score > 0.5"
    }
  
  - name: ensemble_disagreement_rate
    description: "Percentage of inputs where models disagree"
    threshold: {
      warning: "> 5%"
    }
```

## Prevention Checklist

- [ ] Perform adversarial robustness testing pre-deployment
- [ ] Implement input validation and constraint enforcement
- [ ] Deploy ensemble models for critical decisions
- [ ] Monitor prediction confidence and input anomalies
- [ ] Establish security review process for model changes
- [ ] Conduct quarterly red-teaming exercises
- [ ] Document adversarial threat model

## References

- Goodfellow et al. (2015): "Explaining and Harnessing Adversarial Examples"
- Carlini & Wagner (2017): "Towards Evaluating the Robustness of Neural Networks"
- Madry et al. (2019): "Towards Deep Learning Models Resistant to Adversarial Attacks"
- NIST AI Risk Management Framework

## See Also

- [Model Poisoning Detection](../model-poisoning-detection/)
- [Inference Latency Spike](../inference-latency-spike/)
- [Batch Prediction Backlog](../batch-prediction-backlog/)
