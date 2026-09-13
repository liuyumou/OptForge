//! Flow-shop scheduling under SPEC-0008 and ADR-0007.
//!
//! A permutation flow shop: `n` jobs each visiting `m` machines in the same order,
//! scheduled in one job order used identically on every machine, minimizing the
//! completion time of the last job on the last machine.
//!
//! The crate is arranged around one rule. The `evaluate` module holds the makespan
//! recurrence and is the sole authority on what a schedule costs; it imports
//! neither `encode` nor `heuristic`. Two computations sharing an implementation
//! agree by construction, so keeping them apart is what makes their agreement
//! evidence. The `encode` module turns an instance into an ordinary
//! [`optimizer_core::Model`], which is why the existing solve, search, extension
//! and run-record contracts apply unchanged rather than being rebuilt here.
//!
//! Nothing in this crate claims tractability. The positional encoding is correct by
//! construction and its linear relaxation is weak, so proven optimality belongs to
//! tiny instances checked against exhaustive permutation enumeration, and the
//! frozen development subset carries feasibility and determinism evidence only.
//! SPEC-0008 requirement 26 makes that omission part of the contract.

mod encode;
mod evaluate;
mod generate;
mod heuristic;
mod instance;
mod serde_strict;

pub use encode::{assignment_variable, candidate, completion_variable, model, permutation};
pub use evaluate::{completion_times, makespan, validate_permutation};
pub use generate::{
    DEVELOPMENT_SUBSET, GENERATOR_NAME, Lehmer, PublishedInstance, SCALE_SUBSET, taillard_instance,
};
pub use heuristic::{insertion, neh};
pub use instance::{
    FlowShopDocument, FlowShopInstance, MAX_JOBS, MAX_MACHINES, MAX_PROCESSING_TIME,
    SCHEDULE_SCHEMA_VERSION,
};
