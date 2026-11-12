"""Validate non-executable SPEC-0025 proposals and retained-evidence cost bounds."""

import argparse
from fractions import Fraction
import hashlib
import json
from pathlib import Path

from lp_fp4_contract import ContractError, exact, schema_check
from validate_artifacts import read_json_bytes

ROOT = Path(__file__).resolve().parents[1]
RESULT = 'docs/benchmarks/data/resident2-result-v1.json'
SPEC = 'docs/specifications/SPEC-0025-persistent-fp4-contract.md'
MODEL_IDS = tuple('gpup-development-' + s for s in (
    'small-4', 'irregular-2048', 'dense_block-1024', 'scaling-256',
    'scheduling-20x5')) + tuple('gpup-extension-' + s for s in (
        'irregular-32768', 'dense_block-65536', 'mixed-65536'))
LANES = [dict(id='native', format='fp64', components=1),
         dict(id='fp8-4', format='e4m3', components=4),
         dict(id='fp16-2', format='binary16', components=2)] + [
    dict(id=f'fp4-{k}', format='e2m1', components=k) for k in (2, 4, 8)]
GAIN = Fraction(11, 10)


def read(path):
    with Path(path).open('rb') as stream:
        data = stream.read(32 * 1024 * 1024 + 1)
    if len(data) > 32 * 1024 * 1024:
        raise ContractError('artifact exceeds 32 MiB')
    try:
        return read_json_bytes(data)
    except (ValueError, TypeError) as error:
        raise ContractError(str(error)) from error


def artifact(path):
    path = Path(path)
    return dict(path=path.relative_to(ROOT).as_posix(), sha256=hashlib.sha256(path.read_bytes()).hexdigest())


def verify_reference(reference):
    relative = Path(reference['path'])
    if relative.is_absolute() or '..' in relative.parts or relative.as_posix() != reference['path']:
        raise ContractError('noncanonical repository artifact path')
    path = (ROOT / relative).resolve()
    if not path.is_relative_to(ROOT) or not path.is_file():
        raise ContractError('missing or escaping artifact')
    if hashlib.sha256(path.read_bytes()).hexdigest() != reference['sha256']:
        raise ContractError(f'artifact hash mismatch: {relative}')
    return path


def integer_tree(value):
    """Finite JSON, with schema integer fields checked separately where needed."""
    if isinstance(value, dict):
        for child in value.values():
            integer_tree(child)
    elif isinstance(value, list):
        for child in value:
            integer_tree(child)
    elif type(value) in (int, float):
        exact(value)


def whole(value):
    if type(value) is not int or not 0 <= value <= 2**53 - 1:
        raise ContractError('bounded integer required')
    return value


def retained_rows(reference):
    if reference['path'] != RESULT:
        raise ContractError('unexpected retained control source')
    result = read(verify_reference(reference))
    rows = [row for row in result['rows'] if row['mode'] == 'control' and row['lifecycle'] == 'cold']
    if len(rows) != 24 or len({row['id'] for row in rows}) != 24:
        raise ContractError('incomplete retained cold-control evidence')
    for model in MODEL_IDS:
        selected = [row for row in rows if row['model_id'] == model]
        if (len(selected) != 3 or {row['repetition'] for row in selected} != {0, 1, 2}
                or len({row['model']['sha256'] for row in selected}) != 1):
            raise ContractError('retained model/repetition mismatch')
    return rows


def resource_proposal():
    def stage(entries):
        jobs = [dict(name=name, count=count, wall_seconds=wall,
                     cpu_seconds=4 * wall, gpu_seconds=wall if gpu else 0)
                for name, count, wall, gpu in entries]
        return dict(cpu_seconds=sum(j['count'] * j['cpu_seconds'] for j in jobs),
                    gpu_seconds=sum(j['count'] * j['gpu_seconds'] for j in jobs), jobs=jobs)
    return dict(
        prototype=stage([('cpu-reference', 1, 1000, False), ('native-integration', 1, 2000, False),
                         ('device-admission', 4, 60, True), ('sanitizer', 4, 60, True),
                         ('pilot', 24, 30, True), ('diagnostics', 12, 30, True),
                         ('report', 1, 100, False), ('cleanup', 1, 100, False)]),
        study=stage([('cold', 144, 60, True), ('prepared', 48, 100, True),
                     ('coordination', 1, 200, False), ('report', 1, 200, False),
                     ('cleanup', 1, 100, False)]))


def study_cells(proposal):
    cells = []
    for model in proposal['models']:
        for lifecycle, repetitions, solves in [('cold', 3, 1), ('prepared', 1, 3)]:
            for repetition in range(repetitions):
                lanes = sorted(proposal['lanes'], key=lambda lane: hashlib.sha256(
                    f"17112:{model['id']}:{lifecycle}:{repetition}:{lane['id']}".encode()).digest())
                for lane in lanes:
                    cells.append(dict(model=model['id'], lane=lane['id'], lifecycle=lifecycle,
                                      repetition=repetition, solves=solves))
    return cells


def validate_proposal(proposal):
    schema_check('lp-fp4-proposal-v1.schema.json', proposal)
    integer_tree(proposal)
    if proposal['specification']['path'] != SPEC:
        raise ContractError('unexpected specification')
    verify_reference(proposal['specification'])
    source_paths = [ref['path'] for ref in proposal['sources']]
    required = {'tools/lp_fp4_contract.py', 'tools/lp_fp4_protocol.py',
                'schemas/lp-fp4-proposal-v1.schema.json', 'schemas/lp-fp4-checkpoint-v1.schema.json',
                'schemas/lp-fp4-cost-v1.schema.json'}
    if len(set(source_paths)) != len(source_paths) or not required.issubset(source_paths):
        raise ContractError('incomplete or duplicate contract source bindings')
    for reference in proposal['sources']:
        verify_reference(reference)
    rows = retained_rows(proposal['retained_result'])
    by_id = {row['id']: row for row in rows}
    if [model['id'] for model in proposal['models']] != list(MODEL_IDS):
        raise ContractError('frozen development roster changed')
    for model in proposal['models']:
        row = by_id.get(model['source_trial'])
        if (row is None or row['model_id'] != model['id'] or row['repetition'] != 0
                or row['model']['sha256'] != model['sha256']):
            raise ContractError('model not bound to retained source')
    if proposal['lanes'] != LANES:
        raise ContractError('frozen comparison lanes changed')
    for stage in proposal['resources'].values():
        for job in stage['jobs']:
            for key in ('count', 'wall_seconds', 'cpu_seconds', 'gpu_seconds'):
                whole(job[key])
            if (job['cpu_seconds'] != 4 * job['wall_seconds']
                    or job['gpu_seconds'] not in (0, job['wall_seconds'])):
                raise ContractError('whole-job reservation mismatch')
        for resource in ('cpu_seconds', 'gpu_seconds'):
            if whole(stage[resource]) != sum(j['count'] * j[resource] for j in stage['jobs']):
                raise ContractError('resource total mismatch')
    if proposal['resources'] != resource_proposal():
        raise ContractError('frozen resource proposal changed')
    cells = study_cells(proposal)
    if len(cells) != 192 or sum(c['solves'] for c in cells) != 288:
        raise ContractError('incomplete study grid')
    return dict(contract_valid=True, execution_authorized=False, hardware_admitted=False,
                cells=len(cells), endpoints=sum(c['solves'] for c in cells),
                resources=proposal['resources'])


def cost_input(reference):
    return dict(schema_version=1, kind='lp-fp4-cost-input', source=reference, rows=[
        dict(trial_id=row['id'], total_ns=row['elapsed_ns'], phases_ns=row['phases_ns'],
             accepted=len(row['results']) == 1 and row['results'][0]['accepted'], candidate=None)
        for row in retained_rows(reference)])


def interval(value, *, integer=False):
    lo, hi = (whole(value[k]) if integer else exact(value[k]) for k in ('lower', 'upper'))
    if lo < 0 or hi < lo:
        raise ContractError('reversed or negative interval')
    return lo, hi


def forecast(row):
    total, phases = whole(row['total_ns']), row['phases_ns']
    if total == 0 or sum(whole(v) for v in phases.values()) != total:
        raise ContractError('delivery phases are not a disjoint total')
    native = phases['native']
    ideal = None if native == total else Fraction(total, total - native)
    candidate = row['candidate']
    worst = None
    if candidate is not None:
        lower, upper = interval(candidate['accelerated_ns'], integer=True)
        if upper > native:
            raise ContractError('accelerated interval exceeds native phase')
        _, work_max = interval(candidate['work_ratio'])
        speed_min, _ = interval(candidate['speedup'])
        if speed_min <= 0 or work_max <= 0:
            raise ContractError('nonpositive work/throughput ratio')
        overhead = sum(interval(v, integer=True)[1] for v in candidate['incremental_ns'].values())
        worst = max(Fraction(total) - a + a * work_max / speed_min + overhead
                    for a in (lower, upper))
    if not row['accepted']:
        decision = 'ineligible_quality'
    elif ideal is not None and ideal < GAIN:
        decision = 'reject_ideal_bound'
    elif candidate is None:
        decision = 'needs_profile'
    elif worst * GAIN <= total:
        decision = 'forecast_admitted'
    else:
        decision = 'reject_forecast'
    return dict(trial_id=row['trial_id'], decision=decision,
                ideal_speedup=None if ideal is None else float(ideal),
                worst_candidate_ns=None if worst is None else float(worst),
                execution_authorized=False, certified=False)


def review_cost(cost):
    schema_check('lp-fp4-cost-v1.schema.json', cost)
    integer_tree(cost)
    expected = cost_input(cost['source'])
    if len({row['trial_id'] for row in cost['rows']}) != len(cost['rows']):
        raise ContractError('duplicate cost row')
    by_id = {row['trial_id']: row for row in expected['rows']}
    if set(by_id) != {row['trial_id'] for row in cost['rows']}:
        raise ContractError('cost coverage differs from retained control')
    for row in cost['rows']:
        if {k: v for k, v in row.items() if k != 'candidate'} != {
                k: v for k, v in by_id[row['trial_id']].items() if k != 'candidate'}:
            raise ContractError('cost phases or quality differ from retained evidence')
    rows = [forecast(row) for row in cost['rows']]
    return dict(schema_version=1, kind='lp-fp4-cost-review', source=cost['source'],
                execution_authorized=False, hardware_admitted=False,
                counts={key: sum(r['decision'] == key for r in rows) for key in (
                    'ineligible_quality', 'reject_ideal_bound', 'needs_profile',
                    'forecast_admitted', 'reject_forecast')}, rows=rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--proposal', type=Path, required=True)
    parser.add_argument('--cost-input', type=Path)
    parser.add_argument('--cost-output', type=Path)
    args = parser.parse_args()
    try:
        proposal = read(args.proposal)
        verdict = validate_proposal(proposal)
        cost = read(args.cost_input) if args.cost_input else cost_input(proposal['retained_result'])
        if cost['source'] != proposal['retained_result']:
            raise ContractError('cost/proposal source mismatch')
        review = review_cost(cost)
        if args.cost_output:
            # Do not let an output request replace any source or input evidence.
            protected = {verify_reference(ref) for ref in proposal['sources'] + [
                proposal['retained_result'], proposal['specification']]}
            protected.add(args.proposal.resolve())
            if args.cost_input:
                protected.add(args.cost_input.resolve())
            if args.cost_output.resolve() in protected or args.cost_output.exists():
                raise ContractError('cost output must be a new artifact')
            args.cost_output.parent.mkdir(parents=True, exist_ok=True)
            with args.cost_output.open('x') as stream:
                json.dump(review, stream, indent=2, sort_keys=True, allow_nan=False)
                stream.write('\n')
        verdict['cost_counts'] = review['counts']
        print(json.dumps(verdict, indent=2, sort_keys=True, allow_nan=False))
    except (ContractError, ValueError, KeyError, OSError) as error:
        parser.exit(2, f'FP4 contract refusal: {error}\n')


if __name__ == '__main__':
    main()
