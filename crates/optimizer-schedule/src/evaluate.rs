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

/// Prefix completion times and suffix tails for one sequence, which together
/// score every insertion position of one job in a single pass over the machines.
///
/// This lives here rather than in `heuristic` for the reason requirement 8 exists:
/// the value it computes is a makespan, so it must be this module's arithmetic. A
/// heuristic reading it is still reading the recurrence's definition of cost, and
/// the identity it relies on is the recurrence's own. `head[i]` is the row
/// [`partial_completion_times`] would leave after `i` jobs, and `tail[i]` is the
/// same recurrence run backwards from the end, which is what makes the two
/// composable around an inserted job.
///
/// The arrays are rebuilt rather than reallocated, because a caller rebuilds once
/// per job and the allocation would otherwise dominate the saving.
pub(crate) struct InsertionArrays {
    machines: usize,
    length: usize,
    /// `(length + 1) * machines`. `head[i * machines + m]` is the completion time
    /// on machine `m` of the first `i` jobs of the sequence.
    head: Vec<u64>,
    /// `(length + 1) * machines`. `tail[i * machines + m]` is the time from the
    /// start of the job at position `i` on machine `m` to the end of the sequence.
    /// `tail[length]` is zero, which is what makes appending at the end fall out
    /// of the same formula rather than needing a special case.
    tail: Vec<u64>,
}

impl InsertionArrays {
    /// An empty set of arrays for an instance with `machines` machines.
    pub(crate) fn new(machines: usize) -> Self {
        Self {
            machines,
            length: 0,
            head: Vec::new(),
            tail: Vec::new(),
        }
    }

    /// Recompute both arrays for `sequence`, which may be a prefix.
    ///
    /// # Errors
    ///
    /// Returns a numerical failure on overflow, and a candidate failure when the
    /// sequence names a job outside the instance.
    pub(crate) fn rebuild(
        &mut self,
        instance: &FlowShopInstance,
        sequence: &[usize],
    ) -> Result<(), ValidationError> {
        let machines = self.machines;
        let length = sequence.len();
        self.length = length;
        let cells = (length + 1) * machines;
        self.head.clear();
        self.head.resize(cells, 0);
        self.tail.clear();
        self.tail.resize(cells, 0);

        for (position, &job) in sequence.iter().enumerate() {
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
            for machine in 0..machines {
                // The same recurrence as `partial_completion_times`, written over
                // a retained row rather than an overwritten one because the
                // insertion formula needs every prefix, not only the last.
                let start = previous_machine.max(self.head[position * machines + machine]);
                let finish = add(start, instance.processing_time(job, machine), instance)?;
                self.head[(position + 1) * machines + machine] = finish;
                previous_machine = finish;
            }
        }

        for position in (0..length).rev() {
            let job = sequence[position];
            let mut next_machine = 0u64;
            for machine in (0..machines).rev() {
                // Backwards: the successor on this machine is the job at the next
                // position, and the successor in this job is the next machine.
                let start = next_machine.max(self.tail[(position + 1) * machines + machine]);
                let finish = add(start, instance.processing_time(job, machine), instance)?;
                self.tail[position * machines + machine] = finish;
                next_machine = finish;
            }
        }
        Ok(())
    }

    /// The position minimizing the makespan of inserting `job`, and that makespan.
    ///
    /// Positions are scanned in ascending order and accepted only on a strict
    /// improvement, so the earliest position wins a tie. That tie-break is
    /// requirement 17's, and it is reproduced here rather than reinvented because
    /// changing it would change which permutation a heuristic returns.
    ///
    /// # Errors
    ///
    /// Returns a numerical failure on overflow.
    pub(crate) fn best_insertion(
        &self,
        instance: &FlowShopInstance,
        job: usize,
    ) -> Result<(u64, usize), ValidationError> {
        let machines = self.machines;
        let mut best: Option<(u64, usize)> = None;
        for position in 0..=self.length {
            let mut previous_machine = 0u64;
            let mut cost = 0u64;
            for machine in 0..machines {
                let start = previous_machine.max(self.head[position * machines + machine]);
                let finish = add(start, instance.processing_time(job, machine), instance)?;
                previous_machine = finish;
                // Completing `job` on this machine at `finish` delays everything
                // the tail still has to do on it, and the schedule cannot end
                // before the worst of those.
                let through = finish
                    .checked_add(self.tail[position * machines + machine])
                    .ok_or_else(|| overflow(job, machine, instance))?;
                cost = cost.max(through);
            }
            if best.is_none_or(|(best_cost, _)| cost < best_cost) {
                best = Some((cost, position));
            }
        }
        best.ok_or_else(|| {
            ValidationError::new(
                ErrorKind::Numerical,
                "an insertion always has at least one position",
            )
        })
    }
}

/// Checked addition of one processing time, failing rather than wrapping.
fn add(
    start: u64,
    processing_time: u32,
    instance: &FlowShopInstance,
) -> Result<u64, ValidationError> {
    start
        .checked_add(u64::from(processing_time))
        .ok_or_else(|| {
            ValidationError::new(
                ErrorKind::Numerical,
                format!(
                    "completion time overflowed in instance {}",
                    instance.instance_id()
                ),
            )
        })
}

/// Overflow while composing a head with a tail.
fn overflow(job: usize, machine: usize, instance: &FlowShopInstance) -> ValidationError {
    ValidationError::new(
        ErrorKind::Numerical,
        format!(
            "insertion cost overflowed for job {job} on machine {machine} in instance {}",
            instance.instance_id()
        ),
    )
}
