"""Run each frozen capacity cell once, with an idle-only reservation per solve."""
import argparse
import math
import sys
from lp_billion_common import BASE, ROOT, load, require
from lp_billion_campaign import freeze
from lp_billion_budget import run


def execute(manifest, indices=None):
    for i, cell in enumerate(load(manifest)['cells']):
        if indices is not None and i not in indices:
            continue
        if cell['status'] != 'pending':
            print(dict(cell=cell['id'], status=cell['status'], memory=cell['memory']), flush=True)
            continue
        memory = cell['memory']
        require(not (BASE/'resources'/(cell['id']+'.reservation.json')).exists(), 'attempted scientific cell cannot repeat')
        disk = math.ceil(memory['endpoint_bytes_upper']/(1 << 30))+1
        result = run(cell['id'], 'development', cell['seconds'], True,
            [sys.executable, '-B', str(ROOT/'tools/lp_billion_campaign.py'), 'worker', str(manifest), str(i)],
            memory['host_gib'], memory['device_gib'], disk)
        print(cell['id'], result, flush=True)
        require(result['status'] == 'passed', 'capacity cell stopped; retain outcome without retry')


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--tag', required=True)
    p.add_argument('--families', nargs='+', required=True)
    p.add_argument('--wall-ms', type=int, required=True)
    p.add_argument('--seconds', type=int, required=True)
    p.add_argument('--version', type=int, choices=[1,2,3], default=1)
    a = p.parse_args()
    paths = [BASE/f'models-{a.tag}-{family}-v1/result.json' for family in a.families]
    manifest = freeze(f'ladder-{a.tag}-v{a.version}', paths, ['fp4x2'], 100, a.wall_ms, a.seconds, ladder=True, version=a.version)
    execute(manifest)
