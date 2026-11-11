"""SPEC-0029 CPU recovery-policy oracle; no trajectory runner or certificate issuer.

Exact local errors and operational residual observations are different objects.
Nothing in this module bounds error against a full exact/native trajectory.
"""
from copy import deepcopy
from dataclasses import dataclass, replace
from fractions import Fraction as F
import hashlib
import json
from pathlib import Path
import re

import lp_fp4_contract as c
from lp_fp4_reference_v2 import pair_round, vector_encode, vector_values

ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / 'benchmarks/configs/lp-fp4-recovery-v1.json'
TERMS = ('operator', 'instruction', 'combine', 'scalar', 'projection', 'encoding', 'discarded')
PHASES = ('prepare', 'transport', 'iteration', 'audit', 'conversion', 'rollback',
          'native_recovery', 'export', 'checker')
MAX_COUNTER = (1 << 53) - 1


def require(condition, message):
    if not condition:
        raise c.ContractError(message)


def integer(value, minimum=0, maximum=MAX_COUNTER):
    require(type(value) is int and minimum <= value <= maximum, 'invalid integer')
    return value


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                     allow_nan=False).encode()).hexdigest()


def identity(value):
    require(isinstance(value, str) and re.fullmatch('[0-9a-f]{64}', value), 'invalid digest')
    return value


def policy():
    value = json.loads(POLICY.read_text())
    c.schema_check('lp-fp4-recovery-v1.schema.json', value)
    return value


def tolerance(tier):
    require(tier in ('certified-1e-7', 'certified-1e-9'), 'unknown final tier')
    return F(1, 10**(7 if tier == 'certified-1e-7' else 9))


def local_encode(values, components):
    """Triangle-inequality bound to these local inputs, including cancellation."""
    require(bool(values), 'empty local vector')
    rounded = [pair_round(c.exact(v)) for v in values]
    blocks, encoding = vector_encode([v for v, _ in rounded], components)
    rounding = max(e for _, e in rounded)
    return dict(blocks=blocks, pair_rounding=rounding, encoding=encoding,
                total=rounding + encoding, authority='exact-local-only')


def local_product_budget(operator_error, stored_norm, instruction, combine, discarded=0):
    """Bound A*x_stored minus computed product; contains NO trajectory-error term."""
    values = list(map(c.nonnegative, (operator_error, stored_norm, instruction, combine, discarded)))
    a, x, mma, reduction, omitted = values
    return a * x + mma + reduction + omitted


def local_allowance(residual, tier):
    # Dimensionless aggregate local budget for one complete original-unit update.
    return max(tolerance(tier), min(F(1), c.nonnegative(residual))) / 64


def check_local_terms(terms, gains, scale, residual, tier, authority):
    """All errors mapped through local downstream operations into original units.

    'device-observed' is deliberately not promoted to a mathematical bound.
    Missing or unknown errors force recovery; there is no zero-by-default term.
    """
    require(set(terms) == set(gains) == set(TERMS), 'incomplete local error terms')
    require(authority in ('exact-local-only', 'device-observed'), 'unknown local authority')
    scale = c.exact(scale)
    require(scale >= 1, 'normalization scale below one')
    total = sum(c.nonnegative(terms[k]) * c.nonnegative(gains[k]) for k in TERMS) / scale
    return dict(total=total, allowance=local_allowance(residual, tier),
                accepted=total <= local_allowance(residual, tier), authority=authority,
                trajectory_enclosure=False)


def _bounds(lower, upper, size):
    require(len(lower) == len(upper) == size, 'bound shape mismatch')
    pairs = [(None if lo is None else c.exact(lo), None if hi is None else c.exact(hi))
             for lo, hi in zip(lower, upper)]
    require(all(lo is None or hi is None or lo <= hi for lo, hi in pairs), 'reversed bounds')
    return pairs


def _clip(value, bounds):
    lo, hi = bounds
    return min(value, hi) if lo is None and hi is not None else (
        max(value, lo) if hi is None and lo is not None else (
            min(max(value, lo), hi) if lo is not None else value))


def residual_observation(matrix, objective, row_lower, row_upper, column_lower,
                         column_upper, x, y):
    """Exact CPU oracle for a future FP64 original-model operational audit.

    Minimization sign convention: reduced cost c - A^T*y. Unit-step projected
    fixed-point residuals are diagnostic only, not feasibility/gap certificates.
    """
    require(isinstance(matrix, list) and 1 <= len(matrix) <= 64, 'audit oracle rows')
    require(isinstance(objective, list) and 1 <= len(objective) <= 64, 'audit oracle columns')
    m, n = len(matrix), len(objective)
    require(len(x) == n and len(y) == m and all(len(r) == n for r in matrix), 'audit shape')
    a = [list(map(c.exact, row)) for row in matrix]
    x, y, cost = list(map(c.exact, x)), list(map(c.exact, y)), list(map(c.exact, objective))
    rows, cols = _bounds(row_lower, row_upper, m), _bounds(column_lower, column_upper, n)
    ax = [sum(v * w for v, w in zip(row, x)) for row in a]
    reduced = [cost[j] - sum(a[i][j] * y[i] for i in range(m)) for j in range(n)]
    sx = max([F(1)] + list(map(abs, x + reduced)) + [abs(v) for p in cols for v in p if v is not None])
    sy = max([F(1)] + list(map(abs, y + ax)) + [abs(v) for p in rows for v in p if v is not None])
    row = max(abs(v - _clip(v, b)) for v, b in zip(ax, rows)) / sy
    column = max(abs(v - _clip(v, b)) for v, b in zip(x, cols)) / sx
    primal_fixed = max(abs(v - _clip(v - z, b)) for v, z, b in zip(x, reduced, cols)) / sx
    dual_fixed = max(abs(v + _clip(w - v, (None if hi is None else -hi,
                                         None if lo is None else -lo)))
                     for v, w, (lo, hi) in zip(ax, y, rows)) / sy
    result = dict(row=row, column=column, primal_fixed=primal_fixed, dual_fixed=dual_fixed)
    result['rho'] = max(result.values())
    return result


@dataclass(frozen=True)
class Monitor:
    model: str
    policy: str
    tier: str
    checkpoint: str
    generation: int = 0
    iteration: int = 0
    components: int = 2
    residual: F = F(1)
    stalls: int = 0
    mode: str = 'fp4'

    def __post_init__(self):
        for value in (self.model, self.policy, self.checkpoint):
            identity(value)
        tolerance(self.tier)
        integer(self.generation)
        integer(self.iteration)
        integer(self.components, 2, 8)
        require(self.components in (2, 4, 8), 'unsupported components')
        object.__setattr__(self, 'residual', c.nonnegative(self.residual))
        integer(self.stalls, 0, 2)
        require(self.mode in ('fp4', 'native', 'stopped', 'certified'), 'invalid recovery mode')


def submission_size(state, current_iteration, physical_remaining, controller_remaining):
    """A fused window may not cross a controller/audit/cancellation boundary."""
    integer(physical_remaining)
    integer(controller_remaining)
    integer(current_iteration)
    require(state.mode == 'fp4', 'FP4 path is closed')
    require(0 <= current_iteration - state.iteration <= 200, 'unaudited iteration count')
    return min(32, 200 - (current_iteration - state.iteration), physical_remaining, controller_remaining)


def recover(state, reason, *, terminal=False):
    """Return a plan, never mutate checkpoint bytes or uncharge attempted work."""
    require(state.generation < MAX_COUNTER, 'generation exhausted')
    require(state.mode == 'fp4', 'FP4 path is closed')
    native = state.components == 8 or reason == 'conversion_failure'
    action = 'stop_restore' if terminal else ('native_restore' if native else 'promote_restore')
    target = state.components if terminal else (None if native else {2: 4, 4: 8}[state.components])
    next_state = replace(state, generation=state.generation + 1,
                         components=target or state.components, stalls=0,
                         mode='stopped' if terminal else ('native' if native else 'fp4'))
    return dict(action=action, reason=reason, target_components=target, state=next_state,
                restore_sha256=state.checkpoint, reset_work=False)


def audit(state, *, generation, iteration, candidate, candidate_checkpoint, residual, safety='ok',
          cancelled=False, exhausted=False, certificate=None, checker=None):
    """Pure host-policy decision after synchronization and original-A observation.

    A valid checker receipt takes precedence over stagnation, never over unsafe
    state, cancellation, identity failures or an unaudited >200-update window.
    """
    integer(generation)
    require(state.mode == 'fp4', 'FP4 path is closed')
    integer(iteration)
    identity(candidate)
    identity(candidate_checkpoint)
    require(generation == state.generation, 'stale submission')
    require(0 < iteration - state.iteration <= 200, 'audit window outside 1..200')
    require(type(cancelled) is bool and type(exhausted) is bool, 'invalid stop flags')
    require(safety in ('ok', 'nonfinite', 'local_budget', 'projection_ambiguous',
                       'audit_failure', 'conversion_failure'), 'unknown safety status')
    if cancelled or exhausted:
        return recover(state, 'cancelled' if cancelled else 'budget', terminal=True)
    if safety != 'ok':
        return recover(state, safety, terminal=safety == 'audit_failure')
    try:
        rho = c.nonnegative(residual)
    except c.ContractError:
        return recover(state, 'nonfinite')
    if certificate is not None:
        require(checker is not None, 'missing checker identity')
        if certificate_matches(certificate, model=state.model, candidate=candidate,
                               tier=state.tier, checker=checker):
            return dict(action='certified_endpoint', state=replace(state, mode='certified',
                        checkpoint=candidate_checkpoint, iteration=iteration, residual=rho),
                        certificate=deepcopy(certificate))
    if rho > 2 * max(c.nonnegative(state.residual), tolerance(state.tier)):
        return recover(state, 'residual_growth')
    stalls = 0 if state.residual > 0 and rho <= F(9, 10) * state.residual else state.stalls + 1
    if stalls >= 3:
        return recover(state, 'stagnation')
    return dict(action='adopt', state=replace(state, checkpoint=candidate_checkpoint,
                iteration=iteration, residual=rho, stalls=stalls))


def certificate_matches(receipt, *, model, candidate, tier, checker):
    """Validate an already independently produced receipt, not its mathematics.

    Integration MUST verify source/artifact hashes and run the trusted checker.
    A caller-supplied dictionary alone is not independent certification evidence.
    """
    fields = {'model_sha256', 'candidate_sha256', 'checker_sha256', 'tier',
              'absolute', 'relative', 'eligible', 'feasible', 'finite_bound',
              'gap_closed', 'accepted', 'refusal'}
    require(isinstance(receipt, dict) and set(receipt) == fields, 'certificate fields')
    for name, expected in [('model_sha256', model), ('candidate_sha256', candidate),
                           ('checker_sha256', checker)]:
        identity(expected)
        require(receipt[name] == expected, 'certificate binding differs')
    require(receipt['tier'] == tier and receipt['absolute'] == receipt['relative'] == str(tolerance(tier)),
            'certificate tolerance differs')
    flags = [receipt[k] for k in ('eligible', 'feasible', 'finite_bound', 'gap_closed', 'accepted')]
    require(all(type(v) is bool for v in flags), 'certificate flags')
    require(receipt['refusal'] is None or isinstance(receipt['refusal'], str), 'certificate refusal')
    require(not receipt['accepted'] or (all(flags) and receipt['refusal'] is None),
            'inconsistent accepted certificate')
    return all(flags) and receipt['refusal'] is None


def validate_checkpoint(value):
    """V2 retains the full packed payload; local bounds are NOT global errors."""
    c.schema_check('lp-fp4-recovery-checkpoint-v1.schema.json', value)
    legacy_shape = deepcopy(value)
    legacy_shape.pop('policy_sha256')
    legacy_shape.pop('error_authority')
    legacy_shape['kind'] = 'lp-fp4-checkpoint'
    legacy_shape['schema_version'] = 1
    legacy_shape['errors'] = legacy_shape.pop('local_representation_bounds')
    # Reuse shape/bit validation only; never invoke v1 observe/error guard.
    c.validate_checkpoint(legacy_shape)
    return deepcopy(value)


def restore(checkpoint, *, binding, policy_sha256, current_generation):
    result = validate_checkpoint(checkpoint)
    require(result['binding'] == binding and result['policy_sha256'] == policy_sha256,
            'restore identity differs')
    integer(current_generation)
    require(result['generation'] <= current_generation < MAX_COUNTER, 'restore generation')
    result['generation'] = current_generation + 1
    return result


def checkpoint_bundle(payload, monitor):
    """Bind progress/controller metadata to the full numerical checkpoint.

    The monotone work ledger is intentionally external to this rollback bundle.
    """
    result = validate_checkpoint(payload)
    require(monitor.checkpoint == digest(result), 'checkpoint content differs')
    require((monitor.model, monitor.policy, monitor.generation, monitor.iteration, monitor.components)
            == (result['binding']['model'], result['policy_sha256'], result['generation'],
                result['controller']['iterations'], result['components']), 'checkpoint monitor differs')
    return dict(payload=result, monitor=dict(model=monitor.model, policy=monitor.policy,
                tier=monitor.tier, checkpoint=monitor.checkpoint, generation=monitor.generation,
                iteration=monitor.iteration, components=monitor.components,
                residual=c.rational(monitor.residual), stalls=monitor.stalls, mode=monitor.mode))


def restore_bundle(bundle, *, binding, policy_sha256, current_generation):
    require(isinstance(bundle, dict) and set(bundle) == {'payload', 'monitor'}, 'bundle fields')
    saved = deepcopy(bundle['monitor'])
    require(isinstance(saved, dict) and set(saved) ==
            {'model', 'policy', 'tier', 'checkpoint', 'generation', 'iteration',
             'components', 'residual', 'stalls', 'mode'}, 'monitor fields')
    saved['residual'] = c.read_rational(saved['residual'])
    monitor = Monitor(**saved)
    checkpoint_bundle(bundle['payload'], monitor)
    restored = restore(bundle['payload'], binding=binding, policy_sha256=policy_sha256,
                       current_generation=current_generation)
    monitor = replace(monitor, generation=restored['generation'], checkpoint=digest(restored))
    return checkpoint_bundle(restored, monitor)


def convert_checkpoint(checkpoint, components):
    """CPU conversion oracle: preserve decoded values, account for re-encoding.

    Promotion cannot recover information previously discarded. Conversion is an
    explicit checkpoint transition, not an observation or hidden anchor restart.
    """
    result = validate_checkpoint(checkpoint)
    require((result['components'], components) in ((2, 4), (4, 8)), 'nonmonotone promotion')
    for name, blocks in result['vectors'].items():
        converted = [c.encode(c.decode(b), components) for b in blocks]
        require(all(c.decode(a) == c.decode(b) for a, b in zip(blocks, converted)),
                'conversion changed represented state')
        result['vectors'][name] = converted
        # Keep the prior local uncertainty; zero re-encoding error is not a reset.
    result['components'] = components
    return validate_checkpoint(result)


def charge(ledger, phase, elapsed_ns, physical_updates=0):
    require(set(ledger) == set(PHASES) | {'physical_updates'}, 'ledger fields')
    require(phase in PHASES, 'unknown cost phase')
    result = {k: integer(v) for k, v in ledger.items()}
    result[phase] = integer(result[phase] + integer(elapsed_ns))
    result['physical_updates'] = integer(result['physical_updates'] + integer(physical_updates))
    return result


def complete_cost(native_ns, phases_ns):
    integer(native_ns, 1)
    require(set(phases_ns) == set(PHASES), 'incomplete cost phases')
    total = sum(integer(v) for v in phases_ns.values())
    require(total > 0, 'zero candidate cost')
    return dict(candidate_ns=total, native_ns=native_ns, speed_ratio=F(native_ns, total),
                row_meets_110_percent=F(native_ns, total) >= F(11, 10),
                solver_retention_established=False)


def proposed_cells():
    """A fresh non-executable integration roster, unrelated to refused v1 cells."""
    p = policy()['integration_proposal']
    return [dict(id=f'{model}/{lane}/{tier}', model=model, lane=lane, tier=tier,
                 minimum_updates=600)
            for model in p['models'] for lane in p['lanes'] for tier in p['tiers']]
