#!/usr/bin/env python3
"""Report locally verified Portainer deployments; never deploy or restart services."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import re
import ssl
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request

REPO = 'antixenoinitiative/wiki-compose-stack'
TASK = 'deploy:axi-wiki-report'
SERVICES = {'db', 'wiki', 'caddy', 'branding', 'backup'}
NAMES = ['axi-wiki-db', 'axi-wiki-app', 'axi-wiki-caddy', 'axi-wiki-branding', 'axi-wiki-backup']

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None

def request(url, headers, data=None, context=None):
    req = urllib.request.Request(url, headers=headers,
        data=None if data is None else json.dumps(data).encode())
    opener = urllib.request.build_opener(
        urllib.request.ProxyHandler({}), NoRedirect(),
        urllib.request.HTTPSHandler(context=context))
    with opener.open(req, timeout=30) as response:
        return json.load(response)

def deployed_sha(stack):
    if stack.get('Name') != 'axi-wiki' or stack.get('Status') != 1 or stack.get('Type') != 2:
        raise RuntimeError('Expected an active axi-wiki Docker Compose stack')
    info = stack.get('CurrentDeploymentInfo') or {}
    if info.get('RepositoryURL', '').rstrip('/').removesuffix('.git') != 'https://github.com/' + REPO:
        raise RuntimeError('Unexpected deployed Git source')
    if info.get('ConfigFilePath') != 'compose.managed.yaml':
        raise RuntimeError('Expected deployed compose.managed.yaml')
    if info.get('ReferenceName') != 'refs/heads/main':
        raise RuntimeError('Expected deployed refs/heads/main')
    sha = info.get('ConfigHash', '')
    if not re.fullmatch('[0-9a-f]{40}', sha):
        raise RuntimeError('No full commit hash in CurrentDeploymentInfo')
    return sha

def validate_containers(containers):
    found = {}
    for c in containers:
        labels = c.get('Config', {}).get('Labels') or {}
        service = labels.get('com.docker.compose.service')
        if labels.get('com.docker.compose.project') != 'axi-wiki' or service not in SERVICES or service in found:
            raise RuntimeError('Unexpected container stack/service membership')
        state = c.get('State', {})
        if not state.get('Running') or state.get('Restarting') or state.get('Paused'):
            raise RuntimeError('A managed container is not running normally')
        health = state.get('Health', {}).get('Status')
        if (service in {'db', 'branding', 'backup'} and health != 'healthy') or health not in (None, 'healthy'):
            raise RuntimeError('A managed container is not healthy yet')
        found[service] = {'container_id': c['Id'], 'image_id': c['Image'], 'started_at': state['StartedAt']}
    if set(found) != SERVICES:
        raise RuntimeError('Missing managed containers')
    return found

def inspect_containers():
    return validate_containers(json.loads(subprocess.check_output(
        ['docker', 'inspect', *NAMES], text=True, timeout=30)))

def check_http():
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    try:
        with opener.open('http://127.0.0.1:3000/', timeout=15) as response:
            status = response.status
    except urllib.error.HTTPError as exc:
        status = exc.code
    if not 200 <= status < 400:
        raise RuntimeError('Local Wiki.js HTTP check failed')

def local_client(key, cert):
    context = ssl.create_default_context(cafile=str(cert))
    def get(path):
        return request('https://localhost:9443/api' + path, {'X-API-Key': key}, context=context)
    return get

def verify_local(get, stack_id):
    first = get('/stacks/' + str(stack_id))
    sha = deployed_sha(first)
    containers = inspect_containers()
    check_http()
    second = get('/stacks/' + str(stack_id))
    if deployed_sha(second) != sha or first.get('UpdateDate') != second.get('UpdateDate'):
        raise RuntimeError('Deployment changed during verification; retry later')
    if inspect_containers() != containers:
        raise RuntimeError('Containers changed during verification; retry later')
    return sha, containers

def github_client(token):
    headers = {'Authorization': 'Bearer ' + token, 'Accept': 'application/vnd.github+json',
               'Content-Type': 'application/json', 'User-Agent': 'AXI-Deployment-Reporter',
               'X-GitHub-Api-Version': '2022-11-28'}
    def call(path, data=None):
        return request('https://api.github.com/repos/' + REPO + path, headers, data)
    return call

def report_success(github, sha, containers):
    query = urllib.parse.urlencode({'sha': sha, 'environment': 'axi-wiki', 'task': TASK, 'per_page': 100})
    matches = github('/deployments?' + query)
    matching = [d for d in matches if d.get('sha') == sha and d.get('task') == TASK
                and d.get('environment') == 'axi-wiki']
    if matching:
        deployment = max(matching, key=lambda d: int(d['id']))
    else:
        deployment = github('/deployments', {
            'ref': sha, 'task': TASK, 'environment': 'axi-wiki', 'auto_merge': False,
            'required_contexts': [], 'production_environment': True,
            'description': 'Portainer deployed revision; local services verified',
            'payload': {'reporter': 'axi-wiki', 'containers': containers}})
    if deployment.get('sha') != sha:
        raise RuntimeError('GitHub returned an unexpected deployment revision')
    path = '/deployments/' + str(int(deployment['id'])) + '/statuses'
    statuses = github(path + '?per_page=1')
    if not statuses or statuses[0].get('state') != 'success':
        github(path, {'state': 'success', 'environment_url': 'https://wiki.antixenoinitiative.com',
                      'description': 'Portainer active; local containers and HTTP verified', 'auto_inactive': True})
    return deployment['id']

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true', help='Verify locally without contacting GitHub')
    args = parser.parse_args()
    os.umask(0o077)
    marker = Path(os.getenv('DEPLOYMENT_STATE_FILE', '/var/lib/axi-wiki/deployment-reported'))
    marker.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with marker.with_suffix('.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        key = Path(os.environ['PORTAINER_API_KEY_FILE']).read_text().strip()
        get = local_client(key, os.environ['PORTAINER_CA_FILE'])
        sha, containers = verify_local(get, int(os.environ['PORTAINER_STACK_ID']))
        if args.check:
            print('Local verification passed. Deployed commit: ' + sha)
            print('No GitHub deployment was created.')
            return
        if marker.exists() and marker.read_text().strip() == sha:
            print('This deployed revision has already been reported.')
            return
        token = Path(os.environ['GITHUB_TOKEN_FILE']).read_text().strip()
        deployment_id = report_success(github_client(token), sha, containers)
        temporary = marker.with_suffix('.tmp')
        temporary.write_text(sha + '\n')
        temporary.replace(marker)
        print('Verified deployment reported: ' + sha + ' (GitHub ID ' + str(deployment_id) + ')')

if __name__ == '__main__':
    try:
        main()
    except urllib.error.HTTPError as exc:
        print('Reporter failed: HTTP ' + str(exc.code) + '; check access and token expiry.', file=sys.stderr)
        sys.exit(1)
    except Exception as exc:
        print('Reporter failed: ' + str(exc), file=sys.stderr)
        sys.exit(1)
