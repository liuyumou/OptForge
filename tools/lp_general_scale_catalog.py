"""Compact public mapping from frozen cell indices to original model identities."""
import argparse
from pathlib import Path
from lp_general_common import BASE,load,put,ref


def run(output):
    campaigns=[]
    for p in sorted(BASE.glob('scale-*/freeze.json')):
        f=load(p)
        if f.get('mode') not in ['pilot','scale','broad']:continue
        models=[]
        for i,m in enumerate(f['models']):
            row={k:m[k] for k in ['family','model','rows','columns','nonzeros','target','seed','source_group'] if k in m}
            models.append(dict(model_index=i,**row))
        campaigns.append(dict(identity=p.parent.name,freeze=ref(p),models=models,
            unsupported_models=f.get('unsupported_models',[]),continuation_of=f.get('continuation_of')))
    put(output,dict(campaigns=campaigns,source=ref(__file__),
        note='Joins compact result model_index values to frozen original identities. Omitted metadata was not present in that historical freeze; no dimensions are inferred from file names. Repeated model identities are shared development inputs, not independent application samples.'))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);run(p.parse_args().output)
