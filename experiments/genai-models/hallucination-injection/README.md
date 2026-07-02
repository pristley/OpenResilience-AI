# Hallucination Injection Experiment

This directory contains chaos experiments for testing LLM hallucination detection and graceful degradation strategies.

## Files

- **hallucination_experiment.py** - Main experiment script with HallucinationInjector class and multiple test scenarios

## Running the Experiments

### Basic Usage

```bash
# Run full scenario (recommended for demonstration)
python hallucination_experiment.py

# Run specific injection mode
python hallucination_experiment.py --mode inject --scenario date_hallucination
python hallucination_experiment.py --mode inject --scenario number_hallucination
python hallucination_experiment.py --mode inject --scenario entity_hallucination

# Test detection
python hallucination_experiment.py --mode detect

# Test graceful degradation
python hallucination_experiment.py --mode graceful_degrade
```

## Scenarios

1. **Date Hallucination** - Tests incorrect date injection and detection
2. **Number Hallucination** - Tests incorrect numeric value injection
3. **Entity Hallucination** - Tests incorrect name/organization substitution
4. **Graceful Degradation** - Tests fallback strategies when hallucinations detected

## Key Metrics

- Detection rate (percentage of hallucinations caught)
- Average detection time (milliseconds)
- Confidence scores (0.0-1.0)
- Severity distribution (low, medium, high, critical)

## External Dependencies

The experiment can integrate with:
- External fact-checking APIs (via POST to http://localhost:8000/validate)
- Great Expectations validation framework
- Anthropic/Claude API (for production LLM calls)

## See Also

- [Hallucination Injection Recovery Pattern](../../patterns/3-ml-models/hallucination-injection-recovery/)
- [LLM Hallucination Test](../llm-hallucination-test/)
