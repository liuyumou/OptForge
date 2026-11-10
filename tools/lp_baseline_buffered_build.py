"""Scoped final formatting/lint/build for the new buffered checker only."""
import os
from pathlib import Path
import subprocess
import tomllib

ROOT=Path(__file__).resolve().parents[1]
env={**os.environ,'RUSTUP_HOME':'/tmp/ai-optimizer-rustup','CARGO_HOME':'/tmp/ai-optimizer-cargo',
     'PATH':'/tmp/ai-optimizer-cargo/bin:'+os.environ.get('PATH','')}
cargo='/tmp/ai-optimizer-cargo/bin/cargo'
manifest='research/lp-external-baseline-buffered/Cargo.toml'
commands=[[cargo,'fmt','--manifest-path',manifest],
          [cargo,'clippy','--offline','--release','--manifest-path',manifest,'--','-D','warnings'],
          [cargo,'build','--offline','--release','--manifest-path',manifest]]
for command in commands: subprocess.run(command,cwd=ROOT,env=env,check=True,timeout=20)
old=tomllib.loads((ROOT/'Cargo.lock').read_text())
versions={p['name']:p['version'] for p in old['package']}
new=tomllib.loads((ROOT/'research/lp-external-baseline-buffered/Cargo.lock').read_text())
assert all(versions[p['name']]==p['version'] for p in new['package'] if p.get('source'))
print('Buffered checker formatted, linted and built; external Rust dependency versions unchanged.')
