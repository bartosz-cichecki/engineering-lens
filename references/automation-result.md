# Automation result v1

This is the explicit orchestrator contract for `change-review-context --automation` and `change-review`. Read this reference before either workflow produces an automation result. The context Markdown format remains version 1 independently of this result version.

## Execution and transport

Run [the Python runner](../scripts/automation.py) from the target repository with Python 3 and Claude Code on `PATH`. The runner resolves its own checkout through `__file__` and passes its absolute root as `--plugin-dir`; no global Engineering Lens installation is required. It invokes Claude exactly once, validates the entire response locally, and prints exactly one JSON result plus a newline to stdout. Never parse conversational prose or the human report for status or verdict. Stderr carries the redacted human report and CLI diagnostics and is a separate diagnostic channel, including on failure. Do not merge stderr into stdout.

The runner activates automation transport through its system instruction and `--json-schema`. Perform the selected workflow without questions, then submit exactly `{"automation_result": <result object>, "human_report": "<full report or diagnostic>"}` through the CLI's schema-constrained structured output. The transport schema requires both fields, forbids additional fields, and embeds the existing automation result v1 schema for `automation_result`. The CLI JSON envelope's `structured_output` object is the only source of this payload. The `result` field is diagnostic text only: never parse JSON, Markdown fences, or surrounding prose from it, even when structured output is missing or invalid. The runner strictly decodes the entire envelope (including duplicate-key detection) and validates the payload and cross-field semantics locally. It never launches another invocation to repair output; Claude's native structured-output attempts happen within the single invocation.

Without runner transport, context automation and every change review still emit the same result object after human-readable communication, in a fenced JSON block. Interactive context collection remains unchanged. Only the runner's stdout and exit code provide the validated orchestrator interface; direct skill prose is not a validated transport.

## Standalone and orchestrator invocation

From the target repository root, standalone usage remains:

```bash
python3 /path/to/engineering-lens/scripts/automation.py change-review-context --automation < task-contract.md > /tmp/context-result.json
python3 /path/to/engineering-lens/scripts/automation.py change-review > /tmp/review-result.json
```

Run review only after context exits 0. Keep result/log files outside the evaluated worktree so they do not alter its fingerprint. The default invocation retains `claude -p --permission-mode auto --no-session-persistence --output-format json`. It adds `--json-schema` for the required payload, the local plugin directory and the automation system instruction. Model and effort are omitted by default, so Claude's existing environment/settings determine them. Authentication and the rest of the child environment are inherited unchanged; the runner does not install a plugin, change Claude configuration, or persist credentials.

An external orchestrator such as AgentFlow can construct the runner's argv directly, using the same Claude execution parameters it already owns. For example:

```python
completed = subprocess.run(
    [
        "python3", "/path/to/engineering-lens/scripts/automation.py",
        "change-review",
        "--model", selected_model,
        "--effort", selected_effort,
        "--permission-mode", selected_permission_mode,
        "--allowedTools", "Read", "Bash(git *)",
        "--disallowedTools", "Bash(git push *)",
        "--tools", "Read,Bash",
        "--settings", "/path/to/agentflow/claude-policy.json",
    ],
    cwd=target_repository,
    env=claude_environment,
    capture_output=True,
    text=True,
)
# Parse only completed.stdout as the automation result.
# Preserve completed.stderr as diagnostics on every exit code, including 3 and 4.
```

The model, effort and tool list above are invocation parameters, not a recommended review policy. Pass AgentFlow's actual existing values. For context, use `change-review-context --automation` and pass the Task Contract through `input=task_contract`. Credential-bearing environment values stay in `env`, never in the Task Contract, argv, or logs of the orchestrator's invocation.

| Runner option | Claude behavior |
| --- | --- |
| `--model VALUE`, `--effort VALUE` | Forward values unchanged; no runner-imposed model/effort defaults |
| `--permission-mode VALUE` | Replace the standalone `auto` default with the given mode |
| `--permission-mode inherit` | Omit the CLI permission-mode flag so existing Claude settings determine policy |
| `--dangerously-skip-permissions` | Forward the existing bypass flag; mutually exclusive with an explicit permission mode |
| `--permission-prompts VALUE` | Forward print-mode prompt policy |
| `--allowedTools RULE ...`, `--disallowedTools RULE ...` | Forward allow/deny rules as argv elements; kebab-case aliases and repeated options are accepted |
| `--tools TOOL ...` | Forward the tool set, including `--tools ""` for no tools |
| `--settings PATH_OR_JSON`, `--setting-sources VALUE` | Forward settings unchanged, including an empty settings-source string |
| `--redact-env NAME` | Runner-only; also redact this inherited variable's value; repeat for nonstandard secret variable names |
| `--timeout SECONDS` | Runner-only; default 900 seconds |

There is no shell interpolation of option values. The runner owns plugin location, print mode, JSON transport, the automation system instruction and session persistence; callers cannot override these with additional arbitrary Claude flags. Claude validates supported model/effort/policy values, so an incompatible execution option produces the existing technical error with redacted CLI diagnostics. Choosing execution permissions does not change either workflow's scope or write rules.

## Error diagnostics and credential inputs

For `contract_error` and `technical_error`, stderr includes the failure category, actual CLI exit code when available, and captured Claude stdout/stderr. This preserves malformed payloads, model explanations and CLI error details without treating them as a valid result. Context artifact validation failures retain the same captured output. Timeouts preserve partial stdout/stderr. Launch and runner I/O failures identify the exception class without printing exception argv or input. CLI warnings are also retained on successful and rejected operations. Argument usage errors never echo supplied values.

Before any captured output is emitted, the runner replaces known secret values with `[REDACTED]`:

- Inherited environment variables whose names contain token, secret, password/passwd, credential, API/access/private key, auth, or cookie markers (including `ANTHROPIC_API_KEY`, `ANTHROPIC_AUTH_TOKEN`, `CLAUDE_CODE_OAUTH_TOKEN`, and AWS key/session variables).
- Values of additional environment variables named with `--redact-env NAME`, for example `--redact-env AGENTFLOW_INPUT`. Structured credential JSON in these variables is protected both as a whole input and as its string values.
- Credential fields in explicitly supplied `--settings` JSON or settings files, as well as the complete settings input. This includes secret environment values and `apiKeyHelper` input; the runner never executes the helper itself.

Redaction covers literal values, nested JSON escaping, URL encoding and Base64 encoding. It applies to success reports, malformed output, CLI stderr and timeout output alike. Supply custom secrets through marked environment variables; the runner cannot discover credentials fetched internally by Claude or arbitrary model transformations of secrets. Do not put credentials in task prose or execution-option values. The runner never logs its argv, environment, stdin, or credential input independently of CLI diagnostics, and never substitutes redacted text into the versioned machine result.

## Fields and consistency

[The JSON Schema](automation-result-v1.schema.json) defines the closed field vocabulary. [The validator](../scripts/automation.py) additionally enforces operation, status, reason, Task Contract states, and verdict consistency. Unknown fields, duplicate JSON keys, unsupported versions, partial objects, contradictory combinations, multiple verdicts, and free-form strings in machine fields are contract errors.

- `format_version`: integer `1`.
- `operation`: `change-review-context` or `change-review`; identifies the operation kind, not a unique invocation. Orchestrators associate the single stdout result with their own job ID.
- `status`: `success`, `rejected`, `contract_error`, or `technical_error`.
- `reason_code` and `message`: use the exact pair below. Messages are stable English diagnostics, independent of the human report language.
- `task_contract`: for context, an object containing exactly `goal_reason`, `intentional_exclusions`, `completion_criteria`, and `risks_external_constraints`. For review, `null`.
- `verdict` and `verdict_rationale`: populated only for a completed review; otherwise both `null`.

| Status | Reason code | Exact message |
| --- | --- | --- |
| success | CONTEXT_CREATED | Review context created. |
| success | REVIEW_COMPLETED | Review completed. |
| rejected | TASK_CONTRACT_INCOMPLETE | Required Task Contract data is missing or ambiguous. |
| rejected | LANGUAGE_UNSUPPORTED | Task Contract language is unsupported or ambiguous. |
| rejected | BOUNDARY_UNRESOLVED | The review boundary cannot be established safely. |
| rejected | CONTEXT_INVALID | Saved review context is missing or invalid. |
| rejected | CONTEXT_STALE | Saved review context no longer matches the review boundary. |
| contract_error | AUTOMATION_RESULT_INVALID | Automation result is missing, malformed, or inconsistent. |
| technical_error | CLAUDE_FAILURE | Claude or its CLI failed. |

Assess **all four** Task Contract elements even when an earlier one fails. `derived` means explicit, consistent data can be faithfully derived; `missing` means absent; `ambiguous` means present but unclear or contradictory. Goal without a reason is `missing`; contradictory goal/reason is `ambiguous`. `intentional_exclusions` is `derived` when intentional exclusions, an explicit declaration of none, or a clearly bounded scope establishes the change boundary. Risks and external constraints are optional: their omission is `missing` and does not make the Task Contract incomplete. Explicit risks or constraints, including those outside a dedicated section, or an explicit declaration of none are `derived`; unclear or contradictory supplied constraints are `ambiguous`. Never require a synthetic `Risks: none` declaration or infer intent from the diff. Do not include the extracted values in the result.

For context success, language rejection, or boundary rejection, `goal_reason`, `intentional_exclusions`, and `completion_criteria` must be `derived`; `risks_external_constraints` may be `derived` or `missing`. If any of the three required elements is `missing`, or any element is `ambiguous`, use `TASK_CONTRACT_INCOMPLETE` before checking language or Git. All four machine fields remain required by schema v1 even though supplying risks in the input is optional. Reserve `not_evaluated` for runner-generated contract/technical errors: discarded malformed model data cannot establish any element. On these errors, all four states are `not_evaluated`. Review precondition rejection uses `CONTEXT_INVALID`, `CONTEXT_STALE`, or `BOUNDARY_UNRESOLVED`, with no verdict. Never use `NOT READY` for a workflow that could not start a valid review.

For completed reviews, use `success` / `REVIEW_COMPLETED` regardless of readiness, with exactly one of these pairs. Put change-specific rationale and evidence in the human report.

| Verdict | Exact short verdict_rationale |
| --- | --- |
| READY | No blocking finding exists for the saved stage. |
| READY AFTER FIXES | Bounded fixes are required before advancement. |
| NOT READY | Goal conflicts, redesign, or essential evidence prevent advancement. |

The model produces only `success` or `rejected`. The runner owns `contract_error` and `technical_error`. A successful CLI exit alone is insufficient. Missing/invalid result data and structured-output retry exhaustion are contract errors. A nonzero CLI exit, CLI `is_error: true`, launch failure, or timeout is a technical error (retry exhaustion takes precedence). No partial model result is forwarded on stdout on failure; rejected raw output remains available as redacted stderr diagnostics.

| Exit code | Meaning |
| --- | --- |
| 0 | Valid completed operation; inspect the verdict for review readiness |
| 2 | Valid semantic rejection |
| 3 | Automation contract error |
| 4 | Technical Claude/CLI failure |

Command usage errors are argparse errors on stderr with exit 2 and no result; invoke the documented command shape. Unknown versions or absent stdout must never count as success. A runner process killed externally may not emit a result; the orchestrator must treat that as execution failure.

## Credentials and artifacts

Machine fields accept only fixed identifiers, fixed messages/rationales, enums, and null. Do not add raw Task Contract values, repository excerpts, paths, credentials, tokens, CLI metadata, or exception text. Local allowlist validation prevents arbitrary model text from entering the structured result, rather than relying on a secret-detection regex. Keep credentials and secrets out of the human report and saved context too; describe their role without reproducing their values. Human diagnostics can contain repository details and require appropriate log handling.

Context success requires the workflow to create or replace `.engineering-lens/change-review-context.md` according to its existing schema. The runner also checks that the artifact was saved and has the required structure. Semantic rejection must leave the file untouched. A technical or contract failure can occur after a write: do not consume a context from a failed operation. The runner does not roll back filesystem side effects or certify the model's factual derivation/fingerprint calculation. Review remains read-only and no result/report files are written by the runner.

## Claude CLI capability decision

Checked locally with `claude --version` and `claude --help`: Claude Code **2.1.263** supports `--output-format json` and `--json-schema`. The [headless documentation](https://code.claude.com/docs/en/headless) distinguishes the text `result` envelope from schema-constrained `structured_output`. The [CLI reference](https://code.claude.com/docs/en/cli-usage) describes schema output after workflow completion, and [structured output documentation](https://code.claude.com/docs/en/agent-sdk/structured-outputs) documents validation retries and `error_max_structured_output_retries`.

Native schema output constrains shape but does not guarantee this contract's cross-field semantics or secret exclusion. The runner therefore retains deterministic validation and redaction. Native retry exhaustion (`error_max_structured_output_retries`) maps to `contract_error` / `AUTOMATION_RESULT_INVALID`, including when the CLI exits nonzero; the runner does not retry or fall back to `result`. Supported CLI capability was checked on **2.1.263** with local version/help output and the documented `structured_output` envelope contract. Tests exercise a deterministic fake CLI, not paid inference or live model accuracy.
