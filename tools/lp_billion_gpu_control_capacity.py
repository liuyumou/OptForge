"""Conservative combined live allocation for resident control and feasibility."""
import math
from lp_billion_gpu_pack_capacity import capacity as previous
GIB=1<<30

def capacity(model):
    old=previous(model);m,n,z=(model[k] for k in ['rows','columns','nonzeros'])
    support=8*max(z,1)+16*max(m,1)+16*max(n,1)+16*max((max(m,n)+1023)//1024,1)+24
    # Scaled matrices, iterates, anchors, products and extrapolation scratch are
    # borrowed on the same stream. Original CSR values and bounds are resident.
    # Only one bounded <=8 MiB host range-upload scratch is newly live.
    stages={k:v+(16<<20) for k,v in old['stage_live_bytes'].items()}
    host=max(stages.values())+8*GIB
    device=old['device_bytes']+support
    admitted=host<=128*GIB and device<=80*GIB and old['physical_fragment_index_upper']<2**32
    return dict(old,formula_version=8,stage_live_bytes=stages,host_bytes=host,host_gib=math.ceil(host/GIB),
        device_bytes=device,device_gib=math.ceil(device/GIB),gpu_control_extra_bytes=support,
        peak_stage=max(stages,key=stages.get),admitted=admitted,
        reason=None if admitted else 'combined resident control/feasibility capacity exceeds ceiling')
