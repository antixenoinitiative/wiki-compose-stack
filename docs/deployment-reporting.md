# Optional GitHub production deployment history

This feature is prepared but disabled. No GitHub token is in the repo and no reporting service is installed by Compose. Portainer remains the deployment manager.

The host-side reporter reads the local Portainer API, checks its **stack** GitConfig.ConfigHash (not the Source's latest fetched commit), verifies the managed containers and a direct localhost Wiki.js HTTP response, rechecks the hash, and creates a GitHub deployment and success status for that hash. It never infers deployment from the current GitHub main commit or a public CDN response. It does not deploy or restart containers. This is deployment history, not continuous uptime monitoring or a cryptographic audit of every running file. Branding is mutable and can be newer than the reported Compose revision.

## Required one-time setup

1. Activate and verify the managed stack first.
2. Create a fine-grained GitHub token limited to this repository with Deployments read/write and metadata access. Organization approval may be required. Save it privately on the VPS as `/etc/axi-wiki/github-token`, mode 0600, owned by root. GitHub App installation tokens are another option but need automated renewal.
3. Create a Portainer API key for an account able to read this stack. Save it as `/etc/axi-wiki/portainer-api-key`, mode 0600, owned by root. Do not assume CE provides fine-grained read-only permissions; treat this key as privileged according to its account.
4. Copy Portainer's locally trusted certificate/CA to `/etc/axi-wiki/portainer-ca.pem`. Verify its fingerprint through the existing trusted SSH session. The certificate must validate for `localhost`; do not disable TLS verification. If the current auto-generated certificate lacks that hostname, fix local TLS before enabling the reporter.
5. Inspect the local stack API privately to confirm this installed Portainer version exposes GitConfig.URL and GitConfig.ConfigHash for the **applied** revision. Confirm the latter changes after a successful deployment, not just a source fetch. Do not publish the response: it can contain stack environment secrets. If the version uses another schema, leave reporting disabled until adapted.
6. Install the reviewed `scripts/report-deployment.py` as `/opt/axi-wiki/scripts/report-deployment.py`, owned by root, and create `/etc/axi-wiki/report.env` (0600):

```ini
PORTAINER_STACK_ID=REPLACE_WITH_ACTUAL_NUMERIC_STACK_ID
PORTAINER_API_KEY_FILE=/etc/axi-wiki/portainer-api-key
PORTAINER_CA_FILE=/etc/axi-wiki/portainer-ca.pem
GITHUB_TOKEN_FILE=/etc/axi-wiki/github-token
DEPLOYMENT_STATE_FILE=/var/lib/axi-wiki/deployment-reported
```

7. Copy the two reviewed `systemd/axi-wiki-report.*` files into `/etc/systemd/system/`, run `sudo systemctl daemon-reload`, then `sudo systemctl start axi-wiki-report.service` once. Inspect `sudo journalctl -u axi-wiki-report.service --no-pager -n 30`. A GitHub authentication or certificate failure is not fixed by weakening verification.
8. Confirm the production deployment links to the correct applied commit and wiki URL. Only then run `sudo systemctl enable --now axi-wiki-report.timer`.

All connections to GitHub are outbound. Portainer stays bound to localhost; Cloudflare Access setup is independent. Do not add a public unauthenticated callback or expose the Docker socket to the reporter container (there is no reporter container).

The validation badge in the README is CI status, not production status. Deployments should appear in GitHub's repository deployment history; sidebar presentation depends on repository settings and GitHub's UI.
