"""Prospective pilot admission; no tuning from confirmation observations."""
import math
import statistics
from lp_delivery4_common import ROOT,BASE,BINARY,LANES,TIERS,load,put,ref,require
from lp_delivery4_study import validate_manifest


def select():
    for kind in ('profile','diagnostic'):
        directory=BASE/(kind+'-v1');require(load(directory/'result.json')['status']=='complete','incomplete pilot');validate_manifest(load(directory/'manifest.json'))
    rows=load(BASE/'diagnostic-v1/result.json')['rows'];require(len(rows)==128,'pilot roster')
    index={(r['block'],r['family'],r['lane'],r['tier'],r['role']):r for r in rows};require(len(index)==128,'duplicate pilot identity')
    ratios=[index[b,'dense-generic-512',l,t,'control']['complete_ns']/index[b,'dense-generic-512',l,t,'candidate']['complete_ns'] for b in range(4) for l in LANES for t in TIERS]
    score=math.exp(statistics.mean(math.log(v) for v in ratios))
    put(BASE/'selection-v1.json',dict(status='frozen',binary=ref(BINARY),profile=ref(BASE/'profile-v1/result.json'),diagnostic=ref(BASE/'diagnostic-v1/result.json'),score=score,eligible=score>=1.01,ratios=ratios,candidate='candidate',source=ref(ROOT/'tools/lp_delivery4_analysis.py'),not_a_retention_claim=True))
    print(dict(score=score,eligible=score>=1.01),flush=True)
if __name__=='__main__':select()
