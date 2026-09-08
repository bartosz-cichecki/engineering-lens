# Shared Git boundary rules

Use these rules whenever a workflow selects, saves, or reconstructs Git scope.

## Resolve safely

1. Verify the selected directory is inside a Git worktree and record its canonical repository root.
2. Resolve each commit boundary locally as a commit object and retain its full object-format SHA (40 characters for SHA-1, 64 for SHA-256). Preserve the user's entered ref only as context.
3. Use frozen SHAs after resolution, never moving aliases such as `HEAD` or branch names.
4. Record merge bases, parents, empty-tree markers, path filters, history modes, and included untracked paths required to reproduce the scope.
5. If a ref is missing, ambiguous, not a commit, or locally unavailable, stop. Never fetch, guess, substitute, or broaden.
6. If required ancestry is absent, explain the ambiguity and request new boundaries.

The Git empty tree is a tree object, not a commit. Label it `Empty tree — repository has no commits yet` or the selected-language equivalent; never present it as a commit SHA.

## Standard change scopes

### Uncommitted

When `HEAD` exists, freeze its full SHA as the baseline. In an unborn repository, use the empty tree marker. Keep staged changes relative to the baseline, unstaged changes relative to the index, and relevant untracked files distinct. Respect standard Git exclude rules and never include ignored files.

Include an untracked file only when it contributes to the declared goal, selected behavior, tests, configuration, documentation, or delivery story. Explicitly exclude the active workflow's own `.engineering-lens/` state file. Record included and excluded untracked paths with reasons when the workflow contract requires it.

For `change-review-context` and `change-review`, use the [review snapshot helper](review-snapshot.md) for creation and verification. It owns the algorithm and serialization; never choose, describe into existence, or reimplement a fingerprint in model-generated commands. Preserve the saved untracked classification; inventory drift requires fresh context.

Other workflows retain their existing snapshot contracts: freeze baseline, staged and unstaged content, and ordered relevant untracked paths and contents with a deterministic cryptographic fingerprint. A status summary is insufficient. Recompute under the same rules for drift checks and stop on mismatch.

### Last or specific commit

Freeze the target commit and its exact parent as baseline. For a root commit, use the empty tree. For a merge commit, list the parents and ask which parent defines the comparison; never assume first-parent semantics.

### Branch compared with a base

Freeze the locally resolved base SHA, current target SHA, and their merge-base SHA. Use the merge base as the effective diff baseline. A later branch movement does not change the frozen boundary.

### Pull request

Use an already configured read-only repository-host tool only when available. Otherwise ask for locally resolvable base and head refs. Freeze the pull request identifier, base ref when known, merge base, and exact target SHA. Never install a tool, publish a comment, or fetch refs.

### Custom range

Freeze the start commit as baseline and the end commit as target. A commit-by-commit development path requires the start to be an ancestor of the end and covers commits after the start through the end.

## Repository assessment scopes

Freeze two axes independently:

- the code snapshot to evaluate: a commit, a frozen uncommitted snapshot, or another exact locally available commit boundary;
- the history slice to analyze: none, full history through a frozen target, a frozen range, a selected commit, a date window resolved to a frozen commit set, or the last N commits resolved to a frozen commit set.

Record path filters and exclusions separately. For history modes that are not fully described by two boundary SHAs, save the ordered full SHA set or a deterministic SHA-set fingerprint plus the exact selection rule, count, and frozen endpoints. A consuming assessment must reproduce the saved set and stop if it cannot.

## Read file states

Read target versions from the frozen boundary, not from a moving working tree. Read deleted files from the exact baseline. For uncommitted paths, distinguish baseline, index, and working-tree versions. Qualify ambiguous citations with `[baseline <sha>]`, `[index]`, `[working tree]`, or `[empty-tree addition]`.
