"""Compile-only inventory of ordinary and new Tensor device suites."""
import json,os,subprocess
from pathlib import Path
from benchmark_lp import reference,source_identity
from lp_protocol import ROOT,write_json
from lp_tensor_common import BASE

def main():
 r=subprocess.run(['cargo','test','-p','optimizer-cuda','-p','optimizer-schedule-examples','-p','optimizer-lp-cuda','--all-features','--no-run','--message-format=json','--locked'],capture_output=True,text=True,env=dict(os.environ,CARGO_BUILD_JOBS='4'))
 d=BASE/'build';d.mkdir(parents=True,exist_ok=True);(d/'tests.stdout').write_text(r.stdout);(d/'tests.stderr').write_text(r.stderr);r.check_returncode();found={}
 for line in r.stdout.splitlines():
  v=json.loads(line)
  if v.get('reason')!='compiler-artifact' or not v.get('executable') or not v['profile']['test']:continue
  name=v['target']['name'];p=Path(v['target']['src_path']);key='tensor' if name=='tensor_device' else p.parent.parent.name if name=='device' else None
  if key:found[key]=reference(ROOT,Path(v['executable']))
 if set(found)!={'optimizer-cuda','optimizer-schedule-examples','optimizer-lp-cuda','tensor'}:raise ValueError('Tensor test binary roster')
 write_json(ROOT/'target/lp-tensor-binaries.json',dict(source_tree_sha256=source_identity(),binaries=found));print('compiled four suites; zero GPU work')
if __name__=='__main__':main()
