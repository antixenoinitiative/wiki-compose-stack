# Rollout from the existing stack

## Preparation

1. Review and merge the draft PR after validation passes. Leave Portainer pointing at `compose.yaml` for now. Its content has not changed.
2. In GitHub Actions, manually run **Publish tools image** on main. Publishing requires organization permission to create a GHCR package; it does not require VPS or database credentials.
3. In the organization package settings, make `wiki-compose-tools` **public** so Portainer can pull it without registry credentials. The image contains scripts and upstream tools only. No database, environment file or secrets are copied into it. If policy requires a private package, instead configure GHCR credentials in Portainer before proceeding.
4. Copy the exact digest reference shown in the workflow summary into Portainer's `AXI_TOOLS_IMAGE` variable. Keep all existing database variables.
5. Ensure a recent Hetzner backup and the original private Render export are retained.

## Activate

1. Edit the existing axi-wiki Git stack's Compose path to `compose.managed.yaml` and deploy. If this Portainer version does not allow editing the path, do not delete the stack: instead replace the contents of `compose.yaml` with the reviewed managed file in a separate commit, after the image variable is configured.
2. Keep the same stack name and volume names. The wiki container is recreated briefly; PostgreSQL's version, data volume and credentials remain the same.
3. Confirm `db`, `branding` and eventually `backup` are healthy, and Wiki.js/Caddy are running. Branding stays running, rather than exiting after setup. First activation requires GitHub access to fetch the icons. Later restarts can use the persisted generation if GitHub is unavailable.
4. Check `https://wiki.antixenoinitiative.com/_assets/favicons/favicon-32x32.png?check=new2`. Remove only the old favicon injection and script from Wiki.js Theme settings. Purge the affected icon URLs from Cloudflare if they still show the old image.
5. Check public pages, images, search and Discord login. Confirm Render Git storage remains disabled.
6. Verify the first dump and perform the isolated restore procedure in backups.md. Local archive-list validation alone is not a restore test.

## Roll back

If the managed path fails, return the existing stack to `compose.yaml` and redeploy. If you copied the managed content into that file instead, revert that specific activation commit first. Keep the PostgreSQL, wiki, Caddy and backup volumes. Do not delete data volumes. Branding/backup containers may need removal as unused services through Portainer after reverting; their volumes should remain. The old Wiki.js favicon returns when the ordinary wiki container is recreated.

## Later image updates

After script changes merge, publish again and replace `AXI_TOOLS_IMAGE` with the new digest, then redeploy. This intentionally separates reviewed executable changes from automatically updated image assets. Upgrading Wiki.js or PostgreSQL is a separate migration task; this change keeps their existing versions.
