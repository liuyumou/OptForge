"""Reproducible ADR-0032 tables, figures and immutable source/resource catalog."""
import csv
import gzip
import hashlib
import subprocess
from lp_convergence_budget import protocol
from report_lp_convergence import check_measured_source
from lp_protocol import ROOT,file_hash,read_json,write_json

ALIASES={'tuned-fp64':'Tuned FP64','precision-fp64':'Precision FP64','accumulation-fp32':'Accumulation FP32','adaptive-fp64-a32':'Adaptive FP64',
         'adaptive-direct-accumulation_fp32-a32-strict-sticky':'Sticky recovery','adaptive-gradual-working_fp32-a32-strict-demote':'Gradual demotion',
         'copt-cpu-pdlp':'COPT CPU PDLP','copt-gpu-pdlp':'COPT GPU PDLP'}


def csv_rows(path,rows):
    if not rows:return
    fields=list(dict.fromkeys(k for r in rows for k in r))
    with path.open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=fields,lineterminator='\n');writer.writeheader();writer.writerows(rows)


def figures(report,output,value):
    import matplotlib
    matplotlib.use('Agg');matplotlib.rcParams['svg.hashsalt']=value['id']
    import matplotlib.pyplot as plt
    configs=[c['id'] for c in value['configurations'] if c['backend']=='cuda-lp-tuned']
    fig,axes=plt.subplots(1,2,figsize=(14,5))
    for ax,mode in zip(axes,['short200','short2000']):
        rows=[w for w in report['work'] if w['instance_id']=='gpup-extension-irregular-32768' and w['mode']==mode]
        for i,c in enumerate(configs):
            w=next((w for w in rows if w['configuration']==c),None)
            if w is None:ax.text(0,i,'unavailable',va='center');continue
            left=0
            for field,color in [('proposals','#0072B2'),('audits','#D55E00'),('probes','#E69F00')]:
                ax.barh(i,w[field],left=left,color=color);left+=w[field]
            ax.text(left+5,i,'logical '+str(w['logical'])+'\nreplay '+('unavailable' if w['replay'] is None else str(w['replay'])),fontsize=8,va='center')
        ax.set_yticks(range(len(configs)),[ALIASES[c] for c in configs]);ax.invert_yaxis();ax.set_title(mode.removeprefix('short')+' physical-update allowance');ax.set_xlabel('Actual charged updates');ax.set_xlim(0,int(mode.removeprefix('short'))*1.6)
    fig.suptitle('Irregular-32768: actual work mixtures; replay is a subset of proposals')
    fig.legend([plt.Rectangle((0,0),1,1,color=c) for c in ['#0072B2','#D55E00','#E69F00']],['Proposals','Reference audits','Demotion probes'],loc='lower center',ncol=3,frameon=False)
    fig.tight_layout(rect=[0,.06,1,.94]);fig.savefig(output/'convergence-work.svg',metadata={'Date':None});fig.savefig(output/'convergence-work.png',dpi=130);plt.close(fig)
    rows=[p for p in report['profiles'] if p['instance_id']=='gpup-extension-irregular-32768' and p['mode']=='profile']
    groups=sorted({g for p in rows for g in p['groups_ns']});colors=plt.get_cmap('tab20')
    fig,ax=plt.subplots(figsize=(13,7));configs=[c['id'] for c in value['configurations']]
    for i,c in enumerate(configs):
        p=next((p for p in rows if p['configuration']==c),None)
        if p is None:ax.text(0,i,'unavailable',va='center');continue
        left=0
        for j,g in enumerate(groups):
            width=p['groups_ns'].get(g,0)/1e9;ax.barh(i,width,left=left,color=colors(j));left+=width
        ax.text(left+.03,i,'certified' if p['certified'] else 'uncertified',fontsize=8,va='center')
    ax.set_yticks(range(len(configs)),[ALIASES[c] for c in configs]);ax.invert_yaxis();ax.set_xlabel('Instrumented fresh-process wall seconds')
    ax.set_title('Irregular-32768: disjoint host costs; device scopes include synchronization');ax.margins(x=.22)
    fig.legend([plt.Rectangle((0,0),1,1,color=colors(j)) for j in range(len(groups))],[g.replace('_',' ') for g in groups],loc='lower center',ncol=3,fontsize=8,frameon=False)
    fig.tight_layout(rect=[0,.22,1,1]);fig.savefig(output/'convergence-cost.svg',metadata={'Date':None});fig.savefig(output/'convergence-cost.png',dpi=130);plt.close(fig)
    for path in output.glob('convergence-*.svg'):
        path.write_text('\n'.join(line.rstrip() for line in path.read_text().splitlines())+'\n')


def main():
    value=protocol();source=ROOT/value['output'];output=ROOT/'docs/benchmarks/data/convergence';output.mkdir(parents=True,exist_ok=True)
    report=read_json(source/'report.json');measured=check_measured_source(source)
    old=subprocess.check_output(['git','ls-tree','-r','--name-only',value['source_revision']],cwd=ROOT,text=True).splitlines()
    preserved=[n for n in old if n.startswith(('crates/','cuda/','tools/','schemas/','benchmarks/','docs/decisions/')) or n in ['Cargo.toml','Cargo.lock']]
    for n in preserved:
        if (ROOT/n).read_bytes()!=subprocess.check_output(['git','show',value['source_revision']+':'+n],cwd=ROOT):raise ValueError('historical code/authority changed: '+n)
    ledger=(source/'ledger.jsonl').read_bytes();prefix=b''.join(ledger.splitlines(keepends=True)[:value['prior_events']])
    if hashlib.sha256(prefix).hexdigest()!=value['prior_ledger_sha256'] or file_hash(source/'ledger.jsonl')!=report['budget']['ledger_sha256']:raise ValueError('ledger prefix differs')
    write_json(output/'convergence-summary.json',{k:report[k] for k in ['id','planned','attempted','verified','certified_timings','certified_profiles','groups','ratios','equivalence','acceptance','budget','limitations']})
    write_json(output/'convergence-work.json',report['work']);write_json(output/'convergence-profiles.json',report['profiles'])
    csv_rows(output/'convergence-trials.csv',report['rows']);csv_rows(output/'convergence-amplification.csv',report['amplification'])
    flat=[{k:v for k,v in w.items() if k not in ['native','adaptive','precision','control','execution','assessment']} for w in report['work']]
    csv_rows(output/'convergence-work.csv',flat)
    (output/'convergence-analysis.json.gz').write_bytes(gzip.compress((source/'report.json').read_bytes(),mtime=0))
    review = read_json(output/'convergence-review-corrections.json') if (output/'convergence-review-corrections.json').exists() else {'files': []}
    write_json(output/'convergence-source-ledger-audit.json',dict(status='passed',measured_files=measured,preserved_files=preserved,review_corrections=review['files'],
               prior_events=value['prior_events'],prior_ledger_sha256=value['prior_ledger_sha256'],ledger_sha256=report['budget']['ledger_sha256'],events=len(ledger.splitlines())))
    cpu=[dict(path=str(p.relative_to(ROOT)),sha256=file_hash(p),**read_json(p)) for p in sorted((ROOT/value['acceptance_output']).glob('*.cpu.json'))]
    if sum(r['cpu_seconds'] for r in cpu)>value['cpu_cap_seconds']:raise ValueError('metered CPU cap exceeded')
    write_json(output/'convergence-resources.json',dict(gpu=report['budget'],cpu_seconds=sum(r['cpu_seconds'] for r in cpu),cpu_cap_seconds=value['cpu_cap_seconds'],cpu_receipts=cpu,
               note='Metered child CPU; editing/catalog overhead excluded. Ledger CPU reservations separately visible.'))
    catalog=[]
    for name in [value['output'],value['acceptance_output']]:
        for p in sorted((ROOT/name).rglob('*')):
            if p.is_file() and '__pycache__' not in p.parts:catalog.append(dict(path=str(p.relative_to(ROOT)),sha256=file_hash(p),bytes=p.stat().st_size))
    historical=[ROOT/'docs/benchmarks'/n for n in ['lp-copt-comparison.md','lp-adaptive-host-cost.md','lp-copt-adapter.md']]
    write_json(output/'convergence-provenance.json',dict(schema_version=1,source_report=dict(path=str((source/'report.json').relative_to(ROOT)),sha256=file_hash(source/'report.json')),
               artifacts=catalog,historical_context=[dict(path=str(p.relative_to(ROOT)),sha256=file_hash(p),role='separately labeled historical report; not fresh study data') for p in historical]))
    figures(report,output,value)
    print('Exported',len(catalog),'artifact references;',len(measured),'measured files audited and',len(preserved),'historical authority files unchanged')


if __name__=='__main__':main()
