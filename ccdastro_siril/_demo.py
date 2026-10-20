"""Offline preview/test mode. No connection to either host application."""
import sys
import numpy as np
from PyQt6.QtWidgets import QApplication
from ._ui import WorkflowDialog
from ._io import save_fits

class DemoHost:
    title='Offline demo'
    def read(self):
        y,x=np.mgrid[0:360,0:600];level=.05+.7*y/360
        data=np.stack([level*(.5+.5*np.cos(2*np.pi*(x/600-c/3))) for c in range(3)],-1).astype(np.float32)
        return data,{}
    def save(self,data,metadata,path):return save_fits(path,data,metadata)
    def publish(self,*args):raise RuntimeError('Offline demo does not publish to a host.')
    def native(self,*args):raise RuntimeError('Native commands require the real host application.')

def main():
    app=QApplication.instance() or QApplication(sys.argv)
    dialog=WorkflowDialog(DemoHost());dialog.exec()

if __name__=='__main__':main()
