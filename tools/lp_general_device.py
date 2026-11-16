"""Independent sparse GPU arithmetic, restoration and certificate admission."""
import argparse
import json
import math
import struct
import hashlib
import subprocess
from pathlib import Path
from lp_general_common import ROOT,BASE,load,put,ref,require
from lp_general_models import generate,FAMILIES
from lp_general_oracle import settings

BINARY=ROOT/'research/lp-general-lowbit/target/release/lp-general-lowbit'
SERIAL=ROOT/'artifacts/gpup-checker2-v1/build-v5/executor'
IMPLIED_VERIFIED={}

def bits(values):return [struct.pack('>d',v).hex() for v in values]
def f32(v):return struct.unpack('f',struct.pack('f',v))[0]

def product(matrix,x,components=None):
    """Independent explicit 32-lane tree; no device-produced products used."""
    out=[]
    for lo,hi in zip(matrix['offsets'],matrix['offsets'][1:]):
        p=[0.]*32
        for lane in range(32):
            for j in range(lo+lane,hi,32):
                v=x[matrix['indices'][j]]
                if components is None:p[lane]+=matrix['original'][j]*v
                else:
                    for a in components[matrix['ids'][j]]:p[lane]=f32(p[lane]+f32(f32(a)*v))
        for d in (16,8,4,2,1):
            old=p[:]
            for lane in range(32-d):p[lane]=old[lane]+old[lane+d] if components is None else f32(old[lane]+old[lane+d])
        out.append(p[0])
    return out

def fixed_reference(r,format):
    x=r['initial_x'][:];y=r['initial_y'][:];ax=x[:];ay=y[:]
    tau=r['step']/r['weight'];sigma=r['step']*r['weight']
    matrices=r['operator'];components=r['components'] if format!='native' else None
    # FP32 and FP4x1 kernels issue one multiplication, not an extra zero term.
    if components is not None and format in ('fp32','fp4x1'):components=[p[:1] for p in components]
    refs={False:product(matrices['rows'],ax),True:product(matrices['columns'],ay)}
    def apply(transpose,v,anchor):
        matrix=matrices['columns' if transpose else 'rows']
        if components is None:return product(matrix,v)
        delta=[f32(a-b) for a,b in zip(v,anchor)]
        return [a+b for a,b in zip(refs[transpose],product(matrix,delta,components))]
    for t in range(r['count']):
        aty=apply(True,y,ay);lo,hi=r['column_bounds']
        nx=[min(u,max(l,old-tau*(c-a))) for old,c,a,l,u in zip(x,r['objective'],aty,lo,hi)]
        extra=[2*a-b for a,b in zip(nx,x)];av=apply(False,extra,ax);lo,hi=r['row_bounds']
        ny=[]
        for old,a,l,u in zip(y,av,lo,hi):
            raw=old-sigma*a;ny.append(raw-sigma*min(-l if l is not None else math.inf,max(-u if u is not None else -math.inf,raw/sigma)))
        toward=(t+1)/(t+2);back=1/(t+2)
        x=[toward*v+back*a for v,a in zip(nx,ax)];y=[toward*v+back*a for v,a in zip(ny,ay)]
    return x,y

def serial(model,endpoint,tolerance,directory,identity):
    # A repaired certificate carries its actual untrusted witness separately
    # from the numerical continuation state. Replay precisely that witness.
    endpoint={**endpoint,'dual':endpoint['certificate'].get('certificate_dual',endpoint['dual'])}
    proof=endpoint.get('bound_proof',endpoint['certificate'].get('bound_proof',[]))
    if proof:
        # Independently verify every implication before giving the unchanged
        # serial checker the equivalent model. Original primal validation is
        # checked separately: implied bounds may reject approximate endpoints.
        from lp_general_implied import verify
        import copy
        key=hashlib.sha256((ref(model)['sha256']+json.dumps(proof,sort_keys=True)).encode()).hexdigest()
        cache_key=(str(directory),key)
        if cache_key not in IMPLIED_VERIFIED:
            original=load(model);tightened=copy.deepcopy(original)
            variables={v['id']:v for v in tightened['variables']}
            for step in proof:variables[step['variable_id']][step['side']]=dict(kind='finite',value=step['value'])
            verify(original,tightened,proof)
            tightened_path=directory/(key+'.implied.model.json');put(tightened_path,tightened)
            proof_path=directory/(key+'.implied.proof.json');put(proof_path,dict(original=ref(model),tightened=ref(tightened_path),steps=proof,verified=True))
            IMPLIED_VERIFIED[cache_key]=(tightened_path,proof_path)
        tightened_path,proof_path=IMPLIED_VERIFIED[cache_key]
        original_endpoint=directory/(identity+'.original.endpoint.json');original_result=directory/(identity+'.original.serial.json')
        put(original_endpoint,dict(model_sha256=ref(model)['sha256'],primal=endpoint['primal'],dual=endpoint['dual'],transport='completed'))
        subprocess.run([str(SERIAL),'check-serial',str(model),str(original_endpoint),'certified-'+('1e-9' if tolerance==1e-9 else '1e-7'),str(original_result)],check=True,capture_output=True)
        original_certificate=load(original_result)
        model=tightened_path
    path=directory/(identity+'.endpoint.json');dest=directory/(identity+'.serial.json')
    put(path,dict(model_sha256=ref(model)['sha256'],primal=endpoint['primal'],dual=endpoint['dual'],transport='completed'))
    subprocess.run([str(SERIAL),'check-serial',str(model),str(path),'certified-'+('1e-9' if tolerance==1e-9 else '1e-7'),str(dest)],check=True,capture_output=True)
    result=load(dest)
    if proof:
        # The original model remains the primal-feasibility authority.
        result['feasible']=original_certificate['feasible']
        result['accepted']=original_certificate['feasible'] and result['gap_closed']
    expected=endpoint['certificate']
    for key in ['accepted','feasible','objective','bound','gap_upper']:
        require(result[key]==expected[key],'original serial certificate mismatch '+key)
    if proof:
        composed=directory/(identity+'.composed.serial.json')
        put(composed,dict(kind='original-model-implied-bound-certificate',original_check=ref(original_result),
            equivalent_bound_check=ref(dest),implications=ref(proof_path),
            result={k:result[k] for k in ['accepted','feasible','objective','bound','gap_upper']}))
        return ref(composed)
    return ref(dest)

def run(identity,image,sanitizer=None):
    require(load(BASE/'resources/native-v2.settlement.json')['status']=='passed','full native gate required')
    out=BASE/identity;out.mkdir(parents=True,exist_ok=False)
    rows=[]
    def call(command,model,commands,name):
        argv=[str(BINARY),command,str(model),str(image)]
        log=out/(name+'.sanitizer')
        if sanitizer:argv=['/usr/local/cuda/bin/compute-sanitizer','--tool',sanitizer,'--error-exitcode','99','--log-file',str(log),*argv]
        input=''.join(json.dumps(c)+'\n' for c in commands)
        put(out/(name+'.requests.json'),commands)
        p=subprocess.run(argv,input=input,text=True,capture_output=True)
        (out/(name+'.stdout.jsonl')).write_text(p.stdout);(out/(name+'.stderr.txt')).write_text(p.stderr)
        require(p.returncode==0,'device process failed '+name)
        if sanitizer:
            text=log.read_text();require('ERROR SUMMARY: 0 errors' in text or (sanitizer=='racecheck' and 'RACECHECK SUMMARY: 0 hazards' in text),'sanitizer not clean')
        result=[json.loads(line) for line in p.stdout.splitlines()];require(len(result)==len(commands),'coverage')
        return result
    families=['rectangular','ill_scaled','dense_blocks'] if sanitizer else FAMILIES
    for family in families:
        doc,witness=generate(family,33,790081);model=out/(family+'.json');put(model,doc)
        formats=['native','fp32','fp4x1','fp4x2']
        commands=[dict(settings=settings(f),count=5) for f in formats]
        for f,r in zip(formats,call('gpu-fixed',model,commands,family+'-fixed')):
            x,y=fixed_reference(r,f);require(r['valid'],'fixed numerical guard')
            require(bits(x)==bits(r['primal']) and bits(y)==bits(r['dual']),'independent fixed update differs '+family+' '+f)
            require(bits(r['restored_x'])==bits(r['initial_x']) and bits(r['restored_y'])==bits(r['initial_y']),'device reset differs')
            rows.append(dict(case='fixed',family=family,format=f,steps=5))
        commands=[]
        for format in ['native','fp4x2']:
            for fault in [None,'force_recovery_after','cancel_after']:
                s=settings(format);s.update(iteration_limit=24,check_interval=8,reference_window=4)
                if fault:s[fault]=2
                commands.append(dict(settings=s))
        for i,(request,r) in enumerate(zip(commands,call('gpu',model,commands,family+'-solve'))):
            require(sum(r['attempted'])==r['physical'] and sum(r['accepted'])==r['logical'],'work accounting')
            require(all(v['restored_exact'] for v in r['recoveries']),'controller restore differs')
            if request['settings'].get('cancel_after'):
                require(r['status']=='cancelled' and not r['certified'] and r['logical']==0 and r['physical']==2,'cancellation authority')
            if request['settings'].get('force_recovery_after') and request['settings']['format']!='native':
                require(r['recoveries'] and r['physical']>r['logical'],'forced recovery accounting')
            certificates=[]
            for j,ep in enumerate([*r['assessments'],r]):certificates.append(serial(model,{**ep,'bound_proof':r['bound_proof']},request['settings']['tolerance'],out,f'{family}-{i}-{j}'))
            rows.append(dict(case='solve',family=family,settings=request['settings'],status=r['status'],certificates=certificates))
    # Positive strict certificates and empty row/nnz allocations.
    doc,_=generate('rectangular',33,790085);doc['constraints']=[];doc['objective']['terms']=[]
    model=out/'zero-rows.json';put(model,doc)
    commands=[dict(settings={**settings(f),'tolerance':t,'iteration_limit':8,'check_interval':8}) for f in ['native','fp32','fp4x1','fp4x2'] for t in [1e-7,1e-9]]
    for i,(request,r) in enumerate(zip(commands,call('gpu',model,commands,'zero-rows'))):
        require(r['certified'] and r['physical']==8 and r['logical']==8,'positive empty-row certificate')
        proof=serial(model,r,request['settings']['tolerance'],out,f'zero-{i}')
        rows.append(dict(case='zero-rows',certificate=proof))
    # Cover new large and rectangular grids without making a convergence claim.
    for n,mfamily in [(4097,'rectangular'),(32769,'irregular')]:
        if sanitizer and n>4097:continue
        doc,_=generate(mfamily,n,790083);model=out/(f'large-{n}.json');put(model,doc)
        commands=[dict(settings=settings(f),count=2) for f in ['native','fp4x2']]
        for f,r in zip(['native','fp4x2'],call('gpu-fixed',model,commands,f'large-{n}')):
            x,y=fixed_reference(r,f);require(r['valid'] and bits(x)==bits(r['primal']) and bits(y)==bits(r['dual']),'large fixed updates')
            rows.append(dict(case='large',columns=n,format=f))
    put(out/'result.json',dict(status='passed',rows=rows,binary=ref(BINARY),image=ref(image),serial_checker=ref(SERIAL),sanitizer=sanitizer))
    print(dict(status='passed',cases=len(rows),sanitizer=sanitizer),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--id',required=True);p.add_argument('--image',required=True,type=Path)
    p.add_argument('--sanitizer',choices=['memcheck','racecheck','initcheck','synccheck']);a=p.parse_args();run(a.id,a.image,a.sanitizer)
