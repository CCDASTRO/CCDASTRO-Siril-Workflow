import importlib,unittest,tempfile,json
from pathlib import Path
from types import SimpleNamespace
import numpy as np
from ccdastro_siril import _core as core
from ccdastro_siril._host import Host,normalize,to_siril
from ccdastro_siril._io import load_fits,save_fits

class ProcessingTests(unittest.TestCase):
    def setUp(self):self.data=np.random.default_rng(12).uniform(.02,.8,(65,31,3)).astype(np.float32)
    def test_identity_and_source(self):
        before=self.data.copy();out=core.color_tone(self.data,core.tone_defaults());np.testing.assert_array_equal(out,before);np.testing.assert_array_equal(self.data,before)
        out[0,0]=0;self.assertFalse(np.array_equal(out,self.data))
    def test_masks_hue_wrap_and_grey(self):
        p=core.tone_defaults();p['hue_enabled']=True
        x=np.array([[[.8,.02,.03],[.8,.03,.02],[.1,.6,.1],[.3,.3,.3]]],dtype=np.float32)
        mask=core.selection_mask(x,p);self.assertGreater(mask[0,0],.9);self.assertGreater(mask[0,1],.9);self.assertEqual(mask[0,2],0);self.assertEqual(mask[0,3],0)
        p['min_saturation']=100;self.assertTrue((core.selection_mask(x,p)==0).all())
    def test_exposure_and_amount(self):
        p=core.tone_defaults();p['exposure']=1
        x=np.full((4,4),.2,np.float32);np.testing.assert_allclose(core.color_tone(x,p),.4)
        p['amount']=50;np.testing.assert_allclose(core.color_tone(x,p),.3)
    def test_curves_monotone(self):
        for p in [[0,.1,.6,.9,1],[0,.01,.02,.03,1]]:
            out=core.curve_value(np.linspace(0,1,10001),p);self.assertTrue((np.diff(out)>=0).all());self.assertTrue(((out>=0)&(out<=1)).all())
    def test_cancel_and_validation(self):
        p=core.tone_defaults();p['exposure']=.2
        with self.assertRaises(InterruptedError):core.color_tone(self.data,p,lambda:True)
        p['exposure']=float('nan')
        with self.assertRaises(ValueError):core.color_tone(self.data,p)
        with self.assertRaises(ValueError):core.image_array(np.zeros((4,4),dtype=np.uint8))
    def test_stretch_target(self):
        x=np.linspace(.001,.04,10000,dtype=np.float32).reshape(100,100)
        out=core.linked_stretch(x,.23);self.assertAlmostEqual(float(np.median(out)),.23,places=3)
    def test_plane(self):
        y,x=np.mgrid[0:80,0:90];a=(.15+.02*x/89+.03*y/79).astype(np.float32)
        out=core.background_plane(a);self.assertLess(float(np.std(out)),1e-6)
    def test_session_and_recombine(self):
        session=core.Session(self.data,{'source':'untouched'});step=core.Step('green',{'amount':.5});candidate=session.candidate(step)
        self.assertEqual(len(session.audit),0);session.accept(step,candidate);self.assertEqual(len(session.audit),1);np.testing.assert_array_equal(session.source,self.data)
        self.assertEqual(core.recombine(self.data,self.data*.1).shape,self.data.shape)
        with self.assertRaises(ValueError):core.recombine(self.data,self.data[:3])
    def test_fits_roundtrip_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'result.fit';save_fits(path,self.data,{});out,meta=load_fits(path);np.testing.assert_array_equal(out,self.data)
            with self.assertRaises(FileExistsError):save_fits(path,self.data,{})
    def test_color_tone_reference(self):
        path=Path(__file__).with_name('color-tone-reference.json')
        for case in json.loads(path.read_text()):
            p=core.tone_defaults();p.update(case['settings']);rgb=np.asarray(case['input'],dtype=np.float32).reshape(2,2,3)
            result=core.color_tone(rgb,p);np.testing.assert_allclose(result,np.asarray(case['expected']).reshape(2,2,3),atol=2e-7,rtol=0)

    def test_fits_header_preserved(self):
        from astropy.io import fits
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'header.fit'
            header=fits.Header();header['OBJECT']='CCDASTRO synthetic';header['CRPIX1']=12.5
            save_fits(path,self.data,{'original_header':header})
            with fits.open(path) as hdus:
                self.assertEqual(hdus[0].header['OBJECT'],'CCDASTRO synthetic')
                self.assertEqual(hdus[0].header['CRPIX1'],12.5)

class SirilAdapterTests(unittest.TestCase):
    def test_layout(self):
        x=np.arange(60,dtype=np.float32).reshape(3,4,5)/60
        np.testing.assert_array_equal(to_siril(normalize(x)),x)
    def test_new_file_and_original_restore(self):
        class Fake:
            def __init__(self,path):self.path=str(path);self.data=np.full((3,4,5),.2,np.float32);self.calls=[]
            def get_image_pixeldata(self,**kw):return self.data.copy()
            def get_image_fits_header(self,**kw):return ''
            def get_image_filename(self):return self.path
            def save_image_file(self,data,header,path):save_fits(path,normalize(data),{});return True
            def cmd(self,*args):
                self.calls.append(args)
                if args[0]=='load':a,_=load_fits(args[1]);self.data=to_siril(a);self.path=args[1]
                elif args[0]=='autostretch':self.data*=2
                else:raise ValueError('test command failure')
        with tempfile.TemporaryDirectory() as folder:
            source=Path(folder)/'source.fit';save_fits(source,np.full((4,5,3),.2,np.float32),{})
            fake=Fake(source);host=Host(fake);data,meta=host.read();out,_=host.native(data,meta,{'command':'autostretch','args':[]})
            np.testing.assert_allclose(out,.4);np.testing.assert_allclose(fake.data,.2);self.assertEqual(fake.path,str(source))
            with self.assertRaises(ValueError):host.native(data,meta,{'command':'save','args':['bad.fit']})
            with self.assertRaises(ValueError):host.native(data,meta,{'command':'spcc','args':[]})
            np.testing.assert_allclose(fake.data,.2);self.assertEqual(fake.path,str(source))

if __name__=='__main__':unittest.main()
