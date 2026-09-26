"""ADR-0026 category accounting and chained authority; old protocols stay unchanged."""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from lp_protocol import ROOT,NS,Ledger,checked_reference,file_hash,read_json,validate,write_json
CONFIG=ROOT/'benchmarks/configs/lp-copt-comparison-v1.json'

def protocol(path=CONFIG):
    value=validate('campaign',read_json(path))
    for key in ['budget_authority','previous_protocol','decision',*[]]:checked_reference(ROOT,value[key])
    for ref in value['manifests']:checked_reference(ROOT,ref)
    return value

class ComparisonLedger(Ledger):
    def __init__(self,directory,campaign_hash,value):
        super().__init__(directory,campaign_hash,value['phase_gpu_seconds'],cumulative_ns=value['cumulative_gpu_ns'])
        self.value=value
    def usage(self,category,resource='gpu'):
        prefix=self.value['id']+'-'+category+'-'
        return sum(e['charged_ns'] for e in self.events if e['resource']==resource and e['trial_id'].startswith(prefix))+sum(e['reserved_ns'] for e in self.pending().values() if e['resource']==resource and e['trial_id'].startswith(prefix))
    def reserve(self,trial_id,seconds,resource='gpu',phase='ablations'):
        category=next((c for c in self.value['categories'] if trial_id.startswith(self.value['id']+'-'+c+'-')),None)
        if category is None:raise ValueError('unknown COPT comparison category')
        rule=self.value['categories'][category]
        if phase!=rule['phase']:raise ValueError('comparison category/phase mismatch')
        amount=round(seconds*NS)
        total=sum(self.usage(c,resource) for c in self.value['categories'])
        if resource=='gpu' and (self.usage(category)+amount>rule['seconds']*NS or total+amount>self.value['combined_cap_seconds']*NS):
            raise ValueError('comparison budget exhausted: '+category)
        if resource=='cpu' and total+amount>self.value['cpu_cap_seconds']*NS:raise ValueError('CPU study budget exhausted')
        return super().reserve(trial_id,seconds,resource,phase)

def ledger_for(value,root=ROOT):
    authority=checked_reference(root,value['budget_authority']);base=read_json(authority)
    parent=read_json(checked_reference(root,value['previous_protocol']));checked_reference(root,value['decision'])
    checked_reference(root,parent['decision'])
    previous=read_json(checked_reference(root,parent['previous_protocol']))
    checked_reference(root,previous['decision'])
    prior_source=read_json(checked_reference(root,previous['source_campaign']))
    if parent['budget_authority']!=value['budget_authority'] or prior_source['budget_authority']!=value['budget_authority']:
        raise ValueError('comparison authority chain differs')
    if previous['cumulative_ceiling_ns']!=prior_source['cumulative_gpu_ns']+previous['additional_gpu_seconds']*NS:
        raise ValueError('invalid throughput authority')
    if parent['cumulative_gpu_ns']!=previous['cumulative_ceiling_ns']+parent['additional_gpu_seconds']*NS:
        raise ValueError('invalid adaptive authority')
    if value['cumulative_gpu_ns']!=parent['cumulative_gpu_ns']+value['additional_gpu_seconds']*NS:
        raise ValueError('comparison cumulative authority differs')
    if value['phase_gpu_seconds']!=base['phase_gpu_seconds'] or value['total_gpu_seconds']!=base['total_gpu_seconds']:
        raise ValueError('campaign/phase caps changed')
    phases=dict(timing='ablations',profile='repeatability',trace='baseline',accept='repeatability')
    if {k:v['phase'] for k,v in value['categories'].items()}!=phases:raise ValueError('category phase authority differs')
    directory=root/'artifacts/lp-campaign-ledgers'/base['id']
    data=(directory/'ledger.jsonl').read_bytes();prefix=b''.join(data.splitlines(keepends=True)[:value['prior_events']])
    if len(prefix.splitlines())!=value['prior_events'] or not prefix.endswith(b'\n') or hashlib.sha256(prefix).hexdigest()!=value['prior_ledger_sha256']:
        raise ValueError('comparison historical prefix changed')
    if sum(json.loads(line)['charged_ns'] for line in prefix.splitlines() if json.loads(line)['resource']=='gpu')!=value['prior_gpu_ns']:
        raise ValueError('comparison prior consumption differs')
    if read_json(directory/'output.json')!=dict(campaign_sha256=file_hash(authority),output_path=str(root/'artifacts/gpup-baseline-v1')):
        raise ValueError('original output binding changed')
    return ComparisonLedger(directory,file_hash(authority),value)

def receipt(ledger):
    return dict(categories_ns={c:ledger.usage(c) for c in ledger.value['categories']},cpu_ns=sum(ledger.usage(c,'cpu') for c in ledger.value['categories']),
                cumulative_ns=ledger.totals(),ledger_sha256=file_hash(ledger.path),events=len(ledger.events))

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--id',required=True);p.add_argument('--seconds',type=int,required=True);p.add_argument('command',nargs=argparse.REMAINDER);a=p.parse_args()
    value=protocol();command=a.command[1:] if a.command[:1]==['--'] else a.command
    if not command or a.seconds<=0:raise ValueError('positive duration and command required')
    from benchmark_lp import source_identity
    gate=read_json(ROOT/'target/lp-native-gate.json')
    if not gate.get('native') or gate['source_tree_sha256']!=source_identity():raise ValueError('exact-source full native gate required')
    directory=ROOT/value['acceptance_output'];key=value['id']+'-accept-'+a.id
    with ledger_for(value) as ledger:
        if key in ledger.attempted():raise ValueError('acceptance already attempted')
        directory.mkdir(parents=True,exist_ok=True)
        request=dict(schema_version=2,gpu_admission_seconds=3,command=command,directory=str(directory),prefix=key,solve_seconds=a.seconds,cleanup_seconds=2,host_rss_bytes=8589934592,poll_ms=10,output_bytes=33554432)
        path=directory/(key+'.request.json')
        if path.exists():raise ValueError('existing acceptance request')
        write_json(path,request);reservation=ledger.reserve(key,a.seconds+6,phase='repeatability')
        worker=subprocess.Popen(['bash',str(ROOT/'tools/gpu_job.sh'),value['device'],'--lp-study-request',str(path)],pass_fds=(ledger.lock.fileno(),))
        interrupted=False
        try:worker.wait(timeout=a.seconds+310)
        except (subprocess.TimeoutExpired,KeyboardInterrupt):
            interrupted=True;worker.terminate()
            try:worker.wait(timeout=3)
            except subprocess.TimeoutExpired:worker.kill();worker.wait()
        report=directory/(key+'.worker.json');result=read_json(report) if report.exists() else None
        ledger.settle(reservation,result['leased_ns'] if result else reservation['reserved_ns'])
        write_json(directory/'budget.json',receipt(ledger));print(result,flush=True)
        if interrupted or not result or worker.returncode or result['reason']!='completed' or result['returncode']!=0 or result['leased_ns']>reservation['reserved_ns']:raise SystemExit(1)
if __name__=='__main__':main()
