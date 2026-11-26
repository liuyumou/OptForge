"""Bounded mathematical regressions, native build, prospective roster, development."""
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


if __name__ == "__main__":
    commands = [
        [sys.executable, "-B", "-m", "unittest", "discover", "-s", "tests/integration", "-p", "test_lp_sp_pricing.py"],
        [sys.executable, "-B", "tools/lp_sp_pricing_native.py"],
        [sys.executable, "-B", "tools/lp_sp_pricing_study.py", "freeze", "artifacts/lp-sp-pricing-v1/protocol-v1.json"],
        [sys.executable, "-B", "tools/lp_sp_pricing_study.py", "development", "artifacts/lp-sp-pricing-v1/development-cpu-v1"],
    ]
    for command in commands:
        subprocess.run(command, cwd=ROOT, check=True)
