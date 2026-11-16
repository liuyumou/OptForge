"""Final source, lifecycle, historical-byte and portable-evidence acceptance."""
import argparse
import ast
from pathlib import Path
import subprocess
from lp_general_common import BASE,ROOT,load,put,ref,require
from lp_general_budget import accounting


def validate(identity,admission,native,portable,results):
    a=load(BASE/(admission+'.json'));require(a['status']=='passed','device admission')
    for k in ['binary','image']:require(ref(ROOT/a[k]['path'])==a[k],'admitted artifact changed')
    source_count=0
    for r in a['sources']:
        p=r['path'].split(admission+'-sources/',1)[1]
        require(ref(ROOT/p)['sha256']==r['sha256'],'numerical source changed '+p);source_count+=1
    require(ref(ROOT/'research/lp-general-lowbit/target/release/lp-general-lowbit')['sha256']==a['binary']['sha256'],'working binary differs')
    np=BASE/'resources'/(native+'.settlement.json');require(load(np)['status']=='passed','full native gate')
    for p in sorted((ROOT/'crates').rglob('*.rs')):require(p.read_bytes()==(BASE/'sources'/native/p.relative_to(ROOT)).read_bytes(),'root numerical source changed')
    for p in (ROOT/'tools').glob('lp_general_fast*.py'):ast.parse(p.read_text())
    receipts=[];failures=[]
    for p in sorted((BASE/'resources').glob('fast-*.reservation.json')):
        if p.name==identity+'.reservation.json':continue
        sp=p.with_name(p.name.replace('.reservation.json','.settlement.json'));require(sp.exists(),'unfinished job '+p.name)
        s=load(sp);rr=ROOT/s['resource']['path'];require(ref(rr)==s['resource'],'resource byte binding');r=load(rr)
        require(r['guardian_cleanup']['empty'] and r['result']['cleanup']['empty'],'incomplete cleanup')
        require(not s['overrun'],'resource overrun');receipts.append(ref(sp))
        if s['status']!='passed':
            reservation=load(p)
            require(s['cpu_ns']>=reservation['cpu_ns'] and s['gpu_ns']>=reservation['gpu_ns'],'failed reservation undercharged')
            failures.append(dict(settlement=ref(sp),cpu_ns=s['cpu_ns'],gpu_ns=s['gpu_ns'],reason=r['result']['reason']))
    replay=BASE/'portable'/portable/'replay.json';rp=load(replay);require(rp['status']=='passed','portable replay')
    archive=load(BASE/'portable'/portable/'receipt.json')
    historical=[]
    for name in ['AGENTS.md','docs/benchmarks/lp-general-lowbit.md','research/lp-general-lowbit/README.md']:
        before=subprocess.check_output(['git','show','HEAD:'+name],cwd=ROOT)
        after=(ROOT/name).read_bytes();require(before in after,'historical text changed '+name);historical.append(name)
    for name in ['docs/benchmarks/lp-general-tensor.md','docs/benchmarks/lp-general-tensor-results.json','docs/benchmarks/lp-general-tensor-validation.json','docs/benchmarks/lp-general-tensor-diagnosis-results.json','docs/benchmarks/lp-general-tensor-diagnosis-validation.json']:
        require((ROOT/name).read_bytes()==subprocess.check_output(['git','show','HEAD:'+name],cwd=ROOT),'historical record changed '+name);historical.append(name)
    result=load(results);require(all(c['retained']+len(c['missing'])==c['planned'] for c in result['campaigns']),'coverage ledger')
    cpu,gpu=accounting()
    put(BASE/(identity+'.json'),dict(status='passed',admission=ref(BASE/(admission+'.json')),native=ref(np),numerical_sources_exact=source_count,
        receipts=receipts,failed_attempts=failures,failed_cpu_ns=sum(f['cpu_ns'] for f in failures),failed_gpu_ns=sum(f['gpu_ns'] for f in failures),
        historical_text=historical,prior_scientific_files_verified=archive['prior_scientific_files_verified'],prior_diagnostic_files_verified=archive['prior_diagnostic_files_verified'],portable=ref(replay),portable_result=rp['result'],
        archive_logical_bytes=archive['logical_bytes'],archive_unique_bytes=archive['unique_bytes'],archive_compressed_bytes=archive['compressed_bytes'],
        results=ref(results),cleanup_empty=True,allocation_status='open',checkpoint_including_active_reservation=dict(cpu_ns=sum(cpu.values()),gpu_ns=sum(gpu.values())),
        claim='Delivery acceptance only; no broad superiority, confirmation, public default or publication.'))
    print(dict(status='passed',numerical_sources=source_count,resources=len(receipts),failed=len(failures)),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--id',required=True);p.add_argument('--admission',required=True);p.add_argument('--native',required=True);p.add_argument('--portable',required=True);p.add_argument('--results',type=Path,required=True);a=p.parse_args();validate(a.id,a.admission,a.native,a.portable,a.results)
