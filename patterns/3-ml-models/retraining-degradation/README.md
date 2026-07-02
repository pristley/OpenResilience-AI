# Pattern: Retraining Degradation & Model Update Failures

> New model version performs worse than previous; deploying worse model.

## Quick Summary

**Problem**: Retrained model has degraded accuracy (data corruption, hyperparameter error, data leakage)  
**Impact**: Deploying worse model hurts system performance; requires rollback  
**Detection Time**: Seconds (if pre-deployment validation) to minutes (if caught in canary)  
**Solution**: Comprehensive pre-deployment testing, canary deployment, automated rollback

---

**Detailed Pattern**: See [CONTRIBUTING.md](../../../CONTRIBUTING.md) for full documentation including validation strategies, canary deployment, automated rollback procedures, and chaos testing.
