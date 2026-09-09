//! Native HiGHS acceptance tests mapped to SPEC-0002 requirement numbers.
//!
//! Every test states an externally observable contract. Tests that need the
//! pinned native library are skipped with an explicit message when it is not
//! provisioned, so a missing build is never silently reported as coverage.

use optimizer_core::{
    Assignment, Backend, Basis, BasisStatus, Bound, Candidate, Constraint, Domain, ErrorKind,
    LinearTerm, Model, ModelDocument, Objective, ObjectiveSense, SOLVE_SCHEMA_VERSION,
    SolveOptions, SolveRecord, Termination, Tolerances, Variable, WarmStart,
};
use optimizer_highs::{BACKEND_NAME, HighsBackend, is_native};

fn exact() -> Tolerances {
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
        tolerances: exact(),
        threads: 1,
    }
}

fn finite(value: f64) -> Bound {
    Bound::Finite { value }
}

/// `min -x0 - x1` subject to `x0 + x1 <= 1.5`, `0 <= xj <= 1`.
///
/// The LP optimum is -1.5; with integer variables the optimum is -1.
fn model(domain: Domain, model_id: &str) -> Model {
    Model::new(ModelDocument {
        schema_version: optimizer_core::SCHEMA_VERSION,
        model_id: model_id.to_string(),
        variables: vec![
            Variable {
                id: 0,
                domain,
                lower: finite(0.0),
                upper: finite(1.0),
            },
            Variable {
                id: 1,
                domain,
                lower: finite(0.0),
                upper: finite(1.0),
            },
        ],
        constraints: vec![Constraint {
            id: 0,
            lower: Bound::NegativeInfinity,
            upper: finite(1.5),
            terms: vec![
                LinearTerm {
                    variable_id: 0,
                    coefficient: 1.0,
                },
                LinearTerm {
                    variable_id: 1,
                    coefficient: 1.0,
                },
            ],
        }],
        objective: Objective {
            sense: ObjectiveSense::Minimize,
            offset: 0.0,
            terms: vec![
                LinearTerm {
                    variable_id: 0,
                    coefficient: -1.0,
                },
                LinearTerm {
                    variable_id: 1,
                    coefficient: -1.0,
                },
            ],
        },
    })
    .expect("model")
}

/// Skip a native-only test loudly rather than reporting false coverage.
fn require_native(test: &str) -> bool {
    if is_native() {
        return true;
    }
    eprintln!("SKIP {test}: HiGHS not provisioned; run bash tools/setup_highs.sh");
    false
}

// Requirement 1: the adapter reports the pinned native version it linked.
#[test]
fn pinned_version_is_reported_by_the_library_itself() {
    let backend = HighsBackend::new();
    match backend.version() {
        Some(version) => {
            assert!(is_native());
            assert!(
                version.starts_with("1.11."),
                "expected pinned 1.11.x, found {version}"
            );
        }
        None => assert!(!is_native()),
    }
}

// Requirement 5: configuration is explicit and checked before native work.
#[test]
fn solve_options_reject_unsupported_configuration() {
    let backend = HighsBackend::new();
    let model = model(Domain::Continuous, "options");
    let cancel = optimizer_core::CancellationToken::new();

    let mut threaded = options();
    threaded.threads = 4;
    let error = backend
        .solve(&model, &threaded, &cancel, None)
        .expect_err("threads must be rejected");
    assert_eq!(error.kind, ErrorKind::Unsupported);

    let mut zero_limit = options();
    zero_limit.time_limit_ms = Some(0);
    assert_eq!(
        backend
            .solve(&model, &zero_limit, &cancel, None)
            .expect_err("zero limit must be rejected")
            .kind,
        ErrorKind::Unsupported
    );

    let mut version = options();
    version.schema_version = 2;
    assert_eq!(
        backend
            .solve(&model, &version, &cancel, None)
            .expect_err("version must be rejected")
            .kind,
        ErrorKind::Document
    );
}

// Requirement 6: a pre-cancelled solve returns interrupted without native work.
#[test]
fn pre_cancelled_solve_is_interrupted_without_native_work() {
    let backend = HighsBackend::new();
    let model = model(Domain::Continuous, "pre-cancelled");
    let cancel = optimizer_core::CancellationToken::new();
    cancel.cancel();

    let record = backend
        .solve(&model, &options(), &cancel, None)
        .expect("pre-cancelled solve returns a record");
    assert_eq!(record.termination, Termination::Interrupted);
    assert!(record.native_status.is_none());
    assert!(record.candidate.is_none());
    assert!(!record.termination.proves_completion());
}

// Requirements 4 and 7: an optimal LP is validated against the original model.
#[test]
fn optimal_lp_is_validated_against_the_original_model() {
    if !require_native("optimal_lp_is_validated_against_the_original_model") {
        return;
    }
    let backend = HighsBackend::new();
    let model = model(Domain::Continuous, "lp");
    let record = backend
        .solve(
            &model,
            &options(),
            &optimizer_core::CancellationToken::new(),
            None,
        )
        .expect("lp solve");

    assert_eq!(record.termination, Termination::Optimal);
    assert_eq!(record.backend, BACKEND_NAME);
    assert_eq!(record.native_status.as_deref(), Some("optimal"));
    let objective = record.objective.expect("objective");
    assert!(
        (objective - -1.5).abs() <= 1e-7,
        "expected -1.5, found {objective}"
    );
    let validation = record.validation.expect("validation");
    assert!(validation.feasible);
    // The published objective is the core's recomputation, not a native echo.
    assert_eq!(validation.objective, objective);
}

// Requirement 3: integrality is honored, so the MILP optimum differs from the LP.
#[test]
fn integer_domains_are_loaded_and_change_the_optimum() {
    if !require_native("integer_domains_are_loaded_and_change_the_optimum") {
        return;
    }
    let backend = HighsBackend::new();
    let record = backend
        .solve(
            &model(Domain::Integer, "milp"),
            &options(),
            &optimizer_core::CancellationToken::new(),
            None,
        )
        .expect("milp solve");

    assert_eq!(record.termination, Termination::Optimal);
    let objective = record.objective.expect("objective");
    assert!(
        (objective - -1.0).abs() <= 1e-7,
        "expected -1.0 under integrality, found {objective}"
    );
    let validation = record.validation.expect("validation");
    assert!(validation.feasible);
    for check in &validation.variables {
        let domain = check.domain.as_ref().expect("discrete check");
        assert!(domain.satisfied, "integral value expected");
    }
}

// Requirement 3: a binary domain intersects [0,1] regardless of declared bounds.
#[test]
fn binary_bounds_intersect_the_unit_interval() {
    if !require_native("binary_bounds_intersect_the_unit_interval") {
        return;
    }
    let mut document = model(Domain::Binary, "binary").document().clone();
    // Widen the declared bounds; the binary domain must still dominate.
    document.variables[0].upper = finite(9.0);
    document.variables[1].upper = finite(9.0);
    let model = Model::new(document).expect("model");

    let record = HighsBackend::new()
        .solve(
            &model,
            &options(),
            &optimizer_core::CancellationToken::new(),
            None,
        )
        .expect("binary solve");
    let validation = record.validation.expect("validation");
    assert!(validation.feasible);
    for check in &validation.variables {
        assert!(
            check.value >= -1e-9 && check.value <= 1.0 + 1e-9,
            "binary value {} escaped [0,1]",
            check.value
        );
    }
}

// Requirement 4: infeasibility is backend evidence and carries no incumbent.
#[test]
fn infeasible_models_report_no_candidate() {
    if !require_native("infeasible_models_report_no_candidate") {
        return;
    }
    let mut document = model(Domain::Continuous, "infeasible").document().clone();
    // Require x0 + x1 >= 3 while each variable is at most 1.
    document.constraints[0].lower = finite(3.0);
    document.constraints[0].upper = Bound::PositiveInfinity;
    let model = Model::new(document).expect("model");

    let record = HighsBackend::new()
        .solve(
            &model,
            &options(),
            &optimizer_core::CancellationToken::new(),
            None,
        )
        .expect("infeasible solve");
    assert_eq!(record.termination, Termination::Infeasible);
    assert!(record.candidate.is_none());
    assert!(record.objective.is_none());
}

// Requirement 4: unboundedness is evidence, never a feasible incumbent.
#[test]
fn unbounded_models_never_publish_an_incumbent() {
    if !require_native("unbounded_models_never_publish_an_incumbent") {
        return;
    }
    let mut document = model(Domain::Continuous, "unbounded").document().clone();
    document.variables[0].upper = Bound::PositiveInfinity;
    document.variables[1].upper = Bound::PositiveInfinity;
    document.constraints[0].upper = Bound::PositiveInfinity;
    let model = Model::new(document).expect("model");

    let record = HighsBackend::new()
        .solve(
            &model,
            &options(),
            &optimizer_core::CancellationToken::new(),
            None,
        )
        .expect("unbounded solve");
    assert!(
        matches!(
            record.termination,
            Termination::Unbounded | Termination::UnboundedOrInfeasible
        ),
        "found {:?}",
        record.termination
    );
    assert!(record.candidate.is_none());
    assert!(record.objective.is_none());
}

// Requirement 8: a limit must never be reported as proven optimality.
#[test]
fn limits_never_report_proof_completion() {
    if !require_native("limits_never_report_proof_completion") {
        return;
    }
    let mut limited = options();
    limited.iteration_limit = Some(1);
    let record = HighsBackend::new()
        .solve(
            &model(Domain::Continuous, "limited"),
            &limited,
            &optimizer_core::CancellationToken::new(),
            None,
        )
        .expect("limited solve");

    // A tiny model may still finish within one iteration; the contract is that
    // a reported limit is never a completed proof.
    if record.termination != Termination::Optimal {
        assert!(
            !record.termination.proves_completion(),
            "{:?} must not prove completion",
            record.termination
        );
    }
}

// Requirement 9: a candidate warm start must be valid for this exact model.
#[test]
fn candidate_warm_starts_are_validated_before_use() {
    if !require_native("candidate_warm_starts_are_validated_before_use") {
        return;
    }
    let model = model(Domain::Continuous, "warm-candidate");
    let feasible = Candidate {
        schema_version: optimizer_core::SCHEMA_VERSION,
        model_id: "warm-candidate".to_string(),
        values: vec![
            Assignment {
                variable_id: 0,
                value: 0.5,
            },
            Assignment {
                variable_id: 1,
                value: 1.0,
            },
        ],
    };
    let record = HighsBackend::new()
        .solve(
            &model,
            &options(),
            &optimizer_core::CancellationToken::new(),
            Some(WarmStart::Candidate(&feasible)),
        )
        .expect("warm-started solve");
    assert_eq!(record.termination, Termination::Optimal);

    // An infeasible start is rejected rather than silently repaired.
    let infeasible = Candidate {
        schema_version: optimizer_core::SCHEMA_VERSION,
        model_id: "warm-candidate".to_string(),
        values: vec![
            Assignment {
                variable_id: 0,
                value: 1.0,
            },
            Assignment {
                variable_id: 1,
                value: 1.0,
            },
        ],
    };
    assert_eq!(
        HighsBackend::new()
            .solve(
                &model,
                &options(),
                &optimizer_core::CancellationToken::new(),
                Some(WarmStart::Candidate(&infeasible)),
            )
            .expect_err("infeasible start must be rejected")
            .kind,
        ErrorKind::Candidate
    );
}

// Requirement 9: a basis round trips, and a wrong-model basis is rejected.
#[test]
fn basis_round_trips_and_rejects_a_foreign_model() {
    if !require_native("basis_round_trips_and_rejects_a_foreign_model") {
        return;
    }
    let backend = HighsBackend::new();
    let model = model(Domain::Continuous, "warm-basis");
    let (_, basis) = backend
        .solve_with_basis(
            &model,
            &options(),
            &optimizer_core::CancellationToken::new(),
            None,
        )
        .expect("lp solve");
    let basis = basis.expect("an LP solve yields a basis");
    assert_eq!(basis.columns.len(), 2);
    assert_eq!(basis.rows.len(), 1);

    // Replaying the basis against its own model is accepted.
    let record = backend
        .solve(
            &model,
            &options(),
            &optimizer_core::CancellationToken::new(),
            Some(WarmStart::Basis(&basis)),
        )
        .expect("basis warm start");
    assert_eq!(record.termination, Termination::Optimal);

    // A basis is bound to canonical data, not merely to a matching identity.
    let mut altered = model.document().clone();
    altered.constraints[0].upper = finite(1.25);
    let altered = Model::new(altered).expect("model");
    assert_eq!(
        backend
            .solve(
                &altered,
                &options(),
                &optimizer_core::CancellationToken::new(),
                Some(WarmStart::Basis(&basis)),
            )
            .expect_err("changed data must reject the basis")
            .kind,
        ErrorKind::Unsupported
    );

    // Mismatched dimensions are rejected explicitly.
    let wrong = Basis {
        schema_version: SOLVE_SCHEMA_VERSION,
        model_id: "warm-basis".to_string(),
        model_fingerprint: model.fingerprint().expect("fingerprint"),
        columns: vec![BasisStatus::Basic],
        rows: vec![],
    };
    assert_eq!(
        backend
            .solve(
                &model,
                &options(),
                &optimizer_core::CancellationToken::new(),
                Some(WarmStart::Basis(&wrong)),
            )
            .expect_err("dimension mismatch must be rejected")
            .kind,
        ErrorKind::Unsupported
    );
}

// Requirement 2: repeated lifecycles create and destroy native state cleanly.
#[test]
fn repeated_solves_use_fresh_native_state() {
    if !require_native("repeated_solves_use_fresh_native_state") {
        return;
    }
    let backend = HighsBackend::new();
    let model = model(Domain::Continuous, "lifecycle");
    let mut objectives = Vec::new();
    for _ in 0..16 {
        let record = backend
            .solve(
                &model,
                &options(),
                &optimizer_core::CancellationToken::new(),
                None,
            )
            .expect("solve");
        objectives.push(record.objective.expect("objective"));
    }
    // Deterministic configuration must give a deterministic outcome.
    assert!(
        objectives.windows(2).all(|pair| pair[0] == pair[1]),
        "repeated solves diverged: {objectives:?}"
    );
}

// Requirement 11: records round trip and never substitute null for a number.
#[test]
fn records_round_trip_and_omit_absent_measurements() {
    if !require_native("records_round_trip_and_omit_absent_measurements") {
        return;
    }
    let record = HighsBackend::new()
        .solve(
            &model(Domain::Continuous, "record"),
            &options(),
            &optimizer_core::CancellationToken::new(),
            None,
        )
        .expect("solve");

    let json = record.to_json().expect("serialize");
    let parsed = SolveRecord::from_json(json.as_bytes()).expect("deserialize");
    assert_eq!(parsed, record);
    // Enough configuration and provenance to repeat the solve.
    assert_eq!(parsed.options, record.options);
    assert!(!parsed.backend_version.is_empty());

    // An absent measurement is omitted rather than serialized as null. This
    // governs the record's own measurements; the nested M1 report keeps its
    // SPEC-0001 semantics, where an unbounded side is explicitly null.
    let mut absent = record.clone();
    absent.gap = None;
    absent.best_bound = None;
    absent.objective = None;
    absent.native_status = None;
    absent.candidate = None;
    absent.validation = None;
    let json = absent.to_json().expect("serialize");
    for field in [
        "\"gap\"",
        "\"best_bound\"",
        "\"objective\"",
        "\"native_status\"",
        "\"candidate\"",
        "\"validation\"",
    ] {
        assert!(
            !json.contains(field),
            "absent {field} must be omitted, not null: {json}"
        );
    }

    // A nonfinite measurement is a numerical error, not a null.
    let mut nonfinite = record.clone();
    nonfinite.gap = Some(f64::INFINITY);
    assert_eq!(
        nonfinite
            .to_json()
            .expect_err("nonfinite must not serialize")
            .kind,
        ErrorKind::Numerical
    );
}

// Requirement 3: input beyond the native integer range is rejected explicitly.
#[test]
fn coefficients_below_the_native_threshold_are_rejected() {
    if !require_native("coefficients_below_the_native_threshold_are_rejected") {
        return;
    }
    let mut document = model(Domain::Continuous, "tiny-coefficient")
        .document()
        .clone();
    // HiGHS would drop this entry; changing the model silently is not allowed.
    document.constraints[0].terms[0].coefficient = 1e-12;
    let model = Model::new(document).expect("model");

    assert_eq!(
        HighsBackend::new()
            .solve(
                &model,
                &options(),
                &optimizer_core::CancellationToken::new(),
                None
            )
            .expect_err("tiny coefficient must be rejected")
            .kind,
        ErrorKind::Unsupported
    );
}
