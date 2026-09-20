"""GPUP-THROUGHPUT: frozen grid, variant contract, budget authority and byte pins."""
from collections import Counter
from fractions import Fraction as F
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'))
from benchmark_lp_throughput import KINDS,protocol,jobs,label,settings_for,batch_request_for,research_batch_request_for
from analyze_lp_throughput import (FRESH_ENDPOINT,AMORTIZED_ENDPOINT,SEPARATE_TITLE,COVERAGE_KINDS,amortized,identity_count,
                                   tuned_bits,research_bits,cross_mode_bits,tuned_exit_code,expected_batch_exit,check_endpoint_separation)
from lp_protocol import NS,file_hash,read_json,write_json
from lp_research_budget import STUDY_V1,Study,ledger_for
import lp_variants
CONFIG=ROOT/'benchmarks/configs/lp-throughput-v1.json'
BLOCKS=[(0,'fresh',81),(1,'fresh-short',27),(2,'batch-repeat',243),(3,'batch-variant',216),
        (4,'batch-repeat-short',54),(5,'fresh-short',12),(6,'batch-repeat-short',12),
        (7,'batch-variant-short',12),(8,'fresh-variant',48)]


def witness_instances(value):
    manifest=read_json(ROOT/'benchmarks/manifests/lp-development-v1.json')['instances']+read_json(ROOT/'benchmarks/manifests/lp-development-extension-v1.json')['instances']
    return [(p,i) for p,i in enumerate(manifest) if i['witness'] is not None]


class ThroughputGridTests(unittest.TestCase):
    """SPEC-0014 requirements 28-31: the frozen 705-attempt grid and its labels."""
    def test_frozen_grid_counts_kinds_and_labels(self):
        value,base,manifest=protocol();schedule=list(jobs(value,base,manifest))
        self.assertEqual(len(schedule),705);self.assertEqual(len(schedule),value['planned_attempts'])
        counts=Counter(j['block'] for j in schedule)
        kinds={}
        for j in schedule:kinds.setdefault(j['block'],j['kind'])
        self.assertEqual([(b,k,counts[b]) for b,k in sorted(kinds.items())],BLOCKS)
        self.assertEqual(len({label(j) for j in schedule}),705)
        self.assertEqual(base['solve']['seed'],17);self.assertEqual(base['order_seed'],17001)
        self.assertEqual(set(value['tiers']),{'1e-9'});self.assertEqual(value['tiers']['1e-9'],base['solve']['tolerances'])
        self.assertTrue(all(j['instance']['id'].startswith(('gpup-development-','gpup-extension-','ta')) for j in schedule))
        self.assertTrue(all(j['tier']=='1e-9' for j in schedule))
        batch=[j for j in schedule if j['size'] is not None]
        self.assertTrue(all(f'-n{j["size"]}' in label(j) for j in batch))
        variants=[j for j in schedule if j['variant'] is not None]
        self.assertEqual(len(variants),48);self.assertTrue(all(f'-v{j["variant"]}' in label(j) for j in variants))
        # Extension instances are reached only by the research executable; the
        # CLI's 16 MiB document limit excludes them (requirement 35).
        extension=[j for j in schedule if j['instance']['id'].startswith('gpup-extension-')]
        self.assertEqual(len(extension),36);self.assertTrue(all(j['config']['id']=='research-fused-fp64' for j in extension))
    def test_protocol_schema_is_strict(self):
        value,_,_=protocol()
        for mutated in [dict(value,schema_version=2),dict(value,schema_version=4),
                        {k:v for k,v in value.items() if k!='decision'},dict(value,unknown=1)]:
            with self.assertRaises(ValueError):protocol_from(mutated)
        witness_less=dict(value,blocks=[dict(b,instances=b['instances']+['gpup-development-scheduling-20x5']) if b['kind']=='batch-variant' else b for b in value['blocks']])
        with self.assertRaises(ValueError):protocol_from(witness_less)
    def test_settings_and_batch_requests(self):
        value,base,manifest=protocol();schedule=list(jobs(value,base,manifest))
        for job in schedule:
            options,method,seconds,batch_ms=settings_for(job,base,value)
            self.assertEqual(options['tolerances'],value['tiers'][job['tier']])
            extension=job['instance']['id'].startswith('gpup-extension-')
            per_solve=30 if extension else value['development_limit_seconds']
            self.assertEqual(options['time_limit_ms'],per_solve*1000)
            if job['kind'].endswith('-short'):self.assertEqual((options['iteration_limit'],method['iteration_limit']),(200,200))
            if job['size'] is None:
                self.assertEqual(seconds,per_solve);self.assertEqual(batch_ms,per_solve*1000)
            else:
                limit=40+2*job['size'] if extension else 20+job['size']
                self.assertEqual((seconds,batch_ms),(limit+2,limit*1000))
            if job['kind'] in ('batch-repeat','batch-repeat-short','batch-variant','batch-variant-short','fresh-variant'):
                request=batch_request_for(job,value,batch_ms)
                self.assertEqual(request['batch_time_limit_ms'],batch_ms)
                if job['kind'] in ('batch-repeat','batch-repeat-short'):
                    self.assertEqual((request['kind'],request['solves'],request['variants'],request['generator']),('repeat',job['size'],[],None))
                else:
                    self.assertEqual(request['kind'],'variant');self.assertEqual(request['generator'],{'seed':job['variant_seed'],'changes':value['variant_changes']})
                    expected=1 if job['kind']=='fresh-variant' else job['size']
                    self.assertEqual(len(request['variants']),expected)
                if 'mode' in job['config']:
                    research=research_batch_request_for(job,base,value,'a'*64,'b'*64,'c'*64,'d'*64)
                    self.assertEqual(research['schema_version'],1)
                    self.assertIn(research['mode'],('intguard-fp64','fused-fp64'))
                    self.assertEqual(research['options']['iteration_limit'],research['method']['iteration_limit'])
                    self.assertIsNotNone(research['options']['time_limit_ms'])
                    self.assertTrue(research['device'].startswith('GPU-'))
                    self.assertEqual(research['batch'],request)


class VariantContractTests(unittest.TestCase):
    """SPEC-0014 requirements 18-21: determinism, dyadic exactness, witness feasibility."""
    def small(self):
        model=read_json(ROOT/'artifacts/lp-inputs-v1/gpup-development-small-4.json')
        witness=read_json(ROOT/'artifacts/lp-inputs-v1/gpup-development-small-4-witness.json')
        return model,witness
    def test_determinism_prefix_and_change_count(self):
        model,witness=self.small()
        first=lp_variants.variants(model,witness,47108,8,256)
        self.assertEqual(first,lp_variants.variants(model,witness,47108,8,256))
        larger=lp_variants.variants(model,witness,47108,32,256)
        self.assertEqual(larger[:8],first)
        self.assertNotEqual(first,lp_variants.variants(model,witness,47109,8,256))
        self.assertTrue(all(len(v['changes'])==4 for v in larger))
        self.assertTrue(all(len({c['variable_id'] for c in v['changes']})==4 for v in larger))
        self.assertEqual([v['index'] for v in larger],list(range(32)))
        irregular=read_json(ROOT/'artifacts/lp-inputs-v1/gpup-development-irregular-256.json')
        irregular_witness=read_json(ROOT/'artifacts/lp-inputs-v1/gpup-development-irregular-256-witness.json')
        self.assertEqual(len(lp_variants.variants(irregular,irregular_witness,47102,1,256)[0]['changes']),256)
    def test_bounds_are_dyadic_and_exact_in_fp64_and_fp32(self):
        import struct
        model,witness=self.small()
        for variant in lp_variants.variants(model,witness,47108,8,256):
            for change in variant['changes']:
                for side in ['lower','upper']:
                    value=change[side]
                    self.assertEqual(F.from_float(value),F(value))
                    self.assertEqual(struct.unpack('>f',struct.pack('>f',value))[0],value)
                # small-4's witness sits at 0.0: the lower side cannot move,
                # the upper side moves strictly toward it by k/2**m.
                self.assertEqual(change['lower'],0.0)
                self.assertIsNotNone(lp_variants.dyadic(F(1)-F.from_float(change['upper'])))
                self.assertLess(0.0,change['upper']);self.assertLess(change['upper'],1.0)
    def test_every_witness_instance_family_keeps_the_witness_feasible(self):
        value=read_json(CONFIG)
        instances=witness_instances(value)
        self.assertEqual(len(instances),12)
        for position,entry in instances:
            model=read_json(ROOT/entry['model']['path'])
            witness=read_json(ROOT/entry['witness']['path'])
            seed=value['variant_seed_base']+position
            families={n:lp_variants.variants(model,witness,seed,n,value['variant_changes']) for n in (1,8,32)}
            self.assertEqual(families[32][:1],families[1],entry['id'])
            self.assertEqual(families[32][:8],families[8],entry['id'])
            by_id={v['id']:v for v in model['variables']}
            values={v['variable_id']:F.from_float(v['value']) for v in witness['candidate']['values']}
            expected=min(len(model['variables']),value['variant_changes'])
            for variant in families[32]:
                self.assertEqual(len(variant['changes']),expected,entry['id'])
                for change in variant['changes']:
                    lp_variants.check_change(by_id[change['variable_id']],values[change['variable_id']],change)
    def test_refusal_for_witness_less_instances(self):
        model=read_json(ROOT/'artifacts/lp-inputs-v1/gpup-development-scheduling-20x5.json')
        with self.assertRaises(ValueError):lp_variants.variants(model,None,47100,1,256)
        for instance_id in ['gpup-development-scheduling-20x5','gpup-development-scheduling-50x10','ta001-relaxation','ta011-relaxation']:
            with self.assertRaises(ValueError):lp_variants.check(instance_id)
        lp_variants.check('gpup-development-small-4')
    def test_request_documents_follow_the_batch_schema(self):
        model,witness=self.small()
        family=lp_variants.variants(model,witness,47108,8,256)
        document=lp_variants.request('gpup-development-small-4','variant',8,family,47108,256,28000)
        self.assertEqual(set(document),{'schema_version','kind','solves','variants','generator','batch_time_limit_ms'})
        with self.assertRaises(ValueError):lp_variants.request('x','repeat',8,family,None,None,28000)
        with self.assertRaises(ValueError):lp_variants.request('x','repeat',8,[],47108,256,28000)
        with self.assertRaises(ValueError):lp_variants.request('x','variant',8,family[:7],47108,256,28000)
        with self.assertRaises(ValueError):lp_variants.request('x','variant',8,family,None,256,28000)
        with self.assertRaises(ValueError):lp_variants.request('x','variant',8,family,47108,0,28000)
        with self.assertRaises(ValueError):lp_variants.request('x','warmed',8,[],None,None,28000)


class BudgetAuthorityTests(unittest.TestCase):
    """SPEC-0014 requirements 28-31: the v3 Study, its ceiling authority and frozen pins."""
    def test_study_v3_fields_and_v1_v2_unchanged(self):
        value=read_json(CONFIG)
        study=Study.from_protocol(value)
        self.assertEqual(study.prefix,'gpupt')
        self.assertEqual((study.study_cap_seconds,study.acceptance_cap_seconds,study.combined_cap_seconds),(2700,600,3300))
        self.assertEqual((study.prior_ns,study.prior_events),(3794758955639,6722))
        self.assertEqual(study.prior_hash,'ff6f1b5471e80791e964d1e6679017ea33593a7899718d0431f666cfaa5fa23b')
        self.assertEqual(study.additional_ns,3600*NS)
        self.assertEqual(study.cumulative_ceiling_ns,8102574545061)
        self.assertEqual(Study.from_protocol(read_json(ROOT/'benchmarks/configs/lp-research-v1.json')),STUDY_V1)
        self.assertEqual(STUDY_V1.additional_ns,0)
        v2=Study.from_protocol(read_json(ROOT/'benchmarks/configs/lp-research-v2.json'))
        self.assertEqual((v2.prefix,v2.prior_ns,v2.prior_events),('gpup5c',2235353878971,4996))
        self.assertEqual(v2.prior_hash,'737e1301cb31cf5d0ad0585aa81a4dc0b814615d39e4974827e504e880b11e5f')
        self.assertEqual((v2.study_cap_seconds,v2.acceptance_cap_seconds,v2.combined_cap_seconds),(1500,300,1800))
        self.assertEqual(v2.cumulative_ceiling_ns,STUDY_V1.cumulative_ceiling_ns)
        self.assertEqual(v2.additional_ns,0)
        with self.assertRaises(ValueError):Study.from_protocol(dict(value,schema_version=4))
    def test_ledger_for_enforces_the_v3_ceiling_authority(self):
        value=read_json(CONFIG)
        study=Study.from_protocol(value)
        ledger=ledger_for(study,protocol=value)
        self.assertEqual(ledger.slice_ns,study.cumulative_ceiling_ns)
        source=read_json(ROOT/value['source_campaign']['path'])
        self.assertEqual(study.cumulative_ceiling_ns,source['cumulative_gpu_ns']+study.additional_ns)
        wrong_decision=dict(value,decision=dict(value['decision'],sha256='0'*64))
        with self.assertRaises(ValueError):ledger_for(study,protocol=wrong_decision)
        wrong_source=dict(value,source_campaign=dict(value['source_campaign'],sha256='0'*64))
        with self.assertRaises(ValueError):ledger_for(study,protocol=wrong_source)
        wrong_ceiling=dict(value,cumulative_ceiling_ns=value['cumulative_ceiling_ns']-1)
        with self.assertRaises(ValueError):ledger_for(Study.from_protocol(wrong_ceiling),protocol=wrong_ceiling)
        # Without the protocol the v1/v2 rule applies unchanged and refuses the
        # raised ceiling, which differs from the source campaign's consumption.
        with self.assertRaises(ValueError):ledger_for(study)
        self.assertEqual(ledger_for(STUDY_V1).slice_ns,STUDY_V1.cumulative_ceiling_ns)
    def test_frozen_protocol_self_consistency_and_byte_pins(self):
        value=read_json(CONFIG)
        source=read_json(ROOT/value['source_campaign']['path'])
        self.assertEqual(value['cumulative_ceiling_ns'],source['cumulative_gpu_ns']+value['additional_gpu_seconds']*NS)
        for reference in [value['source_campaign'],value['decision'],value['extension_manifest']]:
            self.assertEqual(file_hash(ROOT/reference['path']),reference['sha256'],reference['path'])
        self.assertEqual(value['source_campaign']['path'],'benchmarks/configs/lp-precision-v4.json')
        self.assertEqual(value['decision']['path'],'docs/decisions/ADR-0023-repeated-solve-throughput.md')
        for path in ['benchmarks/manifests/lp-development-v1.json','benchmarks/manifests/lp-validation-v1.json','benchmarks/manifests/lp-held_out-v1.json','benchmarks/configs/lp-research-v1.json','benchmarks/configs/lp-campaign-v1.json']:
            self.assertEqual((ROOT/path).read_bytes(),subprocess.check_output(['git','show','b6732ec:'+path],cwd=ROOT),path)
        for path in ['benchmarks/configs/lp-research-v2.json','benchmarks/configs/lp-precision-v4.json']:
            self.assertEqual((ROOT/path).read_bytes(),subprocess.check_output(['git','show','1a453ee:'+path],cwd=ROOT),path)


class AnalysisTests(unittest.TestCase):
    """SPEC-0014 requirements 1-4 and 15-17: separate endpoint labels and
    analysis bitwise identity counts."""
    def synthetic_result(self):
        return dict(endpoint_labeling={'fresh':FRESH_ENDPOINT,'amortized':AMORTIZED_ENDPOINT,'comparison':SEPARATE_TITLE},
                    fresh_single_solve_latency=[dict(id='fresh/gpup-development-small-4/tuned-fp64')],
                    amortized_repeated_solve_throughput=[dict(id='batch-repeat/gpup-development-small-4/tuned-fp64/n8')],
                    paired_amortized_vs_fresh=[dict(title=SEPARATE_TITLE,endpoints='separate',statistics=None)])
    def test_amortized_endpoint_math_and_refusals(self):
        value=amortized(10**9,8)
        self.assertEqual(value['per_solve_ns'],125000000.0)
        self.assertEqual(value['solves_per_second'],8.0)
        for elapsed,solves in [(0,8),(None,8),(10**9,0),(10**9,-1),(10**9,None)]:
            with self.assertRaises(ValueError):amortized(elapsed,solves)
    def test_requirement15_fields_and_identity_counts(self):
        tuned=dict(record=dict(candidate=[0.0,1.5],termination='optimal'),
                   diagnostics=dict(dual=[-1.0,2.0]),
                   control=dict(logical_iterations=42,restarts=3,device_kernel_launches=252))
        research=dict(witness=dict(primal=[0.0,1.5],dual=[-1.0,2.0],status='optimal',proposed_steps=42,
                                   diagnostics=dict(restarts=3,kernel_launches=252)))
        self.assertEqual(tuned_bits(tuned),research_bits(research))
        self.assertEqual(set(tuned_bits(tuned)),{'primal','dual','status','logical_iterations','restarts','kernel_launches'})
        changed=dict(tuned_bits(tuned),restarts=2)
        self.assertEqual(identity_count([(tuned_bits(tuned),tuned_bits(tuned)),(tuned_bits(tuned),changed)]),
                         dict(compared=2,identical=1))
        self.assertEqual(identity_count([]),dict(compared=0,identical=0))
    def test_cross_mode_identity_excludes_launch_counts(self):
        # fused-fp64 runs two launches per proposal where intguard-fp64 runs
        # six: numerical trajectories agree bitwise while launch counts differ
        # by construction, so cross-mode counts must exclude them (the
        # analyze_lp_research.py endpoint-comparison convention).
        fused=dict(primal=[0.0],dual=[1.0],status='optimal',logical_iterations=200,restarts=0,kernel_launches=400)
        intguard=dict(fused,kernel_launches=1200)
        self.assertNotEqual(fused,intguard)
        self.assertEqual(cross_mode_bits(fused),cross_mode_bits(intguard))
        self.assertEqual(set(cross_mode_bits(fused)),{'primal','dual','status','logical_iterations','restarts'})
        self.assertEqual(identity_count([(cross_mode_bits(fused),cross_mode_bits(intguard))]),dict(compared=1,identical=1))
        changed=dict(intguard,kernel_launches=1200,restarts=1)
        self.assertEqual(identity_count([(cross_mode_bits(fused),cross_mode_bits(changed))]),dict(compared=1,identical=0))
    def test_report_labels_keep_the_endpoints_separate(self):
        check_endpoint_separation(self.synthetic_result())
        merged=self.synthetic_result()
        merged['amortized_repeated_solve_throughput']=[dict(id='fresh/gpup-development-small-4/tuned-fp64')]
        with self.assertRaises(ValueError):check_endpoint_separation(merged)
        untitled=self.synthetic_result()
        untitled['paired_amortized_vs_fresh']=[dict(title=None,endpoints='separate')]
        with self.assertRaises(ValueError):check_endpoint_separation(untitled)
        relabeled=self.synthetic_result()
        relabeled['endpoint_labeling']=dict(relabeled['endpoint_labeling'],amortized='single-solve latency')
        with self.assertRaises(ValueError):check_endpoint_separation(relabeled)
    def test_coverage_kinds_equal_the_planner_kind_universe(self):
        # Regression: the coverage loop once crashed concatenating a tuple to a
        # list; the frozen coverage kinds must match the planner's kind set.
        self.assertEqual(len(COVERAGE_KINDS),7)
        self.assertEqual(sorted(COVERAGE_KINDS),sorted(KINDS))
    def test_batch_exit_codes_mirror_solve_exit_codes(self):
        self.assertEqual([tuned_exit_code(t) for t in ['optimal','infeasible','unbounded','unbounded_or_infeasible']],[0,0,0,0])
        self.assertEqual([tuned_exit_code(t) for t in ['feasible','time_limit','iteration_limit','node_limit']],[1,1,1,1])
        self.assertEqual(tuned_exit_code('interrupted'),130)
        self.assertEqual([tuned_exit_code(t) for t in ['numerical_failure','backend_failure','unsupported']],[2,2,2])
        tuned={'backend':'cuda-lp-tuned'}
        solve=lambda termination,status,reason:dict(termination=termination,status=status,reason=reason)
        self.assertEqual(expected_batch_exit(tuned,[solve('optimal','certified_success',None)]),0)
        self.assertEqual(expected_batch_exit(tuned,[solve('optimal','certified_success',None),solve('iteration_limit','work_limit',None)]),1)
        self.assertEqual(expected_batch_exit(tuned,[solve('optimal','certified_success',None),solve(None,'not_attempted','batch_time_limit')]),1)
        self.assertEqual(expected_batch_exit(tuned,[solve('optimal','certified_success',None),solve(None,'not_attempted','cancelled')]),130)
        self.assertEqual(expected_batch_exit(tuned,[solve(None,'failed','device fault')]),2)
        self.assertEqual(expected_batch_exit({'mode':'fused-fp64'},[solve(None,'not_attempted','shared host lease required')]),0)


def protocol_from(mutated):
    with tempfile.TemporaryDirectory() as tmp:
        path=Path(tmp)/'protocol.json';write_json(path,mutated)
        return protocol(path)


if __name__=='__main__':unittest.main()
