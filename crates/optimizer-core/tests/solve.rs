//! Independent acceptance contracts for the SPEC-0002 solve contract types.
//!
//! These cover the backend-neutral surface only. Native behavior is verified by
//! the optimizer-highs acceptance and differential tests.

use optimizer_core::*;

fn tolerances() -> Tolerances {
    Tolerances {
        absolute: 1e-9,
        relative: 1e-9,
        integrality: 1e-9,
    }
}

fn options() -> SolveOptions {
    SolveOptions {
        schema_version: SOLVE_SCHEMA_VERSION,
        seed: 17,
        time_limit_ms: None,
        iteration_limit: None,
        node_limit: None,
        tolerances: tolerances(),
        threads: 1,
    }
}

// Requirement 5: configuration failures keep distinct diagnostic categories
// rather than collapsing into one opaque message.
#[test]
fn solve_options_validate_each_failure_in_its_own_category() {
    assert_eq!(options().validate().unwrap().tolerances, tolerances());

    let mut version = options();
    version.schema_version = 2;
    assert_eq!(
        version.validate().unwrap_err().kind,
        ErrorKind::Document,
        "an unsupported version is a document failure"
    );

    let mut threads = options();
    threads.threads = 2;
    assert_eq!(threads.validate().unwrap_err().kind, ErrorKind::Unsupported);
    let mut zero_threads = options();
    zero_threads.threads = 0;
    assert_eq!(
        zero_threads.validate().unwrap_err().kind,
        ErrorKind::Unsupported
    );

    // Every limit is optional, but a present limit must be positive.
    for mutate in [
        (|o: &mut SolveOptions| o.time_limit_ms = Some(0)) as fn(&mut SolveOptions),
        |o: &mut SolveOptions| o.iteration_limit = Some(0),
        |o: &mut SolveOptions| o.node_limit = Some(0),
    ] {
        let mut limited = options();
        mutate(&mut limited);
        assert_eq!(
            limited.validate().unwrap_err().kind,
            ErrorKind::Unsupported,
            "a zero limit must be rejected"
        );
    }

    // Tolerance categories propagate instead of being stringified away.
    let mut invalid = options();
    invalid.tolerances.integrality = 0.5;
    assert_eq!(invalid.validate().unwrap_err().kind, ErrorKind::Tolerance);
    let mut negative = options();
    negative.tolerances.absolute = -1.0;
    assert_eq!(negative.validate().unwrap_err().kind, ErrorKind::Tolerance);

    // A present limit converts to a duration; an absent one stays absent.
    let mut timed = options();
    timed.time_limit_ms = Some(1_500);
    assert_eq!(
        timed.time_limit(),
        Some(std::time::Duration::from_millis(1_500))
    );
    assert_eq!(options().time_limit(), None);
}

// Requirement 8: a limit, interruption or failure never proves completion.
#[test]
fn only_mathematical_outcomes_prove_completion() {
    for completed in [
        Termination::Optimal,
        Termination::Infeasible,
        Termination::Unbounded,
        Termination::UnboundedOrInfeasible,
    ] {
        assert!(
            completed.proves_completion(),
            "{completed:?} is a completed outcome"
        );
    }
    for incomplete in [
        Termination::Feasible,
        Termination::Interrupted,
        Termination::TimeLimit,
        Termination::IterationLimit,
        Termination::NodeLimit,
        Termination::NumericalFailure,
        Termination::BackendFailure,
        Termination::Unsupported,
    ] {
        assert!(
            !incomplete.proves_completion(),
            "{incomplete:?} must never prove completion"
        );
    }
}

// Requirement 11: records round trip, and every status name is stable.
#[test]
fn solve_records_round_trip_with_stable_status_names() {
    let names = [
        (Termination::Optimal, "optimal"),
        (Termination::Feasible, "feasible"),
        (Termination::Infeasible, "infeasible"),
        (
            Termination::UnboundedOrInfeasible,
            "unbounded_or_infeasible",
        ),
        (Termination::Unbounded, "unbounded"),
        (Termination::Interrupted, "interrupted"),
        (Termination::TimeLimit, "time_limit"),
        (Termination::IterationLimit, "iteration_limit"),
        (Termination::NodeLimit, "node_limit"),
        (Termination::NumericalFailure, "numerical_failure"),
        (Termination::BackendFailure, "backend_failure"),
        (Termination::Unsupported, "unsupported"),
    ];
    for (termination, name) in names {
        let record = SolveRecord {
            schema_version: SOLVE_RECORD_SCHEMA_VERSION,
            model_id: "record".into(),
            backend: "highs".into(),
            backend_version: "1.11.0".into(),
            termination,
            native_status: Some(name.to_string()),
            objective: None,
            best_bound: None,
            gap: None,
            candidate: None,
            validation: None,
            warnings: vec![],
            elapsed_ms: 7,
            options: options(),
            lp_settings: None,
        };
        let json = record.to_json().unwrap();
        assert!(
            json.contains(&format!("\"termination\": \"{name}\"")),
            "expected stable name {name} in {json}"
        );
        assert_eq!(SolveRecord::from_json(json.as_bytes()).unwrap(), record);
    }
}

// Requirement 11: an absent measurement is omitted; a nonfinite one is an error.
#[test]
fn absent_measurements_are_omitted_and_nonfinite_ones_rejected() {
    let base = SolveRecord {
        schema_version: SOLVE_RECORD_SCHEMA_VERSION,
        model_id: "measurements".into(),
        backend: "highs".into(),
        backend_version: "1.11.0".into(),
        termination: Termination::Optimal,
        native_status: None,
        objective: None,
        best_bound: None,
        gap: None,
        candidate: None,
        validation: None,
        warnings: vec![],
        elapsed_ms: 0,
        options: options(),
        lp_settings: None,
    };

    let json = base.to_json().unwrap();
    for field in ["objective", "best_bound", "gap", "native_status"] {
        assert!(
            !json.contains(&format!("\"{field}\"")),
            "absent {field} must be omitted, not null: {json}"
        );
    }

    // serde_json renders a nonfinite f64 as null, which would misrepresent an
    // unavailable measurement as a real number, so it is rejected explicitly.
    for value in [f64::NAN, f64::INFINITY, f64::NEG_INFINITY] {
        for mutate in [
            (|record: &mut SolveRecord, v: f64| record.objective = Some(v))
                as fn(&mut SolveRecord, f64),
            |record: &mut SolveRecord, v: f64| record.best_bound = Some(v),
            |record: &mut SolveRecord, v: f64| record.gap = Some(v),
        ] {
            let mut record = base.clone();
            mutate(&mut record, value);
            assert_eq!(
                record.to_json().unwrap_err().kind,
                ErrorKind::Numerical,
                "nonfinite {value} must not serialize"
            );
        }
    }

    // A finite measurement is retained exactly.
    let mut finite = base.clone();
    finite.objective = Some(-1.5);
    let json = finite.to_json().unwrap();
    assert!(json.contains("\"objective\": -1.5"));
    assert_eq!(SolveRecord::from_json(json.as_bytes()).unwrap(), finite);

    // finite_or_absent is the guard backends use for native measurements.
    assert_eq!(finite_or_absent(2.5), Some(2.5));
    assert_eq!(finite_or_absent(f64::NAN), None);
    assert_eq!(finite_or_absent(f64::INFINITY), None);
    assert_eq!(finite_or_absent(-0.0), Some(0.0));
}

// Requirement 11: solve documents reject unknown fields, positional records and
// unsupported versions, matching the M1 document rules.
#[test]
fn solve_documents_require_strict_versioned_objects() {
    let valid = serde_json::to_string(&options()).unwrap();
    assert!(serde_json::from_str::<SolveOptions>(&valid).is_ok());

    for invalid in [
        // Unknown field.
        valid.replace("\"seed\":17", "\"seed\":17,\"extra\":1"),
        // A positional array is not a record.
        "[1,17,null,null,null,{\"absolute\":0.0,\"relative\":0.0,\"integrality\":0.0},1]"
            .to_string(),
        // Missing required field.
        "{\"schema_version\":1}".to_string(),
        // Duplicate key.
        valid.replace("\"seed\":17", "\"seed\":17,\"seed\":18"),
    ] {
        assert!(
            serde_json::from_str::<SolveOptions>(&invalid).is_err(),
            "expected rejection of {invalid}"
        );
    }

    // An unsupported record version fails as a document error.
    let record = SolveRecord {
        schema_version: SOLVE_RECORD_SCHEMA_VERSION,
        model_id: "version".into(),
        backend: "highs".into(),
        backend_version: "1.11.0".into(),
        termination: Termination::Optimal,
        native_status: None,
        objective: None,
        best_bound: None,
        gap: None,
        candidate: None,
        validation: None,
        warnings: vec![],
        elapsed_ms: 0,
        options: options(),
        lp_settings: None,
    };
    let bumped = record
        .to_json()
        .unwrap()
        .replace("\"schema_version\": 1", "\"schema_version\": 2");
    assert_eq!(
        SolveRecord::from_json(bumped.as_bytes()).unwrap_err().kind,
        ErrorKind::Document
    );

    // An unknown termination name is rejected rather than silently defaulted.
    let unknown = record
        .to_json()
        .unwrap()
        .replace("\"optimal\"", "\"almost_optimal\"");
    assert_eq!(
        SolveRecord::from_json(unknown.as_bytes()).unwrap_err().kind,
        ErrorKind::Document
    );
}

// Requirement 11: a record's nested versioned documents are validated on parse,
// not only its own version.
//
// The version-1 JSON Schemas pin every nested `schema_version`, so a parser
// checking only the outer version would accept documents
// tools/validate_artifacts.py rejects. That divergence is what let a search
// record test mutate a nested version and still appear to pass.
#[test]
fn nested_document_versions_are_validated_on_parse() {
    let candidate = Candidate {
        schema_version: SCHEMA_VERSION,
        model_id: "nested".into(),
        values: vec![Assignment {
            variable_id: 0,
            value: 1.0,
        }],
    };
    let model = Model::new(ModelDocument {
        schema_version: SCHEMA_VERSION,
        model_id: "nested".into(),
        variables: vec![Variable {
            id: 0,
            domain: Domain::Continuous,
            lower: Bound::Finite { value: 0.0 },
            upper: Bound::Finite { value: 2.0 },
        }],
        constraints: vec![],
        objective: Objective {
            sense: ObjectiveSense::Minimize,
            offset: 0.0,
            terms: vec![LinearTerm {
                variable_id: 0,
                coefficient: 1.0,
            }],
        },
    })
    .expect("model");
    let validation = model.evaluate(&candidate, tolerances()).expect("report");

    let record = SolveRecord {
        schema_version: SOLVE_RECORD_SCHEMA_VERSION,
        model_id: "nested".into(),
        backend: "highs".into(),
        backend_version: "1.11.0".into(),
        termination: Termination::Optimal,
        native_status: None,
        objective: Some(validation.objective),
        best_bound: None,
        gap: None,
        candidate: Some(candidate),
        validation: Some(validation),
        warnings: vec![],
        elapsed_ms: 0,
        options: options(),
        lp_settings: None,
    };

    // The intact record round trips, so each rejection below is caused by the
    // nested version alone.
    let json = record.to_json().expect("serializable");
    assert_eq!(
        SolveRecord::from_json(json.as_bytes()).expect("round trip"),
        record
    );

    // Each nested document is rejected independently. The mutation targets one
    // parsed field by name, so no assertion depends on where a version happens
    // to appear in the serialized text.
    for field in ["candidate", "validation", "options"] {
        let mut document: serde_json::Value = serde_json::from_str(&json).expect("valid JSON");
        document[field]["schema_version"] = serde_json::json!(9);
        let mutated = serde_json::to_string(&document).expect("serializable");

        let error = SolveRecord::from_json(mutated.as_bytes())
            .expect_err("a wrongly versioned nested document must be rejected");
        assert_eq!(error.kind, ErrorKind::Document, "{field}: {error}");
        assert!(
            error.message.contains(field),
            "the failure must name the offending field: {error}"
        );
    }
}
#[test]
fn cancellation_is_observable_through_every_clone() {
    let token = CancellationToken::new();
    let clone = token.clone();
    assert!(!token.is_cancelled());
    assert!(!clone.is_cancelled());

    clone.cancel();
    assert!(token.is_cancelled(), "cancellation must be shared");
    assert!(clone.is_cancelled());

    // Cancellation is monotonic; there is no reset path.
    clone.cancel();
    assert!(token.is_cancelled());
}

// Requirement 9: a basis is bound to exact canonical data, not just an ID.
#[test]
fn model_fingerprints_distinguish_changed_data_under_one_identity() {
    let build = |upper: f64| {
        Model::new(ModelDocument {
            schema_version: 1,
            model_id: "fingerprint".into(),
            variables: vec![Variable {
                id: 0,
                domain: Domain::Continuous,
                lower: Bound::Finite { value: 0.0 },
                upper: Bound::Finite { value: upper },
            }],
            constraints: vec![],
            objective: Objective {
                sense: ObjectiveSense::Minimize,
                offset: 0.0,
                terms: vec![LinearTerm {
                    variable_id: 0,
                    coefficient: 1.0,
                }],
            },
        })
        .unwrap()
    };

    let model = build(1.0);
    // The same canonical data always yields the same fingerprint.
    assert_eq!(
        model.fingerprint().unwrap(),
        build(1.0).fingerprint().unwrap()
    );
    // Changed data under an unchanged identity yields a different fingerprint.
    assert_ne!(
        model.fingerprint().unwrap(),
        build(2.0).fingerprint().unwrap()
    );

    let basis = Basis {
        schema_version: SOLVE_SCHEMA_VERSION,
        model_id: "fingerprint".into(),
        model_fingerprint: model.fingerprint().unwrap(),
        columns: vec![BasisStatus::Basic],
        rows: vec![],
    };
    let json = serde_json::to_string(&basis).unwrap();
    assert_eq!(serde_json::from_str::<Basis>(&json).unwrap(), basis);
    // Basis statuses are strings, not enum objects.
    assert!(json.contains("\"basic\""));
    assert!(serde_json::from_str::<Basis>(&json.replace("\"basic\"", "\"bogus\"")).is_err());
}
