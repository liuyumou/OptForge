//! Isolated ADR-0046 research implementation. Public solver sources stay exact.
pub use optimizer_lp::{Engine, control, exec, precision, quant, reduce, research};
pub mod value;
