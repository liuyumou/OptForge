"""Reconstruct an early development executable and verify exact hash, CPU only."""
import hashlib,shutil,subprocess
from pathlib import Path
from lp_fp4_integrate_common import ROOT,BASE,put,ref,load,require

def main():
 package=ROOT/'research/lp-fp4-integrate';binary=package/'target/release/lp-fp4-integrate';expected=ref(binary)['sha256']
 original={p:p.read_bytes() for p in (package/'src').glob('*.rs')};old=load(BASE/'device-differential-v1/manifest.json')['binary']['sha256'];result={}
 try:
  for p in original:p.write_bytes((BASE/'sources/device-differential-v1'/p.relative_to(ROOT)).read_bytes())
  subprocess.run(['cargo','build','--release','--manifest-path',str(package/'Cargo.toml')],check=True)
  digest=ref(binary)['sha256'];require(digest==old,'early binary reconstruction differs')
  shutil.copy2(binary,BASE/'binaries'/digest);result['early']=ref(BASE/'binaries'/digest)
 finally:
  for p,data in original.items():p.write_bytes(data)
  subprocess.run(['cargo','build','--release','--manifest-path',str(package/'Cargo.toml')],check=True)
  require(ref(binary)['sha256']==expected,'restored final binary differs')
 result['final']=ref(binary);put(BASE/'binary-reconstruction-v1.json',result)
if __name__=='__main__':main()
