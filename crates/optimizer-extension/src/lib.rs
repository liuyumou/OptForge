//! Extension runtime and authority model under SPEC-0004 and ADR-0005.
//!
//! This crate defines what a separately authored component may propose to the
//! [C2 executive](../optimizer_solver/index.html) and, more importantly, what it
//! may not claim. Extensions declare their identity, category, host contract
//! version, determinism and budgets; the core decides what is true.
//!
//! The central rule is that an extension has no mathematical authority. A
//! proposed candidate becomes an incumbent only after
//! [`optimizer_core::Model::evaluate`] validates it against the original model,
//! and the recorded objective is that recomputation, never a value the
//! extension asserted. Proposed search actions take effect only after the
//! executive checks them against its own state.
//!
//! No path through this crate can forfeit a proof claim, end a search, or turn
//! an extension's misbehavior into an error the caller must propagate. An
//! adversarial extension can waste its budget and have every proposal refused;
//! it cannot deny a proof the engine would otherwise complete. Invalid actions,
//! incompatible versions, contained panics and exhausted budgets become typed
//! entries in a search record rather than silent degradation.
//!
//! Containment is panic containment only. A process abort, stack exhaustion or
//! memory fault is outside this boundary; process isolation is deferred and
//! requires its own decision record.

mod declare;
mod guard;
mod hook;
mod record;
mod serde_strict;
mod view;

pub use declare::{
    Authority, Category, DeclaredLimits, EXTENSION_SCHEMA_VERSION, ExtensionDeclaration,
    MAX_EXTENSION_ID_BYTES,
};
pub use guard::{ExtensionHost, Registration};
pub use hook::{Advice, CandidateProducer, Extension, SearchAdviser};
/// The model class an extension declares it supports.
///
/// Re-exported rather than defined here: SPEC-0011 needs the same concept on the
/// solve contract, and one type with one wire form is what keeps a registry
/// entry's `continuous` and a backend's `continuous` from becoming two unrelated
/// facts. Every `optimizer_extension::ProblemClass` path keeps working.
pub use optimizer_core::ProblemClass;
pub use record::{
    ExtensionFailure, ExtensionPolicy, ExtensionSummary, FailureKind, MAX_FAILURE_MESSAGE_BYTES,
    MAX_RETAINED_FAILURES, validate_policies,
};
pub use view::{FractionalVariable, OpenNodeSummary, SearchSnapshot};
