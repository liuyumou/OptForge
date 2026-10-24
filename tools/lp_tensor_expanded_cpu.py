"""ADR-0046 integer CPU prototype; expanded state is private to one window.

This module is not a GPU executor or an admitted solver. It specifies the new
arithmetic/window boundary using the retained integer candidate primitives.
Independent validation uses lp_expansion_oracle, never these rounding helpers.
"""
from dataclasses import dataclass, replace
import struct
import lp_expansion_candidate as arithmetic

E64 = arithmetic.EXPANSION64
F64 = arithmetic.BINARY64
Value = arithmetic.Rounded


class Refusal(ValueError):
    pass


def require(ok, message):
    if not ok:
        raise Refusal(message)


def finite(v):
    require(not v.invalid and not v.infinity_sign, "expanded_arithmetic_range")
    return v.plain()


def integer(n, exponent=0):
    return finite(arithmetic.round_rational(n, 1, exponent, E64))


def encode(bits):
    require(type(bits) is int and 0 <= bits < 1 << 64, "binary64_bits")
    try:
        return finite(arithmetic.round_binary64_bits(bits, E64))
    except arithmetic.ArithmeticRefusal as error:
        raise Refusal(str(error)) from error


def bits(x):
    return int.from_bytes(struct.pack('>d', x), 'big')


def difference(a, b):
    coefficient, exponent = arithmetic.exact_sum([a, arithmetic.negate(b)])
    return Value(coefficient=abs(coefficient), exponent=exponent)


def decode(v):
    rounded = arithmetic.normalize(v, F64)
    require(not rounded.infinity_sign and not rounded.invalid, "boundary_overflow")
    require(not v.coefficient or rounded.coefficient, "boundary_nonzero_to_zero")
    return arithmetic.rounded_to_binary64_bits(rounded), difference(v, rounded)


def add(a, b):
    return finite(arithmetic.add(a, b, E64))


def sub(a, b):
    return finite(arithmetic.add(a, b, E64, subtract=True))


def mul(a, b):
    r = arithmetic.multiply(a, b, E64)
    require(not a.coefficient or not b.coefficient or r.coefficient, "expanded_product_underflow")
    return finite(r)


def soa(v):
    """Four 32-bit words: exact integer-valued FP32 chunks and exponent/sign."""
    d = arithmetic.expansion_chunks(v)
    words = [struct.unpack('>I', struct.pack('>f', float(x)))[0] for x in d['chunks']]
    words.append((d['exponent'] & 0xffff) | d['sign'] << 31)
    return tuple(words)


def from_soa(words):
    require(len(words) == 4 and all(type(w) is int and 0 <= w < 1 << 32 for w in words), "soa_words")
    require(words[3] & 0x7fff0000 == 0, "soa_reserved_bits")
    exponent = words[3] & 0xffff
    if exponent & 0x8000:
        exponent -= 1 << 16
    chunks=[]
    for word, width in zip(words[:3], [24,24,16]):
        v = struct.unpack('>f', word.to_bytes(4,'big'))[0]
        require(0 <= v < 1 << width and v.is_integer() and not word >> 31, "soa_chunk")
        chunks.append(int(v))
    try:
        return arithmetic.decode_expansion_chunks(dict(sign=words[3] >> 31, exponent=exponent, chunks=chunks))
    except arithmetic.ArithmeticRefusal as error:
        raise Refusal(str(error)) from error


@dataclass(frozen=True)
class Packed:
    magnitude: int
    sign: int
    exponent: int
    residual: Value


def pack(v, block_exponent, width=64):
    require(type(block_exponent) is int and width in [56,64], "packing_arguments")
    base = block_exponent - width
    shift = v.exponent - base
    magnitude = abs(v.coefficient)
    q = magnitude << shift if shift >= 0 else magnitude >> -shift
    require(q < 1 << width, "packing_range")
    sign = int(v.coefficient < 0) if v.coefficient else v.zero_sign
    main = Value(coefficient=(-q if sign else q), exponent=base)
    coefficient, exponent = arithmetic.exact_sum([v,arithmetic.negate(main)])
    residual = finite(arithmetic.normalize(Value(coefficient=coefficient,exponent=exponent), E64))
    require(arithmetic.exact_sum([main,residual,v.__class__(coefficient=-v.coefficient,exponent=v.exponent)])[0] == 0,
            "inexact_vector_split")
    return Packed(q,sign,base,residual)


def component_digits(magnitude, sign, width, count):
    require(type(magnitude) is int and 0 <= magnitude < 1 << 64 and sign in (0,1), "component_value")
    return tuple((-1 if sign else 1) * (magnitude >> (width * k) & ((1 << width)-1))
                 for k in range(count))


def main_dot(matrix, vector, matrix_base, vector_base, family):
    require(len(matrix) == len(vector) == 32, "tile_dimension")
    require(family in ['int8','fp16','bf16','simt'], "product_family")
    width, ac, xc = (4,14,16) if family == 'bf16' else (7,8,10)
    exact = 0
    for a, x in zip(matrix,vector):
        require(type(a) is int and abs(a) < 1 << 56, "matrix_significand")
        require(type(x.magnitude) is int and x.magnitude < 1 << 64 and x.sign in (0,1), "vector_significand")
        ad = component_digits(abs(a),int(a < 0),width,ac)
        xd = component_digits(x.magnitude,x.sign,width,xc)
        for i, av in enumerate(ad):
            for k, xv in enumerate(xd):
                exact += (av*xv) << (width*(i+k))
    require(abs(exact) < 1 << 125, "main_dot_accumulator_range")
    value = finite(arithmetic.round_rational(exact,1,matrix_base+vector_base,E64))
    counts = dict(component_products=1024*(224 if family=='bf16' else 1 if family=='simt' else 80),
                  mma_instructions={'int8':32,'fp16':64,'bf16':112,'simt':0}[family])
    counts['padded_products'] = counts['mma_instructions'] * (4096 if family=='int8' else 2048)
    return value, difference(Value(coefficient=exact,exponent=matrix_base+vector_base),value), counts


def project(v, lower, upper):
    try:
        return arithmetic.project(v,lower,upper)
    except arithmetic.ArithmeticRefusal as error:
        raise Refusal(str(error)) from error


def dual_project(raw, step, lower, upper):
    require(step.coefficient > 0, "positive_dual_step")
    lo = mul(step,lower) if lower is not None else None
    hi = mul(step,upper) if upper is not None else None
    return sub(raw,project(raw,lo,hi))


def dense_step(matrix, objective, primal_bounds, dual_bounds, x, y, anchors,
               primal_step, dual_step, toward, back):
    """Small reference updates. Dense component/native implementations bind here later."""
    require(len(matrix)==len(y) and len(objective)==len(x), "model_dimension")
    aty=[finite(arithmetic.dot([row[j] for row in matrix],y,E64)) for j in range(len(x))]
    nxt=[project(sub(v,mul(primal_step,sub(c,a))),*bound)
         for v,c,a,bound in zip(x,objective,aty,primal_bounds)]
    bar=[sub(mul(integer(2),n),v) for n,v in zip(nxt,x)]
    new_x=[add(mul(toward,n),mul(back,a)) for n,a in zip(nxt,anchors[0])]
    ax=[finite(arithmetic.dot(row,bar,E64)) for row in matrix]
    projected=[dual_project(sub(v,mul(dual_step,a)),dual_step,*bound)
               for v,a,bound in zip(y,ax,dual_bounds)]
    new_y=[add(mul(toward,n),mul(back,a)) for n,a in zip(projected,anchors[1])]
    return tuple(new_x),tuple(new_y)


@dataclass(frozen=True)
class State:
    primal: tuple
    dual: tuple
    anchor_primal: tuple
    anchor_dual: tuple
    iterations: int=0
    since_restart: int=0
    checked_iteration: int=0
    restarts: int=0
    weight: int=0x3ff0000000000000
    integral: int=0
    previous_error: int | None=None
    anchor_error: int=0
    last_check_error: int=0


@dataclass(frozen=True)
class Checkpoint:
    owner: object
    state: State
    generation: int


class WindowSession:
    """Transactional CPU specification. Callbacks are source-bound at admission."""
    def __init__(self, state, physical_limit=50000):
        require(len(state.primal)==len(state.anchor_primal) and len(state.dual)==len(state.anchor_dual), "state_dimension")
        for v in (*state.primal,*state.dual,*state.anchor_primal,*state.anchor_dual):
            encode(v)
        for v in [state.weight,state.integral,state.anchor_error,state.last_check_error]:
            encode(v)
        if state.previous_error is not None:
            encode(state.previous_error)
        self.state=state
        self.owner=object()
        self.generation=0
        self.native=False
        self.physical=0
        self.physical_limit=physical_limit
        self.trace=[]
        self.working=None

    def checkpoint(self):
        return Checkpoint(self.owner,self.state,self.generation)

    def restore(self, checkpoint, expected_generation):
        require(checkpoint.owner is self.owner,"checkpoint_session")
        require(expected_generation==self.generation,"stale_generation")
        self.state=checkpoint.state
        self.generation+=1
        self.working=None

    def _vectors(self, x, y):
        require(len(x)==len(self.state.primal) and len(y)==len(self.state.dual),"endpoint_dimension")
        outx=tuple(decode(v) for v in x)
        outy=tuple(decode(v) for v in y)
        return tuple(v[0] for v in outx),tuple(v[0] for v in outy),tuple(v[1] for v in (*outx,*outy))

    def window(self, length, step, reference, audit, native_step=None, cancelled=lambda:False):
        require(type(length) is int and 1 <= length <= 32,"window_length")
        require(not (self.state.iterations and self.state.iterations%200==0 and
                     self.state.checked_iteration<self.state.iterations),"controller_check_pending")
        length=min(length,200-self.state.iterations%200,self.physical_limit-self.physical-1)
        require(length>0,"physical_allowance")
        cp=self.checkpoint()
        while True:
            require(self.physical+length+1<=self.physical_limit,"physical_allowance")
            if cancelled():
                return dict(status='interrupted',started=0)
            x=tuple(encode(v) for v in cp.state.primal)
            y=tuple(encode(v) for v in cp.state.dual)
            pre=None;started=0;conversions=[]
            try:
                for k in range(length):
                    if k+1==length:
                        px,py,error=self._vectors(x,y)
                        pre=replace(cp.state,primal=px,dual=py,iterations=cp.state.iterations+k,
                                    since_restart=cp.state.since_restart+k)
                        x,y=tuple(map(encode,px)),tuple(map(encode,py))
                        conversions.append(('penultimate',error))
                    self.physical+=1;started+=1
                    if self.native:
                        require(native_step is not None,"native_step_missing")
                        bx,by,_=self._vectors(x,y)
                        nx,ny=native_step(bx,by,k,cp.state)
                        x,y=tuple(map(encode,nx)),tuple(map(encode,ny))
                    else:
                        x,y=step(x,y,k,cp.state)
                    self.working=(x,y)
                px,py,error=self._vectors(x,y)
                conversions.append(('endpoint',error))
                if cancelled():
                    self.restore(cp,self.generation)
                    return dict(status='interrupted',started=started)
                self.physical+=1
                rx,ry=reference(pre)
                require(len(rx)==len(px) and len(ry)==len(py),'reference_dimension')
                for v in (*rx,*ry):encode(v)
                require(audit(px,py,rx,ry,pre),'audit_error')
                if cancelled():
                    self.restore(cp,self.generation)
                    return dict(status='interrupted',started=started)
                self.state=replace(cp.state,primal=tuple(rx),dual=tuple(ry),
                                   iterations=cp.state.iterations+length,since_restart=cp.state.since_restart+length)
                self.working=None;self.generation+=1
                row=dict(status='accepted',started=started,native=self.native,pre=pre,
                         candidate=(px,py),adopted=(tuple(rx),tuple(ry)),conversions=conversions)
                self.trace.append(row)
                return row
            except Refusal as failure:
                self.trace.append(dict(status='rejected',reason=str(failure),started=started,native=self.native))
                self.restore(cp,self.generation)
                if self.native or native_step is None:
                    return dict(status='numerical_failure',reason=str(failure),started=started)
                self.native=True
            except BaseException:
                self.restore(cp,self.generation)
                raise
