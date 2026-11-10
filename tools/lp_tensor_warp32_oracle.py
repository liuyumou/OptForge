"""Independent actual-host/kernel-body reduction comparison; no CUDA context."""
import ctypes
import json
import random
import struct
import subprocess
import sys
from lp_protocol import ROOT, write_json, file_hash
from lp_tensor_warp32_common import BASE, DATA, IMAGE
from lp_tensor_warp32_compile import child_environment


def bits(value):
    return struct.unpack('<Q', struct.pack('<d', value))[0]


def cases():
    rows = [([1e16, 1., -1e16, 1.], [0, 1, 2, 3], [1.] * 4),
            ([-0., 0., -0., 0.], [0, 1, 2, 3], [1.] * 4)]
    rng = random.Random(17022)
    for length in [0, 1, 31, 32, 33, 63, 64, 65, 127, 128, 129, 1024]:
        for _ in range(24):
            values = [rng.randint(-127, 127) * 2.**rng.randint(-200, 200) for _ in range(length)]
            vector = [rng.randint(-31, 31) * 2.**rng.randint(-100, 100) for _ in range(max(1, length))]
            indices = list(range(length))
            rng.shuffle(indices)
            rows.append((values, indices, vector))
    for values, vector in [([float.fromhex('0x0.0000000000001p-1022')], [.5]),
                           ([float.fromhex('0x1.fffffffffffffp+1023')], [2.]),
                           ([float('inf')], [1.]), ([0.], [float('inf')]),
                           ([float('nan')], [1.]), ([1e308, 1e308], [1., 1.])]:
        rows.append((values, list(range(len(values))), vector))
    return rows


def main():
    out = BASE / 'reduction-oracle-v1'
    out.mkdir(exist_ok=False)
    environment = child_environment(__import__('os').environ)
    build = subprocess.run(['/tmp/ai-optimizer-cargo/bin/cargo', 'build', '-p', 'optimizer-lp',
                            '--example', 'tensor_warp32_probe', '--all-features', '--release', '--locked'],
                           capture_output=True, text=True, env=environment, timeout=60)
    (out / 'rust-build.stdout').write_text(build.stdout)
    (out / 'rust-build.stderr').write_text(build.stderr)
    build.check_returncode()
    cpp = out / 'reference.cpp'
    cpp.write_text('''#include <cmath>
using std::isfinite;
#define __device__
#define __global__
struct Index { unsigned x; };
Index blockIdx{0}, blockDim{1}, threadIdx{0};
void atomicOr(unsigned* p, unsigned value) { *p |= value; }
double __dmul_rn(double a,double b) { volatile double r=a*b; return r; }
double __dadd_rn(double a,double b) { volatile double r=a+b; return r; }
double __dsub_rn(double a,double b) { volatile double r=a-b; return r; }
double __ddiv_rn(double a,double b) { volatile double r=a/b; return r; }
#include "''' + str(ROOT / 'cuda/lp_pdhg_tensor_warp32/reference_audit.h') + '''"
extern "C" void probe(const double* v,const unsigned* i,const unsigned* o,
                     const double* x,double* y,unsigned* bad,unsigned os,unsigned vs) {
  tc_ref_product(v,i,o,x,y,bad,1,os,vs);
}
''')
    command = ['g++', '-std=c++17', '-O2', '-shared', '-fPIC', '-ffp-contract=off',
               '-fno-fast-math', str(cpp), '-o', str(out / 'reference.so')]
    compiled = subprocess.run(command, capture_output=True, text=True, timeout=30)
    (out / 'cpp.stdout').write_text(compiled.stdout)
    (out / 'cpp.stderr').write_text(compiled.stderr)
    compiled.check_returncode()
    library = ctypes.CDLL(str(out / 'reference.so'))
    f64 = ctypes.c_double
    u32 = ctypes.c_uint
    library.probe.argtypes = [ctypes.POINTER(f64), ctypes.POINTER(u32), ctypes.POINTER(u32),
                              ctypes.POINTER(f64), ctypes.POINTER(f64), ctypes.POINTER(u32), u32, u32]
    library.probe.restype = None
    vectors = cases()
    requests = [dict(values=list(map(bits, v)), indices=i, input=list(map(bits, x))) for v, i, x in vectors]
    binary = ROOT / 'target/release/examples/tensor_warp32_probe'
    result = subprocess.run([sys.executable, str(ROOT / 'tools/lp_tensor_cost_exec.py'),
                             '--memory-bytes', str(256 << 20), '--', str(binary)],
                            input=''.join(json.dumps(r) + '\n' for r in requests),
                            capture_output=True, text=True, env=environment, timeout=30)
    (out / 'host.stdout').write_text(result.stdout)
    (out / 'host.stderr').write_text(result.stderr)
    result.check_returncode()
    expected = [json.loads(line) for line in result.stdout.splitlines()]
    if len(expected) != len(vectors) or expected[0] != dict(bits=bits(2.)):
        raise ValueError('host reference or cancellation witness differs')
    checked = refusals = 0
    for (values, indices, vector), answer in zip(vectors, expected):
        for offset_start, value_start, first in [(0, 0, 0), (1, 3, 2)]:
            prefix = first + value_start
            v = (f64 * (prefix + len(values) + 1))(*([0.] * prefix + values + [0.]))
            i = (u32 * (prefix + len(indices) + 1))(*([0] * prefix + indices + [0]))
            offsets = (u32 * (offset_start + 2))(*([99] * offset_start + [first, first + len(values)]))
            x = (f64 * len(vector))(*vector)
            y = (f64 * 1)(float('nan'))
            bad = (u32 * 1)(0)
            library.probe(v, i, offsets, x, y, bad, offset_start, value_start)
            if ('error' in answer) != (bad[0] != 0) or ('bits' in answer and bits(y[0]) != answer['bits']):
                raise ValueError('actual kernel-body/host bit or refusal mismatch')
            checked += 1
            refusals += bad[0] != 0
    record = dict(identity='gpup-tensor-warp32-reduction-proof-v1', status='passed', gpu_seconds=0,
                  cases=checked, refused_cases=refusals, serial_cancellation_bits=bits(1.),
                  warp32_cancellation_bits=bits(2.), probe_sha256=file_hash(binary),
                  oracle_sha256=file_hash(ROOT / 'tools/lp_tensor_warp32_oracle.py'),
                  kernel_header_sha256=file_hash(ROOT / 'cuda/lp_pdhg_tensor_warp32/reference_audit.h'),
                  host_reference_sha256=file_hash(ROOT / 'crates/optimizer-lp/src/precision.rs'),
                  image_sha256=file_hash(IMAGE), host_adapter_sha256=file_hash(cpp),
                  host_library_sha256=file_hash(out / 'reference.so'), compile_command=command)
    write_json(DATA / 'reduction-proof.json', record)
    print('Independent actual host/kernel-body bits and refusal pass:', checked, 'cases', flush=True)


if __name__ == '__main__':
    main()
