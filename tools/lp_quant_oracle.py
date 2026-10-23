"""Independent integer/Fraction oracle for the bounded ADR-0040 formats and products."""
import bisect,json,math,struct,subprocess,time
from fractions import Fraction as F
from pathlib import Path
from lp_protocol import ROOT,file_hash,write_json
PROBE=ROOT/'target/release/examples/quant_probe'
def bits(x):return struct.unpack('>Q',struct.pack('>d',x))[0]
def decode(name,code):
    eb,mb,bias,maxcode={'fp16':(5,10,15,0x7bff),'e4m3':(4,3,7,0x7e),'e5m2':(5,2,15,0x7b)}[name]
    if code>=1<<(1+eb+mb):return None
    sign=-1 if code>>(eb+mb) else 1;mag=code&((1<<(eb+mb))-1)
    if mag>maxcode:return None
    exponent,mant=divmod(mag,1<<mb)
    e=(exponent-bias-mb) if exponent else (1-bias-mb)
    return sign*F((1<<mb)+mant if exponent else mant)*(F(2)**e)
def codec():
    queries=[];wants=[]
    for name,limit in [('fp16',65536),('e4m3',256),('e5m2',256)]:
        maxcode={'fp16':0x7bff,'e4m3':0x7e,'e5m2':0x7b}[name]
        values=[decode(name,c) for c in range(maxcode+1)]
        for c in range(limit):
            x=decode(name,c);sign=bool(c>>(15 if name=='fp16' else 7));v=float(x) if x is not None else math.inf
            if x==0:v=-0.0 if sign else 0.0
            queries.append(dict(format=name,bits=bits(v),code=c));wants.append(dict(code=c if x is not None else None,decoded_bits=bits(v) if x is not None else None))
        for c in range(1,maxcode):
            mid=(values[c]+values[c+1])/2
            for v in [math.nextafter(float(mid),-math.inf),float(mid),math.nextafter(float(mid),math.inf)]:
                x=F(v);pos=bisect.bisect_left(values,x);choices=[k for k in [pos-1,pos] if 0<=k<len(values)];want=min(choices,key=lambda k:(abs(x-values[k]),k%2))
                queries.append(dict(format=name,bits=bits(v),code=0));wants.append(dict(code=want,decoded_bits=0))
    r=subprocess.run([str(PROBE),'codec'],input=''.join(json.dumps(x)+'\n' for x in queries),capture_output=True,text=True,check=True,timeout=300)
    got=[json.loads(x) for x in r.stdout.splitlines()]
    if len(got)!=len(wants):raise ValueError('codec oracle response count')
    for q,a,b in zip(queries,got,wants):
        if a!=b:raise ValueError(('codec disagreement',q,a,b))
    return len(got)
def products():
    cases=0
    manifest=json.loads((ROOT/'benchmarks/manifests/lp-development-v1.json').read_text())
    model=next(i for i in manifest['instances'] if i['id']=='gpup-development-irregular-256')
    path=ROOT/model['model']['path'];doc=json.loads(path.read_text());rows=doc['constraints'];cols=doc['variables'];ids={v['id']:i for i,v in enumerate(cols)}
    for fmt in ['fp16','e4m3','e5m2']:
      for policy in ['uniform','selective']:
       for transpose in [False,True]:
        vector=[(-1 if i%3==0 else 1)*math.ldexp(1+(i%7)/8,-10) for i in range(len(rows) if transpose else len(cols))]
        settings=dict(format=fmt,policy=policy,tile_size=32,rounding='nearest_even',primal_budget=1e-7,dual_budget=1e-7,audit_interval=32,audit_absolute=1e-7,audit_relative=1e-7)
        r=subprocess.run([str(PROBE),'product',str(path),json.dumps(dict(settings=settings,vector=vector,transpose=transpose))],capture_output=True,text=True,check=True,timeout=60);v=json.loads(r.stdout)
        if v['error'] is not None:raise ValueError('oracle fixture refused '+str(v['error']))
        exact=[F(0) for _ in range(len(cols) if transpose else len(rows))]
        for i,row in enumerate(rows):
         for term in row['terms']:
          j=ids[term['variable_id']];k=i if transpose else j;out=j if transpose else i;scale=v['row_scale'][i] if transpose else v['column_scale'][j]
          exact[out]+=F(term['coefficient'])*F(vector[k])*F(scale)
        output_scale=v['column_scale'] if transpose else v['row_scale']
        for got,want,bound,scale in zip(v['product'],exact,v['bounds'],output_scale):
         if abs(F(got)/F(scale)-want)>F(bound):raise ValueError('original-unit error escaped enclosure')
         cases+=1
    return cases
def main():
    t=time.process_time();n=codec();p=products();d=ROOT/'artifacts/gpup-quant-v1/admission';d.mkdir(parents=True,exist_ok=True)
    receipt=dict(identity='gpup-quant-oracle-v1',status='passed',codec_cases=n,original_unit_product_components=p,probe_sha256=file_hash(PROBE),cpu_seconds=time.process_time()-t,gpu_seconds=0)
    write_json(d/'oracle.json',receipt);print(json.dumps(receipt))
if __name__=='__main__':main()
