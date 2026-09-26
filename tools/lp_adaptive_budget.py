"""ADR-0025 authority chain and bounded phase accounting; never reset historical ledgers."""
import argparse
import hashlib
import subprocess
from pathlib import Path
from lp_protocol import ROOT, Ledger, NS, checked_reference, file_hash, read_json, validate, write_json

CONFIG=ROOT/'benchmarks/configs/lp-adaptive-v1.json'


def protocol(path=CONFIG):
    value=validate('campaign',read_json(path))
    authority=checked_reference(ROOT,value['budget_authority'])
    base=read_json(authority)
    for key in ['manifests','partition','solve','lp_settings','order_seed','repetitions','profile_repetitions','analysis','limits','device','total_gpu_seconds','phase_gpu_seconds']:
        if value[key]!=base[key]:raise ValueError('adaptive changed frozen '+key)
    return value


class AdaptiveLedger(Ledger):
    """Admission enforces phase, slice category and combined caps for every job."""
    def __init__(self,directory,campaign_hash,value):
        super().__init__(directory,campaign_hash,value['phase_gpu_seconds'],cumulative_ns=value['cumulative_gpu_ns'])
        self.value=value

    def usage(self,category):
        prefix=self.value['id']+'-'+category+'-'
        return sum(e['charged_ns'] for e in self.events if e['resource']=='gpu' and e['trial_id'].startswith(prefix))+sum(e['reserved_ns'] for e in self.pending().values() if e['resource']=='gpu' and e['trial_id'].startswith(prefix))

    def reserve(self,trial_id,seconds,resource='gpu',phase='ablations'):
        category=next((c for c in ['study','accept'] if trial_id.startswith(self.value['id']+'-'+c+'-')),None)
        if category is None:raise ValueError('unknown adaptive job identity')
        expected=self.value['study_phase' if category=='study' else 'acceptance_phase']
        if phase!=expected:raise ValueError('adaptive category/phase mismatch')
        cap=self.value['study_cap_seconds' if category=='study' else 'acceptance_cap_seconds']*NS
        if resource=='gpu' and (self.usage(category)+round(seconds*NS)>cap or self.usage('study')+self.usage('accept')+round(seconds*NS)>self.value['combined_cap_seconds']*NS):
            raise ValueError('GPUP-6 budget exhausted; incomplete evidence retained')
        return super().reserve(trial_id,seconds,resource,phase)


def ledger_for(value,root=ROOT):
    """Revalidate chained authority and immutable prefix before opening recovery."""
    authority=checked_reference(root,value['budget_authority']);base=read_json(authority)
    previous=read_json(checked_reference(root,value['previous_protocol']))
    checked_reference(root,value['decision'])
    prior_source=read_json(checked_reference(root,previous['source_campaign']))
    checked_reference(root,previous['decision'])
    if prior_source['budget_authority']!=value['budget_authority']:
        raise ValueError('changed campaign authority')
    if previous['cumulative_ceiling_ns']!=prior_source['cumulative_gpu_ns']+previous['additional_gpu_seconds']*NS:
        raise ValueError('invalid previous ceiling authority')
    if value['cumulative_gpu_ns']!=previous['cumulative_ceiling_ns']+value['additional_gpu_seconds']*NS:
        raise ValueError('adaptive cumulative ceiling differs from authority')
    if value['phase_gpu_seconds']!=base['phase_gpu_seconds'] or value['total_gpu_seconds']!=base['total_gpu_seconds']:
        raise ValueError('adaptive campaign/phase caps differ')
    if value['study_phase']!='ablations' or value['acceptance_phase']!='repeatability':
        raise ValueError('adaptive phase authority differs')
    directory=root/'artifacts/lp-campaign-ledgers'/base['id']
    data=(directory/'ledger.jsonl').read_bytes()
    prefix=b''.join(data.splitlines(keepends=True)[:value['prior_events']])
    if len(prefix.splitlines())!=value['prior_events'] or not prefix.endswith(b'\n') or hashlib.sha256(prefix).hexdigest()!=value['prior_ledger_sha256']:
        raise ValueError('historical ledger prefix changed')
    events=[__import__('json').loads(line) for line in prefix.splitlines()]
    if sum(e['charged_ns'] for e in events if e['resource']=='gpu')!=value['prior_gpu_ns']:
        raise ValueError('historical GPU consumption differs')
    if read_json(directory/'output.json')!=dict(campaign_sha256=file_hash(authority),output_path=str(root/'artifacts/gpup-baseline-v1')):
        raise ValueError('original output binding changed')
    return AdaptiveLedger(directory,file_hash(authority),value)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--id',required=True);p.add_argument('--seconds',type=int,required=True);p.add_argument('command',nargs=argparse.REMAINDER);a=p.parse_args()
    value=protocol();command=a.command[1:] if a.command[:1]==['--'] else a.command
    if not command or a.seconds<=0:raise ValueError('positive deadline and command required')
    from benchmark_lp import source_identity
    receipt=read_json(ROOT/'target/lp-native-gate.json')
    if not receipt.get('native') or receipt['source_tree_sha256']!=source_identity():raise ValueError('exact-source full native gate required')
    directory=ROOT/value['acceptance_output'];key=value['id']+'-accept-'+a.id
    with ledger_for(value) as ledger:
        if key in ledger.attempted():raise ValueError('acceptance already attempted')
        directory.mkdir(parents=True,exist_ok=True)
        request=dict(schema_version=2,gpu_admission_seconds=3,command=command,directory=str(directory),prefix=key,solve_seconds=a.seconds,cleanup_seconds=2,host_rss_bytes=8589934592,poll_ms=10,output_bytes=33554432)
        path=directory/(key+'.request.json')
        if path.exists():raise ValueError('refusing existing acceptance request')
        write_json(path,request)
        reservation=ledger.reserve(key,a.seconds+6,phase=value['acceptance_phase'])
        worker=subprocess.Popen(['bash',str(ROOT/'tools/gpu_job.sh'),value['device'],'--lp-study-request',str(path)],pass_fds=(ledger.lock.fileno(),))
        interrupted=False
        try:worker.wait(timeout=a.seconds+310)
        except (subprocess.TimeoutExpired,KeyboardInterrupt):
            interrupted=True;worker.terminate()
            try:worker.wait(timeout=3)
            except subprocess.TimeoutExpired:worker.kill();worker.wait()
        report=directory/(key+'.worker.json');result=read_json(report) if report.exists() else None
        ledger.settle(reservation,result['leased_ns'] if result else reservation['reserved_ns'])
        write_json(directory/'budget.json',dict(study_ns=ledger.usage('study'),acceptance_ns=ledger.usage('accept'),cumulative_ns=ledger.totals(),ledger_sha256=file_hash(ledger.path)))
        print(result,flush=True)
        if interrupted or not result or worker.returncode or result['leased_ns']>reservation['reserved_ns'] or result['reason']!='completed' or result['returncode']!=0:raise SystemExit(1)

if __name__=='__main__':main()
