"""One source-bound CPU FP4 trajectory admission; never launches device work."""

import argparse
from copy import deepcopy
import json
from pathlib import Path
import sys

import lp_fp4_contract as c
import lp_fp4_protocol as protocol
from lp_fp4_reference import ComponentTrajectory, Prepared, RationalReference, Refusal, validate_model

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = 'benchmarks/configs/lp-fp4-cpu-admission-v1.json'
PROPOSAL = 'benchmarks/configs/lp-fp4-proposal-v1.json'
SOURCE_PATHS = (
    'tools/lp_fp4_reference.py', 'tools/lp_fp4_admission.py',
    'tests/integration/test_lp_fp4_reference.py', 'tools/lp_fp4_contract.py',
    'tools/lp_fp4_protocol.py', 'docs/specifications/SPEC-0025-persistent-fp4-contract.md',
    'docs/specifications/SPEC-0026-fp4-prototype-admission.md',
    'docs/decisions/ADR-0057-fp4-prototype-admission.md')
FIXTURE_IDS = ('scalar-equality', 'coupled-equality', 'diagonally-dominant-equality', 'bounded-ranged')


def write_new(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x') as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n')


def validate_fixtures(value):
    if (set(value) != {'schema_version', 'kind', 'updates', 'components', 'controller', 'fixtures'}
            or type(value['schema_version']) is not int or value['schema_version'] != 1
            or value['kind'] != 'lp-fp4-cpu-admission-fixtures'
            or type(value['updates']) is not int or value['updates'] != 600
            or value['components'] != [2, 4, 8]
            or any(type(v) is not int for v in value['components'])
            or value['controller'] != 'fixed binary64 coefficient replay; observation only'
            or [m['id'] for m in value['fixtures']] != list(FIXTURE_IDS)):
        raise c.ContractError('frozen CPU fixture contract changed')
    for model in value['fixtures']:
        validate_model(model)
    return value


def freeze(path):
    fixtures = validate_fixtures(protocol.read(ROOT / FIXTURES))
    proposal = protocol.read(ROOT / PROPOSAL)
    protocol.validate_proposal(proposal)
    write_new(path, dict(schema_version=1, kind='lp-fp4-cpu-execution', phase='cpu-admission',
                         gpu_authorized=False, fixtures=protocol.artifact(ROOT / FIXTURES),
                         proposal=protocol.artifact(ROOT / PROPOSAL),
                         sources=[protocol.artifact(ROOT / name) for name in SOURCE_PATHS],
                         cells=[dict(id=f"{model['id']}-k{k}", model=model['id'], components=k,
                                     updates=fixtures['updates'])
                                for model in fixtures['fixtures'] for k in fixtures['components']],
                         gate='One lane must retain all four nontrivial 600-update trajectories',
                         retry_policy='No scientific automatic retry',
                         conditional_gpu_seconds=dict(admission=480, pilot=720, diagnostics=360)))


def validate_manifest(value):
    required = {'schema_version', 'kind', 'phase', 'gpu_authorized', 'fixtures', 'proposal',
                'sources', 'cells', 'gate', 'retry_policy', 'conditional_gpu_seconds'}
    if (set(value) != required or type(value['schema_version']) is not int or value['schema_version'] != 1
            or value['kind'] != 'lp-fp4-cpu-execution' or value['phase'] != 'cpu-admission'
            or value['gpu_authorized'] is not False or value['fixtures']['path'] != FIXTURES
            or value['proposal']['path'] != PROPOSAL
            or value['gate'] != 'One lane must retain all four nontrivial 600-update trajectories'
            or value['retry_policy'] != 'No scientific automatic retry'
            or value['conditional_gpu_seconds'] != dict(admission=480, pilot=720, diagnostics=360)):
        raise c.ContractError('invalid CPU execution authority')
    if [ref['path'] for ref in value['sources']] != list(SOURCE_PATHS):
        raise c.ContractError('missing or reordered numerical source binding')
    for ref in value['sources'] + [value['fixtures'], value['proposal']]:
        if not isinstance(ref, dict) or set(ref) != {'path', 'sha256'}:
            raise c.ContractError('invalid artifact reference fields')
        protocol.verify_reference(ref)
    fixtures = validate_fixtures(protocol.read(ROOT / FIXTURES))
    proposal = protocol.read(ROOT / PROPOSAL)
    protocol.validate_proposal(proposal)
    expected = [dict(id=f"{model['id']}-k{k}", model=model['id'], components=k, updates=600)
                for model in fixtures['fixtures'] for k in (2, 4, 8)]
    if (value['cells'] != expected or any(type(cell['components']) is not int
                                        or type(cell['updates']) is not int for cell in value['cells'])):
        raise c.ContractError('CPU admission coverage changed')
    return fixtures


def reference_digest(reference):
    # Hex avoids decimal integer conversion limits on long rational trajectories.
    return c.digest([[hex(v.numerator), hex(v.denominator)] for v in reference.x + reference.y])


def run_cell(model, components, updates, *, cancel_after=None):
    if type(updates) is not int or not 1 <= updates <= 600:
        raise c.ContractError('CPU trajectory length outside bound')
    if cancel_after is not None and (type(cancel_after) is not int or not 0 <= cancel_after <= updates):
        raise c.ContractError('invalid cancellation boundary')
    prepared = Prepared(model, components)
    candidate = ComponentTrajectory(prepared, deadline_ns=1)
    reference = RationalReference(model)
    initial = deepcopy(candidate.state)
    trace, observations, refusal = [], [], None
    for _ in range(updates):
        if cancel_after is not None and candidate.counters['physical_updates'] >= cancel_after:
            refusal = dict(reason='cancelled', iteration=candidate.state['controller']['iterations'])
            break
        reference_values = reference.advance()
        try:
            trace.append(candidate.advance(reference_values))
            if candidate.state['controller']['iterations'] % 200 == 0:
                before = c.digest(candidate.state['vectors'])
                candidate.observe()
                after = c.digest(candidate.state['vectors'])
                if before != after:
                    raise Refusal('observation_changed_components')
                observations.append(dict(iteration=candidate.state['controller']['iterations'],
                                         component_sha256=after, reference_sha256=reference_digest(reference),
                                         preserved=True))
        except Refusal as error:
            refusal = dict(reason=error.reason, iteration=reference.iterations, details=error.details)
            break
        except c.ContractError as error:
            refusal = dict(reason='contract_refusal', iteration=reference.iterations, details=str(error))
            break
    completed = candidate.state['controller']['iterations']
    attempted_state = deepcopy(candidate.state)
    last_checkpoint = deepcopy(candidate.checkpoint)
    ledger = candidate.rollback() if refusal else None
    retained = not refusal and completed == updates and candidate.counters['nonzero_groups'] > 0
    return dict(model=model['id'], components=components, requested_updates=updates,
                retained_fast_path=retained, refused=refusal, completed_updates=completed,
                counters=candidate.counters, observations=observations, trace=trace,
                last_diagnostic=candidate.last_diagnostic, state=candidate.state,
                attempted_state_sha256=c.digest(attempted_state), checkpoint_before_rollback=last_checkpoint,
                initial_sha256=c.digest(initial), reference_sha256=reference_digest(reference),
                rollback_ledger=ledger,
                rollback_executed=bool(refusal),
                next_precision=None if retained else {2: 'fp4-4', 4: 'fp4-8', 8: 'native'}[components],
                precision_recovery_executed=False, certified=False)


def deferred_cells(proposal):
    result = []
    for model in ('gpup-development-irregular-2048', 'gpup-development-dense_block-1024'):
        for lane in proposal['lanes']:
            for lifecycle in ('cold', 'prepared'):
                result.append(dict(kind='pilot', model=model, lane=lane['id'], lifecycle=lifecycle,
                                   status='not_executed'))
        for k in (2, 4, 8):
            for variant in ('unfused', 'per-update-reconstructed'):
                result.append(dict(kind='diagnostic', model=model, lane=f'fp4-{k}', lifecycle='prepared',
                                   variant=variant, status='not_executed'))
    return result


def execute(manifest_path, output):
    manifest = protocol.read(manifest_path)
    fixtures = validate_manifest(manifest)
    output = Path(output).resolve()
    if not output.is_relative_to(ROOT):
        raise c.ContractError('execution output must remain in the repository workspace')
    # A fresh directory makes a partial attempt immutable and prevents overwrite.
    output.parent.mkdir(parents=True, exist_ok=False)
    write_new(output.parent / 'manifest.json', manifest)
    frozen = output.parent / 'sources'
    for ref in manifest['sources'] + [manifest['fixtures'], manifest['proposal']]:
        destination = frozen / ref['path']
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open('xb') as stream:
            stream.write(protocol.verify_reference(ref).read_bytes())
    models = {m['id']: m for m in fixtures['fixtures']}
    rows = []
    for cell in manifest['cells']:
        result = run_cell(models[cell['model']], cell['components'], cell['updates'])
        result_path = output.parent / (cell['id'] + '.json')
        write_new(result_path, result)
        rows.append(dict(id=cell['id'], artifact=protocol.artifact(result_path),
                         model=cell['model'], components=cell['components'],
                         retained_fast_path=result['retained_fast_path'],
                         completed_updates=result['completed_updates'],
                         physical_updates=result['counters']['physical_updates'],
                         observations=len(result['observations']), refusal=result['refused'],
                         last_diagnostic=result['last_diagnostic'],
                         nonzero_groups=result['counters']['nonzero_groups']))
        print(json.dumps({k: rows[-1][k] for k in ('id', 'completed_updates', 'observations', 'retained_fast_path')}), flush=True)
    qualified = [k for k in (2, 4, 8) if all(r['retained_fast_path'] for r in rows if r['components'] == k)]
    report = dict(schema_version=1, kind='lp-fp4-cpu-admission-result',
                  manifest=protocol.artifact(output.parent / 'manifest.json'), rows=rows,
                  numerical_admitted=bool(qualified), qualified_components=qualified,
                  gpu_execution_started=False, gpu_seconds=0, certificates=0,
                  deferred=deferred_cells(protocol.read(ROOT / PROPOSAL)),
                  status='cpu_admitted' if qualified else 'cpu_numerical_refusal',
                  later_stages='await concrete device package' if qualified else 'closed by CPU admission refusal')
    write_new(output, report)
    return bool(qualified)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--freeze', type=Path)
    parser.add_argument('--manifest', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    try:
        if args.freeze and not args.manifest and not args.output:
            freeze(args.freeze)
            return 0
        if args.manifest and args.output and not args.freeze:
            return 0 if execute(args.manifest, args.output) else 3
        parser.error('choose --freeze or --manifest with --output')
    except (c.ContractError, ValueError, OSError, KeyError, TypeError) as error:
        parser.exit(2, f'FP4 admission refusal: {error}\n')


if __name__ == '__main__':
    sys.exit(main())
