# Pattern: Feature Distribution Shift & Covariate Drift

> Feature distributions change in production; model encounters unseen patterns it can't classify well.

## Quick Summary

**Problem**: Input feature distributions change over time; model trained on stale distribution  
**Impact**: Model accuracy degrades silently; predictions on OOD (out-of-distribution) data unreliable  
**Detection Time**: Days to weeks (depends on monitoring)  
**Solution**: Feature drift detection, retraining on recent data, subgroup performance monitoring

---

**Detailed Pattern**: See [CONTRIBUTING.md](../../../CONTRIBUTING.md) for full documentation including resilience strategies, detection alerts, chaos experiments, and case studies.
