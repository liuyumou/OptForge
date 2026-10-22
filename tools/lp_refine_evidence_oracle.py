"""Post-study exact original-operator checks, independent of Rust interval code.

Fraction treats each serialized binary64 value as an exact rational. Sparse
original coefficients determine both orientations; no represented CUDA operator,
candidate residual, or candidate merit is trusted. This is validation tooling,
not a replacement for the authoritative original-model host certificate.
"""
import argparse
from fractions import Fraction as F
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError('duplicate key')
            result[key] = value
        return result
    def constant(value):
        raise ValueError('nonfinite JSON: ' + value)
    return json.loads(path.read_text(), object_pairs_hook=pairs, parse_constant=constant)


def rational(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError('expected finite number')
    return F(value)


def exact_pair(value):
    return dict(numerator=str(value.numerator), denominator=str(value.denominator))


def clip(value, bounds):
    lower, upper = bounds
    if lower is not None:
        value = max(lower, value)
    if upper is not None:
        value = min(upper, value)
    return value


class Original:
    def __init__(self, model):
        variables = sorted(model['variables'], key=lambda x: x['id'])
        rows = sorted(model['constraints'], key=lambda x: x['id'])
        ids = {x['id']: j for j, x in enumerate(variables)}
        if len(ids) != len(variables) or len({x['id'] for x in rows}) != len(rows):
            raise ValueError('duplicate original IDs')
        self.n = len(variables)
        self.m = len(rows)
        self.rows = []
        for row in rows:
            values = {}
            for term in row['terms']:
                j = ids[term['variable_id']]
                values[j] = values.get(j, F()) + rational(term['coefficient'])
            self.rows.append(values)
        self.c = [F() for _ in variables]
        for term in model['objective']['terms']:
            self.c[ids[term['variable_id']]] += rational(term['coefficient'])
        self.offset = rational(model['objective']['offset'])
        sense = 1 if model['objective']['sense'] == 'minimize' else -1
        self.g = [sense * x for x in self.c] + [F() for _ in rows]
        self.box = []
        for item in variables + rows:
            lower, upper = (item[k] for k in ('lower', 'upper'))
            if lower['kind'] not in ('finite', 'negative_infinity') or upper['kind'] not in ('finite', 'positive_infinity'):
                raise ValueError('invalid bound tag')
            bounds = tuple(rational(b['value']) if b['kind'] == 'finite' else None for b in (lower, upper))
            if None not in bounds and bounds[0] > bounds[1]:
                raise ValueError('invalid bounds')
            self.box.append(bounds)
        self.sv = [max([F(1)] + [abs(x) for x in bounds if x is not None]) for bounds in self.box]
        self.sg = [max(F(1), abs(x)) for x in self.g]
        self.sp = [max(F(1), self.sv[self.n+i] + sum((abs(a)*self.sv[j] for j, a in row.items()), F())) for i, row in enumerate(self.rows)]

    def evaluate(self, primal, dual):
        if len(primal) != self.n + self.m or len(dual) != self.m:
            raise ValueError('original dimensions differ')
        v, y = list(map(rational, primal)), list(map(rational, dual))
        activity = [sum((a*v[j] for j, a in row.items()), F()) for row in self.rows]
        rp = [v[self.n+i] - value for i, value in enumerate(activity)]
        rd = self.g.copy()
        for row, yi in zip(self.rows, y):
            for j, a in row.items():
                rd[j] -= a*yi
        for i, yi in enumerate(y):
            rd[self.n+i] += yi
        eq = max((abs(r)/s for r, s in zip(rp, self.sp)), default=F())
        box = max((abs(x-clip(x, b))/s for x, b, s in zip(v, self.box, self.sv)), default=F())
        stationarity = max((abs(x-clip(x-s/t*r, b))/s for x, s, t, r, b in zip(v, self.sv, self.sg, rd, self.box)), default=F())
        original = v[:self.n] + activity
        violation = max((abs(x-clip(x, b)) for x, b in zip(original, self.box)), default=F())
        objective = self.offset + sum((a*x for a, x in zip(self.c, v)), F())
        return dict(merit=max(eq, box, stationarity), equality=eq, box=box,
                    stationarity=stationarity, original_violation=violation, objective=objective)


def enclosed(value, interval):
    lower, upper = rational(interval['lower']), rational(interval['upper'])
    if not lower <= value <= upper:
        raise ValueError('exact original merit escapes recorded enclosure')


def verify(original, outcome):
    count = 0
    contractions = 0
    position = 0
    for trace in outcome['trace']:
        if trace['physical_updates'] < position or trace['physical_updates'] > outcome['work']['physical_updates']:
            raise ValueError('nonmonotonic trace work')
        position = trace['physical_updates']
        anchor = original.evaluate(trace['anchor_v'], trace['anchor_y'])['merit']
        enclosed(anchor, trace['anchor_merit'])
        count += 1
        if trace['candidate_merit'] is not None:
            candidate = original.evaluate(trace['candidate_v'], trace['candidate_y'])['merit']
            enclosed(candidate, trace['candidate_merit'])
            count += 1
            if trace['decision'] == 'contracted':
                if candidate > anchor/2:
                    raise ValueError('false exact contraction')
                contractions += 1
        elif trace['decision'] in ('contracted', 'certified'):
            raise ValueError('missing candidate')
    final = original.evaluate(outcome['v'], outcome['y'])
    return dict(merit_enclosures=count, contractions=contractions,
                final={key: exact_pair(value) for key, value in final.items()})


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--directory', type=Path, default=ROOT/'artifacts/gpup-refine-v2')
    args = parser.parse_args()
    report_path = args.directory/'report.json'
    report = load(report_path)
    protocol = load(args.directory/'study/campaign.json')
    models = {i['id']: i['model'] for manifest in protocol['manifests'] for i in load(ROOT/manifest['path'])['instances']}
    rows = []
    for row in report['rows']:
        if not row['verified'] or row['configuration'] == 'tuned-fp64':
            continue
        endpoint_path = args.directory/'study'/(row['id']+'.endpoint.json')
        model_ref = models[row['instance']]
        model_path = ROOT/model_ref['path']
        if digest(model_path) != model_ref['sha256']:
            raise ValueError('original model hash differs')
        endpoint = load(endpoint_path)
        if endpoint['witness']['request']['source_tree_sha256'] != report['source_tree_sha256']:
            raise ValueError('frozen source identity differs')
        checked = verify(Original(load(model_path)), endpoint['witness']['outcome'])
        rows.append(dict(id=row['id'], model_sha256=digest(model_path), endpoint_sha256=digest(endpoint_path), **checked))
    result = dict(identity='gpup-refine-exact-evidence-v1', source_tree_sha256=report['source_tree_sha256'],
                  report_sha256=digest(report_path), oracle_sha256=digest(Path(__file__)),
                  endpoints=len(rows), merit_enclosures=sum(r['merit_enclosures'] for r in rows),
                  contractions=sum(r['contractions'] for r in rows), rows=rows)
    (args.directory/'exact-evidence.json').write_text(json.dumps(result, sort_keys=True, indent=2, allow_nan=False)+'\n')
    print(json.dumps({key: value for key, value in result.items() if key != 'rows'}, sort_keys=True))


if __name__ == '__main__':
    main()
