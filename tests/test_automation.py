import base64
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from urllib.parse import quote

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location('automation', ROOT / 'scripts/automation.py')
a = importlib.util.module_from_spec(spec)
spec.loader.exec_module(a)


def context(states=None, reason='CONTEXT_CREATED'):
    value = a.failure('change-review-context', 'success' if reason == 'CONTEXT_CREATED' else 'rejected', reason)
    value['task_contract'] = states or dict.fromkeys(a.FIELDS, 'derived')
    return value


def review(verdict='READY'):
    value = a.failure('change-review', 'success', 'REVIEW_COMPLETED')
    value.update(verdict=verdict, verdict_rationale=a.RATIONALES[verdict])
    return value


def envelope(value, report='Human report with arbitrary formatting'):
    return json.dumps(dict(type='result', subtype='success', is_error=False,
                          result='Additional CLI commentary, not JSON.',
                          structured_output=dict(automation_result=value, human_report=report)))


class ResultTests(unittest.TestCase):
    def test_context_success(self):
        value = context()
        self.assertEqual(a.decode_cli(envelope(value), 0, value['operation'])[0], value)

    def test_missing_ambiguous_and_derived_preserved(self):
        states = dict(zip(a.FIELDS, ['derived', 'missing', 'ambiguous', 'derived']))
        value = context(states, 'TASK_CONTRACT_INCOMPLETE')
        self.assertEqual(a.decode_cli(envelope(value), 0, value['operation'])[0], value)

    def test_each_required_element_missing_or_ambiguous(self):
        for field in a.FIELDS:
            for state in ('missing', 'ambiguous'):
                with self.subTest(field=field, state=state):
                    states = dict.fromkeys(a.FIELDS, 'derived')
                    states[field] = state
                    value = context(states, 'TASK_CONTRACT_INCOMPLETE')
                    self.assertEqual(a.decode_cli(envelope(value), 0, value['operation'])[0], value)

    def test_empty_contract_and_language_rejection(self):
        for value in (context(dict.fromkeys(a.FIELDS, 'missing'), 'TASK_CONTRACT_INCOMPLETE'),
                      context(reason='LANGUAGE_UNSUPPORTED'), context(reason='BOUNDARY_UNRESOLVED')):
            self.assertEqual(a.decode_cli(envelope(value), 0, value['operation'])[0], value)

    def test_all_verdicts_independent_of_report(self):
        for verdict in ('READY', 'READY AFTER FIXES', 'NOT READY'):
            for report in ('# Dowolny polski raport\nUzasadnienie.', 'READY NOT READY READY AFTER FIXES', '{"verdict":"misleading"}'):
                with self.subTest(verdict=verdict, report=report):
                    value = review(verdict)
                    self.assertEqual(a.decode_cli(envelope(value, report), 0, 'change-review'), (value, report))

    def test_review_precondition_rejections(self):
        for reason in ('CONTEXT_INVALID', 'CONTEXT_STALE', 'BOUNDARY_UNRESOLVED'):
            value = a.failure('change-review', 'rejected', reason)
            self.assertEqual(a.decode_cli(envelope(value), 0, 'change-review')[0], value)

    def test_malformed_results_fail_closed(self):
        mutations = [
            {'format_version': 2}, {'format_version': True}, {'operation': 'wrong'},
            {'extra': 'secret'}, {'message': 'password=secret'}, {'task_contract': None},
            {'task_contract': dict.fromkeys(a.FIELDS, 'not_evaluated')},
            {'task_contract': dict.fromkeys(a.FIELDS, 'missing')},
            {'verdict': 'READY'}, {'status': 'rejected'},
        ]
        for mutation in mutations:
            value = context()
            value.update(mutation)
            with self.subTest(mutation=mutation):
                result, report = a.decode_cli(envelope(value), 0, 'change-review-context')
                self.assertEqual(result['status'], 'contract_error')
                self.assertIsNone(report)
        for raw in ('', 'not json', '[]', '{}', '{"type":"result","type":"result"}',
                    json.dumps(dict(type='result', subtype='success', is_error=False, result='READY'))):
            self.assertEqual(a.decode_cli(raw, 0, 'change-review')[0]['status'], 'contract_error')
        value = context()
        del value['message']
        self.assertEqual(a.decode_cli(envelope(value), 0, 'change-review-context')[0]['status'], 'contract_error')

    def test_invalid_verdicts_and_rationales(self):
        for changes in ({'verdict': ['READY', 'NOT READY']}, {'verdict': 'ready'},
                        {'verdict': None}, {'verdict_rationale': 'credential'},
                        {'verdict_rationale': a.RATIONALES['NOT READY']}):
            value = review()
            value.update(changes)
            self.assertEqual(a.decode_cli(envelope(value), 0, 'change-review')[0]['status'], 'contract_error')

    def test_structured_output_is_the_only_source(self):
        for value in (context(), review(),
                      context(dict(zip(a.FIELDS, ['derived', 'missing', 'ambiguous', 'derived'])),
                              'TASK_CONTRACT_INCOMPLETE'),
                      a.failure('change-review', 'rejected', 'CONTEXT_STALE')):
            operation = value['operation']
            payload = dict(automation_result=value, human_report='Full human report')
            for text in ('Extra commentary', json.dumps(payload),
                         '```json\n' + json.dumps(payload) + '\n```',
                         json.dumps(dict(automation_result=review('NOT READY'), human_report='Misleading'))):
                outer = json.loads(envelope(value, payload['human_report']))
                outer['result'] = text
                with self.subTest(operation=operation, status=value['status'], text=text):
                    self.assertEqual(a.decode_cli(json.dumps(outer), 0, operation),
                                     (value, payload['human_report']))
                    for invalid in (None, [], 'not JSON', json.dumps(payload), {},
                                    dict(payload, extra=True), dict(payload, human_report='  '),
                                    dict(payload, human_report=42), {'automation_result': value},
                                    {'human_report': 'Missing result'},
                                    dict(payload, automation_result=dict(value, operation='wrong'))):
                        outer['structured_output'] = invalid
                        self.assertEqual(a.decode_cli(json.dumps(outer), 0, operation),
                                         (a.failure(operation, 'contract_error', 'AUTOMATION_RESULT_INVALID'), None))
                    del outer['structured_output']
                    self.assertEqual(a.decode_cli(json.dumps(outer), 0, operation)[0]['status'], 'contract_error')
            outer = json.loads(envelope(value))
            del outer['result']
            self.assertEqual(a.decode_cli(json.dumps(outer), 0, operation)[0], value)

    def test_duplicate_keys_and_nonfinite_number(self):
        for value in (context(), review()):
            raw = envelope(value)
            for key, encoded in (('type', '"result"'), ('structured_output', '{}'),
                                 ('automation_result', '{}'), ('human_report', '"duplicate"'),
                                 ('format_version', '1'), ('verdict', 'null')):
                duplicate = raw.replace('"' + key + '":', '"' + key + '": ' + encoded + ', "' + key + '":', 1)
                with self.subTest(operation=value['operation'], key=key):
                    self.assertEqual(a.decode_cli(duplicate, 0, value['operation'])[0]['status'], 'contract_error')
            if value['task_contract']:
                duplicate = raw.replace('"goal_reason":', '"goal_reason": "derived", "goal_reason":', 1)
                self.assertEqual(a.decode_cli(duplicate, 0, value['operation'])[0]['status'], 'contract_error')
            self.assertEqual(a.decode_cli(raw.replace('"format_version": 1', '"format_version": NaN'),
                                          0, value['operation'])[0]['status'], 'contract_error')

    def test_invalid_envelope_with_valid_structured_output(self):
        for value in (context(), review()):
            for changes in ({'type': 'assistant'}, {'subtype': 'unknown'},
                            {'is_error': 0}, {'is_error': None}):
                outer = json.loads(envelope(value))
                outer.update(changes)
                with self.subTest(operation=value['operation'], changes=changes):
                    self.assertEqual(a.decode_cli(json.dumps(outer), 0, value['operation']),
                                     (a.failure(value['operation'], 'contract_error', 'AUTOMATION_RESULT_INVALID'), None))

    def test_technical_failure_and_native_retry_exhaustion(self):
        for value in (context(), review()):
            for raw, code in (('secret stderr substitute', 1), (envelope(value), 1),
                              (json.dumps(dict(type='result', subtype='error_during_execution', is_error=True)), 0)):
                result, report = a.decode_cli(raw, code, value['operation'])
                self.assertEqual(result['reason_code'], 'CLAUDE_FAILURE')
                self.assertIsNone(report)
            outer = json.loads(envelope(value))
            outer.update(subtype='error_max_structured_output_retries', is_error=True)
            for code in (0, 1):
                self.assertEqual(a.decode_cli(json.dumps(outer), code, value['operation']),
                                 (a.failure(value['operation'], 'contract_error', 'AUTOMATION_RESULT_INVALID'), None))

    def test_generated_failures_obey_schema(self):
        for operation in ('change-review', 'change-review-context'):
            for status, reason in (('contract_error', 'AUTOMATION_RESULT_INVALID'), ('technical_error', 'CLAUDE_FAILURE')):
                a.validate_result(a.failure(operation, status, reason), operation)


class RunnerTests(unittest.TestCase):
    def test_timeout_and_launch_failure_no_retry(self):
        for error in (FileNotFoundError('secret'), subprocess.TimeoutExpired('claude', 1)):
            with patch.object(a.subprocess, 'run', side_effect=error) as run:
                result, _ = a.run('change-review', '', 1)
                self.assertEqual(result['status'], 'technical_error')
                self.assertEqual(run.call_count, 1)
                self.assertNotIn('secret', json.dumps(result))

    def test_command_transport_and_exit_codes(self):
        # Real subprocess boundary with a deterministic fake CLI; no LLM calls.
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            fake = directory / 'claude'
            fake.write_text('''#!/usr/bin/env python3
import json, os, pathlib, sys
p = pathlib.Path(os.environ['FAKE_DIR'])
(p / 'calls').open('a').write('call\\n')
(p / 'args').write_text(json.dumps(sys.argv[1:]))
(p / 'input').write_text(sys.stdin.read())
sys.stdout.write((p / 'response').read_text())
sys.stderr.write('CLI diagnostic: ' + os.environ['ANTHROPIC_API_KEY'])
sys.exit(int(os.environ.get('FAKE_EXIT', '0')))
''')
            fake.chmod(0o755)
            env = dict(os.environ, PATH=tmp + os.pathsep + os.environ['PATH'], FAKE_DIR=tmp,
                       ANTHROPIC_API_KEY='credential-from-cli-must-not-be-forwarded')
            for value, raw, cli_code, expected_exit in (
                (review('READY'), None, 0, 0),
                (review('READY AFTER FIXES'), None, 0, 0),
                (review('NOT READY'), None, 0, 0),
                (a.failure('change-review', 'rejected', 'CONTEXT_STALE'), None, 0, 2),
                (None, 'malformed secret', 0, 3),
                (None, 'failure secret', 1, 4),
            ):
                (directory / 'response').write_text(envelope(value) if value else raw)
                done = subprocess.run([sys.executable, str(ROOT / 'scripts/automation.py'), 'change-review'],
                                      cwd=tmp, env=dict(env, FAKE_EXIT=str(cli_code)), capture_output=True, text=True)
                self.assertEqual(done.returncode, expected_exit, done.stderr)
                result = json.loads(done.stdout)
                a.validate_result(result, 'change-review')
                self.assertNotIn('secret', done.stdout)
                self.assertNotIn('credential-from-cli', done.stderr)
                self.assertIn('CLI diagnostic: [REDACTED]', done.stderr)
                if raw:
                    self.assertIn(raw, done.stderr)
                    self.assertNotIn(raw, done.stdout)
            self.assertEqual((directory / 'calls').read_text().splitlines(), ['call'] * 6)
            args = json.loads((directory / 'args').read_text())
            self.assertEqual(args[args.index('--plugin-dir') + 1], str(ROOT))
            self.assertEqual(args[args.index('--permission-mode') + 1], 'auto')
            self.assertNotIn('--model', args)
            self.assertNotIn('--effort', args)
            self.assertEqual(json.loads(args[args.index('--json-schema') + 1]), a.OUTPUT_SCHEMA)
            self.assertEqual(a.OUTPUT_SCHEMA['properties']['automation_result'], a.SCHEMA)
            self.assertEqual(a.OUTPUT_SCHEMA['required'], ['automation_result', 'human_report'])
            self.assertIs(a.OUTPUT_SCHEMA['additionalProperties'], False)
            self.assertIn('--output-format', args)
            self.assertEqual((directory / 'input').read_text(), '/engineering-lens:change-review')

    def test_orchestrator_options_and_credentials_across_real_process_boundary(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            fake = directory / 'claude'
            fake.write_text('''#!/usr/bin/env python3
import json, os, pathlib, sys
p = pathlib.Path(os.environ['FAKE_DIR'])
(p / 'args').write_text(json.dumps(sys.argv[1:]))
secret = os.environ['CLAUDE_CODE_OAUTH_TOKEN']
custom = os.environ['AGENTFLOW_INPUT']
settings = json.loads(pathlib.Path(sys.argv[sys.argv.index('--settings') + 1]).read_text())
(p / 'received').write_text('yes' if secret and custom else 'no')
payload = {'automation_result': {}, 'human_report': 'Detailed review diagnosis: ' + secret + ' ' + custom}
sys.stdout.write(json.dumps({'type': 'result', 'subtype': 'success', 'is_error': False, 'result': 'CLI commentary ' + secret, 'structured_output': payload}))
sys.stderr.write('CLI connection diagnosis: ' + secret + ' ' + custom + ' ' + settings['env']['ANTHROPIC_AUTH_TOKEN'])
sys.exit(int(os.environ['FAKE_EXIT']))
''')
            fake.chmod(0o755)
            settings_secret = 'settings-token-value'
            settings = directory / 'policy.json'
            settings.write_text(json.dumps({'env': {'ANTHROPIC_AUTH_TOKEN': settings_secret}}))
            secret = 'oauth-credential-"żółć"\nsecond-line'
            custom = 'custom-credential-value'
            env = dict(os.environ, PATH=tmp + os.pathsep + os.environ['PATH'], FAKE_DIR=tmp,
                       CLAUDE_CODE_OAUTH_TOKEN=secret, AGENTFLOW_INPUT=custom)
            supplied = ['--model', 'chosen-model', '--effort', 'high', '--permission-mode', 'dontAsk',
                        '--permission-prompts', 'none', '--allowedTools', 'Read', 'Bash(git *)',
                        '--disallowedTools', 'Bash(git push *)', '--tools', 'Read,Bash',
                        '--settings', str(settings), '--setting-sources', '', '--redact-env', 'AGENTFLOW_INPUT']
            for cli_exit, runner_exit, status in ((0, 3, 'contract_error'), (1, 4, 'technical_error')):
                done = subprocess.run([sys.executable, str(ROOT / 'scripts/automation.py'), 'change-review', *supplied],
                                      cwd=tmp, env=dict(env, FAKE_EXIT=str(cli_exit)), capture_output=True, text=True)
                self.assertEqual(done.returncode, runner_exit, done.stderr)
                result = json.loads(done.stdout)
                self.assertEqual(result['status'], status)
                self.assertEqual(len(done.stdout.splitlines()), 1)
                self.assertIn('Detailed review diagnosis:', done.stderr)
                self.assertIn('CLI connection diagnosis:', done.stderr)
                self.assertIn('[REDACTED]', done.stderr)
                for credential in (secret, custom, settings_secret):
                    self.assertNotIn(credential, done.stdout + done.stderr)
                    self.assertNotIn(json.dumps(credential)[1:-1], done.stdout + done.stderr)
                    self.assertNotIn(json.dumps(json.dumps(credential)[1:-1])[1:-1], done.stdout + done.stderr)
                self.assertNotIn('diagnosis', done.stdout)
                args = json.loads((directory / 'args').read_text())
                self.assertEqual(args[args.index('--plugin-dir') + 1], str(ROOT))
                # Everything except runner-only redaction controls is forwarded verbatim.
                forwarded = supplied[:-2]
                offset = args.index('--permission-mode')
                self.assertEqual(args[offset:offset + 2], ['--permission-mode', 'dontAsk'])
                for flag in ('--model', '--effort', '--permission-prompts', '--settings', '--setting-sources'):
                    self.assertEqual(args[args.index(flag) + 1], forwarded[forwarded.index(flag) + 1])
                self.assertEqual(args[args.index('--allowedTools') + 1:args.index('--disallowedTools')], ['Read', 'Bash(git *)'])
                self.assertEqual(args[args.index('--disallowedTools') + 1:args.index('--tools')], ['Bash(git push *)'])
                self.assertEqual(args[args.index('--tools') + 1], 'Read,Bash')
                self.assertEqual((directory / 'received').read_text(), 'yes')
                self.assertNotIn('--redact-env', args)

    def test_policy_inheritance_bypass_and_empty_tools(self):
        for flags, present, absent in (
            (['--permission-mode', 'inherit', '--tools', ''], ['--tools', ''], '--permission-mode'),
            (['--dangerously-skip-permissions'], ['--dangerously-skip-permissions'], '--permission-mode'),
        ):
            with patch.object(sys, 'argv', ['automation.py', 'change-review', *flags]), \
                 patch.object(a, 'run', return_value=(review(), None)) as run, \
                 patch('builtins.print'):
                self.assertEqual(a.main(), 0)
                options = run.call_args.kwargs['options']
                self.assertEqual(options, present)
                self.assertNotIn(absent, options)

    def test_timeout_keeps_partial_diagnostics_without_credentials(self):
        secret = 'timeout-secret-value'
        error = subprocess.TimeoutExpired(['claude', 'never-log-argv'], 1,
                                          output=('Progress before timeout ' + secret).encode(),
                                          stderr=('CLI timeout detail ' + secret).encode())
        with patch.object(a.subprocess, 'run', side_effect=error) as run:
            result, diagnostics = a.run('change-review', '', 1, diagnostics=a.Diagnostics({'ANTHROPIC_API_KEY': secret}))
        self.assertEqual(result['status'], 'technical_error')
        self.assertIn('Progress before timeout [REDACTED]', diagnostics)
        self.assertIn('CLI timeout detail [REDACTED]', diagnostics)
        self.assertNotIn(secret, diagnostics)
        self.assertNotIn('never-log-argv', diagnostics)
        self.assertEqual(run.call_count, 1)

    def test_success_report_is_redacted_too(self):
        secret = 'success-secret-value'
        completed = subprocess.CompletedProcess([], 0, envelope(review(), 'Report ' + secret), 'Warning ' + secret)
        with patch.object(a.subprocess, 'run', return_value=completed):
            result, diagnostics = a.run('change-review', '', 1, diagnostics=a.Diagnostics({'AUTH_TOKEN': secret}))
        self.assertEqual(result, review())
        self.assertIn('Report [REDACTED]', diagnostics)
        self.assertIn('Warning [REDACTED]', diagnostics)

    def test_structured_and_encoded_credential_inputs_are_redacted(self):
        secret = 'opaque-token/with+encoding="ż"'
        blob = json.dumps({'accessToken': secret, 'refreshToken': 'refresh-value'})
        diagnostics = a.Diagnostics({'CLAUDE_CREDENTIALS': blob})
        for form in (secret, blob, json.dumps(secret)[1:-1], quote(secret, safe=''),
                     base64.b64encode(secret.encode()).decode()):
            with self.subTest(form=form):
                self.assertEqual(diagnostics.clean('Diagnostic: ' + form), 'Diagnostic: [REDACTED]')
        inline_settings = json.dumps({'env': {'ANTHROPIC_API_KEY': secret}, 'apiKeyHelper': 'sensitive-helper-input'})
        diagnostics = a.Diagnostics({}, settings=inline_settings)
        self.assertEqual(diagnostics.clean(secret + ' sensitive-helper-input'), '[REDACTED] [REDACTED]')

    def test_usage_errors_do_not_echo_input_or_allow_transport_override(self):
        for extra in (['--unknown', 'credential-input'], ['--timeout', 'credential-input'],
                      ['--output-format', 'text'], ['--plugin-dir', '/another/plugin']):
            done = subprocess.run([sys.executable, str(ROOT / 'scripts/automation.py'), 'change-review', *extra],
                                  capture_output=True, text=True)
            self.assertEqual(done.returncode, 2)
            self.assertEqual(done.stdout, '')
            self.assertNotIn('credential-input', done.stderr)
            self.assertNotIn('/another/plugin', done.stderr)

    def test_context_success_saves_existing_format_and_rejection_preserves_it(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(a.Path, 'cwd', return_value=Path(tmp)):
            path = Path(tmp) / '.engineering-lens/change-review-context.md'
            path.parent.mkdir()
            # Instantiate the existing documented context format, including all metadata.
            workflow = (ROOT / 'skills/change-review-context/references/workflow.md').read_text()
            fixture = workflow.split('```markdown\n', 1)[1].split('```', 1)[0]
            replacements = {
                'English | Polish': 'English', 'WIP | Pre-commit | Pre-merge': 'Pre-commit',
                '<canonical absolute path>': str(Path(tmp).resolve()),
                'uncommitted | last-commit | branch | pull-request': 'uncommitted',
                'commit | empty-tree': 'commit', '<full SHA or Not applicable>': 'Not applicable',
                '<entered ref or Not applicable>': 'Not applicable', '<identifier or Not applicable>': 'Not applicable',
                '<algorithm or Not applicable>': 'sha256; ordered baseline, staged, unstaged, untracked',
                '<value or Not applicable>': 'a' * 64, '<path or None>': 'example.py',
                '<path — reason or None>': 'None', '<what should change and why>': 'Add validation to reject invalid results.',
                '<explicit exclusions or None declared>': 'None declared', '<observable criterion>': 'Invalid results fail.',
                '<risk or constraint, or None declared>': 'None declared',
            }
            for old, new in replacements.items():
                fixture = fixture.replace(old, new)
            fixture = fixture.replace('- Baseline commit: Not applicable', '- Baseline commit: ' + 'b' * 40)

            def save(*args, **kwargs):
                self.assertIn('--automation\n\nfull task contract', kwargs['input'])
                argv = args[0]
                self.assertEqual(json.loads(argv[argv.index('--json-schema') + 1]), a.OUTPUT_SCHEMA)
                path.write_text(fixture)
                return subprocess.CompletedProcess([], 0, envelope(context()), '')

            with patch.object(a.subprocess, 'run', side_effect=save) as call:
                result, report = a.run('change-review-context', 'full task contract', 1)
                self.assertEqual(result, context())
                self.assertIsNotNone(report)
                self.assertEqual(call.call_count, 1)
            before = path.read_bytes()
            rejected = context(dict.fromkeys(a.FIELDS, 'missing'), 'TASK_CONTRACT_INCOMPLETE')
            with patch.object(a.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, envelope(rejected), '')):
                result, _ = a.run('change-review-context', '', 1)
                self.assertEqual(result, rejected)
                self.assertEqual(path.read_bytes(), before)
            with patch.object(a.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, envelope(context()), '')):
                result, _ = a.run('change-review-context', 'contract', 1)
                self.assertEqual(result['status'], 'contract_error')  # stale file is not proof of success

    def test_rejection_after_write_is_contract_error(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(a.Path, 'cwd', return_value=Path(tmp)):
            path = Path(tmp) / '.engineering-lens/change-review-context.md'
            path.parent.mkdir()
            def invalid_write(*args, **kwargs):
                path.write_text('unexpected mutation')
                rejected = context(dict.fromkeys(a.FIELDS, 'missing'), 'TASK_CONTRACT_INCOMPLETE')
                return subprocess.CompletedProcess([], 0, envelope(rejected), '')
            with patch.object(a.subprocess, 'run', side_effect=invalid_write):
                self.assertEqual(a.run('change-review-context', '', 1)[0]['status'], 'contract_error')

    def test_context_artifact_required(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(a.Path, 'cwd', return_value=Path(tmp)):
            with patch.object(a.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, envelope(context()), '')):
                result, diagnostics = a.run('change-review-context', 'contract', 1)
                self.assertEqual(result['status'], 'contract_error')
                self.assertIn('Context artifact was not saved correctly.', diagnostics)
                self.assertIn('Human report with arbitrary formatting', diagnostics)


if __name__ == '__main__':
    unittest.main()
