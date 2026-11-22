"""New lifetime bounds remove allocations, never resource headroom or GPU checks."""
import sys
from pathlib import Path
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))
from lp_billion_campaign import capacity
from lp_billion_memory_bounds_final import bounded_capacity


class BoundedMemoryContracts(unittest.TestCase):
    def coupled(self):
        return dict(rows=15_625_000,columns=15_625_024,nonzeros=1_000_000_000,
                    canonical_tiles=976_564,covered_nnz=750_000_000)
    def test_coupled_has_complete_stage_bounds_and_unchanged_device_reservation(self):
        p=self.coupled();old=capacity(p,'fp4x2',borrowed_operator=True);new=bounded_capacity(p,'fp4x2')
        self.assertEqual(new['host_gib']+4,68)
        self.assertEqual(old['host_gib']+4,72)
        self.assertEqual(new['device_bytes'],old['device_bytes'])
        self.assertEqual(new['host_bytes'],max(new['stage_live_bytes'].values())+8*(1<<30))
        self.assertEqual(new['peak_stage'],'cpu_construction')
    def test_no_eligible_tile_does_not_allocate_full_residual_matrices(self):
        p=dict(self.coupled(),canonical_tiles=0,covered_nnz=0)
        new=bounded_capacity(p,'fp4x2')
        self.assertEqual(new['packed_bytes_upper'],0)
        self.assertLess(new['packing_scratch_bytes_upper'],5*p['columns']+1024)
    def test_native_and_fp32_also_account_for_repaired_witnesses(self):
        p=self.coupled()
        for lane in ['native','fp32']:
            new=bounded_capacity(p,lane);old=capacity(p,lane,borrowed_operator=True)
            self.assertEqual(new['packed_bytes_upper'],0)
            self.assertGreaterEqual(new['stage_live_bytes']['solve_and_certificate'],old['host_bytes']-8*(1<<30))
    def test_packed_bound_covers_both_orientations_and_residuals(self):
        p=self.coupled();n=bounded_capacity(p,'fp4x2')
        self.assertGreaterEqual(n['packed_bytes_upper'],24*250_000_000+2048*p['canonical_tiles'])
        self.assertTrue(n['host_packed_released_before_control'] and n['strict_checker_unchanged'])

    def test_cpu_fallback_keeps_prepared_values_alive_during_clone(self):
        p=self.coupled();new=bounded_capacity(p,'fp4x2');z=p['nonzeros'];m=p['rows'];n=p['columns']
        resident=40*z+56*m+84*n
        self.assertGreaterEqual(new['stage_live_bytes']['cpu_construction'],resident+16*(1<<30)+16*(m+n)+8*n)
        self.assertGreaterEqual(new['CPU_preparation_host_gib']*(1<<30),new['stage_live_bytes']['cpu_construction']+8*(1<<30))
    def test_final_residual_offsets_include_both_terminal_entries(self):
        p=dict(rows=1_000_000,columns=1_000_000,nonzeros=64_000_000,canonical_tiles=62_500,covered_nnz=48_000_000)
        self.assertEqual(bounded_capacity(p,'fp4x2')['packed_bytes_upper'],531_500_016)


if __name__=='__main__':unittest.main()
