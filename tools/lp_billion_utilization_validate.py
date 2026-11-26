"""Fresh, bounded validation for the opt-in utilization candidate (amendment 91)."""
import argparse
import copy
import json
from pathlib import Path
import re
import shutil
import subprocess
import time

from lp_billion_common import BASE, ROOT, load, put, ref, require, resolve


def idle(identity):
    from lp_billion_availability import observe, proof
    require(not (BASE/'availability'/identity).exists(), 'fresh observation identity')
    for index in range(7):
        if index:
            time.sleep(60)
        observe(identity)
    proof(identity)


def bound_sources(identity):
    for item in load(BASE/'sources'/identity/'manifest.json')['sources']:
        if item['original']['path'].endswith(('.rs', '.cu')) or Path(item['original']['path']).name.startswith('Cargo.'):
            resolve(item['original'])
            resolve(item['retained'])


def quality(identity):
    out = BASE/identity
    out.mkdir(exist_ok=False)
    rows = []
    manifest = 'research/lp-billion-lowbit/Cargo.toml'
    for name, command in [
        ('format', ['cargo', 'fmt', '--manifest-path', manifest, '--check']),
        ('tests', ['cargo', 'test', '--manifest-path', manifest, '--release', '--offline']),
        ('clippy', ['cargo', 'clippy', '--manifest-path', manifest, '--all-targets', '--offline', '--', '-D', 'warnings']),
        ('release', ['cargo', 'build', '--manifest-path', manifest, '--release', '--bins', '--offline']),
    ]:
        result = subprocess.run(command, text=True, capture_output=True)
        for stream in ['stdout', 'stderr']:
            (out/(name+'.'+stream)).write_text(getattr(result, stream))
        rows.append(dict(name=name, command=command, returncode=result.returncode,
                         stdout=ref(out/(name+'.stdout')), stderr=ref(out/(name+'.stderr'))))
        if result.returncode:
            print(result.stdout[-4000:] + result.stderr[-4000:], flush=True)
        require(result.returncode == 0, 'candidate native quality '+name)
        if name == 'tests':
            counts = [tuple(map(int, match)) for match in re.findall(
                r'test result: ok\. (\d+) passed; (\d+) failed; (\d+) ignored;', result.stdout)]
            require(counts and all(failed == ignored == 0 for _, failed, ignored in counts),
                    'complete native tests')
        print(dict(command=name, status='passed'), flush=True)
    bound_sources(identity)
    put(out/'result.json', dict(status='passed', rust_tests=sum(n for n, _, _ in counts), commands=rows,
        executor=ref(BASE/'target/release/billion'), benchmark=ref(BASE/'target/release/certificate_bench')))


def seal(identity):
    from lp_billion_readmission import passed
    passed(identity)
    passed('operational-gpu-v28')
    built = load(BASE/identity/'result.json')
    require(built['status'] == 'passed', 'candidate CPU quality')
    bound_sources(identity)
    previous = BASE/'image-v11'
    old = load(previous/'binding.json')
    for item in old['files'].values():
        resolve(item)
    image = BASE/'image-v12'
    image.mkdir(exist_ok=False)
    sources = [(resolve(built['executor']), 'executor')]
    sources += [(previous/name, name) for name in old['files'] if name != 'executor']
    for source, name in sources:
        shutil.copyfile(source, image/name)
        (image/name).chmod(0o755 if name in ['executor', 'control-check'] else 0o644)
    put(image/'binding.json', dict(status='CPU_quality_only', files={name: ref(image/name) for _, name in sources},
        executor=ref(image/'executor'), cuda=ref(image/'tensor.cubin'),
        quality=ref(BASE/identity/'result.json'), source_manifest=ref(BASE/'sources'/identity/'manifest.json'),
        previous_image=ref(previous/'binding.json')))
    print(dict(status='sealed', image=str(image)), flush=True)


def continuations(identity):
    from lp_billion_admit import call, unpack, serial, validate_timings
    from lp_billion_gpu_control_admit import canonical
    from lp_general_models import generate
    from lp_general_oracle import settings
    out = BASE/identity
    out.mkdir(exist_ok=False)
    old, new = BASE/'image-v11', BASE/'image-v12'
    for image in [old, new]:
        for item in load(image/'binding.json')['files'].values():
            resolve(item)
    rows = []
    for family, size in [('dense', 257), ('irregular', 4097), ('rectangular', 4097), ('ill_scaled', 65), ('dense_blocks', 129)]:
        document, _ = generate(family, size, 861700+size)
        model = out/(family+'.json')
        put(model, document)
        conversion = subprocess.run([str(old/'executor'), 'convert', str(model), str(BASE)], text=True, capture_output=True)
        require(conversion.returncode == 0, 'array conversion '+conversion.stderr)
        arrays = out/(family+'.arrays.json')
        put(arrays, json.loads(conversion.stdout))
        for fmt in ['native', 'fp32', 'fp4x1', 'fp4x2']:
            for fault in [None, 'force_recovery_after', 'cancel_after']:
                options = {**settings(fmt), 'iteration_limit': 32, 'check_interval': 16}
                if fault:
                    options[fault] = 3
                request = dict(settings=options, tensor=dict(control_interval=8, min_tile_nnz=128),
                    fast=dict(host_reductions=True, host_preparation=True, host_certificates=True,
                        auto_schedule=True, gpu_preparation=True, gpu_packing=True, gpu_control=True, gpu_feasibility=True), profile=True)
                name = f'{family}-{fmt}-{fault}'
                before = call([old/'executor', 'solve', arrays, BASE, old/'tensor.cubin'], [request], out, name+'-reference')[0]
                responses = []
                for enabled, reuse in [(False, False), (True, False), (False, True), (True, True)]:
                    candidate = copy.deepcopy(request)
                    candidate['fast']['certificate_scratch'] = enabled
                    candidate['fast']['final_assessment_reuse'] = reuse
                    variant = name+f'-scratch-{enabled}-reuse-{reuse}'
                    after = call([new/'executor', 'solve', arrays, BASE, new/'tensor.cubin'], [candidate], out, variant)[0]
                    validate_timings(after, True)
                    normalized = canonical(after)
                    normalized['fast_config'].pop('certificate_scratch', None)
                    normalized['fast_config'].pop('final_assessment_reuse', None)
                    require(canonical(before) == normalized, 'exact continuation differs '+name)
                    difference = before['cached_assessments'] - after['cached_assessments']
                    expected = int(reuse and after['status'] == 'limit' and bool(after['assessments'])
                        and after['assessments'][-1]['physical'] == after['physical']
                        and after['assessments'][-1]['logical'] == after['logical'])
                    require(difference == expected, 'conservative final reuse coverage '+variant)
                    response = out/(variant+'.response.json')
                    put(response, after)
                    decoded = unpack(after)
                    proofs = [serial(model, endpoint, options['tolerance'], out, variant+f'-{index}')
                              for index, endpoint in enumerate([*decoded['assessments'], decoded])]
                    responses.append(dict(scratch=enabled, reuse=reuse, removed_final_calls=difference,
                                          response=ref(response), serial=proofs))
                rows.append(dict(case=name, exact=True, responses=responses))
                print(dict(case=name, exact=True), flush=True)
    put(out/'result.json', dict(status='passed', rows=rows, image=ref(new/'binding.json'), source=ref(__file__)))


def benchmark(identity):
    out = BASE/identity
    out.mkdir(exist_ok=False)
    quality = load(BASE/'utilization-quality-v1/result.json')
    command = [str(resolve(quality['benchmark']))]
    result = subprocess.run(command, text=True, capture_output=True)
    (out/'stdout.json').write_text(result.stdout)
    (out/'stderr').write_text(result.stderr)
    require(result.returncode == 0, 'CPU certificate benchmark '+result.stderr[-2000:])
    value = json.loads(result.stdout)
    require(value['status'] == 'passed', 'CPU benchmark result')
    put(out/'result.json', dict(value, binary=quality['benchmark'], quality=ref(BASE/'utilization-quality-v1/result.json')))
    print(dict(status='passed', cases=len(value['rows'])), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['idle', 'quality', 'seal', 'continuations', 'benchmark'])
    parser.add_argument('--id', required=True)
    args = parser.parse_args()
    require(args.id and Path(args.id).name == args.id, 'validation identity')
    globals()[args.action](args.id)
