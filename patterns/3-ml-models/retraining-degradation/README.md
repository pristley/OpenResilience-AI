# Pattern: Retraining Degradation & Model Update Failures

> New model version performs worse than previous; deploying degraded model creates silent failures.

## Quick Summary

**Problem**: Retrained model validates well but fails in production (worse than previous model)  
**Impact**: 3% engagement drop, revenue loss, user experience degradation  
**Detection Time**: Seconds (pre-deployment) to minutes (canary deployment)  
**Solution**: Pre-deployment testing, canary deployment, automated rollback

---

## Problem Statement

Retraining introduces new risks:

1. **Training Data Contamination**: Bad data slipped into training set
   - Example: Competitor data mixed with real customer data
   - Result: New model learns wrong patterns

2. **Hyperparameter Regression**: New hyperparameters worse than previous
   - Example: Learning rate too high; model didn't converge
   - Result: New model underfits

3. **Data Leakage**: Training set includes labels from test set
   - Example: Test data accidentally included in training
   - Result: Artificially high training accuracy; poor production performance

4. **Insufficient Training Data**: Recent data too small/biased
   - Example: Retrain on last 1 week instead of last 3 months
   - Result: Model overfits to weekly patterns

5. **Feature Changes**: Feature engineering changed between versions
   - Example: New features added; old features removed
   - Result: Performance measured on different feature space

## Why It Matters

- **Silent Failure**: Model may validate well but fail in production
- **User Impact**: Visible performance degradation damages trust
- **Revenue**: Wrong predictions → user abandonment → revenue loss
- **Rapid Detection Critical**: Need to detect within minutes, not hours
- **Automated Recovery**: Must have automated rollback mechanism

## How It Fails

### Failure Mode

1. **Training-Production Mismatch**:
   - Validation set not representative of production
   - Example: Test on balanced data; production imbalanced
   - Result: Model optimizes for wrong metric

2. **Hyperparameter Tuning Failure**:
   - Search space too large; didn't find good parameters
   - Example: Grid search didn't test learning rate 0.01 (the best one)
   - Result: Worse model deployed

3. **Feature Skew**:
   - Features computed differently in training vs. production
   - Example: Training used cache; production recomputed (different values)
   - Result: Model encounters unexpected feature values

### Observable Signals

- Pre-deployment test accuracy looks good; production fails
- Engagement metrics drop immediately after deployment
- Specific prediction types regress (e.g., edge cases)
- Error rate increases after model update

### Detection Time

- **Pre-deployment test**: Seconds to minutes
- **Canary deployment**: Minutes to hours
- **Production impact**: Hours to days (if canary not used)

### Blast Radius

- **Partial**: Specific predictions affected (edge cases)
- **System-wide**: All predictions degraded
- **Cascade**: Impacts downstream systems

## Resilience Strategy

### Prevention

1. **Pre-deployment Validation**:
   ```python
   # Before deploying new model, validate it's better
   new_model_acc = evaluate(new_model, held_out_test_set)
   old_model_acc = evaluate(old_model, held_out_test_set)
   
   # Require at least 99% of old model performance
   if new_model_acc < old_model_acc * 0.99:
       alert("New model worse than previous!")
       require_manual_review()
   ```

2. **Data Validation**:
   ```python
   # Verify training data hasn't been corrupted
   from great_expectations import dataset
   
   context = ge.get_context()
   batch = context.get_batch(
       datasource_name="training_data",
       data_connector_name="default"
   )
   
   # Run expectations
   batch.expect_table_columns_to_match_ordered_list([
       'feature_1', 'feature_2', 'target'
   ])
   batch.expect_column_values_to_be_in_type_list(
       column='target',
       type_list=['int']
   )
   ```

3. **Feature Validation**:
   ```python
   # Verify features match production schema
   training_features = set(training_data.columns)
   production_features = set(production_data.columns)
   
   if training_features != production_features:
       alert("Feature mismatch between training and production!")
   ```

### Detection

1. **Pre-deployment Testing**:
   ```python
   # Compare new model vs. old model
   def validate_model_deployment(new_model, old_model, test_set):
       new_acc = evaluate(new_model, test_set)
       old_acc = evaluate(old_model, test_set)
       
       # Accept only if better by at least 0.1%
       if new_acc > old_acc * 1.001:
           return True, "New model is better"
       else:
           return False, f"New model worse: {new_acc:.3f} vs {old_acc:.3f}"
   ```

2. **Canary Deployment**:
   ```python
   # Route 5% of traffic to new model
   if traffic_sample < 0.05:
       use_model = new_model
   else:
       use_model = old_model
   
   # Monitor canary metrics
   canary_accuracy = evaluate_canary_traffic()
   if canary_accuracy < old_model_accuracy * 0.98:  # 2% worse
       alert("Canary degradation detected")
       rollback()
   ```

3. **Automated Rollback**:
   ```python
   # If production accuracy drops, rollback automatically
   current_accuracy = get_production_accuracy()
   previous_accuracy = get_previous_model_accuracy()
   
   if current_accuracy < previous_accuracy * 0.95:  # 5% drop
       alert("Production accuracy degraded significantly")
       deploy_previous_model()  # Automatic rollback
   ```

### Recovery

1. **Immediate**:
   - Trigger automated rollback to previous model
   - Alert on-call team
   - Log incident details

2. **Short-term**:
   - Investigate root cause
   - Analyze differences between models
   - Retrain with corrections

3. **Long-term**:
   - Strengthen pre-deployment validation
   - Implement comprehensive testing suite
   - Improve data quality monitoring

## Key Metrics

### Monitoring

```yaml
RetrainingQuality:
  - name: model_accuracy_comparison
    description: "New model accuracy vs. old model on held-out set"
    threshold: {
      warning: "< 0.99x old_model",
      critical: "< 0.95x old_model"
    }
  
  - name: canary_accuracy
    description: "Accuracy on canary traffic (5% sample)"
    threshold: {
      warning: "< baseline - 0.02",
      critical: "< baseline - 0.05"
    }
  
  - name: training_data_size
    description: "Size of training dataset"
    threshold: {
      warning: "< 30 days",
      critical: "< 7 days"
    }
  
  - name: feature_stability
    description: "Feature value ranges match previous model"
    threshold: {
      critical: "significant_divergence"
    }
```

## References

- Sculley et al. (2015): "Hidden Technical Debt in Machine Learning Systems"
- Polyzotis et al. (2019): "Data Validation for Machine Learning"
- Google Cloud: "Testing and deploying ML models in production"

## See Also

- [Model Drift Detection](../model-drift-detection/)
- [Feedback Loop Collapse](../feedback-loop-collapse/)
- [Inference Latency Spike](../inference-latency-spike/)
