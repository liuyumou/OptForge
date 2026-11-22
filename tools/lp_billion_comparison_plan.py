"""Source-bound prospective roster; never executes or freezes unsupported LP cells."""
import argparse
from pathlib import Path
from lp_billion_common import BASE, ROOT, put, load, ref, resolve, require
from lp_billion_generate import FAMILIES
from lp_billion_campaign import capacity
from lp_billion_copt import installation


def plan(identity, capacity_path):
    observation=load(capacity_path)
    available=observation['memory']['MemAvailable']
    admission=load(BASE/'copt-native-cpu-v2/result.json')
    require(admission['status']=='passed' and len(admission['cases'])==12, 'native COPT CPU admission')
    require(load(BASE/'resources/copt-native-cpu-v2.settlement.json')['status']=='passed','supervised COPT admission')
    require(admission['adapter']==ref(ROOT/'tools/lp_billion_copt.py') and admission['installation']==installation(),'current admitted COPT source/library')
    cells=[]
    for family in FAMILIES:
        model_path=BASE/f'models-1b-{family}-v1/result.json'
        model=load(model_path);resolve(model['model'])
        require(model['nonzeros']==1_000_000_000,'original billion matrix')
        for lane in ['native','fp32','fp4x2','copt-cpu-auto','copt-gpu-pdlp']:
            ours=not lane.startswith('copt')
            full=capacity(model,lane,borrowed_operator=True) if ours else None
            required=(full['host_gib']+4)<<30 if full else None
            blockers=['timing_image_gpu_and_four_sanitizers_pending'] if ours else ['native_COPT_billion_peak_memory_unadmitted']
            if ours and available<required:blockers.append('physical_host_headroom')
            if not ours and lane.endswith('gpu-pdlp'):blockers.append('native_COPT_GPU_ownership_and_capacity_unadmitted')
            # This lower bound excludes vendor internal storage, conversion peaks,
            # vectors, checker storage, context and mandatory physical headroom.
            array_lower=24*model['nonzeros']+4*(model['rows']+model['columns']+2)
            cells.append(dict(family=family,lane=lane,model=ref(model_path),original_nonzeros=model['nonzeros'],
                status='unfrozen_unexecuted',blocking_conditions=blockers,host_capacity=full,
                host_required_with_headroom_bytes=required,
                copt_two_sparse_arrays_lower_bound_bytes=None if ours else array_lower,
                complete_cost_ns=None,strict_certified=None))
    require(len(cells)==30,'full six-family five-lane roster')
    put(BASE/(identity+'.json'),dict(status='prospective_not_frozen',cells=cells,
        capacity_observation=ref(capacity_path),copt_cpu_admission=ref(BASE/'copt-native-cpu-v2/result.json'),
        timing_image=ref(BASE/'image-v8/binding.json'),protocol=ref(ROOT/'docs/specifications/SPEC-0046-amendment-30.md'),
        strict_original_model_tolerance=1e-9,control_interval=100,certificate_interval=500,
        common_update_ceiling=None,common_solver_wall_seconds=None,billion_solves=0,
        future_freeze='Largest common 500-update increment up to 5000 fitting every solve, final check, intermediate audit, repaired witness and storage reservation; vendor iterations remain distinct.',
        complete_time='Fresh solver process plus response persistence and independent final checking; offline intermediate audits separate.',
        preparation_comparison='Report original input/hash/model construction separately from solver preparation; include both in complete cost. COPT CSR-to-CSC belongs to import, project original transpose belongs to input.',
        copt_internal_phases='Presolve/scaling/iterations inside native solve call are opaque; vendor SolvingTime is nested, not added again.',
        gpu_timing='Host wall at existing stream synchronization boundaries; not kernel-active time.',
        native_copt_current_limit='CPU adapter admitted only on small models with 12000 MB soft MemLimit; billion host allowance and GPU API remain unadmitted.',
        no_scientific_cell_started=True,no_cuda_context_created=True))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--id',required=True);p.add_argument('--capacity',type=Path,required=True)
    a=p.parse_args();plan(a.id,a.capacity)
