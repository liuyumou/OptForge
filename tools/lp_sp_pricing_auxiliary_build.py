"""Build against the installed pinned GMP ABI without system modifications."""
import ctypes
import json
from pathlib import Path
import subprocess
from lp_sp_pricing_budget import ROOT,BASE,binding,put

if __name__=='__main__':
    import sys
    out=BASE/sys.argv[1];out.mkdir(exist_ok=False)
    runtime=Path('/usr/lib/x86_64-linux-gnu/libgmp.so.10.4.1')
    library=ctypes.CDLL(str(runtime))
    if ctypes.c_char_p.in_dll(library,'__gmp_version').value!=b'6.2.1':raise RuntimeError('GMP ABI version differs')
    source=ROOT/'research/lp-sp-pricing/native/auxiliary.cpp'
    destination=ROOT/'research/lp-sp-pricing/target/cpu/libsp_auxiliary.so'
    command=['g++','-std=c++17','-O3','-fPIC','-shared','-Wall','-Wextra','-Werror',str(source),str(runtime),'-o',str(destination)]
    subprocess.run(command,check=True)
    put(out/'binding.json',dict(status='passed',runtime=binding(runtime),source=binding(source),
        abi=binding(source.with_name('gmp_abi.h')),library=binding(destination),command=command,system_modified=False))
    print(json.dumps(dict(status='passed',library=str(destination))))
