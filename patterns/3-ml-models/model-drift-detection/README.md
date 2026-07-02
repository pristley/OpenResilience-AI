# Pattern: Model Drift Detection & Performance Monitoring

> Model performance degrades gradually as underlying data relationships change; concept drift detection required.

## Quick Summary

**Problem**: Model accuracy gradually degrades (92% → 89% → 85%) as data relationships shift  
**Impact**: Silent performance degradation, wrong decisions, business metric impact ($2M+ revenue loss)  
**Detection Time**: Weeks to months (requires automated monitoring)  
**Solution**: Performance monitoring, automated retraining, online learning

---

## Problem Statement

Unlike data distribution shift, concept drift represents a fundamental change in the relationship between features and target:

- **Churn prediction**: Pre-recession behavior patterns ≠ recession behavior patterns
- **Fraud detection**: What looks like fraud changes as attackers adapt
- **Disease diagnosis**: New disease variants show different symptom patterns
- **Market prediction**: Market dynamics change (bull market vs. bear market)
- **Customer lifetime value**: Economic conditions change customer behavior

## Why It Matters

- **Silent Failure**: No data errors; system operates normally, just predicts wrongly
- **Exponential Impact**: Small accuracy drop (3%) compounds to large business impact
- **Detection Lag**: Takes weeks/months of monitoring to detect and quantify
- **Regulatory**: Model performance degradation may trigger compliance violations
- **Recovery Time**: Retraining alone won't fix if root cause is business change

## How It Fails

### Failure Mode

1. **Gradual Drift**: Slow, continuous change
   - Example: Customer preferences shift seasonally
   - Detection: Requires trend analysis over weeks

2. **Sudden Drift**: Abrupt change in data relationships
   - Example: Market shock, policy change
   - Detection: Can alert in days if monitoring

3. **Virtual Drift**: Features unchanged, labels change (e.g., fraud definition changes)
   - Example: "Fraud" definition evolves as attackers adapt

### Observable Signals

- Accuracy declining on holdout validation set
- Confusion matrix changing shape (some classes affected more)
- Feature importance changing
- Model predictions become miscalibrated (high confidence, wrong answers)

### Detection Time

- **Statistical test**: Days (if test set large enough)
- **Performance degradation**: Weeks (requires sufficient data)
- **Root cause identification**: Weeks to months

### Blast Radius

- **Partial**: Specific segments affected
- **System-wide**: All predictions degraded
- **Cascade**: Impacts downstream systems relying on predictions

## Resilience Strategy

### Prevention

1. **Model Design**:
   - Simple models more robust to drift
   - Feature engineering tied to business logic (more stable)
   - Ensemble models reduce single-model drift impact

2. **Monitoring Infrastructure**:
   - Establish baseline performance expectations
   - Create holdout validation set for long-term testing
   - Document expected data relationships

### Detection

1. **Holdout Validation Monitoring**:
   ```python
   # Maintain separate labeled dataset (e.g., 10K samples)
   # Never use for training; only for monitoring
   held_out_accuracy = evaluate(model, held_out_set)
   
   if held_out_accuracy < baseline_accuracy - 0.03:  # 3% drop
       alert("Model accuracy degrading")
   ```

2. **Performance Trend Analysis**:
   ```python
   # Track weekly accuracy
   accuracy_trend = [0.92, 0.915, 0.91, 0.905, 0.90]  # Downtrend
   slope = linear_regression_slope(accuracy_trend)
   
   if slope < -0.002:  # Significant downtrend
       alert("Sustained accuracy degradation detected")
   ```

3. **Subgroup Performance Monitoring**:
   ```python
   # Track accuracy by segment
   for segment in segments:
       segment_accuracy = evaluate(model, segment_test_set)
       if segment_accuracy < threshold:
           alert(f"Accuracy degrading in segment: {segment}")
   ```

### Recovery

1. **Immediate**:
   - Investigate root cause (data change? model bug?)
   - Assess impact (how many users affected?)
   - Decide: retrain vs. adjust vs. use ensemble

2. **Short-term**:
   - Retrain model on recent data
   - Deploy with canary testing
   - Establish more frequent retraining schedule

3. **Long-term**:
   - Implement automated retraining pipeline
   - Create comprehensive performance dashboard
   - Consider online learning for continuous adaptation

## Key Metrics

### Monitoring

```yaml
ConceptDrift:
  - name: model_accuracy_on_holdout
    description: "Accuracy on fixed holdout validation set"
    threshold: {
      warning: "< baseline - 0.02",
      critical: "< baseline - 0.05"
    }
  
  - name: accuracy_trend_slope
    description: "Weekly accuracy trend (linear regression slope)"
    threshold: {
      warning: "slope < -0.001",
      critical: "slope < -0.005"
    }
  
  - name: subgroup_accuracy_divergence
    description: "Max difference in accuracy across subgroups"
    threshold: {
      warning: "> 0.05",
      critical: "> 0.10"
    }
  
  - name: prediction_calibration_error
    description: "Expected Calibration Error (ECE)"
    threshold: {
      warning: "> 0.1",
      critical: "> 0.2"
    }
```

## References

- Gama et al. (2014): "A Survey on Concept Drift Adaptation"
- Minku et al. (2013): "On the Impact of Imbalanced Data in Stream Learning"
- Bifet et al. (2015): "Adaptive Stream Mining at Scale with Approximate Sketch"

## See Also

- [Feature Distribution Shift](../feature-distribution-shift/)
- [Feedback Loop Collapse](../feedback-loop-collapse/)
- [Retraining Degradation](../retraining-degradation/)

---

This is a placeholder. See [data-quality-degradation](../../2-data-pipelines/data-quality-degradation/) pattern for related content.

**Contributing**: Want to fill this out? Follow [CONTRIBUTING.md](../../CONTRIBUTING.md).
