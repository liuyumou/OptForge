"""SPEC-0019 construction, independent identity and clean-source budget contracts."""
import copy
import hashlib
from pathlib import Path
import struct
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools')); sys.path.insert(0, str(ROOT / 'tests/integration'))
from lp_copt_matrix import prepare, load
from lp_copt_adapter_accept import readback_fixture
from lp_copt_adapter_budget import protocol, ledger_for
from benchmark_lp_copt_adapter import jobs, command, request_for, configuration_hash, SUFFIXES, run_trial, recover_intents
from benchmark_lp_copt import effective
from lp_protocol import read_json, write_json, file_hash, NS
from report_lp_copt_adapter import check_identity, check_artifacts
from validate_artifacts import validator


class MatrixTests(unittest.TestCase):
    def test_exact_canonical_csc_and_objective(self):
        d = readback_fixture(); result = prepare(d)
        self.assertEqual(result['variable_ids'], [3,9,17]); self.assertEqual(result['row_ids'], [2,6,11,15])
        self.assertEqual(result['indptr'], [0,2,4,4]); self.assertEqual(result['indices'], [1,3,1,2])
        self.assertEqual(result['data'], [-2.25,1.0,.125,-0.0])
        self.assertEqual(struct.pack('>d',result['data'][-1]),struct.pack('>d',-0.0))
        self.assertEqual(result['lhs'], [0,-3,-1e30,-7]); self.assertEqual(result['rhs'], [0,4,9,1e30])
        self.assertEqual(result['c'], [2,-1.5,0]); self.assertEqual(result['offset'],7.125)
        self.assertEqual(d,readback_fixture(), 'builder must not mutate original')
        d['objective']['sense']='maximize'; self.assertEqual(prepare(d)['c'],result['c'])
        d['constraints']=[]; self.assertEqual(prepare(d)['shape'],[0,3])
        d['variables']=[]; d['objective']['terms']=[]; self.assertEqual(prepare(d)['indptr'],[0])

    def test_rejects_ambiguous_and_unrepresentable_inputs(self):
        changes=[lambda d:d['variables'].append(copy.deepcopy(d['variables'][0])),
                 lambda d:d['constraints'].append(copy.deepcopy(d['constraints'][0])),
                 lambda d:d['constraints'][0]['terms'].append(copy.deepcopy(d['constraints'][0]['terms'][0])),
                 lambda d:d['objective']['terms'].append(copy.deepcopy(d['objective']['terms'][0])),
                 lambda d:d['constraints'][0]['terms'][0].update(variable_id=99),
                 lambda d:d['variables'][0].update(domain='integer'),
                 lambda d:d['variables'][0]['lower'].update(value=1e30),
                 lambda d:d['variables'][0]['upper'].update(value=-3),
                 lambda d:d['variables'][0].update(lower=dict(kind='positive_infinity')),
                 lambda d:d['variables'][0]['lower'].update(value=float('nan')),
                 lambda d:d['objective'].update(offset=float('inf')),
                 lambda d:d['objective'].update(sense='unknown'),
                 lambda d:d['objective']['terms'][0].update(coefficient=True)]
        for change in changes:
            d=readback_fixture();change(d)
            with self.assertRaises((ValueError,KeyError)):prepare(d)
        for location in ['row','objective']:
            for coefficient in [1e-10,-1e-10,1e-11,float('inf'),float('nan')]:
                d=readback_fixture(); terms=d['constraints'][0]['terms'] if location=='row' else d['objective']['terms'];terms[0]['coefficient']=coefficient
                with self.assertRaises(ValueError):prepare(d)
            d=readback_fixture();d['objective']['terms'][0]['coefficient']=1.0000000000000002e-10
            self.assertEqual(prepare(d)['c'][1],1.0000000000000002e-10)

    def test_bulk_api_preserves_sense_offset_and_empty_names(self):
        model=MagicMock();sparse=MagicMock();cp=SimpleNamespace(COPT=SimpleNamespace(MINIMIZE=1,MAXIMIZE=-1))
        d=prepare(readback_fixture());d['sense']='maximize';load(cp,model,d,sparse)
        model.loadMatrix.assert_called_once();model.setObjSense.assert_called_once_with(-1);model.setObjConst.assert_called_once_with(7.125)
        self.assertEqual(model.setNames.call_count,2)
        model.reset_mock();d['variable_ids']=[];d['row_ids']=[];load(cp,model,d,sparse);model.setNames.assert_not_called()

    def test_missing_dependency_never_solves_or_falls_back(self):
        import lp_copt_bulk
        model=MagicMock();cp=SimpleNamespace(Envr=lambda:SimpleNamespace(createModel=lambda _:model),LogCallback=object)
        with tempfile.TemporaryDirectory() as tmp:
            directory=Path(tmp);write_json(directory/'model.json',readback_fixture());write_json(directory/'solve.json',protocol()['solve'])
            a=SimpleNamespace(model=directory/'model.json',config=directory/'solve.json',output=directory/'endpoint.json',binary=Path('/binary'),method='copt-cpu-pdlp',device='cpu',cost_profile=None)
            with patch.dict(sys.modules,{'coptpy':cp,'scipy':None}),patch('lp_copt_bulk.file_hash',return_value='a'*64),patch('lp_copt_bulk.signal.signal'),patch('lp_copt_bulk.subprocess.run',return_value=SimpleNamespace(returncode=0)) as certify:
                lp_copt_bulk.run(a)
            witness=read_json(a.output.with_suffix('.witness.json'))
            self.assertEqual(witness['status'],'backend_failure');self.assertIsNone(witness['executed_backend']);model.solveLP.assert_not_called();certify.assert_called_once()
            self.assertTrue(any('ModuleNotFoundError' in s for s in witness['limitations']))
            a.method='copt-gpu-pdlp'
            with patch.dict('os.environ',{},clear=True),self.assertRaisesRegex(ValueError,'lease'):lp_copt_bulk.run(a)

    def test_cancellation_reaches_native_interrupt_and_retains_status(self):
        import lp_copt_bulk
        model=MagicMock();callbacks={};model.solveLP.side_effect=lambda:callbacks[lp_copt_bulk.signal.SIGINT](None,None)
        attrs=dict(SimplexIter=0,BarrierIter=0,PDLPIter=0,SolvingTime=0.0,MemPeak=0.0,LpStatus=3,HasLpSol=0)
        model.getAttr.side_effect=lambda key:attrs[key]
        cp=SimpleNamespace(Envr=lambda:SimpleNamespace(createModel=lambda _:model),LogCallback=object,COPT=SimpleNamespace(INFINITY=1e30,MINIMIZE=1,MAXIMIZE=-1,OPTIMAL=1,TIMEOUT=2,INTERRUPTED=3,ITERLIMIT=4))
        with tempfile.TemporaryDirectory() as tmp:
            directory=Path(tmp);write_json(directory/'model.json',readback_fixture());write_json(directory/'solve.json',protocol()['solve'])
            a=SimpleNamespace(model=directory/'model.json',config=directory/'solve.json',output=directory/'endpoint.json',binary=Path('/binary'),method='copt-cpu-pdlp',device='cpu',cost_profile=None)
            with patch.dict(sys.modules,{'coptpy':cp,'scipy':SimpleNamespace(sparse=MagicMock())}),patch('lp_copt_bulk.file_hash',return_value='a'*64),patch('lp_copt_bulk.signal.signal',side_effect=lambda sig,cb:callbacks.update({sig:cb})),patch('lp_copt_bulk.subprocess.run',return_value=SimpleNamespace(returncode=0)):
                lp_copt_bulk.run(a)
            model.interrupt.assert_called_once();self.assertEqual(read_json(a.output.with_suffix('.witness.json'))['status'],'interrupted')


class AdapterStudyTests(unittest.TestCase):
    def fixture(self, root):
        import test_lp_adaptive_cost
        parent,directory=test_lp_adaptive_cost.AdaptiveCostStudyTests().fixture(root)
        from lp_setup_budget import protocol as setup_protocol
        setup=setup_protocol();parent_path=root/setup['previous_protocol']['path'];write_json(parent_path,parent);setup['previous_protocol']['sha256']=file_hash(parent_path)
        decision=root/setup['decision']['path'];decision.parent.mkdir(parents=True,exist_ok=True);decision.write_bytes((ROOT/setup['decision']['path']).read_bytes())
        setup.update(prior_events=parent['prior_events'],prior_gpu_ns=0,prior_ledger_sha256=parent['prior_ledger_sha256'])
        value=protocol();p=root/value['previous_protocol']['path'];write_json(p,setup);value['previous_protocol']['sha256']=file_hash(p)
        p=root/value['decision']['path'];p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((ROOT/value['decision']['path']).read_bytes())
        value.update(prior_events=setup['prior_events'],prior_gpu_ns=0,prior_ledger_sha256=setup['prior_ledger_sha256'])
        return value,directory

    def test_clean_source_authority_caps_and_interrupted_reservations(self):
        with tempfile.TemporaryDirectory() as tmp:
            value,directory=self.fixture(Path(tmp))
            with ledger_for(value,Path(tmp)) as ledger:self.assertEqual(ledger.totals(),0)
            for field,replacement in [('additional_gpu_seconds',1),('cumulative_gpu_ns',value['cumulative_gpu_ns']+1),('prior_gpu_ns',1),('prior_ledger_sha256','0'*64)]:
                wrong=copy.deepcopy(value);wrong[field]=replacement
                with self.assertRaises(ValueError):ledger_for(wrong,Path(tmp))
            for category in value['categories']:
                wrong=copy.deepcopy(value);wrong['categories'][category]['seconds']+=1
                with self.assertRaises(ValueError):ledger_for(wrong,Path(tmp))
            for r in value['categories'].values():r['seconds']=2
            value['combined_cap_seconds']=3
            with ledger_for(value,Path(tmp)) as ledger:
                with self.assertRaises(ValueError):ledger.reserve(value['id']+'-profile-wrong',1,phase='ablations')
                r=ledger.reserve(value['id']+'-timing-complete',2,phase='ablations');ledger.settle(r,2*NS)
                ledger.reserve(value['id']+'-accept-crash',1,phase='repeatability')
            with ledger_for(value,Path(tmp)) as ledger:
                self.assertEqual(ledger.usage('accept'),NS)
                with self.assertRaises(ValueError):ledger.reserve(value['id']+'-profile-over',1,phase='repeatability')
                with self.assertRaises(ValueError):ledger.reserve(value['id']+'-accept-crash',1,phase='repeatability')
            write_json(directory/'output.json',dict(campaign_sha256='a'*64,output_path='wrong'))
            with self.assertRaises(ValueError):ledger_for(value,Path(tmp))

    def test_grid_and_strict_schema(self):
        v=protocol();schedule=list(jobs(v));self.assertEqual(len(schedule),84);self.assertEqual(len({j['id'] for j in schedule}),84)
        self.assertEqual(sum(j['kind']=='timing' for j in schedule),72);self.assertEqual(schedule,list(jobs(v)))
        for field,replacement in [('order_seed',42),('timing_repetitions',4),('additional_gpu_seconds',1),('dependencies',dict(path='wrong',sha256='0'*64))]:
            wrong=copy.deepcopy(v);wrong[field]=replacement
            with self.assertRaises(Exception):validator('lp-copt-adapter-study-v1.schema.json').validate(wrong)
        for job in schedule:
            solve,_,limits=effective(v,job);self.assertEqual(solve['time_limit_ms'],(10 if 'small' in job['instance']['id'] else 30)*1000)
            self.assertEqual(limits['output_bytes'],33554432)

    def test_requests_and_trial_intents_bind_adapter_without_launch(self):
        v=protocol();identity=dict(revision='a'*40,dirty=False,source_tree_sha256='a'*64,binary_sha256='b'*64,code_object_sha256=None,highs_library_sha256='d'*64,rustc='fixture',cargo='fixture',os='fixture',cpu='fixture',cpu_affinity=[0],build_profile='release',device=v['device'],telemetry_before='unavailable',telemetry_after='unavailable',copt_library_sha256='c'*64,copt_binding_sha256='e'*64,schema_snapshot_sha256='f'*64)
        class Admitted(Exception):pass
        class Boundary:
            campaign_hash=v['budget_authority']['sha256']
            def reserve(self,*args,**kwargs):raise Admitted()
        with tempfile.TemporaryDirectory() as tmp:
            directory=Path(tmp);binary=Path('/binary')
            for job in list(jobs(v))[:6]:
                job=copy.deepcopy(job);job['instance']['model']=dict(path='examples/lp-model-v1.json',sha256=file_hash(ROOT/'examples/lp-model-v1.json'))
                with patch('benchmark_lp_copt_adapter.quiet_device',return_value=None),self.assertRaises(Admitted):run_trial(v,job,binary,directory,Boundary(),identity,'a'*64)
                trial=read_json(directory/(job['id']+'.intent.json'));request=read_json(directory/(job['id']+'.request.json'))
                check_identity(v,job,trial,request,directory,binary,'a'*64)
                for field in ['adapter_id','dependencies_sha256','requested_backend','config_id']:
                    wrong=copy.deepcopy(trial);wrong[field]='wrong'
                    with self.assertRaises(ValueError):check_identity(v,job,wrong,request,directory,binary,'a'*64)
                wrong=copy.deepcopy(request);wrong['command'][0]='/different'
                with self.assertRaises(ValueError):check_identity(v,job,trial,wrong,directory,binary,'a'*64)
                wrong=copy.deepcopy(trial);del wrong['endpoint']
                with self.assertRaises(Exception):validator('lp-copt-adapter-trial-v1.schema.json').validate(wrong)
                recover_intents(directory,{job['id']});self.assertIn('no retry',read_json(directory/(job['id']+'.trial.json'))['error'])

    def test_same_bytes_under_another_filename_are_rejected(self):
        from benchmark_lp import reference
        with tempfile.TemporaryDirectory() as tmp:
            d=Path(tmp);trial=dict(id='trial')
            for role,suffix in SUFFIXES.items():
                (d/('trial'+suffix)).write_text('{}');trial[role]=reference(d,d/('trial'+suffix))
            check_artifacts(d,trial)
            for role,suffix in SUFFIXES.items():
                (d/('other'+suffix)).write_text('{}');wrong=copy.deepcopy(trial);wrong[role]=reference(d,d/('other'+suffix))
                with self.assertRaisesRegex(ValueError,'filename'):check_artifacts(d,wrong)
            wrong=copy.deepcopy(trial);wrong['witness']=None
            with self.assertRaises(ValueError):check_artifacts(d,wrong)


if __name__=='__main__':unittest.main()
