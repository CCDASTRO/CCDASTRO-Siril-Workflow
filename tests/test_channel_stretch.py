import unittest
import numpy as np
from ccdastro_siril._channel_stretch import defaults,plan,apply_plan,stretch
from ccdastro_siril._core import Session,Step

class ChannelStretchTests(unittest.TestCase):
    def setUp(self):
        x=np.linspace(.002,.08,128*128,dtype=np.float32).reshape(128,128)
        self.a=np.stack([x*4,x,x*.4],-1)
    def test_equal_targets_balance_and_preserve_source(self):
        original=self.a.copy();result=stretch(self.a)
        np.testing.assert_array_equal(self.a,original)
        np.testing.assert_allclose(np.median(result,axis=(0,1)),[.23]*3,atol=2e-5)
        self.assertTrue(np.isfinite(result).all());self.assertTrue(((result>=0)&(result<=1)).all())
        self.assertTrue((np.diff(result.reshape(-1,3),axis=0)>=0).all())
    def test_targets_and_zero_amount(self):
        result=stretch(self.a,targets=[.12,.3,.4],amounts=[100,100,0])
        np.testing.assert_allclose(np.median(result,axis=(0,1))[:2],[.12,.3],atol=2e-5)
        np.testing.assert_array_equal(result[...,2],self.a[...,2])
        np.testing.assert_array_equal(stretch(self.a,amounts=[0,0,0]),self.a)
    def test_partial_blend(self):
        full=stretch(self.a);half=stretch(self.a,amounts=[50]*3)
        np.testing.assert_allclose(half,(self.a+full)/2,atol=1e-7)
    def test_fixed_preview_plan(self):
        settings=defaults();p=plan(self.a,settings)
        np.testing.assert_array_equal(apply_plan(self.a[::3,::3],p),apply_plan(self.a,p)[::3,::3])
    def test_invalid_and_blank(self):
        for a in [self.a[...,0],self.a*100,self.a.astype(np.uint16),self.a*np.nan]:
            with self.assertRaises(ValueError):stretch(a)
        for kwargs in [dict(targets=[.2]),dict(targets=[True,.2,.2]),dict(amounts=[101]*3),dict(targets=[float('nan')]*3)]:
            with self.assertRaises(ValueError):stretch(self.a,**kwargs)
        blank=self.a.copy();blank[...,0]=0
        with self.assertRaises(ValueError):stretch(blank)
        self.assertTrue(np.isfinite(stretch(blank,amounts=[0,100,100])).all())
    def test_candidate_cancel_and_audit(self):
        session=Session(self.a);step=Step('channel_stretch',defaults())
        with self.assertRaises(InterruptedError):session.candidate(step,lambda:True)
        np.testing.assert_array_equal(session.current,self.a)
        candidate=session.candidate(step);session.accept(step,candidate)
        self.assertEqual(session.report()['steps'][0]['parameters'],defaults())
        np.testing.assert_array_equal(session.source,self.a)
if __name__=='__main__':unittest.main()
