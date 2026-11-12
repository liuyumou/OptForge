"""CPU-only replay of the retained v1 ISA-packing mismatch, no GPU executor."""
from fractions import Fraction as Q
from pathlib import Path
import json
from lp_fp4_gpu_common import BASE, ROOT, load, put, ref, require
import lp_fp4_gpu_oracle as o

def isa_byte(code):
    if type(code)is not int or not 0<=code<16:raise ValueError('E2M1 nibble required')
    return code<<2

def isa_decode(byte):
    if type(byte)is not int or not 0<=byte<256:raise ValueError('byte required')
    return o.decode((byte>>2)&15,4)

def simulate(input_row,result,corrected=False):
    k=input_row['components'];trans=input_row['mode']=='transpose'
    out=[Q(0)]*32
    for p in range(k):
        a=o.unpack(input_row['matrix_codes'][p*128:(p+1)*128],4,1024)
        for s in range(k):
            offset=(1 if trans else 2)*k*4+s*4
            v=o.unpack(result['codes'][offset:offset+4],4,32)
            exponent=input_row['matrix_exponents'][p]+result['exponents'][(1 if trans else 2)*k+s]
            convert=lambda c:isa_decode(isa_byte(c) if corrected else c)
            for i in range(32):
                out[i]+=sum(convert(a[j*32+i if trans else i*32+j])*convert(v[j]) for j in range(32))*Q(2)**exponent
    return out

def main():
    directory=BASE/'primitive';rows=[]
    for path in sorted(directory.glob('*.attempt.json')):
        row=load(path);r=load(ROOT/row['input']['path']);out=load(ROOT/row['output']['path']);expected=o.product_reference(r)
        error=max(abs(Q(a)-b) for a,b in zip(out['product'],expected));scale=max(Q(1,1<<96),max(map(abs,expected)))
        limit=scale*Q(1,1<<(38 if r['format'] in (4,64) else 19))
        rows.append(dict(row,comparison_passed=error<=limit,max_error=float(error),comparison_limit=float(limit)))
    name='4-2-forward-dense';r=load(directory/(name+'.input.json'));out=load(directory/(name+'.output.json'))
    wrong=simulate(r,out);fixed=simulate(r,out,True);expected=o.product_reference(r)
    require(wrong==list(map(Q,out['product'])),'packing hypothesis does not reproduce device output')
    require(fixed==expected,'corrected CPU fragment simulation differs')
    require(sum(row['comparison_passed'] for row in rows)==30 and len(rows)==31,'retained primitive disposition')
    put(ROOT/'docs/benchmarks/data/fp4-gpu-pilot-diagnosis-v1.json',dict(kind='fp4-gpu-pilot-packing-diagnosis-v1',rows=rows,passed=30,failed=1,unexecuted=29,
        failed_case=name,all_32_device_outputs_reproduced=True,corrected_cpu_mapping_matches_oracle=True,
        v1_error=max(row['max_error'] for row in rows if row['id']==name),
        cause='For kind::f8f6f4, each E2M1 nibble occupies bits 5:2 of its MMA byte. V1 puts it in bits 3:0. Storage packing and arithmetic codebook are distinct from this ISA byte layout.',
        source_url='https://docs.nvidia.com/cuda/archive/13.0.0/parallel-thread-execution/index.html#warp-level-matrix-instructions-mma',
        corrected_candidate=ref(ROOT/'research/lp-fp4-gpu-pilot/cuda/pilot_v2.cu'),device_correction_validated=False,
        note='No v1 result or source modified. CPU diagnosis is not a corrected device admission.'))
    print('CPU ISA model reproduces all 32 failed device outputs exactly; corrected packing matches the independent product oracle.')

if __name__=='__main__':main()
