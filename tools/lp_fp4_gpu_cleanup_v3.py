"""Final supervised CPU-only cleanup audit of the completed pilot."""
import subprocess
from lp_fp4_gpu_common import ROOT, BASE, load, put, ref, require
from lp_fp4_gpu_delivery_v3 import verify_manifest, resources


def main():
    for version in (1, 2, 3):
        verify_manifest(ROOT / f'artifacts/gpup-fp4-gpu-pilot-v{version}/manifest.json')
    account = resources()
    unsettled = [r for r in account['resources'] if r['settlement'] is None]
    require(len(unsettled) == 1 and unsettled[0]['reservation']['path'].endswith('final-cleanup-v3.reservation.json'), 'unexpected unsettled job')
    require(all(r['cleanup_empty'] for r in account['resources'] if r['settlement']), 'prior cleanup not empty')
    require(load(ROOT / 'docs/benchmarks/data/fp4-gpu-pilot-acceptance-v3.json')['status'] == 'passed', 'delivery acceptance')
    inventory = subprocess.check_output(['nvidia-smi', '--query-compute-apps=pid,process_name,used_gpu_memory', '--format=csv,noheader'], text=True)
    subprocess.run(['/opt/conda/bin/python3', '-B', 'tools/build_docs.py'], cwd=ROOT, check=True)
    subprocess.run(['git', 'diff', '--check'], cwd=ROOT, check=True)
    subprocess.run(['git', 'diff', '--cached', '--check'], cwd=ROOT, check=True)
    put(BASE / 'cleanup-v3.json', dict(status='passed', prior_jobs_settled=True,
        prior_supervisor_cleanup_empty=True, device_process_inventory=inventory,
        final_active_reservation=unsettled[0]['reservation'], resources=account,
        acceptance=ref(ROOT / 'docs/benchmarks/data/fp4-gpu-pilot-acceptance-v3.json')))
    print('All prior jobs settled; supervisor cleanup empty; final docs/diff/source checks passed.')


if __name__ == '__main__':
    main()
