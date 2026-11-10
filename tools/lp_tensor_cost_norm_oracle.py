"""Independent Fraction Gram witnesses and streaming eight-model layout check."""
import argparse
import sys
import filecmp
import json
import math
import random
import struct
import subprocess
import tempfile
from fractions import Fraction as F
from pathlib import Path
from lp_protocol import ROOT,read_json,write_json,file_hash,checked_reference
from lp_tensor_cost_common import BASE,protocol,instances

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--cohort',default='norm-proof-v1');args=parser.parse_args()
    out=BASE/args.cohort;out.mkdir(parents=True,exist_ok=False)
    prefix=[sys.executable,str(ROOT/'tools/lp_tensor_cost_exec.py'),'--memory-bytes',str(2<<30),'--']
    rng=random.Random(17044)
    blocks=[[0.]*1024, [float.fromhex('0x0.0000000000001p-1022')]*1024]
    blocks.append([1. if (i&j).bit_count()%2==0 else -1. for i in range(32) for j in range(32)])
    for _ in range(21):
        blocks.append([math.ldexp(float(rng.randrange(-127,128)),rng.choice([-16,-4,0,4,16])) for _ in range(1024)])
    blocks.extend([[1e308]*1024,[math.inf]*1024])
    encoded=[[struct.pack('>d',x).hex() for x in block] for block in blocks]
    raw=''.join(json.dumps(row)+'\n' for row in encoded)
    (out/'inputs.jsonl').write_text(raw)
    probe=ROOT/'target/release/examples/tensor_cost_norm_probe'
    result=subprocess.run(prefix+[str(probe)],input=raw,capture_output=True,text=True,timeout=120,check=True)
    (out/'outputs.jsonl').write_text(result.stdout)
    rows=result.stdout.splitlines();assert len(rows)==len(blocks)
    exact_terms=0
    for block,line in zip(blocks,rows):
        bits=json.loads(line)['norm_bits']
        if block[0] in [1e308,math.inf]:
            assert bits is None;continue
        assert bits is not None
        norm=struct.unpack('>d',bytes.fromhex(bits))[0]
        matrix=[list(map(F,block[i*32:(i+1)*32])) for i in range(32)]
        # Exact real Gram entries, with no production interval/reduction helpers.
        upper=max(sum(abs(sum(matrix[k][i]*matrix[k][j] for k in range(32)))
                      for j in range(32)) for i in range(32))
        assert math.isfinite(norm) and F(norm)**2>=upper,(norm,upper)
        exact_terms+=32**3
    value=protocol();models=instances(value)
    names=read_json(ROOT/'benchmarks/configs/lp-exec-v1.json')['timing_instances']
    compact=ROOT/'target/release/examples/tensor_cost_compact_probe';comparisons=[]
    for name in names:
        model=checked_reference(ROOT,models[name]['model'])
        with tempfile.TemporaryDirectory(prefix='gpup8-compact-') as tmp:
            files=[Path(tmp)/'old.snapshot',Path(tmp)/'new.snapshot'];metadata=[]
            for mode,path in zip(['old','new'],files):
                r=subprocess.run(prefix+[str(compact),mode,str(model),str(path)],capture_output=True,text=True,timeout=120,check=True)
                (out/(name+'-'+mode+'.json')).write_text(r.stdout)
                metadata.append(json.loads(r.stdout))
            old,new=metadata
            assert old['status']==new['status'],(name,old,new)
            if old['status']=='refused':assert old['error']==new['error']
            else:
                assert filecmp.cmp(*files,shallow=False),name
                assert struct.pack('>d',old['legacy_bound'])==struct.pack('>d',new['legacy_bound'])
            comparisons.append(dict(model=name,status='matched_refusal' if old['status']=='refused' else 'bitwise_match',metadata=new))
            print(name,comparisons[-1]['status'],flush=True)
    receipt=dict(identity='gpup-tensor-cost-norm-proof-v1',status='passed',gpu_seconds=0,
                 gram_cases=len(blocks),exact_fraction_terms=exact_terms,compact_comparisons=comparisons,
                 probe_sha256=file_hash(probe),compact_probe_sha256=file_hash(compact),oracle_sha256=file_hash(Path(__file__)),
                 inputs_sha256=file_hash(out/'inputs.jsonl'),outputs_sha256=file_hash(out/'outputs.jsonl'))
    write_json(ROOT/'docs/benchmarks/data/tensor-cost'/('norm-proof.json' if args.cohort=='norm-proof-v1' else args.cohort+'.json'),receipt)
    print('Fraction Gram bounds and all eight streamed canonical comparisons pass',flush=True)

if __name__=='__main__':main()
