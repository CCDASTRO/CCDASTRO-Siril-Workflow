"""Review individual linear channels and their recombination."""
from copy import deepcopy
import numpy as np
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QComboBox, QPushButton, QCheckBox, QFileDialog)
from ._channel_stretch import defaults, plan, apply_plan


class ChannelStretchDialog(QDialog):
    def __init__(self, data, metadata, settings=None, parent=None):
        super().__init__(parent)
        from ._ui import Preview, numeric
        self.setWindowTitle('Independent channel stretch — linear input')
        self.source = np.asarray(data)
        self.metadata = deepcopy(metadata)
        self.settings = deepcopy(settings if settings is not None else defaults())
        self.output = None
        self.input_names = []
        self.parameters = None
        root = QVBoxLayout(self)
        note = QLabel('Use before the final stretch. R/G/B are output slots: for SHO, for example, map SII/Ha/OIII. '
            'Equal median targets balance channels artistically and change relative emission brightness. '
            'Lower R target or amount if red dominates. Mono masters must already be registered; no alignment is performed.')
        note.setWordWrap(True); root.addWidget(note)
        load = QPushButton('Load three registered mono FITS masters into R / G / B…')
        load.clicked.connect(self.load_masters); root.addWidget(load)
        self.confirm = QCheckBox('I confirm the input is linear and the channels are registered')
        self.confirm.toggled.connect(self.dirty); root.addWidget(self.confirm)
        self.mode = QComboBox(); self.mode.addItems(['Recombined RGB', 'R channel', 'G channel', 'B channel', 'Before RGB'])
        self.mode.currentIndexChanged.connect(self.display); root.addWidget(self.mode)
        self.preview = Preview(); root.addWidget(self.preview, 1)
        self.status = QLabel('Choose settings, confirm linear input, then update the preview.'); self.status.setWordWrap(True); root.addWidget(self.status)
        for c, name in enumerate(('R', 'G', 'B')):
            def changed(v, index=c, key='targets'):
                self.settings[key][index] = float(v); self.dirty()
            numeric(root, name+' median target', .01, .5, self.settings['targets'][c], changed, 3)
            def amount(v, index=c):
                self.settings['amounts'][index] = float(v); self.dirty()
            numeric(root, name+' stretch amount (%)', 0, 100, self.settings['amounts'][c], amount, 1)
        buttons = QHBoxLayout(); root.addLayout(buttons)
        update = QPushButton('Update preview'); update.clicked.connect(self.update_preview); buttons.addWidget(update)
        self.apply = QPushButton('Review full-resolution result'); self.apply.setEnabled(False)
        self.apply.clicked.connect(self.commit); buttons.addWidget(self.apply)
        close = QPushButton('Cancel'); close.clicked.connect(self.reject); buttons.addWidget(close)
        self.resize(850, 800)

    def dirty(self, *_):
        self.parameters = None; self.apply.setEnabled(False)
        self.status.setText('Settings changed. Update the preview before applying.')

    def load_masters(self):
        paths = []
        for name in ('R', 'G', 'B'):
            path, _ = QFileDialog.getOpenFileName(self, 'Select linear master for '+name+' output slot', '', 'FITS (*.fit *.fits *.fts)')
            if not path: return
            paths.append(path)
        try:
            from ._io import load_fits
            loaded = [load_fits(path) for path in paths]
            arrays = [item[0] for item in loaded]
            if any(a.ndim != 2 for a in arrays) or len({a.shape for a in arrays}) != 1:
                raise ValueError('Select three mono masters with identical dimensions; register them in the host first.')
            self.source = np.stack(arrays, axis=-1)
            self.metadata = deepcopy(loaded[0][1])
            self.input_names = paths
            self.confirm.setChecked(False); self.dirty()
            self.status.setText('Loaded R / G / B: '+' | '.join(paths)+'. Confirm registration and linear input.')
        except Exception as error: self.status.setText(str(error))

    def update_preview(self):
        self.dirty()
        try:
            if not self.confirm.isChecked(): raise ValueError('Confirm linear input and registration first.')
            self.parameters = plan(self.source, self.settings)
            stride = max(1, int(np.ceil(max(self.source.shape[:2])/900)))
            self.sample = self.source[::stride, ::stride]
            self.after = apply_plan(self.sample, self.parameters)
            self.display(); self.apply.setEnabled(True)
            self.status.setText('Sampled preview uses the same fixed stretch plan as the full-resolution result. '+
                ' / '.join(f'{n}: black {p["black"]:.5f}' for n,p in zip('RGB', self.parameters)))
        except Exception as error:
            self.parameters = None; self.status.setText(str(error))

    def display(self, *_):
        if self.parameters is None: return
        mode = self.mode.currentIndex()
        self.preview.display(self.after if mode == 0 else self.sample if mode == 4 else self.after[..., mode-1])

    def commit(self):
        if self.parameters is None or not self.confirm.isChecked(): return
        self.apply.setEnabled(False)
        try:
            self.output = apply_plan(self.source, self.parameters)
            self.accept()
        except Exception as error:
            self.status.setText(str(error)); self.apply.setEnabled(True)
