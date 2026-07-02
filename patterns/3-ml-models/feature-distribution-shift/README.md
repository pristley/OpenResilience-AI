# Pattern: Feature Distribution Shift & Covariate Drift

> Input feature distributions change; model trained on stale data encounters unseen patterns and predicts poorly.

## Quick Summary

**Problem**: Feature distributions shift silently; model accuracy degrades without triggering explicit errors  
**Impact**: Silent accuracy drop (92% → 85%), wrong decisions, unfair predictions  
**Detection Time**: Days to weeks (depends on monitoring cadence)  
**Solution**: Drift monitoring, automatic retraining, subgroup performance tracking

---

## Problem Statement

Production data changes over time. Customer behavior evolves, markets shift, seasons change, policies change. Models trained on historical data encounter distributions they've never seen:

- **E-commerce**: Summer model sees winter purchases; different products, price ranges, user segments
- **Lending**: Pre-recession model sees recession borrowers; income, employment, spending behavior different
- **Healthcare**: Winter model sees spring patients; different disease prevalence, patient demographics
- **Recommendations**: Young user base model meets aging user base; content preferences, engagement patterns change

## Why It Matters

- **Silent Failure**: No errors thrown, just quiet degradation
- **Business Impact**: 5-10% accuracy drop = millions in revenue loss
- **Unfairness**: Drift often affects subgroups differently (e.g., new vs. old customers)
- **Regulatory**: If drift causes discrimination, compliance liability
- **Detection Latency**: Requires monitoring; often takes weeks to notice

## How It Fails

### Failure Mode

1. **Covariate Shift**: Input distribution changes, output relationship unchanged
   - Example: Loan applications shift from urban to rural (different income, education distributions)
   - Model was trained on 60% urban; now receives 80% rural

2. **Prior Shift**: Output distribution changes, input relationship unchanged
   - Example: Product popularity shifts (summer items vs. winter items)

3. **Concept Drift**: Relationship between input and output changes
   - Example: What "good customer" means changes (budget conscious vs. high-spend)

4. **Gradual vs. Sudden**:
   - Gradual: Seasonal shifts, slow behavior evolution
   - Sudden: Policy change, market shock, new user cohort

### Observable Signals

- Accuracy on recent validation set drops below threshold
- Confusion matrix changes shape (some classes affected more)
- Feature distributions shift (mean/variance/quantiles change)
- Prediction confidence stays high despite lower accuracy (calibration loss)

### Detection Time

- **Statistical test**: Minutes (drift detection test)
- **Performance degradation**: Days to weeks (requires enough data)
- **Business impact**: Weeks to months (depends on revenue impact)

### Blast Radius

- **Partial**: Specific segments affected (e.g., new users)
- **System-wide**: All predictions degraded
- **Cascade**: Wrong predictions feed back into training data

## Resilience Strategy

### Prevention

1. **Data Governance**:
   - Document expected feature distributions
   - Establish SLA for feature staleness
   - Monitor data quality upstream

2. **Model Design**:
   - Simple, interpretable models more robust to drift
   - Feature engineering resistant to known shifts
   - Ensemble models reduce single-model drift impact

### Detection

1. **Statistical Drift Tests**:
   ```python
   from scipy.stats import ks_2samp
   
   # Kolmogorov-Smirnov test: compare training vs. production distributions
   statistic, pvalue = ks_2samp(train_feature, prod_feature)
   if pvalue < 0.05:  # Significant drift detected
       alert(f"Feature {name} drifted significantly")
   ```

2. **Performance Monitoring**:
   ```python
   # Track accuracy on holdout validation set over time
   accuracy_trend = [acc_week1, acc_week2, acc_week3, ...]
   if trend_slope < -0.01:  # Significant downward trend
       alert("Model accuracy degrading")
   ```

3. **Subgroup Performance**:
   ```python
   # Track accuracy per segment (new vs. old customers)
   new_customer_accuracy = 0.92
   old_customer_accuracy = 0.88  # Divergence indicates drift
   if abs(new_customer_accuracy - old_customer_accuracy) > 0.05:
       alert("Subgroup performance divergence detected")
   ```

### Recovery

1. **Immediate**:
   - Lower prediction confidence
   - Route uncertain predictions to human review
   - Increase model retraining frequency

2. **Short-term**:
   - Retrain model on recent data
   - Deploy new model with A/B testing
   - Investigate root cause of shift

3. **Long-term**:
   - Implement automated retraining pipeline
   - Establish drift monitoring dashboard
   - Update model serving strategy (online learning vs. batch retraining)

## Key Metrics

### Monitoring

```yaml
DistributionShift:
  - name: feature_drift_score
    description: "Wasserstein distance between training and production distributions"
    threshold: {
      warning: "> 0.5",
      critical: "> 1.0"
    }
  
  - name: model_accuracy_trend
    description: "7-day rolling average accuracy; alert if trending down"
    threshold: {
      warning: "slope < -0.01",
      critical: "slope < -0.05"
    }
  
  - name: subgroup_accuracy_divergence
    description: "Max difference in accuracy across subgroups"
    threshold: {
      warning: "> 0.05",
      critical: "> 0.10"
    }
  
  - name: prediction_calibration_error
    description: "Expected calibration error (ECE)"
    threshold: {
      warning: "> 0.1",
      critical: "> 0.2"
    }
```

## References

- Sugiyama et al. (2012): "Dataset Shift in Machine Learning"
- Quinonero-Candela et al. (2009): "Dataset Shift in Classification"
- Moreno-Torres et al. (2012): "A unifying view on dataset bias in classification"

## See Also

- [Model Drift Detection](../model-drift-detection/)
- [Feedback Loop Collapse](../feedback-loop-collapse/)
- [Inference Latency Spike](../inference-latency-spike/)
