# Pattern: Feedback Loop Collapse & Training Data Poisoning

> Model errors stored as training labels; feedback loop compounds errors exponentially across retraining cycles.

## Quick Summary

**Problem**: Predictions used as training labels → errors become training data → next model learns errors → quality cascades  
**Impact**: Exponential quality degradation (90% → 70% over 3-5 cycles), requires data cleanup  
**Detection Time**: Weeks (takes 3-5 retraining cycles to notice trend)  
**Solution**: Feedback validation, separate training/production, held-out validation

---

## Problem Statement

Many ML systems use a feedback loop: collect user interactions, use model predictions as "ground truth" labels, retrain model on this data. This works when predictions are accurate, but when errors occur:

1. Model makes mistake: Recommends bad movie → user doesn't like it
2. System stores feedback: "This user dislikes this movie" (but reason was wrong recommendation)
3. Next model learns: "This user dislikes this movie" (learns wrong association)
4. Next model repeats error: Recommends similar movies → user dislikes → more poisoned data
5. Exponential degradation: After 5 cycles, model quality collapses

**Real examples**:
- **Content recommendation**: False positive recommendation → stored as negative signal → model learns to avoid good content
- **Fraud detection**: Legitimate transaction marked fraud → stored as "fraud pattern" → new model flags similar legitimate transactions
- **Search ranking**: Irrelevant result clicked → stored as "relevant" → ranking degrades
- **Medical diagnosis**: Doctor overrides model diagnosis → stored as ground truth → next model learns incorrect override pattern

## Why It Matters

- **Exponential Degradation**: Quality doesn't degrade linearly; drops cliff after threshold
- **Silent Failure**: No external error signal; system appears to work for weeks before collapse
- **Data Corruption**: Poisoned labels corrupt future training data irreversibly
- **Investigation Cost**: Requires data forensics to identify exactly when/where poisoning started
- **Recovery Time**: May require months of data cleanup before retraining works

## How It Fails

### Failure Mode

1. **Poisoned Feedback Loop**:
   - Cycle N model makes error
   - Error stored as training label in cycle N+1
   - Cycle N+1 model learns error
   - Cycle N+2 observes compounded errors

2. **Tipping Point**: Degradation accelerates once error rate exceeds ~20%
   - Below 20% errors: System still learns correct patterns
   - Above 20% errors: Noise dominates signal → model gets worse
   - Positive feedback: Worse model → more errors → more poisoned data

### Observable Signals

- Accuracy declining steadily over multiple retraining cycles
- New model performs worse than previous model (unusual)
- User engagement metrics declining (negative feedback)
- Confusion matrix showing systematic biases in wrong direction

### Detection Time

- **Statistical test**: Hours (if running tests on trained model)
- **Production impact**: Days to weeks (takes 3-5 retraining cycles)
- **Root cause identification**: Weeks to months (requires data forensics)

### Blast Radius

- **Partial**: Specific segments affected (e.g., certain user cohorts)
- **System-wide**: All predictions degraded
- **Cascade**: Requires data cleanup before recovery

## Resilience Strategy

### Prevention

1. **Feedback Validation**:
   ```python
   # Don't blindly use predictions as labels
   # Validate feedback before using for training
   if feedback_confidence < 0.8:  # Confidence threshold
       skip_this_sample()  # Don't use for training
   
   # Check for contradictions
   if sample_contradicts_multiple_past_samples():
       flag_for_review()  # Mark as suspicious
   ```

2. **Separation of Concerns**:
   - **Production model**: Use for serving
   - **Training model**: Train on explicitly labeled data only
   - **Evaluation model**: Held-out validation set (never seen production predictions)
   - Never use production predictions as training labels

3. **Human-in-the-Loop**:
   - Sample feedback for human review (e.g., 1% of feedback)
   - Agreement between human and system < 80%? Halt retraining
   - Require explicit labeling for sensitive decisions

### Detection

1. **Pre-Deployment Validation**:
   ```python
   # Before deploying new model, validate it's better than previous
   new_model_acc = evaluate(new_model, held_out_validation_set)
   old_model_acc = evaluate(old_model, held_out_validation_set)
   
   if new_model_acc < old_model_acc * 0.95:  # > 5% worse
       alert("New model worse than previous model!")
       require_manual_approval()
   ```

2. **Trend Analysis**:
   ```python
   # Track accuracy across retraining cycles
   accuracy_trend = [0.92, 0.91, 0.88, 0.83, 0.75]
   if slope < -0.05:  # Strong downward trend
       alert("Quality degrading; possible feedback loop poisoning")
   ```

3. **Held-Out Validation**:
   ```python
   # Maintain separate dataset of explicitly labeled data
   # Never retrain on production predictions
   # Use held-out set to detect poisoning
   held_out_accuracy = evaluate(new_model, held_out_set)
   if held_out_accuracy > production_accuracy:  # Large divergence
       alert("Possible training data poisoning")
   ```

### Recovery

1. **Immediate**:
   - Halt retraining (don't make poisoning worse)
   - Roll back to previous model version
   - Disable feedback loop temporarily

2. **Short-term**:
   - Audit recent feedback data for poisoning
   - Retrain on held-out validation set only
   - Implement stricter feedback validation

3. **Long-term**:
   - Implement explicit human labeling for critical feedback
   - Separate production and training data pipelines
   - Automated monitoring of training data quality

## Key Metrics

### Monitoring

```yaml
FeedbackLoopHealth:
  - name: model_accuracy_trend
    description: "7-day rolling accuracy; alert if degrading"
    threshold: {
      warning: "slope < -0.01",
      critical: "slope < -0.03"
    }
  
  - name: accuracy_divergence
    description: "Difference between held-out accuracy and production accuracy"
    threshold: {
      warning: "> 0.05",
      critical: "> 0.10"
    }
  
  - name: feedback_agreement_rate
    description: "% of feedback that matches human labels"
    threshold: {
      warning: "< 0.80",
      critical: "< 0.70"
    }
  
  - name: new_model_regression
    description: "New model accuracy vs. old model on clean test set"
    threshold: {
      warning: "< 0.98x",
      critical: "< 0.95x"
    }
```

## References

- Perdomo et al. (2020): "Performative prediction"
- Sculley et al. (2015): "Hidden Technical Debt in Machine Learning Systems"
- Selbst & Barocas (2018): "The intuitive appeal and elusive promise of algorithmic fairness"

## See Also

- [Feature Distribution Shift](../feature-distribution-shift/)
- [Model Drift Detection](../model-drift-detection/)
- [Retraining Degradation](../retraining-degradation/)
