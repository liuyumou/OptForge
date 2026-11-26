"""Four complete CUDA sanitizer processes on the precision/format smoke matrix."""
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT/"artifacts/lp-sp-pricing-v1"


def main():
    identity = sys.argv[1]
    directory = BASE/identity
    directory.mkdir(exist_ok=False)
    rows = []
    selected = sys.argv[2:] or ["memcheck", "racecheck", "initcheck", "synccheck"]
    if not selected or len(set(selected)) != len(selected) or any(t not in ("memcheck", "racecheck", "initcheck", "synccheck") for t in selected):
        raise ValueError("invalid sanitizer selection")
    for tool in selected:
        command = ["/usr/local/cuda/bin/compute-sanitizer", "--tool", tool,
                   "--error-exitcode", "91", "--target-processes", "all",
                   sys.executable, "-B", str(ROOT/"tools/lp_sp_pricing_gpu_quality.py"),
                   str(directory/(tool+".json")), "--sanitizer-smoke"]
        start = time.monotonic_ns()
        with (directory/(tool+".log")).open("x") as log:
            result = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT)
        rows.append(dict(tool=tool, returncode=result.returncode, elapsed_ns=time.monotonic_ns()-start,
                         command=command))
        if result.returncode:
            raise RuntimeError("CUDA sanitizer failed: "+tool)
    with (directory/"result.json").open("x") as stream:
        json.dump(dict(status="passed", rows=rows), stream, indent=2)
    print(json.dumps(dict(status="passed", tools=len(rows))))


if __name__ == "__main__":
    main()
