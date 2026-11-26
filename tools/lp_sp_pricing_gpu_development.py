"""One source-frozen development sequence; never repeat a completed identity."""
import subprocess
import sys
from lp_sp_pricing_budget import ROOT, BASE


if __name__ == "__main__":
    commands = [
        [sys.executable, "-B", str(ROOT/"tools/lp_sp_pricing_batch_benchmark.py"), str(BASE/"batch-benchmark-v1.json")],
        [sys.executable, "-B", str(ROOT/"tools/lp_sp_pricing_study.py"), "development", str(BASE/"development-gpu-v1"),
         "--gpu-library", str(ROOT/"research/lp-sp-pricing/target/release/liblp_sp_pricing.so")],
    ]
    for command in commands:
        subprocess.run(command, cwd=ROOT, check=True)
