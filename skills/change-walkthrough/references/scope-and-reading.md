# Walkthrough scope and reading rules

Apply the shared Git boundary rules first.

## Uncommitted changes

Capture staged, unstaged, and relevant untracked content separately. Preserve both index and working-tree versions for a path with both kinds of edits. In an unborn repository, use the empty tree as baseline and continue without requesting a synthetic commit.

Create the required content fingerprint before grouping and rediscover relevant untracked files under the same inclusion rules on every drift check. A matching status summary is insufficient.

Display the full baseline SHA or localized empty-tree marker, then a clearly labeled captured index/working-tree snapshot. List included staged, unstaged, and relevant untracked paths separately. Do not invent a target SHA for a working snapshot.

## Last or specific commit

Analyze only the exact selected commit against the chosen parent or empty tree. Exclude the working tree and later commits. When the commit is a merge, ask which parent defines the comparison and wait.

Display the exact baseline parent SHA or empty tree and the target SHA.

## Branch comparison

Record the entered base ref, its resolved SHA, the merge-base SHA, and the frozen target SHA.

- For `Final delta`, analyze only the merge-base-to-target difference and do not narrate intermediate commits.
- For `Development path`, inspect commits after the merge base through the target in chronological/topological order. Preserve meaningful decision changes, reversals, and false starts while grouping the story by functional idea.

State that the merge base is the effective start boundary.

## Custom range

Record entered refs and their full start and end SHAs.

- For `Final delta`, analyze only the direct start-to-end difference.
- For `Development path`, require start to be an ancestor of end, then inspect commits after start through end in chronological/topological order. Preserve meaningful reversals and false starts.

State that start is exclusive and end inclusive for commit-by-commit history.

## Repository context and file states

Read the complete target version of every changed hand-authored file, not just hunks. Read a deleted file from the exact baseline. For a rename, inspect both applicable paths or revisions when needed to separate movement from behavior.

For uncommitted scope, qualify ambiguous evidence with its source state. Examples include `src/Foo.java:12-18 [index]`, `src/Foo.java:20-27 [working tree]`, `src/Foo.java:8-14 [baseline abc1234...]`, and `src/Foo.java:1-20 [empty-tree addition]`.

Do not read binary files, minified files, generated sources, large lockfiles, wrapper archives, or other non-hand-authored technical artifacts in full when they contain no independently authored logic material to the change. Establish their role from metadata, manifests, source configuration, generator inputs, or authoritative build files. Keep them in the functional group they support and state the evidence limitation.

If such an artifact contains independently authored logic material to the selected change, inspect the relevant content and enough surrounding context to explain it.
