//! General sparse low-bit operators with original-model certificate authority.
pub mod operator;
pub mod solve;
pub type Result<T> = std::result::Result<T, Box<dyn std::error::Error>>;
pub mod control;
pub mod device;
pub mod gpu;
pub mod implied;
pub mod merit;
pub mod repair;

pub mod fast_device;
pub mod gpu_tensor;
pub mod tensor;
pub mod tensor_device;
