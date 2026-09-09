# AXI Wiki Stack

[![Validate stack](https://github.com/antixenoinitiative/wiki-compose-stack/actions/workflows/validate.yml/badge.svg)](https://github.com/antixenoinitiative/wiki-compose-stack/actions/workflows/validate.yml)
[![Publish tools image](https://github.com/antixenoinitiative/wiki-compose-stack/actions/workflows/publish-tools.yml/badge.svg)](https://github.com/antixenoinitiative/wiki-compose-stack/actions/workflows/publish-tools.yml)

Production: [wiki.antixenoinitiative.com](https://wiki.antixenoinitiative.com)

This repository manages the AXI Wiki stack via Docker Compose and Portainer. Page-content synchronization uses the separate [axiwiki repository](https://github.com/antixenoinitiative/axiwiki). Users, permissions, authentication configuration and page history are stored in PostgreSQL. The content repository is not a complete database backup.

## Active deployment

Portainer deploys the `axi-wiki` stack from `refs/heads/main`, using **`compose.managed.yaml`**.

| Service | Container | Purpose | 
| --- | --- | --- | 
| `db` | `axi-wiki-db` | PostgreSQL | 
| `wiki` | `axi-wiki-app` | Wiki.js | 
| `caddy` | `axi-wiki-caddy` | HTTPS reverse proxy, Caddy 2 | 
| `branding` | `axi-wiki-branding` | Fetch and activate native favicon files |
| `backup` | `axi-wiki-backup` | Database dumps and retention |

Keep the stack name `axi-wiki` and the existing external PostgreSQL volume `axi-wiki_postgres_data`. Updates must preserve the named volumes. Do not use `docker compose down -v` as an update procedure.

## Automatic updates

1. Create a branch from the latest `main`, make changes and open a pull request.
2. Wait for **Validate stack** to pass before merging.
3. Successful validation of a push to `main` triggers **Publish tools image**.
4. The publishing workflow builds and pushes `ghcr.io/antixenoinitiative/wiki-compose-tools:main`.
5. After publication, it updates `x-axi-tools-publication` in `compose.managed.yaml` and commits **Refresh tools deployment after publication**.
6. Portainer source polling detects that commit and applies the stack.

The image follows the moving `:main` tag; no manual digest replacement or `AXI_TOOLS_IMAGE` variable is required.
The marker commit uses the repository's built-in `GITHUB_TOKEN`, so its push does not trigger another validation/publication loop. The workflow does not force-push. If `main` advances during a build, the workflow avoids overwriting that newer revision and leaves its validation/publication to handle the next deployment.

### Verify an update

- In GitHub Actions, check both validation and publication, including **Signal the published image to Portainer**.
- In Portainer, check that the stack has processed the automatic marker commit and that the workflow and containers remain healthy/running.
- Check the wiki after changes affecting its configuration or startup.

The tools package is private.

## Variables and secrets

Store real values privately in Portainer:

| Variable | Purpose |
| --- | --- |
| `DB_ADMIN_PASSWORD` | PostgreSQL administrator password |
| `DB_PASSWORD` | Password for the existing `wiki_db_user` application role |
| `POSTGRES_VOLUME_NAME` | Existing volume name: `axi-wiki_postgres_data` |

`.env.example` contains placeholders only. Do not commit passwords, registry tokens, Discord secrets, SSH private keys or database dumps. Changing a Compose password variable does not itself rotate a password in an already-initialised PostgreSQL database.

## Database backups

The backup container checks the database on startup and every 24 hours. It creates and validates a temporary PostgreSQL dump, compares its rendered SQL with previous states and reuses an existing archive when unchanged. Internal database changes or row ordering can produce a distinct state even without a human page edit.

| Tier | Retention |
| --- | --- |
| Daily | One latest distinct daily state |
| Weekly | Last four distinct weekly states |
| Monthly | Last six distinct monthly states |

Dumps and `index.json` are stored under `/backups` in the private Docker volume `axi-wiki_backup_data`. Updating containers preserves this volume. A shortened retention policy can delete previously retained archives on a later backup run.

These are database backups, not complete server images.

See [backup and recovery](docs/backups.md) for downloading archives and testing restoration into an isolated database.  Before starting Wiki.js against a restored database, disable its restored Git storage settings and review.
