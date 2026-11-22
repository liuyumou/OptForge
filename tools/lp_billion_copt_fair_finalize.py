"""Retain the final missing response and finish CPU-only audits and reporting."""
import argparse
from lp_billion_common import BASE, ROOT, NS, CPU_CAPS, load, put, ref, resolve, require
from lp_billion_budget import accounting, run
from lp_billion_prepare_continue import completed, job
from lp_confirmation2_supervisor import same_process
from lp_billion_copt_fair_run import PYTHON, cleanup
import lp_billion_copt_fair_headroom as headroom
import lp_billion_copt_fair_degenerate_tail as tail

CELL = 'copt-fair-1b-v1-degenerate-project'
PLAN = BASE / 'copt-fair-finalization-v1/plan.json'
PROTOCOL = ROOT / 'docs/specifications/SPEC-0046-amendment-90.md'


def prepare():
    require(not PLAN.exists(), 'fresh finalization plan')
    frozen = load(headroom.MANIFEST); resolve(frozen['resumption_source'])
    require(all(c['status'] != 'pending' or (BASE/'resources'/(c['id']+'.settlement.json')).exists() for c in frozen['cells']),
            'all admitted scientific cells attempted and settled')
    path = BASE/'resources'/(CELL+'.settlement.json'); receipt = load(path)
    require(receipt['status']=='refused' and not receipt['overrun'] and not receipt['cleanup_empty'], 'exact retained final failure')
    require(not (BASE/CELL/'response.json').exists() and (BASE/CELL/'stdout.jsonl').stat().st_size == 0, 'missing endpoint remains missing')
    journal = path.with_name(CELL+'.cpu-journal.json'); resource = resolve(receipt['resource']); identities = {}
    def collect(value):
        if isinstance(value, dict):
            if 'pid' in value and 'start_ticks' in value: identities[(value['pid'],value['start_ticks'])]=value
            for child in value.values(): collect(child)
        elif isinstance(value, list):
            for child in value: collect(child)
    collect(load(resource)); collect(load(journal))
    require(identities and not any(same_process(p) for p in identities.values()), 'every exact owned final-attempt identity gone')
    disposition = path.with_name(CELL+'.cleanup-disposition.json'); require(not disposition.exists(), 'fresh additive cleanup evidence')
    put(disposition, dict(status='cleanup_verified', settlement=ref(path), resource=ref(resource), journal=ref(journal),
        identities=list(identities.values()), admission_job='operational-gpu-v28', cpu_admission_job='operational-cpu-v36',
        protocol=ref(PROTOCOL), original_receipt_unchanged=True, preceding_trigger='unknown; retained receipt records cleanup_incomplete'))
    c, _ = accounting(); reserve = dict(reporting=22000, cleanup=480)
    require(all(c[k]+v*NS<=CPU_CAPS[k]*NS for k,v in reserve.items()), 'complete CPU-only finalization envelope')
    put(PLAN, dict(status='cpu_only_finalization', source=ref(__file__), protocol=ref(PROTOCOL),
        manifest=ref(headroom.MANIFEST), previous_driver=ref(tail.PLAN), failed_cell=ref(path),
        cleanup_disposition=ref(disposition), reservation_cpu_seconds=reserve, no_additional_lp_attempt=True))


def prune():
    frozen = load(headroom.MANIFEST)
    require(all(c['status']!='pending' or completed(c['id']+'-full-audit') for c in frozen['cells']), 'entire roster audit dispositions complete')
    cleanup('1b', 'degenerate')
    root = BASE/'objects'; deleted = []
    for path in sorted(root.iterdir()):
        if path.suffix != '.bin' or path.stat().st_size < 8<<20: continue
        require(not path.is_symlink() and path.resolve().parent==root.resolve() and len(path.stem)==64
                and all(c in '0123456789abcdef' for c in path.stem), 'exact task-owned large content object')
        deleted.append(dict(name=path.name, bytes=path.stat().st_size)); path.unlink()
    put(BASE/'copt-fair-final-large-object-prune-v1.json', dict(status='obsolete_completed_and_failed_attempt_large_objects_deleted',
        deleted=deleted, released_bytes=sum(p['bytes'] for p in deleted), source=ref(__file__), protocol=ref(PROTOCOL),
        all_small_results_and_failures_preserved=True, replay_requires_regeneration=True))


def execute():
    plan = load(PLAN); resolve(plan['source']); frozen = load(resolve(plan['manifest']))
    require(not (PLAN.parent/'started.json').exists(), 'never repeat finalization driver')
    put(PLAN.parent/'started.json', dict(plan=ref(PLAN)))
    index = next(i for i,c in enumerate(frozen['cells']) if c['id']==CELL)
    cell = frozen['cells'][index]
    result = run(CELL+'-full-audit','reporting',cell['audit_seconds'],False,
        [str(PYTHON),'-B',str(resolve(frozen['audit'])),str(headroom.MANIFEST),str(index)],64,0,1)
    print(dict(audit=CELL,settlement=result),flush=True); require(result['status']=='passed','retained missing-response audit')
    job('copt-fair-prune-1b-degenerate-v1',120,[str(PYTHON),'-B',__file__,'prune'],phase='cleanup',host=8)
    for path in [PLAN.parent/'completed.json',tail.PLAN.parent/'completed.json',headroom.MANIFEST.parent/'completed.json',
                 headroom.previous.MANIFEST.parent/'completed.json',headroom.previous.ORIGINAL.parent/'completed.json']:
        require(not path.exists(),'fresh completed outcome marker')
        put(path,dict(status='all_attempted_outcomes_and_audit_dispositions_retained',effective_freeze=ref(headroom.MANIFEST),finalization=ref(PLAN)))
    job('copt-fair-complete-report-v1',180,[str(PYTHON),'-B',str(ROOT/'tools/lp_mixed2_reuse_place.py'),str(PYTHON),'-B',
        str(ROOT/'tools/lp_billion_copt_fair_headroom.py'),'report'],phase='reporting',host=8)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['prepare','prune','execute'])
    globals()[parser.parse_args().action]()
