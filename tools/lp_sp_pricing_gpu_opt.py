"""Source-bound GPU optimization study; historical scientific cells stay exact."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
from lp_sp_pricing_budget import ROOT, BASE, binding, put

CRATE = ROOT/'research/lp-sp-pricing'


def archive():
    out = BASE/'gpu-optimization-baseline-v1'
    out.mkdir(exist_ok=False)
    paths = [p for p in CRATE.rglob('*') if p.is_file() and 'target' not in p.parts and '__pycache__' not in p.parts]
    paths += list((ROOT/'tools').glob('lp_sp_pricing_*.py'))
    paths += list((ROOT/'tests/integration').glob('test_lp_sp_pricing*.py'))
    paths += [CRATE/'target/release/liblp_sp_pricing.so', CRATE/'target/cpu/libsp_auxiliary.so',
              CRATE/'target/cpu/libsp_market.so']
    items = []
    for path in paths:
        target = out/path.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
        items.append(dict(original=binding(path), retained=binding(target)))
    put(out/'binding.json', dict(status='retained_before_optimization', sources=items,
        previous_checkpoint=binding(ROOT/'docs/benchmarks/lp-sp-pricing-checkpoint.json'),
        historical_frozen_sources_resolve_via_retained_bindings=True))
    put(out/'plan.json', dict(status='prospective', authorization='user requests diagnosis and GPU optimization',
        hypotheses=['redundant Python exact checks dominate', 'fixed 1000-step passes waste work',
                    'four launches per iteration and repeated allocations dominate small products',
                    'partial GPU labels still incur exact auxiliary fallback'],
        changes=['native exact proposal checks', 'skip resolved targets and unnecessary dual bounds',
                 'persistent fused small-matrix CUDA kernel and reusable buffers',
                 'bounded staged proposals with exact acceptance'],
        evaluation='fixed-work auxiliary diagnostics, differential exact checks, sanitizers, separate-seed development, frozen fresh original-LP comparison',
        preserve='original tolerances, all failures, old source/binary snapshots and scientific identities',
        no_claim='no tensor-core, arbitrary GPU precision, or strongly polynomial implementation claim',
        allocation='unchanged lp-sp-pricing-v1 totals and phase limits'))
    print(json.dumps(dict(status='archived', sources=len(items))))


def build(identity):
    out = BASE/identity
    out.mkdir(exist_ok=False)
    runtime = Path('/usr/lib/x86_64-linux-gnu/libgmp.so.10.4.1')
    cpu = CRATE/'target/cpu/libsp_proof.so'
    gpu = CRATE/'target/release/libsp_batch_optimized.so'
    preceding=[]
    for path in [cpu,gpu]:
        if path.exists():
            target=out/('preceding-'+path.name);shutil.copyfile(path,target)
            preceding.append(dict(original=binding(path),retained=binding(target)))
    put(out/'preceding-libraries.json',preceding)
    commands = [
        ['g++','-std=c++17','-O3','-fPIC','-shared','-Wall','-Wextra','-Werror',
         str(CRATE/'native/proof.cpp'),str(runtime),'-o',str(cpu)],
        ['/usr/local/cuda/bin/nvcc','-std=c++17','-O3','--fmad=false','-Xcompiler','-fPIC',
         '-shared',str(CRATE/'native/batch_optimized.cu'),'-o',str(gpu)]]
    for command in commands:
        subprocess.run(command, check=True)
    retained=[]
    for path in [cpu,gpu]:
        target=out/path.name;shutil.copyfile(path,target);retained.append(binding(target))
    put(out/'binding.json', dict(status='passed', commands=commands, libraries=[binding(cpu),binding(gpu)],
        runtime=binding(runtime), retained_libraries=retained,
        sources=[binding(CRATE/'native'/n) for n in ['proof.cpp','gmp_abi.h','batch_optimized.cu']]))
    print(json.dumps(dict(status='built', libraries=[str(cpu),str(gpu)])))


if __name__ == '__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['archive','build']);p.add_argument('identity',nargs='?')
    a=p.parse_args()
    if a.action=='archive':archive()
    else:build(a.identity)
