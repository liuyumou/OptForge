"""Compile-only instruction, dependency and buffer-contract admission for GPUP-7R."""
import re,subprocess,collections
from lp_protocol import ROOT,read_json,write_json,file_hash
def instruction_counts(sass):
 counts=collections.Counter()
 for body in re.split(r'Function\s*:\s*\w+',sass)[1:]:
  lines=re.findall(r'^\s*/\*([0-9a-fA-F]+)\*/([^\n]*)',body,re.M)
  addresses={int(a,16) for a,_ in lines}
  for _,line in lines:
   m=re.fullmatch(r'\s*(?:@!?(?:U?P\d+|U?PT)\s+)?([A-Z][A-Z0-9_.]*)(?:\s+[^;]*)?;.*',line)
   if not m or re.fullmatch(r'U?[RP]\d+',m[1]):raise ValueError('unparsed resident instruction')
   op=m[1];counts[op]+=1
   if 'ATOM' in op or 'RED.' in op:
    if op!='ATOMG.E.CAS.STRONG.GPU':raise ValueError('unauthorized atomic '+op)
   if op.startswith(('CALL','JCAL')):
    target=re.search(r'CALL\.REL\.NOINC 0x([0-9a-fA-F]+)',line)
    if not target or int(target[1],16) not in addresses:raise ValueError('nonlocal resident arithmetic call')
 if not counts:raise ValueError('empty resident instructions')
 return counts
def main():
 image=ROOT/'target/native/cuda/lp_pdhg_quant_resident.cubin';build=read_json(image.with_suffix('.build.json'));source=ROOT/'cuda/lp_pdhg_quant_resident/lp_pdhg_quant_resident.cu'
 if build['source_sha256']!=file_hash(source) or build['image_sha256']!=file_hash(image) or any(file_hash(ROOT/p)!=sha for p,sha in build['included_sources'].items()) or '-fmad=false' not in build['command'] or '-ftz=false' not in build['command'] or max(build['registers'])>128 or any(a!='0' or b!='0' for a,b in build['spills']):raise ValueError('resident source/resource/flags differ')
 dump='/usr/local/cuda/bin/cuobjdump';resources=subprocess.check_output([dump,'--dump-resource-usage',str(image)],text=True);sass=subprocess.check_output([dump,'--dump-sass',str(image)],text=True);counts=instruction_counts(sass)
 ptx=subprocess.check_output(['/usr/local/cuda/bin/nvcc','--ptx','-arch=sm_120','-O3','-lineinfo','-fmad=false','-ftz=false','-o','-',str(source)],text=True)
 if re.search(r'\b(?:fma\.|\w+\.ftz\.)',ptx) or any('FTZ' in k and k!='F2I.FTZ.U32.TRUNC.NTZ' for k in counts):raise ValueError('resident source contraction/FTZ instruction')
 # ptxas implements div.rn.f64 with local FMA sequences. These implement one
 # correctly rounded division; PTX proves no product/reduction contraction.
 if 'div.rn.f64' not in ptx:raise ValueError('correctly rounded division missing')
 if any(not any(k.startswith(op) for k in counts) for op in ['FMUL','FADD','DMUL','DADD']):raise ValueError('resident arithmetic body missing')
 names=set(re.findall(r'Function\s*:\s*(\w+)',sass));required={'qr_product','qr_norm','qr_primal','qr_dual','qr_collect','qr_reset','qr_begin','qr_tuned_spmv','spmv_warp32','primal_step','dual_step','halpern'}
 if not required<=names:raise ValueError('resident kernel symbols missing '+str(required-names))
 d=ROOT/'artifacts/gpup-quant-resident-v1/instruction-admission';d.mkdir(parents=True,exist_ok=True);(d/'resident.sass.txt').write_text(sass);(d/'resident.resources.txt').write_text(resources);(d/'resident.ptx.txt').write_text(ptx)
 result=dict(status='passed',gpu_seconds=0,source_sha256=file_hash(source),image_sha256=file_hash(image),max_registers=max(build['registers']),spill_bytes=0,instruction_counts=dict(counts),sass_sha256=file_hash(d/'resident.sass.txt'),resources_sha256=file_hash(d/'resident.resources.txt'),functions=sorted(names),ptx_sha256=file_hash(d/'resident.ptx.txt'),division_lowering='local FMA sequences implement PTX div.rn.f64; PTX has no fma or ftz',integer_conversion='F2I.FTZ.U32.TRUNC.NTZ truncates all FP32 subnormals to integer zero, as PTX cvt.rzi requires; no floating arithmetic FTZ');write_json(d/'instruction-audit.json',result);print({k:v for k,v in result.items() if k not in ['instruction_counts','functions']})
if __name__=='__main__':main()
