# Repository assessment workflow

Assess whether the repository delivers on the promise saved in its context, under the saved users, constraints, risk, maturity, and exact scope.

## 1. Load and validate context

Read completely:

- [shared operating rules](../../../references/operating-rules.md)
- [shared Git boundary rules](../../../references/git-boundaries.md)
- [shared evidence rules](../../../references/evidence-rules.md)
- `.engineering-lens/repo-assessment-context.md` from the selected repository root.

If context is missing, empty, ambiguous, unsupported, or not format version `1`, stop and ask the user to run the explicitly invoked `repo-assessment-context` skill. Do not infer replacement context and do not create a report.

Verify that the current canonical root equals the saved repository root. Use the saved report language for all natural-language output. Keep stable report headings and identifiers in English when needed.

Treat `[user-confirmed]` facts as user evidence, `[inferred, not user-confirmed]` values as lower-confidence hypotheses, `[unconfirmed]` values as unknown, and `[not applicable]` values as excluded. Never silently strengthen their status.

## 2. Reconstruct exact code and history scope

Validate every saved SHA, path, mode, selection rule, count, and fingerprint as data.

- For a committed snapshot, inspect the frozen target commit without checking it out. Do not substitute current `HEAD`.
- For an uncommitted snapshot, verify the saved baseline or empty-tree state, rediscover relevant untracked files under the saved purpose and exclusions, exclude both repository-assessment state files, and recompute the content fingerprint. Stop on any drift.
- Reproduce the saved history commit set through its frozen boundaries and exact selection rule. Verify its count and deterministic ordered-SHA fingerprint. Stop if it cannot be reproduced.
- Apply saved path/module filters and exclusions to both inspection and conclusions.

If the boundary is missing, stale, or unavailable, stop, name the exact problem, and request fresh context. Never fetch, widen, or silently update it.

## 3. Judge fit for purpose

Do not apply one generic quality standard. Judge the repository against its actual promise, users, scale, constraints, failure impact, risk, expected maturity, team context, and effort budget.

Maintain an absolute floor for demonstrable correctness and security failures, while keeping architecture, process, documentation, test breadth, and operational expectations proportional to context. Do not reward complexity for its own sake or punish a simple design that fulfills the promise.

Assess only relevant dimensions:

- business and product fit;
- code organization, responsibility placement, maintainability, and justified complexity;
- declared architecture versus observed boundaries and dependency direction;
- tests, changed behavior coverage, and expected quality gates;
- local setup, delivery, CI/CD, operations, and external contracts;
- documentation truthfulness, freshness, and usefulness;
- commit history, traceability, churn, and delivery signals when history is in scope;
- security, privacy, compliance, reliability, and runtime AI/LLM risks when relevant.

Do not infer personal productivity, blame developers, claim AI use without sufficient evidence, or conduct a penetration test unless that separately authorized work is in scope.

## 4. Sample deliberately

Start with cheap aggregate signals inside the frozen scope: tracked-file distribution, manifests, dependency and tool configuration, CI, test footprint, documentation map, history size, author counts, change frequency, and churn hotspots.

Then deeply inspect a small set of:

- representative modules showing the dominant design;
- high-risk modules such as authentication, authorization, money, personal data, external APIs, runtime AI/LLM boundaries, or areas named in context;
- tests and contracts for the most important behavior;
- documentation and delivery configuration tied to the promise.

Track what was read deeply, sampled, and not opened. Confidence must follow coverage. Do not claim high confidence about uninspected areas.

## 5. Validate safely

Identify expected commands from saved context and repository evidence. Run a command only when it is relevant, authorized by context, demonstrably read-only for the worktree, does not install anything, does not start a service, and does not contact production or an external dependency. Do not allow caches, generated files, coverage files, build output, lockfile changes, or other artifacts in the repository.

If a useful gate cannot meet those restrictions, do not run it. Record it as not performed and classify the reason: repository problem, missing local dependency, missing secret, unavailable external service, insufficient environment, unclear documentation, or workflow write restriction.

## 6. Build evidence-based conclusions

For each important finding, provide the evidence location or command, why it matters against the saved promise, who or what is affected, the plausible consequence, the smallest practical next step, and confidence.

Keep repository evidence, user-confirmed facts, declared rules, inferred facts, and unconfirmed areas distinct. Call out context conclusions that rely materially on inferred inputs.

Avoid vague labels. Translate observations into concrete repository signals and consequences. Report uncertainty instead of inventing missing business, runtime, production, or process facts.

## 7. Write only the final report

Create or replace only `.engineering-lens/repo-assessment-report.md`. Do not modify the saved context or another path. Use this compact three-part structure and omit an inapplicable detailed section rather than padding it:

```markdown
# Repository Assessment Report

## Part A — Executive view

### Executive summary
<promise, overall fit, strongest signal, biggest risk, recommended next step>

### Verdict
<FIT FOR PURPOSE | PARTIALLY FIT FOR PURPOSE | NOT FIT FOR PURPOSE | INCONCLUSIVE>
Confidence: <High | Medium | Low, tied to coverage>
<plain-language rationale>

### Top strengths
<up to three: observation, evidence, why it matters>

### Top risks
<up to three: observation, evidence, consequence, severity, confidence, next step>

## Part B — Relevant detail

### Context and scope used
<promise, audience, exact snapshot/history, constraints, inferred inputs, unknowns>

### Fit against the promise
<business, user, scale, operational, documentation, and maturity fit as relevant>

### Engineering evidence
<only relevant subsections: organization, architecture, quality, delivery, documentation, history, security/risk, AI/LLM>

### Validation
<performed commands/results and important commands not performed/reasons>

## Part C — Evidence and action

### Evidence table
| Area | Observation | Evidence | Consequence | Confidence |
|---|---|---|---|---|

### Recommended next steps
<immediate fixes, deeper investigation, and strategic decisions as applicable>

### Questions for further drill-down
<remaining business or technical questions>

### Coverage and limits
<deep reads, samples, unopened areas, unavailable evidence, and confidence effect>
```

For a recruiter audience, add a hiring-signal interpretation against the saved brief and effort budget. Do not recommend a rewrite unless evidence strongly requires it.

After writing, tell the user the report path, verdict and confidence, highest-risk finding, and whether quality gates were performed or blocked.

## Boundaries

- Do not modify application code, tests, configuration, documentation, Git state, context, or any file other than the report.
- Do not commit, deploy, publish, delete data, rotate secrets, contact production, or run destructive migrations.
- Do not claim verification beyond the exact saved scope and evidence coverage.
