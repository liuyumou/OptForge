"""CPU acceptance and isolated safe-executor build."""
import subprocess
from lp_fp4_fast_common import ROOT


def main():
    commands=[
        ['python3','-m','unittest','discover','-s','tests/integration','-p','test_lp_fp4_fast.py'],
        ['cargo','fmt','--manifest-path','research/lp-fp4-fast/Cargo.toml'],
        ['cargo','test','--manifest-path','research/lp-fp4-fast/Cargo.toml','--offline','--locked'],
        ['cargo','clippy','--manifest-path','research/lp-fp4-fast/Cargo.toml','--offline','--locked','--','-D','warnings'],
        ['cargo','build','--release','--manifest-path','research/lp-fp4-fast/Cargo.toml','--offline','--locked']]
    for cmd in commands:
        print(cmd,flush=True);subprocess.run(cmd,cwd=ROOT,check=True)

if __name__=='__main__':main()
