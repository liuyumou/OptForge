//! Locate the device code objects and record where they were found.
//!
//! They are provisioned out of tree by `tools/setup_cuda.sh` under `target/native/`,
//! so nothing device-specific is tracked in source and `nvcc` is never a dependency
//! of an ordinary build. When they are absent, `cuda_native` stays unset and the
//! device path reports an explicit unsupported backend, which is SPEC-0010
//! requirement 37 and the same shape ADR-0003 already uses for the pinned library.

use std::path::PathBuf;

fn main() {
    println!("cargo:rerun-if-env-changed=AI_OPTIMIZER_CUDA_DIR");
    println!("cargo:rustc-check-cfg=cfg(cuda_native)");

    let directory = code_object_directory();
    let cubin = directory.join("schedule_eval.cubin");
    println!("cargo:rerun-if-changed={}", cubin.display());

    // Baking the absolute directory in is what makes the runtime lookup independent
    // of the working directory. A relative default would resolve against wherever
    // the binary happened to be started, which for `cargo test` is the crate rather
    // than the workspace.
    println!(
        "cargo:rustc-env=AI_OPTIMIZER_CUDA_DEFAULT_DIR={}",
        directory.display()
    );

    if !cubin.is_file() {
        println!(
            "cargo:warning=device code objects not provisioned at {}; building without the \
             device path. Run bash tools/setup_cuda.sh for device acceptance.",
            directory.display()
        );
        return;
    }
    println!("cargo:rustc-cfg=cuda_native");
}

fn code_object_directory() -> PathBuf {
    if let Some(directory) = std::env::var_os("AI_OPTIMIZER_CUDA_DIR") {
        return PathBuf::from(directory);
    }
    // crates/optimizer-cuda -> repository root.
    let manifest = PathBuf::from(std::env::var_os("CARGO_MANIFEST_DIR").expect("manifest dir"));
    let root = manifest.join("../..");
    root.canonicalize()
        .unwrap_or(root)
        .join("target/native/cuda")
}
