"""Collect final source-bound numerical and sanitizer admission without retries."""
import argparse
from lp_fp4_fast_common import BASE, ROOT, put, load, ref, require
from lp_fp4_fast_experiment import BINARY


def main():
    p=argparse.ArgumentParser();p.add_argument('version');a=p.parse_args()
    software=[]
    for name in ('native-gate-v1','cpu-build-v6'):
        path=BASE/'resources'/(name+'.settlement.json');require(load(path)['status']=='passed','CPU/software gate required');software.append(ref(path))
    names=['primitives','stress','transactions','memcheck','racecheck','initcheck','synccheck']
    checks=[]
    for name in names:
        directory=BASE/(name+'-'+a.version);result=load(directory/'result.json');manifest=load(directory/'manifest.json')
        require(result['status']=='passed','missing acceptance: '+name)
        require(manifest['image']==ref(BASE/('build-'+a.version)/'fast.cubin') and manifest['binary']['sha256']==ref(BINARY)['sha256'],'acceptance identity differs')
        checks.append(dict(stage=name,count=len(result['rows']),result=ref(directory/'result.json'),manifest=ref(directory/'manifest.json')))
    d=BASE/('admission-'+a.version);d.mkdir(exist_ok=False)
    put(d/'result.json',dict(status='passed',checks=checks,software=software,build=ref(BASE/('build-'+a.version)/'receipt.json'),binary=ref(BINARY),source=ref(ROOT/'research/lp-fp4-fast/cuda/fast.cu'),certified=False))
    print(checks)

if __name__=='__main__':main()
