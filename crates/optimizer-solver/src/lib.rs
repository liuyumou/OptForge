//! Owned solver executive reserved for C2 and SPEC-0003.
//!
//! This crate owns the search that proves optimality of an original M1 model.
//! It uses the backend-neutral [`optimizer_core::Backend`] contract purely as a
//! relaxation service and deliberately does not depend on any particular
//! backend, so its pruning and forfeiture rules are testable without a native
//! library.
//!
//! The central invariant is that a relaxation objective becomes a dual bound
//! only when that relaxation proved optimality. A limit, interruption or
//! failure inside a child solve forbids pruning at that node and permanently
//! forfeits the search's proof claim, recorded as `forfeited`. A search that
//! ran out of budget can therefore never be presented as a completed proof.
//!
//! Proven optimality means the executive exhausted its node tree under the
//! recorded numerical settings; it is not an exact-arithmetic certificate.

mod executive;
mod hooks;
mod node;
mod search;
mod serde_strict;

pub use executive::{initial_checkpoint, search, search_with_extensions};
pub use search::{
    Checkpoint, CheckpointNode, Restriction, SEARCH_SCHEMA_VERSION, SearchOptions, SearchOutcome,
    SearchRecord,
};

/// Identifier recorded for the relaxation service in every search record.
pub const RELAXATION_BACKEND: &str = "relaxation";

/// Normalize signed zero, matching optimizer-core's convention.
fn positive_zero(value: f64) -> f64 {
    if value == 0.0 { 0.0 } else { value }
}
