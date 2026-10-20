# v0.4.2 — CCDASTRO script menu and migration

- Register a dedicated CCDASTRO menu folder while keeping the stable application install location.
- Remove recognized older workflow search-path entries during setup so earlier extracted test copies do not create duplicate menus.
- Preserve old extracted files, personal presets, images, unrelated script paths and settings backups.
- Restart Siril after updating. Launch Scripts > CCDASTRO > CCDASTRO_Siril_Workflow.

## Verification

The v0.4.2 installer and CCDASTRO menu placement were confirmed working by a user on October 20, 2026. Automated checks passed all 36 workflow tests and the isolated install, upgrade, legacy-path migration and uninstall tests.
