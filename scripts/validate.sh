#!/usr/bin/env bash
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
REPO_ROOT=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)

fail() {
  printf 'ERROR: %s\n' "$1" >&2
  exit 1
}

if ! command -v python3 >/dev/null 2>&1; then
  fail "Python 3 is required for structural validation; no third-party Python packages are required."
fi

python3 - "$REPO_ROOT" <<'PY'
import json
import re
import sys
from pathlib import Path

root = Path(sys.argv[1]).resolve()
expected = [
    "change-walkthrough",
    "change-review-context",
    "change-review",
    "repo-assessment-context",
    "repo-assessment",
]
errors = []


def distribution_files():
    files = {
        root / "README.md",
        root / "LICENSE",
        root / "scripts" / "validate.sh",
        root / ".codex-plugin" / "plugin.json",
        root / ".claude-plugin" / "plugin.json",
        root / ".claude-plugin" / "marketplace.json",
        root / ".github" / "workflows" / "validate.yml",
    }
    for pattern in (
        "references/*",
        "scripts/*.py",
        "tests/*.py",
        "skills/**/*",
        "adapters/claude/skills/**/*",
    ):
        files.update(path for path in root.glob(pattern) if path.is_file())
    return sorted(path for path in files if path.is_file())


def frontmatter_keys(frontmatter, relative):
    keys = re.findall(r"(?m)^([a-zA-Z0-9-]+):", frontmatter)
    duplicates = sorted({key for key in keys if keys.count(key) > 1})
    if duplicates:
        error(f"Duplicate frontmatter fields in {relative}: {', '.join(duplicates)}")
    return set(keys)


def error(message):
    errors.append(message)


def load_json(relative):
    path = root / relative
    if not path.is_file():
        error(f"Required manifest is missing: {relative}")
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        error(f"Manifest is not valid JSON: {relative}: {exc}")
        return {}
    if not isinstance(value, dict):
        error(f"Manifest root must be a JSON object: {relative}")
        return {}
    return value


codex_manifest = load_json(".codex-plugin/plugin.json")
claude_manifest = load_json(".claude-plugin/plugin.json")
marketplace = load_json(".claude-plugin/marketplace.json")

for label, manifest in (
    ("Codex", codex_manifest),
    ("Claude Code", claude_manifest),
):
    if manifest:
        if manifest.get("name") != "engineering-lens":
            error(f"{label} manifest name must be engineering-lens.")
        if manifest.get("version") != "0.1.0":
            error(f"{label} manifest version must be 0.1.0.")
        if manifest.get("license") != "MIT":
            error(f"{label} manifest license must be MIT.")

if marketplace:
    if marketplace.get("name") != "engineering-lens-tools":
        error("Claude Code marketplace name must be engineering-lens-tools.")
    plugins = marketplace.get("plugins")
    if not isinstance(plugins, list) or len(plugins) != 1:
        error("Claude Code marketplace must contain exactly one plugin entry.")
    else:
        entry = plugins[0]
        if entry.get("name") != "engineering-lens":
            error("Claude Code marketplace plugin name must be engineering-lens.")
        if entry.get("source") != "./":
            error("Claude Code marketplace source must point to the shared repository root.")
        if entry.get("strict") is not True:
            error("Claude Code marketplace must use the compatibility adapter definition.")
        expected_adapters = {
            f"./adapters/claude/skills/{name}" for name in expected
        }
        if set(entry.get("skills", [])) != expected_adapters:
            error("Claude Code marketplace must expose exactly the five adapter skills.")

skill_names = []
for name in expected:
    skill_dir = root / "skills" / name
    skill_md = skill_dir / "SKILL.md"
    workflow = skill_dir / "references" / "workflow.md"
    agent_yaml = skill_dir / "agents" / "openai.yaml"
    adapter = root / "adapters" / "claude" / "skills" / name / "SKILL.md"

    for path in (skill_md, workflow, agent_yaml, adapter):
        if not path.is_file():
            error(f"Required skill file is missing: {path.relative_to(root)}")

    if skill_md.is_file():
        text = skill_md.read_text(encoding="utf-8")
        match = re.match(r"\A---\n(.*?)\n---\n", text, re.DOTALL)
        if not match:
            error(f"Invalid frontmatter in skills/{name}/SKILL.md")
        else:
            frontmatter = match.group(1)
            unknown = frontmatter_keys(frontmatter, f"skills/{name}/SKILL.md") - {
                "name",
                "description",
            }
            if unknown:
                error(
                    f"Unsupported shared skill frontmatter fields for {name}: "
                    f"{', '.join(sorted(unknown))}"
                )
            name_match = re.search(r"(?m)^name:\s*([^\n]+)$", frontmatter)
            description_match = re.search(r"(?m)^description:\s*([^\n]+)$", frontmatter)
            parsed_name = name_match.group(1).strip() if name_match else ""
            if parsed_name != name:
                error(f"Skill metadata name does not match directory: {name}")
            if not description_match or not description_match.group(1).strip():
                error(f"Skill description is missing: {name}")
            if "disable-model-invocation" in frontmatter:
                error(f"Claude invocation metadata leaked into shared Codex skill: {name}")
            skill_names.append(parsed_name)

    if agent_yaml.is_file():
        text = agent_yaml.read_text(encoding="utf-8")
        for key in ("display_name:", "short_description:", "default_prompt:"):
            if key not in text:
                error(f"Missing Codex metadata {key} for skill {name}")
        if not re.search(r"(?m)^\s*allow_implicit_invocation:\s*false\s*$", text):
            error(f"Codex implicit invocation is not disabled for skill {name}")
        codex_invocation = f"$engineering-lens:{name}"
        if codex_invocation not in text:
            error(f"Codex default prompt does not explicitly name {codex_invocation}")

    if adapter.is_file():
        text = adapter.read_text(encoding="utf-8")
        match = re.match(r"\A---\n(.*?)\n---\n", text, re.DOTALL)
        if not match:
            error(f"Invalid frontmatter in adapters/claude/skills/{name}/SKILL.md")
        else:
            frontmatter = match.group(1)
            allowed = {
                "name",
                "description",
                "disable-model-invocation",
                "user-invocable",
                "argument-hint",
            }
            unknown = frontmatter_keys(
                frontmatter,
                f"adapters/claude/skills/{name}/SKILL.md",
            ) - allowed
            if unknown:
                error(
                    f"Unsupported Claude adapter frontmatter fields for {name}: "
                    f"{', '.join(sorted(unknown))}"
                )
            if not re.search(rf"(?m)^name:\s*{re.escape(name)}\s*$", frontmatter):
                error(f"Claude adapter name does not match directory: {name}")
            if not re.search(r"(?m)^description:\s*\S.*$", frontmatter):
                error(f"Claude adapter description is missing: {name}")
            if not re.search(r"(?m)^disable-model-invocation:\s*true\s*$", frontmatter):
                error(f"Claude model invocation is not disabled for skill {name}")
            if not re.search(r"(?m)^user-invocable:\s*true\s*$", frontmatter):
                error(f"Claude user invocation is not enabled for skill {name}")
        expected_link = f"../../../../skills/{name}/references/workflow.md"
        if expected_link not in text:
            error(f"Claude adapter does not point to the shared workflow: {name}")

        if name == "change-review-context":
            if not re.search(
                r'(?m)^argument-hint:\s*"\[--automation <full Task Contract>\]"\s*$',
                frontmatter,
            ):
                error("Claude change-review-context adapter does not advertise its automation input.")
            if text.count("$ARGUMENTS") != 1:
                error("Claude change-review-context adapter must pass invocation arguments exactly once.")

if len(skill_names) != len(set(skill_names)):
    error("Skill names must be unique.")
if set(skill_names) != set(expected):
    error("Implemented shared skill names do not match the required five skills.")

readme_path = root / "README.md"
if not readme_path.is_file():
    error("README.md is missing.")
    readme = ""
else:
    readme = readme_path.read_text(encoding="utf-8")
required_installation_commands = (
    "codex plugin marketplace add bartosz-cichecki/engineering-lens",
    "codex plugin add engineering-lens@engineering-lens-tools",
    "/plugin marketplace add bartosz-cichecki/engineering-lens",
    "/plugin install engineering-lens@engineering-lens-tools",
    "/reload-plugins",
)
for command in required_installation_commands:
    if command not in readme:
        error(f"README.md is missing installation command: {command}")
for obsolete_command in (
    "codex plugin marketplace add .",
    "claude plugin marketplace add .",
    "claude plugin install engineering-lens@engineering-lens-tools",
):
    if obsolete_command in readme:
        error(f"README.md still uses an obsolete installation command: {obsolete_command}")
for name in expected:
    codex_invocation = f"$engineering-lens:{name}"
    if codex_invocation not in readme:
        error(f"README.md is missing Codex invocation {codex_invocation}.")
    if f"/engineering-lens:{name}" not in readme:
        error(f"README.md is missing Claude Code invocation /engineering-lens:{name}.")

for automation_example_part in (
    "/engineering-lens:change-review-context --automation",
    "cat task-contract.md",
    "claude -p --permission-mode auto --no-session-persistence",
):
    if automation_example_part not in readme:
        error(
            "README.md is missing the minimal headless change-review-context "
            f"example part: {automation_example_part}"
        )

context_workflow_path = root / "skills" / "change-review-context" / "references" / "workflow.md"
review_workflow_path = root / "skills" / "change-review" / "references" / "workflow.md"
if context_workflow_path.is_file() and review_workflow_path.is_file():
    context_workflow = context_workflow_path.read_text(encoding="utf-8")
    review_workflow = review_workflow_path.read_text(encoding="utf-8")

    interactive_prompt = """Choose language / Wybierz język:

1. Polski
2. English"""
    interactive_requirements = (
        "In the interactive path, your first user-visible action must be to ask exactly:",
        interactive_prompt,
        "Stop and wait. Do not inspect the repository or ask another workflow question first.",
        "1. Uncommitted changes: staged, unstaged, and relevant untracked files.",
        "2. Last commit: the exact commit currently at `HEAD`.",
        "3. Current branch compared with a base branch.",
        "4. Pull request.",
        "Ask for exactly one work stage:",
        "- `WIP`\n- `Pre-commit`\n- `Pre-merge`",
        "Show included relevant paths and excluded paths with short reasons, and ask for confirmation.",
    )
    for requirement in interactive_requirements:
        if requirement not in context_workflow:
            error(
                "Interactive change-review-context behavior lost a required invariant: "
                f"{requirement.splitlines()[0]}"
            )

    automation_requirements = (
        "exact standalone token `--automation`",
        "Once automation mode is selected, never fall back to the interactive path.",
        "without asking a question, requesting confirmation, or waiting for user input",
        "Fix `Scope mode` to `uncommitted` and `Review stage` to `Pre-commit`.",
        "Classify every non-ignored untracked path",
        "Always exclude `.engineering-lens/change-review-context.md` from evaluated scope.",
        "Calculate the shared deterministic uncommitted fingerprint.",
        "do not create or replace the context file",
        "use its single format-version-1 schema",
    )
    for requirement in automation_requirements:
        if requirement not in context_workflow:
            error(
                "Automation change-review-context path is missing a required invariant: "
                f"{requirement}"
            )

    if context_workflow.count("# Change Review Context") != 1:
        error("Change review context schema must have a single shared definition.")
    if context_workflow.count("- Format version: 1") != 1:
        error("Change review context must retain its single format version 1 schema.")
    if "does not use format version `1`" not in review_workflow:
        error("Change review no longer requires the shared format version 1 context.")

markdown_files = [
    path for path in distribution_files()
    if path.suffix == ".md"
]
link_pattern = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
for path in markdown_files:
    text = path.read_text(encoding="utf-8")
    for raw_target in link_pattern.findall(text):
        target = raw_target.strip().split("#", 1)[0]
        if not target or "://" in target or target.startswith(("#", "mailto:")):
            continue
        candidate = (path.parent / target).resolve()
        try:
            candidate.relative_to(root)
        except ValueError:
            error(f"Local Markdown link escapes the plugin root: {path.relative_to(root)} -> {raw_target}")
            continue
        if not candidate.exists():
            error(f"Referenced local file does not exist: {path.relative_to(root)} -> {raw_target}")

workflow_files = [
    *root.glob("references/*.md"),
    *root.glob("skills/*/SKILL.md"),
    *root.glob("skills/*/references/*.md"),
    *root.glob("adapters/claude/skills/*/SKILL.md"),
]
workflow_text = "\n".join(path.read_text(encoding="utf-8") for path in workflow_files)
for forbidden in (
    ".claude/change-review-context.md",
    ".codex/change-review-context.md",
    ".claude/repo-assessment-context.md",
    ".codex/repo-assessment-context.md",
    ".claude/repo-assessment-report.md",
    ".codex/repo-assessment-report.md",
):
    if forbidden in workflow_text:
        error(f"Forbidden host-specific workflow state path found: {forbidden}")

if re.search(r"!\s*`?(?:git|cat)\b", workflow_text):
    error("Host-specific command interpolation was found in a shared workflow body.")

for state_name in (
    "change-review-context.md",
    "repo-assessment-context.md",
    "repo-assessment-report.md",
):
    for line in workflow_text.splitlines():
        if state_name in line and f".engineering-lens/{state_name}" not in line:
            error(f"Workflow state file is not under .engineering-lens/: {state_name}")
            break

for duplicate_dir in (root / "codex" / "skills", root / "claude" / "skills"):
    if duplicate_dir.exists():
        error(f"Duplicated host workflow directory is forbidden: {duplicate_dir.relative_to(root)}")

for path in root.glob("README.*.md"):
    error(f"Language-specific README variant is forbidden: {path.name}")

for path in distribution_files():
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        continue
    forbidden_acronym = "K" + "I" + "S" + "S"
    if forbidden_acronym.casefold() in text.casefold():
        error(f"Forbidden personal-philosophy wording found in {path.relative_to(root)}")

for forbidden_path in (
    ".mcp.json",
    ".lsp.json",
    "package.json",
    "package-lock.json",
    "pyproject.toml",
    "requirements.txt",
    "composer.json",
    "build.gradle",
):
    if (root / forbidden_path).exists():
        error(f"Forbidden dependency or integration file exists: {forbidden_path}")
for forbidden_dir in ("hooks", "agents", "mcp", "lsp"):
    if (root / forbidden_dir).exists():
        error(f"Forbidden top-level integration directory exists: {forbidden_dir}")

if errors:
    for message in errors:
        print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)

print("PASS: repository structure, manifests, skills, references, state paths, and invocation policies are valid.")
PY

PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s "$REPO_ROOT/tests" -v

if command -v claude >/dev/null 2>&1; then
  if claude plugin validate --help >/dev/null 2>&1; then
    printf 'INFO: Running official Claude Code strict marketplace validation.\n'
    claude plugin validate --strict "$REPO_ROOT"
  else
    printf 'SKIP: Claude Code CLI is present but plugin validation is unavailable.\n'
  fi
else
  printf 'SKIP: Claude Code CLI is unavailable; official Claude validation was not run.\n'
fi

if command -v codex >/dev/null 2>&1; then
  if codex plugin --help >/dev/null 2>&1; then
    printf 'SKIP: Codex CLI has no standalone plugin validation command; local Codex structure checks passed.\n'
  else
    printf 'SKIP: Codex CLI is present but its plugin command is unavailable.\n'
  fi
else
  printf 'SKIP: Codex CLI is unavailable; representative Codex loading was not run.\n'
fi

printf 'PASS: Engineering Lens validation completed.\n'
