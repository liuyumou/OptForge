//! The positional encoding under SPEC-0008 requirements 11 to 16.
//!
//! An instance becomes an ordinary [`optimizer_core::Model`], so `Model::evaluate`,
//! the C2 executive, the C3 extension host and SPEC-0005's run records all apply
//! unchanged. That reuse is ADR-0007's central structural decision: a separate
//! scheduling solver would have needed every one of them rebuilt, and each rebuilt
//! piece would have been another place for a proof claim to be made incorrectly.
//!
//! The formulation is exactly linear and introduces no big-M constant, so
//! requirement 11's equality between the model's optimum and the instance's
//! minimum makespan holds by construction rather than by a numerical margin.
//! Every coefficient is 1, -1, or a processing time taken from the instance.
//!
//! For job `j`, position `k` and machine `i`, with `x[j][k]` binary and `C[k][i]`
//! continuous:
//!
//! ```text
//! sum over k of x[j][k] = 1                      each job takes one position
//! sum over j of x[j][k] = 1                      each position takes one job
//! C[k][i] - C[k-1][i] - sum_j x[j][k] p[j][i] >= 0    machine predecessor
//! C[k][i] - C[k][i-1] - sum_j x[j][k] p[j][i] >= 0    job predecessor
//! minimize C[n-1][m-1]
//! ```
//!
//! Both predecessor families are inequalities rather than equations, so a
//! completion time may exceed the recurrence's value. Minimizing the last one
//! drives every completion time that matters down to it, and requirement 15's
//! cross-check against the recurrence is what confirms this rather than assuming
//! it.

use optimizer_core::{
    Bound, Candidate, Constraint, Domain, ErrorKind, LinearTerm, Model, ModelDocument, Objective,
    ObjectiveSense, SCHEMA_VERSION, Tolerances, ValidationError, Variable,
};

use crate::evaluate;
use crate::instance::FlowShopInstance;

/// Variable identity for the binary placing `job` in `position`.
///
/// Requirement 13 requires a stable documented identity, so a reader can map an
/// identifier to its meaning arithmetically without consulting this code. The
/// assignment block comes first, ordered by position and then by job.
pub fn assignment_variable(instance: &FlowShopInstance, job: usize, position: usize) -> u32 {
    let jobs = instance.jobs();
    (position * jobs + job) as u32
}

/// Variable identity for the completion time of `position` on `machine`.
///
/// The completion-time block follows the whole assignment block, ordered by
/// position and then by machine.
pub fn completion_variable(instance: &FlowShopInstance, position: usize, machine: usize) -> u32 {
    let jobs = instance.jobs();
    let machines = instance.machines();
    (jobs * jobs + position * machines + machine) as u32
}

/// Build the positional model for `instance`.
///
/// The model's `model_id` is the instance identity, so a record naming a model
/// names the instance it came from.
///
/// # Errors
///
/// Returns an unsupported failure when the encoded size would exceed the variable
/// identifier space, and whatever [`Model::new`] returns for the built document.
pub fn model(instance: &FlowShopInstance) -> Result<Model, ValidationError> {
    let jobs = instance.jobs();
    let machines = instance.machines();
    // Identifiers are u32. The document limits keep this far inside range, but the
    // check is explicit so a future limit increase fails loudly here.
    let total = (jobs * jobs + jobs * machines) as u64;
    if total > u64::from(u32::MAX) {
        return Err(ValidationError::new(
            ErrorKind::Unsupported,
            format!("encoded model would need {total} variables, above the identifier space"),
        ));
    }

    let mut variables = Vec::with_capacity(jobs * jobs + jobs * machines);
    for position in 0..jobs {
        for job in 0..jobs {
            variables.push(Variable {
                id: assignment_variable(instance, job, position),
                domain: Domain::Binary,
                lower: Bound::Finite { value: 0.0 },
                upper: Bound::Finite { value: 1.0 },
            });
        }
    }
    // Completion times are bounded below by zero and above by the total work,
    // which is a valid bound because no schedule can finish later than processing
    // every operation back to back. It is derived from the instance rather than
    // chosen, so it is not a big-M: it constrains nothing an optimal schedule
    // needs and exists so the relaxation is bounded.
    let horizon = total_work(instance);
    for position in 0..jobs {
        for machine in 0..machines {
            variables.push(Variable {
                id: completion_variable(instance, position, machine),
                domain: Domain::Continuous,
                lower: Bound::Finite { value: 0.0 },
                upper: Bound::Finite { value: horizon },
            });
        }
    }

    let mut constraints = Vec::new();
    let mut next_constraint = 0u32;
    let mut push = |constraints: &mut Vec<Constraint>, lower, upper, terms| {
        constraints.push(Constraint {
            id: next_constraint,
            lower,
            upper,
            terms,
        });
        next_constraint += 1;
    };

    // Each job takes exactly one position.
    for job in 0..jobs {
        let terms = (0..jobs)
            .map(|position| LinearTerm {
                variable_id: assignment_variable(instance, job, position),
                coefficient: 1.0,
            })
            .collect();
        push(
            &mut constraints,
            Bound::Finite { value: 1.0 },
            Bound::Finite { value: 1.0 },
            terms,
        );
    }
    // Each position takes exactly one job.
    for position in 0..jobs {
        let terms = (0..jobs)
            .map(|job| LinearTerm {
                variable_id: assignment_variable(instance, job, position),
                coefficient: 1.0,
            })
            .collect();
        push(
            &mut constraints,
            Bound::Finite { value: 1.0 },
            Bound::Finite { value: 1.0 },
            terms,
        );
    }
    // Completion-time propagation. Both families share the selected-processing-time
    // expression, which is linear because the processing time is a constant per
    // (job, machine) and the selection variable is what varies.
    for position in 0..jobs {
        for machine in 0..machines {
            for predecessor in Predecessor::both() {
                let previous = match predecessor {
                    Predecessor::Machine => position
                        .checked_sub(1)
                        .map(|previous| completion_variable(instance, previous, machine)),
                    Predecessor::Job => machine
                        .checked_sub(1)
                        .map(|previous| completion_variable(instance, position, previous)),
                };
                let mut terms = Vec::with_capacity(jobs + 2);
                terms.push(LinearTerm {
                    variable_id: completion_variable(instance, position, machine),
                    coefficient: 1.0,
                });
                if let Some(previous) = previous {
                    terms.push(LinearTerm {
                        variable_id: previous,
                        coefficient: -1.0,
                    });
                }
                for job in 0..jobs {
                    terms.push(LinearTerm {
                        variable_id: assignment_variable(instance, job, position),
                        coefficient: -f64::from(instance.processing_time(job, machine)),
                    });
                }
                // A free upper bound keeps this an inequality: a completion time
                // may exceed both predecessors, and the objective is what pulls it
                // down.
                push(
                    &mut constraints,
                    Bound::Finite { value: 0.0 },
                    Bound::PositiveInfinity,
                    terms,
                );
            }
        }
    }

    let objective = Objective {
        sense: ObjectiveSense::Minimize,
        offset: 0.0,
        terms: vec![LinearTerm {
            variable_id: completion_variable(instance, jobs - 1, machines - 1),
            coefficient: 1.0,
        }],
    };

    Model::new(ModelDocument {
        schema_version: SCHEMA_VERSION,
        model_id: instance.instance_id().to_string(),
        variables,
        constraints,
        objective,
    })
}

/// Which predecessor a propagation constraint refers to.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
enum Predecessor {
    /// The same machine's previous position.
    Machine,
    /// The same position's previous machine.
    Job,
}

impl Predecessor {
    fn both() -> [Self; 2] {
        [Self::Machine, Self::Job]
    }
}

/// Sum of every processing time, a valid completion-time horizon.
fn total_work(instance: &FlowShopInstance) -> f64 {
    let total: u64 = (0..instance.jobs())
        .map(|job| instance.job_total(job))
        .sum();
    // A u64 total of bounded times converts exactly at these sizes; the cast is
    // checked by the document limits rather than assumed.
    total as f64
}

/// Build a candidate over the encoded model from a permutation.
///
/// The completion times are the recurrence's own values, so a candidate produced
/// here is feasible exactly when the permutation is valid. Requirement 19 still
/// has the core revalidate it: this function's output is a proposal, not a claim.
///
/// # Errors
///
/// Returns whatever the recurrence returns for an invalid permutation.
pub fn candidate(
    instance: &FlowShopInstance,
    sequence: &[usize],
) -> Result<Candidate, ValidationError> {
    evaluate::validate_permutation(instance, sequence)?;
    let jobs = instance.jobs();
    let machines = instance.machines();
    let mut values = Vec::with_capacity(jobs * jobs + jobs * machines);
    for (position, &placed) in sequence.iter().enumerate() {
        for job in 0..jobs {
            values.push(optimizer_core::Assignment {
                variable_id: assignment_variable(instance, job, position),
                value: if placed == job { 1.0 } else { 0.0 },
            });
        }
    }
    // Recompute the full completion matrix. `evaluate` exposes only the last
    // machine's times, so the recurrence is applied here for every machine using
    // the same rule; this stays inside the encoding because it is building a
    // candidate rather than deciding what a schedule costs.
    let mut row = vec![0u64; machines];
    for (position, &job) in sequence.iter().enumerate() {
        let mut previous_machine = 0u64;
        for (machine, entry) in row.iter_mut().enumerate() {
            let start = previous_machine.max(*entry);
            let finish = start
                .checked_add(u64::from(instance.processing_time(job, machine)))
                .ok_or_else(|| {
                    ValidationError::new(
                        ErrorKind::Numerical,
                        "completion time overflowed while building a candidate",
                    )
                })?;
            *entry = finish;
            previous_machine = finish;
            values.push(optimizer_core::Assignment {
                variable_id: completion_variable(instance, position, machine),
                value: finish as f64,
            });
        }
    }
    Ok(Candidate {
        schema_version: SCHEMA_VERSION,
        model_id: instance.instance_id().to_string(),
        values,
    })
}

/// Recover the permutation a candidate over the encoded model describes.
///
/// Requirement 14 forbids rounding, repairing or completing a candidate that does
/// not decode. A fractional assignment beyond the integrality tolerance, a
/// position selecting two jobs, and a job placed nowhere are each refused.
///
/// # Errors
///
/// Returns a candidate failure for a wrong model identity, a missing assignment
/// variable, a value that is neither zero nor one within tolerance, a position
/// without exactly one selected job, or a decoded sequence that is not a
/// permutation.
pub fn permutation(
    instance: &FlowShopInstance,
    candidate: &Candidate,
    tolerances: Tolerances,
) -> Result<Vec<usize>, ValidationError> {
    if candidate.model_id != instance.instance_id() {
        return Err(ValidationError::new(
            ErrorKind::Candidate,
            format!(
                "candidate names model {}, expected instance {}",
                candidate.model_id,
                instance.instance_id()
            ),
        ));
    }
    let jobs = instance.jobs();
    let mut sequence = Vec::with_capacity(jobs);
    for position in 0..jobs {
        let mut selected = None;
        for job in 0..jobs {
            let id = assignment_variable(instance, job, position);
            let value = candidate
                .values
                .iter()
                .find(|assignment| assignment.variable_id == id)
                .map(|assignment| assignment.value)
                .ok_or_else(|| {
                    ValidationError::new(
                        ErrorKind::Candidate,
                        format!("candidate omits assignment variable {id}"),
                    )
                })?;
            let integral = value.round();
            if (value - integral).abs() > tolerances.integrality {
                return Err(ValidationError::new(
                    ErrorKind::Candidate,
                    format!(
                        "assignment variable {id} is {value}, which is not integral within {}",
                        tolerances.integrality
                    ),
                ));
            }
            if integral != 0.0 && integral != 1.0 {
                return Err(ValidationError::new(
                    ErrorKind::Candidate,
                    format!("assignment variable {id} rounds to {integral}, expected 0 or 1"),
                ));
            }
            if integral == 1.0 {
                if selected.is_some() {
                    return Err(ValidationError::new(
                        ErrorKind::Candidate,
                        format!("position {position} selects more than one job"),
                    ));
                }
                selected = Some(job);
            }
        }
        sequence.push(selected.ok_or_else(|| {
            ValidationError::new(
                ErrorKind::Candidate,
                format!("position {position} selects no job"),
            )
        })?);
    }
    // A per-position check cannot catch one job filling two positions, so the
    // decoded sequence is validated as a permutation before it is returned.
    evaluate::validate_permutation(instance, &sequence)?;
    Ok(sequence)
}
