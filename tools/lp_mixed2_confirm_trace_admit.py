"""Exercise failure capture on an intentionally slow CPU-only resource scan."""
import json
import subprocess
import sys
from lp_mixed2_confirm_common import BASE, load, put, ref, require


def main():
    version=sys.argv[1] if len(sys.argv)>1 else 'v1'
    require(version in ('v1','v2'),'trace admission version')
    out=BASE/('failure-trace-admission-'+version);out.mkdir(exist_ok=False)
    journal=dict(identity='capture-contract',prior_cpu_ns=0,ceiling_cpu_ns=24000000000,active=None,
                 failed=False,runs=[],stages={'implementation':dict(cap_cpu_ns=24000000000,charged_cpu_ns=0)})
    put(out/'journal.json',journal)
    request=dict(stage='implementation',reserve_cpu_seconds=24,output=str(out/'resource.json'),
        log=str(out/'work.log'),journal=str(out/'journal.json'),lock=str(out/'lock'),slots=4,
        declared_memory_bytes=64<<20,rss_stop_bytes=6<<30,address_space_bytes=0,sources=[],
        bootstrap=False,show_log=False,max_gap_ns=100000000,command=[sys.executable,'-c','import time;time.sleep(1)'])
    put(out/'request.json',request)
    runner=out/'run.py';runner.write_text('''import sys,time,inspect
sys.path.insert(0,'tools')
import lp_confirmation_supervisor as cpu
from lp_mixed2_confirm_failure_trace import install
from lp_mixed2_confirm_common import load
r=load(sys.argv[1]);original=cpu.snapshot
def delayed_scan(*a,**k):
 if inspect.currentframe().f_back.f_code.co_name=='coordinator':time.sleep(.15)
 return original(*a,**k)
cpu.snapshot=delayed_scan
install(cpu,r['output'])
cpu.run(r)
''')
    subprocess.run([sys.executable,str(runner),str(out/'request.json')],check=True,timeout=8)
    r=load(out/'resource.json');capture=load(out/'resource.json.failure-capture.json')
    text=(out/'resource.json.failure-stack.txt').read_text()
    require(r['status']=='refused' and r['result']['reason']=='lost_coordinator_heartbeat','intended refusal')
    require(r['guardian_cleanup']['empty'] and capture['decision_already_refused'],'post-decision cleanup')
    require('delayed_scan' in text and 'coordinator' in text,'missing sampler stack')
    put(out/'result.json',dict(status='passed',source=ref(__file__),resource=ref(out/'resource.json'),
        capture=ref(out/'resource.json.failure-capture.json'),stack=ref(out/'resource.json.failure-stack.txt'),
        scientific_timing=False,added_per_sample_instrumentation=False))


if __name__=='__main__':main()
