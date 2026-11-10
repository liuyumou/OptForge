"""Focused v2 adapter corrections; vendor APIs are mocked, GPUs hidden."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'))
import lp_baseline_adapters_v2 as adapters
from lp_baseline_common_v2 import load, options, put, ref, tiny_model
from lp_baseline_contract import canonicalize
from lp_baseline_study_v2 import validate_proposal
from lp_baseline_test_support import checker


class CorrectedAdapters(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        global CHECKER
        CHECKER = checker()

    def test_actual_cuopt_bound_api_names_and_max_sign(self):
        class DataModel:
            def set_csr_constraint_matrix(self,v,i,p): self.matrix=(v,i,p)
            def set_objective_coefficients(self,v): self.cost=v
            def set_objective_offset(self,v): self.offset=v
            def set_maximize(self,v): self.maximize=v
            def set_variable_lower_bounds(self,v): self.vl=v
            def set_variable_upper_bounds(self,v): self.vu=v
            def set_constraint_lower_bounds(self,v): self.rl=v
            def set_constraint_upper_bounds(self,v): self.ru=v
            def get_constraint_matrix_values(self): return self.matrix[0]
            def get_constraint_matrix_indices(self): return self.matrix[1]
            def get_constraint_matrix_offsets(self): return self.matrix[2]
            def get_objective_coefficients(self): return self.cost
            def get_objective_offset(self): return self.offset
            def get_sense(self): return self.maximize
            def get_variable_lower_bounds(self): return self.vl
            def get_variable_upper_bounds(self): return self.vu
            def get_constraint_lower_bounds(self): return self.rl
            def get_constraint_upper_bounds(self): return self.ru
        class Settings:
            def __init__(self): self.values={}
            def set_parameter(self,k,v): self.values[k]=v
            def get_parameter(self,k): return self.values[k]
        class Solution:
            def get_primal_solution(self): return [2.]
            def get_dual_solution(self): return [1.]
            def get_reduced_cost(self): return [0.]
            def get_termination_reason(self): return 'Optimal'
            def get_solve_time(self): return .001
            def get_solved_by(self): return 1
            def get_lp_stats(self): return {'nb_iterations':40}
        lp=types.SimpleNamespace(DataModel=DataModel,SolverSettings=Settings,Solve=lambda *_:Solution())
        c=next(c for c in load(ROOT/'benchmarks/configs/lp-external-baseline-proposal-v2.json')['configurations'] if c['id']=='cuopt-pdlp-double')
        model=canonicalize(json.dumps(tiny_model('maximize','ranged')).encode())
        with patch.dict(sys.modules,{'cuopt':types.SimpleNamespace(linear_programming=lp)}):
            result=adapters.cuopt(model,c,20,Path('/unused'),True)
        self.assertEqual(result['dual'],[-1.])
        self.assertEqual(result['readback'],'binary64_and_csr_exact')
        self.assertEqual(result['executed_device'],'unknown')

    def test_retained_native_thread_contract(self):
        self.assertEqual(options(20)['threads'],1)
        with tempfile.TemporaryDirectory(dir=ROOT/'artifacts') as tmp:
            root=Path(tmp)
            put(root/'model.json',tiny_model('minimize','ranged'))
            put(root/'options.json',options(20))
            p=subprocess.run([str(CHECKER),'highs',str(root/'model.json'),str(root/'options.json'),str(root/'out.json')],capture_output=True,timeout=5)
            self.assertEqual(p.returncode,0,p.stderr)
            value=load(root/'out.json')
            self.assertEqual(value['record']['options']['threads'],1)
            self.assertEqual(value['diagnostics']['dual'],[1.])

    def test_proposal_delta_is_exact(self):
        proposal=load(ROOT/'benchmarks/configs/lp-external-baseline-proposal-v2.json')
        validate_proposal(proposal,True)
        proposal['configurations'][3]['parameters']['relative_gap_tolerance']=1e-6
        with self.assertRaisesRegex(ValueError,'unauthorized'): validate_proposal(proposal)

    def test_project_export_leaves_observation_path_available(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'artifacts') as tmp:
            root=Path(tmp)
            original=root/'model.json'
            put(original,tiny_model('minimize','ranged'))
            model=canonicalize(original.read_bytes())
            config=load(ROOT/'benchmarks/configs/lp-external-baseline-proposal-v2.json')['configurations'][0]
            manifest=dict(checker=ref(CHECKER),project_binary=ref(CHECKER),
                project_configuration=ref(ROOT/'benchmarks/configs/lp-convergence-v1.json'),
                project_cuda_directory='artifacts/unused',device_uuid='GPU-test')
            def native(cmd,**_):
                self.assertEqual(load(cmd[cmd.index('--config')+1])['threads'],1)
                requested=load(cmd[cmd.index('--lp-execution')+1])
                self.assertEqual(requested['allocation'],'resident')
                output=cmd[cmd.index('--lp-evidence')+1]
                put(output,dict(endpoint=dict(record=dict(backend='cuda-lp-tuned',termination='feasible',
                    candidate=dict(values=[dict(variable_id=9,value=1.)])),
                    diagnostics=dict(dual=[1.],iterations=2,kernel_launches=3))))
            with patch.object(adapters.subprocess,'run',native):
                result=adapters.retained(model,config,20,root,True,manifest,original)
            put(root/'execution.json',dict(observation='durable'))
            self.assertEqual(result['primal'],[1.])
            self.assertEqual(result['effective_parameters']['threads'],1)


if __name__=='__main__': unittest.main()
