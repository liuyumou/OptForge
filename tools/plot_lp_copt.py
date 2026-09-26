"""Standalone plots of independently verified ADR-0026 observations."""
import argparse,csv,json,statistics
from collections import defaultdict
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
matplotlib.rcParams['svg.hashsalt']='gpup-copt-comparison-v1'
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection

GROUPS=['input_representation','preparation','device_setup','transfers','iteration_control','recovery','certification','copt_setup','native_solve','output_teardown','other_host','unexplained_process']
LABELS=['Input / representation','Preparation','Device setup','Transfers (host wall)','Iteration / control','Recovery','Certification','COPT setup','Native solve (opaque)','Output / teardown','Other host','Startup / teardown residual']
COLORS=['#0072B2','#E69F00','#009E73','#56B4E9','#CC79A7','#D55E00','#332288','#88CCEE','#AA4499','#999933','#BBBBBB','#E5E5E5']
ALIASES={'tuned-fp64':'Tuned FP64','copt-cpu-default':'COPT CPU default','copt-cpu-pdlp':'COPT CPU PDLP','copt-gpu-pdlp':'COPT GPU PDLP','adaptive-direct-accumulation_fp32-a32-strict-sticky':'Sticky accumulation','adaptive-gradual-working_fp32-a32-strict-demote':'Gradual demotion'}

def short(name):return name.removeprefix('gpup-development-').removeprefix('gpup-extension-')

def main():
 p=argparse.ArgumentParser();p.add_argument('--report',type=Path,required=True);p.add_argument('--directory',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 r=json.loads(a.report.read_text());v=json.loads((a.directory/'campaign.json').read_text());a.output.mkdir(parents=True,exist_ok=True)
 configs=v['profile_configurations'];models=v['profile_instances'];costs=[c for c in r['costs'] if c['kind']=='profile' and c['process']=='solve' and not any('unclosed' in u or 'scope closed' in u for u in c['unavailable'])]
 groups=defaultdict(list)
 for c in costs:groups[c['instance'],c['config']].append(c)
 summaries=[]
 for instance in models:
  for config in [c['id'] for c in v['configurations']]:
   rows=groups[instance,config]
   if not rows:continue
   wall=statistics.mean(c['worker_elapsed_ns'] for c in rows)
   phase={g:statistics.mean(c['groups_ns'].get(g,0) for c in rows) for g in GROUPS[:-1]}
   phase['unexplained_process']=wall-sum(phase.values())
   if phase['unexplained_process']<0:raise ValueError('profile exceeds worker wall')
   summaries.append(dict(instance=instance,config=config,n=len(rows),partial_outcomes=sum(c['partial'] for c in rows),worker_mean_ns=wall,**phase))
 fields=['instance','config','n','partial_outcomes','worker_mean_ns',*GROUPS]
 with (a.output/'copt-components.csv').open('w',newline='') as f:
  writer=csv.DictWriter(f,lineterminator='\n',fieldnames=fields);writer.writeheader();writer.writerows(summaries)
 for larger in [False,True]:
  selected=[i for i in models if ('extension' in i)==larger];fig,axes=plt.subplots(2,2,figsize=(15,10),squeeze=False)
  scale=1e9 if larger else 1e6
  for ax,instance in zip(axes.flat,selected):
   for index,config in enumerate(configs):
    found=next((s for s in summaries if (s['instance'],s['config'])==(instance,config)),None)
    if found is None:ax.text(0,index,'unavailable',va='center');continue
    left=0
    for group,color in zip(GROUPS,COLORS):
     width=found[group]/scale;ax.barh(index,width,left=left,color=color,height=.72);left+=width
    ax.text(left,index,' n='+str(found['n']),va='center',fontsize=8)
   ax.set_yticks(range(len(configs)),[ALIASES.get(c,c) for c in configs],fontsize=8);ax.set_ylim(len(configs)-.4,-.6);ax.set_title(short(instance));ax.set_xlabel('Mean instrumented process wall ('+('seconds' if larger else 'ms')+')');ax.grid(axis='x',alpha=.15)
  fig.legend([plt.Rectangle((0,0),1,1,color=c) for c in COLORS],LABELS,loc='lower center',ncol=4,frameon=False,fontsize=9)
  fig.suptitle('Disjoint host wall costs; GPU activity is reported separately',fontsize=14);fig.tight_layout(rect=[0,.11,1,.95]);fig.savefig(a.output/('copt-components-'+('large' if larger else 'small')+'.svg'),metadata={'Date':None});fig.savefig(a.output/('copt-components-'+('large' if larger else 'small')+'.png'),dpi=120);plt.close(fig)
 # A separate activity timeline; zero is the first observed device activity,
 # not process launch. Kernel/copy intervals are shown on their actual streams.
 traces=[t for t in r['traces'] if 'data' in t]
 for instance in v['trace_instances']:
  selected=[t for t in traces if t['instance']==instance];fig,axes=plt.subplots(max(1,len(selected)),1,figsize=(14,max(3,len(selected)*2.6)),squeeze=False)
  for ax,t in zip(axes.flat,selected):
   timeline=json.loads((a.directory/t['timeline']['path']).read_text());streams=sorted({str(e['stream']) for e in timeline});ys={s:i for i,s in enumerate(streams)}
   for kind,color in [('graph','#6a3d9a'),('kernel','#0072B2'),('copy','#D55E00'),('fill','#E69F00')]:
    segments=[[(e['start_ns']/1e6,ys[str(e['stream'])]),(e['end_ns']/1e6,ys[str(e['stream'])])] for e in timeline if e['kind']==kind]
    ax.add_collection(LineCollection(segments,colors=color,linewidths=7 if kind=='graph' else 5,alpha=.35 if kind=='graph' else 1,label=kind,rasterized=True));ax.autoscale_view()
   ax.set_yticks(range(len(streams)),['stream '+s for s in streams]);ax.set_title(ALIASES.get(t['config'],t['config'])+' — '+t['status'],fontsize=10);ax.set_xlabel('ms after first observed device activity');ax.margins(y=.4);ax.grid(axis='x',alpha=.15)
  if not selected:axes[0,0].text(.5,.5,'No decoded activity',ha='center');axes[0,0].set_axis_off()
  fig.suptitle(short(instance)+' CUDA observations — blue kernels, orange copies, yellow fills, purple graph envelopes',fontsize=12);fig.tight_layout(rect=[0,0,1,.97]);fig.savefig(a.output/('copt-timeline-'+short(instance)+'.svg'),metadata={'Date':None});plt.close(fig)
 # Complete coverage and paired intervals, including empty cells.
 with (a.output/'copt-latency.csv').open('w',newline='') as f:
  fields=['instance','config','planned','attempted','certified','initial_certified','median_ns','outcomes'];w=csv.DictWriter(f,lineterminator='\n',fieldnames=fields);w.writeheader();w.writerows({**row,'outcomes':json.dumps(row['outcomes'],sort_keys=True)} for row in r['rows'])
 with (a.output/'copt-ratios.csv').open('w',newline='') as f:
  fields=['instance','reference','candidate','paired_repetitions','ratio','ci95_low','ci95_high'];w=csv.DictWriter(f,lineterminator='\n',fieldnames=fields);w.writeheader()
  for row in r['ratios']:
   s=row['statistics'] or {};ci=s.get('ci95',[None,None]);w.writerow({k:row[k] for k in ['instance','reference','candidate']}|dict(paired_repetitions=s.get('paired_repetitions',0),ratio=s.get('ratio'),ci95_low=ci[0],ci95_high=ci[1]))
 with (a.output/'copt-per-unit.csv').open('w',newline='') as f:
  fields=['trial','instance','config','kind','unit','count','phase_ns','ns_per_unit','paths'];w=csv.DictWriter(f,lineterminator='\n',fieldnames=fields);w.writeheader()
  for row in r['per_unit']:
   for metric in row['metrics']:w.writerow({k:row[k] for k in ['trial','instance','config','kind']}|metric|{'paths':json.dumps(metric['paths'])})
 for path in a.output.glob('*.svg'):
  path.write_text('\n'.join(line.rstrip() for line in path.read_text().splitlines())+'\n')
 print('Wrote phase tables, paired latency tables, per-unit costs and separate SVG activity timelines.')
if __name__=='__main__':main()
