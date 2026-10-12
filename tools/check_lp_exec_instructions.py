"""Audit the actual ADR-0035 sparse/decode SASS and resource inventory."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

def audit(image,output):
    image=Path(image);output=Path(output);output.mkdir(parents=True,exist_ok=True)
    tool='/usr/local/cuda/bin/cuobjdump'
    sass=subprocess.check_output([tool,'--dump-sass',str(image)],text=True)
    resources=subprocess.check_output([tool,'--dump-resource-usage',str(image)],text=True)
    (output/'exec.sass').write_text(sass);(output/'exec.resources').write_text(resources)
    inventory={}
    for name in ['exec_prepare','exec_cached','exec_uncached']:
        body=re.search(r'Function : '+name+r'\s+(.*?)(?=Function :|\Z)',sass,re.S).group(1)
        instructions=re.findall(r'/\*[0-9a-f]+\*/\s+(?:@!?P\d+\s+)?([A-Z][A-Z0-9_.]*)',body)
        if not instructions:raise ValueError('missing instructions: '+name)
        forbidden=[x for x in instructions if x.startswith(('DADD','DMUL','DFMA','DSETP','DSET','DMNMX','RRO','CALL','JCAL')) or re.search(r'(?:F2F|I2F|F2I).*F64',x)]
        if forbidden:raise ValueError('FP64 or unaudited call in '+name+': '+str(forbidden))
        props=re.search(r'Function '+name+r':\s+REG:(\d+) STACK:(\d+) SHARED:(\d+) LOCAL:(\d+)',resources)
        if not props:raise ValueError('missing resource inventory')
        regs,stack,shared,local=map(int,props.groups())
        if regs>128 or stack or local:raise ValueError('resource gate failed: '+name)
        inventory[name]=dict(registers=regs,stack_bytes=stack,local_bytes=local,shared_bytes=shared,instructions={x:instructions.count(x) for x in sorted(set(instructions))},native_fp64=False)
    result=dict(identity='lp-exec-instruction-audit-v1',image_sha256=hashlib.sha256(image.read_bytes()).hexdigest(),kernels=inventory,fp64_elsewhere='native vector updates, host control and certification',hardware_counters='not collected')
    (output/'instruction-audit.json').write_text(json.dumps(result,indent=2)+'\n');return result
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--image',default='target/native/cuda/lp_pdhg_exec.cubin');p.add_argument('--output',default='artifacts/gpup-exec-v1');a=p.parse_args()
    print(json.dumps(audit(a.image,a.output),indent=2))
