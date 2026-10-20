import tempfile,unittest,json,sys
from pathlib import Path
from unittest.mock import patch
import numpy as np
from astropy.io import fits
from ccdastro_siril._rcastro import tool_arguments,read_result,probe,run_tool,process_args

class RCAstroTests(unittest.TestCase):
    def schema(self):return {'schemaVersion':6,'license':{'valid':True},'parameters':[{'name':'dn','flag':'--dn','type':'float','min':0,'max':1},{'name':'it','flag':'--it','type':'int','min':1,'max':5}]}
    def test_argument_ranges_and_license_gate(self):
        self.assertEqual(tool_arguments('nxt',{'values':{'dn':.6,'it':2}},self.schema()),['--dn','0.6','--it','2'])
        with self.assertRaises(ValueError):tool_arguments('nxt',{'values':{'dn':2}},self.schema())
        with self.assertRaises(ValueError):tool_arguments('nxt',{'values':{'it':1.5}},self.schema())
        with self.assertRaises(ValueError):tool_arguments('nxt',{'values':{'extra':'bad'}},self.schema())
        with tempfile.TemporaryDirectory() as temp:
            exe=Path(temp)/'rc-astro.exe';exe.touch();schema=self.schema();schema['license']['valid']=False
            with patch('ccdastro_siril._rcastro.process_args',return_value=(0,json.dumps(schema),'')):
                with self.assertRaisesRegex(RuntimeError,'not activated'):probe(exe,'nxt')
    def test_bxt_requires_linear_confirmation(self):
        with self.assertRaisesRegex(ValueError,'linear'):tool_arguments('bxt',{},self.schema())
    def test_output_orientation_and_shape(self):
        data=np.arange(36,dtype=np.float32).reshape(3,3,4)/100
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'out.fit';header=fits.Header();header['ROWORDER']='TOP-DOWN';fits.PrimaryHDU(data,header).writeto(path)
            result=read_result(path,(3,4,3));np.testing.assert_array_equal(result,np.moveaxis(np.flip(data,-2),0,-1))
            with self.assertRaises(ValueError):read_result(path,(4,3,3))
    def test_cancel_stops_child_process(self):
        with self.assertRaises(InterruptedError):process_args(sys.executable,['-c','import time; time.sleep(30)'],lambda:True)
    def test_error_event_rejects_candidate(self):
        data=np.full((3,4,3),.1,np.float32)
        with patch('ccdastro_siril._rcastro.probe',return_value=self.schema()),patch('ccdastro_siril._rcastro.process_args',return_value=(0,'{"event":"error","message":"inference failed"}','')):
            with self.assertRaisesRegex(RuntimeError,'inference failed'):run_tool(data,{'tool':'nxt','executable':sys.executable})
        np.testing.assert_array_equal(data,np.full((3,4,3),.1,np.float32))
    def test_star_difference_alias(self):
        schema={'parameters':[{'name':'difference','flag':'--difference','type':'bool'},{'name':'unscreen','flag':'--unscreen','type':'bool'}]}
        self.assertEqual(tool_arguments('sxt',{'values':{'stars':True,'unscreen':False}},schema),['--difference','--unscreen=false'])
    def test_bad_input_never_accepted(self):
        with self.assertRaises(ValueError):tool_arguments('nxt',{'values':{'dn':float('nan')}},self.schema())

    def test_missing_stars_sidecar_rejects_result(self):
        schema={'schemaVersion':6,'parameters':[{'name':'stars','flag':'--stars','type':'bool'},{'name':'unscreen','flag':'--unscreen','type':'bool'}]}
        def fake_process(executable,args,cancel):
            output=Path(args[args.index('-o')+1]);fits.PrimaryHDU(np.full((3,4,5),.1,np.float32)).writeto(output)
            return 0,json.dumps({'event':'status','phase':'complete','output':str(output)}),''
        with patch('ccdastro_siril._rcastro.probe',return_value=schema),patch('ccdastro_siril._rcastro.process_args',side_effect=fake_process):
            with self.assertRaisesRegex(RuntimeError,'requested stars image'):
                run_tool(np.full((4,5,3),.1,np.float32),{'tool':'sxt','executable':sys.executable})
