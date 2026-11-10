"""Two bounded fresh compatibility observations, before baseline lane admission."""
import os
from pathlib import Path
import subprocess
import sys

from lp_baseline_common_v3 import BASE, DEVICE, ROOT, checked, load, put, require


def main():
    kind = sys.argv[1]
    m = load(BASE/'manifest.json')
    require(os.environ.get('AI_OPTIMIZER_GPU_LEASE')=='inherited' and os.environ.get('CUDA_VISIBLE_DEVICES')==DEVICE, 'inherited lease required')
    require(sorted(os.sched_getaffinity(0))==m['cpu_affinity'], 'hardware affinity differs')
    if kind == 'project':
        env={**os.environ,'AI_OPTIMIZER_CUDA_DIR':str(ROOT/m['project_cuda_directory'])}
        p=subprocess.run([str(checked(m['project_binary'])),'gpu','probe','--device',DEVICE],env=env,check=True,capture_output=True,text=True)
        put(BASE/'hardware-project.json',dict(stdout=p.stdout,stderr=p.stderr,device=DEVICE,status='passed'))
    elif kind == 'cuopt':
        # No solve and no fabricated admission: only the pinned driver's context
        # and allocation path. Actual solver/kernel compatibility is a lane gate.
        from cuda.bindings import driver as cuda
        def call(result):
            require(int(result[0])==0, 'CUDA driver call refused: '+str(result[0]))
            return result[1:]
        call(cuda.cuInit(0))
        device, = call(cuda.cuDeviceGet(0))
        uuid, = call(cuda.cuDeviceGetUuid(device))
        context, = call(cuda.cuDevicePrimaryCtxRetain(device))
        try:
            call(cuda.cuCtxSetCurrent(context))
            pointer, = call(cuda.cuMemAlloc(4096))
            call(cuda.cuMemsetD8(pointer,0,4096))
            call(cuda.cuCtxSynchronize())
            call(cuda.cuMemFree(pointer))
        finally:
            call(cuda.cuDevicePrimaryCtxRelease(device))
        put(BASE/'hardware-cuopt.json',dict(status='passed',device=DEVICE,driver_uuid=str(uuid),
            scope='driver context, 4 KiB allocation, memset and synchronization; not solver acceptance'))
    else: raise ValueError('unknown hardware probe')


if __name__=='__main__': main()
