"""Pure CPU checks of the post-device failure reader's binary64 comparison."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))
from report_lp_tensor_cost_failure import ordered_bits,vector_differences,has_skip

class FailureReportTests(unittest.TestCase):
 def test_quoted_source_is_not_a_runtime_skip(self):
  self.assertFalse(has_skip("  if 'SKIP ' in text: raise ValueError('failed')"))
  self.assertTrue(has_skip('  SKIP GPU unavailable'))

 def test_adjacent_positive_and_negative_values(self):
  import math
  for value in [1.0,-1.0]:self.assertEqual(abs(ordered_bits(value)-ordered_bits(math.nextafter(value,2.0))),1)

 def test_nonfinite_values_refuse(self):
  for value in [float('inf'),float('-inf'),float('nan')]:
   with self.assertRaises(ValueError):ordered_bits(value)

 def test_each_state_vector_is_compared(self):
  names=['primal','dual','scaled_primal','scaled_dual']
  left=', '.join(name+': [1.0]' for name in names)
  right=', '.join(name+': [1.0000000000000002]' for name in names)
  rows=vector_differences('left: Outcome '+left+' right: Outcome '+right)
  self.assertEqual([r['vector'] for r in rows],names)
  self.assertTrue(all(r['maximum_ulp_distance']==1 for r in rows))

 def test_equal_vectors_cannot_prove_the_failure(self):
  part=', '.join(name+': [1.0]' for name in ['primal','dual','scaled_primal','scaled_dual'])
  with self.assertRaises(ValueError):vector_differences('left: Outcome '+part+' right: Outcome '+part)
