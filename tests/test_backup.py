import importlib.util
from datetime import date, timedelta
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

PROJECT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('backup', PROJECT / 'scripts/backup.py')
backup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(backup)

def digest(number):
    return f'{number:064x}'

class RetentionTests(unittest.TestCase):
    def test_daily_simulation_matches_full_history_across_year_boundary(self):
        state = {'version': 1, 'observations': {}, 'retained': []}
        history = {}
        start = date(2025, 9, 1)
        for n in range(430):
            today = start + timedelta(days=n)
            value = digest(n + 1)
            history[today.isoformat()] = value
            state = backup.plan(state, value, today)
            reference = dict(state, observations=history)
            expected, labels, _ = backup.selected(reference, today)
            self.assertEqual(set(state['retained']), expected, today)
            self.assertEqual(state['recovery_points'], labels)
            self.assertLessEqual(len(expected), 11)
        self.assertEqual(len([x for x in state['recovery_points'] if x.startswith('week-')]), 4)
        self.assertEqual(len([x for x in state['recovery_points'] if x.startswith('month-')]), 6)

    def test_no_separate_previous_daily_slot(self):
        state = {'version': 1, 'observations': {}, 'retained': []}
        state = backup.plan(state, digest(1), date(2026, 9, 8))
        state = backup.plan(state, digest(2), date(2026, 9, 9))
        self.assertEqual(state['retained'], [digest(2)])

    def test_unchanged_state_shares_one_archive_across_all_tiers(self):
        state = {'version': 1, 'observations': {}, 'retained': []}
        for n in range(250):
            state = backup.plan(state, digest(1), date(2026, 1, 1) + timedelta(days=n))
        self.assertEqual(state['retained'], [digest(1)])
        self.assertEqual(len(state['recovery_points']), 11)

    def test_missing_weeks_are_not_fabricated(self):
        state = backup.plan({'version': 1, 'observations': {}, 'retained': []}, digest(1), date(2026, 9, 9))
        self.assertEqual(state['recovery_points'], {'latest': digest(1)})

    def test_guard_and_header_variations_do_not_create_duplicates(self):
        def sql(token, version):
            return io.BytesIO(f'-- Dumped by pg_dump version {version}\n\\restrict {token}\nSET x = 1;\nCOPY users FROM stdin;\nAlice\n\\.\n\\unrestrict {token}\n\n'.encode())
        self.assertEqual(backup.logical_fingerprint(sql('aaa', '14.24')), backup.logical_fingerprint(sql('bbb', '14.25')))

    def test_changes_to_sql_data_are_not_ignored(self):
        a = b'SET x = 1;\nCOPY users FROM stdin;\n-- Dumped by pg_dump version user-data\n\\.\n'
        b = a.replace(b'user-data', b'changed-data')
        self.assertNotEqual(backup.logical_fingerprint(io.BytesIO(a)), backup.logical_fingerprint(io.BytesIO(b)))

class BackupExecutionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.bin = self.root / 'bin'
        self.bin.mkdir()
        self.directory = self.root / 'backups'
        for name, body in {
            'pg_dump': 'if [ "${FAIL_DUMP:-0}" = 1 ]; then exit 1; fi\nfor arg; do case "$arg" in --file=*) printf archive > "${arg#--file=}";; esac; done\n',
            'pg_restore': 'if [ "$1" = --list ]; then exit 0; fi\nprintf "SET x = 1;\\n%s\\n" "${FAKE_DATA:-data}"\n'
        }.items():
            path = self.bin / name
            path.write_text('#!/bin/sh\n' + body)
            path.chmod(0o755)

    def run_backup(self, **extra):
        env = dict(os.environ, PATH=str(self.bin) + ':' + os.environ['PATH'], BACKUP_DIR=str(self.directory), BACKUP_ONCE='1', **extra)
        return subprocess.run(['python3', str(PROJECT / 'scripts/backup.py')], env=env, capture_output=True)

    def test_unchanged_rerun_reuses_file_and_private_permissions(self):
        self.assertEqual(self.run_backup().returncode, 0)
        archive, = self.directory.glob('*.dump')
        timestamp = archive.stat().st_mtime_ns
        result = self.run_backup()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(list(self.directory.glob('*.dump'))), 1)
        self.assertEqual(archive.stat().st_mtime_ns, timestamp)
        self.assertEqual(archive.stat().st_mode & 0o777, 0o600)

    def test_failure_preserves_index_and_archives(self):
        self.assertEqual(self.run_backup().returncode, 0)
        index = (self.directory / 'index.json').read_bytes()
        archives = list(self.directory.glob('*.dump'))
        self.assertNotEqual(self.run_backup(FAIL_DUMP='1').returncode, 0)
        self.assertEqual((self.directory / 'index.json').read_bytes(), index)
        self.assertEqual(list(self.directory.glob('*.dump')), archives)
        self.assertFalse((self.directory / '.new.dump.partial').exists())

    def test_corrupt_index_refuses_pruning(self):
        self.assertEqual(self.run_backup().returncode, 0)
        (self.directory / 'index.json').write_text('{broken')
        self.assertNotEqual(self.run_backup().returncode, 0)
        self.assertEqual(len(list(self.directory.glob('*.dump'))), 1)

    def test_restore_refuses_live_database(self):
        path = self.root / 'dummy.dump'
        path.write_bytes(b'archive')
        result = subprocess.run(['bash', str(PROJECT / 'scripts/restore-db.sh'), str(path), 'wiki_db'], capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(b'Target must start wiki_restore_', result.stderr)
