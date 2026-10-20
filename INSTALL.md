# Install and update CCDASTRO Siril Workflow

Version 0.2.1 — development release for Windows. Tested with Siril 1.4.4.

## Recommended: Windows installer

1. Download `CCDASTRO-Siril-Workflow-0.2.1-Setup.exe` from the [GitHub releases page](https://github.com/CCDASTRO/CCDASTRO-Siril-Workflow/releases).
2. Close Siril and its workflow windows. The installer checks this and asks you to close the host if it is running.
3. Run the installer under your normal Windows account. It installs for that account without administrator access.
4. Complete the wizard. The Start menu gets installation-guide, downloads/updates and uninstall shortcuts.

The default folder is `%LOCALAPPDATA%\CCDASTRO\SirilWorkflow`.

If Siril has an existing `config.1.4.ini`, setup backs it up and adds the workflow folder to its script search path while preserving the existing entries. The backup is beside the settings file with a `.ccdastro-...bak` suffix. Start Siril, open an image, wait until loading finishes, then launch **Scripts > Python Scripts > CCDASTRO_Siril_Workflow**.

If Siril has not been run yet, uses a custom settings file, or uses another configuration filename, register the folder once: **Ctrl+P > Scripts > Script Storage Directories**, add the folder above, rescan and Apply. Keep your other script directories. Restart Siril if the entry is missing.

At first launch the script checks/install its NumPy, PyQt6 and Astropy dependencies in Siril's own Python environment. Allow internet access for package downloads; console output reports progress. A compatible Siril installation must provide sirilpy 1.0.25 or later.

## Updating later

Click **Check for updates** in the workflow. It checks this project's public GitHub releases only when requested, including development releases. If a higher version is available, it offers to open that release page. Download its Windows installer, close the host, and run the installer. Setup reuses the same installation directory and replaces the application files. Updates do not run automatically during image processing.

You can also use **Start > CCDASTRO Siril Workflow > Downloads and updates**. The installer is the same tool for first installation and upgrades; no manual copying is needed. Keep your images and personal presets outside the installation directory. A newer installer is published for every versioned release. Development releases are explicitly labeled on GitHub.

## Moving from the earlier ZIP build

Close the old workflow first. Remove the old extracted workflow directory from Siril's Script Storage Directories after the installer has registered its new folder. Preserve any personal presets/images from the old folder. This avoids two menu entries. Do not remove other script directories.

## Portable ZIP option

Extract the ZIP into a permanent writable folder. Keep the launcher file and its companion package folder together. Add the folder containing `CCDASTRO_Siril_Workflow.py` to Siril's Script Storage Directories, rescan and Apply. Launch it from Siril after opening an image.

## First processing check

1. Open a small RGB or monochrome image and wait for loading to finish.
2. For linear data, choose Linked automatic stretch, Add step, then Preview selected step.
3. Compare Current/Candidate, then Accept candidate if satisfied.
4. Open Color & Tone Studio, inspect a mask and adjust a slider/curve. Review the full-resolution result before accepting it.
5. Save result + report under a new FITS filename. Existing files are refused.

## Troubleshooting and removal

- Missing menu entry: restart the host and check the registered directory/layout above.
- Missing companion module: reinstall; the launcher alone is insufficient.
- No usable image: finish opening a single image before launching the workflow.
- Update check unavailable: try again later or open the GitHub releases page directly. Normal processing still works offline once dependencies are installed.
- The installer currently has no Windows Authenticode signature. Use the release page and SHA256SUMS.txt to identify the distributed files; checksums are not a publisher signature.
- Uninstall using Windows Installed apps or the workflow's Start menu shortcut. Close the host first. Only installed workflow files are removed. Siril setup removes its own search-path entry when uninstalling and keeps settings backups. Shared host packages, your images and separately saved presets remain.

## Maintainer release process

Run the tests, update the version in the runtime, installer and packaging script together, and run `scripts/build.ps1`. Review the resulting installer, ZIP and SHA256SUMS.txt. Push a `vX.Y.Z` tag; the repository's GitHub Actions release job builds, tests and publishes that development release. Check its completed job and release assets. Public downloads are at the Releases link above.
