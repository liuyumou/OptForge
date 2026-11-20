"""Prospective image-v9 lifetime bounds; historical capacity formulas stay intact."""
import math
from lp_billion_campaign import capacity, GIB


def bounded_capacity(model, lane):
    old=capacity(model,lane,borrowed_operator=True)
    m,n,z=(model[k] for k in ['rows','columns','nonzeros'])
    dim=m+n
    tiles=model['canonical_tiles'] if lane=='fp4x2' else 0
    residual=z-model['covered_nnz'] if tiles else z
    halves=(m+15)//16+(n+15)//16
    # At most two half tiles per canonical tile in each orientation, components=2.
    # Exact-length output arrays: fragments, exponents, columns, offsets, coverage,
    # and the original FP64 residuals in both orientations.
    packed=2096*tiles+8*dim+4*(halves+4)+24*residual if tiles else 0
    resident=40*z+56*m+84*n
    count_scratch=24*((n+31)//32)+32
    packing_scratch=count_scratch+(8*n+8*halves+(8<<20) if tiles else 4*n)
    preparation=resident+packed+packing_scratch
    # Matrix/Vector initializers can retain several zero temporaries within one
    # Rust struct expression. Account for all of them; conversion uses <=32 MiB.
    upload=resident+packed+32*max(m,n)+(32<<20)
    ncap=1<<max(1,n).bit_length();mcap=1<<max(1,m).bit_length()
    workspace=14*max(m,n)+16*ncap+8*mcap
    certificate=max(48*dim+8*m,24*ncap+24*n+128)
    repaired_witness=8*m
    solve=resident+32*dim+workspace+8*dim+certificate+repaired_witness
    independent=24*z+28*m+48*n+8*dim+certificate+repaired_witness
    # CPU fallback clones PreparedMatrix while its geometrically grown values
    # are still live. Include its scale copies and original scaled objective.
    nzcap=1<<(max(1,z)-1).bit_length()
    cpu_construction=resident+16*nzcap+16*dim+8*n
    # Pock uses one Vec per original row/column, with at most doubled term
    # capacity (and minimum capacity four), plus descriptors and allocation
    # headers. Include fixed-tree reduction scratch even for a single long line.
    cpu_pock=56*z+108*m+128*n+16*((z+1023)//1024)+65536
    cpu_spectral=resident+workspace+8*n+8*ncap+8*max(ncap,mcap)+16*((z+1023)//1024)+65536
    gpu_preparation=resident+32*dim+(32<<20)
    stages=dict(cpu_construction=cpu_construction,cpu_pock=cpu_pock,cpu_spectral=cpu_spectral,
                gpu_preparation=gpu_preparation,preparation=preparation,device_upload=upload,
                solve_and_certificate=solve,independent_final_check=independent)
    host=max(stages.values())+8*GIB
    result=dict(old,formula_version=5,host_bytes=host,host_gib=math.ceil(host/GIB),
        admitted=host<=128*GIB and old['device_bytes']<=80*GIB and old['physical_fragment_index_upper']<2**32,
        peak_stage=max(stages,key=stages.get),stage_live_bytes=stages,internal_allowance_bytes=8*GIB,
        packed_bytes_upper=packed,packing_scratch_bytes_upper=packing_scratch,
        CPU_preparation_host_gib=math.ceil((max(preparation,cpu_construction,cpu_pock,cpu_spectral)+8*GIB)/GIB),
        host_packed_released_before_control=True,strict_checker_unchanged=True)
    result['reason']=None if result['admitted'] else 'complete host/device/index allowance exceeds approved ceiling'
    return result
