import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import unittest,tempfile,json
from pathlib import Path
from unittest.mock import patch
import numpy as np
from astropy.io import fits
from PyQt6.QtWidgets import QApplication
from ccdastro_siril._external import build_arguments,discover,syqon_catalog,run_external
from ccdastro_siril._ui import WorkflowDialog
from ccdastro_siril._core import Step

class Host:
    title='Siril'
    def read(self):return np.full((4,5,3),.3,np.float32),{}

class OptionalToolTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
    def test_only_present_providers_are_offered(self):
        with patch('ccdastro_siril._external.discover',return_value=''):
            dialog=WorkflowDialog(Host());self.assertEqual(dialog.choice.count(),7);dialog.close()
        with patch('ccdastro_siril._external.discover',return_value='installed.exe'):
            dialog=WorkflowDialog(Host());self.assertEqual(dialog.choice.count(),10)
            self.assertIn('GraXpert',dialog.choice.itemText(7));self.assertIn('SyQon',dialog.choice.itemText(9));dialog.close()
    def test_discovery_missing_and_unknown(self):
        with patch('pathlib.Path.is_file',return_value=False):self.assertEqual(discover('graxpert'),'')
        with self.assertRaises(ValueError):discover('other')
    def test_graxpert_version_and_ranges(self):
        settings={'provider':'graxpert','operation':'background','device':'cpu'}
        args=build_arguments(settings,'input.fits','output.fits');self.assertNotIn('-ai_version',args);self.assertIn('false',args)
        settings['ai_version']='1.0.1';self.assertIn('1.0.1',build_arguments(settings,'i','o.fits'))
        settings['ai_version']='--unexpected';self.assertRaises(ValueError,build_arguments,settings,'i','o')
        settings={'provider':'graxpert','operation':'denoise','amount':float('nan')};self.assertRaises(ValueError,build_arguments,settings,'i','o')
    def test_syqon_domain_and_stages(self):
        settings={'provider':'syqon','operation':'prism-essential','domain':'nonlinear'}
        with self.assertRaises(ValueError):build_arguments(settings,'i','o')
        settings={'provider':'syqon','operation':'parallax-nano','correction':False,'reduction':False,'deblur':False}
        with self.assertRaises(ValueError):build_arguments(settings,'i','o')
        settings={'provider':'syqon','operation':'axiom-mini','domain':'linear','stars':True}
        args=build_arguments(settings,'i','o','stars.fits');self.assertIn('--stars-output',args);self.assertNotIn('--model-path',args)
    def test_catalog_filters_unknown_models(self):
        with patch('ccdastro_siril._external.process_args',side_effect=[(0,'SyQon Studio 1.1',''),(0,'axiom-mini free\nunknown paid\nprism-essential included','')]):
            self.assertEqual(syqon_catalog('cli'),['axiom-mini','prism-essential'])
    def test_entitlement_failure_preserves_source(self):
        data=np.full((4,5,3),.3,np.float32);before=data.copy()
        with patch('ccdastro_siril._external.syqon_catalog',return_value=['axiom-mini']),patch('ccdastro_siril._external.process_args',return_value=(4,'','denied')):
            with self.assertRaisesRegex(RuntimeError,'Sign in'):
                run_external(data,{'provider':'syqon','operation':'axiom-mini','executable':__file__})
        np.testing.assert_array_equal(data,before)
    def test_separate_stars_are_not_retained_until_acceptance(self):
        dialog=WorkflowDialog(Host());dialog.steps=[Step('external',{'provider':'syqon','operation':'axiom-mini'})];dialog.refresh();dialog.list.setCurrentRow(0)
        output={'image':np.full((4,5,3),.2,np.float32),'stars':np.full((4,5,3),.1,np.float32),'method':'add'}
        with patch('ccdastro_siril._rcastro_ui.ProcessingDialog.execute',return_value=output):dialog.preview_step()
        self.assertIsNone(dialog.generated_stars);self.assertIsNotNone(dialog.pending_stars);dialog.accept_candidate()
        self.assertTrue(dialog.use_stars.isEnabled());self.assertEqual(dialog.stars_method,'add');dialog.close()
    def test_output_orientation(self):
        data=np.arange(60,dtype=np.float32).reshape(4,5,3)/100;before=data.copy()
        def process(exe,args,cancel):
            output=Path(args[-1]);header=fits.Header();header['ROWORDER']='TOP-DOWN'
            fits.PrimaryHDU(np.flip(np.moveaxis(data,-1,0),axis=-2),header).writeto(output)
            return 0,str(output),''
        with patch('ccdastro_siril._external.syqon_catalog',return_value=['prism-essential']),patch('ccdastro_siril._external.process_args',side_effect=process):
            result=run_external(data,{'provider':'syqon','operation':'prism-essential','executable':__file__})
        np.testing.assert_array_equal(result['image'],before);np.testing.assert_array_equal(data,before)
