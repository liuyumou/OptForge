"""Bind lifecycle costs to original responses and retain every unfavorable pair."""
from collections import defaultdict
from pathlib import Path
from lp_checker2_common import BASE,ROOT,load,put,ref,require


def run():
    frozen=load(BASE/'freeze.json');analysis=load(BASE/'analysis.json');models=load(ROOT/frozen['models']['path'])
    rows={};checked=physical=0
    for cell in frozen['cells']:
        path=BASE/'confirmation'/f"b{cell['block']:02d}"/(cell['id']+'.session.json')
        row=load(path);parts=defaultdict(int,setup=row['setup_ns'],teardown=row['teardown_ns'])
        for index,record in enumerate(row['records']):
            response_path=ROOT/record['result']['path'];require(ref(response_path)==record['result'],'response bytes changed')
            response=load(response_path)
            require(record['costs_ns']==response['costs_ns'] and record['physical']==response['physical'] and record['logical']==response['logical'] and record['gpu_us']==response['gpu_us'],'lifecycle record differs from original response')
            require(record['complete_ns']>=response['solve_ns']==sum(response['costs_ns'].values()),'solve time partition differs')
            require(response['tier']==cell['tier'] and response['lane']==cell['lane'] and response['model_sha256']==models['groups'][cell['family']][index%4]['sha256'],'cell/model binding differs')
            require(response['image_sha256']==frozen['image']['sha256'] and response['checker_binary_sha256']==frozen['binaries'][cell['variant']]['sha256'],'executable/image binding differs')
            require(response['certified'] and response['certificate']['accepted'] and response['physical']==sum(response['attempted'].values()),'certificate/work differs')
            for key,value in response['costs_ns'].items():parts[key]+=value
            checked+=1;physical+=response['physical']
        parts['outer']=row['complete_session_ns']-sum(parts.values());require(parts['outer']>=0,'overlapping cost partitions')
        rows[cell['id']]=dict(cell=cell,session=ref(path),total_ns=row['complete_session_ns'],parts_ns=dict(parts))
    pairs=[]
    for key,row in rows.items():
        if row['cell']['variant']!='baseline':continue
        candidate=rows[key.removesuffix('baseline')+'candidate']
        require(row['parts_ns'].keys()==candidate['parts_ns'].keys(),'cost names differ')
        savings={k:row['parts_ns'][k]-candidate['parts_ns'][k] for k in row['parts_ns']}
        total=row['total_ns']-candidate['total_ns'];require(sum(savings.values())==total,'paired costs do not sum')
        pairs.append(dict(block=row['cell']['block'],family=row['cell']['family'],tier=row['cell']['tier'],lane=row['cell']['lane'],
                          ratio=row['total_ns']/candidate['total_ns'],saved_ns=total,savings_ns=savings,baseline=row,candidate=candidate))
    unfavorable=sorted((r for r in pairs if r['saved_ns']<0),key=lambda r:r['ratio'])
    require(checked==analysis['complete_solves']==16384 and len(pairs)==256,'complete diagnostic coverage')
    result=dict(status='passed',responses=checked,physical_updates=physical,complete_pairs=len(pairs),unfavorable_pairs=unfavorable,
                all_paired_costs=pairs,analysis=ref(BASE/'analysis.json'),source=ref(Path(__file__).resolve()),
                limits=['cost locations do not establish the underlying scheduler/cache/device cause','GPU events are nested within iteration and excluded from additive host partitions','no observations are censored and no gate is changed'])
    put(BASE/'diagnosis-final.json',result);put(ROOT/'docs/benchmarks/data/checker2-diagnosis-v1.json',result)
    print(dict(responses=checked,physical_updates=physical,unfavorable_pairs=len(unfavorable)),flush=True)
    for r in unfavorable:
        print({k:r[k] for k in ['block','family','tier','lane','ratio','saved_ns','savings_ns']},flush=True)

if __name__=='__main__':run()
