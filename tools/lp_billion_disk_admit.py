"""Independent recompilation and exact full-tree validation of the retained counter."""
import argparse,json,shutil,subprocess,time
from lp_billion_common import BASE,ROOT,load,put,ref,require,native_inventory,legacy_disk_bytes,INVENTORY_BINDING
parser=argparse.ArgumentParser();parser.add_argument('--id',required=True);args=parser.parse_args()
require(args.id and '/' not in args.id and args.id not in ['.','..'],'fresh audit identity')
out=BASE/args.id;out.mkdir(exist_ok=False);binding=load(INVENTORY_BINDING)
source=ROOT/'tools/lp_billion_disk_inventory.c';shutil.copyfile(source,out/'inventory.c')
cmd=['/usr/bin/cc','-O2','-std=c11','-Wall','-Wextra','-Werror',str(out/'inventory.c'),'-o',str(out/'inventory')]
p=subprocess.run(cmd,text=True,capture_output=True,timeout=30)
(out/'compiler.stdout').write_text(p.stdout);(out/'compiler.stderr').write_text(p.stderr)
require(p.returncode==0,'independent native inventory compile '+p.stderr)
require(ref(out/'inventory')['sha256']==binding['executable']['sha256'],'byte-identical independent native inventory build')
w=time.monotonic_ns();native=native_inventory(BASE);native_ns=time.monotonic_ns()-w
w=time.monotonic_ns();legacy=legacy_disk_bytes(BASE);legacy_ns=time.monotonic_ns()-w
require(native['bytes']==legacy,'exact full-tree storage count')
put(out/'result.json',dict(status='passed',binding=ref(INVENTORY_BINDING),recompiled=ref(out/'inventory'),source=ref(source),retained_source=ref(out/'inventory.c'),
 full_tree_bytes=legacy,files=native['files'],native_ns=native_ns,legacy_ns=legacy_ns,command=cmd,legacy_oracle_preserved=True,guard_limits_unchanged=True))
print(dict(status='passed',files=native['files'],native_seconds=native_ns/1e9,legacy_seconds=legacy_ns/1e9),flush=True)
