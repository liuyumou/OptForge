"""New independent ADR-0046 CPU proof corpus, run once under its reservation."""
import hashlib
import json
from fractions import Fraction as F
from pathlib import Path
import random
import subprocess
import sys

import lp_expansion_oracle as independent
import lp_tensor_expanded_cpu as candidate
import lp_tensor_expanded_authority as authority

ROOT=authority.ROOT
BASE=authority.BASE
FORMAT=(64,-1022,1023)


def value(document):
    return independent.exact_value(document)


def operand(n,e=0,sign=0):
    d=independent.round_fraction(F(n)*independent.power2(e),FORMAT,zero_sign=sign)
    assert not d['infinity_sign']
    return d


def as_candidate(d):
    return candidate.Value(coefficient=d['coefficient'],exponent=d['exponent'],zero_sign=d['zero_sign'])


def scalar_cases():
    rng=random.Random(17022)
    cases=[]
    exponents=[-1085,-1074,-1022,-126,-64,-63,-1,0,500,959,960]
    for _ in range(7200):
        docs=[]
        for k in range(3):
            e=rng.choice(exponents) if _<2400 else rng.randrange(-1085,961)
            m=rng.getrandbits(64) if e==-1085 else rng.getrandbits(63)|(1<<63)
            docs.append(dict(coefficient=m*(-1 if rng.getrandbits(1) else 1),exponent=e,zero_sign=0))
        if _%3==0:
            # A substantial corpus enters the new exact-span fast construction.
            docs[0]['exponent']=-63;docs[1]['exponent']=-63;docs[2]['exponent']=-63
        cases.append(docs)
    for e in [-1085,-1074,-1022,-64,-63,0,960]:
        for m in [1<<63,(1<<63)+1,(1<<64)-1]:
            for sign in [-1,1]:
                a=operand(sign*m,e)
                for c in [operand(0),operand(0,sign=1),operand(-sign*m,e),operand(1,-1085)]:
                    cases.append([a,operand(1),c])
    for sa in [0,1]:
        for sb in [0,1]:
            for sc in [0,1]:cases.append([operand(0,sign=sa),operand(0,sign=sb),operand(0,sign=sc)])
    return cases


def scalar_proof():
    binary=BASE/'expanded-scalar-host-v1'
    command=['g++','-std=c++17','-O2','-ffp-contract=off','-fno-fast-math',
             '-fsanitize=undefined','-fno-sanitize-recover=all','-Wno-unknown-pragmas',
             str(ROOT/'tools/diagnostics/lp_tensor_expanded_host.cpp'),'-o',str(binary)]
    built=subprocess.run(command,capture_output=True,text=True,timeout=120)
    (BASE/'scalar-build-v1.stdout').write_text(built.stdout)
    (BASE/'scalar-build-v1.stderr').write_text(built.stderr)
    assert built.returncode==0, built.stderr
    cases=scalar_cases()
    data=''.join(' '.join(str(z) for d in case for z in [abs(d['coefficient']),d['exponent'] if d['coefficient'] else 0,
                 int(d['coefficient']<0) if d['coefficient'] else d['zero_sign']])+'\n' for case in cases)
    (BASE/'scalar-input-v1.txt').write_text(data)
    process=subprocess.run([str(binary)],input=data,capture_output=True,text=True,timeout=120)
    (BASE/'scalar-output-v1.txt').write_text(process.stdout)
    (BASE/'scalar-stderr-v1.txt').write_text(process.stderr)
    assert process.returncode==0,process.stderr
    lines=process.stdout.splitlines();assert len(lines)==len(cases)
    fast=0
    for index,(case,line) in enumerate(zip(cases,lines)):
        got=tuple(map(int,line.split()));assert len(got)==5
        expected=independent.primitive_result('fma',case,FORMAT)
        m,e,s,g,f=got;fast+=f
        wanted=(abs(expected['coefficient']),expected['exponent'] if expected['coefficient'] else 0,
                int(expected['coefficient']<0) if expected['coefficient'] else expected['zero_sign'])
        passed= g==2 if expected['infinity_sign'] else g==0 and (m,e,s)==wanted
        if not passed:
            authority.put(BASE/'scalar-counterexample-v1.json',dict(index=index,operands=case,expected=expected,actual=got))
            raise AssertionError('independent scalar mismatch at '+str(index))
    assert fast>2000 and fast<len(cases)
    return dict(cases=len(cases),fast_cases=fast,fallback_cases=len(cases)-fast,binary=authority.ref(binary),
                input=authority.ref(BASE/'scalar-input-v1.txt'),output=authority.ref(BASE/'scalar-output-v1.txt'))


def product_conversion_proof():
    rng=random.Random(17023);products=0;conversions=0;splits=0
    for i in range(1400):
        e=rng.randrange(-1085,961)
        m=rng.getrandbits(64) if e==-1085 else rng.getrandbits(63)|(1<<63)
        d=dict(coefficient=m*(-1 if i%2 else 1),exponent=e,zero_sign=0)
        c=as_candidate(d)
        assert candidate.from_soa(candidate.soa(c))==c
        expected=independent.round_fraction(value(d),(53,-1022,1023))
        if expected['infinity_sign'] or (m and expected['coefficient']==0):
            try:candidate.decode(c)
            except candidate.Refusal:pass
            else:raise AssertionError('unrefused boundary range')
        else:
            bits,bound=candidate.decode(c)
            assert independent.binary64_fraction(bits)==value(expected)
            assert abs(value(d)-independent.binary64_fraction(bits)) <= value(bound.document())
        conversions+=1
        block=e+64+rng.choice([0,1,31,63,127])
        p=candidate.pack(c,block)
        actual=F(-p.magnitude if p.sign else p.magnitude)*independent.power2(p.exponent)+value(p.residual.document())
        assert actual==value(d)
        assert 0<=p.magnitude<1<<64
        splits+=1
    for i in range(180):
        a=[rng.randrange(-(1<<56)+1,1<<56) for _ in range(32)]
        x=[candidate.Packed(rng.getrandbits(64),rng.randrange(2),-64,candidate.integer(0)) for _ in range(32)]
        exact=sum(F(av)*(-v.magnitude if v.sign else v.magnitude) for av,v in zip(a,x))*independent.power2(-120)
        expected=independent.round_fraction(exact,FORMAT)
        for family in ['int8','fp16','bf16','simt']:
            out,bound,counts=candidate.main_dot(a,x,-56,-64,family)
            assert value(out.document())==value(expected)
            assert abs(exact-value(out.document()))<=value(bound.document())
            assert type(counts['mma_instructions']) is int
            products+=1
    return dict(conversions=conversions,exact_splits=splits,component_products=products,
                maximum_main_dot_bound_bits=(32*((1<<56)-1)*((1<<64)-1)).bit_length())


def projection_proof():
    rng=random.Random(17024);count=0
    for i in range(2400):
        raw=operand(rng.randrange(-(1<<64),1<<64),rng.randrange(-100,101))
        step=operand(rng.randrange(1,1<<64),rng.randrange(-100,1))
        lo=operand(-rng.randrange(0,1<<64),-63) if i%7 else None
        hi=operand(rng.randrange(0,1<<64),-63) if i%11 else None
        r,t=value(raw),value(step)
        l=value(lo) if lo else None;h=value(hi) if hi else None
        divided=r/t
        if l is not None:divided=max(divided,l)
        if h is not None:divided=min(divided,h)
        exact=r-t*divided
        rounded_l=independent.round_fraction(t*l,FORMAT) if lo else None
        rounded_h=independent.round_fraction(t*h,FORMAT) if hi else None
        clamp=r
        if rounded_l:clamp=max(clamp,value(rounded_l))
        if rounded_h:clamp=min(clamp,value(rounded_h))
        expected=independent.round_fraction(r-clamp,FORMAT)
        got=candidate.dual_project(as_candidate(raw),as_candidate(step),as_candidate(lo) if lo else None,as_candidate(hi) if hi else None)
        assert value(got.document())==value(expected)
        errors=[F(0)]
        if lo:errors.append(abs(value(rounded_l)-t*l))
        if hi:errors.append(abs(value(rounded_h)-t*h))
        enclosure=max(errors)+abs(value(expected)-(r-clamp))
        assert abs(value(got.document())-exact)<=enclosure
        count+=1
    return dict(cases=count,identity='positive-step-clamp-with-rounded-bound-enclosure-v1')


def main():
    try:
        scalar=scalar_proof()
        products=product_conversion_proof()
        projection=projection_proof()
        report=dict(status='passed',scalar=scalar,products=products,projection=projection,gpu_seconds=0,
                    historical_checks_rerun=False,oracle=authority.ref(ROOT/'tools/lp_expansion_oracle.py'),
                    candidate=authority.ref(ROOT/'tools/lp_tensor_expanded_cpu.py'),
                    fast_source=authority.ref(ROOT/'cuda/lp_pdhg_tensor_expanded/expanded_fast.h'))
        authority.put(authority.DATA/'independent-proof-v1.json',report)
        print(json.dumps(report),flush=True)
    except BaseException as error:
        authority.put(authority.DATA/'independent-proof-refusal-v1.json',dict(status='refused',reason=str(error),
                      exception=type(error).__name__,gpu_seconds=0,proof_source=authority.ref(Path(__file__))))
        raise


if __name__=='__main__':main()
