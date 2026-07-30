# Change review context workflow

Collect intent, work stage, and an exact Git boundary for a later readiness review. Do not review the change.

## 1. Ask for language first

Your first action must be to ask exactly:

```text
Choose language / Wybierz język:

1. Polski
2. English
```

Stop and wait. Do not inspect the repository or ask another workflow question first. After selection, read completely:

- [shared operating rules](../../../references/operating-rules.md)
- [shared Git boundary rules](../../../references/git-boundaries.md)

Use the selected language for every later question and natural-language context value.

## 2. Collect scope and work stage

Ask the user to select exactly one scope:

1. Uncommitted changes: staged, unstaged, and relevant untracked files.
2. Last commit: the exact commit currently at `HEAD`.
3. Current branch compared with a base branch.
4. Pull request.

Localize the choices, ask for only the base ref or pull request identifier required by the selection, and wait after each choice.

Ask for exactly one work stage:

- `WIP`
- `Pre-commit`
- `Pre-merge`

## 3. Resolve the exact boundary

Apply the shared Git boundary rules with read-only tools. Record the canonical repository root.

- `uncommitted`: freeze the current full `HEAD` SHA or empty-tree marker. Defer final relevant-untracked selection and fingerprinting until the goal is known.
- `last-commit`: freeze `HEAD` as target and its selected parent or empty tree as baseline. If it is a merge, ask which parent defines the review.
- `branch`: freeze the entered base ref, resolved base SHA, merge-base SHA, and current `HEAD` target SHA.
- `pull-request`: use an already configured read-only host tool if available; otherwise ask for locally resolvable base and head refs. Freeze the identifier, base ref when known, resolved base SHA, merge base, and target SHA.

If any boundary is unavailable locally, stop and request a resolvable value. Do not review code while resolving it.

## 4. Collect intent

Inspect only the frozen change summary and path list needed to ask short, specific questions. Collect:

- the outcome and reason for the change;
- intentional exclusions;
- observable completion criteria;
- external risks or constraints that repository evidence may not reveal.

Ask in small batches and confirm ambiguous answers. Describe intent as outcomes, not a repetition of diff mechanics.

For uncommitted scope, now classify untracked paths against the declared goal. Show included relevant paths and excluded paths with short reasons, and ask for confirmation. Always exclude `.engineering-lens/change-review-context.md` from evaluated scope. After confirmation, calculate the required deterministic fingerprint across baseline, staged content, unstaged content, and included relevant untracked content.

## 5. Save only the context file

Create `.engineering-lens/` if needed and create or replace only `.engineering-lens/change-review-context.md`. Do not modify another path. Use this schema and write `Not applicable` for inapplicable stable fields:

```markdown
# Change Review Context

- Format version: 1
- Language: English | Polish
- Review stage: WIP | Pre-commit | Pre-merge
- Repository root: <canonical absolute path>
- Scope mode: uncommitted | last-commit | branch | pull-request
- Baseline kind: commit | empty-tree
- Baseline commit: <full SHA or Not applicable>
- Target commit: <full SHA or Not applicable>
- Base ref: <entered ref or Not applicable>
- Base ref commit: <full SHA or Not applicable>
- Merge-base commit: <full SHA or Not applicable>
- Pull request: <identifier or Not applicable>
- Snapshot fingerprint algorithm: <algorithm or Not applicable>
- Snapshot fingerprint: <value or Not applicable>

## Scope paths

### Staged

- <path or None>

### Unstaged

- <path or None>

### Included relevant untracked

- <path or None>

### Excluded untracked

- <path — reason or None>

## Goal

<what should change and why>

## Intentionally excluded

<explicit exclusions or None declared>

## Completion criteria

- <observable criterion>

## Risks and external constraints

- <risk or constraint, or None declared>
```

For committed modes, keep the path subsections but use `None`; the consuming review reconstructs paths from the frozen commits. Use full 40-character SHAs.

After writing, tell the user that the context is ready and that the explicitly invoked `change-review` skill will use its saved language, stage, intent, and exact scope.

## Boundaries

- Do not assess correctness, report findings, or issue a verdict.
- Do not modify evaluated code or the Git worktree except for the declared context file.
- Do not publish pull request comments or add any tool, integration, or dependency.
