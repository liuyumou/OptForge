"""Canonical fixture adapter and one new proof attempt; v1 evidence is immutable."""
import json
from pathlib import Path
import subprocess
import sys
import time

import lp_tensor_expanded_proof as retained
import lp_tensor_expanded_recovery as recovery

a = retained.authority
BASE = recovery.BASE
FORMAT = retained.FORMAT


def validate_operand(d):
    n, e, s = d['coefficient'], d['exponent'], d['zero_sign']
    a.require(type(n) is int and type(e) is int and type(s) is int, 'noninteger field')
    a.require(s in (0, 1) and not d.get('infinity_sign') and not d.get('invalid'),
              'nonfinite or invalid operand')
    a.require((n == 0 and e == 0) or
              (0 < abs(n) < 1 << 64 and -1085 <= e <= 960 and
               (e == -1085 or abs(n) >= 1 << 63)), 'noncanonical operand')


def scalar_cases():
    # Preserve the exact values, seed, ordering and count of v1's intended cases.
    # Renormalize AFTER the directed exponent substitution, without any rounding.
    cases = []
    for row in retained.scalar_cases():
        normalized = []
        for d in row:
            c = retained.operand(d['coefficient'], d['exponent'], d['zero_sign'])
            a.require(retained.value(c) == retained.value(d), 'fixture value changed')
            validate_operand(c)
            normalized.append(c)
        cases.append(normalized)
    return cases


def serialize(cases):
    rows = []
    for case in cases:
        a.require(len(case) == 3, 'wrong operand count')
        fields = []
        for d in case:
            validate_operand(d)
            fields.extend([abs(d['coefficient']), d['exponent'],
                           int(d['coefficient'] < 0) if d['coefficient'] else d['zero_sign']])
        rows.append(' '.join(map(str, fields)))
    return '\n'.join(rows)+'\n'


def subprocess_record(label, command, **kwargs):
    start = time.monotonic_ns()
    try:
        p = subprocess.run(command, capture_output=True, text=True, **kwargs)
    except subprocess.TimeoutExpired as error:
        out = error.stdout or b''
        err = error.stderr or b''
        if isinstance(out, bytes): out = out.decode(errors='replace')
        if isinstance(err, bytes): err = err.decode(errors='replace')
        (BASE/(label+'.stdout')).write_text(out)
        (BASE/(label+'.stderr')).write_text(err)
        a.put(BASE/(label+'.json'), dict(command=command, returncode=None,
            timeout=True, elapsed_ns=time.monotonic_ns()-start,
            stdout=a.ref(BASE/(label+'.stdout')), stderr=a.ref(BASE/(label+'.stderr'))))
        raise
    (BASE/(label+'.stdout')).write_text(p.stdout)
    (BASE/(label+'.stderr')).write_text(p.stderr)
    a.put(BASE/(label+'.json'), dict(command=command, returncode=p.returncode,
        timeout=False, elapsed_ns=time.monotonic_ns()-start,
        stdout=a.ref(BASE/(label+'.stdout')), stderr=a.ref(BASE/(label+'.stderr'))))
    return p


def preflight():
    reused = recovery.preservation()
    original = (a.BASE/'scalar-input-v1.txt').read_text().splitlines()
    cases = scalar_cases()
    data = serialize(cases)
    rows = data.splitlines()
    a.require(len(cases) == len(original) == 7376, 'corpus count changed')
    changes = []
    for index, (old, new) in enumerate(zip(original, rows)):
        left, right = list(map(int, old.split())), list(map(int, new.split()))
        for offset in range(0, 9, 3):
            m, e, s = left[offset:offset+3]
            n, f, t = right[offset:offset+3]
            a.require(s == t and m*retained.independent.power2(e) ==
                      n*retained.independent.power2(f), 'changed fixture value/sign')
        if left != right: changes.append(index)
    a.require(18 in changes, 'retained counterexample not corrected')
    a.require(rows[18].endswith('17170124791618716040 -64 1'), 'wrong counterexample normalization')
    (BASE/'scalar-input-v2.txt').write_text(data)
    binary = BASE/'expanded-scalar-host-v2'
    command = ['g++', '-std=c++17', '-O2', '-ffp-contract=off', '-fno-fast-math',
        '-fsanitize=undefined', '-fno-sanitize-recover=all', '-Wno-unknown-pragmas',
        str(a.ROOT/'tools/diagnostics/lp_tensor_expanded_host_v2.cpp'), '-o', str(binary)]
    built = subprocess_record('scalar-build-v2', command, timeout=120)
    a.require(built.returncode == 0, 'harness compile failed: '+built.stderr)
    # Parser-only regression cases: reject before invoking candidate arithmetic.
    bad = [original[18]+'\n', '0 0 0\n', '-1 0 0 0 0 0 0 0 0\n',
           str(1 << 64)+' 0 0 0 0 0 0 0 0\n',
           '0 1 0 0 0 0 0 0 0\n', '0 0 2 0 0 0 0 0 0\n',
           '0 0 0 0 0 0 0 0 0 trailing\n', '\n']
    for index, text in enumerate(bad):
        p = subprocess_record('parser-negative-'+str(index), [str(binary)], input=text, timeout=5)
        a.require(p.returncode == 2 and 'input 1' in p.stderr and not p.stdout,
                  'missing indexed parser rejection')
    bindings = [a.ref(a.ROOT/path) for path in [
        'tools/lp_tensor_expanded_proof_v2.py', 'tools/diagnostics/lp_tensor_expanded_host_v2.cpp',
        'tools/lp_tensor_expanded_proof.py', 'tools/lp_tensor_expanded_cpu.py',
        'tools/lp_expansion_oracle.py', 'tools/lp_expansion_candidate.py',
        'tools/diagnostics/lp_state_compact_probe.cu', 'tools/diagnostics/lp_state_integer_probe.cu',
        'cuda/lp_pdhg_tensor_expanded/expanded_fast.h']]
    a.put(BASE/'preflight-v2.json', dict(status='passed', cases=len(cases),
        exact_value_and_sign_preserved=True, corrected_indices=changes,
        negative_parser_cases=len(bad), binary=a.ref(binary),
        input=a.ref(BASE/'scalar-input-v2.txt'), sources=bindings, reused_checks=reused,
        scalar_proof_executed=False, passed_checks_rerun=False, gpu_seconds=0))
    print('Canonical input preflight, exact-value preservation, UBSan compilation and eight indexed parser rejections pass.', flush=True)


def scalar_proof():
    pre = a.read(BASE/'preflight-v2.json')
    for item in pre['sources']: a.checked(item)
    binary, input_path = a.checked(pre['binary']), a.checked(pre['input'])
    cases = scalar_cases()
    data = input_path.read_text()
    a.require(serialize(cases) == data, 'frozen corpus differs')
    process = subprocess_record('scalar-execution-v2', [str(binary)], input=data, timeout=120)
    a.require(process.returncode == 0, 'scalar worker exit '+str(process.returncode)+': '+process.stderr)
    lines = process.stdout.splitlines()
    a.require(len(lines) == len(cases), 'scalar output count differs')
    fast = 0
    for index, (case, line) in enumerate(zip(cases, lines)):
        got = tuple(map(int, line.split()))
        a.require(len(got) == 5, 'malformed output at '+str(index))
        expected = retained.independent.primitive_result('fma', case, FORMAT)
        m, e, s, g, f = got
        fast += f
        wanted = (abs(expected['coefficient']), expected['exponent'] if expected['coefficient'] else 0,
                  int(expected['coefficient'] < 0) if expected['coefficient'] else expected['zero_sign'])
        passed = g == 2 if expected['infinity_sign'] else g == 0 and (m,e,s) == wanted
        if not passed:
            a.put(BASE/'scalar-counterexample-v2.json', dict(index=index, operands=case,
                expected=expected, actual=got, independently_compared_before_failure=index,
                input=a.ref(input_path), binary=a.ref(binary)))
            raise AssertionError('independent scalar mismatch at '+str(index))
    a.require(2000 < fast < len(cases), 'fast/fallback coverage differs')
    return dict(cases=len(cases), fast_cases=fast, fallback_cases=len(cases)-fast,
                binary=a.ref(binary), input=a.ref(input_path),
                output=a.ref(BASE/'scalar-execution-v2.stdout'))


def proof():
    try:
        scalar = scalar_proof()
        a.put(BASE/'scalar-pass-v2.json', dict(status='passed', **scalar))
        print('All '+str(scalar['cases'])+' independent scalar comparisons pass.', flush=True)
        products = retained.product_conversion_proof()
        a.put(BASE/'product-conversion-pass-v2.json', dict(status='passed', **products))
        projection = retained.projection_proof()
        a.put(a.DATA/'independent-proof-v2.json', dict(status='passed', scalar=scalar,
            products=products, projection=projection, gpu_seconds=0, historical_checks_rerun=False,
            preflight=a.ref(BASE/'preflight-v2.json'), proof_source=a.ref(Path(__file__).resolve())))
        print(json.dumps(dict(status='passed', scalar=scalar['cases'], products=products, projection=projection)), flush=True)
    except BaseException as error:
        a.put(a.DATA/'independent-proof-refusal-v2.json', dict(status='refused', reason=str(error),
            exception=type(error).__name__, gpu_seconds=0,
            proof_source=a.ref(Path(__file__).resolve()), preflight=a.ref(BASE/'preflight-v2.json')))
        raise


if __name__ == '__main__':
    if sys.argv[1] == 'preflight': preflight()
    elif sys.argv[1] == 'proof': proof()
    else: raise SystemExit('unknown action')
