# Engineering Lens

Cross-platform engineering workflows for explaining changes, reviewing change readiness, and assessing repositories in Codex and Claude Code.

## Skills

- `change-walkthrough` explains one functional group of a frozen Git change at a time for a selected audience.
- `change-review-context` saves the exact scope, stage, goal, exclusions, completion criteria, and external constraints for a later review, either interactively or from an explicit automation Task Contract.
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

## Prepare review context non-interactively

An orchestrator can pass a complete Task Contract to Claude Code after the `--automation` selector. This mode is fixed to uncommitted scope and the `Pre-commit` stage, asks no questions, and writes the same format-version-1 context consumed by the existing `change-review` skill:

```bash
{
  printf '%s\n\n' '/engineering-lens:change-review-context --automation'
  cat task-contract.md
} | claude -p --permission-mode auto --no-session-persistence
```

The Task Contract must state the goal and reason, intentional exclusions, observable completion criteria, and risks or external constraints. Its unambiguous Polish or English prose selects the saved language. If any required value or untracked-file classification is unsafe to derive, the command reports an error and leaves any existing `.engineering-lens/change-review-context.md` unchanged.

## Validate locally

```bash
bash scripts/validate.sh
claude plugin validate --strict .
```
