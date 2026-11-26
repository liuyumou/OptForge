"""Standalone CPU sanitizers and retained native market source/binary binding."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
from lp_sp_pricing_budget import ROOT, BASE, binding, put


if __name__ == "__main__":
    out=BASE/sys.argv[1]
    out.mkdir(exist_ok=False)
    source=ROOT/"research/lp-sp-pricing/native/market.cpp"
    test=ROOT/"research/lp-sp-pricing/native/market_test.cpp"
    executable=out/"market-sanitized"
    command=["g++","-std=c++17","-O1","-g","-fsanitize=address,undefined","-fno-omit-frame-pointer",
             str(source),str(test),"-o",str(executable)]
    subprocess.run(command,check=True)
    with (out/"sanitizer.log").open("x") as stream:
        subprocess.run([str(executable)],stdout=stream,stderr=subprocess.STDOUT,check=True)
    library=ROOT/"research/lp-sp-pricing/target/cpu/libsp_market.so"
    shutil.copyfile(library,out/library.name)
    put(out/"binding.json",dict(status="passed",source=binding(source),test=binding(test),
        library=binding(library),retained_library=binding(out/library.name),sanitizer=binding(executable),
        log=binding(out/"sanitizer.log"),command=command))
    print(json.dumps(dict(status="passed",native_certificate_cases=96)))
