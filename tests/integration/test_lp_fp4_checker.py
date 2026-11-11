"""Checker study guards: numerical drift, executable binding, complete costs, closed budgets."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'))
from lp_fp4_checker_study import matches
from lp_fp4_checker_budget import admission_open
from lp_fp4_checker_profile import BINARY


def sample():
    value={k:None for k in ('endpoint','certificate','audits','checkpoint','events','physical','logical','attempted','status','certified','terminal','final_lane','representation','row_scale','shift','image_sha256','model_sha256')}
    value.update(endpoint={'primal':[1.0],'dual':[2.0]},certificate={'checker_binary_sha256':'old','bound':1.0},
        audits=[{'certificate':{'checker_binary_sha256':'old','accepted':True},'endpoint':{'primal':[0.5]}}],
        checkpoint={'raw':[1.0]},events=[{'kind':'window','step':{'gpu_us':2.0,'flags':[0]}}],
        physical=200,logical=200,checker_binary_sha256='old',costs_ns={'checker':4,'iteration':6},solve_ns=10)
    return value


class EvidenceGuards(unittest.TestCase):
    def test_only_timing_and_executable_identity_may_change(self):
        old=sample();new=copy.deepcopy(old)
        new['checker_binary_sha256']='new';new['certificate']['checker_binary_sha256']='new'
        new['audits'][0]['certificate']['checker_binary_sha256']='new'
        new['events'][0]['step']['gpu_us']=9.0
        matches(new,old,{'sha256':'new'})
        for key,value in [('physical',201),('logical',199),('checkpoint',{'raw':[1.00001]}),('endpoint',{'primal':[2.0],'dual':[2.0]})]:
            changed=copy.deepcopy(new);changed[key]=value
            with self.assertRaises(ValueError):matches(changed,old,{'sha256':'new'})
        for field in ('certificate','audits','events'):
            changed=copy.deepcopy(new)
            if field=='certificate':changed[field]['bound']=1.00001
            elif field=='audits':changed[field][0]['certificate']['accepted']=False
            else:changed[field][0]['step']['flags']=[3]
            with self.assertRaises(ValueError):matches(changed,old,{'sha256':'new'})
    def test_hash_and_phase_mismatches_are_not_accepted(self):
        old=sample()
        with self.assertRaises(ValueError):matches(old,old,{'sha256':'different'})
        changed=copy.deepcopy(old);changed['costs_ns']['checker']=5
        with self.assertRaises(ValueError):matches(changed,old,{'sha256':'old'})
    def test_closed_or_unsettled_allocation_blocks_new_jobs(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);(p/'resources').mkdir();admission_open(p)
            (p/'CLOSED.json').write_text('{}')
            with self.assertRaises(ValueError):admission_open(p)
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);(p/'resources').mkdir();(p/'resources/a.reservation.json').write_text('{}')
            with self.assertRaises(ValueError):admission_open(p)


@unittest.skipUnless(BINARY.exists(),'build isolated checker to run process validation')
class ProcessGuards(unittest.TestCase):
    def test_original_binding_domains_and_terminal_eligibility(self):
        model={'schema_version':1,'model_id':'checker-process','variables':[{'id':7,'domain':'continuous','lower':{'kind':'finite','value':0.0},'upper':{'kind':'finite','value':2.0}}],
            'constraints':[{'id':3,'lower':{'kind':'finite','value':1.0},'upper':{'kind':'finite','value':1.0},'terms':[{'variable_id':7,'coefficient':1.0}]}],
            'objective':{'sense':'minimize','offset':0.0,'terms':[{'variable_id':7,'coefficient':1.0}]}}
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);path=p/'model.json';path.write_text(json.dumps(model))
            proc=subprocess.Popen([str(BINARY),'check-service',str(path)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
            try:
                ready=json.loads(proc.stdout.readline())
                for transport in ('completed','cancelled','limit','error','refused'):
                    e={'model_sha256':ready['model_sha256'],'primal':[1.0],'dual':[1.0],'transport':transport}
                    proc.stdin.write(json.dumps({'endpoint':e,'tier':'certified-1e-9'})+'\n');proc.stdin.flush()
                    result=json.loads(proc.stdout.readline())
                    self.assertEqual(result['accepted'],transport=='completed')
                    self.assertEqual(result['checker_binary_sha256'],ready['checker_binary_sha256'])
                proc.stdin.close();self.assertEqual(proc.wait(timeout=5),0)
            finally:
                if proc.poll() is None:proc.kill();proc.wait()
                proc.stdout.close();proc.stderr.close()
            e['transport']='completed'
            for field,value in [('model_sha256','wrong'),('primal',[]),('dual',[1.0,2.0]),('transport','optimal')]:
                bad=copy.deepcopy(e);bad[field]=value;ep=p/(field+'.json');ep.write_text(json.dumps(bad))
                result=subprocess.run([str(BINARY),'check',str(path),str(ep),'certified-1e-9',str(p/(field+'.out'))],capture_output=True,timeout=5)
                self.assertNotEqual(result.returncode,0);self.assertFalse((p/(field+'.out')).exists())

if __name__=='__main__':unittest.main()
