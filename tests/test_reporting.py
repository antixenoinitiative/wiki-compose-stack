import copy
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('report', Path(__file__).resolve().parents[1] / 'scripts/report-deployment.py')
report = importlib.util.module_from_spec(spec)
spec.loader.exec_module(report)

class ReportingTests(unittest.TestCase):
    def stack(self):
        return {'Name': 'axi-wiki', 'Status': 1, 'Type': 2, 'UpdateDate': 10,
                'CurrentDeploymentInfo': {'RepositoryURL': 'https://github.com/' + report.REPO,
                  'ConfigHash': 'a' * 40, 'ConfigFilePath': 'compose.managed.yaml', 'ReferenceName': 'refs/heads/main'}}

    def test_uses_current_deployment_not_fetched_git_hash(self):
        s = self.stack(); s['GitConfig'] = {'ConfigHash': 'b' * 40}
        self.assertEqual(report.deployed_sha(s), 'a' * 40)

    def test_missing_deployment_info_never_falls_back(self):
        s = self.stack(); s['GitConfig'] = s.pop('CurrentDeploymentInfo')
        with self.assertRaises(RuntimeError): report.deployed_sha(s)

    def test_rejects_wrong_stack_or_incomplete_deployment(self):
        for key, values in [('Status', [2, 3, 4]), ('Name', ['other']), ('Type', [1])]:
            for value in values:
                s = self.stack(); s[key] = value
                with self.assertRaises(RuntimeError): report.deployed_sha(s)
        for key, value in [('RepositoryURL', 'https://github.com/other/repo'), ('ConfigHash', 'short'),
                           ('ConfigFilePath', 'compose.yaml'), ('ReferenceName', 'refs/heads/test')]:
            s = self.stack(); s['CurrentDeploymentInfo'][key] = value
            with self.assertRaises(RuntimeError): report.deployed_sha(s)

    def containers(self):
        return [{'Id': k, 'Image': 'image-' + k, 'Config': {'Labels': {
            'com.docker.compose.project': 'axi-wiki', 'com.docker.compose.service': k}},
            'State': {'Running': True, 'StartedAt': 'now', **({'Health': {'Status': 'healthy'}}
              if k in ('db', 'branding', 'backup') else {})}} for k in sorted(report.SERVICES)]

    def test_requires_health_checks_and_stack_membership(self):
        cs = self.containers(); self.assertEqual(set(report.validate_containers(cs)), report.SERVICES)
        for change in ('missing', 'unhealthy', 'wrong-project', 'restarting'):
            cs = self.containers()
            backup = next(c for c in cs if c['Id'] == 'backup')
            if change == 'missing': del backup['State']['Health']
            if change == 'unhealthy': backup['State']['Health']['Status'] = 'starting'
            if change == 'wrong-project': backup['Config']['Labels']['com.docker.compose.project'] = 'other'
            if change == 'restarting': backup['State']['Restarting'] = True
            with self.assertRaises(RuntimeError): report.validate_containers(cs)

    def test_deployment_or_container_change_rejects_report(self):
        for variant in ('sha', 'time', 'container'):
            second = copy.deepcopy(self.stack())
            if variant == 'sha': second['CurrentDeploymentInfo']['ConfigHash'] = 'b' * 40
            if variant == 'time': second['UpdateDate'] += 1
            stacks = iter([self.stack(), second])
            with patch.object(report, 'check_http'), patch.object(report, 'inspect_containers',
                 side_effect=[{'sample': 1}, {'sample': 2 if variant == 'container' else 1}]):
                with self.assertRaises(RuntimeError): report.verify_local(lambda _: next(stacks), 1)

    def test_success_creation_and_retry_reuse_existing_deployment(self):
        calls = []; deployments = []; statuses = []
        def github(path, data=None):
            calls.append((path, data))
            if path.startswith('/deployments?'): return deployments
            if path == '/deployments':
                self.assertFalse(data['auto_merge']); self.assertEqual(data['ref'], 'a' * 40)
                deployment = dict(data, id=5, sha=data['ref']); deployments.append(deployment); return deployment
            if data is None: return statuses
            statuses[:] = [data]; return data
        report.report_success(github, 'a' * 40, {})
        report.report_success(github, 'a' * 40, {})
        self.assertEqual(sum(data is not None for _, data in calls), 2)
        self.assertEqual(statuses[0]['state'], 'success')
        self.assertEqual(len(deployments), 1)

    def test_failed_status_can_retry_without_duplicate_deployment(self):
        deployment = {'id': 5, 'sha': 'a' * 40, 'task': report.TASK, 'environment': 'axi-wiki'}
        written = []
        def github(path, data=None):
            if path.startswith('/deployments?'): return [deployment]
            if data is None: return []
            written.append(path); return data
        report.report_success(github, 'a' * 40, {})
        self.assertEqual(written, ['/deployments/5/statuses'])

if __name__ == '__main__': unittest.main()
