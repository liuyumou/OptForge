"""Prepared source-bound native gate; run only after native-recovery approval."""
import os
import subprocess
import sys
from benchmark_lp import source_identity
from lp_protocol import ROOT, read_json, write_json
from lp_tensor_warp32_common import BASE
from lp_tensor_warp32_compile import child_environment


def main():
    os.environ.update(child_environment(os.environ))
    os.environ['CUDA_VISIBLE_DEVICES'] = ''
    os.environ.pop('AI_OPTIMIZER_GPU', None)
    os.environ.pop('AI_OPTIMIZER_GPU_LEASE', None)
    subprocess.run(['bash', str(ROOT / 'tools/check.sh')], cwd=ROOT, check=True)
    gate = read_json(ROOT / 'target/lp-native-gate.json')
    if not gate['native'] or gate['source_tree_sha256'] != source_identity():
        raise ValueError('exact final-source native gate required')
    write_json(BASE / 'native-gate-v2.json', gate)
    subprocess.run([sys.executable, '-u', str(ROOT / 'tools/lp_tensor_warp32_inventory.py')],
                   cwd=ROOT, check=True)
    if read_json(ROOT / 'target/lp-tensor-warp32-binaries.json')['source_tree_sha256'] != gate['source_tree_sha256']:
        raise ValueError('compile-only test inventory source differs')
    print('Complete final-source native gate and compile-only inventory pass; zero GPU work', flush=True)


if __name__ == '__main__':
    main()
