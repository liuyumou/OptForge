"""Independent exact-rational conversion and rounding proof for ADR-0042."""
import json,math,random,struct,subprocess
from fractions import Fraction as F
from pathlib import Path
from lp_protocol import ROOT,write_json,file_hash

def power(e):return F(2)**e

def main():
 rng=random.Random(17022);cases=[];expected=[]
 values=[0.,-0.,1.,-1.,float.fromhex('0x1.fffffffffffffp+1023'),float.fromhex('0x1p-1022'),float.fromhex('0x0.0000000000001p-1022')]
 values += [struct.unpack('>d',rng.getrandbits(64).to_bytes(8,'big'))[0] for _ in range(5000)]
 for x in values:
  if not math.isfinite(x):continue
  e=math.frexp(abs(x))[1] if x else -1074
  for spread in [0,3,31,60]:
   exponent=e+spread;z=F(x)/power(exponent-56);q=abs(z.numerator)//z.denominator*(-1 if z<0 else 1)
   cases.append(dict(bits=struct.pack('>d',x).hex(),exponent=exponent));expected.append(('q',q) if not x or q else ('error',None))
 for _ in range(7000):
  n=rng.randrange(-(1<<117),1<<117);e=rng.randrange(-2258,1937);exact=F(n)*power(e)
  try:x=float(exact)
  except OverflowError:x=math.copysign(math.inf,n)
  cases.append(dict(integer=str(n),base=e));expected.append(('bits',struct.pack('>d',x).hex()) if math.isfinite(x) and (not n or x) else ('error',None))
 # Ties, cancellation, subnormal ties, full significands and reconstruction carries.
 for n in [0,1,-1,3,-3,(1<<53)+1,(1<<53)+3,-((1<<53)+3),(1<<117)-1]:
  for e in [-1190,-1075,-1074,-53,0,971,1024]:
   try:x=float(F(n)*power(e))
   except OverflowError:x=math.copysign(math.inf,n)
   cases.append(dict(integer=str(n),base=e));expected.append(('bits',struct.pack('>d',x).hex()) if math.isfinite(x) and (not n or x) else ('error',None))
 binary=ROOT/'target/release/examples/tensor_probe'
 r=subprocess.run([str(binary)],input=''.join(json.dumps(c)+'\n' for c in cases),capture_output=True,text=True,timeout=120,check=True)
 rows=r.stdout.splitlines()
 if len(rows)!=len(cases):raise ValueError('oracle row count')
 for c,(key,want),raw in zip(cases,expected,rows):
  actual=json.loads(raw)
  if key=='error':assert 'error' in actual,(c,actual)
  elif key=='q':assert actual.get('q')==str(want),(c,actual,want)
  else:
   assert actual.get('bits')==want,(c,actual,want)
   exact=F(int(c['integer']))*power(c['base']);x=struct.unpack('>d',bytes.fromhex(want))[0]
   assert abs(exact-F(x))<=F(actual['bound']),(c,actual,exact)
 # Every BF16 digit product is exactly BF16, and every reduction order stays integral.
 for a in range(-15,16):
  for b in range(-15,16):assert int.from_bytes(struct.pack('>f',float(a*b)),'big')&65535==0
 assert 32*127**2<2**24 and 32*15**2<2**24 and 32*((1<<56)-1)**2<2**127
 # Independently enclose products of the original coefficients and exact-real
 # scaling factors; the production guard is never reused by this checker.
 model=ROOT/'artifacts/lp-inputs-v1/gpup-development-dense_block-1024.json'
 product_probe=ROOT/'target/release/examples/tensor_product_probe'
 raw=subprocess.check_output([str(product_probe),str(model)],text=True,timeout=120)
 data=json.loads(raw);doc=json.loads(model.read_text());component_count=0
 for row in data['rows']:
  vector=list(map(F,row['vector']));r=list(map(F,data['row_scale']));c=list(map(F,data['column_scale']));t=row['transpose'];exact=[F(0) for _ in row['output']]
  for i,constraint in enumerate(doc['constraints']):
   for term in constraint['terms']:
    j=term['variable_id'];a=F(term['coefficient'])*r[i]*c[j]
    exact[j if t else i]+=a*vector[i if t else j]
  scale=c if t else r
  for i,(out,bound,flag) in enumerate(zip(row['output'],row['bounds'],row['flags'])):
   if flag&6:continue
   assert abs(F(out)-exact[i])/scale[i]<=F(bound),(t,row['native'],i,out,bound,exact[i])
   component_count+=1
 proof_dir=ROOT/'artifacts/gpup-tensor-v1/proofs';proof_dir.mkdir(parents=True,exist_ok=True);(proof_dir/'original-unit-products.json').write_text(raw)
 from lp_tensor_layout_oracle import verify as verify_layout
 layout=verify_layout()
 receipt=dict(fragment_layout=layout,status='passed',gpu_seconds=0,cases=len(cases),original_unit_components=component_count,product_probe_sha256=file_hash(product_probe),product_witness_sha256=file_hash(proof_dir/'original-unit-products.json'),bf16_digit_products=31**2,maximum_tile_magnitude_bits=(32*((1<<56)-1)**2).bit_length(),probe_sha256=file_hash(binary),oracle_sha256=file_hash(Path(__file__)))
 write_json(ROOT/'docs/benchmarks/data/tensor/oracle.json',receipt);print(receipt)
if __name__=='__main__':main()
