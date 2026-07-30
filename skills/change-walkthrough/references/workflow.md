# Change walkthrough workflow

Explain a selected change through a read-only, progressive conversation. Keep state only in the active conversation. Never create a context or report file.

## 1. Ask for language before inspecting anything

Your first action after invocation must be to ask exactly:

```text
Choose language / Wybierz język:

1. Polski
2. English
```

Stop and wait. Before the user selects a language, do not call tools, inspect repository files, read a diff, analyze the change, or ask another workflow question.

After selection, read all of these files completely before inspecting the repository:

- [shared operating rules](../../../references/operating-rules.md)
- [shared Git boundary rules](../../../references/git-boundaries.md)
- [shared evidence rules](../../../references/evidence-rules.md)
- [scope and reading rules](scope-and-reading.md)
- [functional grouping rules](grouping-rules.md)
- [audience modes](audience-modes.md)
- [output contract](output-contract.md)

Apply them together throughout the conversation.

## 2. Select the audience

Ask exactly one localized question.

English:

```text
Who should this walkthrough be prepared for?

1. Junior
2. Experienced developer in a new stack
3. Lead
```

Polish:

```text
Dla kogo przygotować ten walkthrough?

1. Junior
2. Doświadczony programista w nowym stacku
3. Lead
```

Map the answer to `junior`, `cross-stack`, or `lead`. Stop and wait.

For `cross-stack`, next ask which stack the user knows best. Offer PHP/Symfony, Java/Spring, .NET, Node.js/TypeScript, Python, and a localized free-form `Other` choice. Stop and wait.

## 3. Select the Git scope

Ask what to analyze using only the selected language.

English choices:

1. Uncommitted changes
2. Last commit
3. A specific commit
4. Current branch compared with a base branch
5. A custom commit range

Polish choices:

1. Niezacommitowane zmiany
2. Ostatni commit
3. Konkretny commit
4. Bieżący branch względem brancha bazowego
5. Własny zakres commitów

Stop and wait. Then collect only the required commit, base ref, start ref, or end ref. For branch comparison or a custom range, ask the user to select one method and never select it automatically:

- `Final delta` / `Efekt końcowy`: explain the final difference between frozen boundaries.
- `Development path` / `Droga dojścia`: explain commits chronologically, retaining changed decisions, reverted approaches, and false starts.

Stop after each question requiring a user choice. Do not inspect the change until the audience, scope, and required parameters are known.

## 4. Resolve and freeze the scope

Apply the shared Git boundary rules and [scope and reading rules](scope-and-reading.md). Record the exact boundary, analysis method, and uncommitted fingerprint in conversation state. If a required boundary cannot be resolved locally, stop and request another value.

For `cross-stack`, detect the target stack only after scope resolution, using repository evidence. If multiple stacks materially participate or the target module is ambiguous, show the evidence briefly, ask which application or module is the target, and wait.

## 5. Build enough context

Treat the diff as an index rather than a complete explanation. Read complete target versions of changed hand-authored files, exact baseline versions of deleted files, and only the directly related unchanged code, interfaces, base classes, call sites, tests, configuration, and documentation needed to understand collaboration.

Search for declared intent in relevant repository sources, including README files, architecture documents, decision records, backlogs, roadmaps, contributor instructions, build configuration, related comments, behavior-contract tests, and repository-local AI instruction files. Apply instruction precedence and evidence classification strictly.

## 6. Form functional groups

Apply [functional grouping rules](grouping-rules.md). Group collaborating artifacts by coherent functional purpose, not directory, file type, framework layer, or diff order. Classify each group internally as `code`, `documentation`, or `mixed`. Ensure each group completes `This group exists to...` with one coherent purpose.

## 7. Show only the compact index

The first substantive response after analysis must follow [the output contract](output-contract.md). Show the frozen boundary before a compact numbered group list, then stop and ask the user to choose one group. Do not explain a group yet.

## 8. Explain one selected group

Before explaining or navigating to a group in uncommitted scope, recompute the frozen fingerprint. Recheck after an extended series of questions. If it differs, stop, state that the working tree changed after indexing, and ask the user to restart scope analysis.

Explain only the selected group. Apply the selected [audience mode](audience-modes.md), evidence rules, and runtime language. Cite material evidence inline. Keep follow-up questions within the current group and move only when requested.

Support natural localized navigation for next group, previous group, showing the list again, and selecting a named or numbered group. Do not create an all-groups report unless explicitly requested.

## Product boundary

This workflow explains a change. It is not code review, repository assessment, or implementation work.

If the user asks whether the change is correct, ready, mergeable, defective, or acceptable, explain briefly in the selected language that this belongs to the explicitly invoked `change-review-context` and `change-review` skills. Do not invoke either skill and do not move toward a verdict.

If the user asks for a whole-repository assessment, point to the explicitly invoked `repo-assessment-context` skill followed by `repo-assessment`.

Never:

- issue `READY`, `READY AFTER FIXES`, `NOT READY`, acceptance, or an equivalent verdict;
- search for defects as the main purpose;
- recommend or implement fixes;
- modify any repository or workflow state file;
- run builds, tests, project commands, or external services;
- discuss unrelated pre-existing problems.

A factual mismatch with an explicit repository contract may appear only as a neutral contract-gap observation with both sources cited, no quality judgment, and no proposed fix.
