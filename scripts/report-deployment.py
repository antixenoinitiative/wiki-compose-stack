#!/usr/bin/env python3
"""Optional host-side reporter: no deployment, rollback, or Docker mutations."""
import json
import os
from pathlib import Path
import re
import ssl
import subprocess
import urllib.request
import urllib.error

REPO = 'antixenoinitiative/wiki-compose-stack'

def deployed_sha(stack):
    git = stack.get('GitConfig') or {}
    sha = git.get('ConfigHash', '')
    if stack.get('Name') != 'axi-wiki' or stack.get('Status') != 1:
        raise RuntimeError('Expected active axi-wiki stack')
    if git.get('URL', '').rstrip('/').removesuffix('.git') != 'https://github.com/' + REPO:
        raise RuntimeError('Unexpected Git source; inspect Portainer response privately')
    if not re.fullmatch('[0-9a-f]{40}', sha):
        raise RuntimeError('Portainer did not supply a full deployed commit hash')
    return sha

def request(url, headers, data=None, context=None):
    req = urllib.request.Request(url, headers=headers,
        data=None if data is None else json.dumps(data).encode())
    with urllib.request.urlopen(req, timeout=30, context=context) as response:
        return json.load(response)

def main():
    # Only non-secret configuration is passed in the environment.
    key = Path(os.environ['PORTAINER_API_KEY_FILE']).read_text().strip()
    token = Path(os.environ['GITHUB_TOKEN_FILE']).read_text().strip()
    stack_id = str(int(os.environ['PORTAINER_STACK_ID']))
    context = ssl.create_default_context(cafile=os.environ['PORTAINER_CA_FILE'])
    stack = request('https://localhost:9443/api/stacks/' + stack_id,
                    {'X-API-Key': key}, context=context)
    sha = deployed_sha(stack)
    names = ['axi-wiki-db', 'axi-wiki-app', 'axi-wiki-caddy', 'axi-wiki-branding', 'axi-wiki-backup']
    containers = json.loads(subprocess.check_output(['docker', 'inspect', *names], text=True))
    for container in containers:
        state = container['State']
        if not state['Running'] or state.get('Health', {}).get('Status', 'healthy') != 'healthy':
            raise RuntimeError('Not all managed stack containers are ready')
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *args, **kwargs):
            return None
    try:
        with urllib.request.build_opener(NoRedirect).open('http://127.0.0.1:3000/', timeout=15) as response:
            status = response.status
    except urllib.error.HTTPError as exc:
        status = exc.code
    if not 200 <= status < 400:
        raise RuntimeError('Local Wiki.js HTTP check failed')
    # Confirm Portainer did not change its recorded commit during verification.
    latest = request('https://localhost:9443/api/stacks/' + stack_id, {'X-API-Key': key}, context=context)
    if deployed_sha(latest) != sha:
        raise RuntimeError('Deployment changed during verification; retry later')
    marker = Path(os.getenv('DEPLOYMENT_STATE_FILE', '/var/lib/axi-wiki/deployment-reported'))
    if marker.exists() and marker.read_text().strip() == sha:
        print('This deployment has already been reported.')
        return
    headers = {'Authorization': 'Bearer ' + token, 'Accept': 'application/vnd.github+json',
               'Content-Type': 'application/json', 'User-Agent': 'AXI-Deployment-Reporter',
               'X-GitHub-Api-Version': '2022-11-28'}
    api = 'https://api.github.com/repos/' + REPO
    deployment = request(api + '/deployments', headers, {
        'ref': sha, 'environment': 'production', 'auto_merge': False,
        'required_contexts': [], 'production_environment': True,
        'description': 'Portainer-recorded revision; local services verified'})
    request(api + '/deployments/' + str(deployment['id']) + '/statuses', headers, {
        'state': 'success', 'environment_url': 'https://wiki.antixenoinitiative.com',
        'description': 'Portainer revision and local container/HTTP checks passed', 'auto_inactive': True})
    marker.parent.mkdir(parents=True, exist_ok=True)
    temporary = marker.with_suffix('.tmp')
    temporary.write_text(sha + '\n')
    temporary.replace(marker)
    print('Verified deployment reported: ' + sha)

if __name__ == '__main__':
    main()
