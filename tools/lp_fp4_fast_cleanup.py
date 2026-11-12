"""Final CPU-only evidence, documentation and process-cleanup audit."""
import py_compile
import subprocess
from lp_fp4_fast_common import ROOT, BASE, load, put, ref, checked, require
from lp_fp4_fast_delivery import resources
from lp_fp4_gpu_delivery_v3 import verify_manifest
from lp_fp4_fast_study import STUDY


def main():
    for version in (1,2,3):verify_manifest(ROOT/f'artifacts/gpup-fp4-gpu-pilot-v{version}/manifest.json')
    m=load(STUDY/'manifest.json')
    for item in m['sources']+[m['image'],m['binary'],m['build'],m['admission'],m['grid_cpu'],m['inventory']]:checked(item)
    require(load(ROOT/'docs/benchmarks/data/fp4-fast-acceptance-v1.json')['status']=='passed','delivery acceptance required')
    account=resources();pending=[r for r in account['resources'] if not r['settlement']]
    require(len(pending)==1 and pending[0]['reservation']['path'].endswith('final-cleanup-v2.reservation.json'),'unexpected unsettled reservation')
    for path in list((ROOT/'tools').glob('*fp4_fast*.py'))+[ROOT/'tests/integration/test_lp_fp4_fast.py']:
        py_compile.compile(str(path),doraise=True)
    exception=load(ROOT/'docs/benchmarks/data/fp4-fast-hygiene-v1.json');source=checked(exception['source'])
    lines=[i for i,line in enumerate(source.read_bytes().splitlines(),1) if line and line[-1:] in (b' ',b'\t')]
    require(lines==exception['blank_only_lines'] and all(not source.read_bytes().splitlines()[i-1].strip() for i in lines),'whitespace exception widened')
    require(load(ROOT/'docs/benchmarks/data/fp4-fast-projection-boundaries-v1.json')['status']=='passed','projection boundary admission')
    for cmd in [['python3','tools/validate_artifacts.py'],['python3','tools/build_docs.py'],['cargo','fmt','--manifest-path','research/lp-fp4-fast/Cargo.toml','--','--check'],['git','diff','--check'],['git','diff','--cached','--check','--','.',':(exclude)research/lp-fp4-fast/cuda/fast.cu'],['git','-c','core.whitespace=-blank-at-eol','diff','--cached','--check','--','research/lp-fp4-fast/cuda/fast.cu']]:
        subprocess.run(cmd,cwd=ROOT,check=True)
    inventory=subprocess.check_output(['nvidia-smi','--query-compute-apps=pid,process_name,used_gpu_memory','--format=csv,noheader'],text=True)
    put(BASE/'cleanup-v2.json',dict(status='passed',prior_jobs_settled=True,prior_supervisor_cleanup_empty=True,device_process_inventory=inventory,active_final_reservation=pending[0]['reservation'],hygiene_exception=ref(ROOT/'docs/benchmarks/data/fp4-fast-hygiene-v1.json'),projection_boundaries=ref(ROOT/'docs/benchmarks/data/fp4-fast-projection-boundaries-v1.json'),study_manifest=ref(STUDY/'manifest.json'),acceptance=ref(ROOT/'docs/benchmarks/data/fp4-fast-acceptance-v1.json')))
    print('Historical and final evidence exact; artifacts/docs/format/diff checks pass; prior cleanup empty.')

if __name__=='__main__':main()
