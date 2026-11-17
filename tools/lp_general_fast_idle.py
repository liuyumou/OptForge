"""Bounded management observations while this leased job launches no CUDA work."""
import argparse
import subprocess
import time
from lp_general_common import BASE,DEVICE,put,ref,require


def run(identity):
    out=BASE/identity;out.mkdir(exist_ok=False);rows=[]
    for _ in range(20):
        start=time.monotonic_ns()
        p=subprocess.run(['nvidia-smi','--id='+DEVICE,'--query-gpu=uuid,utilization.gpu,utilization.memory,power.draw,clocks.sm,clocks.mem','--format=csv,noheader'],capture_output=True,text=True)
        q=subprocess.run(['nvidia-smi','--id='+DEVICE,'--query-compute-apps=gpu_uuid,pid,process_name,used_memory','--format=csv,noheader'],capture_output=True,text=True)
        rows.append(dict(start_ns=start,end_ns=time.monotonic_ns(),device_returncode=p.returncode,device=p.stdout,device_stderr=p.stderr,apps_returncode=q.returncode,apps=q.stdout,apps_stderr=q.stderr))
        require(p.returncode==q.returncode==0,'management observation failed');time.sleep(.2)
    put(out/'result.json',dict(status='passed',source=ref(__file__),rows=rows,claim='No solver or CUDA workload launched by this job. Management utilization does not identify the owner or explain historical timing causally.'))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--id',required=True);a=p.parse_args();run(a.id)
