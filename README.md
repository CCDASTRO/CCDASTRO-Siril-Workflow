# CCDASTRO Siril Workflow

Version 0.6.1 — development release, October 22, 2026.

A standalone image-processing workflow for Siril, with Color & Tone controls, masks, curves and review of each processing pass. This project maintains its own source, presets, tests and versioning.

## Download, install and update

Current release: **v0.6.1** (development release). [Release notes](https://github.com/CCDASTRO/CCDASTRO-Siril-Workflow/releases/tag/v0.6.1) · [Windows installer](https://github.com/CCDASTRO/CCDASTRO-Siril-Workflow/releases/download/v0.6.1/CCDASTRO-Siril-Workflow-0.6.1-Setup.exe).

Includes Color & Tone Studio and dedicated optional RC-Astro, GraXpert and SyQon controls when installed. Version 0.6.1 registers a CCDASTRO script menu and removes recognized older workflow paths from Siril settings; old extracted files remain preserved on disk.

[Download the Windows installer or ZIP](https://github.com/CCDASTRO/CCDASTRO-Siril-Workflow/releases). Use the Windows installer for first installation and later upgrades. See [INSTALL.md](INSTALL.md) for exact steps, migration from earlier ZIP copies, and troubleshooting. The workflow provides optional daily startup update notices and a manual **Check for updates** button. Each installer uses a stable per-user folder and preserves separately saved images/presets.

After installation, restart Siril and choose **Scripts > CCDASTRO > CCDASTRO_Siril_Workflow**.

The v0.4.2 installer and CCDASTRO menu placement were confirmed working by a user on October 22, 2026. Version 0.6.1 adds the optional Lighthouse handoff; automated verification covers source preservation, refusal of unsaved sources/existing destinations, and separate-script discovery.

**Check for updates at startup** is enabled by default. It quietly checks this project’s GitHub releases in the background at most once every 24 hours, including development releases. When a newer version is found, a small **Update available: v… — Downloads** button appears in the workflow. Click it to open that release page. A known newer version remains visible on later launches between checks. No startup popup interrupts processing; offline failures are quiet. Clear the startup checkbox to disable automatic checks; that choice is remembered separately for this workflow. **Check for updates** still checks immediately whenever you choose, even if startup checks are disabled or a daily check already ran. Closing the workflow never waits for the network check. Updates are downloaded and installed manually: close the host and run the new Windows installer. Existing images and personal presets stay where you saved them.

## What works

- Work on a copy of an open RGB or monochrome image.
- Add, reorder and review individual processing passes; accept or discard each candidate.
- Independent channel stretch with R/G/B target and amount sliders, individual channel views, RGB recombination review, and optional registered mono FITS inputs.
- Linked automatic stretch, a simple background-plane fit, and green suppression.
- Color & Tone Studio: live sampled before/after/mask/overlay views, hue presets and picker, feathered hue and tonal selections, inversion, amount, exposure, contrast, shadows/highlights, whites/blacks, saturation, vibrance, temperature/tint, and master/R/G/B curve sliders.
- Review full-resolution Color & Tone output before accepting it. Use stretched data for these adjustments.
- Recombine with a separately supplied, registered stars FITS image after inspecting alignment.
- Save/load host-specific JSON workflow presets. Save a new float32 FITS result with a JSON pass report.
- Optional native host commands on a separate working image. Parameters currently use a JSON editor.

## Scope of this build

This is an initial development build. There is no unattended run-all, automatic LRGB/narrowband orchestration, reference-color matching, automatic registration or starless/stars pairing, or full-resolution pan/zoom inspector yet. Color & Tone settings are recorded in the output report; the dialog starts with neutral controls on each new pass. The simple background-plane fit is not AutoDBE or an AI background model. Use conservative amounts and inspect nebulosity.

No third-party AI model, plugin or commercial license is bundled. Native AI, color-calibration and other optional commands depend on the host's installed tools, paths, models, licenses and preset schema. Native stretch and all three RC-Astro tools have been exercised on synthetic inputs; the other allowlisted native commands still need individual validation. An unsuccessful native command may leave a working image open for inspection.

FITS is the portable interchange format. The original image/file is preserved. Existing output files are refused. FITS headers are preserved where supplied by the host; arbitrary host application state, layers and display settings are not serialized to FITS. Save through the host if its native project metadata is needed.

## Independent channel stretch (linear input)

Use **Independent channel stretch (linear RGB / mono masters)** before the final nonlinear stretch, instead of adding a linked stretch as well. Work from a linear RGB image, or select three already registered mono FITS masters for the R / G / B output slots. For SHO, assign SII to R, Ha to G and OIII to B; choose the mapping appropriate to your palette. This tool does not register images or infer filters. Matching dimensions alone do not prove registration.

1. Confirm that the inputs are linear and registered. If loading masters, all three must be mono and have identical dimensions. Their source files remain unchanged; output uses the first master’s FITS header, with structural cards updated for RGB. Conflicting per-filter metadata is not merged.
2. Start with the shared median target of **0.23**. Adjust each channel’s target (0.01–0.50) and stretch amount (0–100%) independently. A lower R target or amount can reduce red dominance. Amount zero leaves that channel unchanged.
3. Click **Update preview**. Inspect Recombined RGB, each grayscale channel and Before RGB. Preview sampling uses the same fixed per-channel plan as the full-resolution result.
4. Click **Review full-resolution result**, then **Accept candidate** or **Discard candidate** in the workflow. Nothing is committed before acceptance. The configured step is added to the workflow list for presets; previewing it again opens the review and requires linear confirmation again. Choose mono input files again for each new review; presets store controls, not image paths. Accepted reports record the loaded master paths when applicable.
5. Continue with stretched-image finishing, Color & Tone or your optional finishing tools. Do not add another automatic stretch to the accepted result.

Each channel uses a robust median/MAD black-point estimate and its own midtones transfer function, followed by its amount blend with the original channel. The Python builds estimate statistics on a grid of at most 512 × 512 samples. Processing is independent per channel and recombines the output planes into RGB. Applying those transforms to the channels of a linear RGB mapping is mathematically equivalent to stretching the same mapped mono planes before combination. Equal targets are an artistic balance choice: they change relative emission brightness and do not preserve calibrated flux ratios or guarantee a particular palette. Already stretched data should use Color & Tone instead.

## Installation

Start with [INSTALL.md](INSTALL.md). It includes Windows folder layouts, menu steps, first-launch checks, updates and troubleshooting. Extract the ZIP before installation; keep the launcher and its complete companion package folder together.

## First test

1. Open a small, saved FITS copy of an image in the host.
2. Launch the workflow, add Linked automatic stretch for linear input, then Preview selected step.
3. Switch Current/Candidate to compare. Accept candidate only when satisfied.
4. Open Color & Tone Studio. Choose a hue or tonal range, inspect Mask/Mask overlay, then adjust sliders and curves.
5. Click Review full-resolution result. Back in the workflow, accept or discard it.
6. Save result + report to a new filename.

Each accepted pass starts from the current workflow result. Re-previewing a pass applies it again to that current result. Presets contain the workflow list, while the result report records passes actually accepted. Presets for the other host are rejected.

## Native passes

Example parameters: `{"command":"autostretch","args":[]}`. Other allowlisted command names are listed in `ccdastro_siril/_host.py`. Arguments must be individual strings using Siril's documented syntax.

Native passes require the current Siril image to be a saved FITS with no unsaved pixel changes. The adapter checks pixels against the disk image, processes a temporary FITS, then reloads the original source. Portable passes can use other loaded image formats. The workflow exports the result to a new FITS file rather than replacing Siril's active source. Native passes may affect Siril's view/history state while reloading.

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

## Development and verification

Python 3.10+ with NumPy, PyQt6 and Astropy. Use the Siril Python environment for integration tests.

Run `python -m unittest discover -s tests -v` from this repository with dependencies installed. The offline UI demo is `python -m ccdastro_siril._demo`; it processes only a synthetic image.

Automated checks cover source-copy protection, mask boundaries, curve monotonicity, Color & Tone reference outputs, stretch behavior, background-plane fitting, FITS roundtrips/no overwrite, and host adapter behavior. See `validation/` for the native application smoke-test records. Tests use small synthetic inputs; large astrophotography datasets and optional AI commands need further field testing. Processing is synchronous, so full-resolution operations may temporarily make the dialog unresponsive.

## Credits and ownership

CCDASTRO workflow/UI and the Color & Tone implementation: Chuck Faranda / CCDASTRO, Inc. The color controls were inspired by Lighthouse by Neven Krcmarek; the Siril Lighthouse header also credits Yannick Dutertre (Cuiv) for its port. No Lighthouse source is bundled. Color & Tone processing is implemented by CCDASTRO and checked against saved reference values.

Siril and sirilpy: the Siril development team and contributors — https://siril.org/ and https://siril.readthedocs.io/en/stable/Python-API.html . Optional StarNet support belongs to Mikita Misiura and the StarNet project; it is not included. Optional native denoising/deconvolution/calibration remains Siril's implementation.

This workflow brings host features together; underlying algorithms and external tools remain the work of their respective authors. Third-party packages and optional tools retain their own licenses. No endorsement or affiliation is implied. See THIRD_PARTY_NOTICES.md.

Copyright 2026 CCDASTRO, Inc. All rights reserved. No new open-source license is granted by this development package.

## Optional Lighthouse finishing

1. Install **Lighthouse for Siril** through **Scripts > Get Scripts**. Use **Optional tools: locate / rescan** in CCDASTRO. Standard local repository locations are detected; Browse can select your trusted Lighthouse.py elsewhere.
2. Work on a stretched image. Accept or discard the candidate first; save your preset and generated stars if needed. The active Siril source must be an unchanged, saved FITS file. Save unsaved host edits and reopen the workflow before handing off.
3. Choose **Prepare Lighthouse handoff…** and select a new FITS filename. Existing files are refused. The accepted result is saved and opened as a copy in Siril; CCDASTRO closes after displaying the next step.
4. Choose **Lighthouse** from Siril's Scripts menu. It runs independently and applies edits to the handoff image. Save its result under a new name. Reopen CCDASTRO to continue if desired.

This is an assisted handoff with a manual Lighthouse launch. Automatic nested launching was not reliable in isolated Siril 1.4.4 checks and is not enabled. There is no automatic return/import, preset conversion or Lighthouse update handling. The original source file is preserved. Lighthouse's own edits and save choices are controlled by its separate interface.

The option is enabled only when an installed script is detected. Lighthouse is not bundled, imported or modified. The installed Siril port v1.0.0 credits **Yannick Dutertre (Cuiv)** and original Lighthouse author **Neven Krčmarek**, and declares GPL-3.0-or-later. Update it through Siril. See [Siril script installation](https://siril.readthedocs.io/en/stable/Scripts.html) and [Lighthouse Suite](https://www.lighthousesuite.org/).

Verification for v0.6.1: 42 automated tests and isolated installer lifecycle checks passed. An isolated Siril 1.4.4 check detected the installed Lighthouse script, opened a 40×32 RGB handoff copy, and confirmed the source file bytes were unchanged. Lighthouse editing itself remains a separately launched user action.
