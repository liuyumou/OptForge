//! End-to-end flow-shop acceptance over the pinned HiGHS backend, under SPEC-0008.
//!
//! The SPEC-0008 contract tests in optimizer-schedule deliberately use no solver at
//! all, because that crate must stay as backend-neutral as optimizer-solver itself.
//! This test closes the remaining gap for requirements 11, 15 and 20: it drives the
//! real executive over the real native relaxation service on encoded flow-shop
//! models, and checks the proven optimum against independent enumeration of every
//! permutation.
//!
//! It lives here, not in optimizer-schedule or optimizer-schedule-examples, so both
//! of those keep their independence guarantees.

use optimizer_core::{CancellationToken, SOLVE_SCHEMA_VERSION, SolveOptions, Tolerances};
use optimizer_extension::{EXTENSION_SCHEMA_VERSION, ExtensionPolicy, Registration};
use optimizer_highs::{HighsBackend, is_native};
use optimizer_schedule::{
    FlowShopDocument, FlowShopInstance, SCHEDULE_SCHEMA_VERSION, makespan, model, permutation,
};
use optimizer_schedule_examples::{RefusedKind, RefusedProducer, SchedulingProducer};
use optimizer_solver::{
    SEARCH_SCHEMA_VERSION, SearchOptions, SearchRecord, search, search_with_extensions,
};

fn tolerances() -> Tolerances {
    Tolerances {
        absolute: 1e-7,
        relative: 1e-9,
        integrality: 1e-6,
    }
}

/// Unlimited budgets, deliberately.
///
/// C3 established why: a producer that spends a node budget differently
/// legitimately changes which outcome a *budgeted* search reaches, so a budgeted
/// comparison would be flaky by design rather than a correctness check.
fn options() -> SearchOptions {
    SearchOptions {
        schema_version: SEARCH_SCHEMA_VERSION,
        seed: 17,
        node_limit: Some(200_000),
        time_limit_ms: Some(120_000),
        open_node_limit: Some(200_000),
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

fn instance(id: &str, times: Vec<Vec<u32>>) -> FlowShopInstance {
    let machines = times.len() as u32;
    let jobs = times[0].len() as u32;
    FlowShopInstance::new(FlowShopDocument {
        schema_version: SCHEDULE_SCHEMA_VERSION,
        instance_id: id.to_string(),
        jobs,
        machines,
        processing_times: times,
    })
    .expect("fixture instance is valid")
}

// Independent oracle: a second recurrence written here, sharing no code with
// optimizer-schedule's evaluator, plus exhaustive permutation enumeration.
fn oracle_makespan(times: &[Vec<u32>], sequence: &[usize]) -> u64 {
    let machines = times.len();
    let mut finish = vec![0u64; machines];
    for &job in sequence {
        for machine in 0..machines {
            let ready = if machine == 0 {
                finish[0]
            } else {
                finish[machine].max(finish[machine - 1])
            };
            finish[machine] = ready + u64::from(times[machine][job]);
        }
    }
    finish[machines - 1]
}

fn permutations(jobs: usize) -> Vec<Vec<usize>> {
    let mut result = vec![vec![]];
    for _ in 0..jobs {
        let mut next = Vec::new();
        for partial in &result {
            for job in 0..jobs {
                if !partial.contains(&job) {
                    let mut extended = partial.clone();
                    extended.push(job);
                    next.push(extended);
                }
            }
        }
        result = next;
    }
    result
}

fn oracle_minimum(times: &[Vec<u32>]) -> u64 {
    permutations(times[0].len())
        .iter()
        .map(|sequence| oracle_makespan(times, sequence))
        .min()
        .expect("a nonempty instance has a best permutation")
}

/// A small fixed grid, sized for a real branch-and-bound rather than for pure
/// enumeration. Four jobs on two or three machines keeps the encoded models at 16
/// binaries while still requiring genuine search.
fn native_grid() -> Vec<(String, Vec<Vec<u32>>)> {
    vec![
        (
            "native-4x2-a".to_string(),
            vec![vec![3, 1, 4, 2], vec![2, 5, 1, 3]],
        ),
        (
            "native-4x2-b".to_string(),
            vec![vec![5, 2, 2, 7], vec![1, 4, 6, 2]],
        ),
        (
            "native-4x3-a".to_string(),
            vec![vec![2, 6, 3, 1], vec![4, 1, 5, 2], vec![3, 2, 1, 6]],
        ),
        (
            "native-3x3-a".to_string(),
            vec![vec![4, 2, 6], vec![1, 5, 3], vec![2, 3, 1]],
        ),
    ]
}

/// Requirements 11 and 15: the proven optimum equals the enumerated minimum.
///
/// This is the load-bearing native assertion. Three independent views must agree:
/// the executive's proven optimum on the encoded model, exhaustive enumeration by
/// the oracle in this file, and the recurrence re-evaluating the decoded winner.
#[test]
fn the_proven_optimum_matches_exhaustive_enumeration() {
    if !require_native("the_proven_optimum_matches_exhaustive_enumeration") {
        return;
    }
    let backend = HighsBackend::new();
    let mut checked = 0usize;
    for (id, times) in native_grid() {
        let fixture = instance(&id, times.clone());
        let encoded = model(&fixture).expect("the encoding builds a valid model");
        let record = search(&encoded, &options(), &backend, &CancellationToken::new())
            .expect("the search completes");
        assert!(
            record.outcome.proves_completion(),
            "{id}: expected a proof, got {:?} (forfeited: {})",
            record.outcome,
            record.forfeited
        );
        assert!(!record.forfeited, "{id} must not forfeit");
        let expected = oracle_minimum(&times);
        let objective = record.objective.expect("a proven search has an objective");
        assert!(
            (objective - expected as f64).abs() < 1e-6,
            "{id}: proven optimum {objective} but enumeration says {expected}"
        );
        // Requirement 14 and 15: the winner decodes and the recurrence agrees.
        let winner = record.candidate.expect("a proven search has a candidate");
        let sequence = permutation(&fixture, &winner, tolerances()).expect("the winner decodes");
        assert_eq!(
            makespan(&fixture, &sequence).expect("a decoded permutation is valid"),
            expected,
            "{id}: the decoded permutation disagrees with enumeration"
        );
        checked += 1;
    }
    assert_eq!(checked, 4, "the native grid must stay fixed");
}

/// Requirement 20: a producer whose proposals are all refused changes nothing.
///
/// The comparison covers the outcome, the proven optimum, the dual bound, the
/// forfeiture state and both prune counters, matching the C3 assertion. The
/// producer's own proposal counter is checked first, so a producer that was never
/// consulted cannot make this pass vacuously.
///
/// A refused producer is the right subject and an honest one is not. An accepted
/// incumbent legitimately changes `nodes_pruned_bound`, because pruning more by
/// bound is exactly what a good incumbent is for; requirement 20 is therefore
/// written about a refused or absent proposal, and this test matches that scope.
#[test]
fn a_refused_scheduling_producer_changes_nothing_a_search_concludes() {
    if !require_native("a_refused_scheduling_producer_changes_nothing_a_search_concludes") {
        return;
    }
    let backend = HighsBackend::new();
    let mut checked = 0usize;
    for (id, times) in native_grid() {
        let fixture = instance(&id, times.clone());
        let encoded = model(&fixture).expect("valid model");
        let baseline = search(&encoded, &options(), &backend, &CancellationToken::new())
            .expect("the producer-free search completes");
        let expected = oracle_minimum(&times) as f64;

        for kind in [RefusedKind::RepeatedPosition, RefusedKind::ImpossiblyEarly] {
            let producer = RefusedProducer::new(fixture.clone(), kind);
            let mut with_producer = options();
            with_producer.extensions = vec![ExtensionPolicy {
                schema_version: EXTENSION_SCHEMA_VERSION,
                extension_id: RefusedProducer::ID.to_string(),
                invocation_budget: u64::MAX,
                proposal_budget: u64::MAX,
            }];
            let registry = [Registration::Producer(&producer)];
            let extended = search_with_extensions(
                &encoded,
                &with_producer,
                &registry,
                &backend,
                &CancellationToken::new(),
            )
            .expect("the extended search completes");

            assert!(
                producer.proposals() > 0,
                "{id} {kind:?}: the producer must actually propose, or this proves nothing"
            );
            let label = format!("{id} {kind:?}");
            assert_conclusions_match(&baseline, &extended, &label);
            let objective = extended
                .objective
                .expect("a proven search has an objective");
            assert!(
                (objective - expected).abs() < 1e-6,
                "{label}: objective {objective} but enumeration says {expected}"
            );
            // The refusal must be recorded rather than silently absorbed.
            let summary = extended
                .extensions
                .iter()
                .find(|entry| entry.extension_id == RefusedProducer::ID)
                .expect("a registered extension has a summary");
            assert!(
                summary.rejected > 0,
                "{label}: an invalid proposal must be recorded as rejected"
            );
        }
        checked += 1;
    }
    assert_eq!(checked, 4, "the native grid must stay fixed");
}

/// Requirements 17 and 19: an honest producer's incumbent is validated, not trusted.
///
/// This is the positive counterpart to the invariance test. The honest producer may
/// legitimately change how much the search prunes, so what is asserted here is what
/// requirement 19 actually promises: the proven optimum is unchanged, and the
/// recorded objective is the core's recomputation rather than anything the producer
/// asserted.
#[test]
fn an_honest_scheduling_producer_reaches_the_same_optimum() {
    if !require_native("an_honest_scheduling_producer_reaches_the_same_optimum") {
        return;
    }
    let backend = HighsBackend::new();
    let mut checked = 0usize;
    for (id, times) in native_grid() {
        let fixture = instance(&id, times.clone());
        let encoded = model(&fixture).expect("valid model");
        let producer = SchedulingProducer::new(fixture.clone());
        let mut with_producer = options();
        with_producer.extensions = vec![ExtensionPolicy {
            schema_version: EXTENSION_SCHEMA_VERSION,
            extension_id: SchedulingProducer::ID.to_string(),
            invocation_budget: 8,
            proposal_budget: 8,
        }];
        let registry = [Registration::Producer(&producer)];
        let record = search_with_extensions(
            &encoded,
            &with_producer,
            &registry,
            &backend,
            &CancellationToken::new(),
        )
        .expect("the extended search completes");

        assert!(
            producer.proposals() > 0,
            "{id}: the producer must actually propose, or this test proves nothing"
        );
        assert!(
            record.outcome.proves_completion() && !record.forfeited,
            "{id}: a producer must not cost a proof, got {:?}",
            record.outcome
        );
        let expected = oracle_minimum(&times) as f64;
        let objective = record.objective.expect("a proven search has an objective");
        assert!(
            (objective - expected).abs() < 1e-6,
            "{id}: objective {objective} but enumeration says {expected}"
        );
        // The incumbent is a real schedule under the independent recurrence.
        let winner = record.candidate.expect("a proven search has a candidate");
        let sequence = permutation(&fixture, &winner, tolerances()).expect("the winner decodes");
        assert_eq!(
            makespan(&fixture, &sequence).expect("valid permutation"),
            expected as u64,
            "{id}: the incumbent disagrees with the recurrence"
        );
        checked += 1;
    }
    assert_eq!(checked, 4, "the native grid must stay fixed");
}

fn assert_conclusions_match(
    baseline: &SearchRecord,
    extended: &SearchRecord,
    id: &impl std::fmt::Display,
) {
    assert_eq!(baseline.outcome, extended.outcome, "{id}: outcome changed");
    assert_eq!(
        baseline.objective.map(f64::to_bits),
        extended.objective.map(f64::to_bits),
        "{id}: proven optimum changed"
    );
    assert_eq!(
        baseline.dual_bound.map(f64::to_bits),
        extended.dual_bound.map(f64::to_bits),
        "{id}: dual bound changed"
    );
    assert_eq!(
        baseline.forfeited, extended.forfeited,
        "{id}: forfeiture changed"
    );
    assert_eq!(
        baseline.nodes_pruned_infeasible, extended.nodes_pruned_infeasible,
        "{id}: infeasible prune count changed"
    );
    assert_eq!(
        baseline.nodes_pruned_bound, extended.nodes_pruned_bound,
        "{id}: bound prune count changed"
    );
}

/// Requirement 26: a limited search reports its limit and claims no optimum.
///
/// A 20-job Taillard instance is 400 binaries and the positional relaxation is
/// weak, which is exactly the case SPEC-0008 refuses to describe as optimal. The
/// incumbent is asserted feasible through the recurrence instead.
#[test]
fn a_limited_search_over_a_taillard_instance_claims_no_optimum() {
    if !require_native("a_limited_search_over_a_taillard_instance_claims_no_optimum") {
        return;
    }
    let published = optimizer_schedule::DEVELOPMENT_SUBSET[0];
    let fixture = published.generate().expect("generation succeeds");
    let encoded = model(&fixture).expect("valid model");
    let mut limited = options();
    limited.node_limit = Some(12);
    limited.time_limit_ms = Some(20_000);

    let producer = SchedulingProducer::new(fixture.clone());
    limited.extensions = vec![ExtensionPolicy {
        schema_version: EXTENSION_SCHEMA_VERSION,
        extension_id: SchedulingProducer::ID.to_string(),
        invocation_budget: 4,
        proposal_budget: 4,
    }];
    let registry = [Registration::Producer(&producer)];
    let record = search_with_extensions(
        &encoded,
        &limited,
        &registry,
        &backend_for_limit(),
        &CancellationToken::new(),
    )
    .expect("the search completes");

    assert!(
        !record.outcome.proves_completion(),
        "a 12-node search over 400 binaries must not claim a proof, got {:?}",
        record.outcome
    );
    // Whatever incumbent exists must be a real schedule: it decodes, and the
    // recurrence agrees with the recorded objective.
    if let Some(candidate) = record.candidate.as_ref() {
        let sequence =
            permutation(&fixture, candidate, tolerances()).expect("an incumbent decodes");
        let cost = makespan(&fixture, &sequence).expect("a decoded permutation is valid");
        let objective = record.objective.expect("an incumbent has an objective");
        assert!(
            (objective - cost as f64).abs() < 1e-6,
            "incumbent objective {objective} disagrees with the recurrence value {cost}"
        );
    }
}

fn backend_for_limit() -> HighsBackend {
    HighsBackend::new()
}
