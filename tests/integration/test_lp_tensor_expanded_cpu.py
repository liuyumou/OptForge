"""New prototype cases; does not invoke historical suites or GPU execution."""
import sys
import unittest
from dataclasses import replace
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))
import lp_tensor_expanded_cpu as c


def state(**kwargs):
    return c.State((c.bits(1.),),(c.bits(0.),),(c.bits(1.),),(c.bits(0.),),**kwargs)


def step(x,y,k,s):
    return (c.add(x[0],c.integer(1,-54)),),y


def reference(pre):
    return pre.primal,pre.dual


def accept(*args):
    return True


class ExpandedPrototypeTests(unittest.TestCase):
    def test_retains_sub_fp64_updates(self):
        s=c.WindowSession(state());r=s.window(8,step,reference,accept)
        self.assertEqual(r['pre'].primal,(c.bits(1.+2**-51),))
        self.assertEqual(s.state.primal,r['pre'].primal)
        self.assertEqual([x[0] for x in r['conversions']],['penultimate','endpoint'])
        self.assertIsNone(s.working)

    def test_lengths(self):
        for n in [1,2,8,31,32]:
            s=c.WindowSession(state());r=s.window(n,step,reference,accept)
            self.assertEqual(r['pre'].iterations,n-1)
            self.assertEqual(s.state.iterations,n)
            self.assertEqual(s.physical,n+1)

    def test_len_one_identity(self):
        s=c.WindowSession(state());r=s.window(1,step,reference,accept)
        self.assertEqual(r['pre'],state())

    def test_invalid_lengths(self):
        for length in [0,33,True,-1]:
            with self.assertRaisesRegex(c.Refusal,'window_length'):
                c.WindowSession(state()).window(length,step,reference,accept)

    def test_control_boundary(self):
        s=c.WindowSession(state(iterations=192,since_restart=192))
        s.window(32,step,reference,accept)
        self.assertEqual(s.state.iterations,200)
        with self.assertRaisesRegex(c.Refusal,'controller_check_pending'):
            s.window(1,step,reference,accept)

    def test_audit_input_is_candidate_input(self):
        observed=[]
        def candidate(x,y,k,s):
            if k==7:observed.append((tuple(c.decode(v)[0] for v in x),tuple(c.decode(v)[0] for v in y)))
            return step(x,y,k,s)
        def ref(pre):
            self.assertEqual(observed[-1],(pre.primal,pre.dual))
            return pre.primal,pre.dual
        c.WindowSession(state()).window(8,candidate,ref,accept)

    def test_conversion_failure_restores_both(self):
        def tiny(x,y,k,s):return x,(c.integer(1,-1085),)
        s=c.WindowSession(state());r=s.window(2,tiny,reference,accept)
        self.assertEqual(r['status'],'numerical_failure')
        self.assertEqual(s.state,state());self.assertEqual(s.physical,1)

    def test_final_conversion_failure(self):
        def tiny(x,y,k,s):return x,(c.integer(1,-1085),)
        s=c.WindowSession(state());r=s.window(1,tiny,reference,accept)
        self.assertEqual(r['status'],'numerical_failure')
        self.assertEqual(s.state,state());self.assertEqual(s.physical,1)

    def test_native_replay_charges_failed_window(self):
        def fail(x,y,k,s):
            if k==2:raise c.Refusal('arithmetic_range')
            return x,y
        def native(x,y,k,s):return x,y
        s=c.WindowSession(state());r=s.window(8,fail,reference,accept,native)
        self.assertTrue(r['native']);self.assertEqual(s.physical,3+8+1)
        self.assertEqual(s.state.iterations,8)
        s.window(1,fail,reference,accept,native)
        self.assertTrue(s.native)

    def test_cancel_before_and_after_reference(self):
        for limit in [1,2]:
            calls=[]
            def cancel():calls.append(1);return len(calls)>limit
            s=c.WindowSession(state());r=s.window(8,step,reference,accept,cancelled=cancel)
            self.assertEqual(r['status'],'interrupted');self.assertEqual(s.state,state())
            self.assertEqual(s.physical,8+(limit==2))

    def test_checkpoint_ownership_and_generation(self):
        a=c.WindowSession(state());b=c.WindowSession(state())
        with self.assertRaisesRegex(c.Refusal,'checkpoint_session'):b.restore(a.checkpoint(),0)
        cp=a.checkpoint();a.window(1,step,reference,accept)
        with self.assertRaisesRegex(c.Refusal,'stale_generation'):a.restore(cp,0)

    def test_deterministic_replay(self):
        a=c.WindowSession(state());b=c.WindowSession(state())
        for _ in range(3):
            self.assertEqual(a.window(32,step,reference,accept),b.window(32,step,reference,accept))
        self.assertEqual(a.state,b.state)

    def test_soa_and_zero(self):
        for v in [c.integer(0),c.Value(zero_sign=1),c.integer(1,-1085),c.integer(-((1<<64)-1),-63)]:
            self.assertEqual(c.from_soa(c.soa(v)),v)
        with self.assertRaisesRegex(c.Refusal,'soa_reserved_bits'):
            c.from_soa((0,0,0,1<<20))

    def test_exact_main_and_residual(self):
        v=c.integer((1<<64)-1,-63);p=c.pack(v,4)
        main=c.Value(coefficient=p.magnitude,exponent=p.exponent)
        self.assertEqual(c.arithmetic.exact_sum([main,p.residual,c.arithmetic.negate(v)])[0],0)
        self.assertNotEqual(p.residual.coefficient,0)

    def test_wide_main_counts(self):
        x=c.Packed((1<<64)-1,0,-64,c.integer(0));a=(1<<56)-1
        for family,pairs,mma in [('int8',80,32),('fp16',80,64),('bf16',224,112),('simt',1,0)]:
            _,_,counts=c.main_dot([a]*32,[x]*32,-56,-64,family)
            self.assertEqual(counts['component_products'],1024*pairs)
            self.assertEqual(counts['mma_instructions'],mma)

    def test_dual_projection_bounds(self):
        self.assertEqual(c.dual_project(c.integer(3),c.integer(2),c.integer(-1),c.integer(1)),c.integer(1))
        self.assertEqual(c.dual_project(c.integer(-3),c.integer(2),None,c.integer(1)),c.integer(0))


if __name__=='__main__':unittest.main()
