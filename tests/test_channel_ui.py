import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
from PyQt6.QtWidgets import QApplication
from ccdastro_siril._channel_ui import ChannelStretchDialog
from ccdastro_siril._core import Step
from ccdastro_siril._ui import WorkflowDialog
from ccdastro_siril._io import save_fits

class ChannelUITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app=QApplication.instance() or QApplication([])
    def setUp(self):
        x=np.linspace(.002,.04,4096,dtype=np.float32).reshape(64,64)
        self.data=np.stack([x*4,x,x*.4],-1)
    def test_confirmation_dirty_and_modes(self):
        d=ChannelStretchDialog(self.data,{'original':'retained'})
        d.update_preview();self.assertFalse(d.apply.isEnabled())
        d.confirm.setChecked(True);d.update_preview();self.assertTrue(d.apply.isEnabled())
        for i in range(5):d.mode.setCurrentIndex(i);d.display()
        d.settings['targets'][0]=.15;d.dirty();self.assertFalse(d.apply.isEnabled())
        d.update_preview();d.commit();self.assertIsNotNone(d.output)
        np.testing.assert_allclose(np.median(d.output,axis=(0,1)),[.15,.23,.23],atol=1e-4)
        d.close()
    def test_load_masters_and_metadata(self):
        with tempfile.TemporaryDirectory() as td:
            paths=[]
            for c in range(3):
                path=str(Path(td)/f'{c}.fits');save_fits(path,self.data[...,c],{});paths.append(path)
            d=ChannelStretchDialog(self.data,{})
            with patch('ccdastro_siril._channel_ui.QFileDialog.getOpenFileName',side_effect=[(p,'') for p in paths]):d.load_masters()
            self.assertEqual(d.input_names,paths);self.assertFalse(d.confirm.isChecked())
            np.testing.assert_array_equal(d.source,self.data)
            self.assertIn('fits_header',d.metadata)
            d.confirm.setChecked(True);d.update_preview();d.commit();self.assertIsNotNone(d.output);d.close()
    def test_workflow_accept_discard_and_replay(self):
        data=self.data
        class Host:
            title='Siril'
            def read(self):return data.copy(),{'original':'retained'}
        w=WorkflowDialog(Host())
        def execute(d):
            d.confirm.setChecked(True);d.update_preview();d.commit();return 1
        with patch.object(ChannelStretchDialog,'exec',execute):w.channel_stretch()
        self.assertIsNotNone(w.pending);self.assertEqual(w.steps[0].kind,'channel_stretch')
        np.testing.assert_array_equal(w.session.current,data)
        w.discard();np.testing.assert_array_equal(w.session.current,data)
        w.list.setCurrentRow(0)
        with patch.object(ChannelStretchDialog,'exec',execute):w.preview_step()
        self.assertEqual(len(w.steps),1);w.accept_candidate()
        np.testing.assert_allclose(np.median(w.session.current,axis=(0,1)),[.23]*3,atol=1e-4)
        np.testing.assert_array_equal(w.session.source,data);self.assertEqual(w.session.metadata['original'],'retained')
        self.assertEqual(w.session.audit[0]['kind'],'channel_stretch');w.close()
