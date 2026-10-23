"""CPU-only generated-instruction and resource admission for the quant image."""
import json,re,subprocess
from pathlib import Path
from lp_protocol import ROOT,file_hash,write_json
from lp_refine_admission import instruction_counts

def main():
 image=ROOT/'target/native/cuda/lp_pdhg_quant.cubin';build=json.loads(image.with_suffix('.build.json').read_text())
 if build['source_sha256']!=file_hash(ROOT/'cuda/lp_pdhg_quant/lp_pdhg_quant.cu') or build['image_sha256']!=file_hash(image) or '-fmad=false' not in build['command'] or '-ftz=false' not in build['command']:raise ValueError('quant source/image/flags')
 dump='/usr/local/cuda/bin/cuobjdump';resources=subprocess.check_output([dump,'--dump-resource-usage',str(image)],text=True);sass=subprocess.check_output([dump,'--dump-sass',str(image)],text=True)
 entries=re.findall(r'Function\s+(\w+):\s*REG:(\d+)\s+STACK:(\d+)\s+SHARED:(\d+)\s+LOCAL:(\d+)',resources)
 if len(entries)!=1 or entries[0][0]!='quant_product' or int(entries[0][1])>128 or any(int(x) for x in entries[0][2:]):raise ValueError('quant kernel/resource admission')
 counts=instruction_counts(sass)
 if any('HFMA2' in line and not re.search(r'HFMA2 R\d+, -RZ, RZ,',line) for line in sass.splitlines()):raise ValueError('nonconstant half arithmetic')
 if any('FTZ' in k or 'FFMA' in k or 'DFMA' in k for k in counts) or any(not any(k.startswith(op) for k in counts) for op in ['FMUL','FADD','DMUL','DADD']):raise ValueError('quant arithmetic instruction admission')
 d=ROOT/'artifacts/gpup-quant-v1/admission';d.mkdir(parents=True,exist_ok=True);(d/'quant.sass.txt').write_text(sass);(d/'quant.resources.txt').write_text(resources);v=dict(status='passed',gpu_seconds=0,image_sha256=file_hash(image),source_sha256=build['source_sha256'],registers=int(entries[0][1]),stack_bytes=0,local_bytes=0,spill_bytes=0,instruction_counts=dict(counts),sass_sha256=file_hash(d/'quant.sass.txt'),resources_sha256=file_hash(d/'quant.resources.txt'));write_json(d/'instruction-audit.json',v);print(v)
if __name__=='__main__':main()
