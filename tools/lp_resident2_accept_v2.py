"""Independent endpoint/export admission for the frozen native resident study."""
import os
from pathlib import Path
import struct
import subprocess

from lp_resident2_common import BASE, ROOT, DEVICE, checked, load, put, ref, require
from lp_baseline_common import verify_certificate
from lp_resident2_study_v2 import MANIFEST, verify


def main():
    m=load(MANIFEST)
    verify(m)
    require(os.environ.get('AI_OPTIMIZER_GPU_LEASE')=='inherited' and os.environ.get('CUDA_VISIBLE_DEVICES')==DEVICE,
            'pinned lease required')
    model=next(j['model'] for j in m['jobs'] if j['model_id']=='gpup-development-irregular-2048')
    rows=[]
    root=BASE/'transport-admission'
    root.mkdir(exist_ok=False)
    for mode in ['control','resident']:
        output=root/mode
        subprocess.run([str(checked(m['binary'])),mode,str(checked(model)),str(output),'50000','8','2','solve'],check=True)
        worker=load(output/'worker.json')
        for row in worker['rows']:
            witness=output/f"candidate-{row['index']}.json"
            certificate=output/f"certificate-{row['index']}.json"
            subprocess.run([str(checked(m['checker'])),'check',str(checked(model)),str(witness),str(certificate)],check=True)
            c=verify_certificate(ref(certificate),ref(witness),model,m['checker'])
            require(c['accepted'] and row['stop']=='accepted' and row['iterations']>0,'nontrivial certificate admission failed')
            w=load(witness)
            bits=lambda values:[struct.pack('!d',v).hex() for v in values]
            rows.append(dict(mode=mode,index=row['index'],iterations=row['iterations'],primal_bits=bits(w['primal']),
                dual_bits=bits(w['dual']),candidate=ref(witness),certificate=ref(certificate)))
    for row in rows[1:]:
        require(all(row[k]==rows[0][k] for k in ['iterations','primal_bits','dual_bits']), 'fresh/prepared endpoint differs')
    for row in rows:
        del row['primal_bits'];del row['dual_bits']
    put(BASE/'transport-admission.json',dict(status='passed',manifest=ref(MANIFEST),endpoints=rows,
        conclusion='Four nontrivial original-model certificates, exact cold-iterate repeated endpoints and native-control equality.'))

if __name__=='__main__':main()
