# Editing in the browser

1. Open [the repository editor](https://github.dev/antixenoinitiative/wiki-compose-stack).
2. Create a branch from the latest `main`.
3. Edit files or upload replacements into their existing folders.
4. Check Source Control for misplaced files or unexpected deletions, then commit and push.
5. Open a pull request. Wait for **Validate stack** to pass before merging.
6. After merging, check **Publish tools image** and Portainer's deployed commit/status.

On iPad, extract ZIPs in Files first. Drag individual files into their destination folders; dragging a folder can leave it empty in the editor. Names beginning with a dot may be hidden in Files. If uploading a temporary name such as `env.example`, rename it to `.env.example` in the editor and remove the duplicate.

Do not upload ZIP archives, real credentials or database dumps to the repository. `.env.example` contains placeholders only.
