"""Prospectively specified changing-RHS/objective fixtures and CPU admission."""
import json
import subprocess
import numpy as np
from lp_mixed2_reuse_common import BASE, OLD, BINARY, ROOT, load, put, ref, require
from lp_mixed2_fp4_cpu import fixture, environment


def run():
    out = BASE / 'models-v3'
    out.mkdir(exist_ok=False)
    old = load(OLD / 'models/manifest-v2.json')
    groups = {}
    for family in ('dense-generic-1024', 'dense-generic-2048',
                   'dense-coupled-1024', 'dense-coupled-2048', 'dense-coupled-33'):
        n = int(family.rsplit('-', 1)[1]); i = np.arange(n)
        if n == 33:
            a = np.eye(n) + (((13*i[:, None]+7*i[None, :]) % 37)-18)/(73*n)
            a[i, (i+1) % n] += .5
            doc = fixture(a, 'reuse-control')
        else:
            source = ROOT / old['models'][family]['path']
            require(source.stat().st_size <= 384 << 20, 'model exceeds admitted 384 MiB')
            with source.open() as stream: doc = json.load(stream)
            a = np.zeros((n, n))
            for row, constraint in enumerate(doc['constraints']):
                for term in constraint['terms']:
                    a[row, (term['variable_id']-7)//3] = term['coefficient']
        models = []
        for scenario in range(4):
            x = ((13*i+5*scenario) % 37)/37-.5
            y = ((7*i+3*scenario) % 29)/29-.5
            rhs = a @ x; c = a.T @ y
            doc['model_id'] = f'mixed2-reuse-{family}-s{scenario}'
            for row, value in zip(doc['constraints'], rhs):
                row['lower'] = dict(kind='finite', value=float(value))
                row['upper'] = dict(kind='finite', value=float(value))
            doc['objective']['offset'] = 3.25 + .125*scenario
            doc['objective']['terms'] = [dict(variable_id=3*j+7, coefficient=float(c[j]))
                                         for j in range(n) if c[j] != 0]
            path = out / f'{family}-s{scenario}.json'
            with path.open('x') as stream:
                json.dump(doc, stream, separators=(',', ':'), allow_nan=False)
            process = subprocess.run([str(BINARY), 'check-service', str(path)], input=b'',
                                     capture_output=True, check=True, timeout=90, env=environment())
            require(json.loads(process.stdout)['ready'], 'scenario CPU checker admission')
            models.append(ref(path))
            print(dict(family=family, scenario=scenario, cpu_checker='passed'), flush=True)
        groups[family] = models
        del doc, a
    put(BASE/'models/manifest.json', dict(groups=groups, generator=ref(__file__), binary=ref(BINARY),
                                 settings=old['settings'], original=ref(OLD/'models/manifest-v2.json')))


if __name__ == '__main__':
    run()
