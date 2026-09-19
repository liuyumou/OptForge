"""Export a model document's constraint matrix as a little-endian CSR file for cuda/diagnostics."""
import argparse
import struct
from lp_protocol import read_json


def export(model_path, output):
    d=read_json(model_path);cons=d['constraints'];n=len(d['variables']);m=len(cons)
    ids={v['id']:k for k,v in enumerate(d['variables'])}
    offs=[0];idx=[];val=[]
    for c in cons:
        for t in c['terms']:idx.append(ids[t['variable_id']]);val.append(t['coefficient'])
        offs.append(len(idx))
    with open(output,'wb') as f:
        f.write(struct.pack('<III',m,n,len(idx)));f.write(struct.pack(f'<{m+1}I',*offs));f.write(struct.pack(f'<{len(idx)}I',*idx));f.write(struct.pack(f'<{len(val)}d',*val))
    return m,n,len(idx)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('model');p.add_argument('output');a=p.parse_args()
    print(*export(a.model,a.output))
if __name__=='__main__':main()
