"""ASan/UBSan and retained exact-native runtime/source binding."""
import json
import shutil
import subprocess
import sys
from lp_sp_pricing_budget import ROOT,BASE,binding,put

if __name__=='__main__':
    out=BASE/sys.argv[1];out.mkdir(exist_ok=False)
    source=ROOT/'research/lp-sp-pricing/native/auxiliary.cpp'
    test=source.with_name('auxiliary_test.cpp');runtime='/usr/lib/x86_64-linux-gnu/libgmp.so.10.4.1'
    executable=out/'auxiliary-sanitized'
    command=['g++','-std=c++17','-O1','-g','-fsanitize=address,undefined','-fno-omit-frame-pointer',str(source),str(test),runtime,'-o',str(executable)]
    subprocess.run(command,check=True)
    with (out/'sanitizer.log').open('x') as stream:subprocess.run([str(executable)],stdout=stream,stderr=subprocess.STDOUT,check=True)
    library=ROOT/'research/lp-sp-pricing/target/cpu/libsp_auxiliary.so';shutil.copyfile(library,out/library.name)
    put(out/'binding.json',dict(status='passed',sources=[binding(source),binding(test),binding(source.with_name('gmp_abi.h'))],
        runtime=binding(runtime),library=binding(library),retained_library=binding(out/library.name),
        sanitizer=binding(executable),log=binding(out/'sanitizer.log')))
    print(json.dumps(dict(status='passed',cases=96)))
