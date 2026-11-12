"""Restore exact earlier development executables from retained source snapshots."""
import hashlib
from pathlib import Path
import shutil
import subprocess
from lp_fp4_fast_common import ROOT, BASE, load, put, ref, require
from lp_fp4_fast_experiment import BINARY


def main():
    output=BASE/'executor-archive';output.mkdir(exist_ok=False)
    main=ROOT/'research/lp-fp4-fast/src/main.rs';current=main.read_bytes();rows=[]
    versions=[('cpu-build-v2','differential-v1'),('cpu-build-v3','differential-v2'),('cpu-build-v4','diagnostics-v4'),('cpu-build-v5','stress-v7')]
    try:
        for version,run in versions:
            source=BASE/'sources'/version/'research/lp-fp4-fast/src/main.rs'
            main.write_bytes(source.read_bytes())
            for cmd in [['cargo','fmt','--manifest-path','research/lp-fp4-fast/Cargo.toml'],['cargo','build','--release','--manifest-path','research/lp-fp4-fast/Cargo.toml','--offline','--locked']]:
                subprocess.run(cmd,cwd=ROOT,check=True)
            expected=load(BASE/run/'manifest.json')['binary']['sha256']
            actual=hashlib.sha256(BINARY.read_bytes()).hexdigest()
            require(actual==expected,'exact executable reconstruction failed: '+version)
            dest=output/(version+'-executor');shutil.copyfile(BINARY,dest);dest.chmod(0o755)
            rows.append(dict(build=version,original_manifest=ref(BASE/run/'manifest.json'),source_snapshot=ref(source),executable=ref(dest),exact_original_sha256=expected))
            print(version,'exact bytes restored and archived',flush=True)
    finally:
        main.write_bytes(current)
        subprocess.run(['cargo','build','--release','--manifest-path','research/lp-fp4-fast/Cargo.toml','--offline','--locked'],cwd=ROOT,check=True)
    put(output/'receipt.json',dict(status='passed',rows=rows,scientific_jobs_reexecuted=0))

if __name__=='__main__':main()
