import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))
import review_snapshot as s


def git(root, *args):
    return subprocess.run(['git', '-C', str(root), *args], check=True, capture_output=True).stdout.decode().strip()


def init_repo(root):
    git(root, 'init', '-q')
    git(root, 'config', 'user.name', 'Test')
    git(root, 'config', 'user.email', 'test@example.invalid')
    (root / '.gitignore').write_text('.engineering-lens/\nignored\n')
    (root / 'code.py').write_text('original\n')
    git(root, 'add', '.')
    git(root, 'commit', '-qm', 'initial')


def request(**changes):
    data = dict(language='English', stage='Pre-commit', mode='uncommitted',
                intent=dict(zip(s.INTENT, ['Validate inputs to protect callers.', 'Successful responses.',
                                          'Invalid inputs fail.', 'None declared'])))
    data.update(changes)
    return data


class SnapshotTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        init_repo(self.root)

    def create(self, **changes):
        return s.create(self.root, request(**changes))

    def stale(self):
        with self.assertRaises(s.SnapshotError) as raised:
            s.verify(self.root)
        self.assertEqual(raised.exception.reason, 'CONTEXT_STALE')

    def test_repeatable_creation_and_verification_without_git_writes(self):
        (self.root / 'code.py').write_bytes(b'staged\x00binary')
        git(self.root, 'add', 'code.py')
        (self.root / 'code.py').write_bytes(b'unstaged\x00binary')
        index = (self.root / '.git/index').read_bytes()
        first = self.create()
        saved = (self.root / s.CONTEXT).read_bytes()
        self.assertEqual(s.verify(self.root), first)
        self.assertEqual(self.create(), first)
        self.assertEqual((self.root / s.CONTEXT).read_bytes(), saved)
        self.assertEqual((self.root / '.git/index').read_bytes(), index)
        _, paths, _ = s.read_context(self.root)
        self.assertEqual(paths['Staged'], ['code.py'])
        self.assertEqual(paths['Unstaged'], ['code.py'])

    def test_each_raw_state_and_baseline_drift(self):
        for mutation in ('working', 'index', 'head', 'mode', 'delete'):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                init_repo(root)
                s.create(root, request())
                if mutation == 'mode':
                    (root / 'code.py').chmod(0o755)
                elif mutation == 'delete':
                    (root / 'code.py').unlink()
                elif mutation == 'head':
                    git(root, 'commit', '--allow-empty', '-qm', 'move')
                else:
                    (root / 'code.py').write_text('modified\n')
                    if mutation == 'index':
                        git(root, 'add', 'code.py')
                        (root / 'code.py').write_text('original\n')
                with self.assertRaises(s.SnapshotError) as raised:
                    s.verify(root)
                self.assertEqual(raised.exception.reason, 'CONTEXT_STALE')

    def test_untracked_inventory_and_excluded_contents(self):
        (self.root / 'included').write_bytes(b'one\x00')
        (self.root / 'excluded').write_text('notes')
        self.create(included_untracked=['included'], excluded_untracked={'excluded': 'Out of scope'})
        (self.root / 'excluded').write_text('new notes')
        (self.root / 'ignored').write_text('ignored')
        s.verify(self.root)
        (self.root / 'included').write_bytes(b'two\x00')
        self.stale()
        (self.root / 'included').write_bytes(b'one\x00')
        (self.root / 'new').write_text('new')
        self.stale()
        (self.root / 'new').unlink()
        (self.root / 'excluded').unlink()
        self.stale()

    def test_path_roundtrip_and_symlink_targets(self):
        names = ['space name', 'tab\tname', 'line\nname', '-option', 'żółć', '$(echo unsafe)']
        for name in names:
            (self.root / name).write_text('content')
        (self.root / 'link').symlink_to('/outside/one')
        self.create(included_untracked=names + ['link'])
        _, paths, _ = s.read_context(self.root)
        self.assertEqual(paths['Included relevant untracked'], sorted(names + ['link']))
        s.verify(self.root)
        (self.root / 'link').unlink()
        (self.root / 'link').symlink_to('/outside/two')
        self.stale()

    def test_diff_config_and_clean_filter_do_not_affect_fingerprint(self):
        (self.root / '.gitattributes').write_text('code.py filter=broken diff=broken\n')
        git(self.root, 'add', '.gitattributes')
        git(self.root, 'config', 'filter.broken.clean', '/not/a/program')
        git(self.root, 'config', 'filter.broken.required', 'true')
        git(self.root, 'config', 'diff.broken.textconv', '/not/a/program')
        before = self.create()
        for key, value in [('diff.algorithm', 'patience'), ('diff.renames', 'true'),
                           ('core.autocrlf', 'true'), ('core.filemode', 'false'),
                           ('diff.external', '/not/a/program')]:
            git(self.root, 'config', key, value)
        self.assertEqual(s.verify(self.root), before)
        self.assertEqual(self.create(), before)

    def test_context_is_excluded_even_when_tracked(self):
        self.create()
        git(self.root, 'add', '-f', s.CONTEXT)
        git(self.root, 'commit', '-qm', 'track context')
        self.create()
        first = s.verify(self.root)
        git(self.root, 'add', '-f', s.CONTEXT)
        self.assertEqual(s.verify(self.root), first)

    def test_unborn_and_root_commit(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            git(root, 'init', '-q')
            (root / 'new').write_text('addition')
            git(root, 'add', 'new')
            value = s.create(root, request())
            self.assertEqual(value['Baseline kind'], 'empty-tree')
            s.verify(root)  # writing context does not change untracked inventory
        value = self.create(mode='last-commit')
        self.assertEqual(value['Baseline kind'], 'empty-tree')
        s.verify(self.root)

    def test_committed_scopes_ignore_ref_and_worktree_movement(self):
        base = git(self.root, 'rev-parse', 'HEAD')
        (self.root / 'code.py').write_text('second')
        git(self.root, 'commit', '-qam', 'second')
        for mode in ('last-commit', 'branch', 'pull-request'):
            with self.subTest(mode=mode):
                self.create(mode=mode, base=base, target='HEAD', pull_request='123')
                (self.root / 'code.py').write_text('later change')
                git(self.root, 'commit', '--allow-empty', '-qam', 'later')
                (self.root / 'untracked').write_text('outside committed scope')
                s.verify(self.root)

    def test_invalid_classification_and_unsafe_paths_leave_context_untouched(self):
        self.create()
        before = (self.root / s.CONTEXT).read_bytes()
        for included in (['../escape'], ['/absolute'], [s.CONTEXT], ['missing'], ['x', 'x']):
            with self.subTest(included=included), self.assertRaises(s.SnapshotError):
                self.create(included_untracked=included)
            self.assertEqual((self.root / s.CONTEXT).read_bytes(), before)
        (self.root / 'unknown').write_text('needs classification')
        with self.assertRaises(s.SnapshotError):
            self.create()
        self.assertEqual((self.root / s.CONTEXT).read_bytes(), before)

    def test_unsupported_algorithm_tampered_paths_and_repository(self):
        self.create()
        path = self.root / s.CONTEXT
        before = path.read_text()
        for old, new, reason in [(s.ALGORITHM, 'sha256 invented by model', 'CONTEXT_INVALID'),
                                 (str(self.root), '/different/repo', 'CONTEXT_INVALID'),
                                 ('### Staged\n\n- None', '### Staged\n\n- "invented"', 'CONTEXT_STALE')]:
            path.write_text(before.replace(old, new))
            with self.assertRaises(s.SnapshotError) as raised:
                s.verify(self.root)
            self.assertEqual(raised.exception.reason, reason)

    def test_saved_contract_changes_require_fresh_context_in_every_mode(self):
        for mode in ('uncommitted', 'last-commit'):
            for section in s.INTENT:
                data = request(mode=mode)
                data['intent'][section] = '  Preserved declaration.\n'
                s.create(self.root, data)
                s.verify(self.root)
                path = self.root / s.CONTEXT
                path.write_text(path.read_text().replace('Preserved declaration.', 'Changed declaration.'))
                with self.subTest(mode=mode, section=section):
                    self.stale()

    def test_capture_drift_does_not_replace_context(self):
        self.create()
        path = self.root / s.CONTEXT
        before = path.read_bytes()
        original = s.capture
        calls = []
        def capture(*args):
            value = original(*args)
            if not calls:
                (self.root / 'code.py').write_text('racing edit')
            calls.append(value)
            return value
        with patch.object(s, 'capture', side_effect=capture), self.assertRaises(s.SnapshotError):
            self.create()
        self.assertEqual(path.read_bytes(), before)

    def test_renames_and_deletions_preserve_both_sides(self):
        git(self.root, 'mv', 'code.py', 'renamed.py')
        (self.root / 'renamed.py').unlink()
        self.create()
        _, paths, _ = s.read_context(self.root)
        self.assertEqual(paths['Staged'], ['code.py', 'renamed.py'])
        self.assertEqual(paths['Unstaged'], ['renamed.py'])
        s.verify(self.root)

    def test_merge_requires_an_explicit_parent(self):
        first = git(self.root, 'rev-parse', 'HEAD')
        tree = git(self.root, 'rev-parse', 'HEAD^{tree}')
        second = git(self.root, 'commit-tree', tree, '-p', first, '-m', 'second')
        merge = git(self.root, 'commit-tree', tree, '-p', first, '-p', second, '-m', 'merge')
        git(self.root, 'update-ref', 'HEAD', merge)
        with self.assertRaises(s.SnapshotError):
            self.create(mode='last-commit')
        value = self.create(mode='last-commit', parent=second)
        self.assertEqual(value['Baseline commit'], second)
        s.verify(self.root)

    def test_unavailable_committed_object_is_boundary_rejection(self):
        value = self.create(mode='last-commit')
        target = value['Target commit']
        (self.root / '.git/objects' / target[:2] / target[2:]).unlink()
        with self.assertRaises(s.SnapshotError) as raised:
            s.verify(self.root)
        self.assertEqual(raised.exception.reason, 'BOUNDARY_UNRESOLVED')

    def test_shallow_commit_does_not_become_an_empty_tree_baseline(self):
        parent = git(self.root, 'rev-parse', 'HEAD')
        git(self.root, 'commit', '--allow-empty', '-qm', 'second')
        target = git(self.root, 'rev-parse', 'HEAD')
        (self.root / '.git/shallow').write_text(target + '\n')
        value = self.create(mode='last-commit')
        self.assertEqual(value['Baseline commit'], parent)
        (self.root / '.git/objects' / parent[:2] / parent[2:]).unlink()
        with self.assertRaises(s.SnapshotError) as raised:
            self.create(mode='last-commit')
        self.assertEqual(raised.exception.reason, 'BOUNDARY_UNRESOLVED')

    def test_missing_head_object_is_not_an_unborn_repository(self):
        target = git(self.root, 'rev-parse', 'HEAD')
        (self.root / '.git/objects' / target[:2] / target[2:]).unlink()
        with self.assertRaises(s.SnapshotError) as raised:
            self.create()
        self.assertEqual(raised.exception.reason, 'BOUNDARY_UNRESOLVED')

    def test_ambiguous_base_is_rejected(self):
        git(self.root, 'branch', 'ambiguous')
        git(self.root, 'tag', 'ambiguous')
        with self.assertRaises(s.SnapshotError) as raised:
            self.create(mode='branch', base='ambiguous')
        self.assertEqual(raised.exception.reason, 'BOUNDARY_UNRESOLVED')

    def test_unsupported_submodule_and_conflicted_index_fail_closed(self):
        initial = git(self.root, 'rev-parse', 'HEAD')
        git(self.root, 'update-index', '--add', '--cacheinfo', '160000,' + initial + ',submodule')
        (self.root / 'submodule').mkdir()
        with self.assertRaises(s.SnapshotError) as raised:
            self.create()
        self.assertEqual(raised.exception.reason, 'BOUNDARY_UNRESOLVED')
        git(self.root, 'update-index', '--force-remove', 'submodule')
        blob = git(self.root, 'rev-parse', 'HEAD:code.py')
        subprocess.run(['git', '-C', str(self.root), 'update-index', '--index-info'],
                       input='0 ' + '0' * 40 + '\tcode.py\n100644 ' + blob + ' 1\tcode.py\n',
                       text=True, check=True, capture_output=True)
        with self.assertRaises(s.SnapshotError) as raised:
            self.create()
        self.assertEqual(raised.exception.reason, 'BOUNDARY_UNRESOLVED')

    def test_cli_create_and_verify(self):
        for operation in ('create', 'verify'):
            done = subprocess.run([sys.executable, str(ROOT / 'scripts/review_snapshot.py'), operation],
                                  cwd=self.root, input=json.dumps(request()), text=True, capture_output=True)
            self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
            self.assertEqual(json.loads(done.stdout)['status'], 'success')
        (self.root / 'code.py').write_text('drift')
        done = subprocess.run([sys.executable, str(ROOT / 'scripts/review_snapshot.py'), 'verify'],
                              cwd=self.root, capture_output=True, text=True)
        self.assertEqual(done.returncode, 2)
        self.assertEqual(json.loads(done.stdout)['reason_code'], 'CONTEXT_STALE')


if __name__ == '__main__':
    unittest.main()
