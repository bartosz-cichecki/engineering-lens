# Engineering Lens

Cross-platform engineering workflows for explaining changes, reviewing change readiness, and assessing repositories in Codex and Claude Code.

## Skills

- `change-walkthrough` explains one functional group of a frozen Git change at a time for a selected audience.
- `change-review-context` saves the exact scope, stage, goal, exclusions, completion criteria, and external constraints for a later review.
- `change-review` reviews only the saved change boundary and finishes with one stage-aware readiness verdict.
- `repo-assessment-context` saves the repository purpose, users, constraints, risk, maturity expectations, and exact code and history scope.
- `repo-assessment` writes an evidence-based fit-for-purpose assessment from the saved repository context.

## Install in Codex

Add the GitHub marketplace and install the plugin; cloning is not required:

```bash
codex plugin marketplace add bartosz-cichecki/engineering-lens
codex plugin add engineering-lens@engineering-lens-tools
```

Start a new Codex session after installation.

## Install in Claude Code

Run these commands in a Claude Code session; cloning is not required:

```text
/plugin marketplace add bartosz-cichecki/engineering-lens
/plugin install engineering-lens@engineering-lens-tools
/reload-plugins
```

## Invoke explicitly

Codex:

```text
$engineering-lens:change-walkthrough
$engineering-lens:change-review-context
$engineering-lens:change-review
$engineering-lens:repo-assessment-context
$engineering-lens:repo-assessment
```

Claude Code:

```text
/engineering-lens:change-walkthrough
/engineering-lens:change-review-context
/engineering-lens:change-review
/engineering-lens:repo-assessment-context
/engineering-lens:repo-assessment
```

## Validate locally

```bash
bash scripts/validate.sh
claude plugin validate --strict .
```
