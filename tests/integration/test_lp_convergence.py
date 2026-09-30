"""ADR-0032 source-only study identity, failure, accounting and work contracts."""
import copy
from collections import Counter
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'));sys.path.insert(0,str(ROOT/'tests/integration'))
from lp_convergence_budget import protocol, ledger_for
from benchmark_lp_convergence import (jobs,effective,request_for,configuration_hash,write_inputs,run_trial,recover_intents,RECOVERED,SUFFIXES,verify_endpoint)
from report_lp_convergence import check_identity,check_artifacts,check_accounting,work_observation,cost_groups,paired,check_cost
from lp_protocol import read_json,write_json,file_hash,NS
from validate_artifacts import validator
from lp_cost import validate_profile


class ConvergenceTests(unittest.TestCase):
    def fixture(self,root):
        from test_lp_copt_adapter import AdapterStudyTests
        parent,directory=AdapterStudyTests().fixture(root)
        value=protocol();path=root/value['previous_protocol']['path'];write_json(path,parent);value['previous_protocol']['sha256']=file_hash(path)
        path=root/value['decision']['path'];path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes((ROOT/value['decision']['path']).read_bytes())
        value.update(prior_events=parent['prior_events'],prior_gpu_ns=0,prior_ledger_sha256=parent['prior_ledger_sha256'])
        return value,directory

    def job(self,value,kind='timing',config='tuned-fp64'):
        job=copy.deepcopy(next(j for j in jobs(value) if j['kind']==kind and j['configuration']['id']==config))
        job['instance']['model']=dict(path='examples/model-v1.json',sha256=file_hash(ROOT/'examples/model-v1.json'))
        return job

    def identity(self):
        fields=read_json(ROOT/'schemas/lp-convergence-trial-v1.schema.json')['properties']['provenance']['required']
        v={k:'x' for k in fields}
        v.update({k:'a'*64 for k in fields if k.endswith('sha256')})
        v.update(revision='a'*40,dirty=True,cpu_affinity=[0],build_profile='release')
        return v

    def failed_trial(self,d,value,job):
        ledger=MagicMock();ledger.attempted.return_value=set();ledger.campaign_hash=value['budget_authority']['sha256']
        ledger.reserve.return_value=dict(reserved_ns=16*NS)
        with patch('benchmark_lp_convergence.quiet_device',return_value={'elapsed_ns':1}),patch('benchmark_lp_convergence.telemetry',return_value='fixture'),patch('benchmark_lp_convergence.subprocess.Popen') as proc,patch('benchmark_lp_convergence.receipt',return_value={}):
            proc.return_value.returncode=1
            with self.assertRaisesRegex(ValueError,'uncertain'):
                run_trial(value,job,Path('/optimizer'),d,ledger,self.identity(),'b'*64)
        return read_json(d/(job['id']+'.trial.json')),ledger

    def test_frozen_matrix_and_settings(self):
        v=protocol();s=list(jobs(v));self.assertEqual(len(s),176);self.assertEqual(len({j['id'] for j in s}),176)
        self.assertEqual(Counter(j['kind'] for j in s),dict(timing=104,short200=24,short2000=24,profile=24))
        self.assertEqual(s,list(jobs(v)))
        historical={c['id']:c for c in read_json(ROOT/'benchmarks/configs/lp-copt-comparison-v1.json')['configurations']}
        for c in v['configurations']:self.assertEqual(c,historical[c['id']])
        self.assertEqual([j['kind'] for j in s[:40]],['timing']*40)
        for j in s:
            a,b,l=effective(v,j)
            expected=int(j['kind'][5:]) if j['kind'].startswith('short') else 50000
            self.assertEqual(a['iteration_limit'],expected);self.assertEqual(b['iteration_limit'],expected)
            self.assertEqual(a['time_limit_ms'],l['solve_seconds']*1000)
            if 'mixed-65536' in j['instance']['id']:self.assertEqual(j['repetition'],0)
        for k,val in [('additional_gpu_seconds',1),('planned_attempts',177),('order_seed',1),('short_work_limits',[200]),('combined_cap_seconds',1901)]:
            x=copy.deepcopy(v);x[k]=val
            with self.assertRaises(Exception):validator('lp-convergence-study-v1.schema.json').validate(x)

    def test_authority_chain_and_caps_without_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);v,d=self.fixture(root)
            with ledger_for(v,root) as ledger:self.assertEqual(ledger.totals(),0)
            for k,val in [('prior_gpu_ns',1),('prior_ledger_sha256','0'*64),('additional_gpu_seconds',1),('cumulative_gpu_ns',v['cumulative_gpu_ns']+1),('combined_cap_seconds',1901)]:
                x=copy.deepcopy(v);x[k]=val
                with self.assertRaises(ValueError):ledger_for(x,root)
            for k in ['previous_protocol','decision','budget_authority']:
                x=copy.deepcopy(v);x[k]['sha256']='0'*64
                with self.assertRaises(ValueError):ledger_for(x,root)
            for category in v['categories']:
                x=copy.deepcopy(v);x['categories'][category]['seconds']+=1
                with self.assertRaises(ValueError):ledger_for(x,root)
            v['combined_cap_seconds']=3
            for rule in v['categories'].values():rule['seconds']=2
            with ledger_for(v,root) as ledger:
                with self.assertRaises(ValueError):ledger.reserve(v['id']+'-profile-wrong',1,phase='ablations')
                r=ledger.reserve(v['id']+'-timing-one',2,phase='ablations');ledger.settle(r,2*NS)
                with self.assertRaises(ValueError):ledger.reserve(v['id']+'-timing-two',1,phase='ablations')
                with self.assertRaises(ValueError):ledger.reserve(v['id']+'-profile-two',2,phase='repeatability')
                ledger.reserve(v['id']+'-profile-crash',1,phase='repeatability')
            with ledger_for(v,root) as ledger:
                self.assertEqual(ledger.totals(),3*NS);self.assertFalse(ledger.pending())
                with self.assertRaises(ValueError):ledger.reserve(v['id']+'-profile-crash',1,phase='repeatability')
            binding=d/'output.json';old=read_json(binding);write_json(binding,dict(old,output_path=str(root/'other')))
            with self.assertRaises(ValueError):ledger_for(v,root)

    def test_effective_command_inputs_and_substitution(self):
        v=protocol()
        for config in ['tuned-fp64','accumulation-fp32','adaptive-fp64-a32','copt-cpu-pdlp']:
            with tempfile.TemporaryDirectory() as tmp:
                d=Path(tmp);j=self.job(v,config=config);trial,ledger=self.failed_trial(d,v,j)
                request=read_json(d/(j['id']+'.request.json'))
                check_identity(v,j,trial,request,d,Path('/optimizer'),'b'*64)
                check_artifacts(d,trial)
                for k,val in [('config_sha256','0'*64),('work_limit',200),('evidence_format','invalid'),('model_sha256','0'*64)]:
                    x=copy.deepcopy(trial);x[k]=val
                    with self.assertRaises(ValueError):check_identity(v,j,x,request,d,Path('/optimizer'),'b'*64)
                changed=copy.deepcopy(request);changed['command']+=['--bad']
                with self.assertRaises(ValueError):check_identity(v,j,trial,changed,d,Path('/optimizer'),'b'*64)
                a,b,l=effective(v,j);write_json(d/(j['id']+'.method.json'),dict(b,iteration_limit=1))
                with self.assertRaises(ValueError):check_identity(v,j,trial,request,d,Path('/optimizer'),'b'*64)
                ledger.attempted.return_value={j['id']}
                with self.assertRaisesRegex(ValueError,'cannot retry'):run_trial(v,j,Path('/optimizer'),d,ledger,self.identity(),'b'*64)

    def test_partial_recovery_and_artifact_binding(self):
        v=protocol()
        with tempfile.TemporaryDirectory() as tmp:
            d=Path(tmp);j=self.job(v);trial,_=self.failed_trial(d,v,j);dest=d/(j['id']+'.trial.json');dest.unlink()
            for role in ['endpoint','raw_cost','stdout']:(d/(j['id']+SUFFIXES[role])).write_bytes(b'{partial')
            recover_intents(d,{j['id']});recovered=read_json(dest);self.assertEqual(recovered['error'],RECOVERED);self.assertEqual(recovered['status'],'process_failure')
            check_artifacts(d,recovered);before=dest.read_bytes();recover_intents(d,{j['id']});self.assertEqual(dest.read_bytes(),before)
            x=copy.deepcopy(recovered);x['raw_cost']=None
            with self.assertRaises(ValueError):check_artifacts(d,x)
            (d/'other.json').write_bytes(b'{partial');x=copy.deepcopy(recovered);x['endpoint']['path']='other.json'
            with self.assertRaises(ValueError):check_artifacts(d,x)
            worker=dict(elapsed_ns=5,queue_ns=1,leased_ns=4,peak_rss_bytes=10,memory_method='fixture',reason='completed')
            t=dict(worker,status='process_failure',error=RECOVERED);settlement=dict(kind='recover',reserved_ns=10,charged_ns=10)
            check_accounting(t,worker,settlement,True)
            with self.assertRaises(ValueError):check_accounting(dict(t,status='completed'),worker,settlement,True)
            with self.assertRaises(ValueError):check_accounting(t,worker,dict(settlement,charged_ns=4),True)

    def test_work_counts_do_not_double_charge_replay(self):
        e=dict(control=dict(physical_iterations=120,logical_iterations=80,assessments=2),diagnostics=dict(iterations=120,restarts=1,assessment_iteration=80),
               adaptive=dict(proposed_steps=100,audit_steps=15,probe_steps=5,rejected_steps=20,replay_steps=20,rung_proposals=[40,60],step=.5),assessment={})
        w=work_observation(e);self.assertEqual(w['physical'],120);self.assertEqual(w['physical_per_logical'],1.5)
        for field in ['audit_steps','probe_steps','proposed_steps']:
            x=copy.deepcopy(e);x['adaptive'][field]+=1
            with self.assertRaises(ValueError):work_observation(x)
        x=copy.deepcopy(e);x['adaptive']['replay_steps']=101
        with self.assertRaises(ValueError):work_observation(x)
        e['control']['logical_iterations']=0;self.assertIsNone(work_observation(e)['physical_per_logical'])
        native=work_observation(dict(witness=dict(native={'pdlp_iterations':12},iterations=12),assessment={}))
        self.assertNotIn('physical',native)

    def test_nested_costs_and_single_pair_uncertainty(self):
        row=lambda p,i,x:dict(path=p,calls=1,inclusive_ns=i,exclusive_ns=x,min_ns=i,max_ns=i)
        raw=dict(schema_version=1,clock='monotonic_host_thread',elapsed_ns=100,scopes=[row(['solve'],90,20),row(['solve','adaptive_audit'],70,20),row(['solve','adaptive_audit','reference_fp64_update'],50,50)],counters={},unavailable=[])
        validate_profile(raw);g=cost_groups(raw,120);self.assertEqual(sum(g.values()),120);self.assertEqual(g['reference_arithmetic'],50);self.assertEqual(g['unattributed'],30)
        with self.assertRaises(ValueError):cost_groups(raw,80)
        x=copy.deepcopy(raw);x['scopes'][0]['exclusive_ns']=90
        with self.assertRaises(ValueError):validate_profile(x)
        self.assertIsNone(paired([(2,1)],protocol())['ci95']);self.assertIsNone(paired([],protocol()))

    def test_compact_and_external_verifiers_are_not_bypassed(self):
        v=protocol()
        with tempfile.TemporaryDirectory() as tmp:
            d=Path(tmp);j=self.job(v);write_json(d/(j['id']+'.endpoint.json'),{'format':'compact-v1','endpoint':{}})
            with self.assertRaises(Exception):verify_endpoint(v,j,d,Path('/missing'),self.identity())
            j=self.job(v,config='copt-cpu-pdlp');write_json(d/(j['id']+'.endpoint.json'),{})
            with self.assertRaises(Exception):verify_endpoint(v,j,d,Path('/missing'),self.identity())

    def test_duplicate_refusal_preserves_every_prior_artifact(self):
        v=protocol()
        with tempfile.TemporaryDirectory() as tmp:
            d=Path(tmp);j=self.job(v);trial,ledger=self.failed_trial(d,v,j)
            before={p.name:p.read_bytes() for p in d.iterdir() if p.is_file()}
            for attempted in [{j['id']},set()]:
                ledger.attempted.return_value=attempted
                with patch('benchmark_lp_convergence.quiet_device') as quiet,self.assertRaises(ValueError):
                    run_trial(v,j,Path('/unused'),d,ledger,self.identity(),'b'*64)
                quiet.assert_not_called()
                self.assertEqual(before,{p.name:p.read_bytes() for p in d.iterdir() if p.is_file()})

    def test_malformed_recovery_and_missing_worker_profile_stay_unavailable(self):
        from report_lp_convergence import profile_envelope
        v=protocol()
        with tempfile.TemporaryDirectory() as tmp:
            d=Path(tmp);j=self.job(v);trial,_=self.failed_trial(d,v,j);dest=d/(j['id']+'.trial.json');dest.unlink()
            endpoint=d/(j['id']+'.endpoint.json');write_json(endpoint,[])
            recover_intents(d,{j['id']});recovered=read_json(dest)
            self.assertEqual(recovered['error'],RECOVERED);self.assertIsNone(recovered['endpoint_class'])
            self.assertEqual(recovered['endpoint']['sha256'],file_hash(endpoint));check_artifacts(d,recovered)
        raw=dict(elapsed_ns=5,scopes=[])
        self.assertIsNone(profile_envelope(raw,None))
        self.assertEqual(profile_envelope(raw,dict(elapsed_ns=6))['groups_ns'],dict(unattributed=6))
        with self.assertRaises(ValueError):profile_envelope(raw,dict(elapsed_ns=4))
        for pair in [(1,0),(0,1),(-1,1)]:
            with self.assertRaises(ValueError):paired([pair],v)

    def test_review_scope_binds_exact_source_and_excludes_measured_workers(self):
        import io,hashlib,tarfile
        from report_lp_convergence import check_measured_source
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);name='tools/benchmark_lp_convergence.py';p=root/name;p.parent.mkdir();p.write_bytes(b'reviewed')
            with tarfile.open(root/'source.tar','w') as archive:
                item=tarfile.TarInfo(name);item.size=8;archive.addfile(item,io.BytesIO(b'measured'))
            declaration=root/'docs/benchmarks/data/convergence/convergence-review-corrections.json';declaration.parent.mkdir(parents=True)
            entry=dict(path=name,measured_sha256=hashlib.sha256(b'measured').hexdigest(),reviewed_sha256=file_hash(p))
            with patch('report_lp_convergence.ROOT',root):
                with self.assertRaises(ValueError):check_measured_source(root)
                write_json(declaration,dict(files=[entry]));self.assertEqual(check_measured_source(root),[name])
                p.write_bytes(b'wrong')
                with self.assertRaises(ValueError):check_measured_source(root)
                p.write_bytes(b'reviewed')
                for entries in [[entry,entry],[dict(entry,path='tools/lp_copt_comparison.py')],[dict(entry,measured_sha256='0'*64)]]:
                    write_json(declaration,dict(files=entries))
                    with self.assertRaises(ValueError):check_measured_source(root)


    def test_project_acceptance_binds_claimed_configuration_and_work(self):
        from report_lp_convergence import check_project_acceptance_identity
        v=protocol();images={'lp_pdhg_tuned.cubin':'1'*64,'lp_pdhg_precision.cubin':'2'*64}
        configs=[c for c in v['configurations'] if c['backend']=='cuda-lp-tuned']
        for config in configs:
            e=dict(model_sha256='a'*64,requested_backend=config['backend'],
                   record=dict(backend=config['backend'],termination='iteration_limit',
                               options=dict(v['solve'],time_limit_ms=30000,iteration_limit=2000),lp_settings=dict(v['lp_settings'],iteration_limit=2000)),
                   diagnostics=dict(profile=False),execution=dict(settings=copy.deepcopy(config['execution']),
                       code_object_sha256=images['lp_pdhg_precision.cubin' if 'precision' in config or 'adaptive' in config else 'lp_pdhg_tuned.cubin']))
            for field in ['precision','adaptive']:
                if field in config:e[field]=dict(settings=copy.deepcopy(config[field]))
            check=lambda x,c=config:check_project_acceptance_identity(v,c,'a'*64,x,False,images)
            check(e)
            for other in configs:
                if other['id']!=config['id']:
                    with self.assertRaisesRegex(ValueError,'configuration|image'):check(e,other)
            for path,value in [(('model_sha256',),'b'*64),(('requested_backend',),'highs'),(('record','backend'),'highs'),
                               (('record','options','iteration_limit'),50000),(('record','lp_settings','iteration_limit'),200),
                               (('record','options','tolerances','absolute'),1e-6),(('diagnostics','profile'),True),
                               (('record','termination'),'time_limit'),(('execution','code_object_sha256'),'0'*64)]:
                changed=copy.deepcopy(e);node=changed
                for name in path[:-1]:node=node[name]
                node[path[-1]]=value
                with self.subTest(config=config['id'],field=path),self.assertRaises(ValueError):check(changed)

    def test_external_acceptance_binds_original_model_parameters_and_dependencies(self):
        from report_lp_convergence import check_external_acceptance_model,check_external_acceptance_identity
        from lp_copt import parameters
        v=protocol();identity=dict(copt_library_sha256='a'*64,copt_binding_sha256='b'*64)
        original=read_json(ROOT/'examples/model-v1.json')
        for sense in ['minimize','maximize']:
            model=copy.deepcopy(original);model['objective'].update(sense=sense,offset=7.0)
            if sense=='maximize':
                for term in model['objective']['terms']:term['coefficient']=-term['coefficient']
            check_external_acceptance_model(original,sense,model)
            wrong=copy.deepcopy(model);wrong['objective']['offset']=0.0
            with self.assertRaises(ValueError):check_external_acceptance_model(original,sense,wrong)
            wrong=copy.deepcopy(model);wrong['objective']['terms'][0]['coefficient']+=1
            with self.assertRaises(ValueError):check_external_acceptance_model(original,sense,wrong)
            with self.assertRaises(ValueError):check_external_acceptance_model(original,'other',model)
        for gpu in [False,True]:
            method='copt-gpu-pdlp' if gpu else 'copt-cpu-pdlp';solve=dict(v['solve'],time_limit_ms=30000)
            witness=dict(model_sha256='c'*64,requested_backend=method,executed_backend=method,options=solve,
                         parameters=parameters(solve,gpu),library_sha256=identity['copt_library_sha256'],
                         binding_sha256=identity['copt_binding_sha256'],copt_version='8.0.6',gpu_confirmed=gpu)
            endpoint=dict(witness=witness,assessment=dict(classification='certified_success'))
            check=lambda e:check_external_acceptance_identity(v,method,'c'*64,e,identity)
            check(endpoint)
            for path,value in [(('witness','model_sha256'),'d'*64),(('witness','requested_backend'),'highs'),
                               (('witness','options','iteration_limit'),2000),(('witness','parameters','Threads'),2),
                               (('witness','library_sha256'),'0'*64),(('witness','binding_sha256'),'0'*64),
                               (('witness','gpu_confirmed'),not gpu),(('witness','copt_version'),'0.0.0'),
                               (('assessment','classification'),'numerical_rejection')]:
                changed=copy.deepcopy(endpoint);node=changed
                for name in path[:-1]:node=node[name]
                node[path[-1]]=value
                with self.subTest(gpu=gpu,field=path),self.assertRaises(ValueError):check(changed)



if __name__=='__main__':unittest.main()
