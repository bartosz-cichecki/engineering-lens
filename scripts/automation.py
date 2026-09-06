#!/usr/bin/env python3
"""One Claude invocation, deterministic validation, one secret-free stdout result."""
import argparse
import base64
import json
import os
import re
from pathlib import Path
import subprocess
import sys
from urllib.parse import quote, quote_plus

ROOT = Path(__file__).resolve().parent.parent
SCHEMA = json.loads((ROOT / 'references/automation-result-v1.schema.json').read_text())
OUTPUT_SCHEMA = {
    'type': 'object',
    'properties': {'automation_result': SCHEMA, 'human_report': {'type': 'string', 'minLength': 1}},
    'required': ['automation_result', 'human_report'],
    'additionalProperties': False,
}
FIELDS = tuple(SCHEMA['properties']['task_contract']['anyOf'][1]['required'])
MESSAGES = dict(zip(SCHEMA['properties']['reason_code']['enum'], SCHEMA['properties']['message']['enum']))
RATIONALES = dict(zip(SCHEMA['properties']['verdict']['enum'], SCHEMA['properties']['verdict_rationale']['enum']))
EXIT_CODES = {'success': 0, 'rejected': 2, 'contract_error': 3, 'technical_error': 4}


def strict_json(text):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError('Duplicate key')
            result[key] = value
        return result
    def invalid_constant(value):
        raise ValueError('Invalid JSON constant')
    return json.loads(text, object_pairs_hook=pairs, parse_constant=invalid_constant)


def validate_schema(value, schema):
    """Validate the small, closed vocabulary used by the shipped schema."""
    if 'anyOf' in schema:
        for branch in schema['anyOf']:
            try:
                validate_schema(value, branch)
                return
            except ValueError:
                pass
        raise ValueError('No matching branch')
    if 'const' in schema and (type(value) is not type(schema['const']) or value != schema['const']):
        raise ValueError('Invalid constant')
    if 'enum' in schema and not any(type(value) is type(item) and value == item for item in schema['enum']):
        raise ValueError('Invalid enum')
    if schema.get('type') == 'null' and value is not None:
        raise ValueError('Expected null')
    if schema.get('type') == 'object':
        if not isinstance(value, dict) or set(value) != set(schema['required']):
            raise ValueError('Invalid object fields')
        for key, child in schema['properties'].items():
            validate_schema(value[key], child)


def failure(operation, status, reason):
    return dict(format_version=1, operation=operation, status=status, reason_code=reason,
                message=MESSAGES[reason], task_contract=({field: 'not_evaluated' for field in FIELDS}
                if operation == 'change-review-context' else None), verdict=None, verdict_rationale=None)


def validate_result(value, operation, from_model=False):
    validate_schema(value, SCHEMA)
    if value['operation'] != operation or value['message'] != MESSAGES[value['reason_code']]:
        raise ValueError('Operation or message mismatch')
    status, reason = value['status'], value['reason_code']
    allowed = {
        'success': {'CONTEXT_CREATED'} if operation == 'change-review-context' else {'REVIEW_COMPLETED'},
        'rejected': {'TASK_CONTRACT_INCOMPLETE', 'LANGUAGE_UNSUPPORTED', 'BOUNDARY_UNRESOLVED'}
                    if operation == 'change-review-context' else {'CONTEXT_INVALID', 'CONTEXT_STALE', 'BOUNDARY_UNRESOLVED'},
        'contract_error': {'AUTOMATION_RESULT_INVALID'},
        'technical_error': {'CLAUDE_FAILURE'},
    }
    if reason not in allowed[status] or (from_model and status in ('contract_error', 'technical_error')):
        raise ValueError('Status mismatch')
    states = value['task_contract']
    if operation == 'change-review-context':
        if states is None:
            raise ValueError('Missing Task Contract states')
        if status in ('contract_error', 'technical_error') and set(states.values()) != {'not_evaluated'}:
            raise ValueError('Unexpected error assessment')
        if status in ('success', 'rejected') and 'not_evaluated' in states.values():
            raise ValueError('Incomplete assessment')
        incomplete = any(state in ('missing', 'ambiguous') for state in states.values())
        if status in ('success', 'rejected') and incomplete != (reason == 'TASK_CONTRACT_INCOMPLETE'):
            raise ValueError('Task Contract inconsistency')
    elif states is not None:
        raise ValueError('Unexpected Task Contract states')
    if operation == 'change-review' and status == 'success':
        if value['verdict'] is None or value['verdict_rationale'] != RATIONALES[value['verdict']]:
            raise ValueError('Invalid verdict')
    elif value['verdict'] is not None or value['verdict_rationale'] is not None:
        raise ValueError('Unexpected verdict')
    return value


def decode_cli(stdout, returncode, operation):
    contract_error = failure(operation, 'contract_error', 'AUTOMATION_RESULT_INVALID')
    technical_error = failure(operation, 'technical_error', 'CLAUDE_FAILURE')
    try:
        envelope = strict_json(stdout)
    except (ValueError, TypeError):
        return (technical_error if returncode else contract_error), None
    if not isinstance(envelope, dict):
        return (technical_error if returncode else contract_error), None
    if envelope.get('type') == 'result' and envelope.get('subtype') == 'error_max_structured_output_retries':
        return contract_error, None
    if returncode or envelope.get('is_error') is True:
        return technical_error, None
    if envelope.get('type') != 'result' or envelope.get('subtype') != 'success' or envelope.get('is_error') is not False:
        return contract_error, None
    try:
        payload = envelope['structured_output']
        if not isinstance(payload, dict) or set(payload) != {'automation_result', 'human_report'}:
            raise ValueError('Invalid payload')
        if not isinstance(payload['human_report'], str) or not payload['human_report'].strip():
            raise ValueError('Missing human report')
        value = validate_result(payload['automation_result'], operation, from_model=True)
        return value, payload['human_report']
    except (KeyError, ValueError, TypeError):
        return contract_error, None


def context_snapshot(path):
    if not path.exists():
        return None
    stat = path.stat()
    return (stat.st_mtime_ns, stat.st_ctime_ns, path.read_bytes())


def check_context(path, before):
    after = context_snapshot(path)
    if after is None or after == before or path.is_symlink():
        raise ValueError('Context was not saved')
    content = after[2].decode('utf-8')
    required = ['# Change Review Context', '- Format version: 1',
                '- Scope mode: uncommitted', '- Review stage: Pre-commit',
                f'- Repository root: {Path.cwd().resolve()}',
                '## Scope paths', '### Staged', '### Unstaged',
                '### Included relevant untracked', '### Excluded untracked',
                '## Goal', '## Intentionally excluded', '## Completion criteria',
                '## Risks and external constraints']
    lines = content.splitlines()
    if any(lines.count(line) != 1 for line in required):
        raise ValueError('Invalid context artifact')
    metadata = {}
    for line in content.split('## Scope paths', 1)[0].splitlines():
        if line.startswith('- '):
            key, separator, value = line[2:].partition(': ')
            if not separator or not value.strip() or key in metadata:
                raise ValueError('Invalid metadata')
            metadata[key] = value
    expected = {'Format version', 'Language', 'Review stage', 'Repository root',
                'Scope mode', 'Baseline kind', 'Baseline commit', 'Target commit',
                'Base ref', 'Base ref commit', 'Merge-base commit', 'Pull request',
                'Snapshot fingerprint algorithm', 'Snapshot fingerprint'}
    if set(metadata) != expected or metadata['Language'] not in ('English', 'Polish'):
        raise ValueError('Invalid metadata fields')
    if metadata['Baseline kind'] not in ('commit', 'empty-tree'):
        raise ValueError('Invalid baseline kind')
    if metadata['Baseline kind'] == 'commit':
        if not re.fullmatch('[0-9a-f]{40}', metadata['Baseline commit']):
            raise ValueError('Invalid baseline')
    elif metadata['Baseline commit'] != 'Not applicable':
        raise ValueError('Invalid empty baseline')
    for key in ('Target commit', 'Base ref', 'Base ref commit', 'Merge-base commit', 'Pull request'):
        if metadata[key] != 'Not applicable':
            raise ValueError('Unexpected committed boundary')
    for key in ('Snapshot fingerprint algorithm', 'Snapshot fingerprint'):
        if metadata[key] == 'Not applicable' or '<' in metadata[key]:
            raise ValueError('Missing fingerprint')
    for heading in required[6:]:
        section = content.split(heading + '\n', 1)[1]
        body = re.split(r'(?m)^#{2,3} ', section, maxsplit=1)[0].strip()
        if heading != '## Scope paths' and (not body or re.search(r'<[^>]+>', body)):
            raise ValueError('Empty or placeholder context section')


SENSITIVE_NAME = re.compile(r'token|secret|password|passwd|credential|api.?key|access.?key|private.?key|auth|cookie', re.I)


class Diagnostics:
    """Redact known credential inputs before any human output leaves the runner."""

    def __init__(self, environ, secret_env=(), settings=None):
        self.secrets = set()
        for name, value in environ.items():
            if SENSITIVE_NAME.search(name) or name in secret_env:
                self.add(value)
        if settings is not None:
            # Settings may contain env credentials or an apiKeyHelper. Never log
            # the credential-bearing input itself, including on read/parse errors.
            self.add(settings, expand_json=False)
            try:
                raw = settings if settings.lstrip().startswith('{') else Path(settings).read_text()
                self.add(raw, expand_json=False)
                self.collect_settings(strict_json(raw))
            except (OSError, ValueError, UnicodeError):
                pass  # CLI owns settings validation; do not expose exception input.

    def add(self, value, expand_json=True):
        if not isinstance(value, str) or not value:
            return
        self.secrets.add(value)
        if value.startswith(('Bearer ', 'Basic ')) and value.split(' ', 1)[1]:
            self.secrets.add(value.split(' ', 1)[1])
        if expand_json:
            try:
                parsed = strict_json(value)
            except (ValueError, TypeError):
                return
            self.collect_values(parsed)

    def collect_values(self, value):
        if isinstance(value, str):
            self.add(value, expand_json=False)
        elif isinstance(value, dict):
            for child in value.values():
                self.collect_values(child)
        elif isinstance(value, list):
            for child in value:
                self.collect_values(child)

    def collect_settings(self, value):
        if isinstance(value, dict):
            for name, child in value.items():
                if SENSITIVE_NAME.search(name):
                    self.collect_values(child)
                else:
                    self.collect_settings(child)
        elif isinstance(value, list):
            for child in value:
                self.collect_settings(child)

    def clean(self, text):
        if isinstance(text, bytes):
            text = text.decode('utf-8', errors='replace')
        if not text:
            return ''
        variants = set()
        for secret in self.secrets:
            variants.update((secret, quote(secret, safe=''), quote_plus(secret),
                             base64.b64encode(secret.encode()).decode(),
                             base64.urlsafe_b64encode(secret.encode()).decode()))
            for ascii_only in (True, False):
                escaped = secret
                for _ in range(2):  # JSON payload nested inside the CLI JSON envelope
                    escaped = json.dumps(escaped, ensure_ascii=ascii_only)[1:-1]
                    variants.add(escaped)
        # One pass: short secrets must not corrupt replacement markers.
        if variants:
            text = re.sub('|'.join(re.escape(v) for v in sorted(variants, key=len, reverse=True)),
                          '[REDACTED]', text)
        return text

    def render(self, *parts):
        return '\n'.join(self.clean(part) for part in parts if part) or None


def execution_options(args):
    options = []
    if args.dangerously_skip_permissions:
        options.append('--dangerously-skip-permissions')
    elif args.permission_mode != 'inherit':
        options.extend(['--permission-mode', args.permission_mode])
    for name in ('model', 'effort', 'settings', 'setting_sources', 'permission_prompts'):
        value = getattr(args, name)
        if value is not None:
            options.extend(['--' + name.replace('_', '-'), value])
    for name, flag in (('allowed_tools', '--allowedTools'), ('disallowed_tools', '--disallowedTools'), ('tools', '--tools')):
        value = getattr(args, name)
        if value is not None:
            options.extend([flag, *value])
    return options


def run(operation, contract, timeout, *, options=None, diagnostics=None):
    diagnostics = diagnostics or Diagnostics(os.environ)
    path = Path.cwd() / '.engineering-lens/change-review-context.md'
    completed = None
    try:
        if operation == 'change-review-context' and (path.is_symlink() or path.parent.is_symlink()):
            return failure(operation, 'contract_error', 'AUTOMATION_RESULT_INVALID'), 'Context path is a symlink.'
        before = context_snapshot(path) if operation == 'change-review-context' else None
        instructions = (ROOT / 'references/automation-result.md').read_text()
        instructions += '\nAUTOMATION TRANSPORT ACTIVE. Submit automation_result and human_report '
        instructions += 'through the CLI schema-constrained structured output. '
        instructions += 'The text result is diagnostic only and cannot supply the automation result.'
        prompt = '/engineering-lens:' + operation
        if operation == 'change-review-context':
            prompt += ' --automation\n\n' + contract
        completed = subprocess.run(
            ['claude', '-p', '--plugin-dir', str(ROOT),
             *(options if options is not None else ['--permission-mode', 'auto']),
             '--no-session-persistence', '--output-format', 'json',
             '--json-schema', json.dumps(OUTPUT_SCHEMA), '--append-system-prompt', instructions],
            input=prompt, text=True, encoding='utf-8', errors='replace', capture_output=True, timeout=timeout,
        )
        result, report = decode_cli(completed.stdout, completed.returncode, operation)
        artifact_error = None
        if operation == 'change-review-context' and result['status'] == 'rejected' and context_snapshot(path) != before:
            artifact_error = 'Context changed during semantic rejection.'
        if result['status'] == 'success' and operation == 'change-review-context':
            try:
                check_context(path, before)
            except (OSError, UnicodeError, ValueError):
                artifact_error = 'Context artifact was not saved correctly.'
        if artifact_error:
            result = failure(operation, 'contract_error', 'AUTOMATION_RESULT_INVALID')
        if result['status'] in ('contract_error', 'technical_error'):
            report = diagnostics.render(result['message'], artifact_error,
                                        f'Claude exit code: {completed.returncode}',
                                        'Claude stdout:\n' + completed.stdout if completed.stdout else None,
                                        'Claude stderr:\n' + completed.stderr if completed.stderr else None)
        else:
            report = diagnostics.render(report, 'Claude stderr:\n' + completed.stderr if completed.stderr else None)
        return result, report
    except subprocess.TimeoutExpired as exc:
        return failure(operation, 'technical_error', 'CLAUDE_FAILURE'), diagnostics.render(
            'Claude timed out.', exc.stdout, exc.stderr)
    except (OSError, subprocess.SubprocessError, UnicodeError) as exc:
        # Never stringify a subprocess exception: it can contain argv/input.
        return failure(operation, 'technical_error', 'CLAUDE_FAILURE'), diagnostics.render(
            'Claude execution or runner I/O failed (' + type(exc).__name__ + ').',
            completed.stdout if completed else None, completed.stderr if completed else None)


class RunnerParser(argparse.ArgumentParser):
    def error(self, message):
        # argparse's normal errors echo arbitrary argument values (possibly secrets).
        super().error('Invalid runner arguments; use --help for supported options.')


def main():
    parser = RunnerParser(description=__doc__, allow_abbrev=False)
    parser.add_argument('operation', choices=['change-review-context', 'change-review'])
    parser.add_argument('--automation', action='store_true', help='Required for context; Task Contract is read from stdin')
    parser.add_argument('--timeout', type=int, default=900, help='CLI timeout in seconds')
    parser.add_argument('--model', help='Forward Claude model alias or ID unchanged')
    parser.add_argument('--effort', help='Forward Claude effort unchanged')
    policy = parser.add_mutually_exclusive_group()
    policy.add_argument('--permission-mode', default='auto', help='Claude permission mode; inherit omits the flag')
    policy.add_argument('--dangerously-skip-permissions', action='store_true')
    parser.add_argument('--permission-prompts', help='Forward Claude print-mode permission prompt policy')
    parser.add_argument('--allowedTools', '--allowed-tools', dest='allowed_tools', nargs='+', action='extend')
    parser.add_argument('--disallowedTools', '--disallowed-tools', dest='disallowed_tools', nargs='+', action='extend')
    parser.add_argument('--tools', nargs='+', action='extend', help='Claude tool set; use an empty string for none')
    parser.add_argument('--settings', help='Claude settings file path or JSON, passed unchanged')
    parser.add_argument('--setting-sources', help='Claude settings sources, passed unchanged')
    parser.add_argument('--redact-env', action='append', default=[], metavar='NAME',
                        help='Also redact the value of this inherited environment variable (repeatable)')
    args = parser.parse_args()
    if args.timeout <= 0 or (args.operation == 'change-review-context' and not args.automation):
        parser.error('Use a positive timeout and --automation for context')
    diagnostics = Diagnostics(os.environ, args.redact_env, args.settings)
    try:
        contract = sys.stdin.read() if args.operation == 'change-review-context' else ''
        result, report = run(args.operation, contract, args.timeout,
                             options=execution_options(args), diagnostics=diagnostics)
    except (OSError, UnicodeError):
        result = failure(args.operation, 'technical_error', 'CLAUDE_FAILURE')
        report = 'Runner could not read Task Contract input.'
    # No CLI metadata, arbitrary model strings, input, paths, or exception text on stdout.
    validate_result(result, args.operation)
    print(json.dumps(result, ensure_ascii=True))
    if report:
        print(report, file=sys.stderr)
    return EXIT_CODES[result['status']]


if __name__ == '__main__':
    sys.exit(main())
