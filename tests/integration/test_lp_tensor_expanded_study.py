"""New composition/receipt tests only; retained numerical gates are not rerun."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))
import lp_tensor_expanded_study as s
import lp_tensor_expanded_authority as a
from lp_gpup8_test_support import historical_path

class StudyAdapters(unittest.TestCase):
    def setUp(self):
        # No live campaign directory or ledger is required or mutated.
        (a.ROOT / 'artifacts').mkdir(exist_ok=True)
        directory = Path(self.enterContext(tempfile.TemporaryDirectory(dir=a.ROOT / 'artifacts')))
        expanded = 'artifacts/gpup-tensor-expanded-v1/study-v1/'
        for name in ['campaign.json', 'roster.json', 'execution.json']:
            historical_path(expanded + name)
        self.enterContext(patch.object(s, 'D', historical_path(expanded + 'campaign.json').parent))
        self.enterContext(patch.object(s, 'OLD', historical_path('artifacts/gpup-tensor-warp32-v1/study-v1/campaign.json').parent))
        self.enterContext(patch.object(a, 'LEDGER', directory / 'ledger.jsonl'))
        self.enterContext(patch.object(a, 'authority', return_value=a.read(a.DATA / 'authorization-v1.json')))

    def test_frozen_roster_order_and_caps(self):
        old=list(s.legacy.jobs(a.read(s.OLD/'campaign.json')));new=s.jobs()
        self.assertEqual(len(new),76)
        for x,y in zip(old,new):
            self.assertEqual((x['kind'],x['order'],x['repetition'],x.get('ablation'),x['instance'],x['configuration']['id']),
                             (y['kind'],y['order'],y['repetition'],y.get('ablation'),y['instance'],y['configuration']['id']))
        self.assertEqual(sum(s.legacy.effective(s.value(),j)[2]+6 for j in new if j['kind']=='profile'),320)
        self.assertEqual(sum(s.legacy.effective(s.value(),j)[2]+6 for j in new if j['kind']=='timing'),990)

    def test_joint_ledger_rejects_duplicate_before_parent_mutation(self):
        ledger=s.JointLedger('acceptance');key=s.PREFIX+'-acceptance-fixture'
        ledger.events=[dict(sequence=0,kind='reserve',trial_id=key,resource='gpu',phase='repeatability',reservation_id=key,reserved_ns=a.NS,charged_ns=0)]
        with patch.object(s,'remaining',return_value=1000*a.NS),patch.object(s.Ledger,'reserve') as launch:
            with self.assertRaisesRegex(ValueError,'duplicate'):ledger.reserve(key,2)
            launch.assert_not_called()

    def test_joint_ledger_historical_phase_and_cpu_isolation(self):
        ledger=s.JointLedger('acceptance');ledger.events=[]
        with patch.object(s,'remaining',return_value=1000*a.NS),patch.object(s.Ledger,'reserve') as launch:
            with self.assertRaisesRegex(ValueError,'cohort phase'):ledger.reserve(s.PREFIX+'-acceptance-fixture',451)
            auth=a.authority();auth['prior_gpup8_gpu_ns']=2999*a.NS
            with patch.object(a,'authority',return_value=auth):
                with self.assertRaisesRegex(ValueError,'GPUP-8 exhausted'):ledger.reserve(s.PREFIX+'-acceptance-fixture',2)
            launch.assert_not_called()
        with patch.object(s,'remaining',return_value=121*a.NS),patch.object(s.Ledger,'reserve') as launch:
            with self.assertRaisesRegex(ValueError,'joint CPU'):ledger.reserve(s.PREFIX+'-acceptance-fixture',2)
            launch.assert_not_called()

    def test_cached_receipt_reused_and_mismatch_refuses(self):
        with tempfile.TemporaryDirectory(dir=a.ROOT/'artifacts') as temp:
            d=Path(temp);files=[]
            for n in ['model','request','endpoint','binary']:
                p=d/n;p.write_text('{}');files.append(p)
            model,rp,ep,binary=files;cache=d/'cache.json';assessment={'gap_closed':False}
            a.put(cache,dict(status='passed',binding=s.verification_binding(*files),assessment=assessment))
            with patch.object(s.subprocess,'run') as execute:
                self.assertEqual(s.verify_new(model,rp,ep,cache,binary),assessment);execute.assert_not_called()
                ep.write_text('{"changed":true}')
                with self.assertRaisesRegex(ValueError,'cache mismatch'):s.verify_new(model,rp,ep,cache,binary)
                execute.assert_not_called()

    def test_missing_receipt_link_never_reverifies(self):
        j=s.jobs()[0]
        with tempfile.TemporaryDirectory(dir=a.ROOT/'artifacts') as temp:
            d=Path(temp);a.put(d/(j['id']+'.verification.json'),{})
            a.put(d/(j['id']+'.trial.json'),dict(verification=None))
            with patch.object(s,'verify_new') as execute:
                with self.assertRaisesRegex(ValueError,'receipt link'):s.verify_cached(s.value(),j,d,s.identity())
                execute.assert_not_called()

    def test_forecast_composition_equivalence_and_maximum_tail(self):
        roster=[copy.deepcopy(j) for j in s.jobs() if j['kind']=='profile']
        for j in roster:j['configuration']['backend']='lp-tensor-expanded-v1'
        with tempfile.TemporaryDirectory(dir=a.ROOT/'artifacts') as temp:
            d=Path(temp);a.put(d/'forecast-rule.json',s.screen.RULE)
            for j in roster:
                key=j['id'];tail=20000000 if j.get('ablation')=='host-audit' else 1000000
                a.put(d/(key+'.trial.json'),dict(status='completed'))
                a.put(d/(key+'.worker.json'),dict(reason='completed',returncode=0,elapsed_ns=100000000+tail))
                a.put(d/(key+'.endpoint.json'),dict(executor='gpu',outcome=dict(core=dict(iterations=2000,stop='work_horizon',failure=None),first_certified_iteration=200,
                    counts=dict(uncertain=0,useful_windows=1,mma_instructions=32,accepted_nonzero_t=1,accepted_nonzero_f=1)),
                    phases_ns={'execute_total':100000000,'boundary/200/execute_total':50000000,'delivery_original_assessment':1000000}))
            with patch.object(s.legacy,'jobs',return_value=roster),patch.object(s.legacy,'verify_endpoint'):
                direct=s.screen.forecast(s.value(),d,{},False)
            with patch.object(s,'jobs',return_value=roster),patch.object(s,'verify_cached'):
                with s.inherited_readers():adapted=s.screen.forecast(s.value(),d,{},False)
            self.assertEqual(direct,adapted);self.assertTrue(adapted['passed']);self.assertEqual(adapted['maximum_producer_tail_ns'],20000000)
            self.assertTrue(all(r['forecast_ns']==71000000 for r in adapted['forecasts']))

if __name__=='__main__':unittest.main()
