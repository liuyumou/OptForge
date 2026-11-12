"""Four configurations, exact same-image device lifecycle and diagnostic admission."""
import itertools
import os
import subprocess
from lp_delivery3_common import ROOT, BASE, BINARY, VARIANTS, LANES, TIERS, load, put, ref, require
from lp_delivery3_cpu import environment, numerical_source
from lp_delivery3_transport import Service
from lp_delivery3_study import PARENT, run_cell
from lp_delivery2_study import matches
import lp_fp4_accel_lifecycle as lifecycle


def run():
    for name in ('cpu-acceptance-v1','native-gate-v1'):
        require(load(BASE/'resources'/f'{name}.settlement.json')['status']=='passed','CPU/native gate incomplete')
    require(load(BASE/'cpu-v1/manifest.json')['binary']==ref(BINARY),'admitted executable changed')
    parent=load(PARENT/'manifest.json');image=ROOT/parent['image']['path']
    require(ref(image)==parent['image'],'device image changed')
    for binding in parent['sources']:require(ref(ROOT/binding['path'])==binding,'historical source changed')
    require(load(ROOT/'docs/benchmarks/data/fp4-checker-acceptance-v1.json')['status']=='passed','unchanged-image sanitizer admission')
    numerical_source();out=BASE/'device-v1';out.mkdir(exist_ok=False)
    lifecycle.BINARY=BINARY;lifecycle.Service=Service;rows={}
    for variant in VARIANTS:
        env=environment(variant)
        for key in ('GPUP_DELIVERY2_CONTROL','GPUP_CHECKER_ORIGINAL'):os.environ.pop(key,None)
        os.environ['GPUP_DELIVERY3_VARIANT']=env['GPUP_DELIVERY3_VARIANT'];os.environ['GPUP_DELIVERY3_PROFILE']='0'
        lifecycle.run(image,out/variant);rows[variant]=load(out/variant/'result.json')['rows']
    require(all(len(r)==42 for r in rows.values()),'lifecycle coverage')
    for variant in VARIANTS[1:]:
        for control,candidate in zip(rows['control'],rows[variant]):
            require(control['case']==candidate['case'],'case order')
            for key in ('first','second','result'):
                if key in control:matches(candidate[key],control[key],ref(BINARY))
    failures=[]
    for variant,profile in itertools.product(VARIANTS,(False,True)):
        result=subprocess.run([str(BINARY),'serve',str(image)+'.missing',str(ROOT/parent['models']['dense-generic-512']['path'])],capture_output=True,timeout=15,env=environment(variant,profile))
        require(result.returncode!=0 and not result.stdout,'missing module became ready')
        failures.append(dict(variant=variant,profile=profile,returncode=result.returncode,stderr=result.stderr.decode()))
    put(out/'startup-failures.json',failures)
    smoke=out/'smoke';smoke.mkdir();cells=[]
    for profile,family,variant,lane,tier in itertools.product((False,True),('coupled-equality','dense-generic-512','ill-scaled-generic-128','infinite-bound-refusal'),VARIANTS,LANES,TIERS):
        old=next(c for c in parent['cells'] if c['family']==family and c['lane']==lane and c['tier']==tier and c['lifecycle']=='prepared' and c['repetition']==0)
        cell=dict(id=f'{profile}-{family}-{variant}-{lane}-{tier}',block=0,family=family,variant=variant,lane=lane,tier=tier,lifecycle='prepared',role=variant,original_result=ref(PARENT/(old['id']+'.json')))
        manifest=dict(profile=profile,image=parent['image'],models=parent['models'],settings=parent['settings'],binary=ref(BINARY),prepared_solves=3)
        row=run_cell(smoke,cell,manifest)
        for record in row['records']:
            result=load(ROOT/record['result']['path'])
            require(('delivery_profile' in result)==profile,'profile mode changed')
            if profile:
                for p in result['delivery_profile']['assessments']:
                    require(0<=p['request_build_encode_write_flush_ns']<=p['response_wait_read_end_ns']<=p['response_decode_end_ns']<=p['binding_end_ns'],'parent response span order')
        cells.append(row)
    put(out/'result.json',dict(status='passed',lifecycle_cases=168,setup_failures=8,smoke_cells=len(cells),smoke_solves=sum(len(c['records']) for c in cells),rows=cells,
        image=parent['image'],binary=ref(BINARY),source=numerical_source(),prior_sanitizer_admission=ref(ROOT/'docs/benchmarks/data/fp4-checker-acceptance-v1.json')))
    print(dict(status='passed',lifecycle_cases=168,setup_failures=8,smoke_cells=len(cells)),flush=True)

if __name__=='__main__':run()
