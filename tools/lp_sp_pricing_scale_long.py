"""Fresh third-seed, longer-window supplement; never retries an existing LP."""
import argparse
import datetime as dt
import json
from pathlib import Path
import time
from lp_sp_pricing_budget import ROOT, BASE, NS, put, binding
from lp_sp_pricing_gpu_opt_compare import read, verify
from lp_sp_pricing_scale_experiment import STUDY as PRIMARY, SPECS, generate, validate as primary
from lp_sp_pricing_baselines import PYTHON, images, audit, copt
from lp_sp_pricing_geometry_copt_auto import child as automatic
from lp_sp_pricing_scale_budget import allocation
from lp_billion_owned_process import execute

STUDY = BASE/'scale-long-v1'
SEED = 122419


def freeze():
    original = primary(); allocation(); STUDY.mkdir(exist_ok=False)
    models, cells = [], []
    for i, spec in enumerate(s for s in SPECS if s['name'] in ('dense-16m', 'sparse-scaled-10m', 'mixed-tall-4m')):
        models.append(generate(spec, SEED, STUDY/'models'/f"{spec['name']}-{SEED}"))
        lanes = ['candidate', 'copt-gpu'] if i % 2 == 0 else ['copt-gpu', 'candidate']
        for lane in lanes+['copt-auto']:
            cells.append(dict(id=f"{spec['name']}-{SEED}-{lane}", model_index=i,
                              family=spec['name'], seed=SEED, lane=lane, group=2))
    put(STUDY/'freeze.json', dict(status='frozen', primary=binding(PRIMARY/'freeze.json'),
        models=models, cells=cells, native_seconds=300, process_seconds=360,
        gpu_reservation_seconds=2220, auto_reservation_seconds=1140,
        independent_audit_process_seconds=240, sources=original['sources']+[binding(__file__)],
        images=images(), wall_deadline_utc=allocation()['wall_deadline_utc'],
        disclosure='Added after first GPU group and first 4M automatic-CPU result were visible; fixed three larger/rectangular families, fresh third seed, unchanged candidate and vendor settings, only native/process windows increased; no historical LP repeated.',
        limitations=original['limitations']+['supplement has 300-second windows and partial third-seed family coverage; do not pool timing medians with 120-second cohort']))
    print(json.dumps(dict(status='frozen', models=len(models), cells=len(cells))), flush=True)


def validate():
    primary(); f = read(STUDY/'freeze.json'); verify(f['primary'])
    for s in f['sources']:
        verify(s)
    for m in f['models']:
        verify(m['model']); verify(m['construction_audit'])
    if images() != f['images']:
        raise RuntimeError('baseline/checker image changed')
    return f


def run(kind):
    f = validate()
    selected = [c for c in f['cells'] if (c['lane'] == 'copt-auto') == (kind == 'auto')]
    for cell in selected:
        m = f['models'][cell['model_index']]; out = STUDY/'runs'/cell['id']
        out.mkdir(parents=True, exist_ok=False)
        left = (dt.datetime.fromisoformat(f['wall_deadline_utc'])-dt.datetime.now(dt.timezone.utc)).total_seconds()
        if left < f['process_seconds']+600:
            put(out/'unattempted.json', dict(reason='campaign_wall_envelope', remaining_seconds=left)); continue
        if cell['lane'] == 'candidate':
            cmd = [str(PYTHON), '-B', str(ROOT/'tools/lp_sp_pricing_scale_run.py'), m['model']['path'],
                   str(out/'response.json'), '--seconds', str(f['native_seconds'])]
        else:
            cmd = [str(PYTHON), '-B', __file__, 'vendor', '--lane', cell['lane'],
                   '--model', m['model']['path'], '--output', str(out)]
        put(out/'started.json', dict(command=cmd, cell=cell, model=m['model']))
        proc = execute(cmd, out/'stdout', out/'stderr', f['process_seconds'], None)
        put(out/'process.json', proc); print(json.dumps(dict(cell=cell['id'], process=proc)), flush=True)
    put(STUDY/f'{kind}-completed.json', dict(status='all_slots_disposed'))


def vendor(lane, model, out):
    f = validate()
    if lane == 'copt-gpu':
        copt(model, out, f['native_seconds'])
    elif lane == 'copt-auto':
        automatic(model, out, f['native_seconds'])
    else:
        raise ValueError('vendor lane')


def audits():
    f = validate()
    for kind in ('gpu', 'auto'):
        if read(STUDY/f'{kind}-completed.json')['status'] != 'all_slots_disposed':
            raise RuntimeError('unfinished solver group')
    rows = []
    for cell in f['cells']:
        m = f['models'][cell['model_index']]; out = STUDY/'runs'/cell['id']
        if (out/'unattempted.json').exists():
            rows.append(dict(**cell, status='unattempted_wall_budget', strict_accepted=False,
                             independent_exact_accepted=False, timely=False)); continue
        proc = read(out/'process.json'); path = out/'response.json'
        response = read(path) if path.exists() else {}
        strict = audit('copt_scale_off', Path(m['model']['path']), Path(m['model']['path']), out)
        start = time.perf_counter_ns(); proof_path = out/'independent-exact.json'
        if path.exists() and (response.get('certificate') or response.get('endpoint')):
            cmd = [str(PYTHON), '-B', str(ROOT/'tools/lp_sp_pricing_scale_verify.py'),
                   m['model']['path'], str(path), str(proof_path), '--seconds', '210']
            audit_proc = execute(cmd, out/'independent-stdout', out/'independent-stderr',
                                 f['independent_audit_process_seconds'], None)
            put(out/'independent-process.json', audit_proc)
            exact = read(proof_path) if audit_proc['returncode'] == 0 and not audit_proc['timed_out'] and proof_path.exists() else dict(accepted=False, reason='independent_audit_process_failed')
        else:
            exact = dict(accepted=False, reason='no_endpoint'); put(proof_path, exact)
        independent_ns = time.perf_counter_ns()-start
        native = response.get('solve_ns', response.get('native_ns'))
        timely = bool(proc['returncode'] == 0 and not proc['timed_out'] and native is not None and native <= f['native_seconds']*NS)
        if response.get('audit', {}).get('accepted') and not exact.get('accepted'):
            raise ArithmeticError('native accepted candidate not independently exact')
        if exact.get('accepted') and not strict['accepted']:
            raise ArithmeticError('exact endpoint not accepted by unchanged strict checker')
        row = dict(**cell, model=f"{m['name']}-{m['seed']}", nonzeros=m['nonzeros'],
            status=response.get('status', 'missing_response'), reason=response.get('reason'), route=response.get('route'),
            timely=timely, strict_accepted=strict['accepted'], independent_exact_accepted=bool(exact.get('accepted')),
            native_ns=native, process_ns=proc['elapsed_ns'], encoding_ns=m['encoding_ns'],
            strict_audit_ns=strict['elapsed_ns'], independent_audit_ns=independent_ns,
            complete_ns=m['encoding_ns']+proc['elapsed_ns']+strict['elapsed_ns']+independent_ns,
            operational_complete_ns=m['encoding_ns']+proc['elapsed_ns']+strict['elapsed_ns'],
            response=binding(path) if path.exists() else None, strict_audit=binding(out/'audit.json'),
            independent_proof=binding(proof_path) if proof_path.exists() else None, process=binding(out/'process.json'))
        rows.append(row)
        print(json.dumps({k:row[k] for k in ['id', 'status', 'strict_accepted', 'independent_exact_accepted', 'complete_ns']}), flush=True)
    put(STUDY/'audits.json', dict(status='all_supplement_endpoints_checked', rows=rows))


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('action', choices=['freeze', 'run', 'vendor', 'audit'])
    p.add_argument('--kind', choices=['gpu', 'auto']); p.add_argument('--lane')
    p.add_argument('--model', type=Path); p.add_argument('--output', type=Path); args = p.parse_args()
    if args.action == 'freeze': freeze()
    elif args.action == 'run': run(args.kind)
    elif args.action == 'vendor': vendor(args.lane, args.model, args.output)
    else: audits()
