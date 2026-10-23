"""Independent integer/Fraction format, product and outward-program witnesses."""
import functools,json,math,struct,subprocess,time,resource
from fractions import Fraction as F
from lp_protocol import ROOT,read_json,write_json,file_hash
from lp_quant_oracle import codec
PROBE=ROOT/'target/release/examples/quant_resident_probe'
@functools.lru_cache(None)
def power(e):return F(2)**e
def rounded(x,p=53):
    if not x:return F(0)
    sign=-1 if x<0 else 1;x=abs(x);n,d=x.numerator,x.denominator
    e=n.bit_length()-d.bit_length()
    if x<power(e):e-=1
    minimum=-149 if p==24 else -1074
    unit=power(max(e-p+1,minimum));v=x/unit;q,r=divmod(v.numerator,v.denominator)
    if 2*r>v.denominator or 2*r==v.denominator and q%2:q+=1
    return sign*q*unit
def next_up(x):
    v=float(rounded(x));bits=struct.unpack('>Q',struct.pack('>d',v))[0]
    if not math.isfinite(v):return None
    return F(struct.unpack('>d',struct.pack('>Q',bits+1))[0])
def add(a,b):return b if not a else a if not b else next_up(a+b)
def mul(a,b):return F(0) if not a or not b else next_up(a*b)
def div(a,b):return F(0) if not a else next_up(a/b)
def gamma(n,low):
    nu=n*power(-24 if low else -53)
    return next_up(nu/(1-nu))
def cast_error(x):
    v=rounded(x,24)
    return F(0) if x==v else next_up(abs(rounded(x-v)))
def bits(x):return struct.pack('>d',float(x))
def evaluate(meta,result,vector,transpose,layout):
    gs=meta['column_groups' if transpose else 'row_groups'];scales=meta['column_scale' if transpose else 'row_scale']
    values=list(map(F,meta['values']));quant=list(map(F,meta['quantized']));le=list(map(F,meta['low_error']));ne=list(map(F,meta['native_error']))
    v=list(map(F,vector));maximum=max(map(abs,v),default=F(0));conversion=F(0) if result['promotion']['native'] else max(map(cast_error,v),default=F(0));tiny=power(-1074)
    products=[];bounds=[];coarse_flags=[]
    for i,groups in enumerate(gs):
        ci=(len(meta['row_groups']) if transpose else 0)+i
        alpha,beta,small=map(F,result['constants'][ci]);scale=F(scales[i])
        coarse=add(div(add(add(mul(alpha,maximum),mul(beta,conversion)),small),scale),tiny)
        detailed=coarse>F(1e-7);total=F(0);bound=F(0);mass=F(0);lanes=[F(0)]*32;entry=0
        for group in groups:
            low=not result['promotion']['mask'][meta['tile_of'][group[0]]]
            s=b=ab=F(0)
            for j in group:
                x=v[meta['row_of'][j] if transpose else meta['column_of'][j]];a=quant[j] if low else values[j];vx=rounded(x,24) if low else x
                product=rounded(a*vx,24 if low else 53);s=rounded(s+product,24 if low else 53)
                if layout!='segmented':lanes[entry%32]=rounded(lanes[entry%32]+product);entry+=1
                if detailed:
                    b=add(b,mul(le[j] if low else ne[j],abs(x)))
                    if low:b=add(b,mul(abs(a),cast_error(x)))
                    ab=add(ab,mul(abs(a),abs(vx)))
            total=rounded(total+s)
            if detailed:
                b=add(b,mul(gamma(len(group)+1,low),ab));b=add(b,(len(group)+1)*power(-149 if low else -1074));bound=add(bound,b);mass=add(mass,ab)
        if layout!='segmented':
            for offset in [16,8,4,2,1]:
                for lane in range(offset):lanes[lane]=rounded(lanes[lane]+lanes[lane+offset])
            total=lanes[0]
        if detailed:
            depth=len(groups)+2 if layout=='segmented' else sum(map(len,groups))+8
            bound=add(div(add(add(bound,mul(gamma(depth,False),add(mass,bound))),(len(groups)+1)*tiny),scale),tiny)
        else:bound=coarse
        products.append(total);bounds.append(bound);coarse_flags.append(not detailed)
    for actual,want in zip(result['product'],products):
        if bits(actual)!=bits(want):raise ValueError('independent product rounding disagreement')
    for actual,want in zip(result['bounds'],bounds):
        if bits(actual)!=bits(want):raise ValueError('directed bound-program disagreement')
    if result['counts']['coarse_pass']!=sum(coarse_flags):raise ValueError('coarse guard selection disagreement')
    return products,bounds,coarse_flags
def model_inputs():
    manifest=read_json(ROOT/'benchmarks/manifests/lp-development-v1.json')
    actual=next(i for i in manifest['instances'] if i['id']=='gpup-development-irregular-256')
    yield ROOT/actual['model']['path']
    d=ROOT/'artifacts/gpup-quant-resident-v1/oracle';d.mkdir(parents=True,exist_ok=True)
    finite=lambda x:dict(kind='finite',value=x)
    # Exact representation, cancellation, sparse/transpose and scaled extremes.
    for name,a in [('exact',1.),('cancel',1.1),('small',2.**-60),('large',2.**60),('subnormal-scale',2.**-1000),('extreme-scale',2.**1000)]:
        variables=[dict(id=i,domain='continuous',lower=finite(-2.),upper=finite(2.)) for i in range(35)]
        rows=[dict(id=i,lower=finite(-1.),upper=finite(1.),terms=[dict(variable_id=j,coefficient=a*((-1.) if (i+j)%2 else 1.)) for j in range(35) if (i*7+j)%5==0]) for i in range(33)]
        doc=dict(schema_version=1,model_id='resident-oracle-'+name,variables=variables,constraints=rows,objective=dict(sense='minimize',offset=0.,terms=[]));p=d/(name+'.model.json');write_json(p,doc);yield p
def main():
    start=time.process_time();before=resource.getrusage(resource.RUSAGE_CHILDREN);formats=codec();components=programs=coefficients=tight_passes=0;cases=[]
    for path in model_inputs():
        model=read_json(path);rows=model['constraints'];cols=model['variables'];var={v['id']:i for i,v in enumerate(cols)}
        for fmt in ['fp16','e4m3','e5m2','fp64']:
            for policy in ['uniform','selective']:
                from lp_quant_admission import settings
                for layout in (['segmented','tuned'] if fmt=='fp64' else ['segmented']):
                    queries=[]
                    for t in [False,True]:
                        n=len(rows) if t else len(cols)
                        for sample in range(7):
                            exponent=[-140,-30,-10,0,10,30,60][sample]
                            vector=[(-1. if i%3==0 else 1.)*math.ldexp(1+(i%7)/8,exponent) for i in range(n)]
                            if sample==2:vector=[math.nextafter(v,math.inf) for v in vector]
                            queries.append(dict(transpose=t,vector=vector))
                    for t in [False,True]:
                        n=len(rows) if t else len(cols);v=[0.]*n
                        if n:v[0]=0.03125
                        queries.append(dict(transpose=t,vector=v))
                    r=subprocess.run([str(PROBE),'batch',str(path),json.dumps(dict(settings=settings(fmt,policy),layout=layout))],input=''.join(json.dumps(q)+'\n' for q in queries),capture_output=True,text=True,timeout=120,check=True)
                    output=[json.loads(x) for x in r.stdout.splitlines()];meta=output[0]
                    if fmt!='fp64':
                        native=[dict(transpose=t,vector=[(-1. if i%2 else 1.)*2.**-200 for i in range(len(rows) if t else len(cols))],promote=list(range(max(meta['tile_of'],default=-1)+1))) for t in [False,True]]
                        nr=subprocess.run([str(PROBE),'batch',str(path),json.dumps(dict(settings=settings(fmt,policy),layout=layout))],input=''.join(json.dumps(q)+'\n' for q in native),capture_output=True,text=True,timeout=120,check=True)
                        no=[json.loads(x) for x in nr.stdout.splitlines()]
                        if no[0]!=meta:raise ValueError('immutable metadata changed')
                        queries+=native;output+=no[1:]
                    # Check every stored error against exact original scaling.
                    for j,(i,k) in enumerate(zip(meta['row_of'],meta['column_of'])):
                        term=next(v for v in rows[i]['terms'] if var[v['variable_id']]==k)
                        exact=F(term['coefficient'])*F(meta['row_scale'][i])*F(meta['column_scale'][k])
                        if F(meta['low_error'][j])<abs(exact-F(meta['quantized'][j])) or F(meta['native_error'][j])<abs(exact-F(meta['values'][j])):raise ValueError('coefficient enclosure escaped')
                        coefficients+=2
                    for q,result in zip(queries,output[1:]):
                        products,bounds,coarse=evaluate(meta,result,q['vector'],q['transpose'],layout)
                        exact=[F(0)]*len(products)
                        for i,row in enumerate(rows):
                            for term in row['terms']:
                                j=var[term['variable_id']];k=i if q['transpose'] else j;out=j if q['transpose'] else i
                                scale=meta['row_scale'][i] if q['transpose'] else meta['column_scale'][j]
                                exact[out]+=F(term['coefficient'])*F(q['vector'][k])*F(scale)
                        scales=meta['column_scale'] if q['transpose'] else meta['row_scale']
                        for i,(got,want,bound,scale) in enumerate(zip(products,exact,bounds,scales)):
                            if abs(rounded(got/F(scale))-want)>bound:raise ValueError('original-unit product error escaped')
                            if not result['flags'][i]&6 and (bound>F(1e-7))!=bool(result['flags'][i]&1):raise ValueError('admission boundary disagreement')
                            if not coarse[i] and bound<=F(1e-7):tight_passes+=1
                            components+=1
                        programs+=1
                    cases.append(dict(model=str(path.relative_to(ROOT)),format=fmt,policy=policy,layout=layout,queries=len(queries)))
    receipt=dict(identity='gpup-quant-resident-oracle-v1',status='passed',format_cases=formats,coefficient_components=coefficients,product_components=components,directed_programs=programs,tight_pass_coarse_fail=tight_passes,probe_sha256=file_hash(PROBE),cases=cases,cpu_seconds=time.process_time()-start+resource.getrusage(resource.RUSAGE_CHILDREN).ru_utime+resource.getrusage(resource.RUSAGE_CHILDREN).ru_stime-before.ru_utime-before.ru_stime,gpu_seconds=0)
    write_json(ROOT/'artifacts/gpup-quant-resident-v1/oracle/oracle.json',receipt);print(json.dumps({k:v for k,v in receipt.items() if k!='cases'}),flush=True)
if __name__=='__main__':main()
