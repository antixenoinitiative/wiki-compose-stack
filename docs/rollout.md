# Stack settings and upgrades

## Portainer settings

| Setting | Value |
| --- | --- |
| Stack | `axi-wiki` |
| Repository | `antixenoinitiative/wiki-compose-stack` |
| Reference | `refs/heads/main` |
| Compose path | `compose.managed.yaml` |
| Source polling | Enabled |
| Registry | Authenticated custom registry at `ghcr.io` |

Set `DB_ADMIN_PASSWORD`, `DB_PASSWORD` and `POSTGRES_VOLUME_NAME` privately in Portainer. The PostgreSQL volume name is `axi-wiki_postgres_data`.

Keep the stack name and all existing volumes. Do not delete the stack or run `docker compose down -v` to update it. The backup and branding services follow `wiki-compose-tools:main`; `AXI_TOOLS_IMAGE` is no longer used.

For a replacement server, restore the database and required roles before starting Wiki.js. Git content sync alone cannot restore users or all wiki settings.

## External HTTPS proxy

The wiki stack does not include a reverse proxy or publish ports 80/443. Public HTTPS is provided by the separate `axi-proxy` stack, whose configuration is managed privately in Portainer.

The proxy connects to `axi-wiki-app:3000` through the existing `axi-wiki_default` Docker network. Preserve the `axi-wiki` stack name and this network. Routine stack updates should use Portainer's update/redeploy operation rather than deleting and recreating the stack or network.

The proxy reuses the existing `axi-wiki_caddy_data` and `axi-wiki_caddy_config` volumes as external volumes. Their names reflect the previous deployment layout; they are now used by the separate proxy. Do not delete them when cleaning up the old wiki Caddy container.

Recovery onto a replacement server must include the separately managed proxy configuration and its persistent storage, as well as the wiki application and database. This repository alone does not recreate public HTTPS access.

After a deployment, check both the wiki-stack health and the public HTTPS site. The deployment reporter checks the local application response, not the external proxy.

## Upgrade Wiki.js or PostgreSQL

1. Make a fresh database backup and keep a copy outside automatic retention. Test restoration.
2. Change the relevant image in `compose.managed.yaml` on a branch. Upgrade Wiki.js and PostgreSQL separately.
3. Wait for validation, then merge during a quiet period. Polling can deploy the merge immediately.
4. Check logs, pages, assets, search, login and Git storage sync.

A PostgreSQL major-version change needs a database migration; do not simply point a new major image at the existing data volume. Changing a password variable does not rotate the password in an existing database.

## If an update fails

Check the failed Actions step and Portainer/container logs. Fix or revert the relevant change through Git. Reverting the application image may not undo database migrations; keep the pre-upgrade backup.

The old `compose.yaml` omits branding and backups. It is not the normal rollback target. Preserve all data volumes during recovery.
