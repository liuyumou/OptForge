//! The makespan recurrence under SPEC-0008 requirements 6 to 10.
//!
//! This module is the sole authority on what a schedule costs. It deliberately
//! imports nothing from `encode` or `heuristic`: two
//! computations that share an implementation agree by construction, and their
//! agreement establishes nothing. Requirement 8 is therefore an architectural
//! property of this file rather than an assertion a test can make.
//!
//! Arithmetic is checked. A makespan is bounded by the sum of all processing
//! times, so overflow requires an instance near the document limits, but
//! requirement 9 forbids wrapping or saturating rather than relying on that bound.

use optimizer_core::{ErrorKind, ValidationError};

use crate::instance::FlowShopInstance;

/// Validate that `sequence` is a permutation of exactly the instance's jobs.
///
/// # Errors
///
/// Returns a candidate failure for a wrong length, a job index outside the
/// instance, or a repeated job. Requirement 7 forbids correcting any of these.
pub fn validate_permutation(
    instance: &FlowShopInstance,
    sequence: &[usize],
) -> Result<(), ValidationError> {
    let jobs = instance.jobs();
    if sequence.len() != jobs {
        return Err(ValidationError::new(
            ErrorKind::Candidate,
            format!(
                "sequence has {} entries, expected {jobs} for instance {}",
                sequence.len(),
                instance.instance_id()
            ),
        ));
    }
    let mut seen = vec![false; jobs];
    for &job in sequence {
        if job >= jobs {
            return Err(ValidationError::new(
                ErrorKind::Candidate,
                format!("sequence names job {job}, which is outside 0..{jobs}"),
            ));
        }
        if seen[job] {
            return Err(ValidationError::new(
                ErrorKind::Candidate,
                format!("sequence repeats job {job}"),
            ));
        }
        seen[job] = true;
    }
    // Every entry is in range, distinct, and there are exactly `jobs` of them, so
    // the pigeonhole principle makes a missing job impossible here. The explicit
    // check stays anyway: it costs nothing and it fails loudly rather than
    // silently if either earlier condition is ever weakened.
    if let Some(missing) = seen.iter().position(|&present| !present) {
        return Err(ValidationError::new(
            ErrorKind::Candidate,
            format!("sequence omits job {missing}"),
        ));
    }
    Ok(())
}

/// Completion time of every position on the last machine, in position order.
///
/// Exposed because the insertion heuristics need partial completion times and
/// recomputing a full schedule per candidate position would be wasteful. It is
/// the same recurrence [`makespan`] uses, so a heuristic reading this is still
/// reading this module's definition rather than its own.
///
/// # Errors
///
/// Returns whatever [`validate_permutation`] returns, or a numerical failure on
/// overflow.
pub fn completion_times(
    instance: &FlowShopInstance,
    sequence: &[usize],
) -> Result<Vec<u64>, ValidationError> {
    validate_permutation(instance, sequence)?;
    partial_completion_times(instance, sequence)
}

/// The recurrence over a prefix, without requiring a complete permutation.
///
/// A prefix of a permutation is what NEH's construction evaluates, so this skips
/// the completeness check while keeping the arithmetic identical. Callers outside
/// this crate reach it through [`completion_times`], which validates first.
pub(crate) fn partial_completion_times(
    instance: &FlowShopInstance,
    sequence: &[usize],
) -> Result<Vec<u64>, ValidationError> {
    let machines = instance.machines();
    // One row of completion times, overwritten in place per position. The
    // recurrence needs only the previous position's row, so this is O(machines)
    // memory regardless of the job count.
    let mut row = vec![0u64; machines];
    let mut last = Vec::with_capacity(sequence.len());
    for &job in sequence {
        if job >= instance.jobs() {
            return Err(ValidationError::new(
                ErrorKind::Candidate,
                format!(
                    "sequence names job {job}, which is outside 0..{}",
                    instance.jobs()
                ),
            ));
        }
        let mut previous_machine = 0u64;
        for (machine, entry) in row.iter_mut().enumerate() {
            // C[k][i] = max(C[k-1][i], C[k][i-1]) + p[job][i]. `entry` holds
            // C[k-1][i] until it is overwritten, and `previous_machine` is
            // C[k][i-1], which is zero for the first machine.
            let start = previous_machine.max(*entry);
            let finish = start
                .checked_add(u64::from(instance.processing_time(job, machine)))
                .ok_or_else(|| {
                    ValidationError::new(
                        ErrorKind::Numerical,
                        format!(
                            "completion time overflowed for job {job} on machine {machine} in instance {}",
                            instance.instance_id()
                        ),
                    )
                })?;
            *entry = finish;
            previous_machine = finish;
        }
        last.push(previous_machine);
    }
    Ok(last)
}

/// Makespan of `sequence` on `instance`.
///
/// This is the definition of makespan for the whole slice. Requirement 6 makes it
/// the only one.
///
/// # Errors
///
/// Returns a candidate failure when `sequence` is not a permutation of the
/// instance's jobs, and a numerical failure when completion times overflow.
pub fn makespan(instance: &FlowShopInstance, sequence: &[usize]) -> Result<u64, ValidationError> {
    let completions = completion_times(instance, sequence)?;
    // A validated permutation is nonempty because an instance has at least one
    // job, so the last completion time exists.
    completions.last().copied().ok_or_else(|| {
        ValidationError::new(
            ErrorKind::Numerical,
            "an instance with no jobs has no makespan",
        )
    })
}
