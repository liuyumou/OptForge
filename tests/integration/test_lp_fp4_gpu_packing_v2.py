"""New CPU-only ISA byte layout contracts; preserves frozen v1 software tests."""
from pathlib import Path
import sys
import unittest
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'))
import lp_fp4_gpu_diagnosis_v2 as d
import lp_fp4_gpu_oracle as o

class CorrectedIsaLayout(unittest.TestCase):
    def test_all_canonical_codes_use_central_bits(self):
        for code in range(16):
            if code==8:continue
            byte=d.isa_byte(code)
            self.assertEqual(byte&0xc3,0)
            self.assertEqual(d.isa_decode(byte),o.decode(code,4))
    def test_all_pair_products_preserve_sign_and_magnitude(self):
        codes=[i for i in range(16) if i!=8]
        for a in codes:
            for b in codes:self.assertEqual(d.isa_decode(d.isa_byte(a))*d.isa_decode(d.isa_byte(b)),o.decode(a,4)*o.decode(b,4))
    def test_wrong_low_nibble_is_a_distinct_regression(self):
        self.assertNotEqual(d.isa_decode(9),o.decode(9,4))
        self.assertEqual(d.isa_decode(d.isa_byte(9)),o.decode(9,4))
    def test_candidate_only_changes_both_fragment_expansions(self):
        old=(ROOT/'research/lp-fp4-gpu-pilot/cuda/pilot.cu').read_text()
        new=(ROOT/'research/lp-fp4-gpu-pilot/cuda/pilot_v2.cu').read_text()
        new=new.replace('// CPU-prepared v2 packing correction; v1 frozen failure remains exact.\n','')
        new=new.replace('if constexpr(F==4)code<<=2; // PTX kind::f8f6f4 E2M1 occupies bits 5:2.\n                    ','')
        new=new.replace('if constexpr(F==4)code<<=2; // Two zero bits above and below each nibble.\n                    ','')
        self.assertEqual(new,old)

if __name__=='__main__':unittest.main()
