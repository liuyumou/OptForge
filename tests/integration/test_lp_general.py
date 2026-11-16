"""General LP source, input, grouping and independent resource boundaries."""
import hashlib
import json
from pathlib import Path
import re
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))
from lp_general_common import ROOT,CPU_CAPS,GPU_CAPS,ref
from lp_general_implied import derive,verify
import copy
from lp_general_budget import accounting,admission_open
from lp_general_models import generate,FAMILIES
from lp_general_public import parse

def body(source,name):
    start=source.index('{',source.index('fn '+name+'('));depth=1;end=start+1
    while depth:
        depth+=(source[end]=='{')-(source[end]=='}');end+=1
    return source[start+1:end-1]

class GeneralTests(unittest.TestCase):
    def test_core_sources_remain_exact_to_retained_derivation(self):
        p=ROOT/'research/lp-general-lowbit/upstream/provenance.json'
        for item in json.loads(p.read_text())['files']:
            a=(ROOT/item['path']).read_bytes();b=(ROOT/item['retained_source']).read_bytes()
            self.assertEqual(a,b);self.assertEqual(hashlib.sha256(a).hexdigest(),item['sha256'])

    def test_checkpoint_work_and_host_step_bodies_are_shared_formulas(self):
        old=(ROOT/'research/lp-general-lowbit/upstream/control.rs.source').read_text()
        new=(ROOT/'research/lp-general-lowbit/src/control.rs').read_text()
        for name in ['checkpoint','restore','remaining','check_pending','next_chunk','buffers','commit_steps','charge_extra','replace_endpoint','host_step','advance_host','iterate']:
            self.assertEqual(body(old,name),body(new,name),name)

    def test_weight_formula_preserves_original_arithmetic(self):
        old=body((ROOT/'research/lp-general-lowbit/upstream/pdhg.rs.source').read_text(),'next_weight')
        source=(ROOT/'research/lp-general-lowbit/src/merit.rs').read_text().split("impl EngineMerit",1)[1]
        new=body(source,'next_weight');new=new[new.index('let primal_movement'):]
        def normalized(s):
            s=re.sub(r'//[^\n]*','',s).replace('self.norm','norm').replace('self.settings.primal_weight','self.settings().primal_weight')
            for a,b in [('1.0e-12','1e-12'),('1.0e-6','1e-6'),('1.0e6','1e6'),('0.0','0.')]:s=s.replace(a,b)
            return ''.join(s.split())
        self.assertEqual(normalized(old),normalized(new))

    def test_generated_operators_are_independent_and_not_square_equalities(self):
        for family in FAMILIES:
            a,wa=generate(family,33,1);b,wb=generate(family,33,2)
            self.assertNotEqual(a['constraints'],b['constraints']);self.assertNotEqual(wa['rows'],wa['columns'])
            self.assertTrue(any(r['lower']!=r['upper'] for r in a['constraints']))
            self.assertNotIn('primal',a);self.assertEqual(wa['partition'],wb['partition'])

    def test_public_converter_range_bounds_and_unsupported_data(self):
        source='NAME tiny\nROWS\n N cost\n E row\nCOLUMNS\n x cost 1 row 2\nRHS\n rhs row 3\nRANGES\n rng row -2\nBOUNDS\n FR bnd x\nENDATA\n'
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'tiny.mps';p.write_text(source);model,_=parse(p)
            self.assertEqual(model['constraints'][0]['lower']['value'],1.)
            self.assertEqual(model['constraints'][0]['upper']['value'],3.)
            self.assertEqual(model['variables'][0]['lower']['kind'],'negative_infinity')
            for bad in [source.replace('ENDATA','QUADOBJ'),source.replace(' x cost 1 row 2'," marker 'MARKER' 'INTORG'"),source.replace('RANGES','RHS')]:
                p.write_text(bad)
                with self.assertRaises(ValueError):parse(p)

    def test_new_budget_never_imports_historical_funding(self):
        self.assertEqual(sum(CPU_CAPS.values()),240000);self.assertEqual(sum(GPU_CAPS.values()),30000)
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);(p/'resources').mkdir()
            (p/'resources/failed.reservation.json').write_text(json.dumps(dict(phase='admission',gpu=True,cpu_ns=400000000000,gpu_ns=100000000000)))
            cpu,gpu=accounting(p);self.assertEqual(cpu['admission'],400000000000);self.assertEqual(gpu['admission'],100000000000)
            with self.assertRaises(ValueError):admission_open(p)

    def test_failed_child_adjustments_bind_receipts_and_charge_full_reservation(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'artifacts') as d:
            p=Path(d);(p/'resources').mkdir();(p/'charge-adjustments').mkdir()
            rp=p/'resources/child.reservation.json';sp=p/'resources/child.settlement.json'
            rp.write_text(json.dumps(dict(phase='development',gpu=True,cpu_ns=400,gpu_ns=100)))
            sp.write_text(json.dumps(dict(cpu_ns=40,gpu_ns=10)))
            a=dict(original_job='child',reservation=ref(rp),settlement=ref(sp),phase='development',cpu_ns=360,gpu_ns=90)
            ap=p/'charge-adjustments/child.json';ap.write_text(json.dumps(a))
            cpu,gpu=accounting(p);self.assertEqual(cpu['development'],400);self.assertEqual(gpu['development'],100)
            a['cpu_ns']=359;ap.write_text(json.dumps(a))
            with self.assertRaises(ValueError):accounting(p)
            a['cpu_ns']=360;ap.write_text(json.dumps(a));sp.write_text(json.dumps(dict(cpu_ns=20,gpu_ns=5)))
            with self.assertRaises(ValueError):accounting(p)

    def test_missing_supervision_disposition_never_releases_gpu_or_science(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'artifacts') as d:
            p=Path(d);(p/'resources').mkdir()
            rp=p/'resources/interrupted.reservation.json';sp=p/'resources/interrupted.settlement.json'
            rp.write_text(json.dumps(dict(phase='development',gpu=True,cpu_ns=400,gpu_ns=100)))
            dp=p/'disposition.json';dp.write_text(json.dumps(dict(kind='missing-supervisor-receipt-disposition',
                reservation=ref(rp),cleanup_observed_empty=True,campaign_stopped=True,
                historical_supervision_established=False,charged_cpu_ns=800,charged_gpu_ns=200)))
            settlement=dict(phase='development',gpu=True,cpu_ns=800,gpu_ns=200,status='refused',overrun=True,
                            resource=None,interruption_disposition=ref(dp))
            sp.write_text(json.dumps(settlement))
            admission_open(p,phase='reporting')
            for phase,gpu in [('admission',True),('development',False),('confirmation',False)]:
                with self.assertRaises(ValueError):admission_open(p,phase=phase,gpu=gpu)
            settlement['cpu_ns']=399;sp.write_text(json.dumps(settlement))
            with self.assertRaises(ValueError):admission_open(p,phase='reporting')
            settlement['cpu_ns']=800;sp.write_text(json.dumps(settlement));dp.write_text('{}')
            with self.assertRaises(ValueError):admission_open(p,phase='reporting')

    def test_original_row_bound_proofs_reject_unproved_changes(self):
        def finite(v):return dict(kind='finite',value=v)
        model=dict(variables=[dict(id=1,lower=finite(0.),upper=dict(kind='positive_infinity')),
                              dict(id=2,lower=dict(kind='negative_infinity'),upper=finite(0.))],
                   constraints=[dict(id=3,lower=dict(kind='negative_infinity'),upper=finite(6.),
                                     terms=[dict(variable_id=1,coefficient=2.),dict(variable_id=2,coefficient=-3.)])])
        tight,proof=derive(model);verify(model,tight,proof)
        self.assertEqual(tight['variables'][0]['upper'],finite(3.));self.assertEqual(tight['variables'][1]['lower'],finite(-2.))
        for k in range(len(proof)):
            bad=copy.deepcopy(proof);bad[k]['value']=0.
            with self.assertRaises(ValueError):verify(model,tight,bad)
        changed=copy.deepcopy(tight);changed['constraints'][0]['upper']=finite(5.)
        with self.assertRaises(ValueError):verify(model,changed,proof)

if __name__=='__main__':unittest.main()
