"""CCDASTRO controls for three licensed, separately installed RC-Astro tools."""
from copy import deepcopy
from PyQt6.QtCore import QSettings,QThread,pyqtSignal
from PyQt6.QtWidgets import (QDialog,QVBoxLayout,QHBoxLayout,QFormLayout,QLabel,QLineEdit,QPushButton,QFileDialog,QComboBox,QDoubleSpinBox,QSpinBox,QCheckBox,QDialogButtonBox,QMessageBox,QProgressBar)
from ._rcastro import TOOLS,DEFAULTS,find_executable,run_tool

class SettingsDialog(QDialog):
    def __init__(self,tool,parameters=None,parent=None):
        super().__init__(parent);self.tool=tool;self.parameters=deepcopy(parameters or {});self.setWindowTitle(TOOLS[tool]+' settings');root=QVBoxLayout(self)
        note=QLabel('Uses your separately installed and activated RC-Astro CLI. Processing works on a temporary copy; review the result before accepting.');note.setWordWrap(True);root.addWidget(note)
        row=QHBoxLayout();self.path=QLineEdit(self.parameters.get('executable') or QSettings('CCDASTRO','SirilWorkflow').value('rcastro/executable','') or find_executable());row.addWidget(self.path,1)
        browse=QPushButton('Browse CLI…');browse.clicked.connect(self.browse);row.addWidget(browse);root.addLayout(row)
        form=QFormLayout();root.addLayout(form);self.device=QComboBox();self.device.addItems(['auto','cpu']);self.device.setCurrentText(self.parameters.get('device','auto'));form.addRow('Compute device',self.device)
        self.fields={};values=dict(DEFAULTS[tool]);values.update(self.parameters.get('values',{}))
        specs={'bxt':[('ss','Sharpen stars',0,.7),('sn','Sharpen nonstellar',0,1),('ash','Adjust star halos',-.5,.5),('ansp','Automatic PSF',None,None),('nsd','Manual PSF diameter (pixels)',0,8)],'nxt':[('dn','Denoise strength',0,1),('it','Iterations',1,5)],'sxt':[('stars','Generate stars image',None,None),('unscreen','Unscreen stars for screen recombination',None,None)]}
        for key,label,low,high in specs[tool]:
            if low is None:widget=QCheckBox();widget.setChecked(values[key])
            elif key=='it':widget=QSpinBox();widget.setRange(low,high);widget.setValue(values[key])
            else:widget=QDoubleSpinBox();widget.setDecimals(2);widget.setRange(low,high);widget.setSingleStep(.05);widget.setValue(values[key])
            form.addRow(label,widget);self.fields[key]=widget
        if tool=='bxt':
            self.correct=QCheckBox('Correct aberrations only');self.correct.setChecked(self.parameters.get('correct_only',False));root.addWidget(self.correct)
            self.linear=QCheckBox('I confirm the input is linear (not stretched)');self.linear.setChecked(self.parameters.get('linear_confirmed',False));root.addWidget(self.linear)
            self.fields['ansp'].toggled.connect(lambda checked:self.fields['nsd'].setEnabled(not checked));self.fields['nsd'].setEnabled(not self.fields['ansp'].isChecked())
        if tool=='sxt':
            self.fields['stars'].toggled.connect(self.fields['unscreen'].setEnabled);self.fields['unscreen'].setEnabled(self.fields['stars'].isChecked())
        buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Ok|QDialogButtonBox.StandardButton.Cancel);buttons.accepted.connect(self.commit);buttons.rejected.connect(self.reject);root.addWidget(buttons);self.resize(620,400)
    def browse(self):
        path,_=QFileDialog.getOpenFileName(self,'Select RC-Astro CLI executable',self.path.text(),'Executable (*.exe);;All files (*)')
        if path:self.path.setText(path)
    def commit(self):
        from pathlib import Path
        if not Path(self.path.text()).is_file():QMessageBox.information(self,'RC-Astro setup','Select the installed rc-astro executable.');return
        if self.tool=='bxt' and not self.linear.isChecked():QMessageBox.information(self,'Linear input required','Run BlurXTerminator before stretching and confirm the input is linear.');return
        values={k:(w.isChecked() if isinstance(w,QCheckBox) else w.value()) for k,w in self.fields.items()}
        if self.tool=='sxt' and not values['stars']:values['unscreen']=False
        if self.tool=='bxt' and values['ansp']:values['nsd']=0.
        self.parameters={'tool':self.tool,'executable':self.path.text(),'device':self.device.currentText(),'values':values}
        if self.tool=='bxt':self.parameters.update(linear_confirmed=True,correct_only=self.correct.isChecked())
        QSettings('CCDASTRO','SirilWorkflow').setValue('rcastro/executable',self.path.text());self.accept()

class ToolWorker(QThread):
    completed=pyqtSignal(object);failed=pyqtSignal(str)
    def __init__(self,data,parameters,parent=None,runner=run_tool):super().__init__(parent);self.data=data;self.parameters=parameters;self.runner=runner
    def run(self):
        try:self.completed.emit(self.runner(self.data,self.parameters,self.isInterruptionRequested))
        except Exception as error:self.failed.emit(str(error))

class ProcessingDialog(QDialog):
    def __init__(self,data,parameters,parent=None,runner=run_tool,title=None):
        super().__init__(parent);self.result=None;self.error='';self.setWindowTitle(title or (TOOLS[parameters['tool']]+' processing'));root=QVBoxLayout(self)
        self.label=QLabel('Working on a temporary copy. First use may require the provider’s model setup.');self.label.setWordWrap(True);root.addWidget(self.label)
        bar=QProgressBar();bar.setRange(0,0);root.addWidget(bar);self.cancel=QPushButton('Cancel processing');self.cancel.clicked.connect(self.stop);root.addWidget(self.cancel)
        self.worker=ToolWorker(data,parameters,self,runner);self.worker.completed.connect(self.complete);self.worker.failed.connect(self.fail);self.resize(520,170)
    def stop(self):self.worker.requestInterruption();self.cancel.setEnabled(False);self.label.setText('Cancelling; waiting for the external process to stop…')
    def complete(self,result):self.result=result;super().done(QDialog.DialogCode.Accepted)
    def fail(self,error):self.error=error;super().done(QDialog.DialogCode.Rejected)
    def done(self,code):
        if self.worker.isRunning():self.stop();return
        super().done(code)
    def execute(self):
        self.worker.start();self.exec();self.worker.wait()
        if self.result is None:raise RuntimeError(self.error or 'External-tool operation cancelled.')
        return self.result
