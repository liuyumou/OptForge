"""Bitwise full-preparation comparisons, including reduction tails and fallbacks."""
import json
import subprocess
from lp_billion_common import BASE,put,ref,require,load
from lp_general_oracle import settings


def document(n,m,kind='normal',sense='minimize'):
    bound=lambda x:dict(kind='finite',value=x)
    coefficient=lambda i,j: (-1. if (i+j)%2 else 1.)*(1.+((i+j)%7)/16.)
    if kind=='tiny':coefficient=lambda i,j:(-1. if (i+j)%2 else 1.)*5e-324
    if kind=='huge':coefficient=lambda i,j:8e307
    return dict(schema_version=1,model_id=f'prep-{n}-{m}-{kind}-{sense}',
        variables=[dict(id=7+13*j,domain='continuous',lower=bound(-2.),upper=bound(3.)) for j in range(n)],
        constraints=[dict(id=9+17*i,lower=bound(-3.),upper=bound(5.),
            terms=[dict(variable_id=7+13*j,coefficient=coefficient(i,j)) for j in range(n)]) for i in range(m)],
        objective=dict(sense=sense,offset=-3.25,terms=[dict(variable_id=7+13*j,coefficient=(j%9-4)/7.) for j in range(n) if j%9!=4]))


def suite(out,image,sanitizer=None):
    from lp_billion_admit import call
    cases=[]
    lengths=[31,33,511,513,1023,1024,1025] if sanitizer else [1,2,3,7,8,15,16,31,32,33,63,64,65,127,128,129,255,256,257,511,512,513,1023,1024,1025]
    for n in lengths:
        cases.append((n,1,'normal','minimize',None))
        if not sanitizer:cases.append((1,n,'normal','maximize',None))
    if not sanitizer:
        for n,m in [(0,0),(0,3),(3,0),(7,11),(33,9)]:cases.append((n,m,'normal','maximize',None))
        for kind in ['tiny','huge']:
            for power in [1,2,20]:cases.append((3,2,kind,'minimize',dict(ruiz=0,alpha=0.,power=power)))
        for ruiz,alpha,power in [(0,1.,20),(3,1.,1),(3,0.,20),(2,.5,20)]:
            cases.append((17,9,'normal','minimize',dict(ruiz=ruiz,alpha=alpha,power=power)))
    results=[]
    for index,(n,m,kind,sense,variant) in enumerate(cases):
        name=f'prepare-{index}';model=out/(name+'.model.json');put(model,document(n,m,kind,sense))
        converted=subprocess.run([str(image/'executor'),'convert',str(model),str(BASE)],text=True,capture_output=True)
        require(converted.returncode==0,'preparation fixture conversion '+converted.stderr)
        arrays=out/(name+'.arrays.json');put(arrays,json.loads(converted.stdout))
        request=dict(settings=settings('native'))
        if variant:
            # Published non-preparation settings remain unchanged.
            request['lp_settings']=dict(schema_version=1,preconditioner=dict(ruiz_passes=variant['ruiz'],pock_chambolle_alpha=variant['alpha']),
                iteration_limit=100,check_interval=100,power_iterations=variant['power'],
                restart=dict(sufficient=.2,necessary=.8,artificial=.36),
                primal_weight=dict(proportional=.5,integral=0.,derivative=0.))
        cmd=[str(image/'executor'),'prepare-check',str(arrays),str(BASE),str(image/'prepare.cubin')]
        if sanitizer:cmd=['/usr/local/cuda/bin/compute-sanitizer','--tool',sanitizer,'--error-exitcode','99','--log-file',str(out/(name+'.sanitizer')),*cmd]
        result=call(cmd,[request],out,name)[0]
        require(result['exact'],'full exact preparation '+name)
        fallback=n==0 or m==0 or max(n,m)>1024 or kind=='huge' or (variant is not None and variant['alpha']==.5)
        require(result['preparation']['backend']==('host-fallback' if fallback else 'gpu-fp64'),'explicit preparation domain '+name)
        if sanitizer and result['preparation']['backend']=='gpu-fp64':
            text=(out/(name+'.sanitizer')).read_text()
            require('ERROR SUMMARY: 0 errors' in text or 'RACECHECK SUMMARY: 0 hazards' in text,'preparation sanitizer summary')
        path=out/(name+'.result.json');put(path,result);results.append(ref(path))
    # More than 1024^2 vector entries exercise three recursive norm levels.
    from lp_billion_generate import generate
    identity=out.name+'-deep-norm';generate(identity,'wide',4_194_368,861198)
    model=BASE/identity/'model.json';name='prepare-deep-norm'
    cmd=[str(image/'executor'),'prepare-check',str(model),str(BASE),str(image/'prepare.cubin')]
    if sanitizer:cmd=['/usr/local/cuda/bin/compute-sanitizer','--tool',sanitizer,'--error-exitcode','99','--log-file',str(out/(name+'.sanitizer')),*cmd]
    result=call(cmd,[dict(settings=settings('native'))],out,name)[0]
    require(result['exact'] and result['preparation']['backend']=='gpu-fp64','deep norm GPU preparation')
    if sanitizer:
        text=(out/(name+'.sanitizer')).read_text()
        require('ERROR SUMMARY: 0 errors' in text or 'RACECHECK SUMMARY: 0 hazards' in text,'deep norm sanitizer')
    path=out/(name+'.result.json');put(path,result);results.append(ref(path))
    return dict(exact_preparations=len(results),results=results)
