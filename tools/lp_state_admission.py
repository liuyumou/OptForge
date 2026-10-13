"""Reproducible CPU/resource admission; never acquires a GPU or launches kernels.

The resource construction may refuse. Such a refusal is neither a solver failure
nor evidence that a different sticky-tail/global-scratch implementation cannot
qualify. The frozen development study remains unadmitted when this gate fails.
"""

import argparse
import hashlib
import json
import math
from pathlib import Path
import random
import re
import subprocess
import sys

from lp_state_oracle import FORMATS, expected, power2, round_fraction
from lp_expansion_oracle import primitive_result

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "tools/diagnostics/lp_state_integer_probe.cu"
HARNESS = ROOT / "tools/diagnostics/lp_state_integer_host.cpp"
FIXTURE = ROOT / "tests/regression/lp-state-admission-v1.json"
KERNELS = ["state_integer_p48", "state_integer_p64", "state_update_p48",
           "state_update_p64", "state_full_fma_p48", "state_full_fma_p64"]
SEED = 17004
FROZEN_FILES = {"compiler.log", "instructions.sass", "integer-host",
                "integer-probe.cubin", "resources.txt"} | {
    "sources/" + name for name in [SOURCE.name, HARNESS.name, FIXTURE.name,
        "lp_state_admission.py", "lp_state_oracle.py", "lp_state_candidate.py",
        "lp_expansion_oracle.py", "lp_expansion_candidate.py"]}


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n"


def read_document(path):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate admission field")
            result[key] = value
        return result
    return json.loads(Path(path).read_text(), object_pairs_hook=unique)


def validate_record_header(record):
    required = {"schema_version", "identity", "status", "cpu_counts", "fixture_sha256",
                "source_sha256", "host_source_sha256", "host_binary_sha256", "image_sha256",
                "nvcc_version", "compiler_command", "kernels", "gpu_executed", "gpu_seconds",
                "solver_implemented", "full_controller_accepted", "primary_attempts",
                "planned_primary_attempts", "planned_profiles", "files"}
    if type(record) is not dict or set(record) != required:
        raise ValueError("admission fields")
    for key in ["schema_version", "gpu_seconds", "primary_attempts", "planned_primary_attempts", "planned_profiles"]:
        if type(record[key]) is not int or record[key] < 0:
            raise ValueError("admission integer field")
    if record["schema_version"] != 1 or record["identity"] != "gpup-state-resource-admission-v1":
        raise ValueError("admission identity")
    for key in ["gpu_executed", "solver_implemented", "full_controller_accepted"]:
        if record[key] is not False:
            raise ValueError("unexecuted work promoted")
    if record["gpu_seconds"] != 0 or record["primary_attempts"] != 0:
        raise ValueError("unexecuted work promoted")
    if record["planned_primary_attempts"] != 96 or record["planned_profiles"] != 12:
        raise ValueError("planned study differs")
    if record["status"] not in {"refused_resource", "refused_instruction", "partial_refusal", "resource_gate_only_passed"}:
        raise ValueError("admission status")
    for key in ["fixture_sha256", "source_sha256", "host_source_sha256", "host_binary_sha256", "image_sha256"]:
        if type(record[key]) is not str or not re.fullmatch(r"[0-9a-f]{64}", record[key]):
            raise ValueError("admission hash field")
    counts = record["cpu_counts"]
    if type(counts) is not dict or set(counts) != {"integer_cases", "fma_cases", "update_cases"} or any(type(n) is not int or n < 0 for n in counts.values()):
        raise ValueError("admission count field")
    if type(record["files"]) is not dict or type(record["kernels"]) is not dict or set(record["kernels"]) != set(KERNELS):
        raise ValueError("admission inventory")
    for item in record["kernels"].values():
        if type(item) is not dict:
            raise ValueError("admission kernel fields")
        for key in ["registers", "stack_bytes", "local_bytes", "shared_bytes", "spill_store_bytes", "spill_load_bytes"]:
            if type(item.get(key)) is not int or item[key] < 0:
                raise ValueError("admission resource integer field")
    if set(record["files"]) != FROZEN_FILES or any(
            type(digest) is not str or not re.fullmatch(r"[0-9a-f]{64}", digest)
            for digest in record["files"].values()):
        raise ValueError("admission file inventory")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def words(value):
    return [(value >> (32 * k)) & 0xffffffff for k in range(10)]


def wire(value):
    return [abs(value["coefficient"]), value["exponent"],
            int(value["coefficient"] < 0) if value["coefficient"] else value["zero_sign"]]


def fixture():
    rng = random.Random(SEED)
    integer_cases = []
    for bits in [0, 1, 31, 32, 63, 64, 127, 128, 255, 272, 319, 320]:
        for _ in range(8):
            a = rng.getrandbits(bits)
            b = rng.getrandbits(max(1, bits)) or 1
            root = math.isqrt(a)
            integer_cases.append(dict(operation=0, input=words(a) + words(b), result=words(root) + words(a - root * root)))
            q, r = divmod(a, b)
            integer_cases.append(dict(operation=1, input=words(a) + words(b), result=words(q) + words(r)))
    fma_cases, update_cases, transcendental_cases = [], [], []
    for name in ["compensated-pair", "expansion64"]:
        fmt = FORMATS[name]
        precision = fmt[0]
        minimum, maximum = -1022 - (precision - 1), 1023 - (precision - 1)
        def operand(n, e=0, zero_sign=0):
            return round_fraction(n * power2(e), fmt, zero_sign=zero_sign)
        low = operand(1, minimum)
        high = operand((1 << precision) - 1, maximum)
        one, zero = operand(1), operand(0)
        negative_zero = operand(0, zero_sign=1)
        triples = [(low, low, high), (high, high, low),
                   (high, one, operand(-((1 << precision) - 1), maximum)),
                   (negative_zero, one, negative_zero), (negative_zero, one, zero),
                   (low, operand(-1), zero),
                   (operand(3), operand(7), operand(-21))]
        for _ in range(128):
            values = []
            for _ in range(3):
                m = rng.randrange(1 << (precision - 1), 1 << precision)
                e = rng.choice([minimum, maximum, -precision, rng.randint(minimum, maximum)])
                values.append(operand(m if rng.randrange(2) else -m, e))
            triples.append(tuple(values))
        for triple in triples:
            result = primitive_result("fma", list(triple), fmt)
            fma_cases.append(dict(precision=precision, input=[wire(v) for v in triple], result=result))
        # Small unprojected primal/Halpern graph, each primitive rounded separately.
        for index in range(32):
            values = [operand((index % 9) - 4, -2), operand(1, -1),
                      operand(index % 3, -2), operand(1, -2), operand(3, -1),
                      operand(index + 1), operand(index + 2), operand(-1, -1)]
            def op(operation, *args):
                operation = {"div": "divide", "sub": "subtract", "mul": "multiply"}.get(operation, operation)
                return primitive_result(operation, list(args), fmt)
            step = op("div", values[3], values[4])
            gradient = op("sub", values[1], values[2])
            next_value = op("sub", values[0], op("mul", step, gradient))
            result = op("add", op("mul", op("div", values[5], values[6]), next_value),
                        op("mul", op("div", one, values[6]), values[7]))
            update_cases.append(dict(precision=precision, input=[wire(v) for v in values], result=result))
    for name, fmt in FORMATS.items():
        for operation, inputs in [("ln", [(1, 0), (3, -1), (7, -3), (1, -1085),
                                         ((1 << 63) + 1, -63), ((1 << 64) - 1, -63), (1, 1023)]),
                                  ("exp", [(0, 0), (1, 0), (-1, 0), (1, -63), (-1, -63),
                                           (13, 0), (-13, 0), (-700, 0), (700, 0)])]:
            for n, e in inputs:
                # Exact dyadic operand, not pre-rounded to an input format.
                document = dict(coefficient=n, exponent=e, zero_sign=0, infinity_sign=0,
                                invalid=False, flags=[], error_exponent=None)
                transcendental_cases.append(dict(format=name, operation=operation, input=document,
                                                  result=expected(operation, document, fmt)))
    return dict(schema_version=1, identity="lp-state-cpu-admission-v1", seed=SEED,
                integer_cases=integer_cases, fma_cases=fma_cases, update_cases=update_cases,
                transcendental_cases=transcendental_cases)


def verify_host(binary, document):
    requests, results = [], []
    for case in document["integer_cases"]:
        requests.append([case["operation"], *case["input"]])
        results.append(case["result"])
    for operation, key in [(2, "fma_cases"), (3, "update_cases")]:
        for case in document[key]:
            requests.append([operation, case["precision"], *[v for item in case["input"] for v in item]])
            expected_value = case["result"]
            results.append(None if expected_value["infinity_sign"] else wire(expected_value) + [0])
    data = "".join(" ".join(map(str, request)) + "\n" for request in requests)
    process = subprocess.run([str(binary)], input=data, text=True, capture_output=True, check=True, timeout=120)
    lines = process.stdout.splitlines()
    if len(lines) != len(results):
        raise ValueError("host receipt count differs")
    for index, (line, result) in enumerate(zip(lines, results)):
        actual = list(map(int, line.split()))
        if result is None:
            if len(actual) != 4 or actual[-1] != 2:
                raise ValueError("overflow receipt differs: " + str(index))
        elif actual != result:
            raise ValueError("independent integer/Fraction result differs: " + str((index, actual, result)))
    return {key: len(document[key]) for key in ["integer_cases", "fma_cases", "update_cases"]}


def verify_transcendentals(source_directory, document):
    """Execute the frozen candidate, then compare with independent fixture values.

    Isolated Python prevents the current checkout or PYTHONPATH from supplying
    the candidate. Historical v1 counts are preserved; this is an additional
    verification obligation, not a rewrite of the frozen admission receipt.
    """
    script = """
import json, sys
sys.path.insert(0, sys.argv[1])
import lp_expansion_candidate as arithmetic
import lp_state_candidate as candidate
formats = {"matched-fp64": arithmetic.BINARY64,
           "compensated-pair": candidate.PAIR48,
           "expansion64": arithmetic.EXPANSION64}
results = []
for case in json.load(sys.stdin):
    function = {"ln": candidate.logarithm, "exp": candidate.exponential}[case["operation"]]
    results.append(function(arithmetic.load_rounded(case["input"]),
                            formats[case["format"]]).document())
print(json.dumps(results, sort_keys=True, separators=(",", ":")))
"""
    cases = document["transcendental_cases"]
    process = subprocess.run([sys.executable, "-I", "-B", "-c", script,
                              str(Path(source_directory).resolve())],
                             input=encoded(cases), text=True, capture_output=True,
                             check=True, timeout=120)
    if process.stdout.strip() != encoded([case["result"] for case in cases]).strip():
        raise ValueError("independent transcendental result differs")
    return len(cases)


def resource_audit(resources, compiler_log, sass, kernels=KERNELS):
    inventory = {}
    for name in kernels:
        props = re.search(r"Function " + name + r":\s+REG:(\d+) STACK:(\d+) SHARED:(\d+) LOCAL:(\d+)", resources)
        spills = re.search(r"Function properties for " + name + r"\s+(\d+) bytes stack frame, (\d+) bytes spill stores, (\d+) bytes spill loads", compiler_log)
        body = re.search(r"Function : " + name + r"\s+(.*?)(?=Function :|\Z)", sass, re.S)
        if not props or not spills or not body:
            raise ValueError("incomplete generated-code receipt: " + name)
        instructions = []
        # Parse every addressed instruction, including uniform predicates. Never
        # treat an unrecognized line as absence of a forbidden operation.
        for line in re.findall(r"^\s*/\*[0-9a-fA-F]+\*/([^\n]*)", body.group(1), re.M):
            instruction = re.fullmatch(
                r"\s*(?:@!?(?:U?P\d+|U?PT)\s+)?([A-Z][A-Z0-9_.]*)(?:\s+[^;]*)?;.*", line)
            if not instruction or re.fullmatch(r"U?[RP]\d+", instruction.group(1)):
                raise ValueError("empty instruction or unparsed instruction receipt")
            instructions.append(instruction.group(1))
        if not instructions:
            raise ValueError("empty instruction receipt")
        forbidden = sorted({i for i in instructions if i.startswith(("DADD", "DMUL", "DFMA", "DSETP", "DSET", "DMNMX", "DMMA", "CALL", "JCAL")) or re.search(r"(?:F2F|I2F|F2I).*F64", i)})
        registers, stack, shared, local = map(int, props.groups())
        compiler_stack, stores, loads = map(int, spills.groups())
        if compiler_stack != stack:
            raise ValueError("compiler/image stack mismatch")
        reasons = []
        if registers > 128:
            reasons.append("register_limit")
        if stack or local or stores or loads:
            reasons.append("compiler_spills")
        if forbidden:
            reasons.append("native_fp64_or_unaudited_call")
        inventory[name] = dict(registers=registers, stack_bytes=stack, local_bytes=local,
                               shared_bytes=shared, spill_store_bytes=stores, spill_load_bytes=loads,
                               forbidden_instructions=forbidden,
                               instruction_counts={i: instructions.count(i) for i in sorted(set(instructions))},
                               status="refused" if reasons else "fits_resource_gate", reasons=reasons)
    return inventory


def admission_status(inventory):
    required = [inventory[name] for name in ["state_full_fma_p48", "state_full_fma_p64"]]
    if any(item["forbidden_instructions"] for item in inventory.values()):
        return "refused_instruction"
    if all(set(item["reasons"]) & {"register_limit", "compiler_spills"} for item in required):
        return "refused_resource"
    if any(item["status"] == "refused" for item in inventory.values()):
        return "partial_refusal"
    return "resource_gate_only_passed"


def verify_admission(path, cuobjdump="/usr/local/cuda/bin/cuobjdump"):
    """Recheck frozen file identities, CPU results and the complete resource audit."""
    path = Path(path)
    root = path.parent
    record = read_document(path)
    validate_record_header(record)
    for name, digest in record["files"].items():
        relative = Path(name)
        if relative.is_absolute() or ".." in relative.parts or sha(root / relative) != digest:
            raise ValueError("frozen admission file identity differs")
    frozen_fixture = root / "sources" / FIXTURE.name
    if sha(frozen_fixture) != record["fixture_sha256"] or sha(root / "sources" / SOURCE.name) != record["source_sha256"]:
        raise ValueError("primitive source/fixture binding differs")
    if sha(root / "sources" / HARNESS.name) != record["host_source_sha256"] or sha(root / "integer-host") != record["host_binary_sha256"] or sha(root / "integer-probe.cubin") != record["image_sha256"]:
        raise ValueError("compiled executable/image binding differs")
    if encoded(fixture()) != frozen_fixture.read_text():
        raise ValueError("independent fixture does not reproduce")
    document = read_document(frozen_fixture)
    counts = verify_host(root / "integer-host", document)
    verify_transcendentals(root / "sources", document)
    inventory = resource_audit((root / "resources.txt").read_text(),
                               (root / "compiler.log").read_text(), (root / "instructions.sass").read_text())
    resources = subprocess.check_output([cuobjdump, "--dump-resource-usage", str(root / "integer-probe.cubin")], text=True)
    sass = subprocess.check_output([cuobjdump, "--dump-sass", str(root / "integer-probe.cubin")], text=True)
    if resources != (root / "resources.txt").read_text() or sass != (root / "instructions.sass").read_text():
        raise ValueError("actual image/resource/instruction receipt differs")
    status = admission_status(inventory)
    if counts != record["cpu_counts"] or inventory != record["kernels"] or record["status"] != status:
        raise ValueError("CPU/resource outcome differs")
    if record["gpu_executed"] is not False or record["gpu_seconds"] != 0 or record["solver_implemented"] is not False or record["full_controller_accepted"] is not False or record["primary_attempts"] != 0:
        raise ValueError("unexecuted work promoted")
    if record["planned_primary_attempts"] != 96 or record["planned_profiles"] != 12:
        raise ValueError("planned study differs")
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-fixture", action="store_true")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--verify", type=Path)
    parser.add_argument("--nvcc", default="/usr/local/cuda/bin/nvcc")
    parser.add_argument("--cuobjdump", default="/usr/local/cuda/bin/cuobjdump")
    args = parser.parse_args()
    if args.verify:
        print(encoded(verify_admission(args.verify, args.cuobjdump)), end="")
        return
    if args.write_fixture:
        if FIXTURE.exists():
            raise ValueError("fixture already exists")
        FIXTURE.write_text(encoded(fixture()))
        return
    if args.output is None:
        if FIXTURE.read_text() != encoded(fixture()):
            raise ValueError("independent fixture does not reproduce")
        print(sha(FIXTURE))
        return
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    if (output / "admission.json").exists():
        raise ValueError("admission identity already exists")
    frozen = output / "sources"
    frozen.mkdir(exist_ok=True)
    for source in [SOURCE, HARNESS, Path(__file__), ROOT / "tools/lp_state_oracle.py",
                   ROOT / "tools/lp_state_candidate.py", ROOT / "tools/lp_expansion_oracle.py",
                   ROOT / "tools/lp_expansion_candidate.py", FIXTURE]:
        target = frozen / source.name
        if target.exists():
            raise ValueError("frozen source exists")
        target.write_bytes(source.read_bytes())
    binary, image = output / "integer-host", output / "integer-probe.cubin"
    subprocess.run(["g++", "-O2", "-Werror", "-Wno-unknown-pragmas", "-std=c++17",
                    str(frozen / HARNESS.name), "-o", str(binary)], check=True, timeout=120)
    cpu_counts = verify_host(binary, json.loads(FIXTURE.read_text()))
    verify_transcendentals(frozen, read_document(FIXTURE))
    command = [args.nvcc, "--cubin", "-std=c++17", "-arch=sm_120", "-O3", "-lineinfo",
               "-fmad=false", "-ftz=false", "--ptxas-options=-v", str(frozen / SOURCE.name), "-o", str(image)]
    compile_result = subprocess.run(command, capture_output=True, text=True, timeout=300)
    (output / "compiler.log").write_text(compile_result.stdout + compile_result.stderr)
    compile_result.check_returncode()
    resources = subprocess.check_output([args.cuobjdump, "--dump-resource-usage", str(image)], text=True)
    sass = subprocess.check_output([args.cuobjdump, "--dump-sass", str(image)], text=True)
    (output / "resources.txt").write_text(resources)
    (output / "instructions.sass").write_text(sass)
    inventory = resource_audit(resources, compile_result.stdout + compile_result.stderr, sass)
    record = dict(schema_version=1, identity="gpup-state-resource-admission-v1", status=admission_status(inventory),
                  cpu_counts=cpu_counts, fixture_sha256=sha(FIXTURE), source_sha256=sha(SOURCE),
                  host_source_sha256=sha(HARNESS), host_binary_sha256=sha(binary), image_sha256=sha(image),
                  nvcc_version=subprocess.check_output([args.nvcc, "--version"], text=True),
                  compiler_command=command, kernels=inventory, gpu_executed=False, gpu_seconds=0,
                  solver_implemented=False, full_controller_accepted=False, primary_attempts=0,
                  planned_primary_attempts=96, planned_profiles=12,
                  files={str(p.relative_to(output)): sha(p) for p in sorted(output.rglob("*")) if p.is_file()})
    (output / "admission.json").write_text(encoded(record))
    print(encoded(record), end="")


if __name__ == "__main__":
    main()
