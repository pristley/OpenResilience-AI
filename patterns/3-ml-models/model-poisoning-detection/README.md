# Pattern: Model Poisoning Detection & Integrity Verification

> Model weights compromised, corrupted, or malicious; produces systematically wrong predictions.

## Quick Summary

**Problem**: Model weights modified (attack/corruption); produces adversarially wrong predictions  
**Impact**: Trust violation, security breach, fraudulent transactions ($500K+ before detection)  
**Detection Time**: Milliseconds (checksum) to days (audit)  
**Solution**: Model signing, checksum verification, secure supply chain, pre-deployment testing

---

## Problem Statement

Model weights can be compromised through:

1. **Supply Chain Attack**: Typosquatted package name, malicious model repository
   - Example: `tensorflow-ml` instead of `tensorflow`
   - Download contains backdoored model

2. **Insider Threat**: Employee uploads malicious model weights
   - Example: Fraud detection model modified to approve fraudulent transactions
   - Impact: Millions of dollars in fraud before detection

3. **Hardware Corruption**: Model weights corrupted on disk/network
   - Example: Bit flip in model weights causes systematic misclassification
   - Impact: Silent accuracy degradation

4. **Infrastructure Compromise**: Attacker gains access to model repository
   - Example: Model weights replaced with modified version
   - Impact: Widespread system compromise

## Why It Matters

- **Trust Violation**: If model poisoned, entire system compromised
- **Backdoors**: Poisoned model may work normally for 99% of inputs, fail strategically
- **Detection Latency**: May not notice corruption until cascading failures occur
- **Financial Impact**: Fraud detection poisoning → $500K+ fraudulent transactions
- **Regulatory**: If discovered, massive compliance violation

## How It Fails

### Failure Mode

1. **Backdoor Attacks**:
   - Model works correctly for normal inputs
   - Fails predictably on inputs with specific pattern
   - Example: Fraud detector accepts transactions with specific merchant ID

2. **Gradual Corruption**:
   - Model weights degraded gradually
   - Looks like concept drift, not poisoning
   - Root cause: bit corruption or subtle modification

3. **Stealth Attacks**:
   - Attack designed to evade detection
   - Only affects specific subpopulation (new users, low-value transactions)
   - Widely deployed before detection

### Observable Signals

- Model accuracy suddenly drops
- Systematic bias in wrong direction (always predicts fraud for certain merchants)
- Supply chain warnings (package not from official source)
- Model hash mismatches expected value
- Unexpected model behavior on benign inputs

### Detection Time

- **Pre-deployment checksum**: Milliseconds (automated)
- **Statistical test**: Hours (performance test suite)
- **Behavioral analysis**: Days to weeks (pattern analysis)
- **Manual audit**: Weeks to months (forensic analysis)

### Blast Radius

- **Partial**: Specific predictions or subgroups affected
- **System-wide**: All predictions compromised
- **Cascade**: Impacts downstream systems

## Resilience Strategy

### Prevention

1. **Secure Supply Chain**:
   - Download models only from official repositories
   - Verify package signatures
   - Use private model registries with access control
   - Checksum verification on download

2. **Code Signing**:
   ```python
   import hashlib
   import hmac
   
   # Sign model weights
   def sign_model(model_path, secret_key):
       with open(model_path, 'rb') as f:
           model_data = f.read()
       signature = hmac.new(
           secret_key.encode(),
           model_data,
           hashlib.sha256
       ).hexdigest()
       return signature
   
   # Verify signature before loading
   def verify_model(model_path, expected_signature, secret_key):
       computed_signature = sign_model(model_path, secret_key)
       if not hmac.compare_digest(computed_signature, expected_signature):
           raise SecurityError("Model signature verification failed!")
       return True
   ```

3. **Access Control**:
   - Restrict who can upload models
   - Require approval for production models
   - Audit all model changes
   - Version control for all model artifacts

### Detection

1. **Checksum Verification**:
   ```python
   import hashlib
   
   # Calculate model hash
   def get_model_hash(model_path):
       sha256_hash = hashlib.sha256()
       with open(model_path, 'rb') as f:
           for byte_block in iter(lambda: f.read(4096), b''):
               sha256_hash.update(byte_block)
       return sha256_hash.hexdigest()
   
   # Verify before loading
   expected_hash = "abc123def456..."
   actual_hash = get_model_hash(model_path)
   assert actual_hash == expected_hash, "Model hash mismatch!"
   ```

2. **Behavioral Testing**:
   ```python
   # Test model on known inputs
   test_cases = [
       (benign_input, benign_expected_output),
       (adversarial_input, adversarial_expected_output),
   ]
   
   for input_data, expected_output in test_cases:
       output = model.predict(input_data)
       if output != expected_output:
           alert("Model behavior unexpected; possible poisoning")
   ```

3. **Statistical Anomaly Detection**:
   ```python
   # Alert if model predictions seem wrong
   recent_accuracy = evaluate(model, recent_test_set)
   if recent_accuracy < historical_avg - 0.1:  # > 10% drop
       alert("Model accuracy dropped significantly; possible poisoning")
   ```

### Recovery

1. **Immediate**:
   - Take model offline
   - Investigate root cause
   - Determine scope of compromise

2. **Short-term**:
   - Restore model from clean backup
   - Audit all transactions since deployment
   - Retrain model if data compromise detected

3. **Long-term**:
   - Implement code signing and verification
   - Establish secure model registry
   - Regular security audits
   - Threat modeling and red-teaming

## Key Metrics

### Monitoring

```yaml
ModelIntegrity:
  - name: model_hash_verification
    description: "Model hash matches expected value"
    threshold: {
      critical: "hash_mismatch"
    }
  
  - name: signature_verification
    description: "Model signature valid"
    threshold: {
      critical: "signature_invalid"
    }
  
  - name: model_accuracy_baseline
    description: "Accuracy on known-good test set"
    threshold: {
      warning: "< baseline - 0.1",
      critical: "< baseline - 0.2"
    }
  
  - name: behavioral_test_success
    description: "All behavioral tests pass"
    threshold: {
      critical: "any_test_fails"
    }
```

## References

- Chakraborty et al. (2021): "Adversarial Machine Learning"
- NIST Cybersecurity Framework
- Software Supply Chain Security (CISA)

## See Also

- [Adversarial Input Injection](../adversarial-input-injection/)
- [Model Drift Detection](../model-drift-detection/)
- [Batch Prediction Backlog](../batch-prediction-backlog/)
