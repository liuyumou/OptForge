"""ADR-0026 contracts; budget tests need no campaign artifacts or installed COPT."""
import copy
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'))
from lp_copt_budget import protocol,ledger_for
from benchmark_lp_copt import jobs,effective,run_trial
from lp_protocol import Ledger,NS,file_hash,read_json,write_json
from lp_cost import Profile,validate_profile,interval_union
from lp_copt_comparison import parameters
from validate_artifacts import validator

class CostContracts(unittest.TestCase):
    def test_hierarchy_overlap_and_partial_observations(self):
        p=Profile(True)
        with p.scope('outer'):
            for _ in range(3):
                with p.scope('inner'):pass
        raw=p.finish();validate_profile(raw)
        self.assertEqual(next(s['calls'] for s in raw['scopes'] if s['path']==['outer','inner']),3)
        wrong=copy.deepcopy(raw);wrong['scopes'][0]['exclusive_ns']+=1
        with self.assertRaises(ValueError):validate_profile(wrong)
        wrong=copy.deepcopy(raw);wrong['scopes'].append(wrong['scopes'][0])
        with self.assertRaises(ValueError):validate_profile(wrong)
        with p.scope('partial'):self.assertTrue(p.finish()['unavailable'])
        self.assertEqual(interval_union([(10,20),(15,30),(30,31),(2,4)]),23)
        self.assertEqual(interval_union([]),0)
        with self.assertRaises(ValueError):interval_union([(3,1)])

    def test_partial_hierarchy_requires_explicit_stack_observation(self):
        p=Profile(True)
        with p.scope('parent'):
            with p.scope('child'):pass
            raw=p.finish()
            validate_profile(raw)
        raw['unavailable']=['native destruction is opaque']
        with self.assertRaises(ValueError):validate_profile(raw)

    def test_worker_clocks_outcomes_and_collector_envelope(self):
        from report_lp_copt import check_worker,check_collector_envelope
        worker=dict(elapsed_ns=10,queue_ns=2,leased_ns=10,peak_rss_bytes=100,memory_method='test',reason='completed')
        trial=dict(worker,status='completed',error=None)
        check_worker(trial,worker)
        for key in ['elapsed_ns','queue_ns','leased_ns','peak_rss_bytes','memory_method']:
            with self.assertRaises(ValueError):check_worker(dict(trial,**{key:'altered'}),worker)
        with self.assertRaises(ValueError):check_worker(dict(trial,status='timeout'),worker)
        with self.assertRaises(ValueError):check_worker(dict(trial,error='supervisor failed'),worker)
        check_worker(dict(trial,status='process_failure',error='supervisor failed'),worker)
        check_collector_envelope(dict(elapsed_ns=10),'solve',10)
        with self.assertRaises(ValueError):check_collector_envelope(dict(elapsed_ns=11),'solve',10)

    def test_component_children_counters_and_requalified_limits(self):
        from report_lp_copt import checked_component_rows,qualified_trial
        p=Profile(True)
        with p.scope('copt'):
            with p.scope('host_certification'):
                child=Profile(True)
                with child.scope('certify'):pass
                child_raw=child.finish()
        parent=p.finish()
        with tempfile.TemporaryDirectory() as tmp:
            d=Path(tmp);write_json(d/'parent.json',parent);write_json(d/'child.json',child_raw)
            ref=lambda name:dict(path=name,sha256=file_hash(d/name))
            cost=dict(observations=[dict(process='solve',parent_scope=None,artifact=ref('parent.json')),
                 dict(process='host-certifier',parent_scope=['copt','host_certification'],artifact=ref('child.json'))])
            checked_component_rows(cost,d,None,True)
            wrong=copy.deepcopy(cost);wrong['observations'][1]['parent_scope']=['wrong']
            with self.assertRaises(ValueError):checked_component_rows(wrong,d,None,True)
            with self.assertRaises(ValueError):checked_component_rows(cost,d,None,False)
            raw=copy.deepcopy(parent);raw['counters']=dict(device_allocated_bytes=12,host_to_device_bytes=5,device_to_host_bytes=3)
            write_json(d/'parent.json',raw);project=dict(observations=[dict(process='solve',parent_scope=None,artifact=ref('parent.json'))])
            endpoint=dict(execution=dict(allocated_bytes=12,upload_bytes=5,readback_bytes=3))
            checked_component_rows(project,d,endpoint,False)
            endpoint['execution']['upload_bytes']=6
            with self.assertRaises(ValueError):checked_component_rows(project,d,endpoint,False)
        trial=dict(status='invalid_evidence',error='independent verification failed: input exceeds 16 MiB',executed_backend=None,endpoint_class=None)
        qualified=qualified_trial(trial,'host-lp','certified_success',dict(reason='completed'))
        self.assertEqual(qualified['status'],'completed');self.assertEqual(trial['status'],'invalid_evidence')
        qualified=qualified_trial(trial,'host-lp','certified_success',dict(reason='timeout'))
        self.assertEqual(qualified['status'],'timeout')
        with self.assertRaises(ValueError):qualified_trial(dict(trial,error='forged mathematics'),'host-lp','certified_success',dict(reason='completed'))

    def test_numerical_profile_digest_ignores_clocks_but_preserves_signed_zero(self):
        from report_lp_copt import numerical_digest
        e=dict(record=dict(elapsed_ms=1,candidate=[0.0],validation={'static':'metadata'}),model_sha256='a'*64,
               diagnostics=dict(dual=[-0.0],iterations=1,assessment_iteration=1,restarts=0,phases_ns={'phase':100}),assessment=dict(objective=0.0))
        other=copy.deepcopy(e);other['record']['elapsed_ms']=123;other['diagnostics']['phases_ns']['phase']=500
        self.assertEqual(numerical_digest(e),numerical_digest(other))
        other['diagnostics']['dual']=[0.0]
        self.assertNotEqual(numerical_digest(e),numerical_digest(other))

class ComparisonContracts(unittest.TestCase):
    def fixture(self,root):
        v=protocol();parent=read_json(ROOT/v['previous_protocol']['path']);previous=read_json(ROOT/parent['previous_protocol']['path'])
        paths={v['budget_authority']['path'],v['previous_protocol']['path'],v['decision']['path'],parent['decision']['path'],parent['previous_protocol']['path'],previous['decision']['path'],previous['source_campaign']['path']}
        for name in paths:
            target=root/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/name,target)
        directory=root/'artifacts/lp-campaign-ledgers/gpup-baseline-v1'
        with Ledger(directory,v['budget_authority']['sha256'],v['phase_gpu_seconds'],cumulative_ns=v['cumulative_gpu_ns']) as ledger:
            ledger.bind_output(root/'artifacts/gpup-baseline-v1');r=ledger.reserve('fixture',1,resource='cpu');ledger.settle(r,1)
        data=(directory/'ledger.jsonl').read_bytes();v.update(prior_events=2,prior_gpu_ns=0,prior_ledger_sha256=hashlib.sha256(data).hexdigest())
        return v,directory
    def test_frozen_schedule_and_per_instance_limits(self):
        v=protocol();schedule=list(jobs(v));self.assertEqual(len(schedule),1140);self.assertEqual(len({j['id'] for j in schedule}),1140)
        from collections import Counter
        self.assertEqual(Counter(j['kind'] for j in schedule),dict(timing=816,profile=232,short=72,trace=20))
        for j in schedule:
            solve,method,limits=effective(v,j);seconds=30 if 'extension' in j['instance']['id'] else 10
            self.assertEqual(solve['time_limit_ms'],seconds*1000)
            self.assertEqual(limits['solve_seconds'],seconds+(15 if j['kind']=='trace' else 0))
            self.assertEqual(method['iteration_limit'],200 if j['kind']=='short' else 50000)
        wrong=copy.deepcopy(v);wrong['configurations'][0]['id']='changed'
        with self.assertRaises(Exception):validator('lp-campaign-v6.schema.json').validate(wrong)
    def test_chain_prefix_output_and_category_caps(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);v,directory=self.fixture(root)
            with ledger_for(v,root) as ledger:self.assertEqual(ledger.totals(),0)
            for name,item in [('cumulative_gpu_ns',v['cumulative_gpu_ns']+1),('prior_gpu_ns',1),('prior_ledger_sha256','0'*64)]:
                wrong=copy.deepcopy(v);wrong[name]=item
                with self.assertRaises(ValueError):ledger_for(wrong,root)
            for key in ['budget_authority','previous_protocol','decision']:
                wrong=copy.deepcopy(v);wrong[key]['sha256']='0'*64
                with self.assertRaises(ValueError):ledger_for(wrong,root)
            wrong=copy.deepcopy(v);wrong['categories']['trace']['phase']='ablations'
            with self.assertRaises(ValueError):ledger_for(wrong,root)
            binding=directory/'output.json';saved=read_json(binding);write_json(binding,{**saved,'output_path':str(root/'wrong')})
            with self.assertRaises(ValueError):ledger_for(v,root)
            write_json(binding,saved)
            for c in v['categories'].values():c['seconds']=2
            v['combined_cap_seconds']=3
            with ledger_for(v,root) as ledger:
                with self.assertRaises(ValueError):ledger.reserve(v['id']+'-trace-wrong',1,phase='ablations')
                r=ledger.reserve(v['id']+'-timing-one',2,phase='ablations');ledger.settle(r,2*NS)
                with self.assertRaises(ValueError):ledger.reserve(v['id']+'-timing-over',1,phase='ablations')
                ledger.reserve(v['id']+'-profile-crash',1,phase='repeatability')
            with ledger_for(v,root) as ledger:
                self.assertEqual(ledger.usage('profile'),NS)
                with self.assertRaises(ValueError):ledger.reserve(v['id']+'-trace-combined',1,phase='baseline')
    def test_every_method_kind_reaches_admission_with_valid_artifacts(self):
        v=protocol()
        class Admitted(Exception):pass
        class Boundary:
            campaign_hash=v['budget_authority']['sha256']
            def reserve(self,*args,**kwargs):raise Admitted()
        identity=dict(revision='a'*40,dirty=False,source_tree_sha256='a'*64,binary_sha256='b'*64,code_object_sha256='c'*64,highs_library_sha256='d'*64,rustc='fixture',cargo='fixture',os='fixture',cpu='fixture',cpu_affinity=[0],build_profile='release',device=v['device'],telemetry_before='unavailable',telemetry_after='unavailable',copt_library_sha256=None,copt_binding_sha256=None)
        selected={}
        for j in jobs(v):selected.setdefault((j['configuration']['id'],j['kind'],'extension' in j['instance']['id']),j)
        with tempfile.TemporaryDirectory() as tmp:
            d=Path(tmp);model=d/'model.json';model.write_text('{}')
            with patch('benchmark_lp_copt.checked_reference',return_value=model),patch('benchmark_lp_copt.quiet_device',return_value={'elapsed_ns':0}),patch('benchmark_lp_copt.telemetry',return_value='unavailable'):
                for j in selected.values():
                    with self.assertRaises(Admitted,msg=j['id']):run_trial(v,j,ROOT/'target/release/optimizer',d,Boundary(),identity,'e'*64,'f'*64)
                    trial=read_json(d/(j['id']+'.intent.json'));validator('lp-trial-v6.schema.json').validate(trial)
                    req=d/(j['id']+'.request.json');self.assertEqual(trial['request_sha256'],file_hash(req))

class ExternalV2Contracts(unittest.TestCase):
    def test_methods_min_max_identity_and_work(self):
        binary=ROOT/'target/debug/optimizer';original=read_json(ROOT/'examples/lp-model-v1.json');options=read_json(ROOT/'examples/solve-config-v1.json');options['iteration_limit']=50000
        with tempfile.TemporaryDirectory() as tmp:
            d=Path(tmp)
            for maximize in [False,True]:
                model=copy.deepcopy(original);model['constraints'][0]['lower']={'kind':'finite','value':0.5};model['objective']['offset']=7.0
                if maximize:
                    model['objective']['sense']='maximize'
                    for term in model['objective']['terms']:term['coefficient']=-term['coefficient']
                path=d/'model.json';write_json(path,model)
                for method in ['copt-cpu-default','copt-cpu-pdlp','copt-gpu-pdlp']:
                    witness=dict(schema_version=2,model_sha256=file_hash(path),requested_backend=method,executed_backend=method,options=options,copt_version='8.0.6',parameters=parameters(options,method),library_sha256='a'*64,binding_sha256='b'*64,gpu_confirmed=method=='copt-gpu-pdlp',row_ids=[0],variable_ids=[0,1],primal=[0.5,1.0],dual=[-1.0],status='optimal',iterations=10,native=dict(simplex_iterations=10,barrier_iterations=0,pdlp_iterations=0,solving_seconds=0.1,peak_memory_mb=1.0),limitations=['fixture'])
                    wp=d/'witness.json';out=d/f'{method}-{maximize}.json';write_json(wp,witness)
                    args=[str(binary),'lp-study','external-certify','--model',str(path),'--evidence',str(wp),'--output',str(out)]
                    result=subprocess.run(args,capture_output=True,text=True);self.assertEqual(result.returncode,0,result.stderr)
                    e=read_json(out);validator('lp-external-endpoint-v2.schema.json').validate(e);self.assertEqual(e['assessment']['classification'],'certified_success')
                    for edit in ['native','parameters','method','hash']:
                        bad=copy.deepcopy(witness)
                        if edit=='native':bad['native']['simplex_iterations']+=1
                        if edit=='parameters':bad['parameters']['Threads']=2
                        if edit=='method':bad['requested_backend']='unknown'
                        if edit=='hash':bad['model_sha256']='c'*64
                        write_json(wp,bad);bad_result=subprocess.run(args[:-1]+[str(d/'invalid.json')],capture_output=True,text=True)
                        self.assertNotEqual(bad_result.returncode,0,edit)
                    interrupted=copy.deepcopy(witness);interrupted['status']='interrupted';write_json(wp,interrupted)
                    interrupted_path=d/f'interrupted-{method}-{maximize}.json'
                    result=subprocess.run(args[:-1]+[str(interrupted_path)],capture_output=True,text=True);self.assertEqual(result.returncode,0,result.stderr)
                    self.assertEqual(read_json(interrupted_path)['assessment']['classification'],'interrupted')
                    if method=='copt-gpu-pdlp':
                        forged=copy.deepcopy(witness);forged['gpu_confirmed']=False;write_json(wp,forged)
                        result=subprocess.run(args[:-1]+[str(d/'forged.json')],capture_output=True,text=True)
                        self.assertNotEqual(result.returncode,0)
                    altered=copy.deepcopy(e);altered['witness']['parameters']['Threads']=2;write_json(out,altered)
                    result=subprocess.run([str(binary),'lp-study','external-verify','--model',str(path),'--evidence',str(out)],capture_output=True,text=True)
                    self.assertNotEqual(result.returncode,0)
                    witness['iterations']=50001;witness['native']['simplex_iterations']=50001;write_json(wp,witness)
                    result=subprocess.run(args[:-1]+[str(d/f'limited-{method}-{maximize}.json')],capture_output=True,text=True);self.assertEqual(result.returncode,0,result.stderr)
                    self.assertEqual(read_json(d/f'limited-{method}-{maximize}.json')['assessment']['classification'],'work_limit')
    def test_large_study_input_and_profile_without_widening_regular_cli(self):
        binary=ROOT/'target/debug/optimizer'
        with tempfile.TemporaryDirectory() as tmp:
            d=Path(tmp);model=d/'large.json';model.write_bytes((ROOT/'examples/lp-model-v1.json').read_bytes()+b' '*(16*1024*1024))
            common=['--backend','host-lp','--model',str(model),'--config',str(ROOT/'examples/solve-config-v1.json'),'--lp-settings',str(ROOT/'examples/lp-settings-v1.json'),'--lp-evidence',str(d/'endpoint.json')]
            regular=subprocess.run([str(binary),'solve',*common],capture_output=True,text=True);self.assertNotEqual(regular.returncode,0);self.assertIn('16 MiB',regular.stderr)
            study=subprocess.run([str(binary),'lp-study','solve',*common,'--model-byte-limit','134217728','--cost-profile',str(d/'cost.json')],capture_output=True,text=True)
            self.assertIn(study.returncode,[0,1],study.stderr);validate_profile(read_json(d/'cost.json'))
            verified=subprocess.run([str(binary),'lp-study','verify','--model',str(model),'--model-byte-limit','134217728','--evidence',str(d/'endpoint.json')],capture_output=True,text=True)
            self.assertEqual(verified.returncode,0,verified.stderr)

    def test_study_verifier_applies_explicit_allowance_to_endpoint_bytes(self):
        binary=ROOT/'target/debug/optimizer';model=ROOT/'examples/lp-model-v1.json'
        with tempfile.TemporaryDirectory() as tmp:
            d=Path(tmp);endpoint=d/'endpoint.json'
            result=subprocess.run([str(binary),'lp-study','solve','--model',str(model),'--config',str(ROOT/'examples/solve-config-v1.json'),
                '--backend','host-lp','--lp-settings',str(ROOT/'examples/lp-settings-v1.json'),'--lp-evidence',str(endpoint)],capture_output=True,text=True)
            self.assertIn(result.returncode,[0,1],result.stderr)
            with endpoint.open('ab') as stream:stream.write(b' '*(17*1024*1024))
            args=[str(binary),'lp-study','verify','--model',str(model),'--evidence',str(endpoint)]
            result=subprocess.run(args,capture_output=True,text=True);self.assertNotEqual(result.returncode,0);self.assertIn('16 MiB',result.stderr)
            result=subprocess.run(args+['--model-byte-limit','134217728'],capture_output=True,text=True);self.assertEqual(result.returncode,0,result.stderr)
            result=subprocess.run(args+['--model-byte-limit','134217729'],capture_output=True,text=True);self.assertNotEqual(result.returncode,0)

class TraceContracts(unittest.TestCase):
    def test_graph_launch_is_not_one_kernel_and_overlap_is_not_double_counted(self):
        import sqlite3
        from lp_copt_trace import analyze
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'trace.sqlite';db=sqlite3.connect(path)
            db.executescript('CREATE TABLE StringIds(id INTEGER,value TEXT); INSERT INTO StringIds VALUES(1,"kernel"),(2,"cudaGraphLaunch"); CREATE TABLE CUPTI_ACTIVITY_KIND_KERNEL(start INTEGER,end INTEGER,shortName INTEGER,streamId INTEGER,correlationId INTEGER); INSERT INTO CUPTI_ACTIVITY_KIND_KERNEL VALUES(10,30,1,1,7),(20,40,1,2,7); CREATE TABLE CUPTI_ACTIVITY_KIND_RUNTIME(start INTEGER,end INTEGER,nameId INTEGER,correlationId INTEGER); INSERT INTO CUPTI_ACTIVITY_KIND_RUNTIME VALUES(1,3,2,7); CREATE TABLE CUPTI_ACTIVITY_KIND_MEMCPY(start INTEGER,end INTEGER,bytes INTEGER,copyKind INTEGER,streamId INTEGER); INSERT INTO CUPTI_ACTIVITY_KIND_MEMCPY VALUES(25,45,100,1,3);')
            db.commit();db.close();result=analyze(path)
            self.assertEqual(result['kernel_count'],2);self.assertEqual(result['kernel_summed_ns'],40);self.assertEqual(result['kernel_union_ns'],30)
            self.assertEqual(result['device_union_ns'],35);self.assertEqual(result['kernel_copy_overlap_ns'],15)
            self.assertEqual(result['correlated_kernels'],2);self.assertEqual(result['apis'][0]['count'],1)
            self.assertEqual(result['correlation_groups'][0]['kernels_per_correlation'],2)
            self.assertIsNone(result['memset_count'])

    def test_recorded_memory_fills_are_activity_without_corrupting_copy_overlap(self):
        import sqlite3
        from lp_copt_trace import analyze
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'trace.sqlite';db=sqlite3.connect(path)
            db.executescript('CREATE TABLE CUPTI_ACTIVITY_KIND_KERNEL(start INTEGER,end INTEGER,shortName INTEGER,streamId INTEGER,correlationId INTEGER); INSERT INTO CUPTI_ACTIVITY_KIND_KERNEL VALUES(10,20,1,1,7); CREATE TABLE CUPTI_ACTIVITY_KIND_MEMCPY(start INTEGER,end INTEGER,bytes INTEGER,copyKind INTEGER,streamId INTEGER); INSERT INTO CUPTI_ACTIVITY_KIND_MEMCPY VALUES(15,25,100,1,3); CREATE TABLE CUPTI_ACTIVITY_KIND_MEMSET(start INTEGER,end INTEGER,bytes INTEGER,streamId INTEGER); INSERT INTO CUPTI_ACTIVITY_KIND_MEMSET VALUES(25,40,64,3);')
            db.commit();db.close();r=analyze(path)
            self.assertEqual(r['kernel_copy_union_ns'],15);self.assertEqual(r['kernel_copy_overlap_ns'],5)
            self.assertEqual(r['memset_union_ns'],15);self.assertEqual(r['memset_bytes'],64)
            self.assertEqual(r['device_union_ns'],30);self.assertEqual(r['activity_free_ns'],0)
            self.assertEqual(sum(e['kind']=='fill' for e in r['timeline']),1)


    def test_opaque_graph_envelopes_do_not_invent_kernel_counts_or_busy_time(self):
        import sqlite3
        from lp_copt_trace import analyze
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'graph.sqlite';db=sqlite3.connect(path)
            db.executescript('CREATE TABLE StringIds(id INTEGER,value TEXT); INSERT INTO StringIds VALUES(1,"cuGraphLaunch"); CREATE TABLE CUPTI_ACTIVITY_KIND_RUNTIME(start INTEGER,end INTEGER,nameId INTEGER,correlationId INTEGER); INSERT INTO CUPTI_ACTIVITY_KIND_RUNTIME VALUES(1,3,1,7); CREATE TABLE CUPTI_ACTIVITY_KIND_GRAPH_TRACE(start INTEGER,end INTEGER,streamId INTEGER,correlationId INTEGER,graphId INTEGER); INSERT INTO CUPTI_ACTIVITY_KIND_GRAPH_TRACE VALUES(10,40,1,7,9);')
            db.commit();db.close();r=analyze(path)
            self.assertFalse(r['kernel_count_is_complete']);self.assertIsNone(r['total_executed_kernel_count'])
            self.assertEqual(r['kernel_count'],0);self.assertEqual(r['device_union_ns'],0)
            self.assertEqual(r['graph_execution_union_ns'],30);self.assertEqual(r['device_envelope_union_ns'],30)
            self.assertEqual(r['activity_free_ns'],0);self.assertEqual(r['unresolved_graph_span_ns'],30)
            self.assertEqual(r['apis'][0]['layer'],'DRIVER');self.assertEqual(r['correlation_groups'][0]['graph_envelopes_per_correlation'],1)

    def test_importer_mutation_recovery_is_exact_and_future_imports_use_copies(self):
        import struct
        from types import SimpleNamespace
        from lp_copt_trace_recover import original_bytes,restore
        from report_lp_copt import decode
        def vi(value):
            out=bytearray()
            while value>=128:out.append((value&127)|128);value>>=7
            return bytes(out)+bytes([value])
        def entry(name,start,size):
            body=b'\x0a'+vi(len(name))+name+b'\x10'+vi(start)+b'\x18'+vi(size)
            return b'\x0a'+vi(len(body))+body
        payload=b'original capture fixture';index=entry(b'Data',0,len(payload))
        original=payload+index+struct.pack('<Q',len(payload))+b'U3w[END]'
        mutated=payload+b'\x08\x01'+index+entry(b'Telemetry Status',len(payload),2)+struct.pack('<Q',len(payload)+2)+b'U3w[END]'
        expected=hashlib.sha256(original).hexdigest()
        self.assertEqual(original_bytes(mutated,expected),original)
        with self.assertRaises(ValueError):original_bytes(b'X'+mutated[1:],expected)
        with tempfile.TemporaryDirectory() as tmp:
            d=Path(tmp);raw=d/'fixture-trace.qdstrm';raw.write_bytes(mutated)
            write_json(d/'fixture-trace.cost.json',dict(trace=dict(path=raw.name,sha256=expected)))
            restore(d);self.assertEqual(raw.read_bytes(),original)
            self.assertEqual((d/'offline-import-mutated'/raw.name).read_bytes(),mutated)
            nsys=d/'nsys';nsys.write_bytes(b'profiler');importer=d/'importer';importer.write_bytes(b'importer')
            write_json(d/'profiler.json',dict(sha256=file_hash(nsys)))
            seen=[]
            def fake_run(command,**kwargs):
                if '--input-file' in command:
                    source=Path(command[command.index('--input-file')+1]);seen.append(source)
                    self.assertNotEqual(source,raw);self.assertEqual(source.read_bytes(),original)
                    source.write_bytes(b'importer changes only its disposable copy')
                    Path(command[command.index('--output-file')+1]).write_bytes(b'report')
                else:Path(next(x.split('=',1)[1] for x in command if x.startswith('--output='))).write_bytes(b'export')
                return SimpleNamespace(returncode=0,stdout='',stderr='')
            with patch('report_lp_copt.jobs',return_value=[dict(kind='trace',id='fixture-trace')]),patch('report_lp_copt.subprocess.run',side_effect=fake_run):
                decode(d,dict(nsys=str(nsys)),importer,d/'libraries')
            self.assertEqual(len(seen),1);self.assertEqual(raw.read_bytes(),original)

if __name__=='__main__':unittest.main()
