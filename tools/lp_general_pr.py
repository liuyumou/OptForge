"""Independent CPU-only integration budget; reuse the admitted supervisor."""
import argparse

import lp_general_budget as budget
from lp_general_common import ROOT, NS

BASE = ROOT / 'artifacts/gpup-general-pr-v1'
CPU_CAPS = dict(implementation=1000, native=8000, research=2000,
                reporting=4000, cleanup=1000)
_accounting = budget.accounting


def accounting(base=BASE):
    cpu, gpu = _accounting(base)
    # Reserve the complete 1000-second publication/closing allowance upfront;
    # the reused ledger already includes 128 seconds of closing administration.
    cpu['cleanup'] += (1000 - 128) * NS
    return cpu, gpu


budget.CPU_CAPS = CPU_CAPS
budget.GPU_CAPS = {}
budget.accounting = accounting


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--id', required=True)
    parser.add_argument('--phase', choices=CPU_CAPS, required=True)
    parser.add_argument('--seconds', type=int, required=True)
    parser.add_argument('command', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ['--'] else args.command
    result = budget.run(args.id, args.phase, args.seconds, False, command, base=BASE)
    print(result, flush=True)
    raise SystemExit(0 if result['status'] == 'passed' else 2)
