"""ADR-0021/ADR-0022 shared-lease supervision; all new work uses the preserved campaign ledger.

Each research study is a frozen protocol file that names its identity prefix, output
directory, separate study/acceptance caps, combined cap and the exact prior ledger
prefix it preserves. The GPUP-5B constants remain the defaults so existing callers,
tests and archived evidence keep their byte-identical behavior.
"""
import argparse
import hashlib
import subprocess
from dataclasses import dataclass
from pathlib import Path
from lp_protocol import ROOT, Ledger, NS, checked_reference, file_hash, read_json, write_json

PRIOR_NS=1467266874696
PRIOR_EVENTS=3288
PRIOR_HASH='b3ca2739b1108a552b0423606ddd0cd94a8ed2323da1506098fa0150ba42bfef'
OUTPUT=ROOT/'artifacts/gpup5b-v1'


@dataclass(frozen=True)
class Study:
    """Frozen accounting identity of one research study."""
    prefix: str
    output: Path
    acceptance: Path
    study_cap_seconds: int
    acceptance_cap_seconds: int
    combined_cap_seconds: int
    prior_ns: int
    prior_events: int
    prior_hash: str
    cumulative_ceiling_ns: int

    @staticmethod
    def from_protocol(value):
        if value['schema_version']==1:
            return STUDY_V1
        if value['schema_version']!=2:raise ValueError('unsupported research protocol version')
        return Study(prefix=value['prefix'],output=ROOT/value['output'],acceptance=ROOT/value['acceptance_output'],
                     study_cap_seconds=value['study_cap_seconds'],acceptance_cap_seconds=value['acceptance_cap_seconds'],
                     combined_cap_seconds=value['combined_cap_seconds'],prior_ns=value['prior_gpu_ns'],
                     prior_events=value['prior_events'],prior_hash=value['prior_ledger_sha256'],
                     cumulative_ceiling_ns=value['cumulative_ceiling_ns'])


STUDY_V1=Study(prefix='gpup5b',output=OUTPUT,acceptance=ROOT/'artifacts/gpup5b-acceptance',study_cap_seconds=900,
               acceptance_cap_seconds=300,combined_cap_seconds=1200,prior_ns=PRIOR_NS,prior_events=PRIOR_EVENTS,
               prior_hash=PRIOR_HASH,cumulative_ceiling_ns=4502574545061)


def ledger_for(study=STUDY_V1):
    value=read_json(ROOT/'benchmarks/configs/lp-precision-v4.json')
    authority=checked_reference(ROOT,value['budget_authority'])
    directory=ROOT/'artifacts/lp-campaign-ledgers'/read_json(authority)['id']
    prefix=b''.join((directory/'ledger.jsonl').read_bytes().splitlines(keepends=True)[:study.prior_events])
    if hashlib.sha256(prefix).hexdigest()!=study.prior_hash: raise ValueError('historical ledger prefix changed')
    if read_json(directory/'output.json')['output_path']!=str(ROOT/'artifacts/gpup-baseline-v1'): raise ValueError('original output binding changed')
    if study.cumulative_ceiling_ns!=value['cumulative_gpu_ns']: raise ValueError('cumulative ceiling differs from the budget authority')
    return Ledger(directory,file_hash(authority),value['phase_gpu_seconds'],cumulative_ns=value['cumulative_gpu_ns'])


def category_usage(ledger,category,prefix='gpup5b'):
    return sum(e['charged_ns'] if e['kind']=='settle' else e['reserved_ns'] if e['reservation_id'] in ledger.pending() else 0
               for e in ledger.events if e['trial_id'].startswith(prefix+'-'+category+'-'))


def run(ledger,category,key,command,seconds,directory=None,study=STUDY_V1):
    directory=directory or study.output
    identity=study.prefix+'-'+category+'-'+key
    if identity in ledger.attempted(): raise ValueError('attempt already admitted')
    reserve=seconds+6
    cap=study.study_cap_seconds if category=='study' else study.acceptance_cap_seconds
    if (category_usage(ledger,category,study.prefix)+reserve*NS>cap*NS
            or ledger.totals()-study.prior_ns+reserve*NS>study.combined_cap_seconds*NS):
        raise ValueError(study.prefix.upper()+' budget exhausted; incomplete evidence retained')
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
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--id',required=True);p.add_argument('--seconds',type=int,required=True)
    p.add_argument('--protocol',type=Path,default=None,help='research protocol file; GPUP-5B when omitted')
    p.add_argument('command',nargs=argparse.REMAINDER);a=p.parse_args()
    command=a.command[1:] if a.command[:1]==['--'] else a.command
    study=Study.from_protocol(read_json(a.protocol)) if a.protocol else STUDY_V1
    with ledger_for(study) as ledger:
        result=run(ledger,'accept',a.id,command,a.seconds,study.acceptance,study)
        print(result);print('acceptance seconds:',category_usage(ledger,'accept',study.prefix)/NS,'campaign:',ledger.totals()/NS)
    if not result['worker'] or result['supervisor_returncode'] or result['worker']['reason']!='completed' or result['worker']['returncode']!=0:raise SystemExit(1)
if __name__=='__main__':main()
