"""Standalone scientific figure from the frozen strict-tier medians."""
from pathlib import Path
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from lp_fp4_accel_common import ROOT

r=json.loads((ROOT/'docs/benchmarks/data/fp4-accel-result-v1.json').read_text())
lanes=('native','nativefast','fp4x4','gridfp4x2')
labels=('Fused FP64','Parallel FP64','Fused FP4 ×4','Parallel FP4 ×2')
colors=('#8c8c8c','#2369bd','#cf7348','#178c78')
fig,axes=plt.subplots(1,2,figsize=(10,3.8),constrained_layout=True)
for ax,key,title in zip(axes,('gpu_ms','complete_ms'),('GPU stream elapsed','Complete prepared solve')):
    for j,(lane,label,color) in enumerate(zip(lanes,labels,colors)):
        vals=[next(x[key] for x in r['medians'] if x['lifecycle']=='prepared' and x['tier']=='certified-1e-9' and x['family']==f'dense-generic-{n}' and x['lane']==lane) for n in (128,256,512)]
        ax.bar(np.arange(3)+(j-1.5)*.19,vals,width=.18,label=label,color=color)
    ax.set_xticks(range(3),['128','256','512']);ax.set_xlabel('Dense model dimension');ax.set_ylabel('Milliseconds');ax.set_title(title);ax.spines[['top','right']].set_visible(False);ax.grid(axis='y',alpha=.18);ax.set_axisbelow(True)
axes[0].legend(frameon=False,fontsize=8,loc='upper left')
fig.suptitle('Original-model 1e−9 certificates · median of 5 trials',fontsize=12)
fig.savefig(ROOT/'docs/benchmarks/data/fp4-accel-strict-v1.png',dpi=170)
