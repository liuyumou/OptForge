"""Failure, split and inferential boundaries of GPUP-9 (no GPU execution)."""
import copy
import math
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))
import lp_gpup9_protocol as protocol
from lp_gpup9_common import configs, CPU_CAPS, GPU_CAPS
from lp_gpup9_analysis import paired, assess
from lp_gpup9_budget import accounting, admission_open
from lp_baseline_common import put


def row(cell,ns=100000000):
    return dict(**cell,complete_session_ns=ns,setup_ns=1,teardown_ns=1,
        records=[dict(certified=True,attempted={'34':200},physical=200,logical=200,
                      recoveries=[],costs_ns={'checker':10}) for _ in range(cell['count'])])


class Gpup9Tests(unittest.TestCase):
    def test_partition_groups_and_seeds_never_overlap(self):
        groups=[g for p in ['admission','screening','validation','holdout'] for g in protocol.descriptors(p)]
        self.assertEqual(len(groups),len({g['id'] for g in groups}))
        self.assertEqual(len(groups),len({g['seed'] for g in groups}))

    def test_holdout_balance_and_complete_roster(self):
        cfg={k:configs()[k] for k in ['native-w32-s1','fp4x2-w16-s1']}
        cells=protocol.schedule('holdout',cfg)
        self.assertEqual(len(cells),384)
        self.assertEqual(len({c['id'] for c in cells}),384)
        for group in protocol.descriptors('holdout'):
            for endpoint in ['prepared','cold']:
                for key in cfg:
                    rs=[c for c in cells if c['group']==group['id'] and c['endpoint']==endpoint and c['config']==key]
                    self.assertEqual(sum(c['position']==0 for c in rs),8)
                    self.assertEqual({c['count'] for c in rs},{1 if endpoint=='cold' else 32})

    def test_whole_stage_reservations_fit_independent_caps(self):
        self.assertEqual(sum(CPU_CAPS.values()),112000)
        self.assertEqual(sum(GPU_CAPS.values()),15500)
        for stage,(blocks,count,seconds) in protocol.STAGES.items():
            self.assertLessEqual(blocks*4*seconds,CPU_CAPS[stage])
            self.assertLessEqual(blocks*seconds,GPU_CAPS[stage])

    def test_selection_rejects_missing_duplicate_or_changed_cells(self):
        cfg=configs();cells=protocol.schedule('screening',cfg);rs=[row(c) for c in cells]
        for bad in [rs[:-1],rs[:-1]+[rs[0]]]:
            with self.assertRaises(Exception):protocol.select('screening',bad,cells,cfg)
        changed=copy.deepcopy(rs);changed[0]['family']='holdout-generic-2048'
        with self.assertRaises(Exception):protocol.select('screening',changed,cells,cfg)

    def test_coverage_precedes_speed_and_holdout_cannot_tune(self):
        cfg=configs();cells=protocol.schedule('screening',cfg);rs=[row(c) for c in cells]
        for r in rs:
            if r['config']=='fp4x2-w16-s1':
                r['complete_session_ns']=1;r['records'][0]['certified']=False
        selected=protocol.select('screening',rs,cells,cfg)['selected']
        self.assertIn('fp4x2-w32-s1',selected)
        self.assertNotIn('fp4x2-w16-s1',selected)
        with self.assertRaises(Exception):protocol.select('holdout',rs,cells,cfg)

    def test_incomplete_or_uncertified_or_native_only_fp4_never_passes(self):
        a=[row(dict(id=str(i),count=1),200000000) for i in range(16)]
        b=[row(dict(id=str(i),count=1),100000000) for i in range(16)]
        self.assertTrue(paired(a,b,16)['scoped_pass'])
        self.assertFalse(paired(a[:-1],b[:-1],16)['scoped_pass'])
        b[0]['records'][0]['certified']=False
        self.assertFalse(paired(a,b,16)['scoped_pass'])
        b[0]['records'][0]['certified']=True;b[0]['records'][0]['attempted']={'32':200}
        self.assertFalse(paired(a,b,16)['scoped_pass'])

    def test_multiplicity_and_absolute_value_floor(self):
        a=[row(dict(id=str(i),count=1),105000000) for i in range(16)]
        b=[row(dict(id=str(i),count=1),100000000) for i in range(16)]
        r=paired(a,b,16)
        self.assertEqual(r['ratio']['rank'],2)
        self.assertFalse(r['scoped_pass'])
        self.assertLessEqual(24*(1-r['ratio']['coverage']),.05)

    def test_unsettled_job_is_fully_charged_and_blocks_admission(self):
        with tempfile.TemporaryDirectory() as folder:
            base=Path(folder);(base/'resources').mkdir()
            # Write directly: temporary fixtures are intentionally outside repository.
            import json
            (base/'resources/crash.reservation.json').write_text(json.dumps(dict(phase='holdout',gpu=True,cpu_ns=400000000000,gpu_ns=100000000000)))
            cpu,gpu=accounting(base)
            self.assertEqual(cpu['holdout'],400000000000)
            self.assertEqual(gpu['holdout'],100000000000)
            with self.assertRaises(Exception):admission_open(base)

    def test_closed_allocation_refuses_execution(self):
        with tempfile.TemporaryDirectory() as folder:
            base=Path(folder);(base/'CLOSED.json').write_text('{}')
            with self.assertRaises(Exception):admission_open(base)

    def test_invalid_pair_timing_or_asymmetric_coverage_refuses(self):
        a=[row(dict(id='a',count=1))];b=[row(dict(id='b',count=1))]
        with self.assertRaises(Exception):paired(a,[],16)
        for value in [0,-1,float('nan'),True]:
            b[0]['complete_session_ns']=value
            with self.assertRaises(Exception):paired(a,b,16)

    def test_strict_schema_unknown_fields_paths_and_cold_count(self):
        from lp_gpup9_schema import validate_session
        import jsonschema
        cell=dict(id='b00-test',block=0,group='holdout-small-33',family='small-33',endpoint='cold',config='fp4x2-w16-s1',position=0,count=1)
        value=row(cell);value.update(schema_version=1,kind='gpup9-session')
        item=dict(path='artifacts/gpup9-v1/result.json',sha256='a'*64)
        value['records'][0].update(index=0,scenario=0,result=item,model=item,complete_ns=10,solve_ns=9,gpu_us=0,final_lane=34)
        value['records'][0]['costs_ns'].update(checkpoint=1,rollback=1,conversion=1)
        validate_session(value)
        extra=copy.deepcopy(value);extra['silent_override']=True
        with self.assertRaises(jsonschema.ValidationError):validate_session(extra)
        escaped=copy.deepcopy(value);escaped['records'][0]['result']['path']='artifacts/gpup9-v1/../secret.json'
        with self.assertRaises(Exception):validate_session(escaped)
        bad=copy.deepcopy(value);bad['count']=4;bad['records']*=4
        with self.assertRaises(Exception):validate_session(bad)

    def test_new_operator_groups_are_distinct_and_reproducible(self):
        from lp_gpup9_models import operator
        import numpy as np
        a,_=operator(protocol.descriptors('screening')[0])
        repeat,_=operator(protocol.descriptors('screening')[0])
        other,_=operator(protocol.descriptors('admission')[0])
        self.assertTrue(np.array_equal(a,repeat))
        self.assertFalse(np.array_equal(a,other))

    def test_sparse_seed_changes_operator_without_changing_sparsity(self):
        from lp_gpup9_models import operator
        import numpy as np
        a,_=operator(protocol.descriptors('admission')[1])
        b,_=operator(protocol.descriptors('screening')[1])
        self.assertFalse(np.array_equal(a,b))
        self.assertTrue(np.array_equal(a!=0,b!=0))
        self.assertEqual(np.count_nonzero(a),256)

    def test_projection_keeps_fixed_cost_and_uses_maximum_request_cost(self):
        pilot=dict(complete_session_ns=12000000000,setup_ns=7000000000,teardown_ns=1000000000,
                   records=[dict(complete_ns=1000000000),dict(complete_ns=3000000000)])
        self.assertEqual(protocol.projected_session(pilot,1),11)
        self.assertEqual(protocol.projected_session(pilot,4),20)
        with self.assertRaises(Exception):protocol.projected_session(pilot,0)

    def test_stage_feasibility_counts_scientific_caps_not_live_metadata_job(self):
        cpu={k:0 for k in CPU_CAPS};gpu={k:0 for k in GPU_CAPS}
        cpu['implementation']=1200*10**9
        protocol.stage_budget_fits('screening',cpu,gpu)
        cpu['screening']=1201*10**9
        with self.assertRaises(Exception):protocol.stage_budget_fits('screening',cpu,gpu)
        cpu['screening']=0;gpu['screening']=301*10**9
        with self.assertRaises(Exception):protocol.stage_budget_fits('screening',cpu,gpu)


if __name__=='__main__':unittest.main()
