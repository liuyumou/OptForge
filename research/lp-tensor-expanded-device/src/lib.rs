//! Isolated ADR-0046 device integration; ordinary/default source stays exact.
pub use lp_tensor_expanded_research::value;
pub use optimizer_lp::{Engine, control, exec, precision, quant, reduce, research};
#[path = "../../lp-tensor-expanded/src/outward.rs"]
#[allow(dead_code)] // Retain the exact shared enclosure body, including unused sums.
pub mod outward;
#[path = "solver_adapter.rs"]
pub mod tensor_cost;
#[path = "../../lp-tensor-expanded/src/prepared.rs"]
pub mod tensor_cost_prepare;
