"""ADR-0046 authority adapters; never alter retained protocols or supervision."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "artifacts/gpup-tensor-expanded-v1"
DATA = ROOT / "docs/benchmarks/data/tensor-expanded"
JOURNAL = BASE / "cpu-journal-v1.json"
LEDGER = ROOT / "artifacts/lp-campaign-ledgers/gpup-baseline-v1/ledger.jsonl"
NS = 1_000_000_000
PREFIX_EVENTS = 17412
PREFIX_SHA256 = "9913d391634bdb0f74012be909be377e5a693d00b76e6882abcf336796ac863e"
PHASES = {"acceptance": "repeatability", "profiles": "ablations", "timings": "screening"}


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def read(path):
    return json.loads(Path(path).read_text())


def ref(path):
    path = Path(path)
    return {"path": str(path.relative_to(ROOT)),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def checked(item):
    path = ROOT / item["path"]
    require(path.resolve().is_relative_to(ROOT), "reference escapes repository")
    require(ref(path) == item, "source/cache mismatch: " + item["path"])
    return path


def put(path, value):
    path = Path(path)
    require(not path.exists(), "immutable artifact exists")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def authority():
    a = read(DATA / "authorization-v1.json")
    require(a["status"] == "accepted" and a["additional_cpu_ns"] == 24000 * NS,
            "authorization differs")
    require(a["cpu_ceiling_ns"] == 77640 * NS and a["prospective_cpu_ns"] == 31600 * NS,
            "CPU caps differ")
    require(a["gpu_caps_seconds"] == {"acceptance": 450, "profiles": 320, "timings": 990},
            "GPU caps differ")
    require(a["gpup8_phase_caps_seconds"] == {"repeatability": 1070, "ablations": 520, "screening": 1410},
            "GPUP-8 phase caps differ")
    for key in ["prior_accounting", "prior_journal"]:
        checked(a[key])
    return a


def aggregate(events):
    """Settled history and pending reservations count before new admission."""
    phases, pending, attempted, settled = {}, {}, set(), []
    for sequence, e in enumerate(events):
        require(e["sequence"] == sequence, "ledger sequence differs")
        key = e["reservation_id"]
        if e["kind"] == "reserve":
            require(key not in pending and e["trial_id"] not in attempted, "duplicate attempt")
            require(type(e["reserved_ns"]) is int and e["reserved_ns"] >= 0 and e["charged_ns"] == 0,
                    "invalid reservation")
            pending[key] = e
            attempted.add(e["trial_id"])
        else:
            require(e["kind"] in ["settle", "recover"] and key in pending, "unmatched settlement")
            old = pending.pop(key)
            require(all(e[k] == old[k] for k in ["trial_id", "resource", "phase", "reserved_ns"]),
                    "settlement binding differs")
            require(type(e["charged_ns"]) is int and e["charged_ns"] >= 0, "invalid charge")
            require(e["kind"] != "recover" or e["charged_ns"] == e["reserved_ns"], "recovery undercharged")
            settled.append(e)
            if e["resource"] == "gpu":
                phases[e["phase"]] = phases.get(e["phase"], 0) + e["charged_ns"]
    for e in pending.values():
        if e["resource"] == "gpu":
            phases[e["phase"]] = phases.get(e["phase"], 0) + e["reserved_ns"]
    return phases, attempted, settled, list(pending.values())


def ledger_events(path=LEDGER):
    raw = Path(path).read_bytes()
    lines = raw.splitlines(keepends=True)
    require(raw.endswith(b"\n") and len(lines) >= PREFIX_EVENTS, "ledger prefix missing")
    require(hashlib.sha256(b"".join(lines[:PREFIX_EVENTS])).hexdigest() == PREFIX_SHA256,
            "historical ledger prefix differs")
    return [json.loads(line) for line in lines]


def gpu_admission(a, events, category, trial_id, reserve_ns, request_exists=False):
    require(category in PHASES and type(reserve_ns) is int and reserve_ns > 0, "invalid GPU request")
    phases, attempted, settled, pending = aggregate(events)
    require(trial_id not in attempted and not request_exists, "duplicate attempt")
    prefix = "gpup-tensor-expanded-v1-"
    require(trial_id.startswith(prefix + category + "-"), "candidate identity differs")
    usage = {k: 0 for k in PHASES}
    for e in [*settled, *pending]:
        if e["resource"] != "gpu":
            continue
        for k in PHASES:
            if e["trial_id"].startswith(prefix + k + "-"):
                require(e["phase"] == PHASES[k], "candidate phase differs")
                usage[k] += e["charged_ns"] if e in settled else e["reserved_ns"]
    usage[category] += reserve_ns
    require(all(usage[k] <= a["gpu_caps_seconds"][k] * NS for k in PHASES), "cohort phase exhausted")
    require(a["prior_gpup8_gpu_ns"] + sum(usage.values()) <= a["gpup8_gpu_cap_ns"], "GPUP-8 exhausted")
    for k, phase in PHASES.items():
        require(a["prior_gpup8_phase_ns"][phase] + usage[k] <= a["gpup8_phase_caps_seconds"][phase] * NS,
                "GPUP-8 phase exhausted")
    phases[PHASES[category]] = phases.get(PHASES[category], 0) + reserve_ns
    caps = read(ROOT / "benchmarks/configs/lp-tensor-warp32-v1.json")["phase_gpu_seconds"]
    require(all(v <= caps[k] * NS for k, v in phases.items()), "campaign phase exhausted")
    require(sum(phases.values()) <= min(a["campaign_gpu_cap_ns"], 28800 * NS), "campaign exhausted")
    return usage


def stage_admission(journal, stage, reserve_ns):
    require(not journal["failed"] and not journal["active"] and not journal.get("scientific_closed"),
            "scientific execution closed")
    require(stage not in journal.get("stage_attempts", {}), "stage already attempted")
    entry = journal["stages"][stage]
    require(type(reserve_ns) is int and 12 * NS <= reserve_ns <= entry["cap_cpu_ns"] - entry["charged_cpu_ns"],
            "stage exhausted")
    require(journal["prior_cpu_ns"] + sum(s["cap_cpu_ns"] for s in journal["stages"].values()) <= journal["ceiling_cpu_ns"],
            "future reserves do not fit")


def validate_conversion_counts(c, windows, dimensions):
    require(all(type(v) is int and v >= 0 for v in c.values()), "malformed conversion counter")
    require(c["penultimate_vectors"] == c["endpoint_vectors"] == 2 * windows,
            "conversion boundary count differs")
    require(c["decoded_coordinates"] == 2 * windows * sum(dimensions), "conversion coordinate count differs")


def report_view(result):
    """Report composition never turns an incomplete stage into completion."""
    keys = ["profiles_complete", "working_families", "forecast_pass", "resource_pass",
            "timings_certified", "coverage_pass", "adjusted_gain"]
    return {"complete": all(result[k] for k in keys) and result["timings_certified"] == 60,
            "criteria": {k: result[k] for k in keys}}


def preserve():
    bridge = read(BASE / "source-bridge-v1.json")
    checked(bridge["supervisor"])
    snapshots = {v["current"]: v["preserved"] for v in bridge["prior_mutable"]}
    for item in read(checked(bridge["prior_worktree"]))["files"]:
        target = snapshots.get(item["path"], item)
        require(target["sha256"] == item["sha256"], "preserved source differs")
        checked(target)
    for item in read(ROOT / "artifacts/gpup-tensor-warp32-v1/receipt-recovery-v1/pins.json")["historical_refs"]:
        checked(item)
    for item in bridge["retained_arithmetic"]:
        checked(item)
    events = ledger_events()
    require(len(events) == PREFIX_EVENTS, "unexpected GPU work before CPU gates")
    return len(events)


def run_stage(stage, command, sources):
    """Use the unchanged supervisor's public run function with named stages."""
    import lp_cpu_admission as supervisor
    a = authority()
    checked(read(BASE / "source-bridge-v1.json")["supervisor"])
    j = read(JOURNAL)
    amount = j["stages"][stage]["cap_cpu_ns"] - j["stages"][stage]["charged_cpu_ns"]
    stage_admission(j, stage, amount)
    output = BASE / (stage + "-resource-v1.json")
    j["stage_attempts"][stage] = {"output": str(output.relative_to(ROOT)), "reserved_cpu_ns": amount}
    supervisor.atomic_json(JOURNAL, j)
    request = dict(stage=stage, reserve_cpu_seconds=amount / NS, output=str(output), log=str(output)+".log",
                   journal=str(JOURNAL), lock=str(ROOT/"artifacts/lp-cpu-admission.lock"), slots=4,
                   declared_memory_bytes=4 << 30, rss_stop_bytes=6 << 30, address_space_bytes=0,
                   sources=[str(ROOT / p) for p in sources], bootstrap=False, show_log=True,
                   max_gap_ns=100_000_000, command=command)
    result = supervisor.run(request)
    print(json.dumps({"stage": stage, "status": result["status"], "charged_cpu_ns": result["charged_cpu_ns"]}))
    return 0 if result["status"] == "passed" else 1
