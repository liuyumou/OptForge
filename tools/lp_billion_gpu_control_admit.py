"""Bitwise GPU control/feasibility, exact continuations, strict independent checks and sanitizers."""
import argparse,copy,json,subprocess
from lp_billion_common import BASE,ROOT,put,load,ref,resolve,require
from lp_billion_admit import call,unpack,serial,validate_timings
from lp_billion_gpu_pack_report import canonical as old_canonical
from lp_billion_prepare_admit import instrument
from lp_general_models import generate
from lp_general_oracle import settings
IMAGE=BASE/'image-v11'

def canonical(response):
    result=old_canonical(response);result.pop('gpu_control',None)
    if 'fast_config' in result:
        result['fast_config'].pop('gpu_control',None);result['fast_config'].pop('gpu_feasibility',None)
    return result

def sanitizer_clean(path):
    text=path.read_text();require('ERROR SUMMARY: 0 errors' in text or 'RACECHECK SUMMARY: 0 hazards' in text,'complete sanitizer summary')

def run(identity,sanitizer=None):
    out=BASE/identity;out.mkdir(exist_ok=False)
    binding=load(IMAGE/'binding.json')
    for item in binding['files'].values():resolve(item)
    cmd=[str(IMAGE/'control-check'),str(IMAGE/'tensor.cubin')]
    if sanitizer:cmd=instrument(cmd,sanitizer,out/'control.sanitizer')
    p=subprocess.run(cmd,text=True,capture_output=True)
    (out/'control.stdout').write_text(p.stdout);(out/'control.stderr').write_text(p.stderr)
    require(p.returncode==0,'bitwise control '+p.stderr[-2000:])
    diagnostics=json.loads(p.stdout.splitlines()[-1]);require(diagnostics==dict(status='passed',merit_comparisons=33,host_fallbacks=3,movement_comparisons=36,feasibility_comparisons=180,invalid_inputs_rejected=78),'complete control/feasibility fixtures')
    if sanitizer:sanitizer_clean(out/'control.sanitizer')
    rows=[]
    for family,size in [('dense',257),('irregular',4097),('rectangular',4097),('ill_scaled',65),('dense_blocks',129)]:
        doc,_=generate(family,size,861700+size);model=out/(family+'.json');put(model,doc)
        p=subprocess.run([str(IMAGE/'executor'),'convert',str(model),str(BASE)],text=True,capture_output=True)
        require(p.returncode==0,'array conversion '+p.stderr)
        arrays=out/(family+'.arrays.json');put(arrays,json.loads(p.stdout))
        for fmt in ['native','fp32','fp4x1','fp4x2']:
            for fault in ([None] if sanitizer else [None,'force_recovery_after','cancel_after']):
                s={**settings(fmt),'iteration_limit':32,'check_interval':16}
                if fault:s[fault]=3
                request=dict(settings=s,tensor=dict(control_interval=8,min_tile_nnz=128),fast=dict(host_reductions=True,host_preparation=True,host_certificates=True,auto_schedule=True,gpu_preparation=True,gpu_packing=True),profile=True)
                candidate=copy.deepcopy(request);candidate['fast'].update(gpu_control=True,gpu_feasibility=True)
                name=f'{family}-{fmt}-{fault}';cmd=[str(IMAGE/'executor'),'solve',str(arrays),str(BASE),str(IMAGE/'tensor.cubin')]
                if sanitizer:cmd=instrument(cmd,sanitizer,out/(name+'.sanitizer'))
                after=call(cmd,[candidate],out,name+'-new')[0]
                before=call([BASE/'image-v10/executor','solve',arrays,BASE,BASE/'image-v10/tensor.cubin'],[request],out,name+'-old')[0]
                validate_timings(after,True);require(canonical(before)==canonical(after),'exact continuation differs '+name)
                require(after['gpu_control']['control_backend']=='gpu' and after['gpu_control']['feasibility_backend']=='gpu','actual GPU control/feasibility')
                response=out/(name+'.response.json');put(response,after);decoded=unpack(after)
                proofs=[serial(model,e,s['tolerance'],out,name+'-'+str(i)) for i,e in enumerate([*decoded['assessments'],decoded])]
                if sanitizer:sanitizer_clean(out/(name+'.sanitizer'))
                rows.append(dict(case=name,response=ref(response),serial=proofs,exact=True))
                print(dict(case=name,exact=True,sanitizer=sanitizer),flush=True)
    put(out/'result.json',dict(status='passed',diagnostics=diagnostics,rows=rows,sanitizer=sanitizer,image=ref(IMAGE/'binding.json'),source=ref(__file__),
        scope='All control/feasibility kernels, exact norm/product trees, deep reduction and long-line fallback; original solve, preparation and packing modules remain byte-identical.'))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--id',required=True);p.add_argument('--sanitizer',choices=['memcheck','racecheck','initcheck','synccheck']);a=p.parse_args();run(a.id,a.sanitizer)
