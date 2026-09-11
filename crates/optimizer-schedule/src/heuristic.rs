//! Deterministic NEH and insertion construction under SPEC-0008 requirement 17.
//!
//! These are heuristics. Nothing here claims a bound, a proof or a quality
//! guarantee, and requirement 17 fixes their tie-breaking so runs are reproducible
//! rather than because either rule is known to be good. Whether one tie-break beats
//! another is a C7 question and is recorded as a hypothesis in SPEC-0008's open
//! questions.
//!
//! Both functions produce permutations and know nothing about models or candidates.
//! Cost comes from `evaluate`, so a heuristic cannot disagree with the
//! recurrence about what a schedule costs; it can only choose badly.

use optimizer_core::ValidationError;

use crate::evaluate::partial_completion_times;
use crate::instance::FlowShopInstance;

/// NEH construction: order jobs by descending total processing time, then insert
/// each into the position minimizing the partial makespan.
///
/// Ties are broken deterministically and the rule is part of the contract. Jobs
/// with equal totals keep ascending job order, and equal insertion costs keep the
/// earliest position. Neither falls out of sort stability: the sort key includes
/// the job index precisely so the result cannot depend on the sorting algorithm.
///
/// # Errors
///
/// Returns whatever the recurrence returns, which for a valid instance is a
/// numerical failure only on overflow.
pub fn neh(instance: &FlowShopInstance) -> Result<Vec<usize>, ValidationError> {
    let jobs = instance.jobs();
    let mut order: Vec<usize> = (0..jobs).collect();
    // Descending total, then ascending job index. Including the index makes the
    // comparison a total order, so the output does not depend on whether the sort
    // is stable.
    order.sort_by(|&left, &right| {
        instance
            .job_total(right)
            .cmp(&instance.job_total(left))
            .then(left.cmp(&right))
    });

    let mut sequence: Vec<usize> = Vec::with_capacity(jobs);
    for job in order {
        let mut best: Option<(u64, usize)> = None;
        for position in 0..=sequence.len() {
            let mut trial = sequence.clone();
            trial.insert(position, job);
            let cost = partial_makespan(instance, &trial)?;
            // Strictly-less keeps the earliest position on a tie.
            if best.is_none_or(|(best_cost, _)| cost < best_cost) {
                best = Some((cost, position));
            }
        }
        let (_, position) = best.expect("at least one insertion position exists");
        sequence.insert(position, job);
    }
    Ok(sequence)
}

/// One pass of insertion improvement: remove each job in turn and reinsert it
/// where the makespan is lowest.
///
/// Jobs are scanned in ascending index order and positions in ascending order, and
/// a move is taken only when it strictly improves, so the pass is deterministic and
/// cannot cycle. One pass is deliberate: iterating to a local optimum is local
/// search, which SPEC-0008 excludes.
///
/// # Errors
///
/// Returns a candidate failure when `sequence` is not a permutation of the
/// instance's jobs, and a numerical failure on overflow.
pub fn insertion(
    instance: &FlowShopInstance,
    sequence: &[usize],
) -> Result<Vec<usize>, ValidationError> {
    crate::evaluate::validate_permutation(instance, sequence)?;
    let mut current = sequence.to_vec();
    let mut best_cost = partial_makespan(instance, &current)?;
    for job in 0..instance.jobs() {
        let from = current
            .iter()
            .position(|&candidate| candidate == job)
            .expect("a validated permutation contains every job");
        let mut without = current.clone();
        without.remove(from);
        let mut best: Option<(u64, usize)> = None;
        for position in 0..=without.len() {
            let mut trial = without.clone();
            trial.insert(position, job);
            let cost = partial_makespan(instance, &trial)?;
            if best.is_none_or(|(best_cost, _)| cost < best_cost) {
                best = Some((cost, position));
            }
        }
        let (cost, position) = best.expect("at least one insertion position exists");
        // Strict improvement only. Accepting an equal move would let the pass
        // shuffle a permutation without improving it, which is a difference a
        // caller would see as nondeterminism between versions.
        if cost < best_cost {
            let mut moved = without;
            moved.insert(position, job);
            current = moved;
            best_cost = cost;
        }
    }
    Ok(current)
}

/// Makespan of a prefix, used to score an insertion.
fn partial_makespan(
    instance: &FlowShopInstance,
    sequence: &[usize],
) -> Result<u64, ValidationError> {
    Ok(partial_completion_times(instance, sequence)?
        .last()
        .copied()
        .unwrap_or(0))
}
