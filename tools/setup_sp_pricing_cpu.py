"""Build CPU test libraries from this checkout, without private/GPU artifacts.

Historical benchmark admission remains tied to its recorded GMP runtime. This
build is for portable CPU acceptance and records the local GMP ABI/version.
"""
import ctypes
import ctypes.util
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def main():
    if ctypes.sizeof(ctypes.c_void_p) != 8 or ctypes.sizeof(ctypes.c_ulong) != 8:
        raise RuntimeError('SP-LP native CPU tests require the 64-bit Linux GMP ABI')
    runtime = ctypes.util.find_library('gmp')
    if runtime != 'libgmp.so.10':
        raise RuntimeError('install the GMP 6 runtime (libgmp.so.10) for CPU acceptance')
    gmp = ctypes.CDLL(runtime)
    version = ctypes.c_char_p.in_dll(gmp, '__gmp_version').value.decode('ascii')
    if not version.startswith('6.'):
        raise RuntimeError('unsupported GMP runtime: '+version)
    compiler = shlex.split(os.environ.get('CXX', 'g++'))
    if not compiler or shutil.which(compiler[0]) is None:
        raise RuntimeError('a C++17 compiler is required for SP-LP CPU acceptance')
    crate = ROOT/'research/lp-sp-pricing'
    output = crate/'target/cpu'
    output.mkdir(parents=True, exist_ok=True)
    libraries = {
        'market': ('market.cpp', False),
        'auxiliary': ('auxiliary.cpp', True),
        'proof': ('proof.cpp', True),
        'interval': ('proof_interval.cpp', False),
        'compact_proof': ('compact_proof.cpp', False),
        'geometry_exact': ('geometry_exact.cpp', True),
    }
    for name, (source, uses_gmp) in libraries.items():
        command = compiler+['-std=c++17', '-O3', '-fPIC', '-shared',
            '-ffp-contract=off', '-fno-fast-math', '-frounding-math',
            str(crate/'native'/source)]
        if uses_gmp:
            command += ['-l:'+runtime]
        command += ['-o', str(output/('libsp_'+name+'.so'))]
        subprocess.run(command, check=True)
    print(json.dumps(dict(status='built', libraries=list(libraries), gmp_version=version,
                          gpu_libraries=False, historical_admission_replaced=False)), flush=True)


if __name__ == '__main__':
    main()
