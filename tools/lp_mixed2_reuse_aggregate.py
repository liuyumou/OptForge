"""Bind all separately bounded family admissions before confirmation."""
from lp_mixed2_reuse_common import BASE, BINARY, IMAGE, load, put, ref, require


def run():
    out=BASE/'scenario-large-v2';out.mkdir(exist_ok=False)
    models=load(BASE/'models/manifest.json');sessions=[];refs=[];comparisons=0
    for family in sorted(models['groups']):
        name='scenario-v2-'+family
        require(load(BASE/'resources'/(name+'.settlement.json'))['status']=='passed','family supervision failed')
        m=load(BASE/name/'manifest.json');r=load(BASE/name/'result.json')
        require(m['binary']==ref(BINARY) and m['image']==ref(IMAGE) and r['status']=='passed','family image admission')
        require(len(r['sessions'])==4,'family lane/tier coverage')
        sessions+=r['sessions'];comparisons+=r['fresh_comparisons']
        refs.extend([ref(BASE/name/'manifest.json'),ref(BASE/name/'result.json'),
                     ref(BASE/'resources'/(name+'.settlement.json'))])
    put(out/'result.json',dict(status='passed',sessions=sessions,fresh_comparisons=comparisons,bindings=refs))


if __name__=='__main__':run()
