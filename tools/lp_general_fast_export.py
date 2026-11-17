"""Compact complete development results; raw vectors and trace databases stay local."""
from pathlib import Path
from lp_general_common import BASE,ROOT,load,put,ref


def main():
    source=BASE/"fast-results-final-v1.json"
    result=load(source);result["full_analysis"]=ref(source)
    result["profile_results"]={f"v{i}":ref(BASE/f"fast-profile-report-v{i}.json") for i in [1,2,3,5]}
    result["idle_observations"]=[ref(BASE/f"fast-idle-v{i}/result.json") for i in [1,2]]
    result["admission"]=ref(BASE/"fast-admission-v5.json")
    result["exporter"]=ref(__file__)
    put(ROOT/"docs/benchmarks/lp-general-fast-results.json",result)
    (ROOT/"docs/benchmarks/lp-general-fast-profile-results.json").write_bytes((BASE/"fast-profile-report-v5.json").read_bytes())
    print("800 cells and 12 final timelines exported; no raw vectors or trace databases in Git",flush=True)


if __name__=="__main__":main()
