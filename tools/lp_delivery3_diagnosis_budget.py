"""Separate CPU-only retained-record diagnosis; reuse the unchanged supervisor."""
import argparse
import shutil
from lp_delivery3_common import ROOT, NS, load, put, ref, require
import lp_delivery3_budget as budget

BASE = ROOT / 'artifacts/gpup-delivery3-diagnosis-v1'
CAPS = dict(implementation=2000, native=4000, reporting=1500, cleanup=500)
budget.CPU_CAPS = CAPS
budget.GPU_CAPS = {}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--id', required=True)
    p.add_argument('--phase', choices=CAPS, required=True)
    p.add_argument('--seconds', type=int, required=True)
    p.add_argument('command', nargs=argparse.REMAINDER)
    a = p.parse_args()
    command = a.command[1:] if a.command[:1] == ['--'] else a.command
    require(command, 'command required')
    budget.admission_open(BASE)
    snapshot = BASE / 'diagnosis-sources' / a.id
    snapshot.mkdir(parents=True, exist_ok=False)
    sources = list((ROOT / 'tools').glob('lp_delivery3_diagnos*.py'))
    sources += list((ROOT / 'tests/integration').glob('test_lp_delivery3_diagnos*.py'))
    sources += [ROOT / 'docs/plans/lp-delivery3-diagnosis.md']
    bindings = []
    for source in sources:
        dest = snapshot / source.relative_to(ROOT)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, dest)
        bindings.append(ref(dest))
    put(snapshot / 'manifest.json', dict(sources=bindings))
    result = budget.run(a.id, a.phase, a.seconds, False, command, base=BASE)
    print(result, flush=True)
    return 0 if result['status'] == 'passed' else 2


if __name__ == '__main__':
    raise SystemExit(main())
