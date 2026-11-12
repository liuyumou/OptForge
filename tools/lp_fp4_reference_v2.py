"""SPEC-0026 development correction: separate local rounding/encoding budgets.

The v1 formal admission remains frozen and refused. This v2 module has no new
scientific qualification; only focused correction contracts may exercise it.
No device executor or certificate issuer.

Rational temporaries define local two-FP32 rounding and an independent original-A
trajectory. Persistent candidate state is packed E2M1. CPU execution time and
modeled group counts are not GPU performance measurements.
"""

from copy import deepcopy
from fractions import Fraction as F
import math
import struct

import lp_fp4_contract as c


class Refusal(c.ContractError):
    def __init__(self, reason, **details):
        super().__init__(reason)
        self.reason, self.details = reason, details


def nearest_integer(value):
    quotient, remainder = divmod(value.numerator, value.denominator)
    doubled = 2 * remainder
    return quotient + int(doubled > value.denominator or
                          (doubled == value.denominator and quotient % 2))


def fp32(value):
    """Direct rational -> IEEE binary32 RN-even, avoiding binary64 double rounding."""
    value = c.exact(value)
    sign = int(value < 0)
    value = abs(value)
    if not value:
        return F(0)
    exponent = value.numerator.bit_length() - value.denominator.bit_length()
    if value < F(2) ** exponent:
        exponent -= 1
    if exponent < -126:
        bits = nearest_integer(value * (1 << 149))
    else:
        if exponent > 127:
            raise Refusal('fp32_overflow')
        significand = nearest_integer(value / F(2) ** (exponent - 23))
        if significand == 1 << 24:
            exponent += 1
            significand >>= 1
        if exponent > 127:
            raise Refusal('fp32_overflow')
        bits = ((exponent + 127) << 23) | (significand - (1 << 23))
    bits |= sign << 31
    return F(struct.unpack('>f', struct.pack('>I', bits))[0])


def pair_round(value):
    value = c.exact(value)
    head = fp32(value)
    tail = fp32(value - head)
    represented = head + tail
    return represented, abs(value - represented)


def upward(value):
    value = c.nonnegative(value)
    rounded = float(value)
    if not math.isfinite(rounded):
        raise Refusal('enclosure_overflow')
    if F(rounded) < value:
        rounded = math.nextafter(rounded, math.inf)
    if not math.isfinite(rounded):
        raise Refusal('enclosure_overflow')
    return F(rounded)


def clamp(value, lower, upper):
    if lower is not None:
        value = max(value, lower)
    if upper is not None:
        value = min(value, upper)
    return value


def validate_model(model):
    fields = {'id', 'matrix', 'objective', 'column_lower', 'column_upper',
              'row_lower', 'row_upper', 'tau', 'sigma', 'inverse_scale_x', 'inverse_scale_y'}
    if not isinstance(model, dict) or set(model) != fields or not isinstance(model['id'], str):
        raise c.ContractError('invalid reference model fields')
    matrix = model['matrix']
    if (not isinstance(matrix, list) or not 1 <= len(matrix) <= 64
            or not isinstance(matrix[0], list) or not 1 <= len(matrix[0]) <= 64):
        raise c.ContractError('reference model shape outside bound')
    m, n = len(matrix), len(matrix[0])
    if any(not isinstance(row, list) or len(row) != n for row in matrix):
        raise c.ContractError('ragged reference matrix')
    result = dict(id=model['id'], matrix=[list(map(c.exact, row)) for row in matrix])
    for name, length in [('objective', n), ('column_lower', n), ('column_upper', n),
                         ('row_lower', m), ('row_upper', m),
                         ('inverse_scale_x', n), ('inverse_scale_y', m)]:
        values = model[name]
        if not isinstance(values, list) or len(values) != length:
            raise c.ContractError('reference vector shape mismatch')
        bounds = name.endswith(('lower', 'upper'))
        result[name] = [None if value is None and bounds else c.exact(value) for value in values]
    for prefix in ('column', 'row'):
        for lo, hi in zip(result[prefix + '_lower'], result[prefix + '_upper']):
            if lo is not None and hi is not None and lo > hi:
                raise c.ContractError('reversed model bounds')
    for key in ('tau', 'sigma'):
        result[key] = c.exact(model[key])
        if result[key] <= 0:
            raise c.ContractError('nonpositive step')
    if any(v <= 0 for key in ('inverse_scale_x', 'inverse_scale_y') for v in result[key]):
        raise c.ContractError('nonpositive inverse scale')
    return result


def blend_coefficients(since_restart):
    if type(since_restart) is not int or not 0 <= since_restart < 1_000_000:
        raise c.ContractError('invalid replay iteration')
    # Same binary64 expressions as the native host controller, frozen replay.
    return F((since_restart + 1) / (since_restart + 2)), F(1 / (since_restart + 2))


def vector_encode(values, components):
    blocks = [c.encode(values[i:i + 32] + [F(0)] * max(0, i + 32 - len(values)), components)
              for i in range(0, len(values), 32)]
    return blocks, max(c.read_rational(block['remainder_bound']) for block in blocks)


def rounded_encode(values, components):
    """Charge pair rounding and representation remainder separately.

    Their signed errors may cancel, but SPEC-0025 checkpoints require the stored
    enclosure to cover the encoding remainder as a separate quantity.
    """
    rounded = [pair_round(value) for value in values]
    blocks, encoding_error = vector_encode([value for value, _ in rounded], components)
    return blocks, max(error for _, error in rounded) + encoding_error


def vector_values(blocks, length):
    return [v for block in blocks for v in c.decode(block)][:length]


class Prepared:
    """Immutable tile data and original-operator norms for the CPU oracle."""

    def __init__(self, model, components):
        self.original = deepcopy(model)
        self.model = validate_model(model)
        if type(components) is not int or components not in c.COMPONENTS:
            raise c.ContractError('unsupported component count')
        self.components = components
        self.rows, self.columns = len(model['matrix']), len(model['matrix'][0])
        self.tiles = []
        self.approximate = [[F(0)] * self.columns for _ in range(self.rows)]
        for row in range(0, self.rows, 32):
            for column in range(0, self.columns, 32):
                values = [self.model['matrix'][r][j] if r < self.rows and j < self.columns else F(0)
                          for r in range(row, row + 32) for j in range(column, column + 32)]
                if not any(values):
                    continue
                block = c.encode(values, components)
                self.tiles.append((row, column, block, c.transpose_tile(block)))
                decoded = c.decode(block)
                for r in range(min(32, self.rows - row)):
                    for j in range(min(32, self.columns - column)):
                        self.approximate[row + r][column + j] = decoded[32 * r + j]
        self.norm_a = max(sum(map(abs, row)) for row in self.model['matrix'])
        self.norm_at = max(sum(abs(row[j]) for row in self.model['matrix']) for j in range(self.columns))
        errors = [[abs(a - b) for a, b in zip(row, approx)]
                  for row, approx in zip(self.model['matrix'], self.approximate)]
        self.error_a = max(map(sum, errors))
        self.error_at = max(sum(row[j] for row in errors) for j in range(self.columns))
        self.identity = c.digest(dict(model=model, components=components, tiles=self.tiles))

    def product(self, blocks, transpose, counters):
        size = self.columns if transpose else self.rows
        output, exact_product = [F(0)] * size, [F(0)] * size
        for row, column, block, transposed in self.tiles:
            offset, input_block, matrix = (column, row // 32, transposed) if transpose else (row, column // 32, block)
            vector = blocks[input_block]
            counters['modeled_mma_tiles'] += 2 * self.components**2
            for plane in matrix['planes']:
                codes_a = c.unpack(plane['data_hex'], 1024)
                for xplane in vector['planes']:
                    codes_x = c.unpack(xplane['data_hex'], 32)
                    for r in range(min(32, size - offset)):
                        group = c.group_product(codes_a[r * 32:(r + 1) * 32], codes_x,
                                                plane['exponent'], xplane['exponent'])
                        if fp32(group) != group:
                            raise Refusal('mathematical_group_not_fp32_exact')
                        counters['component_groups'] += 1
                        counters['nonzero_groups'] += int(group != 0)
                        exact_product[offset + r] += group
                        output[offset + r], _ = pair_round(output[offset + r] + group)
                        counters['local_pair_roundings'] += 1
        error = max(abs(a - b) for a, b in zip(output, exact_product))
        return output, error


class RationalReference:
    """Direct original-A recurrence; does not use tiles, pair arithmetic or bounds."""

    def __init__(self, model):
        self.model = validate_model(model)
        self.x = [clamp(F(0), lo, hi) for lo, hi in zip(self.model['column_lower'], self.model['column_upper'])]
        self.y = [F(0)] * len(self.model['matrix'])
        self.anchor_x, self.anchor_y = self.x.copy(), self.y.copy()
        self.iterations = 0

    def advance(self):
        model, old_x, old_y = self.model, self.x, self.y
        tau, sigma = model['tau'], model['sigma']
        product_t = [sum(row[j] * y for row, y in zip(model['matrix'], old_y)) for j in range(len(old_x))]
        u = [clamp(x - tau * (cost - dot), lo, hi) for x, cost, dot, lo, hi in zip(
            old_x, model['objective'], product_t, model['column_lower'], model['column_upper'])]
        bar = [2 * a - b for a, b in zip(u, old_x)]
        products = [sum(a * b for a, b in zip(row, bar)) for row in model['matrix']]
        v = []
        for y, dot, lo, hi in zip(old_y, products, model['row_lower'], model['row_upper']):
            raw = y - sigma * dot
            v.append(raw - clamp(raw, None if hi is None else -sigma * hi,
                                 None if lo is None else -sigma * lo))
        toward, back = blend_coefficients(self.iterations)
        self.x = [toward * a + back * b for a, b in zip(u, self.anchor_x)]
        self.y = [toward * a + back * b for a, b in zip(v, self.anchor_y)]
        self.iterations += 1
        return self.x, self.y, bar


class ComponentTrajectory:
    def __init__(self, prepared, *, deadline_ns=0):
        self.prepared = prepared
        self.counters = dict(physical_updates=0, component_groups=0, nonzero_groups=0,
                             modeled_mma_tiles=0, local_pair_roundings=0, observations=0)
        self.deadline_ns = deadline_ns
        model = prepared.model
        initial_x = [clamp(F(0), lo, hi) for lo, hi in zip(model['column_lower'], model['column_upper'])]
        initial_y = [F(0)] * prepared.rows
        vectors, errors = {}, {}
        for name, values in [('x', initial_x), ('y', initial_y), ('bar', initial_x),
                             ('anchor_x', initial_x), ('anchor_y', initial_y)]:
            vectors[name], remainder = vector_encode(values, prepared.components)
            errors[name] = c.rational(remainder)
        self.state = dict(schema_version=1, kind='lp-fp4-checkpoint',
                          binding=dict(model=c.digest(prepared.original), operator=prepared.identity,
                                       settings=c.digest(dict(tau=str(model['tau']), sigma=str(model['sigma']))),
                                       proposal=c.digest(dict(contract='SPEC-0026', replay='fixed-600'))),
                          rows=prepared.rows, columns=prepared.columns, components=prepared.components,
                          generation=0, vectors=vectors, errors=errors,
                          controller=dict(weight=c.float_bits(1), integral=c.float_bits(0),
                                          previous_error=None, anchor_error=c.float_bits(1),
                                          last_check_error=c.float_bits(1), iterations=0, restarts=0,
                                          since_restart=0, checked_iteration=0))
        c.validate_checkpoint(self.state)
        self.checkpoint = deepcopy(self.state)
        self.last_diagnostic = None

    def values(self, state=None):
        state = self.state if state is None else state
        return {key: vector_values(state['vectors'][key], length) for key, length in (
            ('x', self.prepared.columns), ('y', self.prepared.rows), ('bar', self.prepared.columns),
            ('anchor_x', self.prepared.columns), ('anchor_y', self.prepared.rows))}

    def advance(self, reference_values=None):
        self.counters['physical_updates'] += 1
        p, state, values = self.prepared, self.state, self.values()
        if reference_values is not None:
            if (not isinstance(reference_values, (tuple, list)) or len(reference_values) != 3
                    or any(not isinstance(vector, (tuple, list)) or len(vector) != length
                           for vector, length in zip(reference_values, (p.columns, p.rows, p.columns)))):
                raise c.ContractError('independent reference shape mismatch')
            reference_values = [list(map(c.exact, vector)) for vector in reference_values]
        model, tau, sigma = p.model, p.model['tau'], p.model['sigma']
        errors = {key: c.read_rational(v) for key, v in state['errors'].items()}
        local = {key: F(0) for key in ('transpose', 'primal', 'extrapolate', 'forward', 'dual', 'blend_x', 'blend_y')}
        transposed, local['transpose'] = p.product(state['vectors']['y'], True, self.counters)
        transpose_bound = c.product_error(p.norm_at, p.error_at, max(map(abs, values['y'])),
                                          errors['y'], local['transpose'])
        u, u_local = [], []
        for j, (x, objective, dot, lo, hi) in enumerate(zip(values['x'], model['objective'], transposed,
                                                         model['column_lower'], model['column_upper'])):
            raw_exact = x - tau * (objective - dot)
            raw, rounding = pair_round(raw_exact)
            interval = c.project_interval(raw, errors['x'] + tau * transpose_bound + rounding, lo, hi)
            if interval['decision'] == 'ambiguous':
                raise Refusal('projection_ambiguous', phase='primal', coordinate=j,
                              center=float(raw), radius=float(errors['x'] + tau * transpose_bound + rounding))
            projected, _ = pair_round(clamp(raw, lo, hi))
            u.append(projected)
            u_local.append(abs(projected - clamp(raw_exact, lo, hi)))
            self.counters['local_pair_roundings'] += 2
        local['primal'] = max(u_local)
        bar_exact = [2 * a - b for a, b in zip(u, values['x'])]
        bar_blocks, local['extrapolate'] = rounded_encode(bar_exact, p.components)
        bar_stored = vector_values(bar_blocks, p.columns)
        self.counters['local_pair_roundings'] += p.columns
        u_bound = errors['x'] + tau * transpose_bound + local['primal']
        bar_bound = 2 * u_bound + errors['x'] + local['extrapolate']
        product, local['forward'] = p.product(bar_blocks, False, self.counters)
        forward_bound = c.product_error(p.norm_a, p.error_a, max(map(abs, bar_stored)),
                                        bar_bound, local['forward'])
        v, v_local = [], []
        for i, (y, dot, lower, upper) in enumerate(zip(values['y'], product, model['row_lower'], model['row_upper'])):
            lo, hi = None if upper is None else -sigma * upper, None if lower is None else -sigma * lower
            raw_exact = y - sigma * dot
            raw, rounding = pair_round(raw_exact)
            interval = c.project_interval(raw, errors['y'] + sigma * forward_bound + rounding, lo, hi)
            if interval['decision'] == 'ambiguous':
                raise Refusal('projection_ambiguous', phase='dual', coordinate=i,
                              center=float(raw), radius=float(errors['y'] + sigma * forward_bound + rounding))
            projected, _ = pair_round(raw - clamp(raw, lo, hi))
            v.append(projected)
            v_local.append(abs(projected - (raw_exact - clamp(raw_exact, lo, hi))))
            self.counters['local_pair_roundings'] += 2
        local['dual'] = max(v_local)
        toward, back = blend_coefficients(state['controller']['since_restart'])
        candidate = deepcopy(state)
        for key, projected, anchor in [('x', u, values['anchor_x']), ('y', v, values['anchor_y'])]:
            ideal_blend = [toward * a + back * b for a, b in zip(projected, anchor)]
            candidate['vectors'][key], local['blend_' + key] = rounded_encode(ideal_blend, p.components)
            self.counters['local_pair_roundings'] += len(ideal_blend)
        candidate['vectors']['bar'] = bar_blocks
        bounds = c.step_error(primal=errors['x'], dual=errors['y'],
                              anchor_primal=errors['anchor_x'], anchor_dual=errors['anchor_y'],
                              norm_a=p.norm_a, norm_at=p.norm_at, error_a=p.error_a, error_at=p.error_at,
                              norm_y=max(map(abs, values['y'])), norm_bar=max(map(abs, bar_stored)),
                              tau=tau, sigma=sigma, toward=toward, back=back, local=local)
        for key, name in [('x', 'primal'), ('y', 'dual'), ('bar', 'extrapolate')]:
            candidate['errors'][key] = c.rational(upward(bounds[name]))
        candidate['controller']['iterations'] += 1
        candidate['controller']['since_restart'] += 1
        c.validate_checkpoint(candidate)
        represented = self.values(candidate)
        actual = {}
        if reference_values is not None:
            for key, reference in zip(('x', 'y', 'bar'), reference_values):
                actual[key] = max(abs(a - b) for a, b in zip(reference, represented[key]))
                if actual[key] > c.read_rational(candidate['errors'][key]):
                    raise Refusal('actual_error_outside_enclosure', vector=key)
        diagnostic = dict(iteration=candidate['controller']['iterations'],
                          error_bounds={k: float(c.read_rational(candidate['errors'][k])) for k in ('x', 'y', 'bar')},
                          actual_errors={k: float(upward(v)) for k, v in actual.items()},
                          local_errors={k: float(upward(v)) for k, v in local.items()},
                          relative_bounds={})
        guard_exceeded = False
        for key in ('x', 'y'):
            factors = model['inverse_scale_' + key]
            norm = max(abs(v * s) for v, s in zip(represented[key], factors))
            relative = c.read_rational(candidate['errors'][key]) * max(factors) / max(1, norm)
            diagnostic['relative_bounds'][key] = float(upward(relative))
            guard_exceeded |= relative > c.ERROR_GUARD
        self.last_diagnostic = diagnostic
        if guard_exceeded:
            raise Refusal('cumulative_enclosure_guard', **diagnostic)
        self.state = candidate
        return diagnostic

    def observe(self):
        before = deepcopy(self.state)
        self.state = c.observe(self.checkpoint, self.state,
                               inverse_scale_x=self.prepared.model['inverse_scale_x'],
                               inverse_scale_y=self.prepared.model['inverse_scale_y'])
        if self.state != before:
            raise Refusal('observation_changed_component_state')
        self.state['controller']['checked_iteration'] = self.state['controller']['iterations']
        self.checkpoint = deepcopy(self.state)
        self.counters['observations'] += 1

    def rollback(self):
        ledger = dict(generation=self.state['generation'], physical_updates=self.counters['physical_updates'],
                      deadline_ns=self.deadline_ns)
        self.state, ledger = c.restore(self.checkpoint, self.state, ledger)
        self.checkpoint = deepcopy(self.state)
        return ledger
