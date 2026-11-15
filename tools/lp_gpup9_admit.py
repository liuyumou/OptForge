"""Fresh native/CPU/device/process/recovery admission; historical sources stay exact."""
import argparse
import os
import subprocess
from lp_gpup9_common import BASE, ROOT, BINARY, IMAGE, load, put, ref, checked, require


def cpu():
    import lp_mixed2_fp4_cpu as cpu_module
    cpu_module.BINARY=BINARY
    cpu_module.run(BASE/'cpu')
    # These are the exact final, admitted CHECKER2 source and image bindings.
    old=load(ROOT/'artifacts/gpup-checker2-v1/freeze.json')
    require(old['binaries']['candidate']==ref(BINARY) and old['image']==ref(IMAGE),'selected implementation differs')
    for item in old['sources']:
        if item['path'].startswith(('research/','crates/')):checked(item)
    for item in old['admissions']:checked(item)
    require('avx512f' in open('/proc/cpuinfo').read(),'x86-64-v4 unsupported')
    put(BASE/'cpu-admission.json',dict(status='passed',binary=ref(BINARY),image=ref(IMAGE),
        retained_freeze=ref(ROOT/'artifacts/gpup-checker2-v1/freeze.json'),cpu=ref(BASE/'cpu/result.json')))


def device():
    require(load(BASE/'resources/native-v1.settlement.json')['status']=='passed','fresh full native gate')
    require(load(BASE/'cpu-admission.json')['binary']==ref(BINARY),'fresh CPU binary admission')
    import lp_mixed2_fp4_transport as fp4_transport
    import lp_mixed2_reuse_transport as reuse_transport
    import lp_mixed2_fp4_device as dev
    import lp_mixed2_fp4_acceptance as process
    import lp_mixed2_reuse_admit as reuse
    fp4_transport.BINARY=reuse_transport.BINARY=dev.BINARY=process.BINARY=reuse.BINARY=BINARY
    dev.run(BASE/'device',IMAGE,BASE/'cpu')
    process.processes(BASE/'process')
    reuse.invalid(BASE/'invalid')
    reuse.recovery(BASE/'recovery')
    put(BASE/'device-admission.json',dict(status='passed',binary=ref(BINARY),image=ref(IMAGE),
        fresh=[ref(BASE/n/'result.json') for n in ['device','process','invalid','recovery']],
        sanitizer_reuse='Identical image, device code, numerical solve and recovery; exact retained four-tool source-bound receipts'))


def finish():
    refs=[]
    for name in ['contracts-v4','native-v1','isolated-v1','cpu-v1','device-v1','pilot-v3','serial-admission-v2']:
        path=BASE/'resources'/(name+'.settlement.json');s=load(path)
        require(s['status']=='passed' and not s['overrun'],'admission failed '+name)
        r=load(checked(s['resource']))
        require(r['guardian_cleanup']['empty'] and r['result']['cleanup']['empty'],'admission cleanup')
        refs.append(ref(path))
    put(BASE/'admission-v2.json',dict(status='passed',binary=ref(BINARY),image=ref(IMAGE),resources=refs,
        native=ref(BASE/'resources/native-v1.settlement.json'),device=ref(BASE/'device-admission.json'),
        pilot=ref(BASE/'pilot-v3/result.json'),serial=ref(BASE/'serial-admission-v2/result.json')))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['cpu','device','finish']);a=p.parse_args();globals()[a.action]()
