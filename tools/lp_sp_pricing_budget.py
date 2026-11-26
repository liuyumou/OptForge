"""Independent SP-LP allocation using the unchanged retained CPU supervisor.

GPU jobs require exact retained resource-source admission, per-job ownership
monitoring, and the prospectively authorized 30-second idle window. A refusal is
never a successful scientific result. Historical reservations remain unchanged.
"""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "artifacts/lp-sp-pricing-v1"
CPU = dict(reference=36000, admission=24000, development=30000,
           confirmation=60000, billion=60000, reporting=30000)
GPU = dict(reference=0, admission=4000, development=6000,
           confirmation=12000, billion=8000, reporting=0)
NS = 1_000_000_000


def put(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x") as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())


def binding(path):
    path = Path(path).resolve()
    raw = path.read_bytes()
    return dict(path=str(path), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())


def accounting(base, gpu=False):
    totals = {phase: 0 for phase in CPU}
    for path in (base / "resources").glob("*.reservation.json"):
        reservation = json.loads(path.read_text())
        settled = path.with_name(path.name.replace(".reservation.", ".settlement."))
        if not settled.exists():
            raise RuntimeError("unsettled reservation: " + path.name)
        receipt = json.loads(settled.read_text())
        if receipt["overrun"]:
            raise RuntimeError("unresolved supervision failure: " + path.name)
        if not receipt["cleanup_empty"]:
            from lp_sp_pricing_cleanup import verify
            try:
                verify(path)
            except (OSError, KeyError, ValueError) as error:
                raise RuntimeError("unresolved supervision failure: " + path.name) from error
        totals[reservation["phase"]] += receipt["gpu_ns" if gpu else "cpu_ns"]
    return totals


def run(identity, phase, seconds, command, host_gib=4, base=BASE, gpu=False):
    if not identity or any(c not in "abcdefghijklmnopqrstuvwxyz0123456789-_" for c in identity):
        raise ValueError("invalid immutable job identity")
    if phase not in CPU or not 30 <= seconds <= 3600 or not 1 <= host_gib <= 128:
        raise ValueError("invalid reservation")
    base = Path(base).resolve()
    if not base.is_relative_to(ROOT / "artifacts"):
        raise ValueError("CPU bootstrap evidence must remain in workspace artifacts")
    base.mkdir(parents=True, exist_ok=True)
    with (base / "budget.lock").open("a+b") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        used = accounting(base)
        gpu_used = accounting(base, True)
        reserved = 4 * seconds * NS
        if used[phase] + reserved > CPU[phase] * NS:
            raise RuntimeError("phase reservation exhausted")
        if gpu and (seconds < 120 or gpu_used[phase]+seconds*NS > GPU[phase]*NS):
            raise RuntimeError("GPU phase reservation exhausted or outer allowance too short")
        if gpu:
            from lp_sp_pricing_cleanup import require_cpu_readmission
            require_cpu_readmission(base)
            from lp_sp_pricing_guard import admitted_resource_sources
            admitted_resource_sources()
        available = int(next(line.split()[1] for line in Path("/proc/meminfo").read_text().splitlines()
                             if line.startswith("MemAvailable:"))) * 1024
        if available < (host_gib + 4) << 30:
            raise RuntimeError("physical host headroom")
        stat = os.statvfs(base)
        if stat.f_bavail * stat.f_frsize < 8 << 30:
            raise RuntimeError("physical disk headroom")
        prefix = base / "resources" / identity
        source_paths = sorted((ROOT / "research/lp-sp-pricing").rglob("*.py"))
        source_paths += sorted((ROOT / "research/lp-sp-pricing").rglob("*.rs"))
        source_paths += sorted((ROOT / "research/lp-sp-pricing").rglob("*.cu"))
        source_paths += sorted((ROOT / "research/lp-sp-pricing").rglob("*.cpp"))
        source_paths += sorted((ROOT / "research/lp-sp-pricing").rglob("*.h"))
        source_paths += sorted((ROOT / "research/lp-sp-pricing").rglob("*.toml"))
        source_paths += sorted((ROOT / "research/lp-sp-pricing").glob("Cargo.lock"))
        source_paths += sorted((ROOT / "tools").glob("lp_sp_pricing_*.py"))
        source_paths += sorted((ROOT / "tests/integration").glob("test_lp_sp_pricing*.py"))
        source_paths += [Path(__file__), ROOT / "tools/lp_confirmation2_supervisor.py"]
        snapshot = []
        for path in sorted(set(source_paths)):
            item = binding(path)
            dest = base / "sources" / identity / path.relative_to(ROOT)
            dest.parent.mkdir(parents=True, exist_ok=True)
            with dest.open("xb") as stream:
                stream.write(path.read_bytes())
            item["retained"] = str(dest)
            snapshot.append(item)
        put(str(prefix) + ".reservation.json", dict(phase=phase, gpu=gpu,
            cpu_ns=reserved, gpu_ns=seconds*NS if gpu else 0, command=command, sources=snapshot))
        put(str(prefix) + ".journal.json", dict(identity="sp-lp-independent-v1",
            prior_cpu_ns=0, ceiling_cpu_ns=reserved, active=None, failed=False,
            runs=[], stages={phase: dict(cap_cpu_ns=reserved, charged_cpu_ns=0)}))
        request = dict(stage=phase, reserve_cpu_seconds=4*seconds,
            output=str(prefix)+".resource.json", log=str(prefix)+".log",
            journal=str(prefix)+".journal.json", lock=str(base/"cpu.lock"),
            slots=4, declared_memory_bytes=(host_gib << 30)-(256 << 20),
            rss_stop_bytes=host_gib << 30, address_space_bytes=0, sources=[],
            bootstrap=False, show_log=False, max_gap_ns=NS,
            observed_finalization=True, receipt_finalization_seconds=10,
            publication_wall_seconds=30, sp_gpu=gpu, command=command)
        if gpu:
            request["command"] = [sys.executable, "-B", str(ROOT/"tools/lp_sp_pricing_guard.py"),
                "idle-exec", str(prefix)+".idle.json", *command]
        put(str(prefix)+".request.json", request)
        started = time.monotonic_ns()
        process = subprocess.run([sys.executable, "-B", __file__, "_supervise", str(prefix)+".request.json"],
            env={**os.environ, "CUDA_VISIBLE_DEVICES": "GPU-6721b13a-30f9-83ec-dace-ba2d9738556f" if gpu else "",
                 "PYTHONDONTWRITEBYTECODE": "1"})
        elapsed = time.monotonic_ns()-started
        resource_path = Path(str(prefix)+".resource.json")
        report = json.loads(resource_path.read_text()) if resource_path.exists() else None
        passed = process.returncode == 0 and report and report.get("status") == "passed"
        empty = bool(report and report.get("guardian_cleanup", {}).get("empty")
                     and report.get("result", {}).get("cleanup", {}).get("empty"))
        overrun = elapsed > seconds*NS
        charged = max(4*elapsed, (report or {}).get("charged_cpu_ns", reserved))
        if not passed or not empty or overrun:
            charged = max(charged, reserved)
        result = dict(status="passed" if passed and empty and not overrun else "refused",
            cpu_ns=charged, gpu_ns=(elapsed if passed and empty and not overrun else max(elapsed, seconds*NS)) if gpu else 0,
            cleanup_empty=empty, overrun=overrun,
            elapsed_ns=elapsed, resource=binding(resource_path) if report else None)
        put(str(prefix)+".settlement.json", result)
        return result


def main():
    if len(sys.argv) == 3 and sys.argv[1] == "_supervise":
        import lp_confirmation2_supervisor as supervisor
        from lp_sp_pricing_guard import install
        request = json.loads(Path(sys.argv[2]).read_text())
        install(supervisor, request)
        return 0 if supervisor.run(request)["status"] == "passed" else 2
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--id", required=True)
    parser.add_argument("--phase", choices=CPU, required=True)
    parser.add_argument("--seconds", type=int, required=True)
    parser.add_argument("--host-gib", type=int, default=4)
    parser.add_argument("--gpu", action="store_true")
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    result = run(args.id, args.phase, args.seconds, command, args.host_gib, gpu=args.gpu)
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] == "passed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
