"""Same-image device/lifecycle admission; no changed numerical kernel or sanitizer claim."""
import subprocess
from lp_delivery2_common import BASE,ROOT,load,put,ref,require
from lp_delivery2_cpu import BINARY,numerical_source
from lp_delivery2_study import delivery_mode,freeze,execute,matches
import lp_fp4_accel_run as transport
import lp_fp4_accel_lifecycle as lifecycle


def run():
    for identity in ('cpu-acceptance-v1','native-gate-v2','software-tail-v1'):
        require(load(BASE/'resources'/f'{identity}.settlement.json')['status']=='passed','missing CPU gate')
    parent=load(ROOT/'artifacts/gpup-fp4-accel-v1/study-v1/manifest.json')
    image=ROOT/parent['image']['path'];require(ref(image)==parent['image'],'device image changed')
    for source in parent['sources']:require(ref(ROOT/source['path'])==source,'numerical source changed')
    numerical_source()
    prior=load(ROOT/'docs/benchmarks/data/fp4-checker-acceptance-v1.json')
    require(prior['status']=='passed','prior unchanged-image admission')
    out=BASE/'lifecycle-v1';out.mkdir(exist_ok=False)
    transport.BINARY=BINARY;lifecycle.BINARY=BINARY
    rows={}
    for mode in ('original','optimized'):
        delivery_mode(mode);lifecycle.run(image,out/mode)
        rows[mode]=load(out/mode/'result.json')['rows']
    require(len(rows['original'])==len(rows['optimized'])==42,'lifecycle coverage')
    for control,candidate in zip(rows['original'],rows['optimized']):
        require(control['case']==candidate['case'],'lifecycle ordering')
        for key in ('first','second','result'):
            if key in control:matches(candidate[key],control[key],ref(BINARY))
    # Candidate starts its checker before module loading: force a module failure
    # after spawn, exercising the startup guard and inherited-pipe EOF cleanup.
    model=ROOT/parent['models']['dense-generic-512']['path']
    failure=subprocess.run([str(BINARY),'serve',str(image)+'.missing',str(model)],capture_output=True,timeout=15)
    require(failure.returncode!=0 and not failure.stdout,'failed module became ready')
    put(out/'setup-failure.json',dict(returncode=failure.returncode,stderr=failure.stderr.decode()))
    put(out/'result.json',dict(status='passed',cases=84,setup_failures=1,exact_modes=True,
        original=ref(out/'original/result.json'),optimized=ref(out/'optimized/result.json'),
        unchanged_image=parent['image'],prior_sanitizer_admission=ref(ROOT/'docs/benchmarks/data/fp4-checker-acceptance-v1.json')))
    freeze(BASE/'smoke-v1',True);execute(BASE/'smoke-v1')

if __name__=='__main__':run()
