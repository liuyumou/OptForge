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

/// Characterization: every observable effect of candidate canonicalization.
///
/// `Candidate::canonical` runs on the branch-and-bound node path, once per
/// evaluated candidate, so it is a target for a fast path that skips the
/// clone-and-re-sort when the input is already canonical. These assertions pin
/// what such a fast path must not change, and they are written against the
/// clone-always implementation so that they characterize existing behavior
/// rather than describe an intended one.
///
/// The negative-zero case is the load-bearing one and is the reason a fast path
/// cannot simply test "sorted and distinct". `finite` returns `zero(value)`, so
/// canonicalization normalizes `-0.0` to `0.0`, and that normalization is
/// observable through `VariableCheck.value` and therefore through every
/// serialized validation report. A fast path that borrowed a candidate holding
/// `-0.0` would publish a different number than the owned path does.
#[test]
fn candidate_canonicalization_normalizes_signed_zero_through_evaluation() {
    let model = Model::new(document()).unwrap();

    // Negative zero survives into the candidate unchanged ...
    let c = candidate(&[-0.0, 2.0]);
    assert_eq!(c.values[0].value.to_bits(), 1_u64 << 63);

    // ... and is normalized by canonicalization, which `evaluate` performs. The
    // assertion is on bits because `-0.0 == 0.0` compares equal and would pass
    // against an unnormalized value.
    let report = model.evaluate(&c, exact()).unwrap();
    assert_eq!(report.variables[0].variable_id, 2);
    assert_eq!(report.variables[0].value.to_bits(), 0);

    // The same normalization on the serialization path, which is the other way a
    // caller observes it.
    assert!(!c.to_json().unwrap().contains("-0.0"));
    assert_eq!(
        Candidate::from_json(c.to_json().unwrap().as_bytes())
            .unwrap()
            .values[0]
            .value
            .to_bits(),
        0
    );

    // A candidate already free of negative zero evaluates to the same report, so
    // normalization is the only difference between the two inputs.
    let plain = model.evaluate(&candidate(&[0.0, 2.0]), exact()).unwrap();
    assert_eq!(report, plain);
}

/// Characterization: the byte-exact refusals and reorderings canonicalization
/// produces, pinned before any fast path can change one of them silently.
#[test]
fn candidate_canonicalization_pins_its_reordering_and_its_refusals() {
    let model = Model::new(document()).unwrap();

    // Reordering is silent and is not an error: an unsorted candidate is accepted
    // and sorted, and evaluates identically to the sorted one.
    let mut unsorted = candidate(&[1.0, 2.0]);
    unsorted.values.reverse();
    assert_eq!(unsorted.values[0].variable_id, 9);
    let report = model.evaluate(&unsorted, exact()).unwrap();
    assert_eq!(report.variables[0].variable_id, 2);
    assert_eq!(
        report,
        model.evaluate(&candidate(&[1.0, 2.0]), exact()).unwrap()
    );
    assert_eq!(
        unsorted.to_json().unwrap(),
        candidate(&[1.0, 2.0]).to_json().unwrap()
    );

    // A duplicate assignment is refused, by both entry points, with this message.
    let mut duplicated = candidate(&[1.0, 2.0]);
    duplicated.values[1].variable_id = 2;
    for error in [
        duplicated.to_json().unwrap_err(),
        model.evaluate(&duplicated, exact()).unwrap_err(),
    ] {
        assert_eq!(error.kind, ErrorKind::Candidate);
        assert_eq!(error.message, "duplicate assignment ID 2");
    }

    // A nonfinite value is refused, naming the variable it belongs to. The
    // message is checked byte for byte because a fast path that inlines the
    // finiteness test could easily produce a different one.
    for value in [f64::NAN, f64::INFINITY, f64::NEG_INFINITY] {
        let nonfinite = candidate(&[1.0, value]);
        for error in [
            nonfinite.to_json().unwrap_err(),
            model.evaluate(&nonfinite, exact()).unwrap_err(),
        ] {
            assert_eq!(error.kind, ErrorKind::Candidate);
            assert_eq!(error.message, "variable 9: nonfinite value");
        }
    }

    // The duplicate check runs before the finiteness check, so a candidate that
    // is both keeps the duplicate message. Order is observable and is pinned.
    let mut both = candidate(&[f64::NAN, 2.0]);
    both.values[1].variable_id = 2;
    assert_eq!(
        both.to_json().unwrap_err().message,
        "duplicate assignment ID 2"
    );

    // Identity and version are refused before anything is sorted or copied.
    let mut anonymous = candidate(&[1.0, 2.0]);
    anonymous.model_id.clear();
    assert_eq!(anonymous.to_json().unwrap_err().kind, ErrorKind::Candidate);
    let mut future = candidate(&[1.0, 2.0]);
    future.schema_version = 2;
    assert_eq!(future.to_json().unwrap_err().kind, ErrorKind::Document);

    // An empty candidate canonicalizes rather than failing; `evaluate` is what
    // rejects it, for coverage rather than for shape.
    let empty = Candidate {
        schema_version: 1,
        model_id: "test".into(),
        values: Vec::new(),
    };
    assert!(empty.to_json().is_ok());
    assert_eq!(
        model.evaluate(&empty, exact()).unwrap_err().message,
        "assignment count does not match variables"
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
fn json_records_require_objects_in_direct_and_nested_inputs() {
    fn reject_array<T: serde::de::DeserializeOwned + serde::Serialize>(value: &T, fields: &[&str]) {
        let object = serde_json::to_value(value).unwrap();
        let array: Vec<_> = fields.iter().map(|field| object[*field].clone()).collect();
        assert!(serde_json::from_value::<T>(object).is_ok());
        assert!(
            serde_json::from_slice::<T>(&serde_json::to_vec(&array).unwrap()).is_err(),
            "{} accepted a positional array",
            std::any::type_name::<T>()
        );
    }
    let d = document();
    reject_array(
        &d,
        &[
            "schema_version",
            "model_id",
            "variables",
            "constraints",
            "objective",
        ],
    );
    reject_array(&d.variables[0], &["id", "domain", "lower", "upper"]);
    reject_array(&d.constraints[0], &["id", "lower", "upper", "terms"]);
    reject_array(&d.objective, &["sense", "offset", "terms"]);
    reject_array(&d.objective.terms[0], &["variable_id", "coefficient"]);
    let c = candidate(&[0.0, 0.0]);
    reject_array(&c, &["schema_version", "model_id", "values"]);
    reject_array(&c.values[0], &["variable_id", "value"]);
    for bound in [
        Bound::NegativeInfinity,
        finite(0.0),
        Bound::PositiveInfinity,
    ] {
        let fields = if matches!(bound, Bound::Finite { .. }) {
            &["kind", "value"][..]
        } else {
            &["kind"][..]
        };
        reject_array(&bound, fields);
    }
    for (path, replacement) in [
        (
            "/variables/0",
            serde_json::json!([2, "continuous", {"kind":"negative_infinity"}, {"kind":"positive_infinity"}]),
        ),
        (
            "/constraints/0",
            serde_json::json!([7, {"kind":"finite","value":-2}, {"kind":"finite","value":3}, []]),
        ),
        ("/objective", serde_json::json!(["minimize", 0.5, []])),
        ("/objective/terms/0", serde_json::json!([2, -1.0])),
        ("/constraints/0/terms/0", serde_json::json!([2, 2.0])),
        (
            "/variables/0/lower",
            serde_json::json!(["negative_infinity"]),
        ),
        (
            "/variables/0/upper",
            serde_json::json!(["positive_infinity"]),
        ),
        ("/constraints/0/lower", serde_json::json!(["finite", -2.0])),
    ] {
        let mut input = serde_json::to_value(&d).unwrap();
        *input.pointer_mut(path).unwrap() = replacement;
        assert_eq!(
            Model::from_json(&serde_json::to_vec(&input).unwrap())
                .unwrap_err()
                .kind,
            ErrorKind::Document
        );
    }
    let mut input = serde_json::to_value(&c).unwrap();
    input["values"][0] = serde_json::json!([2, 0.0]);
    assert_eq!(
        Candidate::from_json(&serde_json::to_vec(&input).unwrap())
            .unwrap_err()
            .kind,
        ErrorKind::Document
    );
    assert_eq!(
        Candidate::from_json(br#"[1,"test",[]]"#).unwrap_err().kind,
        ErrorKind::Document
    );
    assert_eq!(
        Model::from_json(include_bytes!(
            "../../../tests/regression/positional-model.json"
        ))
        .unwrap_err()
        .kind,
        ErrorKind::Document
    );
}

#[test]
fn json_domain_and_objective_enums_require_strings() {
    for name in ["continuous", "integer", "binary"] {
        assert!(serde_json::from_value::<Domain>(serde_json::json!(name)).is_ok());
        assert!(serde_json::from_value::<Domain>(serde_json::json!({name: null})).is_err());
        let mut input = serde_json::to_value(document()).unwrap();
        input["variables"][0]["domain"] = serde_json::json!({name: null});
        assert_eq!(
            Model::from_json(&serde_json::to_vec(&input).unwrap())
                .unwrap_err()
                .kind,
            ErrorKind::Document
        );
    }
    for name in ["minimize", "maximize"] {
        assert!(serde_json::from_value::<ObjectiveSense>(serde_json::json!(name)).is_ok());
        assert!(serde_json::from_value::<ObjectiveSense>(serde_json::json!({name: null})).is_err());
        let mut input = serde_json::to_value(document()).unwrap();
        input["objective"]["sense"] = serde_json::json!({name: null});
        assert_eq!(
            Model::from_json(&serde_json::to_vec(&input).unwrap())
                .unwrap_err()
                .kind,
            ErrorKind::Document
        );
    }
    assert_eq!(
        Model::from_json(include_bytes!(
            "../../../tests/regression/object-enum-model.json"
        ))
        .unwrap_err()
        .kind,
        ErrorKind::Document
    );
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

// Characterization of the numerical-failure diagnostics, written before the
// eager `format!` calls in `evaluate.rs` became lazy. Every message below is the
// byte-exact text the current code produces. The refactor that follows must not
// move a single character of them: these strings reach CLI stderr and the
// categorized error surface, so a "harmless" rewording is a contract change.
mod evaluation_diagnostics {
    use optimizer_core::*;

    fn tolerances(absolute: f64, relative: f64) -> Tolerances {
        Tolerances {
            absolute,
            relative,
            integrality: 1e-9,
        }
    }

    /// A variable with no finite bound, so `check_bound` returns early for it and
    /// a constraint-level diagnostic is the first one reached.
    fn unbounded(id: u32) -> Variable {
        Variable {
            id,
            domain: Domain::Continuous,
            lower: Bound::NegativeInfinity,
            upper: Bound::PositiveInfinity,
        }
    }

    fn variable(id: u32, domain: Domain, upper: f64) -> Variable {
        Variable {
            id,
            domain,
            lower: Bound::Finite { value: -upper },
            upper: Bound::Finite { value: upper },
        }
    }

    fn evaluate(
        variables: Vec<Variable>,
        constraints: Vec<Constraint>,
        objective: Objective,
        values: Vec<(u32, f64)>,
        tolerances: Tolerances,
    ) -> Result<ValidationReport, ValidationError> {
        let model = Model::new(ModelDocument {
            schema_version: SCHEMA_VERSION,
            model_id: "diagnostics".to_owned(),
            variables,
            constraints,
            objective,
        })
        .expect("fixture model is valid");
        let candidate = Candidate {
            schema_version: SCHEMA_VERSION,
            model_id: "diagnostics".to_owned(),
            values: values
                .into_iter()
                .map(|(variable_id, value)| Assignment { variable_id, value })
                .collect(),
        };
        model.evaluate(&candidate, tolerances)
    }

    fn message(result: Result<ValidationReport, ValidationError>) -> String {
        result.expect_err("this fixture must fail").to_string()
    }

    fn objective_of(terms: Vec<LinearTerm>, offset: f64) -> Objective {
        Objective {
            sense: ObjectiveSense::Minimize,
            offset,
            terms,
        }
    }

    fn term(variable_id: u32, coefficient: f64) -> LinearTerm {
        LinearTerm {
            variable_id,
            coefficient,
        }
    }

    #[test]
    fn a_discrete_magnitude_beyond_two_to_the_fifty_three_is_named() {
        let text = message(evaluate(
            vec![variable(7, Domain::Integer, 1e300)],
            Vec::new(),
            objective_of(vec![term(7, 1.0)], 0.0),
            vec![(7, 1e17)],
            tolerances(1e-9, 1e-9),
        ));
        assert!(
            text.contains("variable 7: discrete magnitude exceeds 2^53"),
            "found {text}"
        );
    }

    #[test]
    fn a_nonfinite_objective_product_names_its_variable() {
        let text = message(evaluate(
            vec![variable(3, Domain::Continuous, 1e300)],
            Vec::new(),
            objective_of(vec![term(3, 1e308)], 0.0),
            vec![(3, 1e10)],
            tolerances(1e-9, 1e-9),
        ));
        assert!(
            text.contains("objective, variable 3 product: nonfinite value"),
            "found {text}"
        );
    }

    #[test]
    fn a_nonfinite_objective_sum_names_its_variable() {
        let text = message(evaluate(
            vec![
                variable(0, Domain::Continuous, 1e300),
                variable(1, Domain::Continuous, 1e300),
            ],
            Vec::new(),
            objective_of(vec![term(0, 1.0), term(1, 1.0)], 0.0),
            vec![(0, 9e307), (1, 9e307)],
            tolerances(1e-9, 1e-9),
        ));
        assert!(
            text.contains("objective, variable 1 sum: nonfinite value"),
            "found {text}"
        );
    }

    #[test]
    fn a_nonfinite_term_magnitude_names_its_constraint_and_variable() {
        // Opposite signs keep the running sum finite while the magnitude, which
        // accumulates absolute values, overflows. This is the only path that
        // reaches the `track_magnitude` branch.
        let text = message(evaluate(
            vec![
                variable(0, Domain::Continuous, 1e300),
                variable(1, Domain::Continuous, 1e300),
            ],
            vec![Constraint {
                id: 5,
                lower: Bound::NegativeInfinity,
                upper: Bound::Finite { value: 1e300 },
                terms: vec![term(0, 9e307), term(1, -9e307)],
            }],
            objective_of(vec![term(0, 1.0)], 0.0),
            vec![(0, 1.0), (1, 1.0)],
            tolerances(1e-9, 1e-9),
        ));
        assert!(
            text.contains("constraint 5, variable 1 term magnitude: nonfinite value"),
            "found {text}"
        );
    }

    #[test]
    fn a_nonfinite_objective_offset_is_named() {
        let text = message(evaluate(
            vec![variable(0, Domain::Continuous, 1e300)],
            Vec::new(),
            objective_of(vec![term(0, 1.0)], 1e308),
            vec![(0, 9e307)],
            tolerances(1e-9, 1e-9),
        ));
        assert!(
            text.contains("objective offset addition: nonfinite value"),
            "found {text}"
        );
    }

    #[test]
    fn a_nonfinite_relative_allowance_names_its_constraint() {
        let text = message(evaluate(
            vec![unbounded(0)],
            vec![Constraint {
                id: 9,
                lower: Bound::NegativeInfinity,
                upper: Bound::Finite { value: 1e300 },
                terms: vec![term(0, 1.0)],
            }],
            objective_of(vec![term(0, 1.0)], 0.0),
            vec![(0, 1e300)],
            tolerances(1e-9, 1e308),
        ));
        assert!(
            text.contains("constraint 9 relative allowance: nonfinite value"),
            "found {text}"
        );
    }

    #[test]
    fn a_nonfinite_allowance_sum_names_its_constraint() {
        // relative * scale stays finite at 1e308; adding an absolute allowance of
        // the same size is what overflows, which is the `allowance sum` site
        // rather than the `relative allowance` one above.
        let text = message(evaluate(
            vec![unbounded(0)],
            vec![Constraint {
                id: 11,
                lower: Bound::NegativeInfinity,
                upper: Bound::Finite { value: 1e308 },
                terms: vec![term(0, 1.0)],
            }],
            objective_of(vec![term(0, 1.0)], 0.0),
            vec![(0, 1.0)],
            tolerances(1e308, 1.0),
        ));
        assert!(
            text.contains("constraint 11 allowance sum: nonfinite value"),
            "found {text}"
        );
    }

    #[test]
    fn a_nonfinite_variable_residual_names_its_variable() {
        // The value sits above a bound at the opposite extreme, so the upper
        // residual `activity - bound` overflows.
        let text = message(evaluate(
            vec![Variable {
                id: 4,
                domain: Domain::Continuous,
                lower: Bound::Finite { value: -1e308 },
                upper: Bound::Finite { value: -1e308 },
            }],
            Vec::new(),
            objective_of(vec![term(4, 1.0)], 0.0),
            vec![(4, 1e308)],
            tolerances(1e-9, 1e-9),
        ));
        assert!(
            text.contains("variable 4 upper residual: nonfinite value"),
            "found {text}"
        );
    }
    // `Model::new` runs once per branch-and-bound node through `node::relaxation`,
    // and its per-nonzero diagnostics are on that path. Pinned here before they
    // became lazy, for the same reason as the evaluation messages above.
    #[test]
    fn a_term_naming_an_absent_variable_is_named() {
        let error = Model::new(ModelDocument {
            schema_version: SCHEMA_VERSION,
            model_id: "structural".to_owned(),
            variables: vec![unbounded(0)],
            constraints: vec![Constraint {
                id: 5,
                lower: Bound::NegativeInfinity,
                upper: Bound::Finite { value: 1.0 },
                terms: vec![term(0, 1.0), term(42, 1.0)],
            }],
            objective: objective_of(vec![term(0, 1.0)], 0.0),
        })
        .expect_err("a term naming an absent variable is refused");
        assert!(
            error
                .to_string()
                .contains("constraint 5, variable 42: unknown variable"),
            "found {error}"
        );
    }

    #[test]
    fn a_nonfinite_coefficient_names_its_term() {
        let error = Model::new(ModelDocument {
            schema_version: SCHEMA_VERSION,
            model_id: "structural".to_owned(),
            variables: vec![unbounded(0)],
            constraints: Vec::new(),
            objective: objective_of(vec![term(0, f64::INFINITY)], 0.0),
        })
        .expect_err("a nonfinite coefficient is refused");
        assert!(
            error
                .to_string()
                .contains("objective, variable 0: nonfinite value"),
            "found {error}"
        );
    }

    #[test]
    fn crossed_bounds_name_their_owner() {
        let error = Model::new(ModelDocument {
            schema_version: SCHEMA_VERSION,
            model_id: "structural".to_owned(),
            variables: vec![Variable {
                id: 2,
                domain: Domain::Continuous,
                lower: Bound::Finite { value: 5.0 },
                upper: Bound::Finite { value: 1.0 },
            }],
            constraints: Vec::new(),
            objective: objective_of(vec![term(2, 1.0)], 0.0),
        })
        .expect_err("crossed bounds are refused");
        assert!(
            error.to_string().contains("variable 2: invalid bounds"),
            "found {error}"
        );
    }
}
