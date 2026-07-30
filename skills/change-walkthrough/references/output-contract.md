# Walkthrough output contract

Use progressive disclosure. Preserve language, audience, frozen scope, group list, recommended order, and current group in conversation only.

## First substantive response

After analysis, output only:

1. selected language;
2. selected audience;
3. selected scope and, where applicable, `Final delta` or `Development path` in the selected language;
4. exact Git boundaries with full 40-character commit SHAs or an explicit localized empty-tree marker;
5. detected target stack and known stack for `cross-stack`;
6. a numbered list of every functional group;
7. one short purpose sentence for each group;
8. a recommended group-reading order;
9. a request to choose one group.

For uncommitted scope, state the baseline and truthfully identify the target as a captured index/working-tree snapshot. Separate staged, unstaged, and included relevant untracked paths. Do not fabricate a target SHA.

Do not include group internals, before/after behavior, design explanations, counterfactuals, findings, or a report. Stop after requesting a group.

## Selected group

Explain only the chosen group. Include sections only when useful. Cover its purpose, behavior before and after, collaboration, flow or historical evolution, supported patterns, audience-specific interpretation, sources and confidence, and member files.

Cite material claims inline. Explain one propagated idea once and then list locations. Keep unrelated existing issues out. End with a short localized invitation to ask about the current group or navigate.

## Navigation

Before changing groups in uncommitted scope, verify the fingerprint. Stop on drift.

- Next or previous group: select it in recommended order and explain only it.
- Show the list again: repeat the compact index, retain the frozen boundary, and mark the current group.
- Current-group follow-up: answer without switching.
- Named or numbered group: switch and explain only that group.

If no next or previous group exists, say so briefly and offer the list. Produce all groups only after an explicit request, preserving grouping, order, sourcing, and audience rules.

Never use verdict-like substitutes such as `looks good`, `safe to merge`, `acceptable`, or `should be approved`.
