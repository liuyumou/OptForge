"""CPU admission for original-model mapping, corrected products and independent checking."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'))
from lp_fp4_accel_model import model,FAMILIES,reference_centered
from lp_fp4_accel_run import BINARY,compact
from lp_fp4_fast_prepare import encode_batch


class ModelContracts(unittest.TestCase):
    def test_generic_fixed_point_has_no_full_state_encoding_floor(self):
        _,d=model('dense-generic-128');n=len(d['c']);raw=np.concatenate([d['target_x'],d['target_y'],d['target_x'],d['target_x'],d['target_y']])
        for k in (2,4):
            got=reference_centered(d,raw,32,1,np.ones(n),k)
            self.assertLess(np.max(abs(got-raw)),2e-14)
            np.testing.assert_array_equal(got[3*n:],raw[3*n:])
    def test_generic_solutions_are_not_eighth_integer_targets(self):
        for family in FAMILIES[8:]:
            _,d=model(family)
            self.assertGreater(np.max(np.abs(d['target_x']*8-np.round(d['target_x']*8))),.1)
            self.assertGreater(np.max(np.abs(d['target_y']*8-np.round(d['target_y']*8))),.1)
            self.assertGreater(np.count_nonzero(d['a'])/d['a'].size,.9)
    def test_original_kkt_target_and_scaling_have_nontrivial_coupling(self):
        for family in FAMILIES[8:]:
            _,d=model(family)
            self.assertLess(np.max(abs(d['a']@d['target_x']-d['rl'])),1e-13)
            self.assertLess(np.max(abs(d['a'].T@d['target_y']-d['c'])),1e-13)
            self.assertGreater(np.max(abs(d['a'][:32,32:])),0)


class RustContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not BINARY.exists():raise unittest.SkipTest('isolated acceleration executable not built')
    def inspect(self,family,equilibrate=True):
        doc,d=model(family)
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'model.json';compact(path,doc)
            r=subprocess.run([str(BINARY),'inspect',str(path)]+([] if equilibrate else ['unscaled']),capture_output=True,text=True,check=True,timeout=20)
        return json.loads(r.stdout),d
    def test_rust_packing_matches_independent_cpu_encoder(self):
        for family in ('dense-rich-65','dense-generic-128','ranged-one-sided'):
            r,d=self.inspect(family);p=r['p'];b=p//32
            a=np.asarray(r['a']).reshape(p,p)
            tiles=a.reshape(b,32,b,32).transpose(0,2,1,3).reshape(b*b,1024)
            for k in (2,4):
                codes,exponents=encode_batch(tiles,4,k)
                self.assertEqual(codes,r['packs'][str(k)]['codes'])
                self.assertEqual(exponents,r['packs'][str(k)]['exponents'])
    def test_scaled_step_and_original_dual_mapping(self):
        for family in ('ill-scaled-coupled','ill-scaled-generic-128','dense-generic-128'):
            r,d=self.inspect(family);n=len(d['c']);p=r['p'];a=np.asarray(r['a']).reshape(p,p)[:n,:n]
            np.testing.assert_array_equal(a,d['a']*np.asarray(r['row_scale'])[:,None])
            y=np.asarray(r['initial'])[p:p+n]*r['row_scale']
            np.testing.assert_array_equal(y,(np.arange(n)%7-3)/64)
            self.assertLessEqual(2.**(-2*r['shift'])*np.linalg.norm(a,1)*np.linalg.norm(a,np.inf),.75)
        scaled,_=self.inspect('ill-scaled-coupled');unscaled,_=self.inspect('ill-scaled-coupled',False)
        self.assertLess(scaled['shift'],unscaled['shift'])
    def test_correction_identity_for_generic_original_operator(self):
        r,d=self.inspect('dense-generic-128');p=r['p'];a=np.asarray(r['a']).reshape(p,p)
        for k in (2,4):
            packed=r['packs'][str(k)];b=p//32;codes=np.asarray(packed['codes'],dtype=np.uint32).reshape(b*b,k,128)
            scales=np.asarray(packed['exponents']).reshape(b*b,k)
            nib=((codes[...,None]>>np.arange(0,32,4))&15).reshape(b*b,k,1024)
            levels=np.array([0,.5,1,1.5,2,3,4,6])
            decoded=np.ldexp(levels[nib&7]*np.where(nib&8,-1,1),scales[...,None]).sum(axis=1)
            approximate=decoded.reshape(b,b,32,32).transpose(0,2,1,3).reshape(p,p)
            errors=np.asarray(packed['error']).sum(axis=1).reshape(2,p,p)[0].T
            self.assertLess(np.max(abs(a-approximate-errors)),1e-15)
            self.assertTrue(packed['has_error'])
    def check(self,doc,x,y,tier,transport='completed'):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);compact(p/'model.json',doc)
            compact(p/'endpoint.json',dict(model_sha256=hashlib.sha256((p/'model.json').read_bytes()).hexdigest(),primal=list(map(float,x)),dual=list(map(float,y)),transport=transport))
            subprocess.run([str(BINARY),'check',str(p/'model.json'),str(p/'endpoint.json'),tier,str(p/'certificate.json')],check=True,capture_output=True,timeout=20)
            return json.loads((p/'certificate.json').read_text())
    def test_all_constructed_original_endpoints(self):
        for family in FAMILIES:
            doc,d=model(family)
            for tier in ('certified-1e-7','certified-1e-9'):
                with self.subTest(family=family,tier=tier):
                    result=self.check(doc,d['target_x'],d['target_y'],tier)
                    self.assertEqual(result['accepted'],family!='infinite-bound-refusal')
    def test_loose_tier_does_not_become_strict_certificate(self):
        bound=lambda x:dict(kind='finite',value=x)
        doc=dict(schema_version=1,model_id='tier',variables=[dict(id=7,domain='continuous',lower=bound(0),upper=bound(1))],constraints=[],objective=dict(sense='minimize',offset=0,terms=[dict(variable_id=7,coefficient=1)]))
        self.assertTrue(self.check(doc,[5e-8],[],'certified-1e-7')['accepted'])
        self.assertFalse(self.check(doc,[5e-8],[],'certified-1e-9')['accepted'])
    def test_cancelled_and_refused_endpoints_are_ineligible(self):
        doc,d=model('coupled-equality')
        for transport in ('cancelled','limit','error','refused'):
            r=self.check(doc,d['target_x'],d['target_y'],'certified-1e-9',transport)
            self.assertFalse(r['eligible']);self.assertFalse(r['accepted'])
    def test_zero_column_direction_is_refused_not_certified(self):
        r,_=self.inspect('infinite-bound-refusal');self.assertIsNotNone(r['unbounded_direction'])


if __name__=='__main__':unittest.main()
