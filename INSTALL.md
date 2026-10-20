# Install CCDASTRO Siril Workflow (Windows)

Development version 0.1.0. Tested with Siril 1.4.4. Allow about five minutes, plus any first-run package downloads.

## 1. Extract the download

1. Download `CCDASTRO-Siril-Workflow-0.1.0-dev.zip`.
2. In File Explorer, right-click the ZIP and choose **Extract All**. Do not run the script inside the ZIP.
3. Move the extracted `CCDASTRO-Siril-Workflow` folder to a permanent, writable location. Recommended example:

   `C:\Users\chuck\Documents\Astronomy Scripts\CCDASTRO-Siril-Workflow`

4. Open that folder and confirm this layout:

```text
CCDASTRO-Siril-Workflow\
    CCDASTRO_Siril_Workflow.py
    ccdastro_siril\
        __init__.py
        _core.py
        _host.py
        _io.py
        _ui.py
        _demo.py
    INSTALL.md
    README.md
    presets\
```

The launcher and `ccdastro_siril` folder must be beside each other. Keep the entire package folder. The download also contains development tests and notices; they can remain in the extracted folder.

## 2. Tell Siril where to find the script

1. Open **Siril 1.4.4 or later** with Python scripting support.
2. Press **Ctrl+P** to open Preferences, then select **Scripts**.
3. Under **Script Storage Directories**, add the full path to the folder containing `CCDASTRO_Siril_Workflow.py` (the example path above). Keep your existing script directories.
4. Click the rescan/update button beneath the directory list, then **Apply**.
5. Look in **Scripts > Python Scripts** for `CCDASTRO_Siril_Workflow` (the filename may be displayed without `.py`). Restart Siril if the menu has not refreshed.

For an alternative launch, enter this in **Siril's own command field**, adjusting the path if needed:

```text
pyscript "C:/Users/chuck/Documents/Astronomy Scripts/CCDASTRO-Siril-Workflow/CCDASTRO_Siril_Workflow.py"
```

Siril's preferences and script-directory behavior are described in the [official Scripts preferences documentation](https://siril.readthedocs.io/en/stable/preferences/preferences_gui.html#scripts).

## 3. First launch and dependencies

1. Open a small RGB or monochrome FITS image in Siril.
2. Launch the workflow from the Scripts menu or command above. Do not double-click the `.py` file in File Explorer.
3. On first launch, the script uses Siril's Python environment to check NumPy, PyQt6 and Astropy and install missing or outdated packages. Internet access is needed for downloads. Read progress and errors in Siril's console. No separate Python installation or manual pip command is normally required.
4. If a package update requests a restart, restart Siril and launch the script again. The workflow requires sirilpy 1.0.25 or later, supplied by a compatible Siril installation.
5. Confirm that the **CCDASTRO Siril Workflow 0.1.0** window opens with your image.

The dependency mechanism follows Siril's [Python API guidance](https://siril.readthedocs.io/en/stable/Python-API.html#siril-script-coding-guidance).

## 4. Confirm processing and export

1. For linear data, choose **Linked automatic stretch**, click **Add step**, then **Preview selected step**.
2. Compare **Current** and **Candidate**; click **Accept candidate** if satisfied.
3. Open **Color & Tone Studio**, adjust a slider and inspect the mask. Choose **Review full-resolution result**, then accept or discard the candidate in the main workflow window.
4. Click **Save result + report** and choose a new `.fit` filename. Confirm that both the FITS result and its `.json` report were saved.
5. Close the workflow. Open the saved result in Siril when you want to continue processing it.

Native Siril passes require a saved FITS source with no unsaved pixel edits. Other passes work on the workflow's image copy.

## Troubleshooting

- **Script missing:** confirm the registered directory contains the launcher directly, not another nested extraction folder. Rescan or restart Siril.
- **No module named ccdastro_siril:** copy/extract the complete companion folder beside the launcher.
- **Missing package or download failure:** check the console, restore internet access, and relaunch. Do not install packages into an unrelated system Python.
- **sirilpy too old:** update Siril to a compatible version and relaunch.
- **Open an image first:** open a FITS image before starting the workflow.
- **Output already exists:** use a different filename; this build refuses overwrites.

## Updating or removing

For an update, close the workflow, extract the new package into a new version folder, and point Siril's script directory to that folder. Keep personal presets and output images separately.

To remove it, close the workflow, remove only its directory from Siril's Script Storage Directories, rescan, and delete the extracted workflow folder if no longer needed. Leave shared Python packages installed because other scripts may use them.
