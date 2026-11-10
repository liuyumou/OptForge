"""ADR-0045 single prescribed image construction; compile only, never a lease."""
import re
import subprocess
from pathlib import Path
from lp_protocol import ROOT, read_json, write_json, file_hash

BASE = ROOT / 'artifacts/gpup-tensor-warp32-v1'
SOURCE = ROOT / 'cuda/lp_pdhg_tensor_warp32'
IMAGE = BASE / 'build/lp_pdhg_tensor_cost.cubin'


def preserve():
    old = read_json(BASE / 'historical-numerical-sources.json')
    from lp_tensor_warp32_availability_bridge import verify_source_mapping
    verify_source_mapping(old)
    previous = ROOT / 'cuda/lp_pdhg_tensor_cost'
    for name in ['lp_pdhg_tensor_cost.cu', 'fragment_layout.h']:
        if (SOURCE / name).read_bytes() != (previous / name).read_bytes():
            raise ValueError('unrelated CUDA body changed')
    marker = '  if (j >= lines) return;\n'
    suffix = '\n}\nextern "C" __global__ void tc_ref_primal'
    def outside(path):
        text = path.read_text()
        prefix, rest = text.split(marker, 1)
        _, tail = rest.split(suffix, 1)
        return prefix + marker + '<reference product body>' + suffix + tail
    if outside(SOURCE / 'reference_audit.h') != outside(previous / 'reference_audit.h'):
        raise ValueError('reference ABI or other reference kernel changed')
    historical = read_json(BASE / 'historical-bindings.json')
    if file_hash(ROOT / 'tools/lp_cpu_admission.py') != historical['supervisor_sha256']:
        raise ValueError('supervisor changed')
    old_image = ROOT / 'artifacts/gpup-tensor-cost-v1/study-v1/lp_pdhg_tensor_cost.cubin'
    if file_hash(old_image) != historical['old_image_sha256']:
        raise ValueError('historical image changed')
    return old


def main():
    old = preserve()
    out = IMAGE.parent
    out.mkdir(parents=True, exist_ok=True)
    if IMAGE.exists():
        raise ValueError('image construction cannot retry')
    keep = out / 'nvcc-kept'
    keep.mkdir()
    source = SOURCE / 'lp_pdhg_tensor_cost.cu'
    command = ['/usr/local/cuda/bin/nvcc', '--cubin', '-arch=sm_120', '-O3',
               '-lineinfo', '-fmad=false', '-ftz=false', '-Xptxas=-v',
               '--keep', '--keep-dir', str(keep), '-o', str(IMAGE), str(source)]
    result = subprocess.run(command, capture_output=True, text=True, timeout=120)
    (out / 'compile.stdout').write_text(result.stdout)
    (out / 'compile.stderr').write_text(result.stderr)
    result.check_returncode()
    registers = list(map(int, re.findall(r'Used (\d+) registers', result.stderr)))
    spills = re.findall(r'(\d+) bytes spill stores, (\d+) bytes spill loads', result.stderr)
    if not registers or max(registers) > 128 or not spills or any(a != '0' or b != '0' for a, b in spills):
        raise ValueError('prescribed construction fails register/spill admission')
    ptx_files = list(keep.glob('*.ptx'))
    if len(ptx_files) != 1:
        raise ValueError('ambiguous retained PTX')
    ptx = ptx_files[0].read_text()
    sass = subprocess.check_output(['/usr/local/cuda/bin/cuobjdump', '--dump-sass', str(IMAGE)], text=True)
    resources = subprocess.check_output(['/usr/local/cuda/bin/cuobjdump', '--dump-resource-usage', str(IMAGE)], text=True)
    for name in ['tn_int8', 'tn_fp16', 'tn_bf16']:
        body = sass.split('Function : ' + name, 1)[1].split('Function :', 1)[0]
        if not re.search(r'\b[HI]MMA', body):
            raise ValueError('required Tensor instruction absent: ' + name)
    if re.search(r'\b(?:fma\.|\w+\.ftz\.)', ptx):
        raise ValueError('contraction/FTZ differs')
    for name, text in [('tensor.ptx', ptx), ('tensor.sass', sass), ('tensor.resources', resources)]:
        (out / name).write_text(text)
    sources = {str(p.relative_to(ROOT)): file_hash(p) for p in
               [source, SOURCE / 'fragment_layout.h', SOURCE / 'reference_audit.h',
                ROOT / 'cuda/lp_pdhg_quant_resident/lp_pdhg_quant_resident.cu',
                ROOT / 'cuda/lp_pdhg_tuned/lp_pdhg_tuned.cu', ROOT / 'cuda/lp_pdhg/lp_pdhg.cu']}
    record = dict(identity='gpup-tensor-warp32-image-v1', status='passed', gpu_seconds=0,
                  command=command, sources=sources, image_sha256=file_hash(IMAGE),
                  max_registers=max(registers), spill_bytes=0,
                  ptx_sha256=file_hash(out / 'tensor.ptx'), sass_sha256=file_hash(out / 'tensor.sass'))
    write_json(IMAGE.with_suffix('.build.json'), record)
    write_json(ROOT / 'docs/benchmarks/data/tensor-warp32/instruction-admission.json', record)
    write_json(ROOT / 'docs/benchmarks/data/tensor-warp32/numerical-source-bridge.json',
               dict(status='passed', historical_sources=old, new_sources=sources,
                    changed_body='tc_ref_product lane-strided FP64 sum and active-lane tree only',
                    host_numerical_bodies_unchanged=True, supervisor_unchanged=True,
                    old_image_preserved=True, bootstrap_rerun=False, gpu_seconds=0))
    preserve()
    print('Prescribed warp32 image passes: max registers', max(registers),
          'zero spills; Tensor instructions/rounding and historical bodies preserved', flush=True)


if __name__ == '__main__':
    main()
