"""Replay strict scalar proofs while preserving a synthetic deadline classification."""
from lp_billion_common import BASE,ROOT,put,load,ref,require
from lp_billion_full_audit_v2 import audit

def main():
    out=BASE/'full-audit-admission-v2';out.mkdir(exist_ok=False)
    previous=load(BASE/'full-audit-admission-v1/freeze.json');model=previous['cells'][0]['model']
    project=load(BASE/'full-audit-admission-v1-native/response.json');project['status']='certified'
    vendor=load(BASE/'full-audit-admission-v1-copt-cpu-auto/response.json')
    variants=[('native','native',project),('native-deadline','native',dict(project,status='deadline',certified=False)),('copt-cpu-auto','copt-cpu-auto',vendor)]
    cells=[]
    for suffix,lane,response in variants:
        identity='full-audit-admission-v2-'+suffix;put(BASE/identity/'response.json',response)
        cells.append(dict(id=identity,lane=lane,model=model,audit_seconds=60))
    manifest=out/'freeze.json';put(manifest,dict(status='synthetic_audit_admission_only',cells=cells,checker=previous['checker'],source=ref(__file__),previous=ref(BASE/'full-audit-admission-v1/freeze.json')))
    for i in range(len(cells)):audit(manifest,i)
    results=[load(BASE/(c['id']+'-full-audit/result.json')) for c in cells]
    require([r['certified'] for r in results]==[True,False,True],'deadline status retained without regrading')
    require(all(r['strict_endpoint_accepted'] for r in results),'all final witnesses independently accepted')
    require(all(r['checks']==2 and r['proof_mapping']==[0,1,0] for r in results[:2]),'distinct intermediate and duplicate final coverage')
    require(all(r['final_check_ns']+r['offline_audit_ns']==r['elapsed_ns'] for r in results),'exact audit cost coverage')
    put(out/'result.json',dict(status='passed',manifest=ref(manifest),checker_source=ref(ROOT/'tools/lp_billion_full_audit_v2.py'),audits=[ref(BASE/(c['id']+'-full-audit/result.json')) for c in cells],scientific_solves_repeated=False))
if __name__=='__main__':main()
