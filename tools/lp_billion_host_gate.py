"""Read-only physical capacity snapshot for all eighteen original billion-NNZ cells."""
import argparse
import time
from pathlib import Path
from lp_billion_common import BASE,DEVICE,load,put,ref,require
from lp_billion_campaign import capacity
from lp_billion_generate import FAMILIES
from lp_billion_idle import Nvml
from lp_billion_availability import idle


def snapshot(identity, version=3):
    require(identity and Path(identity).name==identity and identity not in ['.','..'],'capacity snapshot identity')
    started=time.monotonic_ns()
    memory={line.split(':',1)[0]:int(line.split()[1])*1024
            for line in Path('/proc/meminfo').read_text().splitlines()
            if line.startswith(('MemTotal:','MemAvailable:','Shmem:'))}
    sensor=Nvml()
    try:gpu=sensor.sample()
    finally:sensor.close()
    cells=[]
    for family in FAMILIES:
        path=BASE/f'models-1b-{family}-v1/result.json';model=load(path)
        require(model['nonzeros']==1_000_000_000,'one billion original matrix nonzeros')
        for lane in ['native','fp32','fp4x2']:
            allocation=capacity(model,lane,borrowed_operator=version>=4)
            host_required=(allocation['host_gib']+4)<<30
            device_required=(allocation['device_gib']+2)<<30
            cells.append(dict(family=family,lane=lane,model=ref(path),capacity=allocation,
                host_required_bytes=host_required,host_available=memory['MemAvailable']>=host_required,
                device_required_bytes=device_required,device_available=gpu['free']>=device_required))
    count=sum(c['host_available'] for c in cells)
    status='host_headroom_available' if count==len(cells) else 'partial_host_headroom' if count else 'host_headroom_unavailable'
    put(BASE/(identity+'.json'),dict(status=status,started_ns=started,finished_ns=time.monotonic_ns(),
        image_version=version,device=DEVICE,gpu=gpu,instantaneous_gpu_idle=idle(gpu),memory=memory,cells=cells,
        minimum_host_required_bytes=min(c['host_required_bytes'] for c in cells),
        all_cells_host_required_bytes=max(c['host_required_bytes'] for c in cells),
        source=ref(__file__),capacity_source=ref(Path(__file__).with_name('lp_billion_campaign.py')),
        cuda_context_created=False,device_configuration_changed=False,other_processes_signalled=False,
        limitation='Container-visible instantaneous physical capacity only; no GPU reservation, final scientific freeze or sustained-idle admission is implied.'))
    print(dict(status=status,host_available_gib=memory['MemAvailable']/2**30,
               host_admissible_cells=count,total_cells=len(cells),gpu_idle=idle(gpu)),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--id',required=True)
    parser.add_argument('--version',type=int,choices=[3,4,5,6,7],default=3)
    args=parser.parse_args();snapshot(args.id,args.version)
