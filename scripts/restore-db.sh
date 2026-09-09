#!/bin/bash
# Restore into a NEW database only; never overwrite the live wiki_db.
set -euo pipefail
if [[ $# != 2 ]]; then
  echo 'Usage: sudo bash scripts/restore-db.sh /private/path/backup.dump wiki_restore_test' >&2
  exit 2
fi
archive=$1
target=$2
[[ -f "$archive" ]]
[[ "$target" =~ ^wiki_restore_[a-z0-9_]+$ ]] || { echo 'Target must start wiki_restore_ and use lowercase letters, digits, underscores.' >&2; exit 2; }
container=${DB_CONTAINER:-axi-wiki-db}
# createdb fails if the target already exists. Do not drop existing databases.
docker exec "$container" createdb -U postgres -O wiki_db_user "$target"
docker exec -i "$container" pg_restore -U postgres -d "$target" \
  --single-transaction --exit-on-error < "$archive"
docker exec "$container" psql -U postgres -d "$target" -v ON_ERROR_STOP=1 -c \
  'SELECT count(*) AS users FROM public.users; SELECT count(*) AS pages FROM public.pages;'
echo "Restored to $target. No Wiki.js instance has been connected to it."
