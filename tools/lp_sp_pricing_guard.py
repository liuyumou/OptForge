"""Prospective study guard, using the admitted NVML ownership implementation.

The user explicitly relaxed this study's idle window to 30 seconds. Historical
availability proofs and resource sources remain unchanged. Only owned processes
are ever terminated by the retained guardian.
"""
import json
import hashlib
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
IDLE_SECONDS = 30
DISK_LIMIT = 400 << 30


def admitted_resource_sources():
    from lp_billion_readmission import passed
    from lp_billion_common import load, resolve
    passed("operational-cpu-v37")
    gate = passed("operational-gpu-v28")
    reservation = load(gate.with_name("operational-gpu-v28.reservation.json"))
    names = {"tools/"+name for name in (
        "lp_billion_common.py", "lp_billion_budget.py", "lp_billion_idle.py",
        "lp_billion_storage.py", "lp_billion_readmission.py", "lp_billion_disk_inventory.c",
        "lp_billion_source_store.py", "lp_billion_copt_fair_allocation.py",
        "lp_confirmation2_supervisor.py")}
    bound = set()
    for item in load(resolve(reservation["source_manifest"]))["sources"]:
        if item["original"]["path"] in names:
            resolve(item["original"])
            bound.add(item["original"]["path"])
    if bound != names:
        raise RuntimeError("incomplete retained resource-source admission")
    # Additive study-local admission for the process-exit race fix. The shared
    # resource-critical files above remain byte-for-byte unchanged.
    base=ROOT/'artifacts/lp-sp-pricing-v1'
    gate=json.loads((base/'wave-guard-cpu-v1/result.json').read_text())
    settled=json.loads((base/'resources/wave-guard-cpu-v1.settlement.json').read_text())
    if gate['status']!='passed' or settled['status']!='passed' or not settled['cleanup_empty'] or settled['overrun']:
        raise RuntimeError('study-local ownership readmission did not pass')
    expected={str(Path(__file__).resolve()),str(ROOT/'tests/integration/test_lp_sp_pricing_wave_guard.py')}
    if {s['path'] for s in gate['sources']}!=expected:raise RuntimeError('ownership readmission coverage')
    for source in gate['sources']:
        raw=Path(source['path']).read_bytes()
        if len(raw)!=source['bytes'] or hashlib.sha256(raw).hexdigest()!=source['sha256']:
            raise RuntimeError('ownership readmission source changed')


def physical_pids(processes):
    """Keep observed identities; tolerate only the two Linux process-exit races."""
    result=set()
    for item in processes:
        result.add(item['pid'])
        try:
            for line in Path(f"/proc/{item['pid']}/status").read_text().splitlines():
                if line.startswith('NSpid:'):result.update(map(int,line.split()[1:]))
        except (FileNotFoundError,ProcessLookupError):
            pass
    return result


def inventory():
    total = 0
    for base in (ROOT/"artifacts/lp-sp-pricing-v1", ROOT/"research/lp-sp-pricing"):
        for directory, _, files in os.walk(base, followlinks=False):
            for name in files:
                path = Path(directory)/name
                try:
                    if not path.is_symlink():
                        total += path.stat().st_size
                except FileNotFoundError:
                    pass
    return total


def install(supervisor, request):
    from lp_billion_idle import Nvml, validate_gpu
    original = supervisor.snapshot
    sensor = None
    scan = None
    last_scan = time.monotonic_ns()
    started_scan = 0
    trace = Path(request["output"]+".capacity.jsonl")
    def snapshot(*args, **kwargs):
        nonlocal sensor, scan, last_scan, started_scan
        observation = original(*args, **kwargs)
        now = time.monotonic_ns()
        if scan is None and now-last_scan >= 5_000_000_000:
            scan = subprocess.Popen([sys.executable, "-B", __file__, "inventory"],
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            started_scan = now
        if scan is not None:
            if now-started_scan > 60_000_000_000:
                raise RuntimeError("study storage inventory deadline")
            if scan.poll() is not None:
                out, error = scan.communicate()
                if scan.returncode or error or int(out) > DISK_LIMIT:
                    raise RuntimeError("study storage inventory failure or ceiling")
                scan = None
                last_scan = now
        if request.get("sp_gpu"):
            sensor = sensor or Nvml()
            sample = sensor.sample()
            owned = physical_pids(observation["processes"])
            if set(sample["processes"])-owned:
                owned |= physical_pids(original(*args, **kwargs)["processes"])
            validate_gpu(sample, owned)
            with trace.open("a") as stream:
                stream.write(json.dumps(dict(observed_ns=now, gpu=sample,
                    owned_physical_pids=sorted(owned)), sort_keys=True)+"\n")
        return observation
    supervisor.snapshot = snapshot


def idle_then_exec(receipt, command):
    from lp_billion_idle import Nvml, validate_gpu
    samples = []
    sensor = Nvml()
    try:
        while True:
            sample = sensor.sample()
            validate_gpu(sample, set())
            if sample["processes"] or sample["utilization"] != 0 or sample["free"] < 2 << 30:
                raise RuntimeError("GPU unavailable during study idle observation")
            if samples and sample["start_ns"]-samples[-1]["end_ns"] > 1_000_000_000:
                raise RuntimeError("idle observation gap")
            samples.append(sample)
            if sample["end_ns"]-samples[0]["start_ns"] >= IDLE_SECONDS*1_000_000_000:
                break
            time.sleep(.25)
    finally:
        sensor.close()
    with Path(receipt).open("x") as stream:
        json.dump(dict(policy="sp-pricing-30-second-user-relaxation-v1", samples=samples,
                       status="observed_idle", required_seconds=IDLE_SECONDS), stream)
    # Compatibility contract of the unchanged retained image. Set only after
    # this job's idle proof; the parent continues exact PID ownership sampling.
    os.environ['AI_OPTIMIZER_GPU_LEASE']='inherited'
    os.execvpe(command[0], command, os.environ)


if __name__ == "__main__":
    if sys.argv[1:] == ["inventory"]:
        print(inventory())
    elif len(sys.argv) > 3 and sys.argv[1] == "idle-exec":
        idle_then_exec(sys.argv[2], sys.argv[3:])
    else:
        raise SystemExit("invalid guard command")
