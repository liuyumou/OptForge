"""Execute exact-source bounded Tensor acceptance through the shared allocator."""
import argparse,os,subprocess,re
from pathlib import Path
from lp_protocol import ROOT,read_json,write_json,file_hash
from lp_tensor_common import protocol,ledger_for,receipt
from benchmark_lp import source_identity

def main():
 p=argparse.ArgumentParser();p.add_argument('--id',required=True);p.add_argument('--gate',required=True,choices=['regular','project','memcheck','racecheck','initcheck','synccheck']);a=p.parse_args();v=protocol()
 if not re.fullmatch('[a-z0-9-]+',a.id):raise ValueError('acceptance ID differs')
 from benchmark_lp_tensor import freeze
 d,identity=freeze(v);out=ROOT/v['acceptance_output'];out.mkdir(parents=True,exist_ok=True);tests=read_json(d/'acceptance-binaries.json');gate=a.gate
 if gate=='regular':command=['bash',str(ROOT/'tools/lp_exec_regular_check.sh'),*[str(ROOT/tests[k]['path']) for k in ['optimizer-cuda','optimizer-schedule-examples','optimizer-lp-cuda']]];seconds=180
 elif gate=='project':command=[os.environ.get('AI_OPTIMIZER_PYTHON','python3'),str(ROOT/'tools/lp_tensor_accept.py')];seconds=240
 else:command=['bash',str(ROOT/'tools/lp_tensor_gpu_check.sh'),str(ROOT/tests['tensor']['path']),gate];seconds=90
 key=v['id']+'-accept-'+a.id
 request=dict(schema_version=2,gpu_admission_seconds=3,command=['/usr/bin/env','AI_OPTIMIZER_CUDA_DIR='+str(d),*command],directory=str(out),prefix=key,solve_seconds=seconds,cleanup_seconds=2,host_rss_bytes=v['limits']['host_rss_bytes'],poll_ms=10,output_bytes=v['limits']['output_bytes'])
 with ledger_for(v) as ledger:
  if key in ledger.attempted() or (out/(key+'.request.json')).exists():raise ValueError('acceptance identity cannot retry')
  if source_identity()!=identity['source_tree_sha256']:raise ValueError('acceptance source differs')
  path=out/(key+'.request.json');write_json(path,request);write_json(out/(key+'.source.json'),dict(gate=gate,source_tree_sha256=identity['source_tree_sha256'],request_sha256=file_hash(path),command=command))
  reservation=ledger.reserve(key,seconds+6,phase='repeatability');worker=subprocess.Popen(['bash',str(ROOT/'tools/gpu_job.sh'),v['device'],'--lp-study-request',str(path)],pass_fds=(ledger.lock.fileno(),))
  try:worker.wait(timeout=seconds+310)
  finally:
   if worker.poll() is None:worker.terminate();worker.wait(timeout=3)
   report=out/(key+'.worker.json');info=read_json(report) if report.exists() else None;ledger.settle(reservation,info['leased_ns'] if info else reservation['reserved_ns']);write_json(out/'budget.json',receipt(ledger))
  if worker.returncode or info is None or info['reason']!='completed' or info['returncode']!=0 or info['leased_ns']>reservation['reserved_ns']:raise ValueError('Tensor acceptance failed; identity retained')
if __name__=='__main__':main()
