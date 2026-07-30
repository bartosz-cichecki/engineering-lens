# Audience modes

The audience changes what information to extract, not only response length.

## `junior`

Teach the implementation represented by the selected group. Explain observable behavior before and after, execution or data flow, responsibilities across files, recognizable patterns, a useful counterfactual for each non-obvious element, a recommended file-reading order, and evidence status.

Explain ecosystem-specific ideas needed for the change, but do not teach universal programming basics unless required to understand the group.

## `cross-stack`

Assume an experienced programmer who understands architecture but is learning the target language, framework, or build ecosystem. Use the user's known stack as a bridge.

Explain behavior before and after; target-ecosystem implementation; ecosystem idioms versus project-specific decisions; the nearest useful known-stack equivalent; the limit of each analogy; important false friends; canonical target terms; reading order; and evidence status.

Do not explain universal concepts such as classes, HTTP, dependency injection, repositories, or unit tests unless the target ecosystem changes their semantics. Do not force an analogy. State directly when no close equivalent exists.

Detect the target stack from manifests, build files, source extensions, framework configuration, and entry points. Cite evidence when material. Ask the user to choose a target application or module when several stacks are materially involved.

## `lead`

Optimize around `intent → consequence → contract gap`.

Explain the decision or capability, material system/delivery/operations/future-development consequence, the evidence establishing intent or its limitation, and factual mismatches with an explicit contract only when present and relevant.

Compress standard wrappers and boilerplate unless they carry a material decision. Do not teach implementation basics, conduct code review, judge quality, recommend changes, or issue a readiness verdict.

Across every mode, retain before/after behavior, collaboration, supported mechanisms, appropriate counterfactuals, sourced intent, assumptions, and unconfirmed areas according to the group's classification.
