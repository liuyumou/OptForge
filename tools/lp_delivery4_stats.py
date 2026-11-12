"""Frozen prospective median intervals and per-route retention decisions."""
import math
import statistics
from lp_delivery4_common import require, LANES, TIERS, TARGETS
METRICS = 48
BLOCKS = 32


def interval(values, metrics=METRICS):
    require(values and all(math.isfinite(v) for v in values), 'empty or nonfinite metric')
    require(type(metrics) is int and metrics > 0, 'invalid simultaneous metric count')
    n=len(values)
    ranks=[k for k in range(1,n//2+1) if sum(math.comb(n,i) for i in range(k))*40*metrics <= 2**n]
    if not ranks: return dict(median=statistics.median(values), lower=None, upper=None, ranks=None, n=n)
    k=max(ranks); ordered=sorted(values)
    return dict(median=statistics.median(values),lower=ordered[k-1],upper=ordered[n-k],ranks=[k,n-k+1],n=n)


def classify(ci, threshold, benefit):
    if ci['lower'] is None: return 'inconclusive'
    if benefit:
        if ci['lower'] >= threshold: return 'supported'
        if ci['upper'] < threshold: return 'insufficient-benefit'
    else:
        if ci['upper'] <= threshold: return 'supported'
        if ci['lower'] > threshold: return 'material-regression'
    return 'inconclusive'


def paired(rows, families, blocks):
    index={}
    for row in rows:
        key=tuple(row[k] for k in ('block','family','lane','tier','lifecycle','role'))
        require(key not in index,'duplicate confirmation identity');index[key]=row
        require(row['complete_ns']>0,'nonpositive complete cost')
    require(len(index)==len(families)*len(blocks)*2*2*2,'missing or extra confirmation cells')
    for block in blocks:
        for family in families:
            for lane in LANES:
                for tier in TIERS:
                    for lifecycle in ('cold',):
                        for role in ('control','candidate'):
                            require((block,family,lane,tier,lifecycle,role) in index,'confirmation grid mismatch')
    return index


def summarize(rows, families):
    blocks=list(range(BLOCKS));index=paired(rows,families,blocks)
    bounded=[f for f in families if f!='infinite-bound-refusal']
    require(len(families)==12 and len(bounded)==11 and set(TARGETS)<=set(bounded),'declared model roster changed')
    decisions=[]
    for lifecycle in ('cold',):
        for tier in TIERS:
            for lane in LANES:
                guards=[]; ratios=[]; missing=[]
                for block in blocks:
                    target=[]
                    for family in families:
                        a=index[block,family,lane,tier,lifecycle,'control'];b=index[block,family,lane,tier,lifecycle,'candidate']
                        if family in bounded and not (a['certified'] and b['certified']): missing.append([block,family])
                        if family not in bounded and (a['certified'] or b['certified']): missing.append([block,family])
                        if family in TARGETS: target.append(a['complete_ns']/b['complete_ns'])
                    ratios.append(math.exp(statistics.mean(math.log(v) for v in target)))
                benefit=interval(ratios);benefit['decision']=classify(benefit,1.1,True)
                for family in bounded:
                    values=[]
                    for block in blocks:
                        a=index[block,family,lane,tier,lifecycle,'control']['complete_ns']/1e6
                        b=index[block,family,lane,tier,lifecycle,'candidate']['complete_ns']/1e6
                        values.append(b-a-max(.02*a,.10))
                    ci=interval(values);guards.append(dict(family=family,**ci,decision=classify(ci,0.,False)))
                statuses=[benefit['decision']]+[g['decision'] for g in guards]
                decision=('correctness-or-coverage-failure' if missing else 'supported' if all(s=='supported' for s in statuses)
                          else 'material-regression' if 'material-regression' in statuses else 'insufficient-benefit' if 'insufficient-benefit' in statuses else 'inconclusive')
                decisions.append(dict(lifecycle=lifecycle,tier=tier,lane=lane,decision=decision,benefit=benefit,guards=guards,coverage_failures=missing))
    require(sum(1+len(d['guards']) for d in decisions)==METRICS,'simultaneous metric roster')
    return decisions
