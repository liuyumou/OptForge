"""ADR-0021 shared-lease supervision; all new work uses the preserved campaign ledger."""
import argparse
import hashlib
import subprocess
from lp_protocol import ROOT, Ledger, NS, checked_reference, file_hash, read_json, write_json

PRIOR_NS=1467266874696
PRIOR_EVENTS=3288
PRIOR_HASH='b3ca2739b1108a552b0423606ddd0cd94a8ed2323da1506098fa0150ba42bfef'
OUTPUT=ROOT/'artifacts/gpup5b-v1'


def ledger_for():
    value=read_json(ROOT/'benchmarks/configs/lp-precision-v4.json')
    authority=checked_reference(ROOT,value['budget_authority'])
    directory=ROOT/'artifacts/lp-campaign-ledgers'/read_json(authority)['id']
    prefix=b''.join((directory/'ledger.jsonl').read_bytes().splitlines(keepends=True)[:PRIOR_EVENTS])
    if hashlib.sha256(prefix).hexdigest()!=PRIOR_HASH: raise ValueError('historical ledger prefix changed')
    if read_json(directory/'output.json')['output_path']!=str(ROOT/'artifacts/gpup-baseline-v1'): raise ValueError('original output binding changed')
    return Ledger(directory,file_hash(authority),value['phase_gpu_seconds'],cumulative_ns=value['cumulative_gpu_ns'])


def category_usage(ledger,category):
    return sum(e['charged_ns'] if e['kind']=='settle' else e['reserved_ns'] if e['reservation_id'] in ledger.pending() else 0
               for e in ledger.events if e['trial_id'].startswith('gpup5b-'+category+'-'))


def run(ledger,category,key,command,seconds,directory=OUTPUT):
    identity='gpup5b-'+category+'-'+key
    if identity in ledger.attempted(): raise ValueError('attempt already admitted')
    reserve=seconds+6
    cap=900 if category=='study' else 300
    if category_usage(ledger,category)+reserve*NS>cap*NS or ledger.totals()-PRIOR_NS+reserve*NS>1200*NS:
        raise ValueError('GPUP-5B budget exhausted; incomplete evidence retained')
    directory.mkdir(parents=True,exist_ok=True)
    request=dict(schema_version=2,gpu_admission_seconds=3,command=command,directory=str(directory),prefix=key,
                 solve_seconds=seconds,cleanup_seconds=2,host_rss_bytes=8589934592,poll_ms=10,output_bytes=33554432)
    path=directory/(key+'.supervisor.json')
    if path.exists(): raise ValueError('refusing existing GPU request')
    write_json(path,request)
    reservation=ledger.reserve(identity,reserve,phase='screening')
    worker=subprocess.Popen(['bash',str(ROOT/'tools/gpu_job.sh'),read_json(ROOT/'benchmarks/configs/lp-precision-v4.json')['device'],
                               '--lp-study-request',str(path)],pass_fds=(ledger.lock.fileno(),))
    interrupted=False
    try:
        worker.wait(timeout=seconds+310)
    except (subprocess.TimeoutExpired, KeyboardInterrupt):
        interrupted=True
        worker.terminate()
        try:worker.wait(timeout=3)
        except subprocess.TimeoutExpired:
            worker.kill();worker.wait()
    worker_path=directory/(key+'.worker.json')
    result=read_json(worker_path) if worker_path.exists() else None
    ledger.settle(reservation,result['leased_ns'] if result else reservation['reserved_ns'])
    if result and result['leased_ns']>reservation['reserved_ns']: raise ValueError('worker exceeded reservation')
    if interrupted: raise ValueError('acceptance/study supervisor interrupted; charge retained')
    return dict(supervisor_returncode=worker.returncode,worker=result)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--id',required=True);p.add_argument('--seconds',type=int,required=True);p.add_argument('command',nargs=argparse.REMAINDER);a=p.parse_args()
    command=a.command[1:] if a.command[:1]==['--'] else a.command
    with ledger_for() as ledger:
        result=run(ledger,'accept',a.id,command,a.seconds,ROOT/'artifacts/gpup5b-acceptance')
        print(result);print('acceptance seconds:',category_usage(ledger,'accept')/NS,'campaign:',ledger.totals()/NS)
    if not result['worker'] or result['supervisor_returncode'] or result['worker']['reason']!='completed' or result['worker']['returncode']!=0:raise SystemExit(1)
if __name__=='__main__':main()
