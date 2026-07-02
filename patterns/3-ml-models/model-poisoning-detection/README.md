# Pattern: Model Poisoning Detection & Integrity Verification

> Model weights compromised or corrupted; produces adversarially-wrong predictions.

## Quick Summary

**Problem**: Model weights modified/poisoned (supply chain attack, insider threat, corruption)  
**Impact**: Model produces systematically wrong predictions; trust broken  
**Detection Time**: Minutes if checksum/integrity checking in place; days/weeks without it  
**Solution**: Model signing, checksum verification, supply chain security, pre-deployment testing

---

**Detailed Pattern**: See [CONTRIBUTING.md](../../../CONTRIBUTING.md) for full documentation including integrity verification, security strategies, detection alerts, and supply chain best practices.
