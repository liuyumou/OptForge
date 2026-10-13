"""PR 19 full-range FMA challenge; CPU validation and compile-only resource audit.

This is an additional experiment, not a replacement of the frozen first result.
No CUDA context, runtime selector, controller or performance result is provided.
"""

import argparse
from collections import Counter
import json
from pathlib import Path
import random
import subprocess

import lp_state_admission as admission
from lp_expansion_oracle import power2, round_fraction, primitive_result

ROOT = admission.ROOT
SEED = 17019
SOURCE = ROOT / "tools/diagnostics/lp_state_compact_probe.cu"
HARNESS = ROOT / "tools/diagnostics/lp_state_compact_host.cpp"
FIXTURE = ROOT / "tests/regression/lp-state-review-v1.json"
KERNELS = admission.KERNELS + ["state_compact_fma_p48", "state_compact_fma_p64"]
IDENTITY = "gpup-state-fma-review-v1"
SOURCES = [SOURCE, HARNESS, admission.SOURCE, admission.HARNESS,
           Path(__file__), ROOT / "tools/lp_state_admission.py",
           ROOT / "tools/lp_state_oracle.py", ROOT / "tools/lp_state_candidate.py",
           ROOT / "tools/lp_expansion_candidate.py", ROOT / "tools/lp_expansion_oracle.py",
           admission.FIXTURE, FIXTURE]
FILES = {"sources/" + source.name for source in SOURCES} | {
    "fma-host", "fma-host-ubsan", "fma-probe.cubin", "compiler.log",
    "fma-host-compile.log", "fma-host-ubsan-compile.log", "resources.txt", "instructions.sass"}


def fixture():
    """Independent exact Fraction results, with deterministic boundary strata."""
    rng = random.Random(SEED)
    cases = []
    for precision in (48, 64):
        fmt = (precision, -1022, 1023)
        minimum, maximum = -1022 - (precision - 1), 1023 - (precision - 1)

        def operand(m, e=0, sign=0):
            return round_fraction(m * power2(e), fmt, zero_sign=sign)

        def append(category, a, b, c):
            if any(v["infinity_sign"] for v in (a, b, c)):
                raise ValueError("review generated a nonfinite operand")
            cases.append(dict(category=category, precision=precision,
                              input=[admission.wire(v) for v in (a, b, c)],
                              result=primitive_result("fma", [a, b, c], fmt)))

        # Both even/odd midpoint roundings, with signed tails on either side.
        for sign in (-1, 1):
            for low in (1, 3, 5, 7):
                a = operand(sign * ((1 << (precision - 1)) + low), -(precision - 1))
                b = operand(3, -1)
                append("midpoint", a, b, operand(0))
                for exponent in (minimum, -precision - 321, -precision - 160,
                                 -precision - 1, -precision, -precision + 1):
                    for tail_sign in (-1, 1):
                        append("midpoint", a, b, operand(tail_sign, exponent))
        for sign in (-1, 1):
            for delta in (-1, 0, 1):
                append("overflow", operand(sign * ((1 << precision) - 1), maximum),
                       operand(1), operand(sign * ((1 << (precision - 1)) + delta), maximum - precision))
                for subnormal in (1, 3, 5, (1 << (precision - 1)) - 1):
                    b = (operand((1 << precision) - 1, -precision - 1) if delta < 0
                         else operand((1 << (precision - 1)) + delta, -precision))
                    append("underflow", operand(sign * subnormal, minimum), b, operand(0))

        gaps = (0, 1, precision - 1, precision, precision + 1, 63, 64, 65,
                127, 128, 129, 159, 160, 161, 191, 192, 193, 223, 224, 225,
                255, 256, 257, 287, 288, 289, 319, 320, 321, 512, 768)
        for gap in gaps:
            for product_high in (False, True):
                for a_sign in (-1, 1):
                    for c_sign in (-1, 1):
                        for m in (1 << (precision - 1), (1 << precision) - 1):
                            append("alignment", operand(a_sign * m, -precision),
                                   operand(m, precision if product_high else precision - gap),
                                   operand(c_sign * m, -gap if product_high else 0))
        for sign_a in (0, 1):
            for sign_b in (0, 1):
                for sign_c in (0, 1):
                    append("signed_zero", operand(0, sign=sign_a), operand(0, sign=sign_b),
                           operand(0, sign=sign_c))
                    append("signed_zero", operand(0, sign=sign_a), operand(-1 if sign_b else 1),
                           operand(0, sign=sign_c))
        for index in range(256):
            a = operand(rng.randrange(1 << (precision - 1), 1 << precision), -precision)
            b = operand(rng.randrange(1 << (precision - 1), 1 << precision), -precision)
            product = primitive_result("multiply", [a, b], fmt)
            append("cancellation", a, b,
                   operand(-product["coefficient"] + (index % 3 - 1), product["exponent"]))
        for _ in range(2048):
            triple = []
            for _ in range(3):
                e = rng.choice((minimum, maximum, -precision, rng.randint(minimum, maximum)))
                low = 1 if e == minimum else 1 << (precision - 1)
                m = rng.randrange(low, 1 << precision)
                triple.append(operand(m if rng.randrange(2) else -m, e))
            append("full_range", *triple)
    return dict(schema_version=1, identity=IDENTITY, seed=SEED, cases=cases)


def verify_host(binary, document):
    requests, expected = [], []
    for operation in (2, 4):
        for case in document["cases"]:
            requests.append([operation, case["precision"],
                             *[word for value in case["input"] for word in value]])
            result = case["result"]
            expected.append(None if result["infinity_sign"] else admission.wire(result) + [0])
    process = subprocess.run([str(binary)], input="".join(" ".join(map(str, line)) + "\n" for line in requests),
                             capture_output=True, text=True, timeout=120)
    if process.returncode or process.stderr:
        raise ValueError(f"review host failed ({process.returncode}): {process.stderr}")
    lines = process.stdout.splitlines()
    if len(lines) != len(expected):
        raise ValueError("review host result count")
    for index, (line, result) in enumerate(zip(lines, expected)):
        actual = list(map(int, line.split()))
        if (result is None and (len(actual) != 4 or actual[-1] != 2)) or (result is not None and result != actual):
            raise ValueError("independent review FMA result differs: " + str((index, actual, result)))
    return dict(cases_per_construction=len(document["cases"]),
                constructions=2, comparisons=len(expected),
                categories=dict(sorted(Counter(case["category"] for case in document["cases"]).items())))


def outcome(inventory):
    return {name: inventory[name]["status"] for name in KERNELS}


def verify(path, cuobjdump="/usr/local/cuda/bin/cuobjdump"):
    path = Path(path)
    root = path.parent
    record = admission.read_document(path)
    required = {"schema_version", "identity", "gpu_executed", "gpu_seconds",
                "full_controller_accepted", "device_correctness_accepted", "files",
                "cpu", "ubsan", "original_cases_per_construction", "kernels", "outcome",
                "compiler_command", "host_commands", "nvcc_version", "host_compiler_version"}
    if type(record) is not dict or set(record) != required or type(record["schema_version"]) is not int or record["schema_version"] != 1 or record["identity"] != IDENTITY:
        raise ValueError("review identity/fields")
    if any(record[key] is not False for key in ("gpu_executed", "full_controller_accepted", "device_correctness_accepted")) or type(record["gpu_seconds"]) is not int or record["gpu_seconds"] != 0:
        raise ValueError("review unexecuted work promoted")
    if type(record["files"]) is not dict or set(record["files"]) != FILES:
        raise ValueError("review file inventory")
    for name, digest in record["files"].items():
        if admission.sha(root / name) != digest:
            raise ValueError("review frozen file differs: " + name)
    frozen = root / "sources" / FIXTURE.name
    if frozen.read_text() != admission.encoded(fixture()):
        raise ValueError("review independent fixture differs")
    document = admission.read_document(frozen)
    cpu = verify_host(root / "fma-host", document)
    ubsan = verify_host(root / "fma-host-ubsan", document)
    # Also rerun the historical cases, whose exact bytes remain independently
    # reproducible under the unchanged original seed and fixture identity.
    original = admission.fixture()
    if admission.encoded(original) != (root / "sources" / admission.FIXTURE.name).read_text():
        raise ValueError("review historical fixture differs")
    verify_host(root / "fma-host", {"cases": [dict(category="historical", **case) for case in original["fma_cases"]]})
    resources = subprocess.check_output([cuobjdump, "--dump-resource-usage", str(root / "fma-probe.cubin")], text=True)
    sass = subprocess.check_output([cuobjdump, "--dump-sass", str(root / "fma-probe.cubin")], text=True)
    if resources != (root / "resources.txt").read_text() or sass != (root / "instructions.sass").read_text():
        raise ValueError("review actual image audit differs")
    inventory = admission.resource_audit(resources, (root / "compiler.log").read_text(), sass, KERNELS)
    # Canonical encoding also rejects booleans masquerading as integer counts.
    observed = [cpu, ubsan, len(original["fma_cases"]), inventory, outcome(inventory)]
    reported = [record[key] for key in ("cpu", "ubsan", "original_cases_per_construction", "kernels", "outcome")]
    if admission.encoded(observed) != admission.encoded(reported):
        raise ValueError("review CPU/resource outcome differs")
    return record


def run(output, nvcc, cuobjdump):
    # No retries or reuse of a partial freeze under the same identity.
    output.mkdir(parents=True, exist_ok=False)
    frozen = output / "sources"
    frozen.mkdir()
    if FIXTURE.read_text() != admission.encoded(fixture()):
        raise ValueError("review fixture does not reproduce")
    for source in SOURCES:
        (frozen / source.name).write_bytes(source.read_bytes())
    commands = []
    for name, flags in [("fma-host", ["-O2"]),
                        ("fma-host-ubsan", ["-O1", "-g", "-fsanitize=undefined", "-fno-sanitize-recover=all"])]:
        command = ["g++", *flags, "-Werror", "-Wno-unknown-pragmas", "-std=c++17",
                   str(frozen / HARNESS.name), "-o", str(output / name)]
        commands.append(command)
        compiled_host = subprocess.run(command, capture_output=True, text=True, timeout=120)
        (output / (name + "-compile.log")).write_text(compiled_host.stdout + compiled_host.stderr)
        compiled_host.check_returncode()
    document = admission.read_document(frozen / FIXTURE.name)
    cpu = verify_host(output / "fma-host", document)
    ubsan = verify_host(output / "fma-host-ubsan", document)
    original = admission.fixture()
    verify_host(output / "fma-host", {"cases": [dict(category="historical", **case) for case in original["fma_cases"]]})
    image = output / "fma-probe.cubin"
    command = [nvcc, "--cubin", "-std=c++17", "-arch=sm_120", "-O3", "-lineinfo",
               "-fmad=false", "-ftz=false", "--ptxas-options=-v", str(frozen / SOURCE.name), "-o", str(image)]
    compiled = subprocess.run(command, capture_output=True, text=True, timeout=300)
    (output / "compiler.log").write_text(compiled.stdout + compiled.stderr)
    compiled.check_returncode()
    resources = subprocess.check_output([cuobjdump, "--dump-resource-usage", str(image)], text=True)
    sass = subprocess.check_output([cuobjdump, "--dump-sass", str(image)], text=True)
    (output / "resources.txt").write_text(resources)
    (output / "instructions.sass").write_text(sass)
    inventory = admission.resource_audit(resources, compiled.stdout + compiled.stderr, sass, KERNELS)
    record = dict(schema_version=1, identity=IDENTITY, gpu_executed=False, gpu_seconds=0,
                  full_controller_accepted=False, device_correctness_accepted=False,
                  files={name:admission.sha(output / name) for name in sorted(FILES)},
                  cpu=cpu, ubsan=ubsan, original_cases_per_construction=len(original["fma_cases"]),
                  kernels=inventory, outcome=outcome(inventory), compiler_command=command,
                  host_commands=commands,
                  nvcc_version=subprocess.check_output([nvcc, "--version"], text=True),
                  host_compiler_version=subprocess.check_output(["g++", "--version"], text=True))
    (output / "review.json").write_text(admission.encoded(record))
    return verify(output / "review.json", cuobjdump)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_mutually_exclusive_group()
    actions.add_argument("--write-fixture", action="store_true")
    actions.add_argument("--output", type=Path)
    actions.add_argument("--verify", type=Path)
    parser.add_argument("--nvcc", default="/usr/local/cuda/bin/nvcc")
    parser.add_argument("--cuobjdump", default="/usr/local/cuda/bin/cuobjdump")
    args = parser.parse_args()
    if args.write_fixture:
        with FIXTURE.open("x") as output:
            output.write(admission.encoded(fixture()))
    elif args.verify:
        print(admission.encoded(verify(args.verify, args.cuobjdump)), end="")
    elif args.output:
        print(admission.encoded(run(args.output.resolve(), args.nvcc, args.cuobjdump)), end="")
    else:
        if FIXTURE.read_text() != admission.encoded(fixture()):
            raise ValueError("review fixture does not reproduce")
        print(admission.sha(FIXTURE))


if __name__ == "__main__":
    main()
