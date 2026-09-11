//! Scheduling candidate producers under SPEC-0008 requirements 17 to 21.
//!
//! These producers live outside `optimizer-schedule` on purpose. This crate depends
//! only on the published core, extension and scheduling APIs and takes the
//! executive as a test-only dependency, so "a scheduling producer needs no
//! engine-internal change" is established by the workspace building at all rather
//! than asserted in prose. ADR-0005 established the same evidence the same way for
//! the example extensions, and ADR-0007 reuses it.
//!
//! A producer here holds no mathematical authority. It proposes a complete
//! assignment; the core validates it against the original model with
//! `Model::evaluate` and records the recomputed objective, never one a producer
//! asserted. A producer that proposed nonsense would have it refused and recorded,
//! and the search's outcome, proven optimum, dual bound, forfeiture state and prune
//! counters would be unchanged.

use std::cell::Cell;

use optimizer_core::{Assignment, Candidate};
use optimizer_extension::{
    CandidateProducer, Category, DeclaredLimits, EXTENSION_SCHEMA_VERSION, Extension,
    ExtensionDeclaration, ProblemClass, SearchSnapshot,
};
use optimizer_schedule::FlowShopInstance;

/// Proposes the NEH permutation, then one insertion-improvement pass over it.
///
/// The producer holds its own instance because a [`SearchSnapshot`] carries the
/// encoded model rather than the instance it came from. Requirement 19 makes that
/// harmless: a proposal is checked against the model the executive holds, so a
/// producer paired with the wrong instance has its proposals refused rather than
/// believed.
#[derive(Debug)]
pub struct SchedulingProducer {
    instance: FlowShopInstance,
    proposals: Cell<u64>,
}

impl SchedulingProducer {
    /// Identifier this producer declares.
    pub const ID: &'static str = "flow-shop-neh";

    /// Build a producer for one instance.
    pub fn new(instance: FlowShopInstance) -> Self {
        Self {
            instance,
            proposals: Cell::new(0),
        }
    }

    /// How many candidates this producer has returned.
    ///
    /// Exposed so a test can assert the producer was actually invoked before
    /// asserting anything about its effect. An independence test over a producer
    /// that was never consulted proves nothing, which is the lesson C3 recorded
    /// when three of its acceptance tests turned out to be vacuous.
    pub fn proposals(&self) -> u64 {
        self.proposals.get()
    }
}

impl Extension for SchedulingProducer {
    fn declare(&self) -> ExtensionDeclaration {
        ExtensionDeclaration {
            schema_version: EXTENSION_SCHEMA_VERSION,
            extension_id: Self::ID.to_string(),
            version: env!("CARGO_PKG_VERSION").to_string(),
            host_contract_version: EXTENSION_SCHEMA_VERSION,
            category: Category::CandidateProducer,
            // The encoded model always has binary assignment variables, so it is
            // always discrete. Declaring only that class means the host refuses to
            // invoke this producer on a continuous model rather than trusting it to
            // decline.
            problem_classes: vec![ProblemClass::Discrete],
            deterministic: true,
            limits: DeclaredLimits {
                max_invocations: 1,
                max_proposals: 2,
            },
        }
    }
}

/// Proposes schedules the core must refuse, for requirement 20's invariance check.
///
/// Requirement 20 is about a *refused* proposal leaving a search's conclusions and
/// prune counters untouched. An honest producer cannot test that: its accepted
/// incumbent legitimately prunes more by bound, which is the entire purpose of a
/// candidate producer. So the invariance claim needs a producer whose every
/// proposal is rejected, which is what this is.
#[derive(Debug)]
pub struct RefusedProducer {
    instance: FlowShopInstance,
    kind: RefusedKind,
    proposals: Cell<u64>,
}

/// How a [`RefusedProducer`] makes its proposals invalid.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum RefusedKind {
    /// A candidate placing every job in position zero: infeasible assignment rows.
    RepeatedPosition,
    /// A candidate whose completion times are far below the recurrence's values,
    /// violating the propagation constraints.
    ImpossiblyEarly,
}

impl RefusedProducer {
    /// Identifier this producer declares.
    pub const ID: &'static str = "flow-shop-refused";

    /// Build a producer that proposes only invalid candidates.
    pub fn new(instance: FlowShopInstance, kind: RefusedKind) -> Self {
        Self {
            instance,
            kind,
            proposals: Cell::new(0),
        }
    }

    /// How many candidates this producer has returned.
    pub fn proposals(&self) -> u64 {
        self.proposals.get()
    }
}

impl Extension for RefusedProducer {
    fn declare(&self) -> ExtensionDeclaration {
        ExtensionDeclaration {
            schema_version: EXTENSION_SCHEMA_VERSION,
            extension_id: Self::ID.to_string(),
            version: env!("CARGO_PKG_VERSION").to_string(),
            host_contract_version: EXTENSION_SCHEMA_VERSION,
            category: Category::CandidateProducer,
            problem_classes: vec![ProblemClass::Discrete],
            deterministic: true,
            limits: DeclaredLimits {
                max_invocations: u64::MAX,
                max_proposals: u64::MAX,
            },
        }
    }
}

impl CandidateProducer for RefusedProducer {
    fn propose(&self, _snapshot: &SearchSnapshot<'_>) -> Vec<Candidate> {
        let jobs = self.instance.jobs();
        let machines = self.instance.machines();
        let mut values = Vec::new();
        match self.kind {
            RefusedKind::RepeatedPosition => {
                // Every job in position zero, nothing anywhere else. The
                // one-job-per-position rows are violated, so the core refuses it.
                for position in 0..jobs {
                    for job in 0..jobs {
                        values.push(Assignment {
                            variable_id: optimizer_schedule::assignment_variable(
                                &self.instance,
                                job,
                                position,
                            ),
                            value: if position == 0 { 1.0 } else { 0.0 },
                        });
                    }
                }
                for position in 0..jobs {
                    for machine in 0..machines {
                        values.push(Assignment {
                            variable_id: optimizer_schedule::completion_variable(
                                &self.instance,
                                position,
                                machine,
                            ),
                            value: 0.0,
                        });
                    }
                }
            }
            RefusedKind::ImpossiblyEarly => {
                // A genuine permutation, but every completion time is zero, which
                // violates every propagation constraint at once.
                for position in 0..jobs {
                    for job in 0..jobs {
                        values.push(Assignment {
                            variable_id: optimizer_schedule::assignment_variable(
                                &self.instance,
                                job,
                                position,
                            ),
                            value: if job == position { 1.0 } else { 0.0 },
                        });
                    }
                }
                for position in 0..jobs {
                    for machine in 0..machines {
                        values.push(Assignment {
                            variable_id: optimizer_schedule::completion_variable(
                                &self.instance,
                                position,
                                machine,
                            ),
                            value: 0.0,
                        });
                    }
                }
            }
        }
        self.proposals.set(self.proposals.get() + 1);
        vec![Candidate {
            schema_version: optimizer_core::SCHEMA_VERSION,
            model_id: self.instance.instance_id().to_string(),
            values,
        }]
    }
}

impl CandidateProducer for SchedulingProducer {
    fn propose(&self, _snapshot: &SearchSnapshot<'_>) -> Vec<Candidate> {
        // Both heuristics are deterministic and depend only on the instance, so
        // proposing once is enough; the declared invocation budget says so. A
        // failure here returns no candidates rather than propagating, because
        // requirement 21 forbids a producer turning its own trouble into the
        // caller's error.
        let Ok(constructed) = optimizer_schedule::neh(&self.instance) else {
            return Vec::new();
        };
        let mut sequences = vec![constructed.clone()];
        if let Ok(improved) = optimizer_schedule::insertion(&self.instance, &constructed)
            && improved != constructed
        {
            sequences.push(improved);
        }
        let candidates: Vec<Candidate> = sequences
            .iter()
            .filter_map(|sequence| optimizer_schedule::candidate(&self.instance, sequence).ok())
            .collect();
        self.proposals
            .set(self.proposals.get() + candidates.len() as u64);
        candidates
    }
}
