"""Explicit operational-stop adapter; the frozen analysis remains byte-exact.

This adapter adds the unattempted-block ledger after repeated supervision loss.
It uses the original frozen assessment and archive format, and can never turn an
incomplete cohort into a pass. No absent reservation is invented or charged.
"""
import argparse
from lp_mixed2_reuse_common import BASE, load, put, ref, require
import lp_mixed2_reuse_analysis as analysis


def collect():
    freeze=load(BASE/'confirmation-freeze.json');stop=load(BASE/'confirmation-stop-v1.json')
    require(stop['freeze']==ref(BASE/'confirmation-freeze.json') and stop['status']=='operational-stop',
            'operational stop binding')
    untouched=stop['unattempted_blocks'];require(len(set(untouched))==len(untouched),'duplicate unattempted block')
    require(all(type(i) is int and 0<=i<freeze['blocks'] for i in untouched),'unattempted block index')
    sessions=[];records={};failures=[]
    for b in range(freeze['blocks']):
        folder=BASE/f'confirmation-b{b:02d}';prefix=BASE/'resources'/f'confirmation-b{b:02d}'
        if b in untouched:
            require(not folder.exists() and not prefix.with_suffix('.reservation.json').exists() and
                    not prefix.with_suffix('.settlement.json').exists(),'unattempted block has execution evidence')
            continue
        settlement=load(prefix.with_suffix('.settlement.json'))
        if settlement['status']!='passed':failures.append(dict(block=b,settlement=settlement))
        if (folder/'result.json').exists():ss=load(folder/'result.json')['sessions']
        else:
            require(settlement['status']=='refused','missing block without refusal')
            ss=[load(p) for p in sorted(folder.glob('*.session.json'))]
        sessions.extend(ss)
        for p in folder.glob('*-r[0-9][0-9].json'):records[str(p.relative_to(analysis.ROOT))]=p
    require(sorted(r['block'] for r in failures)==stop['failed_blocks'],'stop failure ledger drift')
    missing=sorted({c['id'] for c in freeze['cells']}-{s['id'] for s in sessions})
    require(missing,'operational stop must remain incomplete')
    return freeze,sessions,records,missing,failures


def publish():
    analysis.collect=collect
    analysis.publish()
    require(load(analysis.ANALYSIS)['status']=='incomplete-confirmation','incomplete assessment changed')
    put(analysis.DATA/'mixed2-reuse-coverage-v1.json',dict(stop=load(BASE/'confirmation-stop-v1.json'),
        stop_binding=ref(BASE/'confirmation-stop-v1.json'),adapter=ref(__file__),
        frozen_analysis=ref(analysis.__file__),analysis=ref(analysis.ANALYSIS),
        historical_regrading=False,scientific_retry=False))


if __name__=='__main__':
    argparse.ArgumentParser(description=__doc__).parse_args();publish()
