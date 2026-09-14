//! Acceptance for the first-order backend against the pinned one, mapped to
//! SPEC-0011 requirement numbers.
//!
//! These live in this crate rather than in `optimizer-lp` because the comparison
//! needs both backends, and the dependency must point this way: `optimizer-lp`
//! must not take a dependency on the pinned adapter, or the oracle would be
//! entangled with the thing it is an oracle for.
//!
//! Requirement 23 applies throughout: nothing here records a timing, and no test
//! asserts that either implementation is faster than the other.

use optimizer_core::{
    Backend, Bound, CancellationToken, Constraint, Domain, LinearTerm, Model, ModelDocument,
    Objective, ObjectiveSense, ProblemClass, SOLVE_SCHEMA_VERSION, SolveOptions, Termination,
    Tolerances, Variable, WarmStart,
};
use optimizer_highs::{HighsBackend, is_native};
use optimizer_lp::{HostLpBackend, LpSettings};

fn tolerances() -> Tolerances {
    Tolerances {
        absolute: 1e-6,
        relative: 1e-6,
        integrality: 1e-7,
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

fn settings() -> LpSettings {
    LpSettings::published(50_000, 200)
}

fn finite(value: f64) -> Bound {
    Bound::Finite { value }
}

/// The same four shapes the pinned adapter's differential acceptance uses:
/// a one-sided LP, an objective offset, an equality and a ranged row.
fn model(
    model_id: &str,
    domain: Domain,
    upper: f64,
    row: (Bound, Bound),
    cost: [f64; 2],
    offset: f64,
) -> Model {
    Model::new(ModelDocument {
        schema_version: optimizer_core::SCHEMA_VERSION,
        model_id: model_id.to_string(),
        variables: (0..2)
            .map(|id| Variable {
                id,
                domain,
                lower: finite(0.0),
                upper: finite(upper),
            })
            .collect(),
        constraints: vec![Constraint {
            id: 0,
            lower: row.0,
            upper: row.1,
            terms: (0..2)
                .map(|variable_id| LinearTerm {
                    variable_id,
                    coefficient: 1.0,
                })
                .collect(),
        }],
        objective: Objective {
            sense: ObjectiveSense::Minimize,
            offset,
            terms: (0..2)
                .map(|variable_id| LinearTerm {
                    variable_id,
                    coefficient: cost[variable_id as usize],
                })
                .collect(),
        },
    })
    .expect("a valid model")
}

fn fixtures() -> Vec<(&'static str, Model)> {
    vec![
        (
            "lp-upper",
            model(
                "lp-upper",
                Domain::Continuous,
                1.0,
                (Bound::NegativeInfinity, finite(1.5)),
                [-1.0, -1.0],
                0.0,
            ),
        ),
        (
            "lp-offset",
            model(
                "lp-offset",
                Domain::Continuous,
                1.0,
                (Bound::NegativeInfinity, finite(1.5)),
                [-1.0, -3.0],
                2.5,
            ),
        ),
        (
            "lp-equality",
            model(
                "lp-equality",
                Domain::Continuous,
                1.0,
                (finite(1.0), finite(1.0)),
                [1.0, 1.0],
                0.0,
            ),
        ),
        (
            "lp-ranged",
            model(
                "lp-ranged",
                Domain::Continuous,
                1.0,
                (finite(0.5), finite(1.5)),
                [-2.0, 1.0],
                0.0,
            ),
        ),
    ]
}

fn skip(name: &str) -> bool {
    if is_native() {
        return false;
    }
    eprintln!("SKIP {name}: HiGHS not provisioned; run bash tools/setup_highs.sh");
    true
}

/// Requirement 21: agreement with the pinned backend on objective value.
#[test]
fn the_first_order_backend_agrees_with_the_pinned_backend_on_objective_value() {
    if skip("the_first_order_backend_agrees_with_the_pinned_backend_on_objective_value") {
        return;
    }
    let pinned = HighsBackend::new();
    let first_order = HostLpBackend::new(settings()).expect("valid settings");
    for (name, model) in fixtures() {
        let reference = pinned
            .solve(&model, &options(), &CancellationToken::new(), None)
            .expect("the pinned backend solves");
        let approximate = first_order
            .solve(&model, &options(), &CancellationToken::new(), None)
            .expect("the first-order backend solves");

        let expected = reference.objective.expect("a reference objective");
        let actual = approximate
            .objective
            .unwrap_or_else(|| panic!("{name}: the first-order backend published no objective"));
        assert!(
            (expected - actual).abs() <= 1e-5 * expected.abs().max(1.0),
            "{name}: {actual} disagrees with the pinned backend's {expected}"
        );
    }
}

/// Requirement 21's second half: the comparison is known to be able to fail.
///
/// Without this the agreement test above would be consistent with a backend that
/// never disagrees with anything, including one ignoring the model. A single
/// coefficient is changed, which moves the optimum, and the comparison against the
/// *unmutated* reference is required to fail.
#[test]
fn a_mutated_instance_is_shown_to_disagree() {
    if skip("a_mutated_instance_is_shown_to_disagree") {
        return;
    }
    let pinned = HighsBackend::new();
    let first_order = HostLpBackend::new(settings()).expect("valid settings");

    let original = model(
        "lp-upper",
        Domain::Continuous,
        1.0,
        (Bound::NegativeInfinity, finite(1.5)),
        [-1.0, -1.0],
        0.0,
    );
    let reference = pinned
        .solve(&original, &options(), &CancellationToken::new(), None)
        .expect("solves")
        .objective
        .expect("an objective");

    // Same identity, different objective coefficient: the optimum moves.
    let mut document = original.document().clone();
    document.objective.terms[1].coefficient = -5.0;
    let mutated = Model::new(document).expect("still valid");
    let moved = first_order
        .solve(&mutated, &options(), &CancellationToken::new(), None)
        .expect("solves")
        .objective
        .expect("an objective");

    assert!(
        (reference - moved).abs() > 1e-3,
        "the mutated instance must disagree, or the agreement test proves nothing"
    );
}

/// Requirement 3: a discrete model is refused here and solved by the pinned
/// backend. The pair is the point -- it shows the refusal is a capability
/// boundary rather than a defect.
#[test]
fn a_binary_model_is_unsupported_here_and_solved_by_the_cpu_backend() {
    let discrete = model(
        "milp",
        Domain::Binary,
        1.0,
        (Bound::NegativeInfinity, finite(1.5)),
        [-1.0, -1.0],
        0.0,
    );
    let first_order = HostLpBackend::new(settings()).expect("valid settings");

    assert!(
        !first_order.capabilities().accepts(&discrete),
        "the declaration must not claim a discrete model"
    );
    let refused = first_order
        .solve(&discrete, &options(), &CancellationToken::new(), None)
        .expect("a refusal is an outcome, not an error");
    assert_eq!(refused.termination, Termination::Unsupported);
    assert!(refused.candidate.is_none());
    assert!(refused.best_bound.is_none());

    if skip("a_binary_model_is_unsupported_here_and_solved_by_the_cpu_backend") {
        return;
    }
    let solved = HighsBackend::new()
        .solve(&discrete, &options(), &CancellationToken::new(), None)
        .expect("the pinned backend solves it");
    assert_eq!(solved.termination, Termination::Optimal);
}

/// Requirement 14: `Optimal` needs both a validated candidate and a certified
/// bound, and requirement 15 keeps the published objective the core's own
/// recomputation rather than the method's.
#[test]
fn optimal_requires_a_certified_bound_and_a_validated_candidate() {
    let first_order = HostLpBackend::new(settings()).expect("valid settings");
    let model = model(
        "lp-upper",
        Domain::Continuous,
        1.0,
        (Bound::NegativeInfinity, finite(1.5)),
        [-1.0, -1.0],
        0.0,
    );
    let record = first_order
        .solve(&model, &options(), &CancellationToken::new(), None)
        .expect("solves");

    // Every fixture here does reach optimality today. Asserting it keeps the
    // branch below from silently becoming dead code: without this a regression
    // that stopped certifying would make the test pass by taking the other path.
    assert_eq!(
        record.termination,
        Termination::Optimal,
        "this fixture must close, or the assertions below test nothing"
    );

    if record.termination == Termination::Optimal {
        let bound = record
            .best_bound
            .expect("optimal requires a certified bound");
        let objective = record.objective.expect("optimal requires a candidate");
        let report = record.validation.expect("optimal requires a validation");
        assert!(report.feasible, "the candidate must have been accepted");
        assert_eq!(
            objective, report.objective,
            "the published objective must be the validation's recomputation"
        );
        assert!(
            bound <= objective + tolerances().absolute,
            "a bound above the incumbent must not close"
        );
    } else {
        // Not reaching optimality is a permitted outcome for an approximate
        // method, but it must then claim nothing: requirement 16.
        assert!(!record.termination.proves_completion());
    }
}

/// Requirements 9 and 10: the record carries the settings that produced it.
#[test]
fn the_record_carries_the_settings_that_produced_it() {
    let first_order = HostLpBackend::new(settings()).expect("valid settings");
    let model = model(
        "lp-upper",
        Domain::Continuous,
        1.0,
        (Bound::NegativeInfinity, finite(1.5)),
        [-1.0, -1.0],
        0.0,
    );
    let record = first_order
        .solve(&model, &options(), &CancellationToken::new(), None)
        .expect("solves");
    let recorded = record
        .lp_settings
        .expect("a first-order record has settings");
    assert_eq!(recorded, settings());
    assert_eq!(recorded.check_interval, settings().check_interval);
    assert_eq!(recorded.preconditioner, settings().preconditioner);

    // The record round trips through its own parser with the settings intact,
    // so the block is genuinely part of the document rather than a field the
    // serializer drops.
    let json = record.to_json().expect("serializable");
    let parsed = optimizer_core::SolveRecord::from_json(json.as_bytes()).expect("round trip");
    assert_eq!(parsed.lp_settings, Some(settings()));
}

/// The pinned adapter is not a first-order method and must not claim settings.
#[test]
fn the_pinned_backend_records_no_first_order_settings() {
    if skip("the_pinned_backend_records_no_first_order_settings") {
        return;
    }
    let record = HighsBackend::new()
        .solve(
            &model(
                "lp-upper",
                Domain::Continuous,
                1.0,
                (Bound::NegativeInfinity, finite(1.5)),
                [-1.0, -1.0],
                0.0,
            ),
            &options(),
            &CancellationToken::new(),
            None,
        )
        .expect("solves");
    assert!(record.lp_settings.is_none());
}

/// ADR-0010: this backend produces no basis and cannot consume one, so a basis
/// warm start is recorded as ignored rather than silently dropped.
#[test]
fn a_basis_warm_start_is_recorded_as_ignored() {
    let first_order = HostLpBackend::new(settings()).expect("valid settings");
    let model = model(
        "lp-upper",
        Domain::Continuous,
        1.0,
        (Bound::NegativeInfinity, finite(1.5)),
        [-1.0, -1.0],
        0.0,
    );
    let basis = optimizer_core::Basis {
        schema_version: SOLVE_SCHEMA_VERSION,
        model_id: "lp-upper".to_string(),
        model_fingerprint: model.fingerprint().expect("fingerprints"),
        columns: vec![optimizer_core::BasisStatus::Lower; 2],
        rows: vec![optimizer_core::BasisStatus::Basic],
    };
    let record = first_order
        .solve(
            &model,
            &options(),
            &CancellationToken::new(),
            Some(WarmStart::Basis(&basis)),
        )
        .expect("solves");
    assert!(
        record.warnings.iter().any(|w| w.contains("basis")),
        "an ignored warm start must be recorded, not dropped: {:?}",
        record.warnings
    );
}

/// Requirement 1: the declaration is checked against what the backend accepts.
#[test]
fn the_first_order_declaration_matches_what_it_accepts() {
    let first_order = HostLpBackend::new(settings()).expect("valid settings");
    let declared = first_order.capabilities();
    assert_eq!(declared.problem_classes(), [ProblemClass::Continuous]);
    assert_eq!(declared.device(), optimizer_core::DeviceClass::Cpu);
    assert_eq!(declared.arithmetic(), optimizer_core::Arithmetic::F64);

    let continuous = model(
        "lp-upper",
        Domain::Continuous,
        1.0,
        (Bound::NegativeInfinity, finite(1.5)),
        [-1.0, -1.0],
        0.0,
    );
    let record = first_order
        .solve(&continuous, &options(), &CancellationToken::new(), None)
        .expect("solves");
    assert_ne!(record.termination, Termination::Unsupported);
}

/// Cancellation is observed, and a cancelled solve claims nothing.
#[test]
fn a_cancelled_solve_claims_nothing() {
    let first_order = HostLpBackend::new(settings()).expect("valid settings");
    let model = model(
        "lp-upper",
        Domain::Continuous,
        1.0,
        (Bound::NegativeInfinity, finite(1.5)),
        [-1.0, -1.0],
        0.0,
    );
    let cancel = CancellationToken::new();
    cancel.cancel();
    let record = first_order
        .solve(&model, &options(), &cancel, None)
        .expect("a cancelled solve is an outcome");
    assert_eq!(record.termination, Termination::Interrupted);
    assert!(!record.termination.proves_completion());
    assert!(record.best_bound.is_none());
}

// ---------------------------------------------------------------------------
// SPEC-0011 requirements 17 and 22, and ADR-0010's two able-to-fail tests.
// ---------------------------------------------------------------------------

/// Requirement 22: the certified bound is valid and strictly weaker than the
/// pinned backend's on at least one instance.
///
/// ADR-0010 names this as one of the two tests that can fail, and the reason is
/// that a certificate which only ever agrees has not been shown to be a
/// certificate. It is asserted on a deliberately early-stopped iterate, which is
/// also what requirement 13 wants: at convergence the two bounds can round to the
/// same `f64` -- the pinned backend sets its bound equal to the objective for a
/// continuous LP -- and the assertion would then turn on rounding rather than on
/// the procedure.
#[test]
fn the_certified_bound_is_valid_and_strictly_weaker_than_the_pinned_backends() {
    if skip("the_certified_bound_is_valid_and_strictly_weaker_than_the_pinned_backends") {
        return;
    }
    let model = model(
        "lp-upper",
        Domain::Continuous,
        1.0,
        (Bound::NegativeInfinity, finite(1.5)),
        [-1.0, -3.0],
        0.0,
    );
    let reference = HighsBackend::new()
        .solve(&model, &options(), &CancellationToken::new(), None)
        .expect("solves");
    let optimum = reference.objective.expect("an objective");
    let pinned_bound = reference
        .best_bound
        .expect("the pinned backend proves a bound");

    // Stopped long before convergence, so the dual iterate is a poor guess.
    let program = optimizer_lp::LinearProgram::new(&model).expect("continuous");
    let stopped = LpSettings::published(3, 1);
    let engine = optimizer_lp::Engine::new(&program, stopped);
    let (iterate, _) = engine.run(&CancellationToken::new(), |_| {
        optimizer_lp::Decision::Continue
    });
    let certificate =
        optimizer_lp::certify(&program, &iterate.dual).expect("a boxed program certifies");

    assert!(
        certificate.bound <= optimum + 1e-9,
        "the certified bound {} must not exceed the optimum {optimum}",
        certificate.bound
    );
    assert!(
        certificate.bound < pinned_bound,
        "an early-stopped certificate must be strictly weaker than the pinned \
         backend's {pinned_bound}, or it has not been shown to be a certificate: {}",
        certificate.bound
    );
}

/// ADR-0010's other able-to-fail test: an iterate claiming a better-than-optimal
/// answer is refused twice, and moves nothing.
///
/// A wrong kernel's most dangerous output is not a crash but a plausible number
/// better than the truth. Two independent host computations stand in its way, and
/// this asserts both: `Model::evaluate` refuses the candidate, so no objective is
/// published, and certification refuses to turn the same iterate into a bound
/// below the true optimum.
#[test]
fn an_iterate_claiming_better_than_optimal_is_refused_and_moves_nothing() {
    if skip("an_iterate_claiming_better_than_optimal_is_refused_and_moves_nothing") {
        return;
    }
    let model = model(
        "lp-upper",
        Domain::Continuous,
        1.0,
        (Bound::NegativeInfinity, finite(1.5)),
        [-1.0, -3.0],
        0.0,
    );
    let optimum = HighsBackend::new()
        .solve(&model, &options(), &CancellationToken::new(), None)
        .expect("solves")
        .objective
        .expect("an objective");

    // What a mutated kernel would produce: a point outside the row bound, whose
    // objective is better than any feasible point's.
    let fabricated = optimizer_core::Candidate {
        schema_version: optimizer_core::SCHEMA_VERSION,
        model_id: "lp-upper".to_string(),
        values: vec![
            optimizer_core::Assignment {
                variable_id: 0,
                value: 1.0,
            },
            optimizer_core::Assignment {
                variable_id: 1,
                value: 1.0,
            },
        ],
    };
    let report = model
        .evaluate(&fabricated, tolerances())
        .expect("evaluation itself succeeds");
    assert!(
        report.objective < optimum,
        "the fabricated point must look better than the optimum, or this test is \
         not exercising the hazard"
    );
    assert!(
        !report.feasible,
        "the host must refuse a candidate outside the model's own constraints"
    );

    // And no dual vector -- however the device arrived at it -- turns into a bound
    // below the true optimum. Certification is valid for an arbitrary vector, so
    // this is checked over adversarial ones rather than one convenient one.
    let program = optimizer_lp::LinearProgram::new(&model).expect("continuous");
    for multiplier in [0.0, -1.0, -1e9, 1e9, 12.5] {
        let certificate =
            optimizer_lp::certify(&program, &[multiplier]).expect("a boxed program certifies");
        assert!(
            certificate.bound <= optimum + 1e-9,
            "multiplier {multiplier} produced {} above the optimum {optimum}",
            certificate.bound
        );
    }
}

/// Requirement 17: used as a relaxation, a non-`Optimal` termination forfeits the
/// proof claim and prunes nothing by bound.
///
/// The executive already enforces this for any backend, and C2's contracts are
/// where it is established. What is asserted here is that this backend actually
/// produces such a termination -- a backend that always returned `Optimal` would
/// satisfy requirement 17 vacuously.
#[test]
fn an_iteration_limited_solve_claims_no_proof() {
    let model = model(
        "lp-upper",
        Domain::Continuous,
        1.0,
        (Bound::NegativeInfinity, finite(1.5)),
        [-1.0, -3.0],
        0.0,
    );
    // One iteration cannot converge, so this must not close.
    let backend = HostLpBackend::new(LpSettings::published(1, 1)).expect("valid settings");
    let record = backend
        .solve(&model, &options(), &CancellationToken::new(), None)
        .expect("solves");
    assert_ne!(record.termination, Termination::Optimal);
    assert!(
        !record.termination.proves_completion(),
        "a limited solve must claim no completed proof"
    );
}

/// Requirement 23: no acceptance artifact records a timing.
///
/// Elapsed time is present in a record as a diagnostic, which SPEC-0005 already
/// fixes, and nothing in this suite asserts on it. This states that rule where a
/// later edit would see it, because the easiest way to breach requirement 23 is to
/// add a comparison that looks harmless.
#[test]
fn no_assertion_in_this_suite_depends_on_a_measured_time() {
    let source = include_str!("first_order.rs");
    for line in source.lines() {
        let assertion = line.trim_start().starts_with("assert");
        if assertion && line.contains("elapsed_ms") {
            panic!("an acceptance assertion must not depend on a measured time: {line}");
        }
    }
}

/// GPUP-1: a positive maximization gap can close under relative tolerance.
#[test]
fn a_maximization_solve_reports_a_conservative_positive_gap() {
    let backend = HostLpBackend::new(LpSettings::published(1, 1)).unwrap();

    let model = Model::new(ModelDocument {
        schema_version: optimizer_core::SCHEMA_VERSION,
        model_id: "max-positive-gap".into(),
        variables: vec![Variable {
            id: 0,
            domain: Domain::Continuous,
            lower: finite(0.0),
            upper: finite(1.0),
        }],
        constraints: vec![Constraint {
            id: 0,
            lower: finite(0.0),
            upper: finite(1.0),
            terms: vec![LinearTerm {
                variable_id: 0,
                coefficient: 1.0,
            }],
        }],
        objective: Objective {
            sense: ObjectiveSense::Maximize,
            offset: 0.0,
            terms: vec![LinearTerm {
                variable_id: 0,
                coefficient: 1.0,
            }],
        },
    })
    .unwrap();
    let mut options = options();
    options.tolerances.absolute = 0.0;
    options.tolerances.relative = 0.75;
    let result = backend
        .solve(&model, &options, &CancellationToken::new(), None)
        .unwrap();
    assert_eq!(result.termination, Termination::Optimal);
    assert!(result.validation.as_ref().unwrap().feasible);
    assert!(
        result.objective.unwrap() < 1.0,
        "must exercise a nonzero gap"
    );
    assert!(result.best_bound.unwrap() >= 1.0);
    let gap = result.gap.unwrap();
    assert!(gap > 0.0 && gap <= 0.75);
    assert!(gap >= result.best_bound.unwrap() - result.objective.unwrap());
}
