import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import unittest
from unittest.mock import patch
import numpy as np
from PyQt6.QtWidgets import QApplication
from ccdastro_siril._ui import WorkflowDialog
from ccdastro_siril._core import Step

class UIHost:
    title='Siril'
    def read(self):return np.full((8,10,3),.3,np.float32),{}

class RCAstroReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
    def test_stars_are_available_only_after_acceptance(self):
        dialog=WorkflowDialog(UIHost());dialog.steps=[Step('rcastro',{'tool':'sxt','values':{'stars':True,'unscreen':True}})];dialog.refresh();dialog.list.setCurrentRow(0)
        output={'image':np.full((8,10,3),.2,np.float32),'stars':np.full((8,10,3),.1,np.float32),'method':'screen'}
        with patch('ccdastro_siril._rcastro_ui.ProcessingDialog.execute',return_value=output):dialog.preview_step()
        self.assertIsNotNone(dialog.pending_stars);self.assertIsNone(dialog.generated_stars);self.assertFalse(dialog.use_stars.isEnabled())
        dialog.discard();self.assertIsNone(dialog.pending_stars);self.assertIsNone(dialog.generated_stars)
        with patch('ccdastro_siril._rcastro_ui.ProcessingDialog.execute',return_value=output):dialog.preview_step()
        dialog.accept_candidate();self.assertIsNotNone(dialog.generated_stars);self.assertTrue(dialog.use_stars.isEnabled())
        with patch('PyQt6.QtWidgets.QInputDialog.getDouble',return_value=(1,True)):dialog.recombine_generated()
        np.testing.assert_allclose(dialog.pending,.28,atol=1e-6);np.testing.assert_allclose(dialog.session.current,.2)
        self.assertEqual(len(dialog.session.audit),1);dialog.close()
