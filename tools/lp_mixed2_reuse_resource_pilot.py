"""One prospective whole-block resource smoke; never part of confirmation."""
from lp_mixed2_reuse_common import BASE, BINARY, IMAGE, ROOT, load, put, ref, require
from lp_mixed2_reuse_confirmation import roster
from lp_mixed2_reuse_study import execute_session


def run():
    out=BASE/'resource-pilot-v1';out.mkdir(exist_ok=False)
    models=load(BASE/'models/manifest.json');cells=[c for c in roster(2,390073) if c['block']==0]
    put(out/'manifest.json',dict(binary=ref(BINARY),image=ref(IMAGE),cells=cells,count=32,
        purpose='whole-block resource admission and complete-cost diagnosis, excluded from confirmation'))
    for name in ['device-v2','scenario-large-v2']+[
            n+'-v2' for n in ('memcheck','racecheck','initcheck','synccheck')]+[
            'scenario-'+n+'-v3' for n in ('memcheck','racecheck','initcheck','synccheck')]:
        require(load(BASE/name/'result.json')['status']=='passed','resource smoke admission')
    for paths in models['groups'].values():
        for item in paths:require(ref(ROOT/item['path'])==item,'resource pilot model binding')
    rows=[execute_session(out,c,models) for c in cells]
    put(out/'result.json',dict(status='passed',sessions=rows))


if __name__=='__main__':run()
