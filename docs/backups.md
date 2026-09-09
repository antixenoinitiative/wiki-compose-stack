# Database backup and recovery

The managed stack checks the database on startup and every 24 hours. It creates a temporary custom-format dump, lists it with pg_restore, and hashes the rendered SQL. Archive timestamps and generated SQL guard tokens are excluded from the comparison. All dumped schema, rows, ownership and grants participate; this is not a page-only change check. Physical row order or internal Wiki.js updates can create conservative extra distinct versions even when no human edited a page.

## Retention policy (UTC)

| Recovery tier | Retained points |
| --- | --- |
| Latest distinct daily state | 1 |
| Completed calendar weeks (Monday to Sunday) | Last 4 weeks, last successful observation in each |
| Completed calendar months | Last 6 months, last successful observation in each |

At most 11 tracked archive files are retained; one archive can serve several recovery points. There is no separate previous-distinct slot. The index records successful checks even if the dump is unchanged, so unchanged weeks/months can share a file. Periods before backups began or with no successful checks are not fabricated. Six months of history accumulates over time, not immediately.

Dumps are named `wiki_db-CONTENT_HASH.dump`. `/backups/index.json` maps `latest`, `week-1` through `week-4`, and `month-1` through `month-6` to full hashes. Retention deletes only previously indexed archives after the new archive and updated index are saved successfully. Missing archives or a malformed index stop pruning. Unknown files and manually saved copies are not automatically deleted. A crash can leave an extra unindexed archive; inspect before removing it.

The latest successful check is also recorded in `.last-success`, including unchanged checks. A daily check still uses temporary disk space for a fresh dump. SQL listing/rendering checks do not replace periodic restore testing.

Dumps are private (directory 0700, files 0600), stored in the Docker named volume `axi-wiki_backup_data` for the standard stack name. They are not encrypted by this script. Wiki.js users, content/history, auth configuration and database-stored assets are included. The dump does not include PostgreSQL cluster roles, Portainer settings, Compose variables, external files, or other Docker volumes.

Hetzner server backups cover this local volume on the server disk, but local dumps are not an independent off-server backup. Set up a separate private destination (for example encrypted uploads to a Storage Box or object storage) before treating this as a complete disaster-recovery system. No remote destination or credentials have been configured by this PR.

## Download a dump

Find the actual filename in Portainer's backup-container logs, then from SSH:

```sh
mkdir -p ~/wiki-private-backups
chmod 700 ~/wiki-private-backups
# Replace the example hash with the actual filename from the logs.
sudo docker cp axi-wiki-backup:/backups/wiki_db-CONTENT_HASH.dump ~/wiki-private-backups/
sudo chown "$(id -u):$(id -g)" ~/wiki-private-backups/wiki_db-CONTENT_HASH.dump
chmod 600 ~/wiki-private-backups/wiki_db-CONTENT_HASH.dump
```

Download through Termius SFTP and keep the copy private. Do not commit it, attach it to a public issue, or store it as a public Actions artifact.

## Test restoration without touching the live wiki

From a reviewed local checkout on the VPS:

```sh
sudo bash scripts/restore-db.sh /absolute/private/path/to/backup.dump wiki_restore_test
```

This creates a NEW database on the same PostgreSQL server, restores transactionally and prints user/page counts. It refuses `wiki_db` and refuses an existing target. It restores as PostgreSQL admin and preserves archive ownership (including extension ownership). It assumes the existing `postgres` and `wiki_db_user` roles; on a new server provision the required roles and private passwords first. Any additional custom roles must also exist. Grants/ACLs are retained. Provision any roles referenced by those grants before restoration. Restore consumes disk and compute, so run at a quiet time. A failed restore can leave an empty test database; inspect before removing it.

Do not start a cloned Wiki.js against a restored database until Git storage and other external integrations in the clone are disabled. Restored auth/storage settings can contact production systems.

Once the result is checked, explicitly remove only the test database:

```sh
sudo docker exec axi-wiki-db dropdb -U postgres wiki_restore_test
```

For actual disaster recovery: provision the original roles and variables, restore into an isolated target, verify counts/assets/auth configuration, stop the app, take a safety backup, and deliberately switch the app's database configuration. Do not point a second bidirectional Git writer at the production content repository.
