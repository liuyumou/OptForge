"""Preserved dispatch and independently checkable direct rectangular endpoints."""
from pathlib import Path
import json
import sys
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'tools'))
import lp_sp_pricing_rectangular_run as subject
from lp_sp_pricing_budget import BASE
from lp_sp_pricing_nontall_experiment import generate
from lp_sp_pricing_recovery_endpoint_balanced import prepare
from lp_sp_pricing_scale_verify import check as exact_check
from lp_sp_pricing_factor_proof import check as implicit_check

class RectangularRecovery(unittest.TestCase):
    def test_square_wide_tall_and_large_shapes_delegate_unchanged(self):
        with tempfile.TemporaryDirectory() as temporary:
            model=Path(temporary)/'model.json'
            for m,n in ((16,16),(8,32),(32,16),(8192,4097),(65535,4096)):
                model.write_text(json.dumps(dict(rows=m,columns=n)))
                with patch.object(subject.previous,'run',return_value='delegated') as delegate,patch.object(subject.factor_projection,'projection',side_effect=AssertionError('unexpected projection')):
                    self.assertEqual(subject.run(model,Path(temporary)/'out',17,False,'cpu',64),'delegated')
                    delegate.assert_called_once_with(model,Path(temporary)/'out',17,False,'cpu')
    def test_small_rectangular_endpoint_passes_independent_original_model_check(self):
        with tempfile.TemporaryDirectory(dir=BASE) as temporary:
            out=Path(temporary);spec=dict(name='rectangular-test',m=24,n=16,degree=16,layout='band',shift=1,scaled=False,mixed=True)
            model=generate(spec,127007,out/'model');path=Path(model['model']['path'])
            with patch.object(subject.previous.original.legacy,'certified_factor_proposal',side_effect=AssertionError('CPU presolve must be skipped')):
                self.assertFalse(subject.run(path,out/'response.json',20,False,'cpu',16))
            prepare(path,out/'response.json',out/'certificate.json');cert=json.loads((out/'certificate.json').read_text())
            proof=(implicit_check if cert.get('implicit_certificate') else exact_check)(path,out/'certificate.json')
            self.assertTrue(proof['accepted']);self.assertEqual(proof['visited_nonzeros'],24*16)
    def test_invalid_configuration_rejected_before_any_solver_work(self):
        with patch.object(subject.previous,'run',side_effect=AssertionError('unexpected old path')):
            with self.assertRaises(ValueError):subject.run(Path('/absent'),Path('/absent'),rho_multiplier=0)
