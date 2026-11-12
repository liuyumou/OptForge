"""Preregistered v6/v7 kernel comparison; exact state equality is mandatory."""
import argparse,json,statistics,math
from pathlib import Path
from lp_fp4_integrate_common import put,ref,require
from lp_fp4_integrate_model import model,prepare,LANES
from lp_fp4_integrate_run import Service,BINARY

def compare(first,second,out):
 out=Path(out);out.mkdir(parents=True,exist_ok=False);rows=[]
 put(out/'manifest.json',dict(images=[ref(first),ref(second)],binary=ref(BINARY),families=['coupled-equality','irregular-tail-33','dense-rich-65'],lanes=LANES,repetitions=21,discard_first_for_timing=True,select_if_fp4_geomean_above=1.02,exact_endpoint_required=True))
 for family in ('coupled-equality','irregular-tail-33','dense-rich-65'):
  doc,d=model(family);path=out/(family+'.json');put(path,doc)
  for f,k in LANES:
   services=[Service(im,path,out/f'{family}-{f}-{k}-{j}.stderr') for j,im in enumerate((first,second))];times=[[],[]];generations=[0,0]
   try:
    for s in services:s.call('load',0,request=prepare(d,f,k,max_updates=10000))
    for rep in range(21):
     states=[None,None]
     for j in ([0,1] if rep%2==0 else [1,0]):
      s=services[j];r=s.call('step',generations[j],count=32,limit=1);e=s.call('export',generations[j]);states[j]=[e['raw'],e['codes'],e['exponents'],r['flags'],r['local_terms']];times[j].append(r['gpu_us']);s.call('restore',generations[j]);generations[j]+=1
     require(states[0]==states[1],f'changed arithmetic {family}/{f}/{k}/{rep}')
    ratio=statistics.median(times[0][1:])/statistics.median(times[1][1:]);rows.append(dict(family=family,lane=[f,k],gpu_us=times,ratio=ratio,exact=True))
   finally:
    for s in services:s.close()
 ratios=[r['ratio'] for r in rows if r['lane'][0]==4];gm=math.exp(statistics.mean(math.log(r) for r in ratios))
 put(out/'result.json',dict(rows=rows,fp4_geomean=gm,selected='v7' if gm>1.02 else 'v6'));print(json.dumps(dict(fp4_geomean=gm,selected='v7' if gm>1.02 else 'v6')))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--first',required=True);p.add_argument('--second',required=True);p.add_argument('--output',required=True);a=p.parse_args();compare(Path(a.first),Path(a.second),a.output)
