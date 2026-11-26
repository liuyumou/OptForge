"""Build the isolated native candidate; run only inside the study reservation."""
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
CRATE = ROOT/"research/lp-sp-pricing"


def main():
    env = dict(os.environ)
    env["PATH"] = "/root/.rustup/toolchains/1.93.1-x86_64-unknown-linux-gnu/bin:"+env["PATH"]
    env["CARGO_BUILD_JOBS"] = "4"
    commands = [["cargo", "test", "--offline"],
                ["cargo", "build", "--offline", "--release", "--features", "cuda"]]
    for command in commands:
        subprocess.run(command, cwd=CRATE, env=env, check=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
