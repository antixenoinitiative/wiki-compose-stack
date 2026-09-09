#!/usr/bin/env python3
"""Daily dumps: latest distinct, four completed weeks, six completed months."""
import copy
from datetime import date, datetime, timedelta, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import time

HEX = re.compile(r'^[0-9a-f]{64}$')

def month_start(today, offset):
    index = today.year * 12 + today.month - 1 + offset
    return date(index // 12, index % 12 + 1, 1)

def selected(state, today):
    observations = sorted((date.fromisoformat(day), digest) for day, digest in state['observations'].items())
    labels = {'latest': state['latest']}
    current = today - timedelta(days=today.weekday())
    intervals = [(f'week-{n}', current - timedelta(days=7*n), current - timedelta(days=7*(n-1))) for n in range(1, 5)]
    intervals += [(f'month-{n}', month_start(today, -n), month_start(today, -n+1)) for n in range(1, 7)]
    for label, start, end in intervals:
        choices = [(day, digest) for day, digest in observations if start <= day < end]
        if choices:
            labels[label] = choices[-1][1]
    return set(labels.values()), labels, min(current - timedelta(days=28), month_start(today, -6))

def plan(state, digest, today):
    state = copy.deepcopy(state)
    state.pop('previous', None)
    state['latest'] = digest
    state['observations'][today.isoformat()] = digest
    keep, labels, cutoff = selected(state, today)
    # Also retain the current incomplete week/month candidates: the latest
    # observation is today's latest and is already kept. Preserve observations
    # for every retained archive so unchanged weeks can share the same file.
    state['observations'] = {day: value for day, value in state['observations'].items()
                             if date.fromisoformat(day) >= cutoff and value in keep}
    state['retained'] = sorted(keep)
    state['recovery_points'] = labels
    return state

def logical_fingerprint(lines):
    """Ignore archive-generated header/guard metadata, never SQL table content.

    Row ordering and internal DB updates may conservatively create extra distinct
    versions. This is not a semantic database equality comparison.
    """
    digest = hashlib.sha256()
    header = True
    guard = None
    pending = b''
    for line in lines:
        if header:
            if line.startswith(b'\\restrict '):
                guard = line.strip().split(b' ', 1)[1]
                continue
            if line.startswith((b'-- Started on ', b'-- Dumped from database version ', b'-- Dumped by pg_dump version ')):
                continue
            if line.strip() and not line.startswith(b'--'):
                header = False
        if pending:
            if not line.strip():
                pending += line
                continue
            digest.update(pending)
            pending = b''
        if guard and line.strip() == b'\\unrestrict ' + guard:
            pending = line
        else:
            digest.update(line)
    return digest.hexdigest()

def fingerprint(archive):
    process = subprocess.Popen(['pg_restore', '--file=-', str(archive)], stdout=subprocess.PIPE)
    try:
        result = logical_fingerprint(process.stdout)
    finally:
        process.stdout.close()
    if process.wait() != 0:
        raise RuntimeError('Could not render backup archive for verification')
    return result

def validate_state(state):
    if state.get('version') != 1 or not isinstance(state.get('observations'), dict):
        raise ValueError('Unsupported backup index; refusing retention')
    for digest in [*state.get('retained', []), *state['observations'].values(), state.get('latest'), state.get('previous')]:
        if digest is not None and not HEX.fullmatch(digest):
            raise ValueError('Invalid backup index; refusing retention')
    for day in state['observations']:
        date.fromisoformat(day)

def backup_once(root):
    root.mkdir(parents=True, exist_ok=True)
    root.chmod(0o700)
    with (root / '.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        index = root / 'index.json'
        state = json.loads(index.read_text()) if index.exists() else {'version': 1, 'observations': {}, 'retained': []}
        validate_state(state)
        for old in state.get('retained', []):
            if not (root / f'wiki_db-{old}.dump').is_file():
                raise RuntimeError('A retained archive is missing; refusing retention')
        temporary = root / '.new.dump.partial'
        try:
            subprocess.run(['pg_dump', '--format=custom', '--file=' + str(temporary)], check=True)
            subprocess.run(['pg_restore', '--list', str(temporary)], check=True, stdout=subprocess.DEVNULL)
            digest = fingerprint(temporary)
            destination = root / f'wiki_db-{digest}.dump'
            if not destination.exists():
                temporary.chmod(0o600)
                with temporary.open('rb') as archive:
                    os.fsync(archive.fileno())
                temporary.replace(destination)
            updated = plan(state, digest, datetime.now(timezone.utc).date())
            updated['last_success_utc'] = datetime.now(timezone.utc).isoformat()
            new_index = root / '.index.json.tmp'
            with new_index.open('w') as output:
                json.dump(updated, output, indent=2, sort_keys=True)
                output.flush()
                os.fsync(output.fileno())
            new_index.replace(index)
            fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(fd)
            finally:
                os.close(fd)
            for old in set(state.get('retained', [])) - set(updated['retained']):
                (root / f'wiki_db-{old}.dump').unlink(missing_ok=True)
            (root / '.last-success').touch()
            status = 'Unchanged dump; reused archive' if digest == state.get('latest') else 'Distinct backup saved'
            print(f'{status}: {destination.name}; retained={len(updated["retained"])}', flush=True)
        finally:
            temporary.unlink(missing_ok=True)

if __name__ == '__main__':
    os.umask(0o077)
    interval = int(os.getenv('BACKUP_INTERVAL_SECONDS', '86400'))
    if interval <= 0:
        raise ValueError('Backup interval must be positive')
    while True:
        try:
            backup_once(Path(os.getenv('BACKUP_DIR', '/backups')))
        except Exception as exc:
            print(f'Backup failed; retention not completed: {exc}', flush=True)
            if os.getenv('BACKUP_ONCE') == '1':
                raise
        if os.getenv('BACKUP_ONCE') == '1':
            break
        time.sleep(interval)
