import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('report', Path(__file__).resolve().parents[1] / 'scripts/report-deployment.py')
report = importlib.util.module_from_spec(spec)
spec.loader.exec_module(report)

class ReportingTests(unittest.TestCase):
    def stack(self):
        return {'Name': 'axi-wiki', 'Status': 1, 'GitConfig': {
            'URL': 'https://github.com/antixenoinitiative/wiki-compose-stack.git',
            'ConfigHash': 'a' * 40}}

    def test_uses_stack_recorded_commit(self):
        self.assertEqual(report.deployed_sha(self.stack()), 'a' * 40)

    def test_missing_commit_cannot_report_success(self):
        stack = self.stack()
        del stack['GitConfig']['ConfigHash']
        with self.assertRaises(RuntimeError):
            report.deployed_sha(stack)

    def test_wrong_source_or_inactive_stack_rejected(self):
        for field, value in [('Name', 'another-stack'), ('Status', 2)]:
            stack = self.stack()
            stack[field] = value
            with self.assertRaises(RuntimeError):
                report.deployed_sha(stack)
        stack = self.stack()
        stack['GitConfig']['URL'] = 'https://github.com/another/repo'
        with self.assertRaises(RuntimeError):
            report.deployed_sha(stack)
