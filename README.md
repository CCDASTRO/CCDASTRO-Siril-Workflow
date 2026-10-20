# CCDASTRO Siril Workflow

Version 0.2.0 — development release, October 20, 2026.

A standalone image-processing workflow for Siril, with Color & Tone controls, masks, curves and review of each processing pass. This project maintains its own source, presets, tests and versioning.

## Download, install and update

[Download the Windows installer or ZIP](https://github.com/CCDASTRO/CCDASTRO-Siril-Workflow/releases). Use the Windows installer for first installation and later upgrades. See [INSTALL.md](INSTALL.md) for exact steps, migration from earlier ZIP copies, and troubleshooting. The workflow's **Check for updates** button finds new releases and opens their download page. Each installer uses a stable per-user folder and preserves separately saved images/presets.

## What works

- Work on a copy of an open RGB or monochrome image.
- Add, reorder and review individual processing passes; accept or discard each candidate.
- Linked automatic stretch, a simple background-plane fit, and green suppression.
- Color & Tone Studio: live sampled before/after/mask/overlay views, hue presets and picker, feathered hue and tonal selections, inversion, amount, exposure, contrast, shadows/highlights, whites/blacks, saturation, vibrance, temperature/tint, and master/R/G/B curve sliders.
- Review full-resolution Color & Tone output before accepting it. Use stretched data for these adjustments.
- Recombine with a separately supplied, registered stars FITS image after inspecting alignment.
- Save/load host-specific JSON workflow presets. Save a new float32 FITS result with a JSON pass report.
- Optional native host commands on a separate working image. Parameters currently use a JSON editor.

## Scope of this build

This is an initial development build. There is no unattended run-all, automatic LRGB/narrowband orchestration, reference-color matching, automatic registration or starless/stars pairing, or full-resolution pan/zoom inspector yet. Color & Tone settings are recorded in the output report; the dialog starts with neutral controls on each new pass. The simple background-plane fit is not AutoDBE or an AI background model. Use conservative amounts and inspect nebulosity.

No third-party AI model, plugin or commercial license is bundled. Native AI, color-calibration and other optional commands depend on the host's installed tools, paths, models, licenses and preset schema. Only the native stretch has been exercised in the installed application; the other allowlisted native commands still need individual validation. An unsuccessful native command may leave a working image open for inspection.

FITS is the portable interchange format. The original image/file is preserved. Existing output files are refused. FITS headers are preserved where supplied by the host; arbitrary host application state, layers and display settings are not serialized to FITS. Save through the host if its native project metadata is needed.

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

## Development and verification

Python 3.10+ with NumPy, PyQt6 and Astropy. Use the Siril Python environment for integration tests.

Run `python -m unittest discover -s tests -v` from this repository with dependencies installed. The offline UI demo is `python -m ccdastro_siril._demo`; it processes only a synthetic image.

Automated checks cover source-copy protection, mask boundaries, curve monotonicity, Color & Tone reference outputs, stretch behavior, background-plane fitting, FITS roundtrips/no overwrite, and host adapter behavior. See `validation/` for the native application smoke-test records. Tests use small synthetic inputs; large astrophotography datasets and optional AI commands need further field testing. Processing is synchronous, so full-resolution operations may temporarily make the dialog unresponsive.

## Credits and ownership

CCDASTRO workflow/UI and the Color & Tone implementation: Chuck Faranda / CCDASTRO, Inc. The color controls were inspired by Lighthouse by Neven Krcmarek; the Siril Lighthouse header also credits Yannick Dutertre (Cuiv) for its port. No Lighthouse source is bundled. Color & Tone processing is implemented by CCDASTRO and checked against saved reference values.

Siril and sirilpy: the Siril development team and contributors â€” https://siril.org/ and https://siril.readthedocs.io/en/stable/Python-API.html . Optional StarNet support belongs to Mikita Misiura and the StarNet project; it is not included. Optional native denoising/deconvolution/calibration remains Siril's implementation.

This workflow brings host features together; underlying algorithms and external tools remain the work of their respective authors. Third-party packages and optional tools retain their own licenses. No endorsement or affiliation is implied. See THIRD_PARTY_NOTICES.md.

Copyright 2026 CCDASTRO, Inc. All rights reserved. No new open-source license is granted by this development package.
