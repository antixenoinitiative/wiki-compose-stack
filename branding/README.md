# Branding

The branding container checks this folder every five minutes. It installs these files at Wiki.js's native favicon paths:

- `axi_logo_new2.ico`
- `axi_logo_new2_16x16.png`
- `axi_logo_new2_32x32.png`
- `axi_logo_new2_150x150.png`
- `axi_logo_new2_180x180.png`
- `axi_logo_new2_192x192.png`
- `axi_logo_new2_256x256.png`

Keep the names and dimensions, and commit related changes together. Other sizes can remain here as source assets.

The updater checks the files before switching them over. Wiki.js reads them through a shared volume; no header injection or wiki restart is needed for the file update.

Cloudflare and browsers may retain old icons. Wait for expiry or purge the affected URLs. Test the normal URL as well as a query-string variant:

https://wiki.antixenoinitiative.com/_assets/favicons/favicon-32x32.png

SVGs are not replaced by this setup.
