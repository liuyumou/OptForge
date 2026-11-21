"""Exercise full-audit streaming on retained geometry and a synthetic rollback trace."""
import json,subprocess
import numpy as np
from lp_billion_common import BASE,ROOT,put,load,ref,resolve,require
from lp_billion_arrays import write
from lp_general_oracle import settings
from lp_billion_full_audit import audit

def main():
    out=BASE/'full-audit-admission-v1';out.mkdir(exist_ok=False)
    original=load(BASE/'copt-full-admission-v2/result.json')['cases'][0]
    model=load(resolve(original['model']));endpoint=dict(primal=write(BASE,np.zeros(model['columns'],dtype=np.float64)),dual=write(BASE,np.zeros(model['rows'],dtype=np.float64)))
    request=dict(settings=settings('native'),endpoint=endpoint)
    p=subprocess.run([str(BASE/'image-v1/executor'),'assess',str(resolve(original['model'])),str(BASE)],input=json.dumps(request)+'\n',text=True,capture_output=True)
    (out/'zero-check.stdout').write_text(p.stdout);(out/'zero-check.stderr').write_text(p.stderr);require(p.returncode==0,'independent admission zero endpoint')
    zero=json.loads(p.stdout);final=load(resolve(original['check']))
    strip=lambda proof:{k:v for k,v in proof.items() if k not in ['input_ns','model_sha256']}
    vendor=load(resolve(original['response']))
    project=dict(settings=settings('native'),endpoint=vendor['endpoint'],certificate=strip(final),certified=final['accepted'],
        assessments=[dict(endpoint=endpoint,certificate=strip(zero)),dict(endpoint=vendor['endpoint'],certificate=strip(final))])
    cells=[]
    for lane,response in [('native',project),('copt-cpu-auto',vendor)]:
        identity='full-audit-admission-v1-'+lane;put(BASE/identity/'response.json',response)
        cells.append(dict(id=identity,lane=lane,model=original['model'],audit_seconds=60))
    manifest=out/'freeze.json';put(manifest,dict(status='synthetic_audit_admission_only',cells=cells,checker=ref(BASE/'image-v1/executor'),source=ref(__file__),retained_response=original['response']))
    for i in range(len(cells)):audit(manifest,i)
    a=load(BASE/(cells[0]['id']+'-full-audit/result.json'));b=load(BASE/(cells[1]['id']+'-full-audit/result.json'))
    require(a['checks']==2 and a['covered_endpoints']==3 and a['proof_mapping']==[0,1,0] and a['certified'],'distinct rollback and identical-proof coverage')
    require(b['checks']==1 and b['certified'],'independent vendor certificate')
    require(all(x['final_check_ns']+x['offline_audit_ns']==x['elapsed_ns'] for x in [a,b]),'disjoint complete checker costs')
    put(out/'result.json',dict(status='passed',manifest=ref(manifest),checker_source=ref(ROOT/'tools/lp_billion_full_audit.py'),project_audit=ref(BASE/(cells[0]['id']+'-full-audit/result.json')),vendor_audit=ref(BASE/(cells[1]['id']+'-full-audit/result.json')),scientific_solves_repeated=False))
if __name__=='__main__':main()
