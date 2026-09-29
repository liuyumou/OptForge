"""Real CPU import readback and leased 24-endpoint SPEC-0019 acceptance."""
import argparse
import copy
import os
from pathlib import Path
import subprocess
from benchmark_lp import source_identity, reference
from lp_copt import validate_import_coefficients
from lp_copt_accept import equal_bits
from lp_copt_comparison import METHODS
from lp_copt_matrix import prepare, load
from lp_copt_adapter_budget import protocol
from lp_protocol import ROOT, checked_reference, file_hash, read_json, write_json
from lp_cost import validate_profile
from report_lp_copt import numerical_digest


def environment(value, gpu=False):
    env = {**os.environ, 'COPT_HOME': value['copt_installation'], 'COPT_LICENSE_DIR': value['copt_installation'],
           'LD_LIBRARY_PATH': '/usr/local/cuda/lib64', 'PYTHONDONTWRITEBYTECODE': '1'}
    if not gpu: env['CUDA_VISIBLE_DEVICES'] = ''
    return env


def scalar_load(cp, model, doc):
    """Independent transcription of the preserved scalar import, for readback only."""
    validate_import_coefficients(doc)
    bound = lambda b: b['value'] if b['kind'] == 'finite' else cp.COPT.INFINITY if b['kind'] == 'positive_infinity' else -cp.COPT.INFINITY
    vs = {v['id']: model.addVar(lb=bound(v['lower']), ub=bound(v['upper']), name='v' + str(v['id'])) for v in sorted(doc['variables'], key=lambda v: v['id'])}
    for r in sorted(doc['constraints'], key=lambda r: r['id']):
        model.addBoundConstr(cp.LinExpr([vs[t['variable_id']] for t in r['terms']], [t['coefficient'] for t in r['terms']]), lb=bound(r['lower']), ub=bound(r['upper']), name='r' + str(r['id']))
    obj = doc['objective']; expr = cp.LinExpr([vs[t['variable_id']] for t in obj['terms']], [t['coefficient'] for t in obj['terms']])
    expr.addConstant(obj['offset']); model.setObjective(expr, cp.COPT.MINIMIZE if obj['sense'] == 'minimize' else cp.COPT.MAXIMIZE)


def readback(model):
    from scipy import sparse
    shape = (int(model.getAttr('Rows')), int(model.getAttr('Cols')))
    # COPT refuses getA for a zero-column model; native dimensions prove emptiness.
    matrix = model.getA() if all(shape) else sparse.csc_matrix(shape)
    matrix.eliminate_zeros(); matrix.sort_indices()
    variables, rows = model.getVars(), model.getConstrs()
    info = lambda field, items: list(model.getInfo(field, items)) if len(items) else []
    return dict(shape=list(matrix.shape), indptr=matrix.indptr.tolist(), indices=matrix.indices.tolist(), data=matrix.data.tolist(),
                c=info('Obj', variables), lb=info('LB', variables), ub=info('UB', variables),
                lhs=info('LB', rows), rhs=info('UB', rows),
                sense='minimize' if model.getAttr('ObjSense') == 1 else 'maximize', offset=model.getAttr('ObjConst'),
                variable_names=[v.getName() for v in variables], row_names=[r.getName() for r in rows])


def readback_fixture():
    finite = lambda x: dict(kind='finite', value=x)
    return dict(schema_version=1, model_id='adapter-readback', variables=[
        dict(id=9, domain='continuous', lower=finite(-2), upper=finite(5)),
        dict(id=3, domain='continuous', lower=dict(kind='negative_infinity'), upper=dict(kind='positive_infinity')),
        dict(id=17, domain='continuous', lower=finite(0), upper=finite(0))], constraints=[
        dict(id=6, lower=finite(-3), upper=finite(4), terms=[dict(variable_id=9, coefficient=0.125), dict(variable_id=3, coefficient=-2.25)]),
        dict(id=2, lower=finite(0), upper=finite(0), terms=[]),
        dict(id=11, lower=dict(kind='negative_infinity'), upper=finite(9), terms=[dict(variable_id=9, coefficient=-0.0)]),
        dict(id=15, lower=finite(-7), upper=dict(kind='positive_infinity'), terms=[dict(variable_id=3, coefficient=1.0)])],
        objective=dict(sense='minimize', offset=7.125, terms=[dict(variable_id=9, coefficient=-1.5), dict(variable_id=3, coefficient=2.0)]))


def run_readback(value):
    import coptpy as cp
    from scipy import sparse
    directory = ROOT / value['acceptance_output']; cases = []
    for name, doc in [('mixed', readback_fixture()), ('empty_rows', dict(readback_fixture(), constraints=[])),
                      ('empty_columns', dict(readback_fixture(), variables=[], constraints=[], objective=dict(sense='minimize', offset=2.5, terms=[])))]:
        for sense in ['minimize', 'maximize']:
            doc = copy.deepcopy(doc); doc['objective']['sense'] = sense
            data = prepare(doc, cp.COPT.INFINITY)
            matrix = sparse.csc_matrix((data['data'], data['indices'], data['indptr']), shape=tuple(data['shape'])); matrix.eliminate_zeros(); matrix.sort_indices()
            expected = {k: data[k] for k in ['shape','c','lb','ub','lhs','rhs','sense','offset']}
            expected.update(indptr=matrix.indptr.tolist(), indices=matrix.indices.tolist(), data=matrix.data.tolist(),
                            variable_names=['v'+str(i) for i in data['variable_ids']], row_names=['r'+str(i) for i in data['row_ids']])
            for adapter in ['scalar', 'bulk']:
                env = cp.Envr(); model = env.createModel('adapter-readback'); model.setParam('GPUMode', 0)
                if adapter == 'scalar': scalar_load(cp, model, doc)
                else: load(cp, model, data, sparse)
                observed = readback(model)
                if not equal_bits(expected, observed): raise ValueError('native readback differs: ' + name + '/' + sense + '/' + adapter + ' ' + str(observed))
                cases.append(dict(case=name, sense=sense, adapter=adapter, matches=True, observed=observed))
    write_json(directory / 'readback.json', dict(status='passed', source_tree_sha256=source_identity(), dependencies_sha256=value['dependencies']['sha256'], cases=cases))
    print('12 scalar/bulk native readbacks match canonical inputs')


def run_endpoints(value, gpu):
    if gpu and (os.environ.get('AI_OPTIMIZER_GPU_LEASE') != 'inherited' or os.environ.get('CUDA_VISIBLE_DEVICES') != value['device']):
        raise ValueError('acceptance requires inherited shared lease and UUID')
    directory = ROOT / value['acceptance_output']; binary = ROOT / value['output'] / 'optimizer'
    options = dict(value['solve'], time_limit_ms=30000)
    config = directory / 'accept-solve.json'; write_json(config, options)
    original = read_json(ROOT / 'artifacts/lp-inputs-v1/gpup-development-irregular-256.json')
    results = []
    for sense in ['minimize', 'maximize']:
        doc = copy.deepcopy(original); doc['objective']['sense'] = sense; doc['objective']['offset'] = 7.0
        if sense == 'maximize':
            for t in doc['objective']['terms']: t['coefficient'] = -t['coefficient']
        model = directory / ('accept-' + sense + '.model.json'); write_json(model, doc)
        for method in [m for m in METHODS if (m == 'copt-gpu-pdlp') == gpu]:
            for adapter, script in [('scalar', 'lp_copt_comparison.py'), ('bulk', 'lp_copt_bulk.py')]:
                for profile in [False, True]:
                    key = 'accept-' + sense + '-' + method + '-' + adapter + ('-on' if profile else '-off')
                    output = directory / (key + '.json')
                    if output.exists(): raise ValueError('acceptance endpoint already attempted')
                    command = [str(ROOT / value['copt_python']), '-B', str(ROOT / 'tools' / script), '--model', str(model), '--config', str(config),
                               '--output', str(output), '--binary', str(binary), '--method', method, '--device', value['device'] if gpu else 'cpu']
                    if profile: command += ['--cost-profile', str(directory / (key + '.cost.json'))]
                    result = subprocess.run(command, env=environment(value, gpu), capture_output=True, text=True, timeout=35)
                    (directory / (key + '.stdout')).write_text(result.stdout); (directory / (key + '.stderr')).write_text(result.stderr)
                    if result.returncode: raise ValueError('acceptance worker failed: ' + key)
                    endpoint = read_json(output)
                    if endpoint['witness']['executed_backend'] != method or endpoint['assessment']['classification'] != 'certified_success':
                        raise ValueError('acceptance did not certify requested method: ' + key)
                    for verifier in [binary, ROOT / value['baseline_output'] / 'optimizer']:
                        check = subprocess.run([str(verifier), 'lp-study', 'external-verify', '--model', str(model), '--evidence', str(output)], capture_output=True, timeout=120)
                        if check.returncode: raise ValueError('independent acceptance verification failed: ' + key)
                    if profile: validate_profile(read_json(directory / (key + '.cost.json')))
                    results.append(dict(id=key, sense=sense, method=method, adapter=adapter, profile=profile, model=reference(directory, model),
                                        endpoint=reference(directory, output), numerical_sha256=numerical_digest(endpoint)))
    comparisons = []
    for sense in ['minimize', 'maximize']:
        for method in sorted({r['method'] for r in results}):
            group = [r for r in results if r['sense'] == sense and r['method'] == method]
            comparisons.append(dict(sense=sense, method=method, matching=len({r['numerical_sha256'] for r in group}) == 1))
    if not all(c['matching'] for c in comparisons): raise ValueError('acceptance numerical/work discrepancy requires diagnosis')
    write_json(directory / ('endpoints-gpu.json' if gpu else 'endpoints-cpu.json'), dict(status='passed', source_tree_sha256=source_identity(),
               binary_sha256=file_hash(binary), dependencies_sha256=value['dependencies']['sha256'], results=results, comparisons=comparisons))
    print(str(len(results)) + ' endpoints certify; scalar/bulk/profile numerical state and work match')


def check_acceptance(value):
    directory = ROOT / value['acceptance_output']; source = source_identity()
    for name, count in [('readback.json', 12), ('endpoints-cpu.json', 16), ('endpoints-gpu.json', 8)]:
        data = read_json(directory / name)
        if data['status'] != 'passed' or data['source_tree_sha256'] != source or data['dependencies_sha256'] != value['dependencies']['sha256']:
            raise ValueError('acceptance source/dependency identity differs')
        if len(data.get('cases', data.get('results', []))) != count: raise ValueError('incomplete acceptance')
        if 'results' in data:
            if data['binary_sha256'] != file_hash(ROOT / value['output'] / 'optimizer'): raise ValueError('acceptance binary differs')
            for r in data['results']:
                checked_reference(directory, r['model']); checked_reference(directory, r['endpoint'])
    key = value['id'] + '-accept-endpoints'
    request = directory / (key + '.request.json'); worker = read_json(directory / (key + '.worker.json')); binding = read_json(directory / (key + '.source.json'))
    if worker['reason'] != 'completed' or worker['returncode'] != 0 or binding['source_tree_sha256'] != source or binding['request_sha256'] != file_hash(request):
        raise ValueError('leased acceptance receipt differs')


def main():
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('mode', choices=['readback', 'cpu', 'gpu']); a = p.parse_args(); value = protocol()
    if a.mode == 'readback': run_readback(value)
    else: run_endpoints(value, a.mode == 'gpu')


if __name__ == '__main__': main()
