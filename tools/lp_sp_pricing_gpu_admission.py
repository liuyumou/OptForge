"""Final candidate binding: full quality matrix plus all four sanitizer smokes."""
import json
from pathlib import Path
import subprocess
import sys
from lp_sp_pricing_budget import binding, put, ROOT, BASE


def sources(library):
    return [binding(p) for p in [library, ROOT/"research/lp-sp-pricing/src/lib.rs",
        ROOT/"research/lp-sp-pricing/native/batch.cu", ROOT/"research/lp-sp-pricing/build.rs",
        ROOT/"research/lp-sp-pricing/python/sp_pricing/gpu.py",
        ROOT/"research/lp-sp-pricing/python/sp_pricing/geometry.py",
        ROOT/"research/lp-sp-pricing/python/sp_pricing/lp.py",
        ROOT/"research/lp-sp-pricing/python/sp_pricing/exact.py",
        ROOT/"research/lp-sp-pricing/python/sp_pricing/native_auxiliary.py",
        ROOT/"research/lp-sp-pricing/target/cpu/libsp_auxiliary.so"]]


def validate(library, receipt=BASE/"gpu-admission-v5.json"):
    data = json.loads(receipt.read_text())
    if data["status"] != "passed" or data["sources"] != sources(library):
        raise RuntimeError("candidate device admission does not bind current sources")
    for item in data["evidence"]:
        if binding(item["path"]) != item:
            raise RuntimeError("candidate admission evidence changed")


def main():
    identity = sys.argv[1]
    library = ROOT/"research/lp-sp-pricing/target/release/liblp_sp_pricing.so"
    quality = BASE/(identity+"-quality.json")
    subprocess.run([sys.executable, "-B", str(ROOT/"tools/lp_sp_pricing_gpu_quality.py"), str(quality)], check=True)
    subprocess.run([sys.executable, "-B", str(ROOT/"tools/lp_sp_pricing_sanitizers.py"), identity+"-sanitizers"], check=True)
    evidence = [binding(quality), binding(BASE/(identity+"-sanitizers")/"result.json")]
    for name in ("memcheck", "racecheck", "initcheck", "synccheck"):
        evidence += [binding(BASE/(identity+"-sanitizers")/(name+suffix)) for suffix in (".json", ".log")]
    put(BASE/(identity+".json"), dict(status="passed", sources=sources(library), evidence=evidence))


if __name__ == "__main__":
    main()
