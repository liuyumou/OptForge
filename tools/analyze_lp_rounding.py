"""Reproduce GPUP-5B rounding observations using exact rational CPU arithmetic."""
import argparse
from fractions import Fraction as F
import math
from pathlib import Path
import random
import struct
from lp_protocol import ROOT, file_hash, read_json, write_json


def f32(x):
    return struct.unpack('<f', struct.pack('<f', x))[0]


def components(x):
    h = f32(x)
    mid = f32(x-h)
    return h, mid, f32((x-h)-mid)


def power_exponent(x):
    """Nearest log-distance power: compare squared integer significand with 2."""
    if not math.isfinite(x) or x <= 0:
        raise ValueError('positive finite scale required')
    m, e = math.frexp(x)
    n, d = m.as_integer_ratio()
    return e if 2*n*n > d*d else e-1


def analyze():
    source = ROOT/'artifacts/gpup5-diagnosis-v1'
    manifest = read_json(ROOT/'benchmarks/manifests/lp-development-v1.json')
    count = original_exact = power_exact = 0
    exact = [0]*3
    errors = [F(0)]*3
    inputs = []
    witness_rows = []
    for instance in manifest['instances']:
        path = source/(instance['id']+'.operator.json')
        op = read_json(path)
        if op['model_sha256'] != instance['model']['sha256']:
            raise ValueError('operator/model identity differs')
        endpoint_path = ROOT/'artifacts/gpup5-fp32-v1'/f'gpup5-fp32-v1-timing-{instance["id"]}-0-storage-fp32.endpoint.json'
        endpoint = read_json(endpoint_path)
        model = read_json(ROOT/instance['model']['path'])
        primal = {a['variable_id']: F(a['value']) for a in endpoint['record']['candidate']['values']}
        x = [primal[v['id']] for v in sorted(model['variables'], key=lambda v:v['id'])]
        shifts = [[F(0)]*3 for _ in op['row_scale']]
        for r, c, a, scaled, _ in op['entries']:
            count += 1
            original_exact += f32(a) == a
            parts = components(scaled)
            for k in range(3):
                reconstructed = sum(map(F, parts[:k+1]))
                delta = reconstructed-F(scaled)
                exact[k] += delta == 0
                errors[k] = max(errors[k], abs(delta))
                shifts[r][k] += delta*x[c]/(F(op['row_scale'][r])*F(op['column_scale'][c]))
            exponent = power_exponent(op['row_scale'][r])+power_exponent(op['column_scale'][c])
            transformed = math.ldexp(a, exponent)
            assert F(transformed) == F(a)*F(2)**exponent
            power_exact += f32(transformed) == transformed
        row_ids = [r['id'] for r in sorted(model['constraints'], key=lambda r:r['id'])]
        witness_rows.append(dict(instance=instance['id'], endpoint_sha256=file_hash(endpoint_path),
                                 rows=[dict(row_id=i, shifts=[float(v) for v in s], exact_shifts=[str(v) for v in s]) for i,s in zip(row_ids,shifts)]))
        inputs.append(dict(path=str(path.relative_to(ROOT)),sha256=file_hash(path),model_sha256=op['model_sha256']))
    rng = random.Random(17002)
    values = [0.0,-0.0,math.ulp(0.0),-math.ulp(0.0),float.fromhex('0x1.fffffffffffffp+1023'),float.fromhex('0x1p-1022')]
    while len(values)<10006:
        x=struct.unpack('<d',rng.getrandbits(64).to_bytes(8,'little'))[0]
        if math.isfinite(x): values.append(x)
    splits=[]
    for x in values:
        m,e=math.frexp(x); c=components(m)
        assert sum(map(F,c))*F(2)**e == F(x)
        splits.append(c)
    pairs=0
    for a,b in zip(splits[::2],splits[1::2]):
        for u in a:
            for v in b:
                exact_product=u*v
                p=f32(exact_product); q=f32(exact_product-p)
                assert F(p)+F(q)==F(u)*F(v)
                pairs+=1
    scaled_third = 1.0/3.0
    toy_x = scaled_third/f32(scaled_third)
    return dict(schema_version=1,kind='exact_rational_cpu_diagnostic_not_certificate',seed=17002,
                tool_sha256=file_hash(Path(__file__)),inputs=inputs,coefficients=count,
                original_exact_fp32=original_exact,component_exact=exact,
                component_max_error=[float(e) for e in errors],power2_exact_fp32=power_exact,
                finite_samples=len(values),normalized_three_exact=len(splits),partial_product_pairs=pairs,
                toy=dict(scaled_coefficient=scaled_third,rounded_coefficient=f32(scaled_third),represented_solution=toy_x,original_error=1-toy_x),
                witness_rows=witness_rows)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,default=ROOT/'artifacts/gpup5b-rounding-v1/analysis.json')
    a=p.parse_args()
    result=analyze()
    if a.output.exists():
        if read_json(a.output)!=result: raise ValueError('refusing to overwrite different rounding evidence')
    else: write_json(a.output,result)
    print({k:v for k,v in result.items() if k not in ['inputs','witness_rows']})
if __name__=='__main__': main()
