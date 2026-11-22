"""Independent read-only validation of artifacts retained after interrupted sealing."""
from lp_billion_common import BASE,ROOT,load,put,ref,resolve,require
failed=BASE/'resources/gpu-pack-seal-v1.settlement.json';s=load(failed)
require(s['status']=='refused' and s['cleanup_empty'] and not s['overrun'],'exact retained seal interruption')
require(load(resolve(s['resource']))['result']['reason']=='lost_coordinator_heartbeat','retained heartbeat failure')
quality=BASE/'resources/gpu-pack-quality-v7.settlement.json';q=load(quality)
require(q['status']=='passed' and q['cleanup_empty'] and not q['overrun'],'complete native candidate acceptance')
image=BASE/'image-v10';binding=load(image/'binding.json')
require(binding['quality']==ref(BASE/'gpu-pack-quality-v7/result.json') and binding['source_manifest']==ref(BASE/'sources/gpu-pack-quality-v7/manifest.json'),'source-specific build identity')
for item in binding['files'].values():resolve(item)
for original,name in [(BASE/'target/release/billion','executor'),(BASE/'target/release/packing_check','packing-check'),(BASE/'image-v9/tensor.cubin','tensor.cubin'),(BASE/'image-v9/prepare.cubin','prepare.cubin'),(BASE/'gpu-pack-quality-v7/pack.cubin','pack.cubin')]:
 require(ref(original)['sha256']==ref(image/name)['sha256'],'exact retained artifact '+name)
for item in load(resolve(binding['source_manifest']))['sources']:
 if item['original']['path'].endswith(('.rs','.cu')) or item['original']['path'].split('/')[-1].startswith('Cargo.'):
  resolve(item['original']);resolve(item['retained'])
put(BASE/'gpu-pack-seal-audit-v1/result.json',dict(status='passed',image=ref(image/'binding.json'),quality=ref(quality),retained_failed_seal=ref(failed),source=ref(__file__),protocol=ref(ROOT/'docs/specifications/SPEC-0046-amendment-62.md'),rewrote_artifacts=False))
print(dict(status='passed',files=len(binding['files']),rewrote_artifacts=False),flush=True)
