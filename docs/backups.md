# Backups

`axi-wiki-backup` checks the database on startup and every 24 hours. It creates a temporary dump and compares its SQL with previous backups. Unchanged data reuses an existing archive; internal database changes can also count as a new version.

| Tier | Retained |
| --- | --- |
| Daily | Latest distinct daily backup |
| Weekly | One point for each of the last four completed weeks |
| Monthly | One point for each of the last six completed months |

Weeks run Monday to Sunday; all boundaries use UTC. Each period keeps its last successful observation. Identical points share a file, so at most 11 tracked archives are retained. History builds up over time.

Files are stored in `/backups` on the Docker volume `axi-wiki_backup_data`. `index.json` maps recovery points to dump filenames. Updates preserve the volume; shorter retention can remove older archives.

Dumps contain the database, including users and authentication settings. They do not contain PostgreSQL cluster roles, Portainer configuration, deployment credentials or other volumes. Files are private but not encrypted. This stack does not send them off-server; Hetzner server backups are separate.

## Run a backup now

```sh
sudo docker exec -e BACKUP_ONCE=1 axi-wiki-backup /bin/sh /app/backup.sh
```

## Copy a backup

Use the filename printed by the backup command or container logs. Replace `CONTENT_HASH` below:

```sh
mkdir -p ~/wiki-private-backups
chmod 700 ~/wiki-private-backups
sudo docker cp axi-wiki-backup:/backups/wiki_db-CONTENT_HASH.dump ~/wiki-private-backups/
sudo chown "$(id -u):$(id -g)" ~/wiki-private-backups/wiki_db-CONTENT_HASH.dump
chmod 600 ~/wiki-private-backups/wiki_db-CONTENT_HASH.dump
```

Download through SFTP. Keep copies private and out of Git.

## Test restoration

From a repository checkout on the VPS:

```sh
sudo bash scripts/restore-db.sh /absolute/path/to/backup.dump wiki_restore_test
```

The script creates a separate database and prints user/page counts. It refuses the live database and existing targets. The database roles named in the dump must already exist. A failed restore may leave an empty test database.

After checking the result, remove only the test database:

```sh
sudo docker exec axi-wiki-db dropdb -U postgres wiki_restore_test
```

Before starting Wiki.js against a restored database, disable its restored Git storage settings and review other integrations. Decide whether the backup or current Git content should win before re-enabling bidirectional sync.
