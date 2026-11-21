"""CPU-only retained build and exact checks of native storage inventory."""
import os,subprocess,time,tempfile,shutil,json
from pathlib import Path
from lp_billion_common import BASE,ROOT,load,put,ref,require,disk_bytes
out=BASE/'disk-inventory-build-v1';out.mkdir(exist_ok=False)
source=ROOT/'tools/lp_billion_disk_inventory.c';shutil.copyfile(source,out/'inventory.c')
cmd=['/usr/bin/cc','-O2','-std=c11','-Wall','-Wextra','-Werror',str(out/'inventory.c'),'-o',str(out/'inventory')]
p=subprocess.run(cmd,text=True,capture_output=True,timeout=30)
(out/'compiler.stdout').write_text(p.stdout);(out/'compiler.stderr').write_text(p.stderr)
require(p.returncode==0,'native inventory compile '+p.stderr)
with tempfile.TemporaryDirectory(prefix='lp-inventory-') as tmp:
 root=Path(tmp);(root/'sub').mkdir();(root/'a').write_bytes(b'a'*37);os.link(root/'a',root/'sub/hard');(root/'sub/b').write_bytes(b'12345')
 (root/'link').symlink_to(root/'a');(root/'dirlink').symlink_to(root/'sub',target_is_directory=True);os.mkfifo(root/'fifo')
 proof=json.loads(subprocess.check_output([out/'inventory',root],text=True));require(proof==dict(bytes=42,files=3),'exact files/hardlink/symlink/FIFO fixture')
start=time.monotonic_ns();native=json.loads(subprocess.check_output([out/'inventory',BASE],text=True));native_ns=time.monotonic_ns()-start
start=time.monotonic_ns();legacy=disk_bytes();legacy_ns=time.monotonic_ns()-start
require(native['bytes']==legacy,'exact full owned-tree inventory')
put(out/'result.json',dict(status='passed',source=ref(source),retained_source=ref(out/'inventory.c'),executable=ref(out/'inventory'),command=cmd,
 compiler=subprocess.check_output(['/usr/bin/cc','--version'],text=True).splitlines()[0],full_tree_bytes=legacy,native_ns=native_ns,legacy_ns=legacy_ns,fixture=proof,compiled_under_existing_guard=True))
print(dict(status='passed',native_seconds=native_ns/1e9,legacy_seconds=legacy_ns/1e9,bytes=legacy),flush=True)
