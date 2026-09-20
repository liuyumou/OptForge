"""Bounded, separately accounted GPUP-5 GPU acceptance under the shared host lease."""
import argparse,hashlib,subprocess
from pathlib import Path
from lp_protocol import ROOT,Ledger,read_json,write_json

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--id',required=True);p.add_argument('--seconds',type=int,required=True)
    p.add_argument('--device',default='GPU-dfb2449a-9eff-e868-3597-2c448c9a8e48');p.add_argument('command',nargs=argparse.REMAINDER);a=p.parse_args()
    command=a.command[1:] if a.command[:1]==['--'] else a.command
    directory=ROOT/'artifacts/gpup5-acceptance'
    with Ledger(directory/'gpu-budget',hashlib.sha256(b'ADR-0019 GPUP-5 acceptance 900 seconds').hexdigest(),slice_seconds=900) as ledger:
        ledger.bind_output(directory)
        request=dict(command=command,directory=str(directory),prefix=a.id,solve_seconds=a.seconds,cleanup_seconds=2,
                     host_rss_bytes=8589934592,poll_ms=10,output_bytes=33554432)
        path=directory/(a.id+'.request.json')
        if path.exists():raise ValueError('acceptance attempt ID already exists')
        write_json(path,request);reservation=ledger.reserve(a.id,a.seconds+5)
        run=subprocess.run(['bash',str(ROOT/'tools/gpu_job.sh'),a.device,'--lp-study-request',str(path)],pass_fds=(ledger.lock.fileno(),))
        result_path=directory/(a.id+'.worker.json');result=read_json(result_path) if result_path.exists() else None
        ledger.settle(reservation,result['leased_ns'] if result else reservation['reserved_ns'])
        print('Acceptance GPU seconds:',ledger.totals()/1e9,'of 900; result:',result)
        if not result or run.returncode or result['reason']!='completed' or result['returncode']!=0:raise SystemExit(1)
if __name__=='__main__':main()
