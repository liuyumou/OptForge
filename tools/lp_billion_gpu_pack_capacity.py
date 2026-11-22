"""Prospective bounds for isolated image-v10 GPU packing and unchanged checking."""
import math
from lp_billion_memory_bounds_final import bounded_capacity as previous
GIB=1<<30

def capacity(model):
    old=previous(model,'fp4x2')
    m,n,z=(model[k] for k in ['rows','columns','nonzeros']);tiles=model['canonical_tiles'];dim=m+n
    # Host keeps immutable originals/engine plus canonical Packed. Geometry and
    # downloads add only axes/tiles, not another full nonzero permutation.
    # Exact-length vectors are bounded by twice requested capacity where Rust may
    # grow them; residual downloads create one final Vec per orientation.
    stages=dict(old['stage_live_bytes'])
    stages['gpu_packing']=40*z+56*m+84*n+old['packed_bytes_upper']+32*dim+96*tiles+(64<<20)
    host=max(stages.values())+8*GIB
    base=24*z+4*(dim+2)+8*((m+31)//32)+64
    # Matches the conservative Rust pre-allocation bound, components=2, compact.
    packing=base if not tiles else base+24*z+12*(dim+2)+40*tiles+8*(256*tiles+4*tiles+2*tiles)+1024
    device=max(old['device_bytes'],packing)
    return dict(old,formula_version=7,stage_live_bytes=stages,host_bytes=host,host_gib=math.ceil(host/GIB),
        device_bytes=device,device_gib=math.ceil(device/GIB),gpu_packing_bytes_upper=packing,
        peak_stage=max(stages,key=stages.get),admitted=host<=128*GIB and device<=80*GIB and old['physical_fragment_index_upper']<2**32,
        reason=None if host<=128*GIB and device<=80*GIB else 'complete GPU packing capacity exceeds approved ceiling')
