//! End-to-end acceptance for the C2 executive over the pinned HiGHS backend.
//!
//! The SPEC-0003 contract tests in optimizer-solver deliberately use test
//! backends, because that crate must not depend on any particular backend.
//! This test closes the remaining gap: it drives the real executive over the
//! real native relaxation service and checks the proven optimum against an
//! independent brute-force enumeration of the discrete assignment space.
//!
//! It lives here, not in optimizer-solver, so that crate keeps its
//! backend-neutrality guarantee.

use optimizer_core::{
    Assignment, Bound, CancellationToken, Candidate, Constraint, Domain, LinearTerm, Model,
    ModelDocument, Objective, ObjectiveSense, SOLVE_SCHEMA_VERSION, SolveOptions, Tolerances,
    Variable,
};
use optimizer_extension::{EXTENSION_SCHEMA_VERSION, ExtensionPolicy, Registration};
use optimizer_extension_examples::{BadAdvice, BadProposal, HostileAdviser, HostileProducer};
use optimizer_highs::{HighsBackend, is_native};
use optimizer_solver::{
    SEARCH_SCHEMA_VERSION, SearchOptions, SearchOutcome, search, search_with_extensions,
};

fn tolerances() -> Tolerances {
    Tolerances {
        absolute: 1e-7,
        relative: 1e-9,
        integrality: 1e-6,
    }
}

fn options() -> SearchOptions {
    SearchOptions {
        schema_version: SEARCH_SCHEMA_VERSION,
        seed: 17,
        node_limit: Some(5_000),
        time_limit_ms: Some(30_000),
        open_node_limit: Some(5_000),
        improvement_tolerance: 1e-9,
        relaxation: SolveOptions {
            schema_version: SOLVE_SCHEMA_VERSION,
            seed: 17,
            time_limit_ms: None,
            iteration_limit: None,
            node_limit: None,
            tolerances: tolerances(),
            threads: 1,
        },
        extensions: Vec::new(),
    }
}

/// Skip a native-only test loudly rather than reporting false coverage.
fn require_native(test: &str) -> bool {
    if is_native() {
        return true;
    }
    eprintln!("SKIP {test}: HiGHS not provisioned; run bash tools/setup_highs.sh");
    false
}

fn knapsack(model_id: &str, weights: &[f64], values: &[f64], capacity: f64) -> Model {
    let variables = (0..weights.len())
        .map(|index| Variable {
            id: u32::try_from(index).expect("small index"),
            domain: Domain::Binary,
            lower: Bound::Finite { value: 0.0 },
            upper: Bound::Finite { value: 1.0 },
        })
        .collect();
    let terms = |coefficients: &[f64]| {
        coefficients
            .iter()
            .enumerate()
            .map(|(index, coefficient)| LinearTerm {
                variable_id: u32::try_from(index).expect("small index"),
                coefficient: *coefficient,
            })
            .collect::<Vec<_>>()
    };
    Model::new(ModelDocument {
        schema_version: optimizer_core::SCHEMA_VERSION,
        model_id: model_id.to_string(),
        variables,
        constraints: vec![Constraint {
            id: 0,
            lower: Bound::NegativeInfinity,
            upper: Bound::Finite { value: capacity },
            terms: terms(weights),
        }],
        objective: Objective {
            sense: ObjectiveSense::Maximize,
            offset: 0.0,
            terms: terms(values),
        },
    })
    .expect("model")
}

/// Independent enumeration over every subset, sharing no code with the engine.
fn best_subset(weights: &[f64], values: &[f64], capacity: f64) -> f64 {
    let mut best = f64::NEG_INFINITY;
    for mask in 0u32..(1 << weights.len()) {
        let mut weight = 0.0;
        let mut value = 0.0;
        for index in 0..weights.len() {
            if mask & (1 << index) != 0 {
                weight += weights[index];
                value += values[index];
            }
        }
        if weight <= capacity + 1e-9 && value > best {
            best = value;
        }
    }
    best
}

/// The executive proves the optimum that exhaustive enumeration finds, using
/// the pinned native library as its relaxation service.
#[test]
fn executive_matches_enumeration_over_native_relaxations() {
    if !require_native("executive_matches_enumeration_over_native_relaxations") {
        return;
    }
    let backend = HighsBackend::new();
    let cancel = CancellationToken::new();

    let cases: &[(&str, &[f64], &[f64], f64)] = &[
        ("knap-a", &[3.0, 4.0, 5.0, 2.0], &[4.0, 5.0, 8.0, 3.0], 9.0),
        (
            "knap-b",
            &[2.0, 3.0, 7.0, 1.0, 4.0],
            &[3.0, 4.0, 9.0, 1.0, 6.0],
            10.0,
        ),
        ("knap-c", &[5.0, 5.0, 5.0], &[7.0, 6.0, 5.0], 4.0),
    ];

    for (model_id, weights, values, capacity) in cases {
        let model = knapsack(model_id, weights, values, *capacity);
        let record = search(&model, &options(), &backend, &cancel).expect("search");

        assert_eq!(
            record.outcome,
            SearchOutcome::ProvenOptimal,
            "{model_id}: expected a completed proof, got {:?}",
            record.outcome
        );
        assert!(
            !record.forfeited,
            "{model_id}: a clean search must not forfeit"
        );
        assert!(record.outcome.proves_completion());

        let expected = best_subset(weights, values, *capacity);
        let found = record.objective.expect("an optimum has an objective");
        assert!(
            (found - expected).abs() <= 1e-6,
            "{model_id}: engine {found} vs enumeration {expected}"
        );

        // The published incumbent must itself satisfy the original model.
        let candidate = record.candidate.as_ref().expect("incumbent");
        let report = model.evaluate(candidate, tolerances()).expect("report");
        assert!(report.feasible, "{model_id}: incumbent must be feasible");
        assert!(
            (report.objective - expected).abs() <= 1e-6,
            "{model_id}: recomputed objective disagrees with enumeration"
        );

        // The record must be reproducible and free of nonfinite measurements.
        let json = record.to_json().expect("serializable");
        assert!(json.contains("\"outcome\": \"proven_optimal\""));
    }
}

/// A model whose discrete restrictions cannot be satisfied is proven infeasible
/// through native relaxations, with no incumbent attached.
#[test]
fn native_search_proves_infeasibility() {
    if !require_native("native_search_proves_infeasibility") {
        return;
    }
    // Two binaries, each at most 1, required to sum to at least 3.
    let model = Model::new(ModelDocument {
        schema_version: optimizer_core::SCHEMA_VERSION,
        model_id: "native-infeasible".to_string(),
        variables: vec![
            Variable {
                id: 0,
                domain: Domain::Binary,
                lower: Bound::Finite { value: 0.0 },
                upper: Bound::Finite { value: 1.0 },
            },
            Variable {
                id: 1,
                domain: Domain::Binary,
                lower: Bound::Finite { value: 0.0 },
                upper: Bound::Finite { value: 1.0 },
            },
        ],
        constraints: vec![Constraint {
            id: 0,
            lower: Bound::Finite { value: 3.0 },
            upper: Bound::PositiveInfinity,
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
            terms: vec![LinearTerm {
                variable_id: 0,
                coefficient: 1.0,
            }],
        },
    })
    .expect("model");

    let record = search(
        &model,
        &options(),
        &HighsBackend::new(),
        &CancellationToken::new(),
    )
    .expect("search");

    assert_eq!(record.outcome, SearchOutcome::ProvenInfeasible);
    assert!(record.candidate.is_none());
    assert!(record.objective.is_none());
    assert!(!record.forfeited);
}

/// A pre-cancelled search performs no native work, exactly as it performs no
/// stub work: the rule is the executive's, not the backend's.
#[test]
fn native_search_honors_pre_cancellation() {
    if !require_native("native_search_honors_pre_cancellation") {
        return;
    }
    let model = knapsack("cancelled", &[1.0, 2.0], &[1.0, 2.0], 2.0);
    let cancel = CancellationToken::new();
    cancel.cancel();

    let record = search(&model, &options(), &HighsBackend::new(), &cancel).expect("search");
    assert_eq!(record.outcome, SearchOutcome::Interrupted);
    assert_eq!(record.relaxations_solved, 0);
    assert!(!record.outcome.proves_completion());
}

/// A warm-start candidate is unused here, but the executive must still accept a
/// model whose incumbent it discovers itself and re-validate it independently.
#[test]
fn native_incumbents_are_revalidated_against_the_original_model() {
    if !require_native("native_incumbents_are_revalidated_against_the_original_model") {
        return;
    }
    let model = knapsack("revalidate", &[4.0, 3.0, 2.0], &[6.0, 4.0, 3.0], 5.0);
    let record = search(
        &model,
        &options(),
        &HighsBackend::new(),
        &CancellationToken::new(),
    )
    .expect("search");

    let objective = record.objective;
    let validation = record.validation.expect("an incumbent carries its report");
    assert!(validation.feasible);
    assert_eq!(validation.model_id, "revalidate");
    // The record's objective is the independently recomputed one.
    assert_eq!(objective, Some(validation.objective));

    let candidate: Candidate = record.candidate.expect("incumbent");
    let ids: Vec<u32> = candidate.values.iter().map(|v| v.variable_id).collect();
    assert_eq!(ids, vec![0, 1, 2]);
    for Assignment { value, .. } in &candidate.values {
        assert!(
            (value - value.round()).abs() <= 1e-6,
            "a binary incumbent must be integral"
        );
    }
}

/// C3 end to end: adversarial extensions cannot change a native search's proof.
///
/// The SPEC-0004 contracts in optimizer-extension and the acceptance suite in
/// optimizer-extension-examples run over test backends. This closes the
/// remaining gap: the real executive, the real native relaxation service, and
/// extensions that lie, panic and misadvise, checked against independent
/// enumeration.
#[test]
fn native_search_is_unaffected_by_hostile_extensions() {
    if !require_native("native_search_is_unaffected_by_hostile_extensions") {
        return;
    }
    let backend = HighsBackend::new();
    let model = knapsack(
        "native-extensions",
        &[3.0, 4.0, 5.0, 2.0],
        &[4.0, 5.0, 8.0, 3.0],
        9.0,
    );
    let expected = best_subset(&[3.0, 4.0, 5.0, 2.0], &[4.0, 5.0, 8.0, 3.0], 9.0);

    let plain = search(&model, &options(), &backend, &CancellationToken::new()).expect("search");
    assert_eq!(plain.outcome, SearchOutcome::ProvenOptimal);

    let policy = |extension_id: &str| ExtensionPolicy {
        schema_version: EXTENSION_SCHEMA_VERSION,
        extension_id: extension_id.to_string(),
        invocation_budget: 10_000,
        proposal_budget: 10_000,
    };

    // A producer whose every candidate is infeasible, an adviser that names a
    // node the search never created, and one that panics on first contact.
    let liar = HostileProducer::new(BadProposal::OutOfBounds);
    let ghost = HostileAdviser::new(BadAdvice::NonexistentNode);
    let bomb = HostileAdviser::new(BadAdvice::Panic);

    let mut configuration = options();
    configuration.extensions = vec![
        policy(liar.declare_id()),
        policy(ghost.declare_id()),
        policy(bomb.declare_id()),
    ];

    let record = search_with_extensions(
        &model,
        &configuration,
        &[
            Registration::Producer(&liar),
            Registration::Adviser(&ghost),
            Registration::Adviser(&bomb),
        ],
        &backend,
        &CancellationToken::new(),
    )
    .expect("a hostile extension must never make a search fail");

    assert_eq!(
        record.outcome,
        SearchOutcome::ProvenOptimal,
        "hostile extensions must not deny a proof the engine can complete"
    );
    assert!(!record.forfeited, "no extension path may forfeit");
    let found = record.objective.expect("an optimum has an objective");
    assert!(
        (found - expected).abs() <= 1e-6,
        "engine {found} vs enumeration {expected}"
    );
    assert_eq!(
        record.objective, plain.objective,
        "the proven optimum is identical with and without extensions"
    );

    // Every one of them was consulted and every one of them was refused.
    assert_eq!(record.extensions.len(), 3, "all three are summarized");
    assert!(
        record
            .extensions
            .iter()
            .all(|summary| summary.registered && summary.accepted == 0),
        "each was admitted and had nothing accepted: {:?}",
        record.extensions
    );
    assert!(
        record
            .extensions
            .iter()
            .any(|summary| !summary.failures.is_empty()),
        "the refusals are recorded rather than absorbed silently"
    );

    // The published incumbent still satisfies the original model.
    let candidate = record.candidate.as_ref().expect("incumbent");
    let report = model.evaluate(candidate, tolerances()).expect("report");
    assert!(report.feasible);
    assert_eq!(record.objective, Some(report.objective));
}
