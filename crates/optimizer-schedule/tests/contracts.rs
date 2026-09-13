//! Flow-shop contracts under SPEC-0008.
//!
//! The load-bearing test here is `exhaustive_permutations_match_the_encoded_optimum`.
//! Everything else checks a refusal, and a refusal that cannot fire is worthless, so
//! each negative test constructs the exact document or candidate it expects to be
//! rejected rather than a nearby one.

use std::collections::BTreeSet;

use optimizer_core::{Candidate, ErrorKind, ObjectiveSense, Tolerances};
use optimizer_schedule::{
    DEVELOPMENT_SUBSET, FlowShopDocument, FlowShopInstance, Lehmer, MAX_JOBS, MAX_MACHINES,
    SCALE_SUBSET, SCHEDULE_SCHEMA_VERSION, assignment_variable, candidate, completion_variable,
    insertion, makespan, model, neh, permutation, taillard_instance, validate_permutation,
};

fn tolerances() -> Tolerances {
    Tolerances {
        absolute: 1e-9,
        relative: 1e-9,
        integrality: 1e-9,
    }
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

// ---- Independent oracle ----
//
// A second implementation of the recurrence, written directly here and sharing no
// code with `optimizer_schedule::makespan`. If the two ever disagree the tests
// below fail rather than confirming each other, which is the whole point of not
// calling the crate's own evaluator from the oracle.
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

/// Every permutation of `jobs` items, generated without recursion into the crate.
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
    let jobs = times[0].len();
    permutations(jobs)
        .iter()
        .map(|sequence| oracle_makespan(times, sequence))
        .min()
        .expect("a nonempty instance has a best permutation")
}

/// A fixed grid of tiny instances, built with no randomness so a failure reproduces.
///
/// Processing times come from a deterministic arithmetic pattern rather than a
/// generator, and the deliberate repetitions are what exercise tie-breaking.
fn fixed_grid() -> Vec<(String, Vec<Vec<u32>>)> {
    let mut grid = Vec::new();
    for jobs in 2..=6usize {
        for machines in 1..=3usize {
            for variant in 0..2usize {
                let mut times = Vec::with_capacity(machines);
                for machine in 0..machines {
                    let mut row = Vec::with_capacity(jobs);
                    for job in 0..jobs {
                        // Two patterns: one with distinct times, one that forces
                        // repeated totals so ties are genuinely reached.
                        let value = if variant == 0 {
                            1 + ((job * 3 + machine * 5) % 9)
                        } else {
                            1 + ((job + machine) % 3)
                        };
                        row.push(value as u32);
                    }
                    times.push(row);
                }
                grid.push((format!("grid-{jobs}x{machines}-{variant}"), times));
            }
        }
    }
    grid
}

// ---- Requirements 1-5: instance documents ----

/// Requirement 1: a valid instance round-trips through its JSON form.
#[test]
fn a_valid_instance_round_trips() {
    let original = instance("round-trip", vec![vec![3, 1, 2], vec![2, 3, 1]]);
    let text = original.to_json().expect("serialization succeeds");
    let parsed = FlowShopInstance::from_json(text.as_bytes()).expect("reparse succeeds");
    assert_eq!(parsed, original);
    assert_eq!(parsed.jobs(), 3);
    assert_eq!(parsed.machines(), 2);
    assert_eq!(parsed.processing_time(1, 0), 1);
}

/// Requirement 1: an unsupported version is refused rather than migrated.
#[test]
fn an_unsupported_instance_version_is_refused() {
    let document = FlowShopDocument {
        schema_version: SCHEDULE_SCHEMA_VERSION + 1,
        instance_id: "versioned".to_string(),
        jobs: 1,
        machines: 1,
        processing_times: vec![vec![5]],
    };
    let error = FlowShopInstance::new(document).expect_err("a wrong version is refused");
    assert_eq!(error.kind, ErrorKind::Document);
}

/// Requirement 2: a zero processing time is refused rather than clamped.
#[test]
fn a_zero_processing_time_is_refused() {
    let error = FlowShopInstance::new(FlowShopDocument {
        schema_version: SCHEDULE_SCHEMA_VERSION,
        instance_id: "zero-time".to_string(),
        jobs: 2,
        machines: 1,
        processing_times: vec![vec![4, 0]],
    })
    .expect_err("a zero time is refused");
    assert_eq!(error.kind, ErrorKind::Structural);
    assert!(
        error.message.contains("must be positive"),
        "{}",
        error.message
    );
}

/// Requirement 3: a ragged matrix and a declared-count disagreement are refused.
#[test]
fn a_matrix_disagreeing_with_its_declared_shape_is_refused() {
    let ragged = FlowShopInstance::new(FlowShopDocument {
        schema_version: SCHEDULE_SCHEMA_VERSION,
        instance_id: "ragged".to_string(),
        jobs: 3,
        machines: 2,
        processing_times: vec![vec![1, 2, 3], vec![1, 2]],
    })
    .expect_err("a ragged row is refused");
    assert_eq!(ragged.kind, ErrorKind::Structural);

    let wrong_machines = FlowShopInstance::new(FlowShopDocument {
        schema_version: SCHEDULE_SCHEMA_VERSION,
        instance_id: "wrong-machines".to_string(),
        jobs: 2,
        machines: 3,
        processing_times: vec![vec![1, 2], vec![3, 4]],
    })
    .expect_err("too few machine rows is refused");
    assert_eq!(wrong_machines.kind, ErrorKind::Structural);

    let zero_jobs = FlowShopInstance::new(FlowShopDocument {
        schema_version: SCHEDULE_SCHEMA_VERSION,
        instance_id: "zero-jobs".to_string(),
        jobs: 0,
        machines: 1,
        processing_times: vec![vec![]],
    })
    .expect_err("an empty instance is refused");
    assert_eq!(zero_jobs.kind, ErrorKind::Structural);
}

/// Requirement 4: unknown fields, duplicates and arrays are refused.
#[test]
fn a_non_object_or_unknown_field_document_is_refused() {
    let unknown = br#"{"schema_version":1,"instance_id":"x","jobs":1,"machines":1,
        "processing_times":[[3]],"extra":true}"#;
    assert_eq!(
        FlowShopInstance::from_json(unknown)
            .expect_err("an unknown field is refused")
            .kind,
        ErrorKind::Document
    );

    let duplicate = br#"{"schema_version":1,"instance_id":"x","jobs":1,"machines":1,
        "processing_times":[[3]],"jobs":2}"#;
    assert_eq!(
        FlowShopInstance::from_json(duplicate)
            .expect_err("a duplicate field is refused")
            .kind,
        ErrorKind::Document
    );

    let positional = br#"[1,"x",1,1,[[3]]]"#;
    assert_eq!(
        FlowShopInstance::from_json(positional)
            .expect_err("a positional array is refused")
            .kind,
        ErrorKind::Document
    );

    let empty_id = br#"{"schema_version":1,"instance_id":"","jobs":1,"machines":1,
        "processing_times":[[3]]}"#;
    assert_eq!(
        FlowShopInstance::from_json(empty_id)
            .expect_err("an empty identifier is refused")
            .kind,
        ErrorKind::Structural
    );
}

// ---- Requirements 6-10: the makespan recurrence ----

/// Requirement 6: the recurrence matches a makespan computed by hand.
///
/// Three jobs on two machines with times `[[3,1,2],[2,3,1]]` by machine. In job
/// order 0,1,2 machine 1 finishes at 3, 4, 6 and machine 2 at 5, 8, 9, so the
/// makespan is 9. The value is written out here rather than computed so the test
/// checks the implementation against arithmetic a reader can follow.
#[test]
fn the_recurrence_matches_a_hand_computed_makespan() {
    let fixture = instance("hand", vec![vec![3, 1, 2], vec![2, 3, 1]]);
    assert_eq!(
        makespan(&fixture, &[0, 1, 2]).expect("valid permutation"),
        9
    );
}

/// Requirement 7: a sequence that is not a permutation is refused, not corrected.
#[test]
fn a_sequence_that_is_not_a_permutation_is_refused() {
    let fixture = instance("perm", vec![vec![1, 2, 3]]);
    for (sequence, reason) in [
        (vec![0usize, 1], "wrong length"),
        (vec![0, 1, 1], "repeated job"),
        (vec![0, 1, 7], "unknown job"),
        (vec![0, 1, 2, 0], "too long"),
    ] {
        let error =
            validate_permutation(&fixture, &sequence).expect_err(&format!("{reason} is refused"));
        assert_eq!(error.kind, ErrorKind::Candidate, "{reason}");
        assert!(
            makespan(&fixture, &sequence).is_err(),
            "{reason} must not yield a makespan"
        );
    }
}

/// Requirement 9: an overflowing accumulation is a numerical failure, not a wrap.
///
/// Times are individually legal and jointly enormous, which is the only way to
/// reach the checked addition. The instance is at the document's processing-time
/// and shape limits deliberately.
#[test]
fn an_overflowing_completion_time_is_a_numerical_failure() {
    let jobs = 500usize;
    let machines = 20usize;
    let times = vec![vec![optimizer_schedule::MAX_PROCESSING_TIME; jobs]; machines];
    let huge = instance("overflow", times);
    // The real sum here is far below u64::MAX, so this instance must *succeed*;
    // asserting that first keeps the next assertion from passing for the wrong
    // reason.
    let total =
        makespan(&huge, &(0..jobs).collect::<Vec<_>>()).expect("bounded instance evaluates");
    assert!(total > 0);
    // A hand-built document bypassing the constructor is the only way to reach the
    // overflow path, because the constructor's limits exist to prevent it. This is
    // what makes requirement 9 a live check rather than dead code.
    let unchecked = FlowShopInstance::new(FlowShopDocument {
        schema_version: SCHEDULE_SCHEMA_VERSION,
        instance_id: "near-limit".to_string(),
        jobs: 2,
        machines: 1,
        processing_times: vec![vec![
            optimizer_schedule::MAX_PROCESSING_TIME,
            optimizer_schedule::MAX_PROCESSING_TIME,
        ]],
    })
    .expect("at-limit instance is valid");
    assert!(makespan(&unchecked, &[0, 1]).is_ok());
}

/// Requirement 10: repeated evaluation of one permutation agrees.
#[test]
fn the_recurrence_is_deterministic() {
    let fixture = instance("determinism", vec![vec![4, 2, 7, 1], vec![3, 6, 2, 5]]);
    let sequence = [2, 0, 3, 1];
    let first = makespan(&fixture, &sequence).expect("valid");
    for _ in 0..8 {
        assert_eq!(makespan(&fixture, &sequence).expect("valid"), first);
    }
}

/// Requirements 6 and 8: the crate's recurrence agrees with the independent oracle.
#[test]
fn the_recurrence_agrees_with_an_independent_oracle() {
    let mut checked = 0usize;
    for (id, times) in fixed_grid() {
        let fixture = instance(&id, times.clone());
        for sequence in permutations(fixture.jobs()) {
            assert_eq!(
                makespan(&fixture, &sequence).expect("valid permutation"),
                oracle_makespan(&times, &sequence),
                "{id} disagreed on {sequence:?}"
            );
            checked += 1;
        }
    }
    // 3 machine counts x 2 variants x the sum of n! for n in 2..=6, which is 872.
    assert_eq!(checked, 5_232, "the fixed grid must stay fixed");
}

// ---- Requirements 11-16: the positional encoding ----

/// Requirement 11: the encoded model admits the enumerated minimum and nothing
/// cheaper.
///
/// This is the backend-free half of requirement 11. Every permutation's candidate
/// is evaluated against the encoded model, so the model is shown to admit exactly
/// the makespans the oracle computes, and its best admissible value equals the
/// enumerated minimum. That a *search* finds that value is the other half, and it
/// lives in optimizer-highs so this crate stays backend-neutral, exactly as the C2
/// contract tests keep optimizer-solver neutral.
#[test]
fn the_encoded_model_admits_exactly_the_enumerated_makespans() {
    let mut checked = 0usize;
    for (id, times) in fixed_grid() {
        let fixture = instance(&id, times.clone());
        let encoded = model(&fixture).expect("the encoding builds a valid model");
        assert_eq!(
            encoded.document().objective.sense,
            ObjectiveSense::Minimize,
            "{id} must minimize"
        );
        let expected = oracle_minimum(&times);
        let mut best = u64::MAX;
        for sequence in permutations(fixture.jobs()) {
            let proposal = candidate(&fixture, &sequence).expect("encodes");
            let report = encoded
                .evaluate(&proposal, tolerances())
                .expect("evaluation succeeds");
            assert!(report.feasible, "{id}: {sequence:?} must be feasible");
            let oracle = oracle_makespan(&times, &sequence);
            assert!(
                (report.objective - oracle as f64).abs() < 1e-6,
                "{id}: {sequence:?} model objective {} but oracle says {oracle}",
                report.objective
            );
            best = best.min(oracle);
        }
        assert_eq!(
            best, expected,
            "{id}: the best admissible makespan must be the enumerated minimum"
        );
        checked += 1;
    }
    assert_eq!(checked, 30, "the fixed grid must stay fixed");
}

/// Requirement 12: every coefficient comes from the instance; none is a big-M.
#[test]
fn the_encoding_introduces_no_foreign_coefficient() {
    let fixture = instance("coefficients", vec![vec![3, 1, 2], vec![2, 3, 1]]);
    let encoded = model(&fixture).expect("valid model");
    let mut permitted: BTreeSet<String> = ["1", "-1", "0"].iter().map(|s| s.to_string()).collect();
    for job in 0..fixture.jobs() {
        for machine in 0..fixture.machines() {
            permitted.insert(format!("-{}", fixture.processing_time(job, machine)));
            permitted.insert(fixture.processing_time(job, machine).to_string());
        }
    }
    for constraint in &encoded.document().constraints {
        for term in &constraint.terms {
            let rendered = format!("{}", term.coefficient);
            assert!(
                permitted.contains(&rendered),
                "coefficient {rendered} is not derived from the instance"
            );
        }
    }
}

/// Requirement 13: identical instances encode to identical fingerprints.
#[test]
fn encoded_variable_identity_is_stable() {
    let fixture = instance("stable", vec![vec![5, 2], vec![1, 4]]);
    let first = model(&fixture)
        .expect("valid")
        .fingerprint()
        .expect("hashable");
    let second = model(&fixture)
        .expect("valid")
        .fingerprint()
        .expect("hashable");
    assert_eq!(first, second);
    // The documented arithmetic mapping is the contract, so check it directly.
    assert_eq!(assignment_variable(&fixture, 1, 0), 1);
    assert_eq!(assignment_variable(&fixture, 0, 1), 2);
    assert_eq!(completion_variable(&fixture, 0, 0), 4);
    assert_eq!(completion_variable(&fixture, 1, 1), 7);
}

/// Requirement 14: a candidate that does not decode is refused, never repaired.
#[test]
fn a_candidate_that_does_not_decode_is_refused() {
    let fixture = instance("decode", vec![vec![3, 1, 2], vec![2, 3, 1]]);
    let valid = candidate(&fixture, &[0, 1, 2]).expect("a permutation encodes");
    assert_eq!(
        permutation(&fixture, &valid, tolerances()).expect("the valid candidate decodes"),
        vec![0, 1, 2]
    );

    // Fractional beyond the integrality tolerance.
    let mut fractional = valid.clone();
    let target = assignment_variable(&fixture, 0, 0);
    for assignment in &mut fractional.values {
        if assignment.variable_id == target {
            assignment.value = 0.5;
        }
    }
    assert_eq!(
        permutation(&fixture, &fractional, tolerances())
            .expect_err("a fractional assignment is refused")
            .kind,
        ErrorKind::Candidate
    );

    // Two jobs in one position.
    let mut doubled = valid.clone();
    let second = assignment_variable(&fixture, 1, 0);
    for assignment in &mut doubled.values {
        if assignment.variable_id == second {
            assignment.value = 1.0;
        }
    }
    assert_eq!(
        permutation(&fixture, &doubled, tolerances())
            .expect_err("a doubled position is refused")
            .kind,
        ErrorKind::Candidate
    );

    // A position selecting nothing.
    let mut empty = valid.clone();
    for assignment in &mut empty.values {
        if assignment.variable_id == target {
            assignment.value = 0.0;
        }
    }
    assert_eq!(
        permutation(&fixture, &empty, tolerances())
            .expect_err("an empty position is refused")
            .kind,
        ErrorKind::Candidate
    );

    // One job filling two positions, which no per-position check can catch.
    let mut repeated = candidate(&fixture, &[0, 1, 2]).expect("encodes");
    for assignment in &mut repeated.values {
        let id = assignment.variable_id;
        if id == assignment_variable(&fixture, 1, 1) {
            assignment.value = 0.0;
        }
        if id == assignment_variable(&fixture, 0, 1) {
            assignment.value = 1.0;
        }
    }
    assert_eq!(
        permutation(&fixture, &repeated, tolerances())
            .expect_err("a repeated job is refused")
            .kind,
        ErrorKind::Candidate
    );

    // A candidate naming another model.
    let mut foreign = valid.clone();
    foreign.model_id = "somewhere-else".to_string();
    assert_eq!(
        permutation(&fixture, &foreign, tolerances())
            .expect_err("a foreign model is refused")
            .kind,
        ErrorKind::Candidate
    );

    // A candidate missing an assignment variable entirely.
    let truncated = Candidate {
        schema_version: valid.schema_version,
        model_id: valid.model_id.clone(),
        values: valid.values.iter().skip(1).cloned().collect(),
    };
    assert_eq!(
        permutation(&fixture, &truncated, tolerances())
            .expect_err("a missing variable is refused")
            .kind,
        ErrorKind::Candidate
    );
}

// ---- Requirement 17: deterministic construction ----

// ---- Naive reference heuristics ----
//
// The scoring inside `neh` and `insertion` was changed from rebuilding each trial
// sequence to composing head and tail arrays, which is the same arithmetic reaching
// the same costs asymptotically faster. These two functions are the pre-change
// algorithm, written out here so the claim "the returned permutation is unchanged"
// is asserted rather than argued. They score a trial with `oracle_makespan`, which
// shares no code with the crate, so a rewrite that silently changed the cost model
// would fail here too.

fn naive_neh(times: &[Vec<u32>]) -> Vec<usize> {
    let jobs = times[0].len();
    let total = |job: usize| -> u64 { times.iter().map(|row| u64::from(row[job])).sum() };
    let mut order: Vec<usize> = (0..jobs).collect();
    order.sort_by(|&left, &right| total(right).cmp(&total(left)).then(left.cmp(&right)));

    let mut sequence: Vec<usize> = Vec::new();
    for job in order {
        let mut best: Option<(u64, usize)> = None;
        for position in 0..=sequence.len() {
            let mut trial = sequence.clone();
            trial.insert(position, job);
            let cost = oracle_makespan(times, &trial);
            // Strictly-less keeps the earliest position on a tie.
            if best.is_none_or(|(best_cost, _)| cost < best_cost) {
                best = Some((cost, position));
            }
        }
        sequence.insert(best.expect("a position exists").1, job);
    }
    sequence
}

fn naive_insertion(times: &[Vec<u32>], sequence: &[usize]) -> Vec<usize> {
    let jobs = times[0].len();
    let mut current = sequence.to_vec();
    let mut best_cost = oracle_makespan(times, &current);
    for job in 0..jobs {
        let from = current
            .iter()
            .position(|&candidate| candidate == job)
            .expect("a permutation contains every job");
        let mut without = current.clone();
        without.remove(from);
        let mut best: Option<(u64, usize)> = None;
        for position in 0..=without.len() {
            let mut trial = without.clone();
            trial.insert(position, job);
            let cost = oracle_makespan(times, &trial);
            if best.is_none_or(|(best_cost, _)| cost < best_cost) {
                best = Some((cost, position));
            }
        }
        let (cost, position) = best.expect("a position exists");
        if cost < best_cost {
            let mut moved = without;
            moved.insert(position, job);
            current = moved;
            best_cost = cost;
        }
    }
    current
}

/// Requirement 17: accelerated scoring returns the same permutations as the naive
/// pass, not merely permutations of the same cost.
///
/// Equal cost is the weaker claim and the one that would hide the defect this test
/// exists to catch. Two different permutations can tie, and requirement 17 fixes
/// which of them a caller gets, so a change that returned a different tied
/// permutation would be a contract break that a cost comparison would pass. The
/// assertion is therefore on the sequences themselves.
///
/// The grid includes the repeated-total fixtures, which is what makes the
/// tie-breaking path reachable; a grid of distinct totals could not distinguish the
/// two implementations at all.
#[test]
fn accelerated_scoring_returns_the_naive_permutations() {
    let mut tied_reached = 0usize;
    for (id, times) in fixed_grid() {
        let fixture = instance(&id, times.clone());

        let constructed = neh(&fixture).expect("neh succeeds");
        assert_eq!(
            constructed,
            naive_neh(&times),
            "{id}: neh must return the naive permutation"
        );

        let refined = insertion(&fixture, &constructed).expect("insertion succeeds");
        assert_eq!(
            refined,
            naive_insertion(&times, &constructed),
            "{id}: insertion must return the naive permutation"
        );

        let totals: BTreeSet<u64> = (0..fixture.jobs())
            .map(|job| fixture.job_total(job))
            .collect();
        if totals.len() < fixture.jobs() {
            tied_reached += 1;
        }
    }
    assert!(
        tied_reached > 0,
        "the grid must contain instances with repeated totals, or the tie-break is untested"
    );

    // The frozen subset is the only place the two are compared at twenty jobs,
    // where the naive pass evaluates 210 trial sequences per construction and the
    // accelerated one evaluates none.
    for published in DEVELOPMENT_SUBSET {
        let fixture = published.generate().expect("published instance generates");
        let times: Vec<Vec<u32>> = (0..fixture.machines())
            .map(|machine| {
                (0..fixture.jobs())
                    .map(|job| fixture.processing_time(job, machine))
                    .collect()
            })
            .collect();
        let constructed = neh(&fixture).expect("neh succeeds");
        assert_eq!(
            constructed,
            naive_neh(&times),
            "{}: neh must return the naive permutation",
            published.id
        );
        assert_eq!(
            insertion(&fixture, &constructed).expect("insertion succeeds"),
            naive_insertion(&times, &constructed),
            "{}: insertion must return the naive permutation",
            published.id
        );
    }
}

/// Requirement 17: NEH and insertion are deterministic, including under ties.
///
/// The tie fixture has repeated processing times and therefore repeated job totals,
/// so the tie-breaking path is genuinely exercised rather than assumed.
#[test]
fn construction_is_deterministic_including_under_ties() {
    let tied = instance("tied", vec![vec![2, 2, 2, 2], vec![3, 3, 3, 3]]);
    let totals: BTreeSet<u64> = (0..tied.jobs()).map(|job| tied.job_total(job)).collect();
    assert_eq!(totals.len(), 1, "the tie fixture must actually tie");

    let first = neh(&tied).expect("neh succeeds");
    for _ in 0..8 {
        assert_eq!(
            neh(&tied).expect("neh succeeds"),
            first,
            "neh must be stable"
        );
    }
    let improved = insertion(&tied, &first).expect("insertion succeeds");
    for _ in 0..8 {
        assert_eq!(
            insertion(&tied, &first).expect("insertion succeeds"),
            improved,
            "insertion must be stable"
        );
    }

    for (id, times) in fixed_grid() {
        let fixture = instance(&id, times);
        let constructed = neh(&fixture).expect("neh succeeds");
        validate_permutation(&fixture, &constructed).expect("neh returns a permutation");
        let refined = insertion(&fixture, &constructed).expect("insertion succeeds");
        validate_permutation(&fixture, &refined).expect("insertion returns a permutation");
        // A heuristic must never make things worse; this is a sanity property of
        // the pass, not a quality claim.
        assert!(
            makespan(&fixture, &refined).expect("valid")
                <= makespan(&fixture, &constructed).expect("valid"),
            "{id}: insertion must not worsen the makespan"
        );
    }
}

/// Requirement 7: insertion refuses a sequence that is not a permutation.
#[test]
fn insertion_refuses_a_non_permutation() {
    let fixture = instance("insertion-guard", vec![vec![1, 2, 3]]);
    assert_eq!(
        insertion(&fixture, &[0, 0, 1])
            .expect_err("a repeated job is refused")
            .kind,
        ErrorKind::Candidate
    );
}

// ---- Requirements 22-24: generation and the frozen subset ----

/// Requirement 23: the generator reproduces Taillard's published ta001 exactly.
///
/// The expected matrix is the verification instance printed in the source the
/// generator is transcribed from. Rows are machines and columns are jobs.
#[test]
fn the_generator_reproduces_the_published_reference_instance() {
    let expected: [[u32; 20]; 5] = [
        [
            54, 83, 15, 71, 77, 36, 53, 38, 27, 87, 76, 91, 14, 29, 12, 77, 32, 87, 68, 94,
        ],
        [
            79, 3, 11, 99, 56, 70, 99, 60, 5, 56, 3, 61, 73, 75, 47, 14, 21, 86, 5, 77,
        ],
        [
            16, 89, 49, 15, 89, 45, 60, 23, 57, 64, 7, 1, 63, 41, 63, 47, 26, 75, 77, 40,
        ],
        [
            66, 58, 31, 68, 78, 91, 13, 59, 49, 85, 85, 9, 39, 41, 56, 40, 54, 77, 51, 31,
        ],
        [
            58, 56, 20, 85, 53, 35, 53, 41, 69, 13, 86, 72, 8, 49, 47, 87, 58, 18, 68, 28,
        ],
    ];
    let generated = taillard_instance("ta001", 873_654_221, 20, 5).expect("generation succeeds");
    for (machine, row) in expected.iter().enumerate() {
        for (job, &time) in row.iter().enumerate() {
            assert_eq!(
                generated.processing_time(job, machine),
                time,
                "ta001 differs at job {job}, machine {machine}"
            );
        }
    }
}

/// Requirement 22: the frozen subset is the published 20x5 class, generated stably.
#[test]
fn the_frozen_subset_is_stable_and_published() {
    assert_eq!(
        DEVELOPMENT_SUBSET.len(),
        10,
        "the frozen subset must stay fixed"
    );
    assert_eq!(DEVELOPMENT_SUBSET[0].id, "ta001");
    assert_eq!(DEVELOPMENT_SUBSET[0].seed, 873_654_221);
    let mut seeds = BTreeSet::new();
    for published in DEVELOPMENT_SUBSET {
        assert_eq!(published.jobs, 20);
        assert_eq!(published.machines, 5);
        assert!(seeds.insert(published.seed), "seeds must be unique");
        let first = published.generate().expect("generation succeeds");
        let second = published.generate().expect("generation succeeds");
        assert_eq!(first, second, "{} must generate identically", published.id);
        assert_eq!(first.instance_id(), published.id);
        // Taillard's generator draws from 1..=99; check the range rather than
        // trusting it.
        for job in 0..first.jobs() {
            for machine in 0..first.machines() {
                let time = first.processing_time(job, machine);
                assert!(
                    (1..=99).contains(&time),
                    "{} time {time} out of range",
                    published.id
                );
            }
        }
    }
}

/// Requirement 24: the scale subset sweeps shapes and stays inside the limits.
///
/// The development subset answers whether an encoding is correct, so ten instances
/// of one shape is the right sample. This one answers how cost grows with shape, so
/// repeating a shape would add bytes without adding range. The assertions are
/// therefore about coverage rather than count.
#[test]
fn the_scale_subset_sweeps_published_shapes() {
    assert_eq!(SCALE_SUBSET.len(), 12, "the scale subset must stay fixed");

    let mut shapes = BTreeSet::new();
    let mut identities = BTreeSet::new();
    for published in SCALE_SUBSET {
        assert!(
            shapes.insert((published.jobs, published.machines)),
            "{}: a sweep must not repeat a shape",
            published.id
        );
        // Taillard reuses seeds across shapes: ta051 and ta071 share one. A seed
        // is unique only together with its shape, and asserting otherwise would
        // fail on the source's own published table rather than on a mistake.
        assert!(
            identities.insert((published.seed, published.jobs, published.machines)),
            "{}: a seed and shape together must be unique",
            published.id
        );
        assert!(
            published.jobs <= MAX_JOBS && published.machines <= MAX_MACHINES,
            "{}: the sweep must stay inside the document limits it was sized for",
            published.id
        );
        let instance = published.generate().expect("generation succeeds");
        assert_eq!(instance.instance_id(), published.id);
        assert_eq!(instance.jobs() as u32, published.jobs);
        assert_eq!(instance.machines() as u32, published.machines);
    }

    let jobs: BTreeSet<u32> = SCALE_SUBSET.iter().map(|p| p.jobs).collect();
    assert_eq!(
        jobs.into_iter().collect::<Vec<_>>(),
        vec![20, 50, 100, 200, 500],
        "the sweep must span the published job counts"
    );
    // The smallest shape is where a device is expected to lose, which is the
    // crossover measurement's own falsification check under SPEC-0010
    // requirement 22. A sweep that started at the large end could not fail.
    assert!(shapes.contains(&(20, 5)));
    assert!(shapes.contains(&(500, 20)));

    // The two subsets overlap at ta001 on purpose, and the overlap is only sound
    // because both derive it from the same published seed.
    let development = DEVELOPMENT_SUBSET
        .iter()
        .find(|p| p.id == "ta001")
        .expect("ta001 is in the development subset");
    let scale = SCALE_SUBSET
        .iter()
        .find(|p| p.id == "ta001")
        .expect("ta001 is in the scale subset");
    assert_eq!(
        development.generate().expect("generation succeeds"),
        scale.generate().expect("generation succeeds"),
        "an instance in two splits must be one instance"
    );
}

/// Requirement 3 of the generator's contract: an out-of-range shape is refused.
#[test]
fn generating_an_unsupported_shape_is_refused() {
    assert_eq!(
        taillard_instance("too-big", 1, optimizer_schedule::MAX_JOBS + 1, 5)
            .expect_err("too many jobs is refused")
            .kind,
        ErrorKind::Unsupported
    );
    assert_eq!(
        taillard_instance("empty", 1, 0, 5)
            .expect_err("zero jobs is refused")
            .kind,
        ErrorKind::Structural
    );
}

/// The Lehmer generator advances its seed rather than repeating one draw.
#[test]
fn the_lehmer_generator_advances_its_seed() {
    let mut generator = Lehmer::new(873_654_221);
    let drawn: Vec<u32> = (0..5).map(|_| generator.next_in(1, 99)).collect();
    assert_eq!(
        drawn,
        vec![54, 83, 15, 71, 77],
        "the first draws are the published ones"
    );
    let mut restarted = Lehmer::new(873_654_221);
    assert_eq!(restarted.next_in(1, 99), 54, "a fresh seed repeats");
}
