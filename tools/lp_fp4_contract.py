"""SPEC-0025 exact CPU oracles; no solver, device execution or certificate issuer."""

from copy import deepcopy
from fractions import Fraction
import hashlib
import json
import math
import struct

from validate_artifacts import validator

MAGNITUDES = tuple(map(Fraction, (0, '0.5', 1, '1.5', 2, 3, 4, 6)))
COMPONENTS = (2, 4, 8)
MIN_EXPONENT, MAX_EXPONENT = -48, 48
ERROR_GUARD = Fraction(1, 10_000_000)


class ContractError(ValueError):
    """A bounded CPU contract refused its input."""


def exact(value):
    if isinstance(value, Fraction):
        return value
    if type(value) not in (int, float) or (type(value) is float and not math.isfinite(value)):
        raise ContractError('finite real required; booleans are not numbers')
    if type(value) is int and abs(value).bit_length() > 256:
        raise ContractError('integer too large')
    return Fraction(value)


def nonnegative(value):
    value = exact(value)
    if value < 0:
        raise ContractError('negative error or norm')
    return value


def rational(value):
    value = nonnegative(value)
    result = dict(numerator=str(value.numerator), denominator=str(value.denominator))
    # Binary64 subnormal inputs need up to 1075 denominator bits. Bound strings,
    # including programmatically supplied Fractions, before serialization.
    if max(map(len, result.values())) > 400:
        raise ContractError('rational exceeds bounded representation')
    return result


def read_rational(value):
    if not isinstance(value, dict) or set(value) != {'numerator', 'denominator'}:
        raise ContractError('invalid rational fields')
    for field in value.values():
        if (not isinstance(field, str) or not 1 <= len(field) <= 400
                or not field.isascii() or not field.isdecimal()
                or (len(field) > 1 and field[0] == '0')):
            raise ContractError('invalid rational integer')
    if int(value['denominator']) == 0:
        raise ContractError('zero denominator')
    result = Fraction(int(value['numerator']), int(value['denominator']))
    if rational(result) != value:
        raise ContractError('noncanonical rational')
    return result


def scale(exponent):
    if type(exponent) is not int or not MIN_EXPONENT <= exponent <= MAX_EXPONENT:
        raise ContractError('scale exponent outside v1 range')
    return Fraction(2) ** exponent


def code_value(code):
    if type(code) is not int or not 0 <= code < 16 or code == 8:
        raise ContractError('invalid or negative-zero E2M1 code')
    return (-1 if code & 8 else 1) * MAGNITUDES[code & 7]


def nearest_code(value):
    value = exact(value)
    if abs(value) > 6:
        raise ContractError('E2M1 overflow')
    # Magnitude-code parity implements ties-to-even at every codebook boundary.
    code = min(range(8), key=lambda i: (abs(abs(value) - MAGNITUDES[i]), i & 1))
    return code | (8 if value < 0 and code else 0)


def pack(codes):
    codes = list(codes)
    for code in codes:
        code_value(code)
    return bytes(codes[i] | ((codes[i + 1] if i + 1 < len(codes) else 0) << 4)
                 for i in range(0, len(codes), 2)).hex()


def unpack(data_hex, length):
    if type(length) is not int or not 1 <= length <= 1024:
        raise ContractError('invalid block length')
    if (not isinstance(data_hex, str) or len(data_hex) != 2 * ((length + 1) // 2)
            or any(c not in '0123456789abcdef' for c in data_hex)):
        raise ContractError('noncanonical packed bytes')
    data = bytes.fromhex(data_hex)
    if length % 2 and data[-1] >> 4:
        raise ContractError('nonzero padding nibble')
    result = [(data[i // 2] >> (4 * (i % 2))) & 15 for i in range(length)]
    for code in result:
        code_value(code)
    return result


def encode(values, components):
    values = list(values)
    if type(components) is not int or components not in COMPONENTS:
        raise ContractError('unsupported component count')
    if not 1 <= len(values) <= 1024:
        raise ContractError('invalid block length')
    residual = list(map(exact, values))
    planes = []
    for _ in range(components):
        largest = max(map(abs, residual))
        exponent = MIN_EXPONENT
        while exponent < MAX_EXPONENT and largest > 6 * scale(exponent):
            exponent += 1
        if largest > 6 * scale(exponent):
            raise ContractError('component scale overflow: native escalation required')
        codes = [nearest_code(v / scale(exponent)) for v in residual]
        planes.append(dict(exponent=exponent, data_hex=pack(codes)))
        residual = [v - scale(exponent) * code_value(c) for v, c in zip(residual, codes)]
    return dict(length=len(values), planes=planes,
                remainder_bound=rational(max(map(abs, residual))))


def decode(block):
    if not isinstance(block, dict) or set(block) != {'length', 'planes', 'remainder_bound'}:
        raise ContractError('invalid block fields')
    length = block['length']
    if type(length) is not int or not 1 <= length <= 1024:
        raise ContractError('invalid block length')
    if not isinstance(block['planes'], list) or len(block['planes']) not in COMPONENTS:
        raise ContractError('invalid component count')
    read_rational(block['remainder_bound'])
    result = [Fraction(0)] * length
    for plane in block['planes']:
        if not isinstance(plane, dict) or set(plane) != {'exponent', 'data_hex'}:
            raise ContractError('invalid plane fields')
        factor = scale(plane['exponent'])
        codes = unpack(plane['data_hex'], length)
        result = [v + factor * code_value(c) for v, c in zip(result, codes)]
    return result


def transpose_tile(block):
    decode(block)
    if block['length'] != 1024:
        raise ContractError('matrix tile must be 32 by 32')
    result = deepcopy(block)
    for plane in result['planes']:
        codes = unpack(plane['data_hex'], 1024)
        plane['data_hex'] = pack(codes[c * 32 + r] for r in range(32) for c in range(32))
    return result


def tile_errors(original, block):
    if len(original) != 1024 or block['length'] != 1024:
        raise ContractError('matrix tile must be 32 by 32')
    errors = [abs(exact(a) - b) for a, b in zip(original, decode(block))]
    return (max(sum(errors[r * 32:(r + 1) * 32]) for r in range(32)),
            max(sum(errors[c::32]) for c in range(32)))


def group_product(left, right, left_exponent, right_exponent):
    """Mathematical oracle, NOT an assertion about an actual MMA instruction."""
    if len(left) != 32 or len(right) != 32:
        raise ContractError('exactly 32 contraction terms required')
    integer = sum(4 * code_value(a) * code_value(b) for a, b in zip(left, right))
    if integer.denominator != 1 or abs(integer) > 4608:
        raise ContractError('group invariant violated')
    return integer * scale(left_exponent) * scale(right_exponent) / 4


def project_interval(center, error, lower=None, upper=None):
    center, error = exact(center), nonnegative(error)
    lower = None if lower is None else exact(lower)
    upper = None if upper is None else exact(upper)
    if lower is not None and upper is not None and lower > upper:
        raise ContractError('reversed bounds')

    def clamp(value):
        if lower is not None:
            value = max(lower, value)
        if upper is not None:
            value = min(upper, value)
        return value

    lo, hi = center - error, center + error
    if lower is not None and lower == upper:
        decision = 'fixed'
    elif lower is not None and hi <= lower:
        decision = 'lower'
    elif upper is not None and lo >= upper:
        decision = 'upper'
    elif (lower is None or lo >= lower) and (upper is None or hi <= upper):
        decision = 'interior'
    else:
        decision = 'ambiguous'
    return dict(lower=clamp(lo), upper=clamp(hi), decision=decision)


def product_error(operator_norm, operator_error, state_norm, state_error, compute_error):
    a, da, x, ex, ec = map(nonnegative,
                         (operator_norm, operator_error, state_norm, state_error, compute_error))
    return da * x + a * ex + ec


def step_error(*, primal, dual, anchor_primal, anchor_dual, norm_a, norm_at,
               error_a, error_at, norm_y, norm_bar, tau, sigma, toward, back, local):
    required = {'transpose', 'primal', 'extrapolate', 'forward', 'dual', 'blend_x', 'blend_y'}
    if set(local) != required:
        raise ContractError('every local error term is required')
    local = {k: nonnegative(v) for k, v in local.items()}
    primal, dual, anchor_primal, anchor_dual = map(
        nonnegative, (primal, dual, anchor_primal, anchor_dual))
    tau, sigma = exact(tau), exact(sigma)
    toward, back = exact(toward), exact(back)
    if tau <= 0 or sigma <= 0 or toward < 0 or back < 0 or toward > 1 or back > 1:
        raise ContractError('invalid step/blend coefficients')
    u = primal + tau * product_error(norm_at, error_at, norm_y, dual, local['transpose'])
    u += local['primal']
    bar = 2 * u + primal + local['extrapolate']
    v = dual + sigma * product_error(norm_a, error_a, norm_bar, bar, local['forward'])
    v += local['dual']
    # V1 keeps a conservative monotone envelope across observation windows.
    return dict(primal=max(primal, toward * u + back * anchor_primal + local['blend_x']),
                dual=max(dual, toward * v + back * anchor_dual + local['blend_y']), extrapolate=bar)


def original_error(error, inverse_scale):
    inverse_scale = exact(inverse_scale)
    if inverse_scale <= 0:
        raise ContractError('inverse scaling must be positive')
    return nonnegative(error) * inverse_scale


def float_bits(value):
    checked = exact(value)
    value = value if type(value) is float else float(checked)
    if not math.isfinite(value):
        raise ContractError('nonfinite binary64 scalar')
    return struct.pack('>d', value).hex()


def read_float_bits(value):
    if (not isinstance(value, str) or len(value) != 16
            or any(c not in '0123456789abcdef' for c in value)):
        raise ContractError('invalid binary64 bits')
    number = struct.unpack('>d', bytes.fromhex(value))[0]
    exact(number)
    return number


def schema_check(name, value):
    errors = list(validator(name).iter_errors(value))
    if errors:
        raise ContractError(f'{name}: {errors[0].message}')


def validate_checkpoint(state):
    schema_check('lp-fp4-checkpoint-v1.schema.json', state)
    counters = [state[k] for k in ('rows', 'columns', 'components', 'generation')]
    counters.extend(state['controller'][k] for k in (
        'iterations', 'restarts', 'since_restart', 'checked_iteration'))
    if any(type(value) is not int for value in counters):
        raise ContractError('checkpoint counters must be integers')
    n, m = state['columns'], state['rows']
    for key, length in [('x', n), ('y', m), ('bar', n), ('anchor_x', n), ('anchor_y', m)]:
        blocks = state['vectors'][key]
        if len(blocks) != (length + 31) // 32:
            raise ContractError('vector block count mismatch')
        values = []
        for block in blocks:
            if block['length'] != 32 or len(block['planes']) != state['components']:
                raise ContractError('vector block/component mismatch')
            values.extend(decode(block))
        if any(values[length:]):
            raise ContractError('nonzero vector padding')
    for value in state['errors'].values():
        read_rational(value)
    for key, blocks in state['vectors'].items():
        if read_rational(state['errors'][key]) < max(
                read_rational(b['remainder_bound']) for b in blocks):
            raise ContractError('enclosure omits representation remainder')
    control = state['controller']
    for key in ('weight', 'integral', 'anchor_error', 'last_check_error', 'previous_error'):
        if control[key] is not None:
            read_float_bits(control[key])
    if read_float_bits(control['weight']) <= 0:
        raise ContractError('controller weight must be positive')
    if (control['checked_iteration'] > control['iterations']
            or control['since_restart'] > control['iterations']):
        raise ContractError('invalid controller counters')
    return deepcopy(state)


def snapshot(state):
    validate_checkpoint(state)
    result, rounding = {}, {}
    for key, length in [('x', state['columns']), ('y', state['rows'])]:
        values = [v for b in state['vectors'][key] for v in decode(b)][:length]
        floats = list(map(float, values))
        if not all(math.isfinite(v) for v in floats):
            raise ContractError('snapshot overflow')
        result[key] = floats
        rounding[key] = max((abs(v - Fraction(f)) for v, f in zip(values, floats)), default=Fraction(0))
    return result, rounding


def observe(checkpoint, candidate, *, inverse_scale_x, inverse_scale_y, cancelled=False):
    """Validate observation only. The caller still owes original-model checking.

    Both enclosure guards use original units. Scale arguments are either a
    uniform scalar or the complete positive inverse scaling vector.
    """
    checkpoint, candidate = validate_checkpoint(checkpoint), validate_checkpoint(candidate)
    for field in ('binding', 'rows', 'columns', 'components', 'generation'):
        if checkpoint[field] != candidate[field]:
            raise ContractError('transaction identity or generation mismatch')
    start, end = checkpoint['controller']['iterations'], candidate['controller']['iterations']
    boundary = 200 - start % 200
    if not 0 < end - start <= boundary:
        raise ContractError('audit window exceeds controller boundary')
    if candidate['controller']['checked_iteration'] != checkpoint['controller']['checked_iteration']:
        raise ContractError('observation must precede controller adoption')
    for key in ('x', 'y'):
        if read_rational(candidate['errors'][key]) < read_rational(checkpoint['errors'][key]):
            raise ContractError('observation cannot reduce the cumulative v1 enclosure')
    for key in ('anchor_x', 'anchor_y'):
        if (candidate['vectors'][key] != checkpoint['vectors'][key]
                or candidate['errors'][key] != checkpoint['errors'][key]):
            raise ContractError('restart anchors require an explicit controller transition')
    for key in ('weight', 'integral', 'previous_error', 'anchor_error', 'last_check_error', 'restarts'):
        if candidate['controller'][key] != checkpoint['controller'][key]:
            raise ContractError('controller fields changed before observation')
    if candidate['controller']['since_restart'] - checkpoint['controller']['since_restart'] != end - start:
        raise ContractError('restart counter disagrees with attempted window')
    if cancelled:
        raise ContractError('cancelled observation')
    values, rounding = snapshot(candidate)
    for key, factor in [('x', inverse_scale_x), ('y', inverse_scale_y)]:
        factors = factor if isinstance(factor, list) else [factor] * len(values[key])
        if len(factors) != len(values[key]):
            raise ContractError('inverse scaling shape mismatch')
        factors = list(map(exact, factors))
        if any(s <= 0 for s in factors):
            raise ContractError('inverse scaling must be positive')
        error = original_error(read_rational(candidate['errors'][key]) + rounding[key], max(factors))
        norm = max(abs(exact(v) * s) for v, s in zip(values[key], factors))
        if error > ERROR_GUARD * max(1, norm):
            raise ContractError('original-unit cumulative error guard exceeded')
    return candidate  # Deliberately no decode/re-encode/adoption of the snapshot.


def restore(checkpoint, current, ledger):
    checkpoint, current = validate_checkpoint(checkpoint), validate_checkpoint(current)
    for field in ('binding', 'rows', 'columns'):
        if checkpoint[field] != current[field]:
            raise ContractError('rollback identity mismatch')
    if (set(ledger) != {'generation', 'physical_updates', 'deadline_ns'}
            or any(type(v) is not int or v < 0 for v in ledger.values())
            or ledger['generation'] != current['generation']
            or current['generation'] < checkpoint['generation']
            or ledger['physical_updates'] < current['controller']['iterations']):
        raise ContractError('invalid external work ledger')
    result, next_ledger = deepcopy(checkpoint), deepcopy(ledger)
    next_ledger['generation'] += 1
    result['generation'] = next_ledger['generation']
    validate_checkpoint(result)
    return result, next_ledger


def progress_action(residuals, components, certified=False):
    if type(components) is not int or components not in COMPONENTS:
        raise ContractError('unsupported component count')
    residuals = list(map(nonnegative, residuals))
    if certified:
        return 'complete'
    if len(residuals) >= 4 and all(b > Fraction(9, 10) * a
                                   for a, b in zip(residuals[-4:-1], residuals[-3:])):
        return {2: 'promote_4', 4: 'promote_8', 8: 'native'}[components]
    return 'continue'


def payload_bytes(length, components):
    if (type(length) is not int or not 1 <= length <= 1024
            or type(components) is not int or components not in COMPONENTS):
        raise ContractError('invalid payload shape')
    return dict(packed=((length + 1) // 2) * components, scales=components)


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                     allow_nan=False).encode()).hexdigest()
