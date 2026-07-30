# Functional grouping rules

Grouping is the central walkthrough behavior. Build a two-level map of functional groups and idea-level subsections.

## Group level

A group is valid only when one coherent sentence completes:

```text
This group exists to...
```

Group collaborating artifacts even when they cross directories, file types, or framework layers. A migration, entity, repository, and integration test can form one persistence capability. A dependency, configuration, endpoint, and endpoint test can form one operational capability. Related documentation can join code only when it supports the same purpose.

Do not default to grouping by directory, file type, framework layer, one file per group, or diff hunk. Split a group when it contains independent purposes that can be understood separately. Merge candidates when neither purpose is complete without the other.

For `Development path`, retain functional grouping and show how each idea evolved across commits, including meaningful reversals and false starts.

## Subsection level

One subsection represents one thought, not one occurrence. Explain a propagated decision once and name its propagation points. Keep mechanical propagation subordinate to the functional decision.

## Internal classification

Classify each group as `code`, `documentation`, or `mixed` without exposing the label unless useful.

For code, cover observable behavior before and after, important collaboration, supported patterns or mechanisms, one useful counterfactual for each non-obvious decision, and evidence status.

For documentation, extract decisions, rationale, promises, and synchronization already present. Combine repeated statements and do not invent a counterfactual when the document states its reason.

For mixed groups, explain code, tests, configuration, and documentation as one capability without assuming a nearby document proves implementation intent.

## Avoid diff narration

Do not merely translate hunks into prose. Explain capability, collaboration, intent, consequence, or historical evolution. Name recognizable ecosystem or architecture concepts only when evidence supports them.

Compress generated wrappers, standard entry points, mirrored translations, framework boilerplate, mechanical moves, and repeated value propagation unless they carry a real decision. Spend attention on non-obvious alternatives, cross-file collaboration, ecosystem idioms, architectural boundaries, intent sources, and evidence limits.

Recommend an understanding-driven reading order: central capability or contract first, enabling integrations next, and supporting documentation or delivery artifacts last. Within each group, order files from contract or entry point through implementation and evidence.
