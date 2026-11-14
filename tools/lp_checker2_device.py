"""Fresh same-image arithmetic/lifecycle admission for CPU-only changes."""
from lp_checker2_common import BASE, ROOT, PRIOR, IMAGE, load, put, ref, require
from lp_checker2_study import CANDIDATE
import lp_mixed2_fp4_transport as fp4_transport
import lp_mixed2_reuse_transport as reuse_transport
import lp_mixed2_fp4_device as device
import lp_mixed2_fp4_acceptance as process
import lp_mixed2_reuse_admit as reuse

def run():
    require(load(BASE/'resources/native-final.settlement.json')['status']=='passed','fresh native gate')
    require(load(BASE/'cpu-optimized/result.json')['binary']==ref(CANDIDATE),'CPU binary identity')
    prior=load(PRIOR/'confirmation-freeze.json')
    require(prior['image']==ref(IMAGE),'device image differs')
    for name in ['device.rs','policy.rs','config.rs']:
        require((ROOT/'research/lp-mixed2-reuse/src'/name).read_bytes()==(ROOT/'research/lp-mixed2-checker2/src'/name).read_bytes(),'device configuration differs')
    for item in prior['admissions']:require(ref(ROOT/item['path'])==item,'retained admission differs')
    fp4_transport.BINARY=reuse_transport.BINARY=device.BINARY=process.BINARY=reuse.BINARY=CANDIDATE
    device.run(BASE/'device-optimized',IMAGE,BASE/'cpu-optimized/original-cpu')
    process.processes(BASE/'process-optimized')
    reuse.invalid(BASE/'invalid-optimized')
    reuse.recovery(BASE/'recovery-optimized')
    put(BASE/'device-admission-optimized.json',dict(status='passed',binary=ref(CANDIDATE),image=ref(IMAGE),
        original_image_admissions=prior['admissions'],fresh=[ref(BASE/n/'result.json') for n in ['device-optimized','process-optimized','invalid-optimized','recovery-optimized']],
        reuse_basis='Exact CUDA image, device ownership code, numerical solve and policy; CPU preparation/assessment independently admitted'))
if __name__=='__main__':run()
