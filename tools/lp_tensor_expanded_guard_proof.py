"""New exact-rational checks of the update metadata enclosures, not scalar reruns."""
import math
import random
from fractions import Fraction as F
import lp_expansion_oracle as oracle

ETA=math.ulp(0.)
FORMAT=(64,-1022,1023)
def add(a,b):return b if a==0 else a if b==0 else math.nextafter(a+b,math.inf)
def mul(a,b):return 0. if a==0 or b==0 else math.nextafter(a*b,math.inf)
def div(a,b):return 0. if a==0 else math.nextafter(a/b,math.inf)
def primitive(v):return add(mul(2.**-63,v),ETA)
def rounded(v):
    d=oracle.round_fraction(v,FORMAT)
    if d['infinity_sign']:raise OverflowError()
    return oracle.exact_value(d)
def absolute(v):
    if not v:return 0.
    d=oracle.round_fraction(abs(v),(53,-1022,1023))
    if d['infinity_sign']:raise OverflowError()
    out=math.nextafter(float(oracle.exact_value(d)),math.inf)
    if not math.isfinite(out):raise OverflowError()
    return out
def clamp(v,lo,hi):return min(max(v,lo),hi)
def enclosed(error,bound,where):
    if not math.isfinite(bound):raise OverflowError()
    assert abs(error)<=F(bound),(where,str(error),bound)

def run():
    rng=random.Random(17028);passed=0;refused=0;inverses=0
    for k in range(2400):
        # Includes exponent extremes, nearly active bounds, cancellation and
        # tiny accumulated changes. Every operand is canonicalized independently.
        e=rng.choice([-1085,-1074,-900,-63,-20,0,20,400,900])
        def val():return rounded(F(rng.randrange(-(1<<64),1<<64))*oracle.power2(e))
        x,a,anchor=val(),val(),val()
        step=math.ldexp(1.+rng.random(),rng.choice([-20,-1,0,10]))
        toward=(k%200+1)/(k%200+2);back=1./(k%200+2)
        cost=float(rng.randrange(-100,101))/64
        # Independent true-product perturbation, enclosed by product_error.
        product_error=math.ldexp(1.,rng.choice([-1074,-900,-80,-40,0]))
        delta=F(product_error)*rng.choice([-1,0,1])
        lower,upper=F(-3),F(5)
        try:
            diff=rounded(F(cost)-a);change=rounded(F(step)*diff)
            raw=rounded(x-change);projected=clamp(raw,lower,upper)
            bar=rounded(rounded(2*projected)-x)
            next_x=rounded(rounded(F(toward)*projected)+rounded(F(back)*anchor))
            ideal=clamp(x-F(step)*(F(cost)-(a+delta)),lower,upper)
            xv,av,anchorv=absolute(x),absolute(a),absolute(anchor)
            difference=add(abs(cost),av)
            de=add(product_error,primitive(difference))
            rd=add(difference,primitive(difference))
            cm=mul(step,rd)
            ce=add(mul(step,de),primitive(cm))
            rc=add(cm,primitive(cm))
            re=add(ce,primitive(add(xv,rc)))
            pm=add(mul(float.fromhex('0x1.0000000000001p-1'),add(absolute(bar),xv)),ETA)
            enclosed(projected,pm,'primal inverse magnitude')
            be=add(mul(2.,re),mul(2.,primitive(add(mul(2.,pm),xv))))
            xe=add(mul(toward,re),mul(3.,primitive(add(mul(toward,pm),mul(back,anchorv)))))
            enclosed(bar-(2*ideal-x),be,'bar error')
            enclosed(next_x-(F(toward)*ideal+F(back)*anchor),xe,'primal error')

            # Dual local target uses a separately perturbed product and the
            # exact positive-step projection identity (finite bounds here).
            y=x;ax=a
            change=rounded(F(step)*ax);raw=rounded(y-change)
            lo=rounded(F(step)*lower);hi=rounded(F(step)*upper)
            clamp_value=clamp(raw,lo,hi)
            projected=rounded(raw-clamp_value)
            next_y=rounded(rounded(F(toward)*projected)+rounded(F(back)*anchor))
            ideal_raw=y-F(step)*(ax+delta)
            ideal=ideal_raw-clamp(ideal_raw,F(step)*lower,F(step)*upper)
            cm=mul(step,av);rc=add(cm,primitive(cm));rm=add(xv,rc)
            re=add(mul(step,product_error),mul(2.,primitive(rm)))
            rr=add(rm,primitive(rm))
            numerator=add(add(absolute(next_y),mul(back,anchorv)),8*ETA)
            pm=mul(div(float.fromhex('0x1.0000000000008p0'),toward),numerator)
            enclosed(projected,pm,'dual inverse magnitude')
            clm=add(add(rr,mul(float.fromhex('0x1.0000000000008p0'),pm)),ETA)
            enclosed(clamp_value,clm,'clamp inverse magnitude')
            bound_error=max(primitive(mul(step,abs(float(lower)))),primitive(mul(step,abs(float(upper)))))
            pe=add(add(mul(2.,re),bound_error),primitive(add(rr,clm)))
            ye=add(mul(toward,pe),mul(3.,primitive(add(mul(toward,pm),mul(back,anchorv)))))
            enclosed(next_y-(F(toward)*ideal+F(back)*anchor),ye,'dual error')
            passed+=1;inverses+=3
        except OverflowError:refused+=1
    assert passed>=1800
    return dict(status='passed',seed=17028,cases=2400,finite_enclosures=passed,
        range_refusals=refused,inverse_magnitude_enclosures=inverses,
        authority='Exact Fraction arithmetic plus independent p64 nearest-even oracle.',
        old_cases_rerun=False,gpu_seconds=0)
