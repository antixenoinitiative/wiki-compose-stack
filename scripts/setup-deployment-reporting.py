#!/usr/bin/env python3
"""Install the optional reporter after local checks; leave reporting disabled."""
import getpass
import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('report', HERE / 'report-deployment.py')
report = importlib.util.module_from_spec(spec)
spec.loader.exec_module(report)

def private_write(path, content):
    path.write_text(content)
    path.chmod(0o600)

def main():
    if os.geteuid() != 0 or not sys.stdin.isatty():
        raise RuntimeError('Run using sudo from an interactive Termius terminal')
    config = Path('/etc/axi-wiki')
    if (config / 'report.env').exists():
        raise RuntimeError('Reporter configuration already exists; inspect it before replacing credentials')
    os.umask(0o077)
    print('This installs reporting files but does not start the service or publish a GitHub deployment.')
    key = getpass.getpass('Portainer API access token (hidden): ').strip()
    token = getpass.getpass('GitHub fine-grained deployment token (hidden): ').strip()
    if not key or not token:
        raise RuntimeError('Both tokens are required')
    with tempfile.TemporaryDirectory() as temporary:
        cert = Path(temporary) / 'portainer-ca.pem'
        subprocess.run(['docker', 'cp', 'portainer:/data/certs/cert.pem', str(cert)], check=True)
        get = report.local_client(key, cert)
        stacks = get('/stacks')
        matches = [s for s in stacks if s.get('Name') == 'axi-wiki' and s.get('Type') == 2]
        if len(matches) != 1:
            raise RuntimeError('Expected exactly one accessible axi-wiki Compose stack')
        stack_id = int(matches[0]['Id'])
        sha, _ = report.verify_local(get, stack_id)
        report.github_client(token)('/deployments?per_page=1')
        print('Local checks passed for axi-wiki, stack ID ' + str(stack_id) + ', commit ' + sha)
        print('GitHub deployment read access passed; the first service run will verify write access.')
        config.mkdir(parents=True, exist_ok=True, mode=0o700)
        private_write(config / 'portainer-api-key', key + '\n')
        private_write(config / 'github-token', token + '\n')
        private_write(config / 'portainer-ca.pem', cert.read_text())
        private_write(config / 'report.env', '\n'.join([
            'PORTAINER_STACK_ID=' + str(stack_id),
            'PORTAINER_API_KEY_FILE=/etc/axi-wiki/portainer-api-key',
            'PORTAINER_CA_FILE=/etc/axi-wiki/portainer-ca.pem',
            'GITHUB_TOKEN_FILE=/etc/axi-wiki/github-token',
            'DEPLOYMENT_STATE_FILE=/var/lib/axi-wiki/deployment-reported', '']))
    target = Path('/opt/axi-wiki/scripts')
    target.mkdir(parents=True, exist_ok=True, mode=0o755)
    shutil.copyfile(HERE / 'report-deployment.py', target / 'report-deployment.py')
    (target / 'report-deployment.py').chmod(0o644)
    for name in ('axi-wiki-report.service', 'axi-wiki-report.timer'):
        destination = Path('/etc/systemd/system') / name
        shutil.copyfile(HERE.parent / 'systemd' / name, destination)
        destination.chmod(0o644)
    subprocess.run(['systemctl', 'daemon-reload'], check=True)
    print('Installed. Reporting is not started or enabled. Follow docs/deployment-reporting.md.')

if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print('Setup stopped: ' + str(exc), file=sys.stderr)
        sys.exit(1)
