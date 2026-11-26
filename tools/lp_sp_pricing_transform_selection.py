"""Prespecified finite step-size selection on development-only fresh inputs."""
import json
import math
from lp_sp_pricing_budget import ROOT,BASE,put,binding
from lp_sp_pricing_gpu_opt_compare import read
from lp_sp_pricing_factor_experiment import SPECS
from lp_sp_pricing_scale_experiment import generate
from lp_sp_pricing_transform_admit import validate,sources
from lp_sp_pricing_transform_experiment import cell


def run():
    gate=validate();out=BASE/'transform-selection-v1';out.mkdir(exist_ok=False)
    put(out/'plan.json',dict(source=binding(__file__),admission=gate,sources=sources()+[
        binding(ROOT/'tools/lp_sp_pricing_transform_endpoint.py'),binding(ROOT/'tools/lp_sp_pricing_transform_experiment.py')],
        seed=124301,multipliers=[1,4,16,64],representations=['factor','transform'],families=SPECS[:3],
        selection='Require timely independently accepted certificates on all three scales; select minimum geometric mean complete cost. Tie resolves to smaller multiplier. Preserve every outcome; holdout seeds are separate.'))
    rows=[]
    for index,spec in enumerate(SPECS[:3]):
        model=generate(spec,124301,out/'models'/spec['name'])
        choices=[(representation,multiplier) for representation in ('factor','transform') for multiplier in (1,4,16,64)]
        choices=choices[index:]+choices[:index]
        for representation,multiplier in choices:
            row=cell(model,'optimized',out/'runs'/f"{spec['name']}-{representation}-rho-{multiplier}",multiplier,representation)
            row.update(rho_multiplier=multiplier,representation=representation);rows.append(row)
    scores=[]
    for representation in ('factor','transform'):
        for multiplier in (1,4,16,64):
            group=[r for r in rows if r['rho_multiplier']==multiplier and r['representation']==representation]
            if len(group)==3 and all(r['accepted'] and r['timely'] for r in group):
                scores.append(dict(representation=representation,rho_multiplier=multiplier,geometric_mean_complete_ns=math.exp(sum(math.log(r['complete_ns']) for r in group)/3)))
    if not scores:raise RuntimeError('no valid selection')
    selected=min(scores,key=lambda r:(r['geometric_mean_complete_ns'],r['rho_multiplier'],r['representation']))
    put(out/'result.json',dict(status='selected',**selected,scores=scores,rows=rows,plan=binding(out/'plan.json')))
    print(json.dumps(selected),flush=True)


if __name__=='__main__':run()
