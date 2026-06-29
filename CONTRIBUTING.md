# Contributing to Resilience Patterns

Thank you for contributing! This guide explains how to submit patterns, experiments, runbooks, and case studies.

## Pattern Submission Guidelines

Each pattern should follow this structure:

```
patterns/[category]/[pattern-name]/
├── README.md              # Main pattern documentation
├── chaos-experiment/      # Optional: executable chaos test
│   └── run.py
├── monitoring/            # Optional: observability setup
│   └── prometheus-alerts.yaml
└── references/            # Optional: links to papers, articles
    └── LINKS.md
```

### Pattern Template

Use [templates/pattern-template.md](templates/pattern-template.md) as your starting point.

**Requirements:**
- [ ] Problem statement (what goes wrong?)
- [ ] Why it matters (business impact)
- [ ] How it fails (mechanism, signals, blast radius)
- [ ] Resilience strategy (prevention, detection, recovery)
- [ ] Chaos experiment code (if applicable)
- [ ] References (papers, tools, real incidents)

## Experiment Submission Guidelines

Experiments should be:
- **Safe**: Include `--dry-run` flag by default
- **Documented**: Clear setup instructions
- **Reproducible**: Work in sandboxed environments
- **Observable**: Output metrics and logs

Place experiments in: `experiments/[system-type]/[experiment-name]/`

## Runbook Submission Guidelines

Runbooks are incident response playbooks.

Format:
- **Symptoms**: What alerts fire?
- **Triage**: How to verify the problem
- **Mitigation**: Immediate steps to reduce blast radius
- **Recovery**: How to restore normal operation
- **Post-mortem**: What to investigate afterward

Place runbooks in: `runbooks/[incident-type]/README.md`

## Case Study Submission Guidelines

Real incidents (anonymized) are gold for learning.

Include:
- **Timeline**: When did things break?
- **Root cause**: What actually failed?
- **Detection time**: How long to notice?
- **Impact**: Users/systems affected
- **Fix**: What did you do?
- **Prevention**: How to avoid next time?

Place case studies in: `case-studies/[YYYY-MM-DD-incident-name].md`

## Pull Request Process

1. **Fork and branch**: Create feature branch from `main`
2. **Add your content**: Pattern, experiment, or runbook
3. **Test links**: Ensure all references are valid
4. **Submit PR**: Include description of what you're adding
5. **Review**: We'll provide feedback within 1 week
6. **Merge**: Once approved!

## Code Style

- **Python**: Follow PEP 8; use type hints where possible
- **YAML**: 2-space indentation
- **Markdown**: Consistent heading hierarchy

## Questions?

Open an issue or start a discussion. We're here to help!
