"""CCDASTRO Siril Workflow 0.1.0.
Author: Chuck Faranda / CCDASTRO, Inc. https://ccdastro.com/
Copyright (c) 2026 CCDASTRO, Inc. All rights reserved.
Launch from Siril's Python scripts menu. No PixInsight installation is used.
"""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))

def main():
    import sirilpy
    sirilpy.check_module_version('>=1.0.25')
    from PyQt6.QtWidgets import QApplication,QMessageBox
    from ccdastro_siril._host import Host
    from ccdastro_siril._ui import WorkflowDialog
    api=sirilpy.SirilInterface();api.connect()
    app=QApplication.instance() or QApplication([])
    try:
        api.cmd('requires','1.4.4')
        window=WorkflowDialog(Host(api));window.exec()
    except Exception as e:
        QMessageBox.warning(None,'CCDASTRO Siril Workflow',str(e))
        raise
    finally:api.disconnect()

if __name__=='__main__':main()
