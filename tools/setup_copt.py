"""Provision isolated local COPT 8.0.6 bindings for GPUP-5; never copy licenses."""
import argparse,re,shutil,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--installation',type=Path,default=Path.home()/'copt80');a=p.parse_args()
    header=(a.installation/'include/copt.h').read_text()
    version=tuple(int(re.search(r'#define\s+COPT_VERSION_'+n+r'\s+(\d+)',header).group(1)) for n in ['MAJOR','MINOR','TECHNICAL'])
    if version!=(8,0,6):raise ValueError('the accepted study pins COPT 8.0.6')
    if sys.version_info[:2]!=(3,11):raise ValueError('the frozen local study uses Python 3.11')
    venv=ROOT/'artifacts/gpup5-copt/venv';subprocess.run([sys.executable,'-m','venv','--system-site-packages',str(venv)],check=True)
    site=venv/'lib/python3.11/site-packages';shutil.copytree(a.installation/'lib/python/311/coptpy',site/'coptpy',dirs_exist_ok=True)
    shutil.copy2(a.installation/'lib/python/deps/libcopt_python.so',site/'coptpy/libcopt_python.so')
    subprocess.run([str(venv/'bin/python'),'-B','-c','import coptpy; print("COPT bindings imported; no solver executed")'],check=True)
if __name__=='__main__':main()
