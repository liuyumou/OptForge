"""Same-filesystem isolated replay; preserve the failed cross-device attempt."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from lp_checker2_common import BASE,ROOT,load,put,ref,require
from lp_checker2_evidence import INDEX


def run():
    failed=BASE/'resources/portable.settlement.json'
    require(load(failed)['status']=='refused','prior setup failure missing')
    index=load(INDEX)
    # The temporary checkout contains only tools and evidence. Its own artifacts
    # directory is absent; the frozen reader resolves every ROOT-relative input
    # within this checkout. Using the same filesystem permits immutable hardlinks.
    with tempfile.TemporaryDirectory(prefix='portable-v2-',dir=BASE) as directory:
        root=Path(directory);(root/'tools').mkdir()
        for path in (ROOT/'tools').glob('*.py'):shutil.copy2(path,root/'tools'/path.name)
        for path in [INDEX]+[ROOT/p['path'] for p in index['parts']]:
            target=root/path.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True);os.link(path,target)
        require(not (root/'artifacts').exists(),'portable original artifacts exist')
        command=[sys.executable,'-c','import json,sys;sys.path.insert(0,"tools");from lp_checker2_evidence import verify;print(json.dumps(verify(False)))']
        result=subprocess.run(command,cwd=root,check=True,capture_output=True,text=True,
                              env=os.environ|{'CUDA_VISIBLE_DEVICES':'','PYTHONDONTWRITEBYTECODE':'1'})
        value=json.loads(result.stdout)
        require(not (root/'artifacts').exists() and value['status']=='passed','isolated replay differs')
    put(BASE/'portable.json',dict(status='passed',original_artifacts_absent=True,result=value,
        verifier=ref(ROOT/'tools/lp_checker2_evidence.py'),publisher=ref(Path(__file__).resolve()),archive=ref(INDEX),
        prior_failed_setup=ref(failed),resolution='same-filesystem temporary checkout; frozen reader and archived bytes unchanged'))
    print(value,flush=True)

if __name__=='__main__':run()
