"""Independent exact rational original-model checker; no candidate imports.

This certificate tier is distinct from the historical binary64 1e-9 checker.
It proves returned answers, never search complexity or algorithm completeness.
"""
import argparse
from fractions import Fraction
import hashlib
import json
import math
import re
from pathlib import Path


def number(value):
    if isinstance(value, bool):
        raise ValueError("boolean coefficient")
    if isinstance(value, dict):
        if set(value) != {"numerator", "denominator"}:
            raise ValueError("rational fields")
        for entry in value.values():
            if type(entry) is int:
                continue
            if not isinstance(entry, str) or re.fullmatch("[+-]?[0-9]+", entry) is None:
                raise ValueError("noninteger rational field")
        return Fraction(int(value["numerator"]), int(value["denominator"]))
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError("nonfinite coefficient")
    return Fraction(value)


def verify(model, endpoint):
    a = [[number(v) for v in row] for row in model["A"]]
    b, c = [[number(v) for v in model[key]] for key in ("b", "c")]
    if len(a) != len(b) or any(len(row) != len(c) for row in a):
        raise ValueError("original dimensions")
    if model.get("sense", "max") != "max":
        raise ValueError("canonical checker expects maximize")
    def inner(left, right):
        if len(left) != len(right):
            raise ValueError("witness dimension")
        return sum((u*v for u, v in zip(left, right)), Fraction())
    cert = endpoint.get("certificate", endpoint)
    status = cert["status"]
    if status not in ("optimal", "infeasible", "unbounded"):
        return dict(accepted=False, reason="no_mathematical_certificate")
    if status != "infeasible":
        x = [number(v) for v in cert["x"]]
        if len(x) != len(c) or any(inner(row, x) > rhs for row, rhs in zip(a, b)):
            return dict(accepted=False, reason="primal_infeasible")
    if status != "unbounded":
        y = [number(v) for v in cert["y"]]
        if len(y) != len(b) or any(v < 0 for v in y):
            return dict(accepted=False, reason="dual_sign_or_dimension")
        for j in range(len(c)):
            expected = c[j] if status == "optimal" else Fraction()
            if inner([row[j] for row in a], y) != expected:
                return dict(accepted=False, reason="dual_equation")
        dual = inner(b, y)
        if status == "infeasible" and dual >= 0:
            return dict(accepted=False, reason="farkas_sign")
        if status == "optimal" and inner(c, x) != dual:
            return dict(accepted=False, reason="exact_gap")
        if status == "optimal" and "value" in cert and number(cert["value"]) != inner(c, x):
            return dict(accepted=False, reason="reported_objective")
    if status == "unbounded":
        ray = [number(v) for v in cert["ray"]]
        if len(ray) != len(c) or any(inner(row, ray) > 0 for row in a) or inner(c, ray) <= 0:
            return dict(accepted=False, reason="improving_ray")
    strict = None
    if status == "optimal":
        strict = all(rhs-inner(row, x)+v > 0 for row, rhs, v in zip(a, b, y))
    return dict(accepted=True, certificate_tier="exact_rational_original",
                outcome=status, strict_complementarity=strict,
                historical_1e9_checker_run=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("model", type=Path)
    parser.add_argument("endpoint", type=Path)
    args = parser.parse_args()
    try:
        result = verify(json.loads(args.model.read_text()), json.loads(args.endpoint.read_text()))
    except (ValueError, TypeError, KeyError, ZeroDivisionError) as error:
        result = dict(accepted=False, reason=str(error))
    result["model_sha256"] = hashlib.sha256(args.model.read_bytes()).hexdigest()
    result["endpoint_sha256"] = hashlib.sha256(args.endpoint.read_bytes()).hexdigest()
    print(json.dumps(result, sort_keys=True))
    return 0 if result["accepted"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
