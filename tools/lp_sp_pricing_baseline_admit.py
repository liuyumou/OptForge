"""Separate-seed baseline adapter admission; no held-out tuning."""
import json
import sys
from lp_sp_pricing_budget import BASE,put,binding
from lp_sp_pricing_baselines import portable,launch,audit,images
from lp_sp_pricing_study import generated


if __name__=='__main__':
    out=BASE/sys.argv[1];out.mkdir(exist_ok=False)
    put(out/'plan.json',dict(families=['dense','wide','ill_scaled'],columns=4,seed=73335,
        lanes=['practical','retained_image_v11','copt_scale_off'],images=images(),heldout=False))
    rows=[]
    for family in ('dense','wide','ill_scaled'):
        directory=out/family;directory.mkdir()
        model,construction=generated(dict(family=family,columns=4,rows=2 if family=='wide' else 8,seed=73335))
        path=directory/'rational.json';put(path,model);put(directory/'construction.json',construction)
        native=directory/'portable.json';portable(model,native)
        for lane in ('practical','retained_image_v11','copt_scale_off'):
            target=directory/lane
            process=launch(lane,native,path,target,10,30,roundtrip=True)
            checked=audit(lane,native,path,target)
            row=dict(family=family,lane=lane,process=process,accepted=checked['accepted'],checks=checked['checks'],
                audit=binding(target/'audit.json'))
            rows.append(row);print(json.dumps(row),flush=True)
    # A valid bounded result is needed from each baseline to admit its endpoint
    # convention. Difficult-case nonconvergence is recorded, never hidden.
    admitted=all(any(r['lane']==lane and r['accepted'] for r in rows)
                 for lane in ('practical','retained_image_v11','copt_scale_off'))
    put(out/'result.json',dict(status='passed' if admitted else 'not_admitted',rows=rows,
        sources=[binding(__file__),binding(__file__.replace('_baseline_admit.py','_baselines.py'))],images=images()))
    if not admitted:raise SystemExit(2)
