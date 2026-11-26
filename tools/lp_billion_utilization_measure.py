"""Fresh 4 M-NNZ paired diagnostics; complete proofs and all outcomes are retained."""
import copy
import json
import subprocess
import time

from lp_billion_common import BASE, ROOT, load, put, ref, resolve, require


def run():
    from lp_billion_admit import validate_timings
    from lp_billion_generate import generate
    from lp_billion_gpu_control_capacity import capacity
    from lp_billion_gpu_control_admit import canonical
    from lp_billion_full_audit_v2 import audit
    from lp_billion_readmission import passed
    from lp_general_oracle import settings
    passed('utilization-candidate-v1')
    root = BASE/'utilization-4m-v1'
    root.mkdir(exist_ok=False)
    request = dict(settings={**settings('fp32'), 'iteration_limit': 1000,
        'check_interval': 500, 'wall_ms': 30000}, tensor=dict(control_interval=100, min_tile_nnz=128),
        fast=dict(host_reductions=True, host_preparation=True, host_certificates=True,
            auto_schedule=True, gpu_preparation=True, gpu_packing=True, gpu_control=True, gpu_feasibility=True), profile=True)
    families = ['irregular', 'tall', 'coupled_blocks']
    images = {name: load(BASE/('image-'+version)/'binding.json')
              for name, version in [('reference', 'v11'), ('candidate', 'v12')]}
    for image in images.values():
        for item in image['files'].values():
            resolve(item)
    put(root/'plan.json', dict(status='prospective', source=ref(__file__), families=families,
        target=4_194_304, seed=20261123, request=request, rotated_order=True,
        independent_checker=ref(BASE/'image-v1/executor'),
        limits=dict(outer_seconds=600, host_gib=16, device_gib=2),
        scope='One rotated fresh pair per family; descriptive phase timing, no certified superiority or utilization percentage inferred'))
    cells, pairs = [], []
    for index, family in enumerate(families):
        identity = f'utilization-4m-v1-{family}'
        generate(identity+'-input', family, 4_194_304, 20261123+index)
        model_result = load(BASE/(identity+'-input')/'result.json')
        model = resolve(model_result['model'])
        memory = capacity(model_result)
        require(memory['admitted'] and memory['host_gib'] <= 16 and memory['device_gib'] <= 2,
                'small cohort combined capacity')
        # Scratch retains at most four full-column vectors and original terms.
        extra = 4*24*model_result['rows'] + 24*(model_result['rows']+model_result['columns']+1)
        require(memory['host_bytes'] + extra < 16 << 30, 'candidate scratch host capacity')
        order = ['reference', 'candidate'] if index % 2 == 0 else ['candidate', 'reference']
        rows = []
        for version in order:
            cell_id = identity+'-'+version
            out = BASE/cell_id
            out.mkdir(exist_ok=False)
            image = images[version]
            options = copy.deepcopy(request)
            if version == 'candidate':
                options['fast'].update(certificate_scratch=True, final_assessment_reuse=True)
            put(out/'request.json', options)
            start = time.monotonic_ns()
            process = subprocess.run([str(resolve(image['executor'])), 'solve', str(model),
                str(BASE), str(resolve(image['cuda']))], input=json.dumps(options)+'\n',
                text=True, capture_output=True, timeout=60)
            (out/'stdout.jsonl').write_text(process.stdout)
            (out/'stderr').write_text(process.stderr)
            require(process.returncode == 0, 'fresh solver process '+process.stderr[-2000:])
            response = json.loads(process.stdout)
            put(out/'response.json', response)
            process_ns = time.monotonic_ns()-start
            validate_timings(response, True)
            require(response['model_sha256'] == model_result['model']['sha256'], 'original model binding')
            cell = dict(id=cell_id, lane='fp32', model=model_result['model'], audit_seconds=60)
            cells.append(cell)
            manifest = out/'audit-plan.json'
            put(manifest, dict(checker=ref(BASE/'image-v1/executor'), cells=[cell]))
            audit(manifest, 0)
            proof_path = BASE/(cell_id+'-full-audit')/'result.json'
            proof = load(proof_path)
            rows.append(dict(version=version, response=ref(out/'response.json'), audit=ref(proof_path),
                process_ns=process_ns, final_proof_ns=proof['final_check_ns'],
                complete_ns=process_ns+proof['final_check_ns'], offline_audit_ns=proof['offline_audit_ns'],
                status=response['status'], certified=response['certified']))
            print(dict(case=cell_id, status=response['status'], complete_seconds=rows[-1]['complete_ns']/1e9), flush=True)
        normalized = []
        for row in rows:
            response = canonical(load(resolve(row['response'])))
            response['fast_config'].pop('certificate_scratch', None)
            response['fast_config'].pop('final_assessment_reuse', None)
            normalized.append(response)
        pairs.append(dict(family=family, model=model_result['model'], construction_ns=model_result['elapsed_ns'],
            exact_continuation=normalized[0] == normalized[1], rows=rows))
    put(root/'result.json', dict(status='passed', pairs=pairs, source=ref(__file__), plan=ref(root/'plan.json'),
        scope='Complete costs include fresh-process input/CSR-to-CSC and cold final independent proof; shared generation and offline intermediate proofs are separate. One rotated pair; caches not flushed.'))


if __name__ == '__main__':
    run()
