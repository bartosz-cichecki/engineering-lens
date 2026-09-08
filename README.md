# Engineering Lens

Engineering Lens provides context and scope control for AI engineering reviews in Codex and Claude Code. `change-review-context` saves the contract — Goal / Excluded / DONE / Risks — and freezes an exact Git snapshot; `change-review` evaluates that snapshot against the contract and the selected work stage. Code creates and verifies the snapshot, while the host model performs the review. The value is a controlled review context and scope, not a proprietary or “better” code-review model.

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

For direct skill use, a caller can pass a complete Task Contract to Claude Code after the `--automation` selector. This mode is fixed to uncommitted scope and the `Pre-commit` stage, asks no questions, and writes the same format-version-1 context consumed by the existing `change-review` skill:

```bash
{
  printf '%s\n\n' '/engineering-lens:change-review-context --automation'
  cat task-contract.md
} | claude -p --permission-mode auto --no-session-persistence
```

The Task Contract must establish the goal and reason, a scope boundary (intentional exclusions, an explicit declaration of none, or a clearly bounded scope), and observable completion criteria. Risks and external constraints are optional; omitting them needs no `Risks: none` declaration and does not cause `TASK_CONTRACT_INCOMPLETE`. Explicit risks and constraints are preserved, while unclear or contradictory supplied constraints still cause rejection. Its unambiguous Polish or English prose selects the saved language. If any required value or untracked-file classification is unsafe to derive, the command reports an error and leaves any existing `.engineering-lens/change-review-context.md` unchanged.

## Validated automation for orchestrators

Use the runner from this plugin checkout (set `ENGINEERING_LENS_ROOT` to its absolute location), with the target repository as the working directory:

```bash
python3 "$ENGINEERING_LENS_ROOT/scripts/automation.py" change-review-context --automation < task-contract.md > /tmp/context-result.json
python3 "$ENGINEERING_LENS_ROOT/scripts/automation.py" change-review > /tmp/review-result.json
```

Keep result files outside the evaluated worktree so they do not change its fingerprint. Run review only after context exit 0. Stdout is exactly one validated versioned JSON object; stderr retains the human report. Exit codes are 0 (completed), 2 (semantic rejection), 3 (invalid automation result), and 4 (Claude/CLI failure). A completed review can have any of the three verdicts, so read `verdict` rather than assuming exit 0 means readiness. The runner does not retry or use another LLM to interpret/repair output.

See the [automation result contract](references/automation-result.md) for fields, reason codes, Task Contract element states, secret exclusion, the Claude CLI capability decision, and failure handling. The direct invocation above alone is not the validated orchestrator interface.

## Validate locally

```bash
bash scripts/validate.sh
claude plugin validate --strict .
```
