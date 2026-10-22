"""Standalone review UI shared by value, not by a dependency on another project."""
from __future__ import annotations
from copy import deepcopy
import json
from pathlib import Path
import numpy as np
from PyQt6.QtCore import Qt,QTimer
from PyQt6.QtGui import QImage,QPixmap,QPainter,QPen,QColor
from PyQt6.QtWidgets import (QApplication,QDialog,QWidget,QVBoxLayout,QHBoxLayout,QLabel,
 QComboBox,QSlider,QDoubleSpinBox,QPushButton,QCheckBox,QScrollArea,QFileDialog,
 QMessageBox,QListWidget,QListWidgetItem,QInputDialog,QSplitter,QGroupBox)
from ._core import (VERSION,Step,Session,tone_defaults,color_tone,selection_mask,
 curve_value,linked_stretch,image_array,write_report)

def pixmap(data):
    a=np.asarray(np.clip(data,0,1)*255,dtype=np.uint8)
    if a.ndim==2: a=np.repeat(a[...,None],3,-1)
    a=np.ascontiguousarray(a)
    return QPixmap.fromImage(QImage(a.data,a.shape[1],a.shape[0],a.strides[0],QImage.Format.Format_RGB888).copy())

class Preview(QLabel):
    def __init__(self):
        super().__init__(); self.setMinimumSize(260,220);self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet('background:#202124;');self.image=None;self.sample=None;self.pick=None
    def display(self,data): self.image=pixmap(data);self.refresh()
    def refresh(self):
        if self.image: self.setPixmap(self.image.scaled(self.size(),Qt.AspectRatioMode.KeepAspectRatio,Qt.TransformationMode.SmoothTransformation))
    def resizeEvent(self,e): super().resizeEvent(e);self.refresh()
    def mousePressEvent(self,e):
        if self.pick and self.sample is not None and self.image:
            scale=min(self.width()/self.image.width(),self.height()/self.image.height())
            x=(e.position().x()-(self.width()-self.image.width()*scale)/2)/scale
            y=(e.position().y()-(self.height()-self.image.height()*scale)/2)/scale
            if 0<=x<self.image.width() and 0<=y<self.image.height(): self.pick(self.sample[int(y),int(x)])

class CurvePlot(QWidget):
    def __init__(self): super().__init__();self.points=[0,.25,.5,.75,1];self.setMinimumHeight(100)
    def paintEvent(self,e):
        p=QPainter(self);p.fillRect(self.rect(),QColor('#202124'));w=self.width()-16;h=self.height()-16
        p.setPen(QPen(QColor('#555555'),1));p.drawLine(8,h+8,w+8,8)
        p.setPen(QPen(QColor('white'),2));x=np.linspace(0,1,129);y=curve_value(x,self.points)
        for i in range(128):p.drawLine(int(8+x[i]*w),int(8+(1-y[i])*h),int(8+x[i+1]*w),int(8+(1-y[i+1])*h))

def numeric(layout,label,lo,hi,value,callback,decimals=0):
    row=QHBoxLayout();name=QLabel(label);name.setMinimumWidth(150);row.addWidget(name)
    edit=QDoubleSpinBox();edit.setRange(lo,hi);edit.setDecimals(decimals);edit.setValue(value);row.addWidget(edit)
    slider=QSlider(Qt.Orientation.Horizontal);slider.setRange(0,1000);slider.setValue(round((value-lo)/(hi-lo)*1000));row.addWidget(slider,1)
    def from_edit(v):
        slider.blockSignals(True);slider.setValue(round((v-lo)/(hi-lo)*1000));slider.blockSignals(False);callback(v)
    def from_slider(v): edit.setValue(lo+(hi-lo)*v/1000)
    edit.valueChanged.connect(from_edit);slider.valueChanged.connect(from_slider);layout.addLayout(row)
    return edit,slider

class ColorToneDialog(QDialog):
    def __init__(self,data,parent=None):
        super().__init__(parent);self.setWindowTitle('CCDASTRO Color & Tone — independent port')
        self.source=image_array(data);step=max(1,int(np.ceil(max(data.shape[:2])/720)));self.sample=self.source[::step,::step].copy()
        self.settings=tone_defaults();self.output=None;self.channel='RGB';self.loading=False;self.picking=False
        self.timer=QTimer(self);self.timer.setSingleShot(True);self.timer.setInterval(200);self.timer.timeout.connect(self.render_preview)
        root=QVBoxLayout(self);root.addWidget(QLabel('Adjust a copy of the stretched image. White in the mask selects; black protects.'))
        body=QSplitter();root.addWidget(body,1);left=QWidget();ll=QVBoxLayout(left);body.addWidget(left)
        self.mode=QComboBox();self.mode.addItems(['Before','After','Mask','Mask overlay']);self.mode.setCurrentIndex(1);ll.addWidget(self.mode)
        self.preview=Preview();self.preview.sample=self.sample;self.preview.pick=self.pick_pixel;ll.addWidget(self.preview,1)
        self.status=QLabel();self.status.setWordWrap(True);ll.addWidget(self.status);self.graph=CurvePlot();ll.addWidget(self.graph)
        scroll=QScrollArea();scroll.setWidgetResizable(True);body.addWidget(scroll);controls=QWidget();cl=QVBoxLayout(controls);scroll.setWidget(controls);controls.setMinimumWidth(400);scroll.setMinimumWidth(420);body.setStretchFactor(0,1);body.setStretchFactor(1,0)
        self.edits={};self.presets=QComboBox();self.hues=[None,0,30,60,120,180,240,270,300,None]
        self.presets.addItems(['All colors','Red','Orange','Yellow','Green','Cyan','Blue','Purple','Magenta','Custom hue']);cl.addWidget(self.presets)
        def add(key,label,lo,hi,dec=0):
            def updated(v): self.settings[key]=v;self.dirty()
            self.edits[key]=numeric(cl,label,lo,hi,self.settings[key],updated,dec)
        for k,label,lo,hi in [('hue','Hue center',0,360),('width','Hue width',1,180),('feather','Hue feather',1,180),('min_saturation','Minimum saturation (%)',0,100)]:add(k,label,lo,hi)
        self.range=QComboBox();self.range.addItems(['All tones','Shadows','Midtones','Highlights']);cl.addWidget(self.range)
        self.invert=QCheckBox('Invert combined selection');cl.addWidget(self.invert)
        add('amount','Overall amount (%)',0,100)
        for title,fields in [('Tone',[('exposure','Exposure (stops)',-2,2,2),('contrast','Contrast',-100,100,0),('shadows','Shadows',-100,100,0),('highlights','Highlights',-100,100,0),('whites','Whites',-100,100,0),('blacks','Blacks',-100,100,0)]),('Color',[(k,k.title(),-100,100,0) for k in ('saturation','vibrance','temperature','tint')])]:
            cl.addWidget(QLabel('<b>'+title+'</b>'))
            for field in fields:add(*field)
        cl.addWidget(QLabel('<b>Curves: output at 25%, 50%, 75% inputs</b>'));self.channels=QComboBox();self.channels.addItems(['RGB','R','G','B'] if data.ndim==3 else ['RGB']);cl.addWidget(self.channels)
        self.curves=[]
        for i,label in enumerate(['Curve shadows','Curve midtones','Curve highlights']):
            def updated(v,index=i):
                if self.loading:return
                a=self.settings['curves'][self.channel];a[index+1]=float(np.clip(v/100,a[index]+.001,a[index+2]-.001));self.load_curve();self.dirty()
            self.curves.append(numeric(cl,label,1,99,(i+1)*25,updated,1)[0])
        self.channels.currentTextChanged.connect(self.change_channel);cl.addStretch()
        buttons=QHBoxLayout();root.addLayout(buttons)
        pick=QPushButton('Pick hue from image');pick.setEnabled(data.ndim==3);pick.clicked.connect(lambda:setattr(self,'picking',not self.picking));buttons.addWidget(pick)
        reset=QPushButton('Reset adjustments');reset.clicked.connect(self.reset);buttons.addWidget(reset);buttons.addStretch()
        self.apply=QPushButton('Review full-resolution result');self.apply.clicked.connect(self.commit);buttons.addWidget(self.apply)
        cancel=QPushButton('Cancel');cancel.clicked.connect(self.reject);buttons.addWidget(cancel)
        self.mode.currentIndexChanged.connect(self.render_preview);self.presets.currentIndexChanged.connect(self.select_hue)
        self.range.currentTextChanged.connect(lambda v:self.set_field('range',v));self.invert.toggled.connect(lambda v:self.set_field('invert',v))
        self.presets.setEnabled(data.ndim==3)
        if data.ndim!=3:
            for k in ('saturation','vibrance','temperature','tint'):
                for c in self.edits[k]:c.setEnabled(False)
        self.resize(1100,760);self.render_preview()
    def dirty(self):
        if not self.loading:self.apply.setEnabled(False);self.timer.start()
    def set_field(self,k,v):self.settings[k]=v;self.dirty()
    def select_hue(self,i):
        self.settings['hue_enabled']=i!=0
        if self.hues[i] is not None:self.settings['hue']=float(self.hues[i]);self.edits['hue'][0].setValue(self.hues[i])
        self.dirty()
    def change_channel(self,name):self.channel=name;self.load_curve()
    def load_curve(self):
        self.loading=True
        for i,edit in enumerate(self.curves):edit.setValue(self.settings['curves'][self.channel][i+1]*100)
        self.loading=False;self.graph.points=self.settings['curves'][self.channel];self.graph.update()
    def pick_pixel(self,rgb):
        if self.picking and np.ndim(rgb)==1:
            from ._core import hue_degrees
            if np.ptp(rgb)<1e-6:self.status.setText('Choose a colored pixel.');return
            self.presets.setCurrentIndex(9);self.edits['hue'][0].setValue(float(hue_degrees(rgb[None,None])[0,0]));self.picking=False
    def reset(self):
        self.loading=True;self.settings=tone_defaults()
        for k,(edit,slider) in self.edits.items():edit.setValue(self.settings[k])
        self.presets.setCurrentIndex(0);self.range.setCurrentIndex(0);self.invert.setChecked(False);self.channels.setCurrentIndex(0)
        self.loading=False;self.load_curve();self.render_preview()
    def render_preview(self):
        try:
            m=selection_mask(self.sample,self.settings);mode=self.mode.currentText()
            out=self.sample if mode=='Before' else color_tone(self.sample,self.settings)
            if mode=='Mask':out=m
            elif mode=='Mask overlay':
                out=np.repeat(self.sample[...,None],3,-1) if self.sample.ndim==2 else self.sample.copy()
                out=out*(1-.5*m[...,None]);out[...,0]+=.5*m
            self.preview.display(out);self.graph.update();self.apply.setEnabled(True)
            self.status.setText(f'Sampled preview {self.sample.shape[1]}×{self.sample.shape[0]}. Mask coverage {m.mean()*100:.1f}%. Full-resolution review follows before accepting.')
        except Exception as e:self.apply.setEnabled(False);self.status.setText(str(e))
    def commit(self):
        self.timer.stop();self.apply.setEnabled(False)
        try:self.output=color_tone(self.source,self.settings);self.accept()
        except Exception as e:self.status.setText(str(e));self.apply.setEnabled(True)
    def done(self,code):self.timer.stop();super().done(code)

DEFAULTS={'stretch':{'target':.23},'background':{'amount':1.},'green':{'amount':.5}}

class WorkflowDialog(QDialog):
    def __init__(self,host,parent=None):
        super().__init__(parent);self.host=host;data,metadata=host.read();self.session=Session(data,metadata);self.pending=None;self.pending_meta=None;self.pending_step=None;self.steps=[];self.pending_stars=None;self.generated_stars=None;self.stars_method='screen';self.pending_stars_method='screen'
        self.setWindowTitle(f'CCDASTRO {host.title} Workflow {VERSION} — development');root=QVBoxLayout(self)
        note=QLabel('Independent port. Work on copies, review each result, then export. Native commands are optional and require host-specific setup.');note.setWordWrap(True);root.addWidget(note)
        body=QSplitter();root.addWidget(body,1);left=QWidget();ll=QVBoxLayout(left);body.addWidget(left)
        self.list=QListWidget();ll.addWidget(self.list,1)
        self.choice=QComboBox();self.choice.addItems(['Linked automatic stretch','Background plane (simple model)','Green suppression','Host-native command','BlurXTerminator','NoiseXTerminator','StarXTerminator']);ll.addWidget(self.choice)
        for text,callback in [('Add step',self.add_step),('Edit selected parameters',self.edit_step),('Move up',lambda:self.move(-1)),('Move down',lambda:self.move(1)),('Remove step',self.remove_step),('Save preset',self.save_preset),('Load preset',self.load_preset)]:
            b=QPushButton(text);b.clicked.connect(callback);ll.addWidget(b)
        right=QWidget();rl=QVBoxLayout(right);body.addWidget(right)
        self.mode=QComboBox();self.mode.addItems(['Current','Candidate']);rl.addWidget(self.mode);self.mode.currentIndexChanged.connect(self.display)
        self.display_stretch=QCheckBox('Display stretch only (for linear data)');rl.addWidget(self.display_stretch);self.display_stretch.toggled.connect(self.display)
        self.preview=Preview();rl.addWidget(self.preview,1)
        self.status=QLabel('No source file or host image has been modified.');self.status.setWordWrap(True);rl.addWidget(self.status)
        self.action=QHBoxLayout();root.addLayout(self.action)
        for text,callback in [('Preview selected step',self.preview_step),('Color & Tone Studio',self.grade),('Accept candidate',self.accept_candidate),('Discard candidate',self.discard),('Save result + report',self.save_result),('Close',self.reject)]:
            b=QPushButton(text);b.clicked.connect(callback);self.action.addWidget(b)
            if text=='Accept candidate':self.accept_button=b;b.setEnabled(False)
        self.publish_button=None
        if host.title!='Siril':
            self.publish_button=QPushButton('Open result as new host document');self.publish_button.clicked.connect(self.publish);root.addWidget(self.publish_button)
        stars=QPushButton('Review recombination with a registered stars FITS image');stars.clicked.connect(self.recombine_stars);root.addWidget(stars)
        generated=QHBoxLayout();root.addLayout(generated)
        self.use_stars=QPushButton('Recombine with generated stars');self.use_stars.setEnabled(False);self.use_stars.clicked.connect(self.recombine_generated);generated.addWidget(self.use_stars)
        self.save_stars=QPushButton('Save generated stars FITS');self.save_stars.setEnabled(False);self.save_stars.clicked.connect(self.export_generated_stars);generated.addWidget(self.save_stars)
        channels=QPushButton('Independent channel stretch (linear RGB / mono masters)…');channels.clicked.connect(lambda:self.channel_stretch());root.addWidget(channels)
        self.update_button=QPushButton('Check for updates');self.update_button.clicked.connect(self.check_updates)
        from ._updates import install_update_controls
        install_update_controls(self,root)
        setup=QPushButton('Optional tools: locate / rescan');setup.clicked.connect(self.setup_optional_tools);ll.addWidget(setup)
        self.lighthouse_button=QPushButton('Prepare Lighthouse handoff…');self.lighthouse_button.clicked.connect(self.open_lighthouse);ll.addWidget(self.lighthouse_button)
        self.refresh_optional_tools()
        self.resize(1180,790);self.display()
    def refresh_optional_tools(self):
        from ._external import discover
        from PyQt6.QtCore import QSettings
        while self.choice.count()>7:self.choice.removeItem(7)
        store=QSettings('CCDASTRO','SirilWorkflow')
        from ._lighthouse import discover as find_lighthouse
        self.lighthouse_path=find_lighthouse(store.value('optional/lighthouse',''))
        self.lighthouse_button.setEnabled(bool(self.lighthouse_path))
        self.lighthouse_button.setToolTip('Save and open a copy, then launch the separately installed Lighthouse from Siril’s Scripts menu.' if self.lighthouse_path else 'Install Lighthouse using Siril Get Scripts, then use Optional tools: locate / rescan.')
        if discover('graxpert',store.value('optional/graxpert','')):
            self.choice.addItem('GraXpert: background extraction',{'provider':'graxpert','operation':'background'})
            self.choice.addItem('GraXpert: denoising',{'provider':'graxpert','operation':'denoise'})
        if discover('syqon',store.value('optional/syqon','')):
            self.choice.addItem('SyQon Studio tools…',{'provider':'syqon','operation':'prism-essential'})
    def setup_optional_tools(self):
        from ._external_ui import SetupDialog
        if SetupDialog(self).exec():self.refresh_optional_tools()
    def open_lighthouse(self):
        from ._lighthouse import handoff
        if self.pending is not None:
            self.error('Accept or discard the current candidate before opening Lighthouse.');return
        message=('Lighthouse runs as a separate Siril script. Use a stretched image. '
                 'Your accepted result will be saved as a new FITS file and opened in Siril. '
                 'This workflow window will close; then choose Lighthouse from Siril’s Scripts menu. Save your preset and generated stars first if needed. '
                 'Save Lighthouse output separately, then reopen CCDASTRO to continue.')
        if QMessageBox.question(self,'Finish in Lighthouse',message)!=QMessageBox.StandardButton.Yes:return
        path,_=QFileDialog.getSaveFileName(self,'Save accepted result for Lighthouse','','FITS (*.fits *.fit)')
        if not path:return
        try:
            handoff(self.host,self.session.current,self.session.metadata,path,self.lighthouse_path)
        except Exception as error:self.error(error);return
        QMessageBox.information(self,'Lighthouse handoff ready','Your accepted copy is open in Siril. This workflow will now close. Choose Lighthouse from Siril’s Scripts menu. After editing, save its result under a new name.\n\nInstalled script: '+self.lighthouse_path)
        self.accept()
    def external_settings(self,parameters):
        from ._external_ui import SettingsDialog
        try:
            dialog=SettingsDialog(parameters,self)
            return dialog.parameters if dialog.exec() else None
        except Exception as error:self.error(error);return None
    def check_updates(self):
        from ._updates import check_for_updates
        check_for_updates(self)
    def done(self,code):
        controller=getattr(self,'update_controller',None)
        if controller is not None:controller.shutdown()
        super().done(code)
    def error(self,e):QMessageBox.warning(self,'CCDASTRO workflow',str(e))
    def refresh(self):
        self.list.clear()
        for i,s in enumerate(self.steps):
            if s.kind=='rcastro':
                from ._rcastro import TOOLS
                self.list.addItem(f"{i+1}. {TOOLS.get(s.parameters.get('tool'),'RC-Astro')} · {s.parameters.get('device','auto')}")
            elif s.kind=='external':
                from ._external import SYQON_MODELS
                label=SYQON_MODELS.get(s.parameters.get('operation'),s.parameters.get('operation',''))
                self.list.addItem(f"{i+1}. {s.parameters.get('provider','').title()}: {label}")
            else:self.list.addItem(f'{i+1}. {s.kind}: '+json.dumps(s.parameters))
    def add_step(self):
        index=self.choice.currentIndex()
        if isinstance(self.choice.currentData(),dict):
            parameters=self.external_settings(self.choice.currentData())
            if parameters:
                self.discard();self.steps.append(Step('external',parameters));self.refresh();self.list.setCurrentRow(len(self.steps)-1)
            return
        if index>=4:
            from ._rcastro_ui import SettingsDialog
            dialog=SettingsDialog(['bxt','nxt','sxt'][index-4],parent=self)
            if dialog.exec():
                self.discard();self.steps.append(Step('rcastro',dialog.parameters));self.refresh();self.list.setCurrentRow(len(self.steps)-1)
            return
        kind=['stretch','background','green','native'][index]
        p=deepcopy(DEFAULTS.get(kind,{'command':'autostretch','args':[]} if self.host.title=='Siril' else {'command':'stat_stretch','preset':{'target_median':.23}}))
        self.discard();self.steps.append(Step(kind,p));self.refresh();self.list.setCurrentRow(len(self.steps)-1)
    def edit_step(self):
        i=self.list.currentRow()
        if i<0:return
        if self.steps[i].kind=='external':
            parameters=self.external_settings(self.steps[i].parameters)
            if parameters:self.discard();self.steps[i].parameters=parameters;self.refresh();self.list.setCurrentRow(i)
            return
        if self.steps[i].kind=='rcastro':
            from ._rcastro_ui import SettingsDialog
            dialog=SettingsDialog(self.steps[i].parameters['tool'],self.steps[i].parameters,self)
            if dialog.exec():self.discard();self.steps[i].parameters=dialog.parameters;self.refresh();self.list.setCurrentRow(i)
            return
        text,ok=QInputDialog.getMultiLineText(self,'Step parameters','JSON parameters',json.dumps(self.steps[i].parameters,indent=2))
        if ok:
            try:
                p=json.loads(text)
                if not isinstance(p,dict):raise ValueError('Parameters must be a JSON object.')
                self.discard();self.steps[i].parameters=p;self.refresh();self.list.setCurrentRow(i)
            except Exception as e:self.error(e)
    def move(self,delta):
        i=self.list.currentRow();j=i+delta
        if 0<=i<len(self.steps) and 0<=j<len(self.steps):self.discard();self.steps[i],self.steps[j]=self.steps[j],self.steps[i];self.refresh();self.list.setCurrentRow(j)
    def remove_step(self):
        i=self.list.currentRow()
        if i>=0:self.discard();self.steps.pop(i);self.refresh()
    def display(self,*_):
        a=self.pending if self.mode.currentIndex()==1 and self.pending is not None else self.session.current
        a=a[::max(1,int(np.ceil(max(a.shape[:2])/900))),::max(1,int(np.ceil(max(a.shape[:2])/900)))]
        if self.display_stretch.isChecked():
            try:a=linked_stretch(a)
            except ValueError:pass
        self.preview.display(a)
    def preview_step(self):
        i=self.list.currentRow()
        if i<0:return
        if self.steps[i].kind=='channel_stretch':
            self.channel_stretch(self.steps[i].parameters,False);return
        self.discard();s=self.steps[i]
        try:
            if s.kind=='external':
                from ._rcastro_ui import ProcessingDialog
                from ._external import run_external,discover
                from PyQt6.QtCore import QSettings
                settings=deepcopy(s.parameters);provider=settings['provider']
                settings['executable']=discover(provider,QSettings('CCDASTRO','SirilWorkflow').value('optional/'+provider,''))
                result=ProcessingDialog(self.session.current,settings,self,runner=run_external,title=provider.title()+' processing').execute()
                a=result['image'];meta=deepcopy(self.session.metadata);self.pending_stars=result['stars'];self.pending_stars_method=result['method']
            elif s.kind=='rcastro':
                from ._rcastro_ui import ProcessingDialog
                from ._rcastro import find_executable
                from PyQt6.QtCore import QSettings
                settings=deepcopy(s.parameters);settings['executable']=QSettings('CCDASTRO','SirilWorkflow').value('rcastro/executable','') or find_executable()
                result=ProcessingDialog(self.session.current,settings,self).execute()
                a=result['image'];meta=deepcopy(self.session.metadata);self.pending_stars=result['stars'];self.pending_stars_method=result['method']
            elif s.kind=='native':a,meta=self.host.native(self.session.current,self.session.metadata,s.parameters)
            else:a=self.session.candidate(s);meta=deepcopy(self.session.metadata)
            self.pending=image_array(a);self.pending_step=deepcopy(s);self.pending_meta=meta;self.accept_button.setEnabled(True);self.mode.setCurrentIndex(1);self.display()
            self.status.setText('Candidate ready. Accept commits only to the workflow copy; Discard keeps the previous result.')
        except Exception as e:self.error(e)
    def channel_stretch(self,settings=None,add=True):
        from ._channel_ui import ChannelStretchDialog
        try:
            parameters=None if settings is None else {k:v for k,v in settings.items() if k!='input_masters'}
            d=ChannelStretchDialog(self.session.current,self.session.metadata,parameters,self)
            if d.exec():
                if add and len(self.steps)>=32:raise ValueError("Use at most 32 workflow steps.")
                self.discard();p=deepcopy(d.settings)
                if d.input_names:p['input_masters']=list(d.input_names)
                self.pending=d.output;self.pending_step=Step('channel_stretch',p);self.pending_meta=deepcopy(d.metadata)
                if add:
                    self.steps.append(Step('channel_stretch',deepcopy(d.settings)));self.refresh();self.list.setCurrentRow(len(self.steps)-1)
                elif 0<=self.list.currentRow()<len(self.steps):
                    self.steps[self.list.currentRow()].parameters=deepcopy(d.settings);self.refresh()
                self.accept_button.setEnabled(True);self.mode.setCurrentIndex(1);self.display()
                self.status.setText('Full-resolution channel-stretch candidate ready. Accept or discard. Use this instead of a linked final stretch; avoid stretching twice.')
        except Exception as error:self.error(error)
    def grade(self):
        d=ColorToneDialog(self.session.current,self)
        if d.exec():
            self.pending=d.output;self.pending_step=Step('color_tone',deepcopy(d.settings));self.pending_meta=deepcopy(self.session.metadata)
            self.accept_button.setEnabled(True);self.mode.setCurrentIndex(1);self.display();self.status.setText('Full-resolution Color & Tone candidate ready. Accept or discard.')
    def accept_candidate(self):
        if self.pending is None:return
        if (self.pending_step.kind=='rcastro' and self.pending_step.parameters['tool']=='sxt') or (self.pending_step.kind=='external' and self.pending_step.parameters.get('operation','').startswith('axiom')):
            self.generated_stars=self.pending_stars;self.stars_method=self.pending_stars_method
            self.use_stars.setEnabled(self.generated_stars is not None);self.save_stars.setEnabled(self.generated_stars is not None)
        self.session.accept(self.pending_step,self.pending);self.session.metadata=deepcopy(self.pending_meta)
        self.discard();self.status.setText('Pass accepted. Additional passes start from this result. Source remains unchanged.')
    def discard(self):self.pending_stars=None;self.pending=None;self.pending_step=None;self.pending_meta=None;self.accept_button.setEnabled(False);self.mode.setCurrentIndex(0);self.display()
    def save_result(self):
        path,_=QFileDialog.getSaveFileName(self,'Save a new result','','FITS image (*.fit)')
        if not path:return
        if not path.lower().endswith(('.fit','.fits','.fts')):path+='.fit'
        try:
            if Path(path+'.json').exists():raise FileExistsError('Report exists. Choose a new result filename.')
            self.host.save(self.session.current,self.session.metadata,path);write_report(path+'.json',self.session.report());self.status.setText('Saved result and report: '+path)
        except Exception as e:self.error(e)
    def publish(self):
        try:self.host.publish(self.session.current,self.session.metadata);self.status.setText('A new result document was opened. Original document is unchanged.')
        except Exception as e:self.error(e)
    def recombine_stars(self):
        path,_=QFileDialog.getOpenFileName(self,'Select registered stars image','','FITS (*.fit *.fits *.fts)')
        if not path:return
        try:
            from ._io import load_fits
            from ._core import recombine
            stars,_=load_fits(path);amount,ok=QInputDialog.getDouble(self,'Stars brightness','Multiplier',1,0,2,2)
            if not ok:return
            self.pending=recombine(self.session.current,stars,amount,'screen');self.pending_meta=deepcopy(self.session.metadata)
            self.pending_step=Step('recombine',{'stars_path':path,'amount':amount,'method':'screen'})
            self.accept_button.setEnabled(True);self.mode.setCurrentIndex(1);self.display();self.status.setText('Recombined candidate ready. Matching dimensions do not prove registration; inspect before accepting.')
        except Exception as e:self.error(e)
    def save_preset(self):
        from dataclasses import asdict
        path,_=QFileDialog.getSaveFileName(self,'Save workflow preset','','JSON (*.json)')
        if path:
            try:
                if Path(path).exists():raise FileExistsError('Choose a new preset filename.')
                Path(path).write_text(json.dumps({'schema':1,'host':self.host.title,'steps':[dict(asdict(s),parameters={k:v for k,v in s.parameters.items() if k!='executable'}) for s in self.steps]},indent=2),encoding='utf-8')
            except Exception as e:self.error(e)
    def load_preset(self):
        path,_=QFileDialog.getOpenFileName(self,'Load workflow preset','','JSON (*.json)')
        if not path:return
        try:
            p=json.loads(Path(path).read_text(encoding='utf-8'))
            if p.get('schema')!=1 or p.get('host')!=self.host.title:raise ValueError('Preset belongs to a different host or schema.')
            steps=[Step(**s) for s in p['steps']]
            if len(steps)>32 or any(s.kind not in ('channel_stretch','stretch','background','green','native','color_tone','rcastro','external') for s in steps):raise ValueError('Invalid workflow steps.')
            for step in steps:
                if not isinstance(step.parameters,dict):raise ValueError('Step parameters must be an object.')
                if step.kind=='external':
                    from ._external import SYQON_MODELS
                    provider=step.parameters.get('provider');operation=step.parameters.get('operation')
                    if not ((provider=='graxpert' and operation in ('background','denoise')) or (provider=='syqon' and operation in SYQON_MODELS)):raise ValueError('Unsupported optional tool in preset.')
                    step.parameters.pop('executable',None)
                if step.kind=='rcastro':
                    if step.parameters.get('tool') not in ('bxt','nxt','sxt'):raise ValueError('Unsupported RC-Astro tool in preset.')
                    step.parameters.pop('executable',None)
            self.discard();self.steps=steps;self.refresh()
        except Exception as e:self.error(e)

    def recombine_generated(self):
        if self.generated_stars is None:return
        from ._core import recombine
        amount,ok=QInputDialog.getDouble(self,'Generated stars','Stars brightness multiplier',1,0,2,2)
        if not ok:return
        try:
            self.discard();self.pending=recombine(self.session.current,self.generated_stars,amount,self.stars_method)
            self.pending_step=Step('recombine',{'stars_source':'accepted star-separation pass','amount':amount,'method':self.stars_method})
            self.pending_meta=deepcopy(self.session.metadata);self.accept_button.setEnabled(True);self.mode.setCurrentIndex(1);self.display()
            self.status.setText('Generated-stars recombination candidate ready. Compare and accept or discard.')
        except Exception as error:self.error(error)
    def export_generated_stars(self):
        if self.generated_stars is None:return
        path,_=QFileDialog.getSaveFileName(self,'Save generated stars as a new FITS','','FITS (*.fit)')
        if not path:return
        if not path.lower().endswith(('.fit','.fits','.fts')):path+='.fit'
        try:self.host.save(self.generated_stars,self.session.metadata,path);self.status.setText('Generated stars saved: '+path)
        except Exception as error:self.error(error)
