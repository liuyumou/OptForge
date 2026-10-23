"""Bound CPU/RSS; CPU admission may coexist only with non-numerical tooling work."""
import argparse,os,resource,signal,subprocess,time
from pathlib import Path
from lp_quant_resources import process_tree
from lp_quant_resident_common import numeric_sources
from benchmark_lp import source_identity
from lp_protocol import write_json
def main():
 p=argparse.ArgumentParser();p.add_argument('--output',required=True,type=Path);p.add_argument('--admission',action='store_true');p.add_argument('command',nargs=argparse.REMAINDER);a=p.parse_args();command=a.command[1:] if a.command[:1]==['--'] else a.command
 if not command:raise ValueError('resource command required')
 a.output.parent.mkdir(parents=True,exist_ok=True);source=source_identity();numeric=numeric_sources();start=time.monotonic_ns();own=time.process_time();before=resource.getrusage(resource.RUSAGE_CHILDREN);peak=0;reason='completed'
 with a.output.with_suffix('.log').open('wb') as out:
  child=subprocess.Popen(command,stdout=out,stderr=subprocess.STDOUT,start_new_session=True)
  while child.poll() is None:
   rss,cpu=process_tree(child.pid);peak=max(peak,rss)
   if rss>8<<30 or cpu>21600 or time.monotonic_ns()-start>21600*10**9:
    reason='resource_limit';os.killpg(child.pid,signal.SIGTERM)
    try:child.wait(timeout=3)
    except subprocess.TimeoutExpired:os.killpg(child.pid,signal.SIGKILL);child.wait()
    break
   time.sleep(.05)
 after=resource.getrusage(resource.RUSAGE_CHILDREN);final=source_identity();same_numeric=numeric==numeric_sources()
 if not same_numeric or not a.admission and final!=source:reason='source_changed'
 result=dict(command=command,reason=reason,returncode=child.returncode,source_before=source,source_after=final,numerical_sources_unchanged=same_numeric,cpu_seconds=time.process_time()-own+after.ru_utime+after.ru_stime-before.ru_utime-before.ru_stime,elapsed_ns=time.monotonic_ns()-start,peak_process_tree_rss_bytes=peak,max_child_rss_bytes=after.ru_maxrss*1024,gpu_seconds=0)
 write_json(a.output,result);print(result,flush=True)
 if child.returncode or reason!='completed':raise SystemExit(child.returncode or 1)
if __name__=='__main__':main()
