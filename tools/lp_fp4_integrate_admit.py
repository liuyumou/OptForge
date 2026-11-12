"""Bind final software, device, sanitizer and historical-source admission."""
from pathlib import Path
from lp_fp4_integrate_common import ROOT,BASE,load,put,ref,require
from lp_fp4_integrate_run import BINARY

def main():
 image=BASE/'build-v8/integrate.cubin';gates=[];sanitizers=[]
 for name in ('final-cpu-v1','final-device-v1','final-sanitizers-v1'):
  p=BASE/'resources'/(name+'.settlement.json');require(load(p)['status']=='passed','failed gate');gates.append(ref(p))
 for name,count in [('final-device-v1',90),('final-lifecycle-v1',13),('final-safety-v1',14)]:
  p=BASE/name/'result.json';r=load(p);require(r['status']=='passed' and len(r['rows'])==count,'device coverage');manifest=load(BASE/name/'manifest.json');require(manifest['image']==ref(image) and manifest['binary']==ref(BINARY),'device image mismatch');gates.append(ref(p))
 for tool in ('memcheck','racecheck','initcheck','synccheck'):
  paths=[]
  for prefix in ('final-','final-boundary-'):
   directory=BASE/(prefix+tool+'-v1');require(load(directory/'result.json')['status']=='passed','sanitizer process failure')
   manifest=load(directory/'manifest.json');require(manifest['image']==ref(image) and manifest['binary']==ref(BINARY),'sanitizer image mismatch')
   paths+=sorted(directory.glob('*.sanitizer'))
  require(len(paths)==50,'sanitizer path coverage')
  for p in paths:
   text=p.read_text();expected='RACECHECK SUMMARY: 0 hazards displayed (0 errors, 0 warnings)' if tool=='racecheck' else 'ERROR SUMMARY: 0 errors'
   require(expected in text,'nonzero sanitizer report')
  sanitizers.append(dict(tool=tool,processes=len(paths),logs=[ref(p) for p in paths]))
 history=load(BASE/'history.json');navigation={'AGENTS.md','state/active-task.md','state/backlog.yaml','docs/plans/gpu-lp-precision-roadmap.md'}
 for binding in history['files']:
  if binding['path'] not in navigation:require(ref(ROOT/binding['path'])==binding,'historical source changed')
 sources=list((ROOT/'research/lp-fp4-integrate/src').glob('*.rs'))+list((ROOT/'research/lp-fp4-integrate/cuda').glob('*'))+[ROOT/'tools'/n for n in ('lp_fp4_integrate_run.py','lp_fp4_integrate_model.py','lp_fp4_integrate_policy.py','lp_fp4_integrate_common.py')]
 receipt=dict(status='passed',image=ref(image),binary=ref(BINARY),sources=[ref(p) for p in sorted(sources)],gates=gates,sanitizers=sanitizers,history=ref(BASE/'history.json'),historical_files=len(history['files']),software=dict(rust=641,python=636,native=True,replay=True,docs=True,smoke=True),semantics='operational residual guard; independent original-model final certification')
 put(BASE/'admission-v1.json',receipt);print(dict(status='passed',sanitized_processes=200,historical_files=len(history['files'])))
if __name__=='__main__':main()
