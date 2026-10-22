"""CPU-only numerical fixture and generated-code admission for ADR-0037."""
import argparse
import collections
import hashlib
import json
from pathlib import Path
import re
import subprocess
from lp_protocol import ROOT,file_hash,write_json
import lp_refine_oracle

def audit(image,directory):
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
    image=Path(image)
    build_path=image.with_name('lp_pdhg_refine.build.json')
    build=json.loads(build_path.read_text())
    if build['image_sha256']!=file_hash(image) or build['source_sha256']!=file_hash(ROOT/'cuda/lp_pdhg_refine/lp_pdhg_refine.cu'):raise ValueError('refine build source/image binding')
    for stream in ['stdout','stderr']:
        if build[stream+'_sha256']!=file_hash(image.with_name('lp_pdhg_refine.compile.'+stream)):raise ValueError('refine compiler log binding')
    if '0 bytes spill stores, 0 bytes spill loads' not in image.with_name('lp_pdhg_refine.compile.stderr').read_text():raise ValueError('refine compiler spill receipt')
    dump='/usr/local/cuda/bin/cuobjdump'
    resources=subprocess.check_output([dump,'--dump-resource-usage',str(image)],text=True)
    sass=subprocess.check_output([dump,'--dump-sass',str(image)],text=True)
    entries=re.findall(r'Function\s+(\w+):\s*REG:(\d+)\s+STACK:(\d+)\s+SHARED:(\d+)\s+LOCAL:(\d+)',resources)
    if len(entries)!=1 or entries[0][0]!='refine_product':raise ValueError('refine kernel family differs')
    _,registers,stack,shared,local=entries[0]
    if int(registers)>128 or any(int(x) for x in [stack,shared,local]):raise ValueError('refine register/stack/scratch admission')
    instructions=collections.Counter()
    for line in sass.splitlines():
        match=re.search(r'/\*[0-9a-f]+\*/\s+(?:@!?U?P\d+\s+)?([A-Z][A-Z0-9_.]*)',line)
        if match:instructions[match.group(1)]+=1
    if not any(k.startswith('FMUL') for k in instructions) or not any(k.startswith('FADD') for k in instructions):raise ValueError('refine FP32 multiply/reduction missing')
    if any('ATOM' in k or 'RED.' in k for k in instructions):raise ValueError('atomic refinement reduction')
    (directory/'refine.resources.txt').write_text(resources);(directory/'refine.sass.txt').write_text(sass)
    result=dict(image_sha256=file_hash(image),kernel='refine_product',registers=int(registers),stack_bytes=int(stack),shared_bytes=int(shared),local_bytes=int(local),instruction_counts=dict(instructions),resources_sha256=file_hash(directory/'refine.resources.txt'),sass_sha256=file_hash(directory/'refine.sass.txt'))
    write_json(directory/'refine.audit.json',result);return result

def main():
    p=argparse.ArgumentParser();p.add_argument('--image',type=Path);p.add_argument('--output',type=Path,default=ROOT/'artifacts/gpup-refine-v1/admission');a=p.parse_args()
    fixture=lp_refine_oracle.generate()
    if json.loads(lp_refine_oracle.FIXTURE.read_text())!=fixture:raise ValueError('independent rational fixture differs')
    result=dict(identity='gpup-refine-admission-v1',cases=len(fixture['cases']),correction_maps=sum(c['expected']['maps'] for c in fixture['cases']),fixture_sha256=file_hash(lp_refine_oracle.FIXTURE))
    if a.image:result['kernel']=audit(a.image,a.output)
    a.output.mkdir(parents=True,exist_ok=True);write_json(a.output/'admission.json',result);print(json.dumps(result))

if __name__=='__main__':main()
