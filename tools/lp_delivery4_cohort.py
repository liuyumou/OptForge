"""Serial immutable whole-block reservations; stop at the first failed block."""
import argparse
from pathlib import Path
import sys
sys.path.insert(0,str(Path.cwd()/'tools'))
from lp_delivery4_common import BASE,load,require
from lp_delivery4_budget import run
p=argparse.ArgumentParser();p.add_argument('kind',choices=['profile','diagnostic','confirmation']);a=p.parse_args()
directory=BASE/(a.kind+'-v1')
initial=run(a.kind+"-freeze-v1","implementation",60,False,[sys.executable,"-B","tools/lp_delivery4_study.py","freeze",str(directory),"--kind",a.kind])
require(initial["status"]=="passed","manifest freeze failed")
manifest=load(directory/'manifest.json')
for block in range(manifest['blocks']):
    result=run(f'{a.kind}-block-{block:02d}-v1','confirmation' if a.kind=='confirmation' else 'diagnosis',90 if a.kind=='confirmation' else 70,True,
        [sys.executable,'-B','tools/lp_delivery4_study.py','block',str(directory),'--block',str(block)])
    print(dict(kind=a.kind,block=block,settlement=result),flush=True)
    require(result['status']=='passed','block failed; cohort will not retry')
final=run(a.kind+"-collect-v1","reporting",60,False,[sys.executable,"-B","tools/lp_delivery4_study.py","collect",str(directory)])
require(final["status"]=="passed","cohort collection failed")
