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

use crate::evaluate::{InsertionArrays, partial_completion_times};
use crate::instance::FlowShopInstance;

/// NEH construction: order jobs by descending total processing time, then insert
/// each into the position minimizing the partial makespan.
///
/// Ties are broken deterministically and the rule is part of the contract. Jobs
/// with equal totals keep ascending job order, and equal insertion costs keep the
/// earliest position. Neither falls out of sort stability: the sort key includes
/// the job index precisely so the result cannot depend on the sorting algorithm.
///
/// Insertion positions are scored from head and tail arrays rather than by
/// rebuilding each trial sequence, which is the same arithmetic reaching the same
/// costs in `O(n^2 m)` instead of `O(n^3 m)`. The returned permutation is
/// unchanged, and a contract test asserts that against a naive reference rather
/// than trusting the argument.
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
    let mut arrays = InsertionArrays::new(instance.machines());
    for job in order {
        arrays.rebuild(instance, &sequence)?;
        let (_, position) = arrays.best_insertion(instance, job)?;
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
/// The pass stays sequential: an accepted move is visible to the next job, so the
/// jobs cannot be scored independently of one another. Only the scoring of one
/// job's positions is accelerated, which is why the accepted moves and therefore
/// the returned permutation are identical to the naive pass.
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
    let mut without: Vec<usize> = Vec::with_capacity(current.len());
    let mut arrays = InsertionArrays::new(instance.machines());
    for job in 0..instance.jobs() {
        let from = current
            .iter()
            .position(|&candidate| candidate == job)
            .expect("a validated permutation contains every job");
        without.clear();
        without.extend_from_slice(&current);
        without.remove(from);
        arrays.rebuild(instance, &without)?;
        let (cost, position) = arrays.best_insertion(instance, job)?;
        // Strict improvement only. Accepting an equal move would let the pass
        // shuffle a permutation without improving it, which is a difference a
        // caller would see as nondeterminism between versions.
        if cost < best_cost {
            current.clear();
            current.extend_from_slice(&without);
            current.insert(position, job);
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

/// For every job, the cost and position of its best reinsertion into `sequence`,
/// with that job removed first.
///
/// This is the whole insertion neighborhood of one permutation, evaluated from one
/// starting point. It is deliberately *not* what [`insertion`] does: that pass is
/// sequential, so an accepted move is visible to the next job and the jobs cannot be
/// scored independently. This function scores them independently, which is what makes
/// it expressible as a batch and therefore what a device can compute.
///
/// Choosing among the results is left to the caller, so the tie-break lives in one
/// place rather than being duplicated by every consumer.
///
/// # Errors
///
/// Returns a candidate failure when `sequence` is not a permutation of the
/// instance's jobs, and a numerical failure on overflow.
pub fn insertion_neighborhood(
    instance: &FlowShopInstance,
    sequence: &[usize],
) -> Result<Vec<(u64, usize)>, ValidationError> {
    crate::evaluate::validate_permutation(instance, sequence)?;
    let mut arrays = InsertionArrays::new(instance.machines());
    let mut without: Vec<usize> = Vec::with_capacity(sequence.len());
    let mut best = Vec::with_capacity(instance.jobs());
    for job in 0..instance.jobs() {
        let from = sequence
            .iter()
            .position(|&candidate| candidate == job)
            .expect("a validated permutation contains every job");
        without.clear();
        without.extend_from_slice(sequence);
        without.remove(from);
        arrays.rebuild(instance, &without)?;
        best.push(arrays.best_insertion(instance, job)?);
    }
    Ok(best)
}
