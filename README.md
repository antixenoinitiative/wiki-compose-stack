# AXI Wiki infrastructure

[![Validate stack](https://github.com/antixenoinitiative/wiki-compose-stack/actions/workflows/validate.yml/badge.svg)](https://github.com/antixenoinitiative/wiki-compose-stack/actions/workflows/validate.yml)

Production: https://wiki.antixenoinitiative.com

This repository describes the stack deployment of Wiki.js, PostgreSQL and Caddy, managed through Portainer. Page-content synchronization belongs to [axiwiki](https://github.com/antixenoinitiative/axiwiki). Users, permissions, authentication configuration and history live in PostgreSQL; the Git content repository is not a full wiki backup.

## Current and prepared deployments

`compose.yaml` is the existing production configuration -- `compose.managed.yaml` is a complete replacement. It adds automatic branding and database dumps after the tools image has been published. Generally follow [rollout.md](docs/rollout.md)..

| Service | Purpose | Exposure |
| --- | --- | --- |
| db | PostgreSQL 14.24, existing restored database | Docker network only |
| wiki | Wiki.js 2.5.289 | localhost:3000 and Docker network |
| caddy | Public HTTPS reverse proxy | TCP 80/443 |
| branding (managed) | Poll approved icon filenames on main every five minutes | - |
| backup (managed) | Dump PostgreSQL immediately at startup and every 24 hours | - |

Keep the existing `POSTGRES_VOLUME_NAME=axi-wiki_postgres_data`. The volume remains external. Never run `docker compose down -v` as an update procedure. Keep the stack name `axi-wiki` to retain its other named volumes.

## Repository layout

- `branding/`: public AXI image assets, updated without rebuilding the tools image.
- `scripts/`: branding, startup, backup, isolated restore, optional deployment reporting.
- `docker/tools.Dockerfile`: versioned tools image with PostgreSQL clients and Python.
- `.github/workflows/validate.yml`: syntax, failure-path tests, Compose checks, image build.
- `.github/workflows/publish-tools.yml`: manually publish tools from main to GHCR; never deploys.
- `systemd/`: optional host-side reporting units, not installed or enabled automatically.

## Updates and branding

Portainer continues tracking main for the selected Compose file. Its GitOps polling is separate from the branding updater. 

Replace the existing logo files on main to update icons when required, no restart is needed. The updater validates dimensions and activates all fetched files together. Keep icon sets in one commit.

Control scripts are baked into the tools image: script updates require publishing a new tools image and changing `AXI_TOOLS_IMAGE`. They are never executed directly from mutable Git URLs. Routine icon changes do not rebuild images. The shared branding volume is mounted read-only in Wiki.js.

## Backups and deployment history

Retention: one latest distinct daily, four completed weeklies, and six completed monthly points, based on changes made.
Read [backup and recovery](docs/backups.md) and [deployment reporting](docs/deployment-reporting.md).

## Local checks

```sh
python3 -m unittest discover -s tests -v
for script in scripts/backup.sh scripts/wiki-start.sh; do sh -n "$script"; done
bash -n scripts/restore-db.sh
```

With Docker installed, set dummy values from `.env.example` and run `docker compose -f compose.managed.yaml config --quiet`. CI additionally builds the tools image. No automated check restores or modifies the production database.
