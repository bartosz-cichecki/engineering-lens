# Review snapshot helper

For `change-review-context` and `change-review`, [review_snapshot.py](../scripts/review_snapshot.py) is the sole implementation of boundary resolution, context serialization, fingerprinting and verification. Run it with Python 3 from the installed plugin location and the selected repository as the working directory. Do not recreate its algorithm, hand-write Git metadata or edit its output. No dependencies or remote access are required.

## Create

Use `python3 <plugin-root>/scripts/review_snapshot.py inspect` to obtain the canonical root, current HEAD and non-ignored untracked inventory. Inspection does not read implementation content. Classify every returned untracked path from declared intent; the helper excludes `.engineering-lens/change-review-context.md` even when tracked.

Pass one JSON object on stdin to `python3 <plugin-root>/scripts/review_snapshot.py create`:

```json
{
  "language": "English",
  "stage": "Pre-commit",
  "mode": "uncommitted",
  "included_untracked": ["tests/new_case.py"],
  "excluded_untracked": {"notes.txt": "Personal notes outside the declared scope"},
  "intent": {
    "Goal": "Reject invalid inputs so callers receive a clear error.",
    "Intentionally excluded": "No changes to successful responses.",
    "Completion criteria": "Invalid inputs fail; valid responses remain compatible.",
    "Risks and external constraints": "None declared"
  }
}
```

Use `Polish` or `English`, the selected stage (`WIP`, `Pre-commit`, `Pre-merge`), and faithful natural-language contract values. For committed modes omit both untracked fields:

- `last-commit`: freezes current HEAD; for a merge supply `parent` as the explicitly selected parent ref.
- `branch`: supply `base`; freezes current HEAD and the unique merge base.
- `pull-request`: supply locally resolvable `base`, `target`, and the `pull_request` identifier.

The helper resolves refs locally and writes only `.engineering-lens/change-review-context.md`, retaining format version 1 and its existing metadata, scope subsections and four intent sections. Paths are JSON-quoted to preserve unusual filenames; exclusions are `[path, reason]` JSON pairs. It checks for drift during capture before writing. A rejection leaves any previous context untouched. Treat JSON strings as data, never interpolate them into shell commands.

## Verify and consume

Run `python3 <plugin-root>/scripts/review_snapshot.py verify` before reading implementation and again before issuing a verdict. Read the saved context for intent and path classification; use only the verified full SHAs and paths for review. Do not reclassify untracked files or refresh context in the consuming workflow.

Exit 0 means the saved boundary matches; exit 2 returns a rejection with an existing automation reason code: `CONTEXT_INVALID`, `CONTEXT_STALE`, or `BOUNDARY_UNRESOLVED`. Unknown fingerprint algorithms (including old prose-defined fingerprints) require fresh context. This helper's diagnostic JSON is internal; it does not replace or version the public automation result v1. Context automation maps a capture failure to `BOUNDARY_UNRESOLVED`; review preserves the verification reason.

The fingerprint also binds the saved intent, stage and scope metadata. Uncommitted verification covers the baseline, full index, raw tracked worktree content and modes, included untracked content and symlink targets, and the classified untracked inventory. Newly appearing or disappearing untracked paths require fresh context; excluded file contents and ignored files do not. Reading raw bytes avoids Git diff settings, text conversions and clean filters. This can read the full tracked worktree and treats raw line-ending or executable-bit changes as snapshot changes. Conflicted indexes, submodule worktrees and unsupported file types fail closed. Committed verification uses frozen commit objects and ignores later HEAD, branch and worktree movement. Fingerprint internals live only in the helper code.
