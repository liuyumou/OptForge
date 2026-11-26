"""Native admission: all widths, formats and arithmetic modes, with exact labels."""
import argparse
from fractions import Fraction as Q
import hashlib
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/"research/lp-sp-pricing/python"))
from sp_pricing.exact import Work, encode
from sp_pricing.geometry import paired_space, LabelOracle
from sp_pricing.calibration import DirectCalibration
from sp_pricing.gpu import GpuBatch, accept_proposal, MODES


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--library", type=Path, default=ROOT/"research/lp-sp-pricing/target/release/liblp_sp_pricing.so")
    parser.add_argument("--sanitizer-smoke", action="store_true")
    args = parser.parse_args()
    work = Work(max_operations=10_000_000, seconds=180)
    # Cases include both known sides, coupling, cancellation, and half prices.
    cases = [([[1, 0, 0, 0], [0, 1, 0, 0]], [Q(0)]*4),
             ([[1, -2, 0, 3], [0, 1, 1, -1]], [Q(-1, 2), Q(1, 2), Q(0), Q(0)])]
    if args.sanitizer_smoke:
        cases = cases[:1]
    rows = []
    for case, (space, prices) in enumerate(cases):
        cal = DirectCalibration(paired_space(space, work), work).query(prices)
        oracle = LabelOracle(cal["basis"], cal["H"], cal["epsilon"], work)
        exact, _ = oracle.labels(broadcast=False)
        for sparse in (False, True):
            with GpuBatch(args.library, oracle.b, sparse) as engine:
                for mode in MODES:
                    for width in ((32,) if args.sanitizer_smoke else (1, 8, 32, 64)):
                        targets = [i%oracle.n for i in range(width)]
                        result = engine.propose(targets, oracle.h, oracle.epsilon,
                                                steps=64 if args.sanitizer_smoke else 256, mode=mode)
                        accepted = 0
                        for q, target in enumerate(targets):
                            proof = accept_proposal(oracle, target, result["x"][q], result["dual"][q])
                            for index, sign in proof.get("established", {}).items():
                                if exact[index] != sign:
                                    raise AssertionError("GPU proposal contradicted independent exact optimum")
                            accepted += proof["accepted"]
                        if case == 0 and not accepted:
                            raise AssertionError("no GPU certificate on diagonal admission case")
                        rows.append(dict(case=case, sparse=sparse, mode=mode, width=width,
                            accepted_targets=accepted, targets=width, preparation_ns=engine.preparation_ns,
                            elapsed_ns=result["elapsed_ns"], device_iteration_ms=result["device_iteration_ms"]))
                        slots=[i%(2*oracle.n) for i in range(width)]
                        signed=engine.propose(slots,oracle.h,oracle.epsilon,
                            steps=64 if args.sanitizer_smoke else 256,mode=mode,slot_targets=True)
                        checked=0
                        for q,slot in enumerate(slots):
                            proof=accept_proposal(oracle,slot//2,signed['x'][q],signed['dual'][q])
                            for index,sign in proof.get('established',{}).items():
                                if exact[index]!=sign:raise AssertionError('signed-slot certificate contradicted exact optimum')
                            checked+=proof['accepted']
                        rows.append(dict(case=case,sparse=sparse,mode=mode,width=width,signed_slots=True,
                            accepted_targets=checked,targets=width,preparation_ns=engine.preparation_ns,
                            elapsed_ns=signed['elapsed_ns'],device_iteration_ms=signed['device_iteration_ms']))
                # Validation must reject before a native out-of-bounds launch.
                try:
                    engine.propose([oracle.n], oracle.h, oracle.epsilon, steps=1)
                except RuntimeError:
                    pass
                else:
                    raise AssertionError("invalid target accepted")
                try:engine.propose([2*oracle.n],oracle.h,oracle.epsilon,steps=1,slot_targets=True)
                except RuntimeError:pass
                else:raise AssertionError('invalid signed slot accepted')
    receipt = dict(status="passed", rows=rows, comparisons=len(rows),
        native_sha256=hashlib.sha256(args.library.read_bytes()).hexdigest(),
        tensor_cores=False, original_lp_benchmark=False)
    with args.output.open("x") as stream:
        json.dump(receipt, stream, indent=2, sort_keys=True)
    print(json.dumps(dict(status="passed", comparisons=len(rows),
                         accepted=sum(r["accepted_targets"] for r in rows))))


if __name__ == "__main__":
    main()
