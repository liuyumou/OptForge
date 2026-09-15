"""Adversarial contracts for the bounded GPUP-2 LP-only study."""
import copy
from fractions import Fraction
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'))
from lp_protocol import Ledger, NS, campaign, encoded, file_hash, ordered, read_json, strict_loads, validate, write_json
from lp_generate import linear
from lp_report import analyze, paired_ratio, successful
from benchmark_lp import schedule

BINARY=ROOT/'target/debug/optimizer'

class ProtocolTests(unittest.TestCase):
    def test_frozen_inputs_grid_order_and_partition(self):
        value,manifests=campaign(ROOT/'benchmarks/configs/lp-campaign-v1.json')
        self.assertEqual([len(m['instances']) for m in manifests],[12,10,10])
        jobs=list(schedule(value,manifests))
        self.assertEqual(len(jobs),144)
        self.assertEqual(sum(j[2]['backend']=='cuda-lp' for j in jobs),48)
        self.assertEqual(jobs,list(schedule(value,manifests)))
        self.assertTrue(all('held_out' not in j[0] and 'validation' not in j[0] for j in jobs))
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'campaign.json'
            for key,replacement in [('order_seed',8),('partition','held_out'),('slice_gpu_seconds',901)]:
                wrong=copy.deepcopy(value);wrong[key]=replacement;write_json(path,wrong)
                with self.assertRaises(Exception):campaign(path)

    def test_related_seed_leakage_and_hidden_setting_changes_fail(self):
        value,manifests=campaign(ROOT/'benchmarks/configs/lp-campaign-v1.json')
        with tempfile.TemporaryDirectory(dir=ROOT/'artifacts') as tmp:
            tmp=Path(tmp); config=tmp/'campaign.json'
            changed=copy.deepcopy(value);changed['lp_settings']['check_interval']=201
            write_json(config,changed)
            with self.assertRaises(ValueError):campaign(config)
            changed=copy.deepcopy(value)
            manifest=copy.deepcopy(manifests[1])
            manifest['instances'][0]['group']=manifests[0]['instances'][0]['group']
            path=tmp/'manifest.json';write_json(path,manifest)
            changed['manifests'][1]={'path':str(path.relative_to(ROOT)),'sha256':file_hash(path)}
            write_json(config,changed)
            with self.assertRaises(ValueError):campaign(config)

    def test_strict_json_and_path_hash_checks(self):
        for raw in ['{"a":1,"a":2}','{"n":NaN}','{"n":1e400}']:
            with self.assertRaises(ValueError):strict_loads(raw)
        from lp_protocol import local, checked_reference
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):local(tmp,'../escape')
            with self.assertRaises(ValueError):local(tmp,'/absolute')
            path=Path(tmp)/'data';path.write_bytes(b'original')
            ref={'path':'data','sha256':file_hash(path)}
            checked_reference(tmp,ref);path.write_bytes(b'changed')
            with self.assertRaises(ValueError):checked_reference(tmp,ref)

    def test_generated_witnesses_use_independent_exact_weak_duality(self):
        for family,n in [('small',4),('small',16),('irregular',32),('dense_block',32),('scaling',32)]:
            model,witness=linear('exact-'+family,family,n,17100)
            x=[Fraction.from_float(a['value']) for a in witness['candidate']['values']]
            y=list(map(Fraction.from_float,witness['dual']))
            sense=1 if model['objective']['sense']=='minimize' else -1
            costs={t['variable_id']:sense*Fraction.from_float(t['coefficient']) for t in model['objective']['terms']}
            reduced=[costs.get(j,Fraction()) for j in range(n)]
            dual=Fraction.from_float(sense*model['objective']['offset'])
            for i,row in enumerate(model['constraints']):
                activity=sum(Fraction.from_float(t['coefficient'])*x[t['variable_id']] for t in row['terms'])
                self.assertLessEqual(Fraction.from_float(row['lower']['value']),activity)
                self.assertLessEqual(activity,Fraction.from_float(row['upper']['value']))
                dual+=y[i]*Fraction.from_float(row['lower' if y[i]>=0 else 'upper']['value'])
                for term in row['terms']:reduced[term['variable_id']]-=y[i]*Fraction.from_float(term['coefficient'])
            dual+=sum(min(Fraction(),r) for r in reduced)
            primal=Fraction.from_float(sense*model['objective']['offset'])+sum(costs.get(j,Fraction())*v for j,v in enumerate(x))
            self.assertEqual(primal,dual)

    def test_reservations_recover_without_reset_and_reject_concurrent_writers(self):
        with tempfile.TemporaryDirectory() as tmp:
            with Ledger(tmp,'a'*64,slice_seconds=3) as ledger:
                ledger.bind_output(Path(tmp)/'outputs')
                with self.assertRaises(ValueError):ledger.bind_output(Path(tmp)/'different-output')
                first=ledger.reserve('one',1)
                with self.assertRaises(BlockingIOError):
                    with Ledger(tmp,'a'*64):pass
                ledger.settle(first,NS//2)
                ledger.reserve('crashed',2)
            with Ledger(tmp,'a'*64,slice_seconds=3) as ledger:
                self.assertEqual(ledger.totals(),2_500_000_000)
                with self.assertRaises(ValueError):ledger.reserve('over',1)
                with self.assertRaises(ValueError):ledger.reserve('one',0.1)
                cpu=ledger.reserve('cpu',20,'cpu');ledger.settle(cpu,NS)
                self.assertEqual(ledger.totals('cpu'),NS)
                self.assertEqual(ledger.totals(),2_500_000_000)
            with self.assertRaises(ValueError):
                with Ledger(tmp,'b'*64):pass

    def test_torn_settlement_and_phase_budget(self):
        with tempfile.TemporaryDirectory() as tmp:
            with Ledger(tmp,'c'*64,allocations={'baseline':1}) as ledger:ledger.reserve('r',1)
            with (Path(tmp)/'ledger.jsonl').open('ab') as stream:stream.write(b'{"kind":"sett')
            with Ledger(tmp,'c'*64,allocations={'baseline':1}) as ledger:
                self.assertEqual(ledger.totals(),NS)
                with self.assertRaises(ValueError):ledger.reserve('r2',0.1)
            self.assertEqual(len(list(Path(tmp).glob('torn-*.bin'))),1)

    def test_paired_analysis_keeps_failures_and_incomplete_counts(self):
        self.assertEqual(paired_ratio([(20,10),(40,20),(60,30)],resamples=100),
                         {'paired_repetitions':3,'ratio':2.0,'ci95':[2.0,2.0]})
        self.assertIsNone(paired_ratio([]))
        value={'configurations':[{'id':'highs'},{'id':'host-lp'},{'id':'cuda-lp'}],
               'repetitions':3,'analysis':{'seed':17002,'resamples':100}}
        trials=[]
        for backend in ['highs','cuda-lp']:
            for r in range(2):
                trials.append(dict(mode='timing',instance_id='i',config_id=backend,repetition=r,
                    requested_backend=backend,executed_backend=backend,status='completed',
                    endpoint_class='certified_success',elapsed_ns=10 if backend=='cuda-lp' else 20))
        trials[-1]['status']='timeout'
        rows,ratios=analyze(trials,value,[{'id':'i'}])
        gpu=next(row for row in rows if row['backend']=='cuda-lp')
        self.assertEqual((gpu['attempted'],gpu['planned'],gpu['certified']),(2,3,1))
        self.assertEqual(ratios[0]['statistics']['paired_repetitions'],1)
        trials[0]['executed_backend']='cuda-lp';self.assertFalse(successful(trials[0]))

class EndpointTests(unittest.TestCase):
    def solve(self,directory,backend='host-lp',model=None,extra=()):
        model=model or ROOT/'examples/lp-model-v1.json'
        path=Path(directory)/'endpoint.json'
        args=[str(BINARY),'solve','--model',str(model),'--config',str(ROOT/'examples/solve-config-v1.json'),
              '--backend',backend,'--lp-evidence',str(path)]
        if backend!='highs':args+=['--lp-settings',str(ROOT/'examples/lp-settings-v1.json')]
        run=subprocess.run(args+list(extra),capture_output=True,timeout=15)
        self.assertIn(run.returncode,[0,1],run.stderr)
        endpoint=validate('endpoint',read_json(path))
        verified=subprocess.run([str(BINARY),'lp-study','verify','--model',str(model),'--evidence',str(path)],capture_output=True)
        self.assertEqual(verified.returncode,0,verified.stderr)
        return endpoint,path,model

    def test_endpoint_profiles_are_opt_in_and_tampering_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            endpoint,path,model=self.solve(tmp)
            self.assertEqual(endpoint['diagnostics']['phases_ns'],{})
            for mutation in [lambda e:e['assessment'].update(bound=1e30),
                             lambda e:e['record'].update(objective=1e30),
                             lambda e:e['diagnostics'].update(dual=[]),
                             lambda e:e['record'].update(termination='optimal')]:
                wrong=copy.deepcopy(endpoint);mutation(wrong);write_json(path,wrong)
                run=subprocess.run([str(BINARY),'lp-study','verify','--model',str(model),'--evidence',str(path)],capture_output=True)
                # The status may already have been optimal; use a guaranteed change.
                if wrong!=endpoint:self.assertNotEqual(run.returncode,0)
            profiled,_,_=self.solve(tmp,extra=['--lp-profile','true'])
            self.assertIn('independent_endpoint',profiled['diagnostics']['phases_ns'])

    def test_endpoint_parser_rejects_nested_duplicates_sequences_and_missing_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            endpoint,path,model=self.solve(tmp,extra=['--lp-profile','true'])
            encoded_endpoint=json.dumps(endpoint)
            duplicate=encoded_endpoint.replace('"phases_ns": {','"phases_ns": {"iteration":1,',1)
            candidates=[duplicate]
            wrong=copy.deepcopy(endpoint);wrong['diagnostics']=list(wrong['diagnostics'].values());candidates.append(json.dumps(wrong))
            wrong=copy.deepcopy(endpoint);del wrong['assessment']['bound'];candidates.append(json.dumps(wrong))
            wrong=copy.deepcopy(endpoint);wrong['schema_version']=2;candidates.append(json.dumps(wrong))
            for raw in candidates:
                path.write_text(raw)
                run=subprocess.run([str(BINARY),'lp-study','verify','--model',str(model),'--evidence',str(path)],capture_output=True)
                self.assertNotEqual(run.returncode,0,raw[:80])

    @unittest.skipIf(os.environ.get('AI_OPTIMIZER_SKIP_NATIVE')=='1','native acceptance explicitly skipped')
    def test_native_min_and_max_multipliers_certify_independently(self):
        with tempfile.TemporaryDirectory() as tmp:
            minimum,_,_=self.solve(tmp,'highs')
            self.assertEqual(minimum['assessment']['classification'],'certified_success')
            self.assertEqual(minimum['assessment']['bound'],-3.5)
            model=read_json(ROOT/'examples/lp-model-v1.json')
            model['objective']['sense']='maximize'
            for term in model['objective']['terms']:term['coefficient']*=-1
            path=Path(tmp)/'max.json';write_json(path,model)
            maximum,_,_=self.solve(tmp,'highs',path)
            self.assertEqual(maximum['assessment']['classification'],'certified_success')
            self.assertEqual(maximum['assessment']['bound'],3.5)

class SupervisorTests(unittest.TestCase):
    def request(self,tmp,code,seconds=0.1):
        value=dict(command=[sys.executable,'-c',code],directory=tmp,prefix='job',
            solve_seconds=seconds,cleanup_seconds=0.1,host_rss_bytes=100*1024**2,poll_ms=10,output_bytes=1024**2)
        path=Path(tmp)/'request.json';write_json(path,value);return path

    def test_known_delays_full_timing_and_forced_cleanup(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=self.request(tmp,'import time; print("begin",flush=True); time.sleep(.04); print("end")',1)
            subprocess.run([sys.executable,str(ROOT/'tools/lp_supervise.py'),'--request',str(path)],check=True)
            info=read_json(Path(tmp)/'job.worker.json')
            self.assertEqual(info['reason'],'completed');self.assertGreaterEqual(info['elapsed_ns'],40_000_000)
            self.assertIn(b'end',(Path(tmp)/'job.stdout').read_bytes())
            path=self.request(tmp,'import signal,time; signal.signal(signal.SIGINT,signal.SIG_IGN); time.sleep(10)')
            subprocess.run([sys.executable,str(ROOT/'tools/lp_supervise.py'),'--request',str(path)],check=True,timeout=3)
            info=read_json(Path(tmp)/'job.worker.json')
            self.assertEqual(info['reason'],'timeout');self.assertEqual(info['signal'],'SIGKILL')
            self.assertEqual([e['signal'] for e in info['signal_events']],['SIGINT','SIGKILL'])
            self.assertLess(info['signal_events'][0]['elapsed_ns'],info['signal_events'][1]['elapsed_ns'])
            self.assertEqual(read_json(Path(tmp)/'job.worker.partial.json')['signal_events'],info['signal_events'])
            self.assertLess(info['elapsed_ns'],NS)

    def test_orphan_descendant_is_reaped_before_worker_completion(self):
        with tempfile.TemporaryDirectory() as tmp:
            descendant=Path(tmp)/'descendant.pid'
            code=('import os,signal,time; pid=os.fork(); '
                  f'open({str(descendant)!r},"w").write(str(pid)) if pid else None; '
                  'os._exit(0) if pid else None; '
                  'signal.signal(signal.SIGINT,signal.SIG_IGN); time.sleep(10)')
            path=self.request(tmp,code,1)
            subprocess.run([sys.executable,str(ROOT/'tools/lp_supervise.py'),'--request',str(path)],check=True,timeout=3)
            pid=int(descendant.read_text())
            self.assertFalse(Path(f'/proc/{pid}').exists(), 'descendant still running or unreaped')
            self.assertEqual(read_json(Path(tmp)/'job.worker.json')['reason'],'completed')

    def test_simulated_clock_deadline_boundary(self):
        from lp_supervise import supervise
        for observed, expected in [(NS-1,None),(NS,'SIGINT'),(NS+1,'SIGINT')]:
            with self.subTest(observed=observed), tempfile.TemporaryDirectory() as tmp:
                request=read_json(self.request(tmp,'unused',1))
                class Child:
                    pid=123456789
                    returncode=None
                    def poll(self): return self.returncode
                    def wait(self,timeout=None): self.returncode=0;return 0
                child=Child()
                with patch('lp_supervise.enable_subreaper'), patch('lp_supervise.reap_group'), \
                     patch('lp_supervise.subprocess.Popen',return_value=child), \
                     patch('lp_supervise.rss_tree',return_value=0), \
                     patch('lp_supervise.os.killpg'), \
                     patch('lp_supervise.time.monotonic_ns',side_effect=[0,0,observed,observed+1]):
                    info=supervise(request)
                self.assertEqual(info['signal'],expected)
                self.assertEqual(info['reason'],'completed' if expected is None else 'timeout')

    def test_memory_and_output_limits_and_supervisor_survive_coordinator_loss(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=self.request(tmp,'import time; data=bytearray(64*1024*1024); time.sleep(5)',1)
            request=read_json(path);request['host_rss_bytes']=16*1024**2;write_json(path,request)
            subprocess.run([sys.executable,str(ROOT/'tools/lp_supervise.py'),'--request',str(path)],check=True,timeout=3)
            info=read_json(Path(tmp)/'job.worker.json')
            self.assertEqual(info['reason'],'memory_limit')
            path=self.request(tmp,'import os; os.write(1,b"x"*65536)',1)
            request=read_json(path);request['output_bytes']=4096;write_json(path,request)
            subprocess.run([sys.executable,str(ROOT/'tools/lp_supervise.py'),'--request',str(path)],check=True,timeout=3)
            self.assertLessEqual((Path(tmp)/'job.stdout').stat().st_size,4096)
            path=self.request(tmp,'import signal,time; signal.signal(signal.SIGINT,signal.SIG_IGN); time.sleep(10)')
            (Path(tmp)/'job.worker.json').unlink()
            # Only CPU work under an isolated simulated lease; the coordinator
            # exits immediately and leaves the independent bounded supervisor.
            code='import subprocess,sys; subprocess.Popen(sys.argv[1:])'
            env={**os.environ,'AI_OPTIMIZER_GPU_LOCK':str(Path(tmp)/'lock')}
            subprocess.run([sys.executable,'-c',code,'bash',str(ROOT/'tools/gpu_job.sh'),'GPU-simulated','--lp-study-request',str(path)],env=env,check=True)
            deadline=time.monotonic()+3
            while not (Path(tmp)/'job.worker.json').exists() and time.monotonic()<deadline:time.sleep(.02)
            info=read_json(Path(tmp)/'job.worker.json')
            self.assertEqual(info['reason'],'timeout');self.assertLess(info['leased_ns'],NS)

    def test_cpu_only_simulated_shared_lease_exclusion_and_queue_accounting(self):
        import fcntl
        with tempfile.TemporaryDirectory() as tmp:
            lock_path=Path(tmp)/'lock';lock=lock_path.open('a+b');fcntl.flock(lock,fcntl.LOCK_EX)
            path=self.request(tmp,'print("simulated; no CUDA context")',1)
            env={**os.environ,'AI_OPTIMIZER_GPU_LOCK':str(lock_path)}
            worker=subprocess.Popen(['bash',str(ROOT/'tools/gpu_job.sh'),'GPU-simulated','--lp-study-request',str(path)],env=env)
            try:
                # Observe the worker opening the lock, after its queue clock starts.
                # Import/startup time is not lease wait and varies across CI hosts.
                deadline=time.monotonic()+5
                opened=False
                while worker.poll() is None and time.monotonic()<deadline:
                    try:
                        opened=any(fd.resolve()==lock_path for fd in Path(f'/proc/{worker.pid}/fd').iterdir())
                    except (FileNotFoundError,ProcessLookupError):
                        opened=False
                    if opened:break
                    time.sleep(.01)
                self.assertTrue(opened,'worker never reached lease acquisition')
                time.sleep(.075)
                self.assertIsNone(worker.poll())
                self.assertFalse((Path(tmp)/'job.stdout').exists(),'child launched while lease held')
                fcntl.flock(lock,fcntl.LOCK_UN)
                self.assertEqual(worker.wait(timeout=3),0)
                info=read_json(Path(tmp)/'job.worker.json')
                self.assertGreater(info['queue_ns'],50_000_000)
                self.assertGreater(info['leased_ns'],0)
                self.assertEqual(info['reason'],'completed')
            finally:
                fcntl.flock(lock,fcntl.LOCK_UN);lock.close()
                if worker.poll() is None:
                    worker.terminate();worker.wait(timeout=3)

if __name__=='__main__':unittest.main()
