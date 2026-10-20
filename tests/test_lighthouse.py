import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock
import numpy as np
from ccdastro_siril._lighthouse import discover, handoff
from ccdastro_siril._io import save_fits, load_fits


class LighthouseTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.script=self.root/'processing/Lighthouse.py'
        self.script.parent.mkdir();self.script.write_text('raise RuntimeError("must never import")')
        self.source=self.root/'source.fits';self.data=np.full((4,5,3),.2,np.float32)
        save_fits(self.source,self.data,{})
        self.host=Mock();self.host.read.return_value=(self.data,{'source_path':str(self.source)})
        def save(data,meta,path):save_fits(path,data,meta);return str(path)
        self.host.save.side_effect=save
    def test_discovery_does_not_execute_script(self):
        self.assertEqual(discover(roots=[self.root]),str(self.script.resolve()))
        self.assertEqual(discover(str(self.root/'missing.py'),roots=[self.root]),'')
    def test_handoff_prepares_copy_and_preserves_source(self):
        before=self.source.read_bytes();dest=self.root/'copy.fits'
        handoff(self.host,self.data*.8,{},dest,str(self.script))
        self.assertEqual(self.source.read_bytes(),before)
        np.testing.assert_array_equal(load_fits(dest)[0],self.data*.8)
        self.host.api.cmd.assert_called_once_with('load',str(dest.resolve()))
    def test_reject_unsaved_source_before_export(self):
        self.host.read.return_value=(self.data+.1,{'source_path':str(self.source)})
        with self.assertRaisesRegex(ValueError,'unsaved'):handoff(self.host,self.data,{},self.root/'out.fit',str(self.script))
        self.host.save.assert_not_called();self.host.api.cmd.assert_not_called()
    def test_existing_destination_refused(self):
        with self.assertRaises(FileExistsError):handoff(self.host,self.data,{},self.source,str(self.script))
        self.host.api.cmd.assert_not_called()
    def test_failed_launch_restores_source_and_keeps_export(self):
        def command(*args):
            if args[0]=='load' and str(args[1]).endswith('copy.fits'):raise RuntimeError('launch failed')
        self.host.api.cmd.side_effect=command;dest=self.root/'copy.fits'
        with self.assertRaisesRegex(RuntimeError,'launch failed'):handoff(self.host,self.data,{},dest,str(self.script))
        self.assertEqual(self.host.api.cmd.call_args.args,('load',str(self.source.resolve())))
        self.assertTrue(dest.exists())
    def test_missing_script_does_not_touch_host(self):
        with self.assertRaises(FileNotFoundError):handoff(self.host,self.data,{},self.root/'copy.fits',str(self.root/'absent.py'))
        self.host.read.assert_not_called()

if __name__=='__main__':unittest.main()
