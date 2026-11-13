"""Execute each frozen block once; preserve refusals and never inspect speedup."""
import subprocess
import sys
from lp_mixed2_confirm_common import BASE, ROOT, load, require


def main():
    f=load(BASE/'confirmation-freeze.json')
    require(not list((BASE/'resources').glob('confirmation-b*.reservation.json')),'cohort already started')
    for index in range(f['blocks']):
        identity=f'confirmation-b{index:02d}'
        code=subprocess.run([sys.executable,'tools/lp_mixed2_confirm_budget.py','--id',identity,
            '--phase','confirmation','--seconds',str(f['block_reserve_seconds']),'--gpu','--',
            sys.executable,'tools/lp_mixed2_reuse_place.py',sys.executable,
            'tools/lp_mixed2_confirm_confirmation.py','block','--index',str(index)],cwd=ROOT).returncode
        settlement=load(BASE/'resources'/(identity+'.settlement.json'))
        require(not settlement['overrun'],'resource overrun forbids further execution')
        r=load(ROOT/settlement['resource']['path'])
        require(r['guardian_cleanup']['empty'] and r['result']['cleanup']['empty'],'cleanup must finish before next block')
        require(code in (0,2),'unexpected launcher result')
        print(dict(block=index+1,total=f['blocks'],status=settlement['status'],reason=r['result']['reason'],
            sample_gap_ms=r['result'].get('max_sample_gap_ns',0)/1e6,
            sample_work_ms=r['result'].get('max_sample_work_ns',0)/1e6),flush=True)


if __name__=='__main__':main()
