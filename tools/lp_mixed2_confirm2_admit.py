"""Fresh same-image lifecycle and complete-block resource admission."""
import argparse
import random
from lp_mixed2_confirm2_common import BASE, PRIOR, ROOT, BINARY, IMAGE, load, put, ref, require
from lp_mixed2_confirm2_confirmation import FAMILIES, TIERS, environment_snapshot
from lp_mixed2_reuse_study import execute_session
from lp_mixed2_reuse_admit import numerical


def run(kind):
    count=4 if kind=='same-image-smoke' else 32
    out=BASE/(kind+'-v1');out.mkdir(exist_ok=False)
    prior=load(PRIOR/'confirmation-freeze.json')
    require(prior['binary']==ref(BINARY) and prior['image']==ref(IMAGE),'numerical image changed')
    for item in prior['sources']+prior['admissions']:
        require(ref(ROOT/item['path'])==item,'historical source or admission changed')
    models=load(PRIOR/'models/manifest.json')
    cells=[dict(id=f'{family}-{tier}-{lane}',block=0,family=family,tier=tier,lane=lane,position=position)
           for family in FAMILIES for tier in TIERS for position,lane in enumerate(['native','fp4x2'])]
    random.Random(400074).shuffle(cells)
    put(out/'manifest.json',dict(binary=ref(BINARY),image=ref(IMAGE),models=ref(PRIOR/'models/manifest.json'),
        count=count,seed=400074,cells=cells,source=ref(__file__),environment=environment_snapshot(),
        scientific_confirmation=False))
    rows=[];comparisons=0
    for cell in cells:
        row=execute_session(out,cell,models,count=count)
        for r in row['records']:
            old=PRIOR/('scenario-v2-'+cell['family'])/(cell['id']+f'-r{r["scenario"]:02d}.json')
            require(numerical(load(ROOT/r['result']['path']))==numerical(load(old)),
                    'fresh supervision changed numerical result')
            comparisons+=1
        rows.append(row)
    put(out/'result.json',dict(status='passed',sessions=rows,exact_historical_comparisons=comparisons,
                              environment=environment_snapshot()))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('kind',choices=['same-image-smoke','resource-pilot','resource-pilot2','resource-pilot3'])
    run(p.parse_args().kind)
