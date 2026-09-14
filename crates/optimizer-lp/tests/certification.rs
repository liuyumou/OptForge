//! Independent regression cases for conservative LP certification.

use optimizer_core::{
    Bound, Constraint, Domain, LinearTerm, Model, ModelDocument, Objective, ObjectiveSense,
    SCHEMA_VERSION, Variable,
};
use optimizer_lp::{LinearProgram, NoBound, certify};

fn finite(value: f64) -> Bound {
    Bound::Finite { value }
}

fn cancellation(sense: ObjectiveSense, free: bool) -> LinearProgram {
    let sign = if sense == ObjectiveSense::Minimize {
        1.0
    } else {
        -1.0
    };
    let model = Model::new(ModelDocument {
        schema_version: SCHEMA_VERSION,
        model_id: "reduced-cost-cancellation".into(),
        variables: vec![
            Variable {
                id: 0,
                domain: Domain::Continuous,
                lower: finite(-3e16),
                upper: finite(3e16),
            },
            Variable {
                id: 1,
                domain: Domain::Continuous,
                lower: if free {
                    Bound::NegativeInfinity
                } else {
                    finite(-1e16)
                },
                upper: if free {
                    Bound::PositiveInfinity
                } else {
                    finite(1e16)
                },
            },
        ],
        constraints: vec![Constraint {
            id: 0,
            lower: finite(0.0),
            upper: finite(0.0),
            terms: vec![
                LinearTerm {
                    variable_id: 0,
                    coefficient: 1.0,
                },
                LinearTerm {
                    variable_id: 1,
                    coefficient: 3.0,
                },
            ],
        }],
        objective: Objective {
            sense,
            offset: 0.0,
            terms: vec![
                LinearTerm {
                    variable_id: 0,
                    coefficient: sign * 0.1,
                },
                LinearTerm {
                    variable_id: 1,
                    coefficient: sign * 0.300_000_000_000_000_04,
                },
            ],
        },
    })
    .unwrap();
    LinearProgram::new(&model).unwrap()
}

#[test]
fn rounded_zero_reduced_cost_does_not_erase_uncertainty() {
    // Exact rational evaluation of the stored binary64 coefficients at
    // (3e16, -1e16). The numerator fits in 53 bits and the denominator is 2^39,
    // so this division is exact, unlike recomputing the cancelling products.
    let exact = -152_587_890_625.0 / 549_755_813_888.0;
    for sense in [ObjectiveSense::Minimize, ObjectiveSense::Maximize] {
        let program = cancellation(sense, false);
        let result = certify(&program, &[0.1]).unwrap();
        match sense {
            ObjectiveSense::Minimize => assert!(result.bound <= exact, "{result:?}"),
            ObjectiveSense::Maximize => assert!(result.bound >= -exact, "{result:?}"),
        }
        assert!(result.allowance > 0.0);
    }
}

#[test]
fn uncertain_reduced_cost_with_a_free_variable_refuses_a_finite_bound() {
    assert_eq!(
        certify(&cancellation(ObjectiveSense::Minimize, true), &[0.1]),
        Err(NoBound::UnboundedVariable { variable_id: 1 })
    );
}

fn float(raw: &serde_json::Value) -> f64 {
    f64::from_bits(u64::from_str_radix(raw.as_str().unwrap(), 16).unwrap())
}

fn values(raw: &serde_json::Value) -> Vec<f64> {
    raw.as_array().unwrap().iter().map(float).collect()
}

fn range(raw: &serde_json::Value) -> (Bound, Bound) {
    let side = |index: usize| {
        if raw[index].is_null() {
            if index == 0 {
                Bound::NegativeInfinity
            } else {
                Bound::PositiveInfinity
            }
        } else {
            finite(float(&raw[index]))
        }
    };
    (side(0), side(1))
}

fn oracle_program(case: &serde_json::Value) -> LinearProgram {
    let sense = if case["sense"] == "minimize" {
        ObjectiveSense::Minimize
    } else {
        ObjectiveSense::Maximize
    };
    let cost = values(&case["cost"]);
    let variables = (0..cost.len())
        .map(|i| {
            let (lower, upper) = if case["columns"].is_array() {
                range(&case["columns"][i])
            } else {
                // Gap fixtures fix the candidate, so all bounds except the
                // deliberately inconsistent one are valid for an actual LP.
                let value = float(&case["primal"][i]);
                (finite(value), finite(value))
            };
            Variable {
                id: i as u32,
                domain: Domain::Continuous,
                lower,
                upper,
            }
        })
        .collect();
    let constraints = case["matrix"]
        .as_array()
        .map(|matrix| {
            matrix
                .iter()
                .enumerate()
                .map(|(i, row)| {
                    let (lower, upper) = range(&case["rows"][i]);
                    Constraint {
                        id: i as u32,
                        lower,
                        upper,
                        terms: values(row)
                            .iter()
                            .enumerate()
                            .filter(|(_, v)| **v != 0.0)
                            .map(|(j, value)| LinearTerm {
                                variable_id: j as u32,
                                coefficient: *value,
                            })
                            .collect(),
                    }
                })
                .collect()
        })
        .unwrap_or_default();
    let model = Model::new(ModelDocument {
        schema_version: SCHEMA_VERSION,
        model_id: case["name"].as_str().unwrap().into(),
        variables,
        constraints,
        objective: Objective {
            sense,
            offset: float(&case["offset"]),
            terms: cost
                .iter()
                .enumerate()
                .filter(|(_, v)| **v != 0.0)
                .map(|(j, value)| LinearTerm {
                    variable_id: j as u32,
                    coefficient: *value,
                })
                .collect(),
        },
    })
    .unwrap();
    LinearProgram::new(&model).unwrap()
}

#[test]
fn certificates_bound_independent_exact_rational_weak_duality() {
    let fixture: serde_json::Value = serde_json::from_str(include_str!(
        "../../../tests/regression/lp-certification-oracle.json"
    ))
    .unwrap();
    for case in fixture["programs"].as_array().unwrap() {
        let program = oracle_program(case);
        let certificate = certify(&program, &values(&case["dual"]));
        if case["exact_bound"].is_null() {
            assert!(
                matches!(certificate, Err(NoBound::UnboundedVariable { .. })),
                "{case}: {certificate:?}"
            );
        } else if let Ok(certificate) = certificate {
            let exact = float(&case["exact_bound"]);
            assert!(certificate.allowance.is_finite() && certificate.allowance >= 0.0);
            match program.sense() {
                ObjectiveSense::Minimize => {
                    assert!(certificate.bound <= exact, "{case}: {certificate:?}")
                }
                ObjectiveSense::Maximize => {
                    assert!(certificate.bound >= exact, "{case}: {certificate:?}")
                }
            }
        } else {
            assert!(
                !case["required"].as_bool().unwrap(),
                "{case}: {certificate:?}"
            );
            assert!(
                matches!(certificate, Err(NoBound::NonfiniteArithmetic)),
                "{case}: {certificate:?}"
            );
        }
    }
}

#[test]
fn gap_closure_and_diagnostics_cover_the_exact_objective() {
    let fixture: serde_json::Value = serde_json::from_str(include_str!(
        "../../../tests/regression/lp-certification-oracle.json"
    ))
    .unwrap();
    for case in fixture["gaps"].as_array().unwrap() {
        let program = oracle_program(case);
        let result = optimizer_lp::certify::assess_gap(
            &program,
            &values(&case["primal"]),
            float(&case["bound"]),
            optimizer_core::Tolerances {
                absolute: float(&case["absolute"]),
                relative: float(&case["relative"]),
                integrality: 0.0,
            },
        );
        if let Some(gap) = result {
            assert!(
                gap.upper >= float(&case["exact_gap_upper"]),
                "{case}: {gap:?}"
            );
            assert!(
                !gap.closed || case["exact_closes"].as_bool().unwrap(),
                "false closure: {case}: {gap:?}"
            );
            assert!(
                !case["must_close"].as_bool().unwrap() || gap.closed,
                "missed exact closure: {case}: {gap:?}"
            );
        } else {
            assert!(!case["required"].as_bool().unwrap(), "{case}");
        }
    }
}
