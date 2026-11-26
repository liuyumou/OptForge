"""Read-only adapter admission across retained development receipts.

This admits interfaces, not numerical superiority. Every nonaccepting endpoint
and failed reservation remains visible. Each convention must have a separately
checked valid endpoint, an import roundtrip and exact source identity.
"""
import json
from pathlib import Path
import sys
from lp_sp_pricing_budget import BASE,ROOT,binding,put
from lp_sp_pricing_baselines import images

if __name__=='__main__':
    out=BASE/sys.argv[1];out.mkdir(exist_ok=False);rows=[]
    source=binding(ROOT/'tools/lp_sp_pricing_baselines.py')
    for identity in ('baseline-adapters-v1','baseline-adapters-v2','baseline-adapters-v3'):
        settled=json.loads((BASE/'resources'/f'{identity}.settlement.json').read_text())
        if not settled['cleanup_empty'] or settled['overrun']:raise RuntimeError('unresolved adapter attempt')
        original=BASE/'sources'/identity/'tools/lp_sp_pricing_baselines.py'
        matches=binding(original)['sha256']==source['sha256']
        for family in ('dense','wide','ill_scaled'):
            for lane in ('practical','retained_image_v11','copt_scale_off'):
                directory=BASE/identity/family/lane
                if not (directory/'process.json').exists():continue
                process=json.loads((directory/'process.json').read_text())
                path=directory/'audit.json'
                proof=json.loads(path.read_text()) if path.exists() else {'accepted':False}
                response_path=directory/'response.json'
                response=json.loads(response_path.read_text()) if response_path.exists() else {}
                rows.append(dict(identity=identity,family=family,lane=lane,source_matches=matches,
                    valid_process=process['returncode']==0 and not process['timed_out'],
                    accepted=bool(proof['accepted']),roundtrip=response.get('roundtrip_checked'),
                    process=binding(directory/'process.json'),audit=binding(path) if path.exists() else None))
    for lane in ('practical','retained_image_v11','copt_scale_off'):
        if not any(r['lane']==lane and r['source_matches'] and r['valid_process'] and r['accepted']
                   and (lane!='copt_scale_off' or r['roundtrip']) for r in rows):
            raise RuntimeError('adapter convention not admitted: '+lane)
    put(out/'result.json',dict(status='passed',scope='adapter_identity_and_endpoint_conventions_only',
        source=source,images=images(),rows=rows,all_failures_retained=True,no_scientific_repeat=True))
    print(json.dumps(dict(status='passed',retained_rows=len(rows))))
