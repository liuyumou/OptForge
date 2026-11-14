"""Independent exact dyadic products of every retained nonzero study vector."""
from fractions import Fraction
import json
import struct
import time
from lp_mixed2_fp4_common import BASE,ROOT,load,put,ref,require

def add(acc,number,denominator_bits):
    value,bits=acc
    if denominator_bits>bits:return (value<<(denominator_bits-bits))+number,denominator_bits
    return value+(number<<(bits-denominator_bits)),bits

def run():
    models=load(BASE/'models/manifest.json')['models'];rows=[];rational=native=0
    for family in ('dense-generic-128','dense-generic-256','dense-generic-512','dense-generic-1024','dense-generic-2048'):
        doc=json.loads((ROOT/models[family]['path']).read_bytes());n=len(doc['variables']);indices={v['id']:i for i,v in enumerate(doc['variables'])}
        seed=load(BASE/'products-v2'/f'b0-{family}-fp4x2-0-1.json');raw=seed['raw'];require(len(raw)==5*n,'product shape')
        require(all(s==1. for s in load(BASE/'device-v6'/(family+'-native.json'))['row_scale']),'oracle original scaling scope')
        xs=[v.as_integer_ratio() for v in raw[2*n:3*n]];ys=[v.as_integer_ratio() for v in raw[n:2*n]]
        ax=[(0,0) for _ in range(n)];aty=ax.copy();pr=[[0.]*8 for _ in range(n)];pc=[[0.]*8 for _ in range(n)]
        for i,row in enumerate(doc['constraints']):
            if i%16==0:time.sleep(.001)
            for term in row['terms']:
                j=indices[term['variable_id']];a=float(term['coefficient']);num,den=a.as_integer_ratio();x,xd=xs[j];y,yd=ys[i]
                ax[i]=add(ax[i],num*x,den.bit_length()+xd.bit_length()-2)
                aty[j]=add(aty[j],num*y,den.bit_length()+yd.bit_length()-2)
                pr[i][j%8]+=a*raw[2*n+j];pc[j][i%8]+=a*raw[n+i]
        truth=[[Fraction(v,1<<e) for v,e in acc] for acc in (ax,aty)]
        exact_native=[[sum(parts) for parts in partial] for partial in (pr,pc)]
        for version in ('products-v1','products-v2'):
            for block in range(3):
                for lane in ('native','fp4x2','fp4x4'):
                    for tr in (0,1):
                        path=BASE/version/f'b{block}-{family}-{lane}-{tr}-1.json';r=load(path);require(r['raw']==raw,'fixed operands differ');result=r['result'];require(len(result['product'])==n,'output coverage')
                        if lane=='native':
                            require([struct.pack('!d',v) for v in result['product']]==[struct.pack('!d',v) for v in exact_native[tr]],'native product tree differs');native+=n
                        else:
                            for v,b,q in zip(result['product'],result['bound'],truth[tr]):require(abs(Fraction(v)-q)<=Fraction(b),'original exact product escapes guard')
                            rational+=n
                        rows.append(dict(record=ref(path),outputs=n,oracle='original-native-tree' if lane=='native' else 'exact-dyadic-original-product'))
        print(dict(family=family,rational_outputs=rational,native_outputs=native),flush=True)
    put(BASE/'product-oracle-v2.json',dict(status='passed',rational_outputs=rational,native_outputs=native,rows=rows))
if __name__=='__main__':run()
