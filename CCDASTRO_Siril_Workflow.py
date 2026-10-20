"""CCDASTRO Siril Workflow 0.2.1.
Author: Chuck Faranda / CCDASTRO, Inc. https://ccdastro.com/
Copyright (c) 2026 CCDASTRO, Inc. All rights reserved.
Launch from Siril's Python scripts menu.
"""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))

def main():
    import sirilpy
    sirilpy.check_module_version('>=1.0.25')
    if not sirilpy.ensure_installed('numpy','PyQt6','astropy',version_constraints=['>=1.24','>=6.5','>=5.3']):
        raise RuntimeError('Required Python packages could not be installed. See the Siril console and INSTALL.md.')
    from PyQt6.QtWidgets import QApplication,QMessageBox
    from ccdastro_siril._host import Host,ImageNotReadyError
    from ccdastro_siril._ui import WorkflowDialog
    api=sirilpy.SirilInterface();api.connect()
    app=QApplication.instance() or QApplication([])
    try:
        api.cmd('requires','1.4.4')
        window=WorkflowDialog(Host(api));window.exec()
    except ImageNotReadyError as e:
        api.log(str(e))
        QMessageBox.information(None,'CCDASTRO Siril Workflow',str(e))
    except Exception as e:
        QMessageBox.warning(None,'CCDASTRO Siril Workflow',str(e))
        raise
    finally:api.disconnect()

if __name__=='__main__':main()
