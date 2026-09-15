//! First-order linear programming on a device, under SPEC-0011 and ADR-0010.
//!
//! This crate is the device half of the GPU LP backend. It reaches hardware only
//! through `optimizer-cuda-sys`'s safe surface -- the single new unsafe boundary
//! ADR-0009 authorizes -- and takes its session and lease from `optimizer-cuda`, so
//! it contains no unsafe code of its own and opens no second boundary.
//!
//! It depends on `optimizer-lp` and never the other way round. That direction is
//! load-bearing: `optimizer-lp` is the oracle these kernels are checked against
//! under requirement 24, and an oracle that depended on the thing it checks would
//! establish nothing.
//!
//! Nothing here holds mathematical authority. The device computes iterates; the
//! host decides what they mean, and the bound in particular comes from a
//! certification that does not assume any of this computed correctly.

pub mod backend;
pub mod residency;

pub use backend::{BACKEND_NAME, BACKEND_VERSION, CudaLpBackend};
pub use residency::{
    AdvanceResult, Decline, KERNEL_NAMES, LpResidency, Requirement, TARGET_CAPABILITY,
    code_object_path, device_path_available,
};

pub mod tuned;
