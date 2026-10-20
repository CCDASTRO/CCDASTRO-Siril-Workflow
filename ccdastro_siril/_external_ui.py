"""Configuration of installed optional applications, kept outside shared presets."""
from copy import deepcopy
from pathlib import Path
from PyQt6.QtCore import QSettings
from PyQt6.QtWidgets import (QDialog,QVBoxLayout,QHBoxLayout,QFormLayout,QLabel,QLineEdit,QPushButton,QFileDialog,QComboBox,QDoubleSpinBox,QCheckBox,QDialogButtonBox,QGroupBox,QMessageBox)
from ._external import discover,syqon_catalog,SYQON_MODELS
from ._rcastro_ui import ProcessingDialog

class SetupDialog(QDialog):
    def __init__(self,parent=None):
        super().__init__(parent);self.setWindowTitle('Optional GraXpert and SyQon installations');root=QVBoxLayout(self);self.paths={};store=QSettings('CCDASTRO','SirilWorkflow')
        note=QLabel('Select installed executables or leave blank for automatic detection. SyQon sign-in, model installation and product access are managed in SyQon Studio.');note.setWordWrap(True);root.addWidget(note)
        for provider,label in [('graxpert','GraXpert'),('syqon','SyQon Studio CLI')]:
            root.addWidget(QLabel(label));row=QHBoxLayout();path=QLineEdit(discover(provider,store.value('optional/'+provider,'')));row.addWidget(path,1);self.paths[provider]=path
            button=QPushButton('Browse…');button.clicked.connect(lambda _,key=provider:self.browse(key));row.addWidget(button);root.addLayout(row)
        links=QLabel('<a href="https://www.graxpert.com/">GraXpert</a> · <a href="https://syqon.eu/develop">SyQon Studio and CLI</a>');links.setOpenExternalLinks(True);root.addWidget(links)
        buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Ok|QDialogButtonBox.StandardButton.Cancel);buttons.accepted.connect(self.commit);buttons.rejected.connect(self.reject);root.addWidget(buttons);self.resize(650,250)
    def browse(self,key):
        path,_=QFileDialog.getOpenFileName(self,'Locate installed executable',self.paths[key].text(),'Executable (*.exe);;All files (*)')
        if path:self.paths[key].setText(path)
    def commit(self):
        for provider,edit in self.paths.items():
            if edit.text() and not Path(edit.text()).is_file():QMessageBox.information(self,'Optional tool missing','The selected '+provider+' executable was not found.');return
        store=QSettings('CCDASTRO','SirilWorkflow')
        for provider,edit in self.paths.items():store.setValue('optional/'+provider,edit.text())
        self.accept()

def query_catalog(data,settings,cancel):return syqon_catalog(settings['executable'],cancel)

class SettingsDialog(QDialog):
    def __init__(self,parameters,parent=None):
        super().__init__(parent);self.parameters=deepcopy(parameters);self.provider=parameters['provider'];self.setWindowTitle('GraXpert settings' if self.provider=='graxpert' else 'SyQon model settings');root=QVBoxLayout(self);form=QFormLayout();root.addLayout(form)
        self.amount=QDoubleSpinBox();self.amount.setRange(0,1);self.amount.setSingleStep(.05);self.amount.setDecimals(2);self.amount.setValue(parameters.get('amount',.5 if self.provider=='graxpert' else 1));form.addRow(('Background smoothing' if parameters['operation']=='background' else 'Denoise strength') if self.provider=='graxpert' else 'Application amount',self.amount)
        if self.provider=='graxpert':
            self.device=QComboBox();self.device.addItems(['auto','cpu']);self.device.setCurrentText(parameters.get('device','auto'));form.addRow('Compute device',self.device)
            self.version=QLineEdit(parameters.get('ai_version','latest'));form.addRow('AI model version (or latest)',self.version)
            self.correction=QComboBox();self.correction.addItems(['Subtraction','Division']);self.correction.setCurrentText(parameters.get('correction','Subtraction'))
            if parameters['operation']=='background':form.addRow('Background correction',self.correction)
        else:
            store=QSettings('CCDASTRO','SirilWorkflow');executable=discover('syqon',store.value('optional/syqon',''))
            catalog=ProcessingDialog(None,{'executable':executable},self,runner=query_catalog,title='Discovering SyQon models').execute()
            self.model=QComboBox()
            for model in catalog:self.model.addItem(SYQON_MODELS[model],model)
            index=self.model.findData(parameters.get('operation','prism-essential'));self.model.setCurrentIndex(max(0,index));form.addRow('Model advertised by CLI',self.model)
            self.domain=QComboBox();self.domain.addItems(['linear','nonlinear']);self.domain.setCurrentText(parameters.get('domain','linear'));form.addRow('Input image domain',self.domain)
            self.stars=QCheckBox('Generate a stars image');self.stars.setChecked(parameters.get('stars',True));root.addWidget(self.stars)
            self.parallax=QGroupBox('Parallax stages');layout=QFormLayout(self.parallax);root.addWidget(self.parallax);self.stages={}
            for name,label in [('correction','Stellar correction'),('reduction','Star reduction'),('deblur','Deblur')]:
                box=QCheckBox();box.setChecked(parameters.get(name,True));layout.addRow(label,box);self.stages[name]=box
            self.family=QComboBox();self.family.addItems(['aesthetics','classic']);self.family.setCurrentText(parameters.get('family','aesthetics'));layout.addRow('Premium Parallax family',self.family)
            self.reduction=QDoubleSpinBox();self.reduction.setRange(0,10);self.reduction.setValue(parameters.get('reduction_level',3));layout.addRow('Star reduction level',self.reduction)
            self.deblur=QDoubleSpinBox();self.deblur.setRange(0,1);self.deblur.setSingleStep(.05);self.deblur.setValue(parameters.get('deblur_strength',.5));layout.addRow('Deblur strength',self.deblur)
            note=QLabel('The CLI listing describes supported models; it does not prove your account has installed or licensed each model. SyQon validates access when processing starts. Studio manages the compute device.');note.setWordWrap(True);root.addWidget(note)
            self.model.currentIndexChanged.connect(self.refresh);self.refresh()
        buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Ok|QDialogButtonBox.StandardButton.Cancel);buttons.accepted.connect(self.commit);buttons.rejected.connect(self.reject);root.addWidget(buttons);self.resize(650,400)
    def refresh(self):
        model=self.model.currentData();self.stars.setVisible(model.startswith('axiom'));self.parallax.setVisible(model.startswith('parallax'));self.family.setEnabled(model=='parallax')
    def commit(self):
        self.parameters['amount']=self.amount.value()
        if self.provider=='graxpert':self.parameters.update(device=self.device.currentText(),ai_version=self.version.text().strip(),correction=self.correction.currentText())
        else:
            model=self.model.currentData();domain=self.domain.currentText()
            if model in ('prism-essential','prism-advanced','prism-legacy-v2','deep-gradient') and domain!='linear':QMessageBox.information(self,'Linear input required','Choose linear input for this model or select a compatible model.');return
            if model=='prism-legacy-v1' and domain!='nonlinear':QMessageBox.information(self,'Non-linear input required','Prism Legacy V1 requires non-linear input.');return
            if model.startswith('parallax') and not any(c.isChecked() for c in self.stages.values()):QMessageBox.information(self,'Enable a stage','Enable at least one Parallax stage.');return
            self.parameters.update(operation=model,domain=domain,device='auto',stars=self.stars.isChecked(),family=self.family.currentText(),reduction_level=self.reduction.value(),deblur_strength=self.deblur.value(),**{name:box.isChecked() for name,box in self.stages.items()})
        self.accept()
