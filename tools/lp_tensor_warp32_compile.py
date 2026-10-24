"""Reviewable corrected compiler entry; execution needs launch-recovery approval."""
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def child_environment(environ):
    """Keep the working interpreter/tool paths while adding the pinned Cargo."""
    child = dict(environ)
    child['PATH'] = '/tmp/ai-optimizer-cargo/bin' + os.pathsep + child.get('PATH', '')
    child['RUSTUP_HOME'] = '/tmp/ai-optimizer-rustup'
    child['CARGO_HOME'] = '/tmp/ai-optimizer-cargo'
    return child


def main():
    environment = child_environment(os.environ)
    subprocess.run(['/tmp/ai-optimizer-cargo/bin/cargo', 'fmt', '--all'],
                   cwd=ROOT, env=environment, check=True)
    subprocess.run([sys.executable, '-u', str(ROOT / 'tools/lp_tensor_warp32_build.py')],
                   cwd=ROOT, env=environment, check=True)


if __name__ == '__main__':
    main()
