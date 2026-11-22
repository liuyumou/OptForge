"""Read-only small status view for the active supervised continuation."""
import json,time
from lp_billion_common import BASE,load

def main():
    active=[]
    for p in (BASE/'resources').glob('*.reservation.json'):
        if not p.with_name(p.name.replace('.reservation.','.settlement.')).exists():
            active.append(dict(id=p.name.removesuffix('.reservation.json'),seconds=round(time.time()-p.stat().st_mtime)))
    audited=[]
    paths=sorted(BASE.glob('full-billion-v1-*/response.json'))
    extra=sorted(BASE.glob('copt-nopresolve-1b-v1-*/response.json'))
    capacity=[p for tag in ['64m','256m','512m'] for p in sorted(BASE.glob(f'copt-nopresolve-{tag}-v1-*/response.json'))]
    for p in paths+extra+capacity:
        try:
            identity=p.parent.name;a_path=BASE/(identity+'-full-audit/result.json')
            if not a_path.exists():continue
            r=load(p);a=load(a_path);m=load(p.parent/'result.json')
            audited.append(dict(id=identity,status=r['status'],certified=a['certified'],has_solution=r.get('has_solution',True),original_nonzeros=r['nonzeros'],updates=r.get('logical',r.get('native',{}).get('PDLPIter')),
                complete_seconds=round((m['fresh_process_ns']+a['final_check_ns'])/1e9,3),
                gpu_advance_seconds=round(r['solver_profile']['exclusive_ns']['device_advance']/1e9,3) if 'solver_profile' in r else None,
                peak_gib=round(m['solver_child_hwm_bytes']/(1<<30),3) if m.get('solver_child_hwm_bytes') is not None else None))
        except (FileNotFoundError,json.JSONDecodeError):pass
    print(json.dumps(dict(responses=len(paths),additional_copt_responses=len(extra),active=active,audited=audited)))
if __name__=='__main__':main()
