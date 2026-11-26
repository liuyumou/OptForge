//! General sparse low-bit operators with original-model certificate authority.
pub mod operator;
pub mod solve;
pub type Result<T> = std::result::Result<T, Box<dyn std::error::Error>>;
pub mod assessment;
pub use optimizer_lp::tree_sum;
#[allow(dead_code)]
#[path = "../../lp-mixed2-checker2/src/cached_certificate.rs"]
mod cached_certificate;
pub mod control;
pub mod device;
pub mod engine;
#[allow(dead_code)]
mod exact_math;
pub mod gpu;
pub mod gpu_control;
pub mod gpu_packing;
pub mod gpu_prepare;
pub mod host;
pub mod implied;
pub mod input;
pub mod merit;
#[allow(dead_code)]
#[path = "../../../crates/optimizer-lp/src/outward.rs"]
mod outward;
#[allow(dead_code)]
mod prepared_feasibility;
#[allow(dead_code)]
#[path = "../../../crates/optimizer-lp/src/reduce.rs"]
mod reduce;
pub mod repair;

pub mod array_assessment;
pub mod array_input;
pub mod billion;
pub mod bounded_certificate;
pub mod fast_device;
pub mod gpu_tensor;
pub mod scratch_certificate;
pub mod tensor;
pub mod tensor_device;

pub mod tensor_prepare;
mod tensor_prepare_encode;
pub mod tensor_prepare_reference;

mod phase_profile;
