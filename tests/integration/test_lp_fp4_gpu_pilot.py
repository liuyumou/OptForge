"""Independent pre-device contracts for SPEC-0027 (never runs GPU jobs)."""
from fractions import Fraction as Q
from pathlib import Path
import sys
import unittest
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'))
import lp_fp4_contract as c
import lp_fp4_gpu_oracle as o
from lp_fp4_reference_v2 import rounded_encode,pair_round

class PilotContracts(unittest.TestCase):
    def test_all_e2m1_codes_and_ties(self):
        for code in range(16):
            if code==8:continue
            self.assertEqual(o.nearest(c.code_value(code),4),code)
        for j in range(7):
            mid=(c.MAGNITUDES[j]+c.MAGNITUDES[j+1])/2
            self.assertEqual(o.nearest(mid,4),j+(j&1))
            self.assertEqual(o.nearest(mid+Q(1,1<<40),4),j+1)
            self.assertEqual(o.nearest(mid-Q(1,1<<40),4),j)
    def test_packing_and_instruction_byte_layout(self):
        codes=[i if i!=8 else 0 for i in range(16)]*2
        words=o.pack(codes,4);self.assertEqual(o.unpack(words,4,32),codes)
        # Storage nibbles expand into low four bits of each MMA byte.
        for lane in range(4):
            fragment=sum(codes[4*lane+j]<<(8*j) for j in range(4))
            self.assertEqual(fragment&0xf0f0f0f0,0)
    def test_transpose_matches_existing_exact_contract(self):
        values=tuple(Q((13*i+7*j)%17-8,64) for i in range(32) for j in range(32))
        for k in (2,4,8):
            words,exponents,represented,_=o.encode(values,4,k)
            contract=c.encode(values,k)
            self.assertEqual(represented,c.decode(contract))
            trans=c.decode(c.transpose_tile(contract))
            self.assertEqual(trans,[represented[j*32+i] for i in range(32) for j in range(32)])
            self.assertEqual(o.decode_planes(words,exponents,4,1024),represented)
    def test_scale_extremes_and_refusal(self):
        for e in (-48,48):
            values=(Q(6)*Q(2)**e,)*32
            self.assertEqual(o.encode(values,4,2)[2],list(values))
        with self.assertRaises(ValueError):o.encode((Q(7)*Q(2)**48,)*32,4,2)
    def test_local_budget_does_not_cancel_encoding(self):
        pair,_=pair_round(Q(1,3));target=pair-Q(1,1<<55)
        blocks,bound=rounded_encode([target],8)
        self.assertGreaterEqual(bound,c.read_rational(blocks[0]['remainder_bound']))
        self.assertGreaterEqual(bound,abs(c.decode(blocks[0])[0]-target))
    def test_projection_boundaries(self):
        for x in (Q(-2),Q(-1),Q(0),Q(1),Q(2)):
            result=c.project_interval(x,0,-1,1)
            self.assertNotEqual(result['decision'],'ambiguous')
        self.assertEqual(c.project_interval(1,Q(1,100),-1,1)['decision'],'ambiguous')
    def test_tail_and_nontrivial_reference(self):
        r=o.request('irregular-29',64,1)
        for row in range(32):
            for col in range(32):
                if row>=29 or col>=29:self.assertEqual(r['matrix'][row*32+col],0)
        state=o.reference(r,8)
        self.assertTrue(any(state));self.assertTrue(all(v==0 for j,v in enumerate(state) if j%32>=29))
    def test_control_formats(self):
        for bits,k in [(8,4),(16,2)]:
            values=tuple(Q(i-16,64) for i in range(32))
            w,e,v,error=o.encode(values,bits,k)
            self.assertEqual(v,list(values));self.assertEqual(error,0)
            self.assertEqual(o.decode_planes(w,e,bits,32),v)
    def test_corrupt_packing_refuses(self):
        for bits,codes in [(4,[16]*32),(8,[127]*32),(16,[0x7c00]*32)]:
            with self.assertRaises((ValueError,OverflowError)):o.pack(codes,bits)

if __name__=='__main__':unittest.main()
