"""Additive proof that a failed study cleanup has subsequently finished.

Original receipts, full charges and stale journal records remain unchanged.
Only exact PID/start identities are examined. Overruns receive no exception.
GPU work additionally needs a fresh source-bound CPU readmission.
"""
import json
from pathlib import Path
import sys
import time
from lp_sp_pricing_budget import BASE,ROOT,binding,put


def read(path):return json.loads(Path(path).read_text())


def identities(value):
    result=set()
    if isinstance(value,dict):
        if 'pid' in value and 'start_ticks' in value:result.add((int(value['pid']),int(value['start_ticks'])))
        for child in value.values():result.update(identities(child))
    elif isinstance(value,list):
        for child in value:result.update(identities(child))
    return result


def live(pid,start):
    try:fields=Path(f'/proc/{pid}/stat').read_text().rsplit(')',1)[1].split()
    except FileNotFoundError:return False
    return int(fields[19])==start


def inputs(reservation):
    prefix=Path(str(reservation).replace('.reservation.json',''))
    paths=[Path(str(prefix)+suffix) for suffix in ['.reservation.json','.settlement.json','.resource.json','.journal.json']]
    reserved,settled,resource,journal=map(read,paths)
    if settled['status']!='refused' or settled['overrun'] or settled['cleanup_empty']:
        raise RuntimeError('not a failed non-overrun cleanup')
    if any(settled[k]<reserved[k] for k in ['cpu_ns','gpu_ns']):raise RuntimeError('original full charge missing')
    owned=identities(resource)|identities(journal)
    if not owned:raise RuntimeError('no recorded process identities')
    return prefix,paths,owned


def verify(reservation):
    prefix,paths,owned=inputs(reservation)
    proof=read(str(prefix)+'.cleanup-disposition.json')
    if proof['kind']!='post_exit_exact_identity_check' or proof['evidence']!=[binding(p) for p in paths]:
        raise RuntimeError('cleanup disposition does not bind original evidence')
    if proof['verifier']!=binding(__file__) or proof['identities']!=[list(v) for v in sorted(owned)]:
        raise RuntimeError('cleanup disposition source/identity mismatch')
    if proof['required_cpu_readmission']!='gpu-opt-cleanup-readmission-v1':raise RuntimeError('readmission requirement changed')
    if any(live(pid,start) for pid,start in owned):raise RuntimeError('an exact owned identity is still present')
    return proof


def record(identity):
    reservation=BASE/'resources'/(identity+'.reservation.json')
    prefix,paths,owned=inputs(reservation)
    if any(live(pid,start) for pid,start in owned):raise RuntimeError('owned cleanup is still incomplete')
    proof=dict(schema=1,kind='post_exit_exact_identity_check',evidence=[binding(p) for p in paths],
        verifier=binding(__file__),identities=[list(v) for v in sorted(owned)],observed_ns=time.monotonic_ns(),
        original_receipts_unchanged=True,original_failed_full_charge_retained=True,
        required_cpu_readmission='gpu-opt-cleanup-readmission-v1')
    put(str(prefix)+'.cleanup-disposition.json',proof)
    verify(reservation)
    print(json.dumps(dict(status='subsequent_cleanup_proved',identities=len(owned),original_failure_retained=True)))


def require_cpu_readmission(base=BASE):
    for reservation in (base/'resources').glob('*.reservation.json'):
        receipt=Path(str(reservation).replace('.reservation.','.settlement.'))
        if not receipt.exists() or read(receipt)['cleanup_empty']:continue
        proof=verify(reservation);name=proof['required_cpu_readmission']
        path=base/'resources'/(name+'.settlement.json')
        if not path.exists():raise RuntimeError('fresh CPU cleanup readmission required before GPU work')
        result=read(path)
        if result['status']!='passed' or not result['cleanup_empty'] or result['overrun']:
            raise RuntimeError('cleanup CPU readmission did not pass')
        request=read(base/'resources'/(name+'.reservation.json'))
        sources={item['path']:item for item in request['sources']}
        for source in [ROOT/'tools/lp_sp_pricing_budget.py',Path(__file__),ROOT/'tests/integration/test_lp_sp_pricing_cleanup.py']:
            item=binding(source);previous=sources.get(item['path'])
            if previous is None or any(previous[k]!=item[k] for k in ['bytes','sha256']):
                raise RuntimeError('cleanup CPU readmission source changed')


if __name__=='__main__':record(sys.argv[1])
