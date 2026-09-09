# Manual repository setup

## Upload and validate

1. Download axi-wiki-repository-update-v2.zip. Do not use the earlier archive.
2. Open antixenoinitiative/wiki-compose-stack on GitHub. Under Code → Codespaces, create a browser Codespace on main. Codespaces usage is subject to your GitHub quota and billing settings.
3. In its terminal, run `git switch -c infrastructure/managed-wiki-operations`.
4. Upload the ZIP into the workspace root using the Explorer Upload action. Then run:

```sh
unzip -o axi-wiki-repository-update-v2.zip -d .
git add .dockerignore .env.example .gitignore README.md compose.managed.yaml docker scripts systemd tests docs .github
git diff --cached --stat
git commit -m "Add managed branding and tiered database backups"
git push -u origin infrastructure/managed-wiki-operations
```

5. On GitHub, open a pull request from this branch into main. Review the changed files. Existing branding assets and compose.yaml must remain present. The ZIP contains neither credentials nor backup dumps; do not add those yourself.
6. Wait for Validate stack to pass. It builds the helper image and tests a disposable database backup, unchanged-state deduplication and restoration. Resolve failures before merging.
7. Merge the pull request. This alone does not alter the current compose.yaml used by Portainer. Stop the Codespace when finished using it.

## Publish and activate

8. In GitHub Actions, select Publish tools image → Run workflow → main. Wait for success.
9. Open the organization package wiki-compose-tools settings and make the package public, or configure authenticated registry access in Portainer if it must remain private.
10. Copy the complete image reference ending in @sha256:... from the workflow summary. In the existing Portainer stack, add AXI_TOOLS_IMAGE with that value. Keep DB_ADMIN_PASSWORD, DB_PASSWORD and POSTGRES_VOLUME_NAME unchanged.
11. Follow docs/rollout.md to switch the existing stack's Compose path to compose.managed.yaml. Do not delete the stack or volumes. If the UI cannot change that path, copy the reviewed managed file contents over compose.yaml in a separate commit after setting AXI_TOOLS_IMAGE.
12. Verify the new branding and backup containers are healthy, and check public pages, assets, search and Discord login. Remove the old favicon injection once native icons work.
13. Follow docs/backups.md to inspect the first dump and test restoration into a separate database. Verify the backup logs again after the next scheduled check.

## Optional deployment reporting

14. Follow docs/deployment-reporting.md only if you want GitHub's Deployments sidebar populated. This requires separate private credentials and verification of the installed Portainer API. It is not required for branding or backups and is not enabled by uploading this package.

Retention: one latest distinct daily backup, one point for each of the last four completed weeks, and one for each of the last six completed months. UTC boundaries apply. Identical points share an archive. History accumulates from installation; it cannot recreate older backups.
