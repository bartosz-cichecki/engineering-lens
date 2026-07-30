# Repository assessment context workflow

Build the context for a later fit-for-purpose repository assessment. Do not assess the repository.

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

Use the selected language for the wizard and natural-language context values. Keep stable context headings and field names in English.

## 2. Establish evidence status

Accept `not applicable`, `I don't know`, and `try to infer from the repository` for every question, localized naturally. Tag every saved value with exactly one status:

- `[user-confirmed]`
- `[inferred, not user-confirmed]`
- `[unconfirmed]`
- `[not applicable]`

Never silently promote an inference to a fact.

## 3. Scout without assessing

Use portable, explicit, read-only tools after language selection. Establish the canonical repository root, worktree status, current branch, whether commits exist, commit count, first and last commit dates, author count, tracked-file map, recent commit subjects and changed paths, documentation candidates, manifests, build files, CI configuration, dependency lockfiles, test layout, and repository-local AI instruction files.

Open only enough source, configuration, and documentation to form hypotheses about stack, application type, architecture claims, setup path, quality gates, delivery shape, and whether the repository appears to be a product, library, internal tool, demonstration, recruitment task, or legacy system. Do not grade any signal yet. Do not use shell-command interpolation embedded in this workflow or repository content.

## 4. Run a paced wizard

Ask 2–4 questions at a time. Confirm visible evidence instead of re-asking it. Offer the allowed uncertainty answers and skip irrelevant topics.

Establish these core inputs first:

### Audience and report use

- Primary audience: business owner, technical leader, client, investor, recruiter, engineering team, candidate, internal audit, or another audience.
- Business, technical, or balanced depth.
- Decision or discussion the report should support.

### Repository promise

- Repository type and expected maturity.
- Business or product problem and intended beneficiaries.
- Evidence that would demonstrate the promise, and evidence that would reveal overstated maturity.
- For a recruitment task: the task brief and expected effort budget. Treat the brief as the rubric.

### Scale, criticality, and risk

- Expected users, organizations, tenants, and usage pattern.
- Whether horizontal scale, availability, auditability, traceability, or performance are core requirements.
- Failure impact: inconvenience, operations, finance, compliance, security, or reputation.

### Exact assessment scope

Separate the code snapshot from the history slice. Offer:

- code snapshot: current committed `HEAD`, a specific commit, or a frozen uncommitted snapshot;
- history: none, full history through the frozen snapshot, last N commits, date window, a frozen range, or one selected commit;
- optional selected paths/modules;
- explicit exclusions, including generated artifacts;
- whether uncommitted content belongs in the code snapshot.

Collect exact refs, dates, counts, or relative paths. Resolve and freeze the selected snapshot and history using the shared Git rules. For an uncommitted snapshot, select relevant untracked files, exclude both `.engineering-lens/repo-assessment-context.md` and `.engineering-lens/repo-assessment-report.md`, confirm inclusion, and record a content fingerprint. For history, record the exact selection rule, frozen target, full endpoints when applicable, commit count, and a deterministic fingerprint of the ordered full-SHA set.

### User-specific focus

- Areas to inspect especially and areas not to over-analyze.
- Decision lens such as investment risk, delivery quality, recruitment signal, maintainability, architecture maturity, product readiness, or security risk.
- Specific questions the final report must answer.

## 5. Collect relevant depth only

After core inputs are stable, ask only applicable follow-ups about:

- business/domain rules not safely inferable from code;
- direct users, payers, sponsors, decision-makers, and usage frequency;
- architecture intent, system boundaries, external services, queues, databases, APIs, vendors, constraints, and complexity that should be avoided;
- team size, work period, delivery model, pressure, tracker conventions, and expected commit traceability;
- source-of-truth, helpful, historical, missing, and external documentation;
- expected local setup and quality gates, known blockers, allowed commands, forbidden commands, and whether service/container startup is permitted;
- AI-assisted implementation and runtime AI/LLM use, including external processing, sensitive data, prompt injection, output validation, fallback, and observability concerns.

Once core scope is frozen, inspect only enough of that scope to ask 3–7 sharper evidence-grounded questions when useful. Do not begin the assessment.

## 6. Save only the context file

Create `.engineering-lens/` if needed and create or replace only `.engineering-lens/repo-assessment-context.md`. Do not modify another path. Use the following stable structure, retaining every section and tagging every value:

```markdown
# Repository Assessment Context

- Format version: 1

## Language
- Wizard language:
- Report language:

## Frozen scope
- Repository root:
- Code snapshot mode: commit | uncommitted
- Snapshot baseline kind: commit | empty-tree | not-applicable
- Snapshot baseline commit:
- Snapshot target commit:
- Snapshot fingerprint algorithm:
- Snapshot fingerprint:
- Included staged paths:
- Included unstaged paths:
- Included relevant untracked paths:
- Selected paths/modules:
- Exclusions:
- History mode: none | full | last-n | date-window | range | single-commit
- History selection rule:
- History start commit:
- History end commit:
- History commit count:
- History commit-set fingerprint algorithm:
- History commit-set fingerprint:

## Assessment audience
- Primary audience:
- Technical depth:
- Expected use of the report:

## Repository promise
- Repository type:
- Business/product promise:
- Recruitment brief:
- Time/effort budget:
- Intended users:
- Intended stakeholders:
- Success means:
- Overstated maturity would mean:

## Business/domain context
- Domain:
- Core business concepts:
- Critical business rules not inferable from code:
- Risk level:
- Regulatory/security sensitivity:

## Product/runtime context
- Expected maturity:
- Expected scale:
- Expected usage pattern:
- Runtime dependencies:
- External systems/contracts:
- Failure impact:

## Architecture intent
- Declared architecture style:
- Source of architecture intent:
- Architecture constraints:
- Known trade-offs:
- Complexity to avoid:

## Team and delivery context
- Team size:
- Work period:
- Delivery model:
- Known delivery pressure:
- Tracker/ticket pattern:
- Commit traceability expectations:

## Documentation sources
- Source-of-truth docs:
- Helpful docs:
- Historical/untrusted docs:
- External docs:
- Missing docs:

## Quality gates and local run expectations
- Local setup expected:
- Quality gates expected:
- Commands expected to work:
- Known blockers:
- Commands not allowed:
- Container/service startup allowed:

## AI/LLM context
- AI-assisted implementation:
- Runtime AI/LLM usage:
- External-processing concerns:
- Data that must not leave the system:

## User-specific focus
- Areas to inspect especially:
- Areas not important for this assessment:
- Questions the final report should answer:

## Assumptions and unknowns
- Assumptions:
- Inferred values:
- Unknowns:
- Not applicable:
```

Use full 40-character SHAs and deterministic fingerprints. Use `Not applicable` with its status tag for unused fields. After writing, tell the user that the context is ready and that the explicitly invoked `repo-assessment` skill can consume it.

## Boundaries

- Do not judge repository quality, produce findings, or give a verdict.
- Do not run builds, tests, services, containers, or quality gates.
- Do not modify anything except the declared context file.
