//! First-order linear programming on the host, under SPEC-0011.
//!
//! This crate is the host half of the GPU LP backend, and it is deliberately
//! device-free: it builds and runs on a machine with no driver and no code
//! object. That is not a portability nicety. `state/backlog.yaml` requires a CPU
//! first-order method as the oracle for, and therefore before, the approximate
//! device one, and SPEC-0011 requirement 24 makes the device kernels checkable
//! against it. An oracle that needed the thing it checks would establish nothing.
//!
//! Requirement 26 draws the other line this crate must not cross. The host method
//! is *not* the fallback path: SPEC-0010 requirement 23 requires a fallback to be
//! the implementation the project already treats as authoritative, which is the
//! pinned HiGHS backend. Falling back to a second first-order implementation
//! written to match the kernel would make an agreement test compare a component
//! with itself.
//!
//! Nothing here carries mathematical authority either. The objective in a record
//! is the host's recomputation under SPEC-0002, the feasibility verdict is
//! `Model::evaluate`'s, and a bound comes only from the certification procedure,
//! which does not assume any iterate was computed correctly.

pub mod backend;
pub mod certify;
pub mod pdhg;
pub mod precondition;
pub mod problem;
pub mod reduce;

pub use backend::{BACKEND_NAME, BACKEND_VERSION, HostLpBackend};
pub use certify::{Certificate, NoBound, certify, certify_model};
/// The settings documents this crate's method reads.
///
/// Defined in `optimizer-core` beside every other wire format, because a solve
/// record carries them and records are core types. Re-exported so a caller of
/// this crate needs only one import.
pub use optimizer_core::{
    LP_SETTINGS_SCHEMA_VERSION, LpSettings, PreconditionerSettings, PrimalWeightSettings,
    RestartSettings,
};
pub use pdhg::{Decision, Engine, Iterate, Stop};
pub use precondition::Preconditioner;
pub use problem::{Compressed, LinearProgram, Range};
pub use reduce::{ReductionOrder, SEGMENT, sequential_sum, sum, tree_sum};
