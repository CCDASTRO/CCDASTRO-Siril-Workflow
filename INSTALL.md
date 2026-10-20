# Install and update CCDASTRO Siril Workflow

Version 0.5.0 — development release for Windows. Tested with Siril 1.4.4.

## Recommended: Windows installer

1. Download `CCDASTRO-Siril-Workflow-0.5.0-Setup.exe` from the [GitHub releases page](https://github.com/CCDASTRO/CCDASTRO-Siril-Workflow/releases).
2. Close Siril and its workflow windows. The installer checks this and asks you to close the host if it is running.
3. Run the installer under your normal Windows account. It installs for that account without administrator access.
4. Complete the wizard. The Start menu gets installation-guide, downloads/updates and uninstall shortcuts.

The default folder is `%LOCALAPPDATA%\CCDASTRO\SirilWorkflow`.

If Siril has an existing `config.1.4.ini`, setup backs it up and adds the dedicated CCDASTRO menu folder to its script search path while preserving the existing entries. The backup is beside the settings file with a `.ccdastro-...bak` suffix. Start Siril, open an image, wait until loading finishes, then launch **Scripts > CCDASTRO > CCDASTRO_Siril_Workflow**.

If Siril has not been run yet, uses a custom settings file, or uses another configuration filename, register the folder once: **Ctrl+P > Scripts > Script Storage Directories**, add the CCDASTRO subfolder inside the folder above, rescan and Apply. Keep your other script directories. Restart Siril if the entry is missing.

At first launch the script checks/install its NumPy, PyQt6 and Astropy dependencies in Siril's own Python environment. Allow internet access for package downloads; console output reports progress. A compatible Siril installation must provide sirilpy 1.0.25 or later.

## Updating later

Click **Check for updates** in the workflow. It checks this project's public GitHub releases only when requested, including development releases. If a higher version is available, it offers to open that release page. Download its Windows installer, close the host, and run the installer. Setup reuses the same installation directory and replaces the application files. Updates do not run automatically during image processing.

You can also use **Start > CCDASTRO Siril Workflow > Downloads and updates**. The installer is the same tool for first installation and upgrades; no manual copying is needed. Keep your images and personal presets outside the installation directory. A newer installer is published for every versioned release. Development releases are explicitly labeled on GitHub.

## Moving from the earlier ZIP build

Close Siril and the old workflow, then run the current installer. Setup removes recognized older workflow directories from Siril's script search path and registers the new CCDASTRO menu folder. Restart Siril afterward. Old extracted folders remain on disk; preserve any personal presets/images before archiving or removing them. With custom settings or an unrecognized copy, remove only that old workflow entry from Script Storage Directories. Keep unrelated script directories.

## Portable ZIP option

Extract the ZIP into a permanent writable folder. Keep the launcher file and its companion package folder together. Add the folder containing `CCDASTRO_Siril_Workflow.py` to Siril's Script Storage Directories, rescan and Apply. Launch it from Siril after opening an image.

## RC-Astro tools

Version 0.3.0 adds dedicated **BlurXTerminator**, **NoiseXTerminator** and **StarXTerminator** choices in the processing-pass selector. Install the [RC-Astro standalone CLI](https://www.rc-astro.com/stand-alone-rc-astro-tools/) and activate the products you own through RC-Astro. The CLI must expose schema version 4 or later. This workflow checks `license.valid`; it does not activate licenses, collect activation codes, or bundle vendor software/models.

Choose a tool, click **Add step**, set its controls, then **Preview selected step**. The executable is detected at the standard Windows location or on PATH; Browse CLI selects another installation. That local path is saved separately from shareable presets. Auto selects the CLI's compute device; CPU provides a software alternative. The CLI uses its default licensed model and may download that model on first use. Processing runs in a cancellable background task on a temporary float32 FITS copy. Failures are rejected. Compare Current/Candidate and explicitly accept or discard the result.

- **BlurXTerminator:** stellar/nonstellar sharpening, star halos, automatic/manual PSF, and Correct Only. Confirm that the input is linear and run this before stretching. The workflow cannot determine linearity automatically.
- **NoiseXTerminator:** denoise strength and iterations. Advanced frequency/channel-specific settings are not exposed in this release.
- **StarXTerminator:** optional generated stars image and unscreening. Accept the starless candidate to retain its generated stars. Then use **Save generated stars FITS** or **Recombine with generated stars**. Unscreened stars use screen recombination; difference stars use addition. Generated stars remain in memory until the workflow closes; save them before closing if needed.

All three tools completed CPU inference tests on a synthetic 256x256 RGB star field; source pixels were unchanged. A native StarX background-worker/review test also passed. This verifies integration and outputs, not image-quality performance across astronomical datasets or GPU configurations. No original user image was processed in those tests.

## Optional GraXpert and SyQon tools

GraXpert and SyQon choices appear in the pass selector when their installed executables are detected. Use **Optional tools: locate / rescan** to configure a custom installation or refresh detection after installing a provider. Local executable paths are kept out of shared presets. Existing passes fail cleanly if their application is subsequently removed.

- **GraXpert:** AI background extraction (smoothing; subtraction/division) and denoising (strength), with Auto/CPU selection and an optional numeric AI model version. Install GraXpert separately; it manages its own models and may download one on first use.
- **SyQon Studio CLI:** the model selector reads the CLI's advertised list. Supported families include Prism denoising, Axiom/Axiom Mini star separation, Parallax/Parallax Nano correction, star reduction and deblur, and Deep Gradient. Premium Parallax offers Aesthetics/Classic stages. Declare linear/non-linear input explicitly; incompatible domains and empty Parallax pipelines are rejected.
- Axiom-generated stars are retained only after accepting the starless candidate, then can be exported or recombined. All tools process temporary float32 FITS copies with cancellable background execution and explicit review.

The SyQon CLI manages its own acceleration, secure account access and models. Complete Studio sign-in and Required Items installation yourself. A listed model is not proof of installation or entitlement; the CLI validates those when it runs. The workflow never accesses account credentials or loads SyQon weight files directly. No vendor executables or models are bundled.

Native checks passed on a synthetic RGB image for GraXpert background extraction and denoising (CPU), and SyQon Prism Essential, Axiom Mini with stars output, Parallax Nano and Deep Gradient (CLI-selected device). Other advertised premium models remain untested here. This validates the integration, not image quality across real datasets. See the provider documentation: [GraXpert](https://github.com/Steffenhir/GraXpert), [SyQon CLI](https://syqon.eu/develop).

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


Installer menu layout (v0.5.0): setup registers the CCDASTRO subfolder inside the stable installation directory. In Siril, select Scripts > CCDASTRO > CCDASTRO_Siril_Workflow. For manual registration, add %LOCALAPPDATA%\CCDASTRO\SirilWorkflow\CCDASTRO. Setup removes older registered directories containing both this workflow launcher and its companion package, while retaining unrelated script paths and making a settings backup. Older extracted folders remain on disk to preserve personal files; after checking your saved files, you can archive or remove those folders yourself. Restart Siril after setup. Portable ZIP users continue to register their extracted launcher folder.

## Optional Lighthouse finishing

1. Install **Lighthouse for Siril** through **Scripts > Get Scripts**. Use **Optional tools: locate / rescan** in CCDASTRO. Standard local repository locations are detected; Browse can select your trusted Lighthouse.py elsewhere.
2. Work on a stretched image. Accept or discard the candidate first; save your preset and generated stars if needed. The active Siril source must be an unchanged, saved FITS file. Save unsaved host edits and reopen the workflow before handing off.
3. Choose **Prepare Lighthouse handoff…** and select a new FITS filename. Existing files are refused. The accepted result is saved and opened as a copy in Siril; CCDASTRO closes after displaying the next step.
4. Choose **Lighthouse** from Siril's Scripts menu. It runs independently and applies edits to the handoff image. Save its result under a new name. Reopen CCDASTRO to continue if desired.

This is an assisted handoff with a manual Lighthouse launch. Automatic nested launching was not reliable in isolated Siril 1.4.4 checks and is not enabled. There is no automatic return/import, preset conversion or Lighthouse update handling. The original source file is preserved. Lighthouse's own edits and save choices are controlled by its separate interface.

The option is enabled only when an installed script is detected. Lighthouse is not bundled, imported or modified. The installed Siril port v1.0.0 credits **Yannick Dutertre (Cuiv)** and original Lighthouse author **Neven Krčmarek**, and declares GPL-3.0-or-later. Update it through Siril. See [Siril script installation](https://siril.readthedocs.io/en/stable/Scripts.html) and [Lighthouse Suite](https://www.lighthousesuite.org/).

Verification for v0.5.0: 42 automated tests and isolated installer lifecycle checks passed. An isolated Siril 1.4.4 check detected the installed Lighthouse script, opened a 40×32 RGB handoff copy, and confirmed the source file bytes were unchanged. Lighthouse editing itself remains a separately launched user action.
