# Third-party notices

The package contains CCDASTRO Python source and test data. Third-party runtime packages and host applications are not included in the archive.

- NumPy: NumPy developers, BSD 3-Clause. https://numpy.org/doc/stable/license.html
- Astropy: Astropy developers, BSD 3-Clause. https://www.astropy.org/about.html
- PyQt6: Riverbank Computing, GPL v3 or commercial licensing. https://www.riverbankcomputing.com/commercial/license-faq
- Qt: The Qt Company and contributors; applicable LGPL/GPL/commercial terms depend on the host build. https://www.qt.io/licensing/
- Siril/sirilpy and SASpro: use each installed host under its own license. These independent ports do not bundle or relicense the hosts.
- Lighthouse inspiration: Neven Krcmarek; Siril port credits Yannick Dutertre (Cuiv). No source copied or distributed here.

Optional tools, algorithms, models and commercial plugins are not included. Their use and licenses are governed by their authors and the installed host. Full author acknowledgments and host documentation links are in README.md.

Optional integrations: GraXpert is developed by the GraXpert team and contributors (https://github.com/Steffenhir/GraXpert). SyQon models and Studio/CLI are developed by the SyQon team (https://syqon.eu/). RC-Astro tools are by Russell Croman / RC-Astro (https://www.rc-astro.com/). This package includes independent adapter code; vendor applications, models, account data and licenses are not redistributed.

## Optional Lighthouse finishing

1. Install **Lighthouse for Siril** through **Scripts > Get Scripts**. Use **Optional tools: locate / rescan** in CCDASTRO. Standard local repository locations are detected; Browse can select your trusted Lighthouse.py elsewhere.
2. Work on a stretched image. Accept or discard the candidate first; save your preset and generated stars if needed. The active Siril source must be an unchanged, saved FITS file. Save unsaved host edits and reopen the workflow before handing off.
3. Choose **Prepare Lighthouse handoff…** and select a new FITS filename. Existing files are refused. The accepted result is saved and opened as a copy in Siril; CCDASTRO closes after displaying the next step.
4. Choose **Lighthouse** from Siril's Scripts menu. It runs independently and applies edits to the handoff image. Save its result under a new name. Reopen CCDASTRO to continue if desired.

This is an assisted handoff with a manual Lighthouse launch. Automatic nested launching was not reliable in isolated Siril 1.4.4 checks and is not enabled. There is no automatic return/import, preset conversion or Lighthouse update handling. The original source file is preserved. Lighthouse's own edits and save choices are controlled by its separate interface.

The option is enabled only when an installed script is detected. Lighthouse is not bundled, imported or modified. The installed Siril port v1.0.0 credits **Yannick Dutertre (Cuiv)** and original Lighthouse author **Neven Krčmarek**, and declares GPL-3.0-or-later. Update it through Siril. See [Siril script installation](https://siril.readthedocs.io/en/stable/Scripts.html) and [Lighthouse Suite](https://www.lighthousesuite.org/).
