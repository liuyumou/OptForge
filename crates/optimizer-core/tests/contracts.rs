//! Independent acceptance contracts for SPEC-0001.

use optimizer_core::*;

fn finite(value: f64) -> Bound {
    Bound::Finite { value }
}

fn variable(id: u32, domain: Domain) -> Variable {
    Variable {
        id,
        domain,
        lower: Bound::NegativeInfinity,
        upper: Bound::PositiveInfinity,
    }
}

fn term(variable_id: u32, coefficient: f64) -> LinearTerm {
    LinearTerm {
        variable_id,
        coefficient,
    }
}

fn document() -> ModelDocument {
    ModelDocument {
        schema_version: 1,
        model_id: "test".into(),
        variables: vec![
            variable(2, Domain::Continuous),
            variable(9, Domain::Integer),
        ],
        constraints: vec![Constraint {
            id: 7,
            lower: finite(-2.0),
            upper: finite(3.0),
            terms: vec![term(2, 2.0), term(9, -1.0)],
        }],
        objective: Objective {
            sense: ObjectiveSense::Minimize,
            offset: 0.5,
            terms: vec![term(2, -1.0), term(9, 3.0)],
        },
    }
}

fn candidate(values: &[f64]) -> Candidate {
    Candidate {
        schema_version: 1,
        model_id: "test".into(),
        values: [2, 9]
            .into_iter()
            .zip(values)
            .map(|(variable_id, &value)| Assignment { variable_id, value })
            .collect(),
    }
}

fn exact() -> Tolerances {
    Tolerances {
        absolute: 0.0,
        relative: 0.0,
        integrality: 0.0,
    }
}

#[test]
fn structure_rejects_invalid_models_without_confusing_infeasibility() {
    let invalid: Vec<fn(&mut ModelDocument)> = vec![
        |d| d.model_id.clear(),
        |d| d.variables.push(d.variables[0].clone()),
        |d| d.constraints.push(d.constraints[0].clone()),
        |d| d.variables[0].lower = Bound::PositiveInfinity,
        |d| d.variables[0].upper = Bound::NegativeInfinity,
        |d| {
            d.variables[0].lower = finite(2.0);
            d.variables[0].upper = finite(1.0);
        },
        |d| d.variables[0].lower = finite(f64::NAN),
        |d| d.constraints[0].upper = finite(f64::INFINITY),
        |d| d.constraints[0].lower = finite(4.0),
        |d| d.constraints[0].terms.push(term(2, 0.0)),
        |d| d.constraints[0].terms.push(term(99, 1.0)),
        |d| d.constraints[0].terms[0].coefficient = f64::NEG_INFINITY,
        |d| d.objective.offset = f64::NAN,
        |d| d.objective.terms.push(term(9, 1.0)),
        |d| d.objective.terms.push(term(99, 1.0)),
        |d| d.objective.terms[0].coefficient = f64::NAN,
    ];
    for mutate in invalid {
        let mut d = document();
        mutate(&mut d);
        assert_eq!(Model::new(d).unwrap_err().kind, ErrorKind::Structural);
    }
    let mut d = document();
    d.schema_version = 2;
    assert_eq!(Model::new(d).unwrap_err().kind, ErrorKind::Document);
    let mut d = document();
    d.variables.clear();
    d.objective.terms.clear();
    d.constraints[0].terms.clear();
    d.constraints[0].lower = finite(1.0);
    let model = Model::new(d).unwrap();
    let report = model.evaluate(&candidate(&[]), exact()).unwrap();
    assert!(!report.feasible);
    assert_eq!(report.objective, 0.5);
    let mut d = model.document().clone();
    d.constraints.clear();
    assert!(
        Model::new(d)
            .unwrap()
            .evaluate(&candidate(&[]), exact())
            .unwrap()
            .feasible
    );
}

#[test]
fn canonicalization_preserves_ids_zero_terms_and_original_objective_sense() {
    let mut d = document();
    d.variables[0].lower = finite(-0.0);
    d.objective.offset = -0.0;
    d.objective.terms[0].coefficient = -0.0;
    d.objective.sense = ObjectiveSense::Maximize;
    let model = Model::new(d.clone()).unwrap();
    d.variables.reverse();
    d.constraints[0].terms.reverse();
    d.objective.terms.reverse();
    let reordered = Model::new(d).unwrap();
    assert_eq!(model.to_json().unwrap(), reordered.to_json().unwrap());
    assert!(!model.to_json().unwrap().contains("-0.0"));
    assert_eq!(model.document().objective.terms.len(), 2);
    assert_eq!(model.document().variables[1].id, 9);
    let report = model.evaluate(&candidate(&[0.0, 2.0]), exact()).unwrap();
    assert_eq!(report.objective, 6.0);
    assert_eq!(
        Model::from_json(model.to_json().unwrap().as_bytes()).unwrap(),
        model
    );
    let mut c = candidate(&[-0.0, 2.0]);
    let original = c.to_json().unwrap();
    c.values.reverse();
    assert_eq!(original, c.to_json().unwrap());
    assert_eq!(
        Candidate::from_json(original.as_bytes()).unwrap().values[0]
            .value
            .to_bits(),
        0
    );
}

#[test]
fn f64_round_trips_across_exponents_and_mantissas() {
    for exponent in (0_u64..2047).step_by(17) {
        for mantissa in [0, 1, 0x8_0000_0000_0001, 0xf_ffff_ffff_ffff] {
            for sign in [0, 1_u64 << 63] {
                let value = f64::from_bits(sign | (exponent << 52) | mantissa);
                let mut d = document();
                d.objective.offset = value;
                let model = Model::new(d).unwrap();
                let decoded = Model::from_json(model.to_json().unwrap().as_bytes()).unwrap();
                assert_eq!(
                    decoded.document().objective.offset.to_bits(),
                    if value == 0.0 { 0 } else { value.to_bits() }
                );
                let c = candidate(&[value, 0.0]);
                let decoded = Candidate::from_json(c.to_json().unwrap().as_bytes()).unwrap();
                assert_eq!(
                    decoded.values[0].value.to_bits(),
                    if value == 0.0 { 0 } else { value.to_bits() }
                );
            }
        }
    }
}

#[test]
fn strict_json_rejects_unknown_duplicate_and_unsupported_input() {
    assert!(
        serde_json::from_str::<Bound>(include_str!(
            "../../../tests/regression/infinite-bound-extra-field.json"
        ))
        .is_err()
    );
    let valid = Model::new(document()).unwrap().to_json().unwrap();
    for invalid in [
        format!("{valid} {{}}"),
        valid.replacen(
            "\"schema_version\": 1",
            "\"schema_version\": 1, \"schema_version\": 1",
            1,
        ),
        valid.replacen("\"schema_version\": 1", "\"schema_version\": 2", 1),
        valid.replacen("\"model_id\":", "\"unknown\": 0, \"model_id\":", 1),
        valid.replacen("\"continuous\"", "\"semicontinuous\"", 1),
        valid.replacen("\"minimize\"", "\"quadratic\"", 1),
        valid.replacen("\"offset\": 0.5", "\"offset\": NaN", 1),
        valid.replacen("\"offset\": 0.5", "\"offset\": 1e999", 1),
        valid.replacen(
            "\"negative_infinity\"",
            "\"negative_infinity\", \"value\": 1",
            1,
        ),
        valid.replacen(
            "\"kind\": \"finite\"",
            "\"kind\": \"finite\", \"value\": 7",
            1,
        ),
        valid.replacen(
            "\"negative_infinity\"",
            "\"negative_infinity\", \"kind\": \"negative_infinity\"",
            1,
        ),
    ] {
        assert_eq!(
            Model::from_json(invalid.as_bytes()).unwrap_err().kind,
            ErrorKind::Document,
            "{invalid}"
        );
    }
    let c = candidate(&[0.0, 0.0]).to_json().unwrap();
    for invalid in [
        format!("{c} null"),
        c.replacen("\"model_id\":", "\"extra\": 1, \"model_id\":", 1),
        c.replacen("\"value\": 0.0", "\"value\": 0.0, \"value\": 1.0", 1),
        c.replacen("\"schema_version\": 1", "\"schema_version\": 0", 1),
        c.replacen("\"value\": 0.0", "\"value\": Infinity", 1),
    ] {
        assert_eq!(
            Candidate::from_json(invalid.as_bytes()).unwrap_err().kind,
            ErrorKind::Document
        );
    }
}

#[test]
fn candidate_identity_coverage_and_tolerances_are_explicit() {
    let model = Model::new(document()).unwrap();
    let invalid: Vec<fn(&mut Candidate)> = vec![
        |c| c.model_id = "other".into(),
        |c| c.model_id.clear(),
        |c| {
            c.values.pop();
        },
        |c| c.values.push(c.values[0].clone()),
        |c| c.values[0].variable_id = 99,
        |c| c.values[0].value = f64::NAN,
        |c| c.values[1].value = f64::INFINITY,
    ];
    for mutate in invalid {
        let mut c = candidate(&[0.0, 0.0]);
        mutate(&mut c);
        assert_eq!(
            model.evaluate(&c, exact()).unwrap_err().kind,
            ErrorKind::Candidate
        );
    }
    for invalid in [f64::NAN, f64::INFINITY, -1.0] {
        for t in [
            Tolerances {
                absolute: invalid,
                ..exact()
            },
            Tolerances {
                relative: invalid,
                ..exact()
            },
            Tolerances {
                integrality: invalid,
                ..exact()
            },
        ] {
            assert_eq!(
                model.evaluate(&candidate(&[0.0, 0.0]), t).unwrap_err().kind,
                ErrorKind::Tolerance
            );
        }
    }
    assert!(
        Tolerances {
            integrality: 0.5,
            ..exact()
        }
        .validate()
        .is_err()
    );
    let before = model.to_json().unwrap();
    model.evaluate(&candidate(&[0.0, 0.0]), exact()).unwrap();
    assert_eq!(before, model.to_json().unwrap());
}

#[test]
fn exhaustive_dense_oracle_checks_objectives_domains_and_violations() {
    // Exact integer arithmetic on doubled assignments is independent of sparse f64 evaluation.
    let ids = [2, 9, 30];
    for a in -1_i64..=1 {
        for b in -1_i64..=1 {
            for c in -1_i64..=1 {
                let rows = [[a, b, c], [c, a, b]];
                for sense in [ObjectiveSense::Minimize, ObjectiveSense::Maximize] {
                    let d = ModelDocument {
                        schema_version: 1,
                        model_id: "dense".into(),
                        variables: ids
                            .into_iter()
                            .zip([Domain::Continuous, Domain::Integer, Domain::Binary])
                            .map(|(id, domain)| Variable {
                                id,
                                domain,
                                lower: finite(-1.0),
                                upper: finite(2.0),
                            })
                            .collect(),
                        constraints: rows
                            .iter()
                            .enumerate()
                            .map(|(i, row)| Constraint {
                                id: u32::try_from(i).unwrap(),
                                lower: finite(if i == 0 { -1.0 } else { 0.0 }),
                                upper: finite(if i == 0 { 2.0 } else { 0.0 }),
                                terms: ids
                                    .into_iter()
                                    .zip(row)
                                    .filter(|(_, coefficient)| **coefficient != 0)
                                    .map(|(id, &coefficient)| term(id, coefficient as f64))
                                    .collect(),
                            })
                            .collect(),
                        objective: Objective {
                            sense,
                            offset: 2.5,
                            terms: vec![term(2, 2.0), term(9, -3.0), term(30, 1.0)],
                        },
                    };
                    let model = Model::new(d).unwrap();
                    let mut reordered = model.document().clone();
                    reordered.variables.reverse();
                    reordered.constraints.reverse();
                    reordered.objective.terms.reverse();
                    for row in &mut reordered.constraints {
                        row.terms.reverse();
                    }
                    assert_eq!(
                        model.to_json().unwrap(),
                        Model::new(reordered).unwrap().to_json().unwrap()
                    );
                    for x in -2_i64..=4 {
                        for y in -2_i64..=4 {
                            for z in -2_i64..=4 {
                                let doubled = [x, y, z];
                                let candidate = Candidate {
                                    schema_version: 1,
                                    model_id: "dense".into(),
                                    values: ids
                                        .into_iter()
                                        .zip(doubled)
                                        .rev()
                                        .map(|(variable_id, v)| Assignment {
                                            variable_id,
                                            value: v as f64 / 2.0,
                                        })
                                        .collect(),
                                };
                                let report = model.evaluate(&candidate, exact()).unwrap();
                                assert_eq!(report.objective, (5 + 2 * x - 3 * y + z) as f64 / 2.0);
                                let mut feasible = y % 2 == 0 && [0, 2].contains(&z);
                                assert_eq!(
                                    report.variables[1].domain.as_ref().unwrap().violation,
                                    (y % 2).abs() as f64 / 2.0
                                );
                                assert_eq!(
                                    report.variables[2].domain.as_ref().unwrap().violation,
                                    z.abs().min((z - 2).abs()) as f64 / 2.0
                                );
                                for (i, row) in rows.iter().enumerate() {
                                    let activity = row[0] * x + row[1] * y + row[2] * z;
                                    let (lower, upper) = if i == 0 { (-2, 4) } else { (0, 0) };
                                    let check = &report.constraints[i];
                                    assert_eq!(check.activity, activity as f64 / 2.0);
                                    assert_eq!(
                                        check.lower.as_ref().unwrap().violation,
                                        (lower - activity).max(0) as f64 / 2.0
                                    );
                                    assert_eq!(
                                        check.upper.as_ref().unwrap().violation,
                                        (activity - upper).max(0) as f64 / 2.0
                                    );
                                    feasible &= (lower..=upper).contains(&activity);
                                }
                                assert_eq!(report.feasible, feasible);
                            }
                        }
                    }
                }
            }
        }
    }
}

#[test]
fn allowances_include_term_magnitudes_and_accept_exact_boundaries() {
    let mut d = document();
    d.variables[1].domain = Domain::Continuous;
    d.constraints[0].terms = vec![term(2, 1e8), term(9, -1e8)];
    d.constraints[0].lower = finite(1.0);
    d.constraints[0].upper = finite(1.0);
    let model = Model::new(d).unwrap();
    let report = model
        .evaluate(
            &candidate(&[1.0, 1.0]),
            Tolerances {
                relative: 1e-8,
                ..exact()
            },
        )
        .unwrap();
    let check = report.constraints[0].lower.as_ref().unwrap();
    assert_eq!(check.violation, 1.0);
    assert_eq!(check.allowance, 2.0);
    assert!(report.feasible);
    assert!(
        !model
            .evaluate(&candidate(&[1.0, 1.0]), exact())
            .unwrap()
            .feasible
    );
    let mut d = document();
    d.variables[0].lower = finite(1.0);
    d.variables[0].upper = finite(1.0);
    d.constraints.clear();
    let model = Model::new(d).unwrap();
    for value in [0.75, 1.25] {
        assert!(
            model
                .evaluate(
                    &candidate(&[value, 0.0]),
                    Tolerances {
                        absolute: 0.25,
                        ..exact()
                    }
                )
                .unwrap()
                .feasible
        );
    }
    assert!(
        !model
            .evaluate(
                &candidate(&[1.5, 0.0]),
                Tolerances {
                    absolute: 0.25,
                    ..exact()
                }
            )
            .unwrap()
            .feasible
    );
    let report = model
        .evaluate(
            &candidate(&[2.0, 0.0]),
            Tolerances {
                relative: 0.5,
                ..exact()
            },
        )
        .unwrap();
    assert_eq!(report.variables[0].upper.as_ref().unwrap().allowance, 1.0);
    assert!(report.feasible);
}

#[test]
fn discrete_domains_are_independent_of_bounds_and_never_round_candidates() {
    let mut d = document();
    d.constraints.clear();
    d.variables[0].domain = Domain::Binary;
    let model = Model::new(d).unwrap();
    for value in [-0.125, 0.125, 0.875, 1.125] {
        let report = model
            .evaluate(
                &candidate(&[value, -1.125]),
                Tolerances {
                    integrality: 0.125,
                    ..exact()
                },
            )
            .unwrap();
        assert!(report.feasible);
        assert_eq!(report.objective, 0.5 - value - 3.375);
        assert_eq!(report.variables[0].value, value);
    }
    assert!(
        !model
            .evaluate(
                &candidate(&[2.0, 0.0]),
                Tolerances {
                    absolute: 100.0,
                    ..exact()
                }
            )
            .unwrap()
            .feasible
    );
    for value in [-9_007_199_254_740_992.0, 9_007_199_254_740_992.0] {
        assert!(
            model
                .evaluate(&candidate(&[0.0, value]), exact())
                .unwrap()
                .feasible
        );
        assert_eq!(
            model
                .evaluate(&candidate(&[0.0, value * 2.0]), exact())
                .unwrap_err()
                .kind,
            ErrorKind::Numerical
        );
    }
}

#[test]
fn numerical_failures_cover_products_sums_residuals_and_allowances() {
    let mut base = document();
    base.variables[1].domain = Domain::Continuous;
    base.constraints.clear();
    base.objective.terms.clear();
    base.objective.offset = 0.0;
    let mut cases = Vec::new();
    let mut d = base.clone();
    d.objective.terms = vec![term(2, f64::MAX)];
    cases.push((d, candidate(&[2.0, 0.0]), exact()));
    let mut d = base.clone();
    d.objective.terms = vec![term(2, f64::MAX), term(9, f64::MAX)];
    cases.push((d, candidate(&[1.0, 1.0]), exact()));
    let mut d = base.clone();
    d.objective.terms = vec![term(2, f64::MAX)];
    d.objective.offset = f64::MAX;
    cases.push((d, candidate(&[1.0, 0.0]), exact()));
    let mut d = base.clone();
    d.variables[0].lower = finite(f64::MAX);
    cases.push((d, candidate(&[-f64::MAX, 0.0]), exact()));
    let mut d = base.clone();
    d.variables[0].upper = finite(-f64::MAX);
    cases.push((d, candidate(&[f64::MAX, 0.0]), exact()));
    let mut d = base.clone();
    d.variables[0].lower = finite(0.0);
    cases.push((
        d.clone(),
        candidate(&[f64::MAX, 0.0]),
        Tolerances {
            relative: 2.0,
            ..exact()
        },
    ));
    cases.push((
        d,
        candidate(&[f64::MAX, 0.0]),
        Tolerances {
            absolute: f64::MAX,
            relative: 1.0,
            integrality: 0.0,
        },
    ));
    let mut d = base.clone();
    d.constraints.push(Constraint {
        id: 1,
        lower: Bound::NegativeInfinity,
        upper: Bound::PositiveInfinity,
        terms: vec![term(2, f64::MAX), term(9, -f64::MAX)],
    });
    cases.push((d, candidate(&[1.0, 1.0]), exact()));
    for (d, c, tolerances) in cases {
        assert_eq!(
            Model::new(d)
                .unwrap()
                .evaluate(&c, tolerances)
                .unwrap_err()
                .kind,
            ErrorKind::Numerical
        );
    }
    // Satisfied bounds avoid an unnecessary overflowing subtraction; finite underflow is allowed.
    base.variables[0].lower = finite(-f64::MAX);
    base.objective.terms = vec![term(9, f64::MIN_POSITIVE)];
    let report = Model::new(base)
        .unwrap()
        .evaluate(&candidate(&[f64::MAX, f64::MIN_POSITIVE]), exact())
        .unwrap();
    assert!(report.feasible);
    assert_eq!(report.objective.to_bits(), 0);
}

#[test]
fn persisted_edge_models_are_valid_structure_without_solver_classification() {
    for source in [
        include_str!("../../../tests/fixtures/models/infeasible.json"),
        include_str!("../../../tests/fixtures/models/unbounded.json"),
        include_str!("../../../tests/fixtures/models/degenerate.json"),
        include_str!("../../../tests/fixtures/models/poorly-scaled.json"),
        include_str!("../../../tests/fixtures/models/overflow-prone.json"),
    ] {
        let model = Model::from_json(source.as_bytes()).unwrap();
        assert_eq!(
            Model::from_json(model.to_json().unwrap().as_bytes()).unwrap(),
            model
        );
        let id = model.document().model_id.as_str();
        let candidate = Candidate {
            schema_version: 1,
            model_id: id.into(),
            values: model
                .document()
                .variables
                .iter()
                .map(|variable| Assignment {
                    variable_id: variable.id,
                    value: match (id, variable.id) {
                        ("unbounded", _) => 7.0,
                        ("overflow-prone", _) => 2.0,
                        ("poorly-scaled", 1) => 1e-12,
                        _ => 0.0,
                    },
                })
                .collect(),
        };
        let result = model.evaluate(&candidate, exact());
        if id == "overflow-prone" {
            assert_eq!(result.unwrap_err().kind, ErrorKind::Numerical);
        } else {
            let report = result.unwrap();
            assert_eq!(report.feasible, id != "infeasible");
            assert_eq!(report.objective, if id == "unbounded" { -7.0 } else { 0.0 });
            if id == "infeasible" {
                assert_eq!(report.constraints[0].lower.as_ref().unwrap().violation, 1.0);
                assert!(report.constraints[1].upper.as_ref().unwrap().satisfied);
            }
        }
    }
}
