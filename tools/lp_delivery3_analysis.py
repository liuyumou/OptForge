"""Prospectively specified diagnostic selection, separate from confirmation."""
import math
import statistics
from lp_delivery3_common import ROOT, BASE, BINARY, VARIANTS, LANES, TIERS, load, put, ref, require
from lp_delivery3_study import DIAGNOSTIC, validate_manifest


def select():
    profile=BASE/'profile-v1';diagnostic=BASE/'diagnostic-v1'
    for directory in (profile,diagnostic):
        require(load(directory/'result.json')['status']=='complete','diagnosis incomplete')
        validate_manifest(load(directory/'manifest.json'))
    rows=load(diagnostic/'result.json')['rows']
    require(len(rows)==512,'diagnostic coverage')
    lookup={(r['block'],r['family'],r['lane'],r['tier'],r['lifecycle'],r['variant']):r for r in rows}
    require(len(lookup)==512,'duplicate diagnostic identity')
    scores=[];candidates={}
    for lifecycle in ('cold','prepared'):
        families=('dense-generic-512',) if lifecycle=='cold' else DIAGNOSTIC
        for variant in VARIANTS:
            ratios=[];regressions=[]
            for family in DIAGNOSTIC:
                for lane in LANES:
                    for tier in TIERS:
                        a=[lookup[b,family,lane,tier,lifecycle,'control']['complete_ns']/1e6 for b in range(4)]
                        c=[lookup[b,family,lane,tier,lifecycle,variant]['complete_ns']/1e6 for b in range(4)]
                        if family in families:ratios.extend(x/y for x,y in zip(a,c))
                        if statistics.median(c)-statistics.median(a)>max(.02*statistics.median(a),.10):regressions.append(dict(family=family,lane=lane,tier=tier))
            score=math.exp(statistics.mean(math.log(v) for v in ratios))
            eligible=score>=(1.01 if lifecycle=='cold' else 1.02) and (lifecycle=='cold' or not regressions)
            scores.append(dict(lifecycle=lifecycle,variant=variant,score=score,eligible=eligible,diagnostic_regressions=regressions))
        valid=[s for s in scores if s['lifecycle']==lifecycle and s['eligible']]
        candidates[lifecycle]=max(valid,key=lambda s:(s['score'],-VARIANTS.index(s['variant'])))['variant'] if valid else 'control'
    put(BASE/'selection-v1.json',dict(status='frozen',binary=ref(BINARY),profile=ref(profile/'result.json'),diagnostic=ref(diagnostic/'result.json'),
        candidates=candidates,scores=scores,source=ref(ROOT/'tools/lp_delivery3_analysis.py'),not_a_retention_claim=True))
    print(dict(candidates=candidates,scores=scores),flush=True)

if __name__=='__main__':select()
