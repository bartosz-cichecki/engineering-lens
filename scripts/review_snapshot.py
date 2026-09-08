#!/usr/bin/env python3
"""Create/verify the frozen Change Review Context. JSON input; no dependencies."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
from subprocess import run as git_run
import sys

CONTEXT = '.engineering-lens/change-review-context.md'
ALGORITHM = 'engineering-lens-git-snapshot-sha256-v1'
NA = 'Not applicable'
INTENT = ('Goal', 'Intentionally excluded', 'Completion criteria', 'Risks and external constraints')
PATHS = ('Staged', 'Unstaged', 'Included relevant untracked', 'Excluded untracked')
FIELDS = ('Format version', 'Language', 'Review stage', 'Repository root', 'Scope mode',
          'Baseline kind', 'Baseline commit', 'Target commit', 'Base ref', 'Base ref commit',
          'Merge-base commit', 'Pull request', 'Snapshot fingerprint algorithm', 'Snapshot fingerprint')


class SnapshotError(ValueError):
    def __init__(self, reason, message):
        super().__init__(message)
        self.reason = reason


def require(condition, message, reason='CONTEXT_INVALID'):
    if not condition:
        raise SnapshotError(reason, message)


def git(root, *args, optional=False):
    # Do not refresh the index, invoke a configured filesystem monitor, or inherit
    # an alternate repository/index from the caller's environment.
    env = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')}
    # Review may deliberately run as a different user on a read-only worktree.
    # Retain only explicit, canonical directories from command-scoped config;
    # never forward arbitrary Git configuration or wildcard trust.
    count = os.environ.get('GIT_CONFIG_COUNT', '')
    directories = []
    if count.isascii() and count.isdecimal() and len(count) < 7 and int(count) <= len(os.environ):
        for i in range(int(count)):
            key = os.environ.get(f'GIT_CONFIG_KEY_{i}', '')
            value = os.environ.get(f'GIT_CONFIG_VALUE_{i}', '')
            if (key.lower() == 'safe.directory' and os.path.isabs(value)
                    and not any(c in value for c in '*?[\r\n\x00')
                    and str(Path(value).resolve()) == value):
                directories.append(value)
    if directories:
        env['GIT_CONFIG_COUNT'] = str(len(directories))
        for i, directory in enumerate(directories):
            env[f'GIT_CONFIG_KEY_{i}'] = 'safe.directory'
            env[f'GIT_CONFIG_VALUE_{i}'] = directory
    env.update(GIT_OPTIONAL_LOCKS='0', GIT_NO_REPLACE_OBJECTS='1', GIT_NO_LAZY_FETCH='1', LC_ALL='C')
    result = git_run(['git', '-c', 'core.fsmonitor=false', '-C', str(root), *args],
                     capture_output=True, env=env)
    if result.returncode or b'ambiguous' in result.stderr:
        if optional:
            return None
        raise SnapshotError('BOUNDARY_UNRESOLVED', 'Required local Git boundary is unavailable.')
    return result.stdout


def repository(root):
    root = Path(root).resolve()
    return Path(os.fsdecode(git(root, 'rev-parse', '--show-toplevel')).rstrip('\n')).resolve()


def commit(root, ref):
    require(isinstance(ref, str) and ref and not ref.startswith('-') and '\n' not in ref,
            'Invalid commit ref.')
    return git(root, 'rev-parse', '--verify', '--end-of-options', ref + '^{commit}').decode().strip()


def head(root):
    value = git(root, 'rev-parse', '--verify', 'HEAD', optional=True)
    if value is not None:
        return commit(root, 'HEAD')
    # An invalid/missing HEAD object is not an unborn branch.
    ref = git(root, 'symbolic-ref', '-q', 'HEAD', optional=True)
    require(ref is not None and git(root, 'show-ref', '--verify', ref.decode().strip(), optional=True) is None,
            'HEAD is unavailable.', 'BOUNDARY_UNRESOLVED')
    return NA


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(',', ':')).encode('ascii')


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def path_value(value):
    require(isinstance(value, str) and value and '\x00' not in value, 'Invalid scope path.')
    p = PurePosixPath(value)
    require(not p.is_absolute() and str(p) == value and not any(x in ('.', '..', '.git') for x in p.parts),
            'Invalid scope path.')
    require(value != CONTEXT, 'Context cannot be included in evaluated scope.')
    return value


def inventory(root):
    return sorted(os.fsdecode(p) for p in git(root, 'ls-files', '--others', '--exclude-standard', '-z').split(b'\0')
                  if p and os.fsdecode(p) != CONTEXT)


def file_state(root, path, object_format):
    path_value(path)
    file = root / path
    # Do not follow a replaced directory or a symlink outside the worktree.
    for parent in file.parents:
        if parent == root:
            break
        require(not parent.is_symlink(), 'Scope path has a symlink parent.', 'BOUNDARY_UNRESOLVED')
    try:
        info = file.lstat()
    except FileNotFoundError:
        return None
    if stat.S_ISLNK(info.st_mode):
        content = os.fsencode(os.readlink(file))
        mode = '120000'
    elif stat.S_ISREG(info.st_mode):
        content = file.read_bytes()
        mode = '100755' if info.st_mode & stat.S_IXUSR else '100644'
    else:
        raise SnapshotError('BOUNDARY_UNRESOLVED', 'Unsupported scope file type (including submodules).')
    oid = hashlib.new(object_format, b'blob ' + str(len(content)).encode() + b'\0' + content).hexdigest()
    return [mode, oid, hashlib.sha256(content).hexdigest()]


def tree(root, sha):
    entries = {}
    if sha == NA:
        return entries
    for row in git(root, 'ls-tree', '-r', '-z', sha).split(b'\0'):
        if row:
            meta, path = row.split(b'\t', 1)
            mode, kind, oid = meta.decode().split()
            if os.fsdecode(path) != CONTEXT:
                entries[os.fsdecode(path)] = [mode, oid]
    return entries


def capture(root, metadata, included, excluded, intent):
    """Hash raw states, independent of diff display, rename detection and filters."""
    mode = metadata['Scope mode']
    if mode != 'uncommitted':
        for key in ('Baseline commit', 'Target commit', 'Base ref commit', 'Merge-base commit'):
            value = metadata[key]
            if value != NA:
                require(commit(root, value) == value, 'Commit boundary changed.', 'BOUNDARY_UNRESOLVED')
        return digest([metadata, intent]), {name: ({} if name == 'Excluded untracked' else []) for name in PATHS}

    require(head(root) == metadata['Baseline commit'], 'HEAD changed.', 'CONTEXT_STALE')
    require(inventory(root) == sorted(included + list(excluded)),
            'Untracked inventory changed; refresh context.', 'CONTEXT_STALE')
    baseline = tree(root, metadata['Baseline commit'])
    index = {}
    for row in git(root, 'ls-files', '--stage', '-z').split(b'\0'):
        if not row:
            continue
        meta, raw_path = row.split(b'\t', 1)
        file_mode, oid, stage = meta.decode().split()
        path = os.fsdecode(raw_path)
        if path == CONTEXT:
            continue
        require(stage == '0', 'Resolve index conflicts before freezing scope.', 'BOUNDARY_UNRESOLVED')
        index[path] = [file_mode, oid]
    object_format = git(root, 'rev-parse', '--show-object-format').decode().strip()
    working = {p: file_state(root, p, object_format) for p in sorted(index)}
    untracked = {p: file_state(root, p, object_format) for p in sorted(included)}
    require(all(untracked.values()), 'Included untracked file disappeared.', 'CONTEXT_STALE')
    paths = {
        'Staged': sorted(p for p in baseline.keys() | index.keys() if baseline.get(p) != index.get(p)),
        'Unstaged': sorted(p for p in index if working[p] is None or working[p][:2] != index[p]),
        'Included relevant untracked': sorted(included),
        'Excluded untracked': dict(sorted(excluded.items())),
    }
    # Full index and raw tracked worktree states bind both sides of staged and
    # unstaged changes, including binaries, mode changes and symlink targets.
    return digest([metadata, intent, index, working, untracked, excluded]), paths


def boundary(root, data):
    m = dict.fromkeys(FIELDS, NA)
    m.update({'Format version': '1', 'Repository root': str(root), 'Language': data['language'],
              'Review stage': data['stage'], 'Scope mode': data['mode'],
              'Snapshot fingerprint algorithm': ALGORITHM})
    mode = data['mode']
    require(mode in ('uncommitted', 'last-commit', 'branch', 'pull-request'), 'Invalid scope mode.')
    if mode == 'uncommitted':
        m['Baseline commit'] = head(root)
    elif mode == 'last-commit':
        target = commit(root, 'HEAD')
        # Read actual commit headers: rev-list hides parents at shallow boundaries.
        headers = git(root, 'cat-file', '-p', target).split(b'\n\n', 1)[0].splitlines()
        parents = [line[7:].decode('ascii') for line in headers if line.startswith(b'parent ')]
        require(len(parents) <= 1 or 'parent' in data, 'Select a merge parent.', 'BOUNDARY_UNRESOLVED')
        parent = commit(root, data['parent']) if 'parent' in data else (parents[0] if parents else NA)
        require(parent in parents or (not parents and parent == NA), 'Invalid selected parent.')
        m.update({'Target commit': target, 'Baseline commit': parent})
    else:
        base = commit(root, data['base'])
        target = commit(root, data['target'] if mode == 'pull-request' else 'HEAD')
        bases = git(root, 'merge-base', '--all', base, target).decode().split()
        require(len(bases) == 1, 'A unique merge base is required.', 'BOUNDARY_UNRESOLVED')
        m.update({'Base ref': data['base'], 'Base ref commit': base, 'Target commit': target,
                  'Baseline commit': bases[0], 'Merge-base commit': bases[0]})
        if mode == 'pull-request':
            m['Pull request'] = data['pull_request']
    m['Baseline kind'] = 'empty-tree' if m['Baseline commit'] == NA else 'commit'
    return m


def render(metadata, paths, intent):
    lines = ['# Change Review Context', ''] + [f'- {k}: {metadata[k]}' for k in FIELDS]
    lines += ['', '## Scope paths', '']
    for name in PATHS:
        values = paths[name]
        lines += ['### ' + name, '']
        if name == 'Excluded untracked':
            lines += ['- ' + json.dumps([p, reason], ensure_ascii=True) for p, reason in values.items()] if values else ['- None']
        else:
            lines += ['- ' + json.dumps(p, ensure_ascii=True) for p in values] if values else ['- None']
        lines += ['']
    for name in INTENT:
        lines += ['## ' + name, '', intent[name], '']
    return '\n'.join(lines)


def validate_metadata(m):
    require(set(m) == set(FIELDS), 'Invalid context metadata.')
    require(m['Format version'] == '1' and m['Snapshot fingerprint algorithm'] == ALGORITHM,
            'Unsupported context or fingerprint; regenerate context.')
    require(m['Language'] in ('English', 'Polish') and m['Review stage'] in ('WIP', 'Pre-commit', 'Pre-merge'),
            'Invalid language or stage.')
    require(m['Scope mode'] in ('uncommitted', 'last-commit', 'branch', 'pull-request'), 'Invalid mode.')
    for value in m.values():
        require(isinstance(value, str) and value and not any(c in value for c in '\r\n\x00'), 'Invalid metadata value.')
    require(m['Baseline kind'] == ('empty-tree' if m['Baseline commit'] == NA else 'commit'), 'Invalid baseline kind.')
    for key in ('Baseline commit', 'Target commit', 'Base ref commit', 'Merge-base commit'):
        require(m[key] == NA or re.fullmatch(r'[0-9a-f]{40}|[0-9a-f]{64}', m[key]), 'Invalid frozen SHA.')
    mode = m['Scope mode']
    if mode == 'uncommitted':
        require(all(m[k] == NA for k in ('Target commit', 'Base ref', 'Base ref commit', 'Merge-base commit', 'Pull request')),
                'Unexpected committed boundary.')
    else:
        require(m['Target commit'] != NA, 'Missing target commit.')
        if mode == 'last-commit':
            require(all(m[k] == NA for k in ('Base ref', 'Base ref commit', 'Merge-base commit', 'Pull request')),
                    'Unexpected branch boundary.')
        else:
            require(all(m[k] != NA for k in ('Base ref', 'Base ref commit', 'Merge-base commit')) and
                    m['Baseline commit'] == m['Merge-base commit'], 'Missing branch boundary.')
            require((m['Pull request'] != NA) == (mode == 'pull-request'), 'Invalid pull request boundary.')


def validate_intent(intent):
    require(set(intent) == set(INTENT), 'Missing change contract.')
    for value in intent.values():
        require(isinstance(value, str) and value.strip() and not re.search(r'(?m)^#{1,3} ', value)
                and '\x00' not in value, 'Invalid contract section.')


def context_path(root):
    path = root / CONTEXT
    require(not path.is_symlink() and not path.parent.is_symlink(), 'Context path is a symlink.')
    return path


def create(root, data):
    root = repository(root)
    metadata = boundary(root, data)
    validate_metadata(metadata)
    intent = data['intent']
    validate_intent(intent)
    intent = {name: value.strip() for name, value in intent.items()}
    included, excluded = data.get('included_untracked', []), data.get('excluded_untracked', {})
    require(isinstance(included, list) and isinstance(excluded, dict), 'Invalid untracked classification.')
    for path in included + list(excluded):
        path_value(path)
    require(len(set(included)) == len(included) and not set(included) & set(excluded), 'Duplicate scope path.')
    require(all(isinstance(v, str) and v.strip() for v in excluded.values()), 'Missing exclusion reason.')
    require(metadata['Scope mode'] == 'uncommitted' or not (included or excluded), 'Unexpected untracked scope.')
    path = context_path(root)
    first = capture(root, metadata, included, excluded, intent)
    require(capture(root, metadata, included, excluded, intent) == first, 'Snapshot changed during capture.', 'CONTEXT_STALE')
    fingerprint, paths = first
    metadata['Snapshot fingerprint'] = fingerprint
    content = render(metadata, paths, intent)
    path.parent.mkdir(exist_ok=True)
    path.write_text(content, encoding='utf-8')
    return metadata


def read_context(root):
    path = context_path(root)
    require(path.is_file(), 'Run change-review-context first.')
    text = path.read_text(encoding='utf-8')
    headings = ['# Change Review Context', '## Scope paths'] + ['### ' + n for n in PATHS] + ['## ' + n for n in INTENT]
    require(re.findall(r'(?m)^#{1,3} .*$', text) == headings, 'Invalid context sections.')
    parts = re.split(r'(?m)^#{1,3} .*\n', text)[1:]
    metadata = {}
    for line in parts[0].strip().splitlines():
        require(line.startswith('- ') and ': ' in line, 'Invalid metadata.')
        key, value = line[2:].split(': ', 1)
        require(key not in metadata, 'Duplicate metadata.')
        metadata[key] = value
    validate_metadata(metadata)
    require(metadata['Repository root'] == str(root), 'Context belongs to another repository.')
    require(re.fullmatch('[0-9a-f]{64}', metadata['Snapshot fingerprint']), 'Invalid fingerprint.')
    paths = {}
    for name, part in zip(PATHS, parts[2:6]):
        lines = part.strip().splitlines()
        require(bool(lines) and all(line.startswith('- ') for line in lines), 'Invalid scope paths.')
        values = [] if lines == ['- None'] else [json.loads(line[2:]) for line in lines]
        if name == 'Excluded untracked':
            require(all(isinstance(v, list) and len(v) == 2 and isinstance(v[1], str) and v[1].strip() for v in values),
                    'Invalid exclusions.')
            require(len({v[0] for v in values}) == len(values), 'Duplicate exclusion.')
            values = dict(values)
        for value in values:
            path_value(value)
        require(list(values) == sorted(set(values)), 'Noncanonical scope paths.')
        paths[name] = values
    require(not set(paths[PATHS[2]]) & set(paths[PATHS[3]]), 'Overlapping scope paths.')
    intent = dict(zip(INTENT, (part.strip() for part in parts[6:])))
    validate_intent(intent)
    return metadata, paths, intent


def verify(root):
    root = repository(root)
    metadata, paths, intent = read_context(root)
    expected = metadata['Snapshot fingerprint']
    metadata['Snapshot fingerprint'] = NA
    actual, current_paths = capture(root, metadata, paths[PATHS[2]], paths[PATHS[3]], intent)
    require(actual == expected and current_paths == paths, 'Frozen snapshot changed; refresh context.', 'CONTEXT_STALE')
    metadata['Snapshot fingerprint'] = expected
    return metadata


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=('inspect', 'create', 'verify'))
    parser.add_argument('--repo', default='.')
    args = parser.parse_args()
    try:
        root = repository(args.repo)
        if args.operation == 'inspect':
            output = {'repository_root': str(root), 'head': head(root), 'untracked': inventory(root)}
        elif args.operation == 'create':
            output = create(root, json.load(sys.stdin))
        else:
            output = verify(root)
        print(json.dumps({'status': 'success', 'snapshot': output}, ensure_ascii=True))
        return 0
    except (SnapshotError, OSError, ValueError, KeyError, TypeError) as exc:
        print(json.dumps({'status': 'rejected', 'reason_code': getattr(exc, 'reason', 'CONTEXT_INVALID'),
                          'message': str(exc) if isinstance(exc, SnapshotError) else 'Invalid snapshot input or unavailable file.'}))
        return 2


if __name__ == '__main__':
    sys.exit(main())
