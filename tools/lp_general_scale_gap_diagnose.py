"""Exact objective diagnosis of retained PDS endpoints; no solve or regrading."""
import argparse
from fractions import Fraction
import math
from lp_general_common import BASE, ROOT, load, put, ref, require
from lp_general_scale_evidence import read as read_response
from lp_general_scale_io import read


def run(identity):
    out=BASE/identity;out.mkdir(exist_ok=False);rows=[]
    directory=BASE/'scale-final-main-tail-v2/m00'
    for cell in sorted(directory.glob('*.cell.json')):
        row=load(cell);r=read_response(ROOT/row['response']['path'])
        data=read(ROOT/row['model']['path']);x=r['primal'];cert=row['certificate']
        exact=Fraction(float(data['offset']))
        for j,c in zip(data['objective_indices'],data['objective_values']):
            exact+=Fraction(float(c))*Fraction(x[int(j)])
        bound=cert['bound'];require(bound is not None,'retained PDS bound missing')
        gap=(exact-Fraction(bound))*(1 if data['sense']=='minimize' else -1)
        approximate_allowance=cert['tolerance']*(1+max(abs(float(exact)),abs(bound)))
        rows.append(dict(cell=ref(cell),response=row['response'],model=row['model'],lane=row['cell']['lane'],
            original_certificate=cert,exact_objective_numerator=str(exact.numerator),exact_objective_denominator=str(exact.denominator),
            exact_directed_gap_numerator=str(gap.numerator),exact_directed_gap_denominator=str(gap.denominator),
            exact_directed_gap_float=float(gap),objective_ulp=math.ulp(float(exact)),
            approximate_upper_gap_allowance=approximate_allowance,
            lower_gap_guard_implicated=bool(cert['feasible'] and not cert['accepted'] and cert['gap_upper']<approximate_allowance*.5)))
    require(len(rows)==3,'retained public tail coverage')
    put(out/'result.json',dict(status='passed',rows=rows,source=ref(__file__),
        original_gap_source=ref(ROOT/'crates/optimizer-lp/src/certify.rs'),
        claim='Exact rational objective at unchanged retained endpoints. Does not re-evaluate feasibility, prove a new dual bound, regrade a historical certificate or repair a missing timing. The lower-guard diagnosis follows the unchanged assess_gap predicate; the displayed allowance is diagnostic, not a replacement outward computation.'))
    print([(r['lane'],r['exact_directed_gap_float'],r['lower_gap_guard_implicated']) for r in rows],flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--id',required=True);run(p.parse_args().id)
