"""Independently settle portable replay before final evidence aggregation."""
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from lp_mixed2_confirm_common import BASE, ROOT, load, put, ref, require
from lp_mixed2_confirm_analysis import ANALYSIS, ARCHIVE
from lp_mixed2_confirm_evidence import INDEX as EVIDENCE


def main():
    sources=sorted((ROOT/'tools').glob('*.py'))
    files=[ANALYSIS,ARCHIVE,EVIDENCE]+[ROOT/r['path'] for index in (ARCHIVE,EVIDENCE) for r in load(index)['parts']]
    bindings=[ref(p) for p in sources+files]
    with tempfile.TemporaryDirectory(prefix='mixed2-confirm-portable-v4-') as temp:
        dest=Path(temp);(dest/'tools').mkdir()
        for p in sources:shutil.copy2(p,dest/'tools'/p.name)
        for p in files:
            target=dest/p.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True)
            try:target.hardlink_to(p)
            except OSError:shutil.copy2(p,target)
        for tool,action in [('analysis','verify'),('evidence','portable')]:
            subprocess.run([sys.executable,'-B',f'tools/lp_mixed2_confirm_{tool}.py',action],cwd=dest,check=True)
        require(not (dest/'artifacts').exists(),'portable replay depended on artifacts')
    require(bindings==[ref(p) for p in sources+files],'portable source/evidence changed during replay')
    put(BASE/'portable-v4.json',dict(status='passed',bindings=bindings,source=ref(__file__),original_artifacts_absent=True))
    print('Separately recorded portable replay passed',flush=True)


if __name__=='__main__':main()
