"""Frozen research boundaries, exact rounding and shared accounting."""
from collections import Counter
from fractions import Fraction as F
from pathlib import Path
import sys
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'))
from analyze_lp_rounding import components,power_exponent
from benchmark_lp_research import protocol,jobs,label
from lp_research_budget import category_usage,PRIOR_NS
from lp_protocol import Ledger
class ResearchTests(unittest.TestCase):
    def test_frozen_grid_and_original_targets(self):
        value,base,manifest=protocol();schedule=list(jobs(value,base,manifest))
        self.assertEqual(Counter(j['kind'] for j in schedule),dict(timing=432,profile=48,short=336,trace=24))
        self.assertEqual(len({label(j) for j in schedule}),840)
        self.assertEqual(base['solve']['seed'],17);self.assertEqual(base['order_seed'],17001)
        self.assertEqual(value['prior_gpu_ns'],PRIOR_NS)
        self.assertTrue(all(j['instance']['id'].startswith('gpup-development-') or j['instance']['id'].startswith('ta') for j in schedule))
    def test_three_components_are_exact_and_two_are_not_assumed_exact(self):
        x=1/3;parts=components(x)
        self.assertEqual(sum(map(F,parts)),F(x));self.assertNotEqual(sum(map(F,parts[:2])),F(x))
        self.assertEqual(power_exponent(1.4),0);self.assertEqual(power_exponent(1.5),1)
        self.assertEqual(power_exponent(float.fromhex('0x1p-1074')),-1074)
    def test_acceptance_and_study_share_ledger_with_separate_caps(self):
        with tempfile.TemporaryDirectory() as tmp:
            with Ledger(Path(tmp),'a'*64) as ledger:
                r=ledger.reserve('gpup5b-study-one',2,phase='screening');ledger.settle(r,123)
                r=ledger.reserve('gpup5b-accept-one',2,phase='screening');ledger.settle(r,456)
                self.assertEqual(category_usage(ledger,'study'),123);self.assertEqual(category_usage(ledger,'accept'),456);self.assertEqual(ledger.totals(),579)
    def test_archived_report_is_not_rewritten_by_new_notes(self):
        import subprocess
        path='docs/benchmarks/lp-fp32-slowdown-diagnosis.md'
        old=subprocess.check_output(['git','show','7636845:'+path],cwd=ROOT)
        self.assertEqual((ROOT/path).read_bytes(),old)

    def test_independent_rational_sparse_and_product_fixtures_reproduce(self):
        from lp_research_oracle import generate,verify_products
        from lp_protocol import read_json
        self.assertEqual(generate(),read_json(ROOT/'crates/optimizer-lp/tests/fixtures/research-sparse.json'))
        self.assertEqual(verify_products(),39)

class ResearchV2Tests(unittest.TestCase):
    """ADR-0022: the v2 protocol is frozen, tiered, extension-aware and leaves v1 untouched."""
    CONFIG=ROOT/'benchmarks/configs/lp-research-v2.json'
    def test_frozen_v2_grid_tiers_and_budget_identity(self):
        from lp_protocol import read_json,file_hash
        from lp_research_budget import Study,STUDY_V1
        value,base,manifest=protocol(self.CONFIG);schedule=list(jobs(value,base,manifest))
        self.assertEqual(len(schedule),value['planned_attempts']);self.assertEqual(len(schedule),874)
        self.assertEqual(Counter(j['kind'] for j in schedule),dict(timing=678,short=177,profile=14,trace=5))
        self.assertEqual(len({label(j) for j in schedule}),874)
        self.assertEqual(set(value['tiers']),{'1e-9','1e-6','1e-4'})
        self.assertEqual(value['tiers']['1e-9'],base['solve']['tolerances'])
        self.assertTrue(all(j['instance']['id'].startswith(('gpup-development-','gpup-extension-','ta')) for j in schedule))
        self.assertFalse(any('components' in j['config']['id'] for j in schedule))
        study=Study.from_protocol(value)
        self.assertEqual((study.prefix,study.prior_ns,study.prior_events),('gpup5c',2235353878971,4996))
        self.assertEqual(study.prior_hash,'737e1301cb31cf5d0ad0585aa81a4dc0b814615d39e4974827e504e880b11e5f')
        self.assertEqual((study.study_cap_seconds,study.acceptance_cap_seconds,study.combined_cap_seconds),(1500,300,1800))
        self.assertEqual(study.cumulative_ceiling_ns,STUDY_V1.cumulative_ceiling_ns)
        self.assertEqual(Study.from_protocol(read_json(ROOT/'benchmarks/configs/lp-research-v1.json')),STUDY_V1)
        # Labels of v1 jobs never carry a tier; v2 labels always do.
        v1=list(jobs(*protocol()));self.assertTrue(all(label(j).count('-fp')>=1 and not label(j).endswith(('1e-9','1e-6','1e-4')) for j in v1))
        self.assertTrue(all(label(j).endswith(('-1e-9','-1e-6','-1e-4')) for j in schedule))
    def test_v2_requests_record_tiers_and_extension_limits(self):
        from benchmark_lp_research import settings_for,request_for
        value,base,manifest=protocol(self.CONFIG)
        for job in jobs(value,base,manifest):
            options,method,seconds=settings_for(job,base,value)
            self.assertEqual(options['tolerances'],value['tiers'][job['tier']])
            self.assertEqual(seconds,30 if job['instance']['id'].startswith('gpup-extension-') else 10)
            self.assertEqual(options['time_limit_ms'],seconds*1000)
            if job['kind'] in ('short','trace'):self.assertEqual((options['iteration_limit'],method['iteration_limit']),(200,200))
            if 'mode' in job['config']:
                r=request_for(job,base,value,'a'*64,'b'*64,'c'*64,'d'*64)
                self.assertEqual(r['schema_version'],2);self.assertEqual(r['options']['tolerances'],value['tiers'][job['tier']])
    def test_extension_manifest_is_frozen_and_v1_outputs_are_unchanged(self):
        import subprocess
        from lp_protocol import read_json,validate,file_hash
        manifest=validate('manifest',read_json(ROOT/'benchmarks/manifests/lp-development-extension-v1.json'))
        self.assertEqual(manifest['schema_version'],2);self.assertEqual(manifest['partition'],'development')
        self.assertEqual([i['id'] for i in manifest['instances']],['gpup-extension-irregular-32768','gpup-extension-irregular-65536','gpup-extension-dense_block-65536','gpup-extension-mixed-65536'])
        self.assertTrue(all(i['time_limit_seconds']==30 and i['generator']['version']==2 and i['bytes']<=268435456 for i in manifest['instances']))
        development=read_json(ROOT/'benchmarks/manifests/lp-development-v1.json')
        self.assertEqual(manifest['extends']['sha256'],file_hash(ROOT/'benchmarks/manifests/lp-development-v1.json'))
        self.assertFalse({i['group'] for i in manifest['instances']}&{i['group'] for i in development['instances']})
        self.assertFalse({i['generator']['seed'] for i in manifest['instances']}&{i['generator']['seed'] for i in development['instances']})
        for path in ['benchmarks/manifests/lp-development-v1.json','benchmarks/manifests/lp-validation-v1.json','benchmarks/manifests/lp-held_out-v1.json','benchmarks/configs/lp-research-v1.json','benchmarks/configs/lp-campaign-v1.json']:
            self.assertEqual((ROOT/path).read_bytes(),subprocess.check_output(['git','show','b6732ec:'+path],cwd=ROOT),path)
        with self.assertRaises(ValueError):validate('manifest',dict(manifest,schema_version=3))
    def test_mixed_family_witness_is_exact_with_free_variables_and_one_sided_rows(self):
        from lp_generate import mixed
        model,witness=mixed('exact-mixed',96,17112)
        x=[F.from_float(a['value']) for a in witness['candidate']['values']];y=list(map(F.from_float,witness['dual']))
        n=len(x);costs={t['variable_id']:F.from_float(t['coefficient']) for t in model['objective']['terms']}
        reduced=[costs.get(j,F()) for j in range(n)];dual=F.from_float(model['objective']['offset'])
        kinds=Counter()
        for i,row in enumerate(model['constraints']):
            activity=sum(F.from_float(t['coefficient'])*x[t['variable_id']] for t in row['terms'])
            kinds[(row['lower']['kind'],row['upper']['kind'])]+=1
            if row['lower']['kind']=='finite':self.assertLessEqual(F.from_float(row['lower']['value']),activity)
            if row['upper']['kind']=='finite':self.assertLessEqual(activity,F.from_float(row['upper']['value']))
            side=row['lower' if y[i]>=0 else 'upper'];self.assertEqual(side['kind'],'finite')
            dual+=y[i]*F.from_float(side['value'])
            for t in row['terms']:reduced[t['variable_id']]-=y[i]*F.from_float(t['coefficient'])
            self.assertTrue(any(float(F.from_float(t['coefficient']))!=struct_f32(t['coefficient']) for t in row['terms']))
        free=0
        for j,v in enumerate(model['variables']):
            if v['lower']['kind']!='finite':self.assertEqual(reduced[j],0);free+=1
            else:dual+=min(F(),reduced[j])
        primal=F.from_float(model['objective']['offset'])+sum(costs.get(j,F())*v for j,v in enumerate(x))
        self.assertEqual(primal,dual);self.assertGreater(free,0)
        self.assertEqual(set(kinds),{('finite','finite'),('finite','positive_infinity'),('negative_infinity','finite')})
    def test_doublefloat_rational_fixture_reproduces(self):
        from lp_research_oracle import generate_doublefloat
        from lp_protocol import read_json
        self.assertEqual(generate_doublefloat(),read_json(ROOT/'crates/optimizer-lp/tests/fixtures/research-doublefloat.json'))

def struct_f32(x):
    import struct
    return struct.unpack('>f',struct.pack('>f',x))[0]
