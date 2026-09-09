# Prepared AXI Wiki repository update

Status: 16 local unit tests and Python/shell/YAML syntax checks passed. Docker is unavailable in the preparation environment; the GitHub validation workflow includes image build, Compose validation, and a disposable PostgreSQL backup/restore test, but these have NOT run yet. No branch, PR, image publication, VPS change, or backup schedule has been created or enabled. GitHub branch creation was denied with Resource not accessible by integration.

Upload these files preserving their paths to a NEW branch of antixenoinitiative/wiki-compose-stack. Existing branding assets and compose.yaml are intentionally absent from this ZIP; keep them in the repository. Open a draft PR to main and let Validate stack finish. Suggested title: Prepare managed wiki branding, backups and deployment reporting.

After review, follow docs/rollout.md. Merging the prepared files alone does not change compose.yaml. Publish the tools image and configure its digest before activating compose.managed.yaml. The optional deployment reporter requires private credentials and local verification before enabling its timer. Retention is one latest distinct daily state, four completed weekly points and six completed monthly points. Backup dumps are local and private; off-server copies still need configuring.
