# Pattern: Feedback Loop Collapse & Training Data Poisoning

> Model predictions stored as "ground truth" for retraining; errors corrupt training data and cascade.

## Quick Summary

**Problem**: Model errors stored as training labels; feedback loop compounds errors across retraining cycles  
**Impact**: Model quality degrades exponentially; poisoned data requires manual cleanup  
**Detection Time**: Weeks (takes 3-5 cycles to notice degradation trend)  
**Solution**: Validation before using feedback, separate training/production pipelines, held-out validation set

---

**Detailed Pattern**: See [CONTRIBUTING.md](../../../CONTRIBUTING.md) for full documentation including feedback validation, data poisoning detection, recovery strategies, and long-term resilience patterns.
