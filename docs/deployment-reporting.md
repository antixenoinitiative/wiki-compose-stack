# GitHub deployment status

The optional reporter checks the deployed commit, five stack containers and the local wiki response every five minutes. It records successful deployments under **axi-wiki** on GitHub, with a link to the live site. It does not restart services or report ongoing outages.

This guide uses the updated reporter and `setup-deployment-reporting.py`. It reads Portainer's `CurrentDeploymentInfo`, rather than the legacy `GitConfig` fields. Upload those script updates before installing it.

## Credentials

- **GitHub:** fine-grained token, resource owner `antixenoinitiative`, only repository `wiki-compose-stack`, **Deployments: Read and write**. Organisation approval may be required.
- **Portainer:** user menu → My account → Access tokens. Use an account that can inspect the wiki stack. The token inherits that account's privileges.

Keep these separate from the image-download token. Do not put tokens in Git or shell commands.

## Install

Upload the reporter ZIP to `/home/alexmg1/`, then run:

```sh
python3 -m zipfile -e ~/axi-wiki-deployment-reporter.zip ~/axi-deployment-reporter
sudo python3 ~/axi-deployment-reporter/scripts/setup-deployment-reporting.py
```

Enter the Portainer token first, then the GitHub token, at the hidden prompts. Setup checks the local stack and GitHub read access. It copies Portainer's public certificate locally and verifies HTTPS; if that fails, resolve the certificate error rather than disabling verification.

The script installs code under `/opt/axi-wiki/scripts`, private configuration under `/etc/axi-wiki`, and the systemd units. It does not start reporting and refuses to overwrite an existing configuration.

## First report

```sh
sudo systemctl start axi-wiki-report.service
sudo journalctl -u axi-wiki-report.service --no-pager -n 20
```

Check for `Verified deployment reported:`. On GitHub, check **Deployments → axi-wiki** for the same commit shown in Portainer and the wiki link. Then enable the schedule:

```sh
sudo systemctl enable --now axi-wiki-report.timer
sudo systemctl list-timers axi-wiki-report.timer --no-pager
```

## Maintenance

Renew expiring tokens in `/etc/axi-wiki/portainer-api-key` and `/etc/axi-wiki/github-token`, keeping root ownership and mode 0600. Refresh the trusted certificate if Portainer's certificate changes. Inspect failures with the journal command above.

Reporter code is installed on the host; GitOps does not update that copy. After downloading a reviewed update into the same folder:

```sh
sudo systemctl stop axi-wiki-report.timer
sudo systemctl stop axi-wiki-report.service
sudo install -m 0644 ~/axi-deployment-reporter/scripts/report-deployment.py /opt/axi-wiki/scripts/report-deployment.py
sudo systemctl start axi-wiki-report.service
```

Check the result, then restart the timer. If unit files changed, install them and run `sudo systemctl daemon-reload` too.

To stop scheduled reporting:

```sh
sudo systemctl disable --now axi-wiki-report.timer
sudo systemctl stop axi-wiki-report.service
```

The wiki and Portainer updates continue running.
