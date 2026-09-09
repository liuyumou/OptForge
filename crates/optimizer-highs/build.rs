//! Locate the pinned HiGHS 1.11.0 CPU build and emit its link directives.
//!
//! The library is provisioned out of tree by `tools/setup_highs.sh` under
//! `target/native/`, so nothing native is tracked in source. When the `native`
//! feature is off, or the install prefix is absent, `highs_native` stays unset
//! and the adapter compiles to an explicit unsupported backend.

use std::path::PathBuf;

fn main() {
    println!("cargo:rerun-if-env-changed=AI_OPTIMIZER_HIGHS_DIR");
    println!("cargo:rustc-check-cfg=cfg(highs_native)");

    if std::env::var_os("CARGO_FEATURE_NATIVE").is_none() {
        return;
    }

    let prefix = install_prefix();
    let library = prefix.join("lib/libhighs.a");
    let header = prefix.join("include/highs/interfaces/highs_c_api.h");
    println!("cargo:rerun-if-changed={}", library.display());

    if !library.is_file() || !header.is_file() {
        println!(
            "cargo:warning=HiGHS not provisioned at {}; building the unsupported backend. \
             Run bash tools/setup_highs.sh for native acceptance.",
            prefix.display()
        );
        return;
    }

    println!(
        "cargo:rustc-link-search=native={}",
        prefix.join("lib").display()
    );
    println!("cargo:rustc-link-lib=static=highs");
    // HiGHS is C++; its static archive needs the C++ runtime.
    println!("cargo:rustc-link-lib=dylib=stdc++");
    println!("cargo:rustc-cfg=highs_native");
}

fn install_prefix() -> PathBuf {
    if let Some(dir) = std::env::var_os("AI_OPTIMIZER_HIGHS_DIR") {
        return PathBuf::from(dir);
    }
    // crates/optimizer-highs -> repository root.
    let manifest = PathBuf::from(std::env::var_os("CARGO_MANIFEST_DIR").expect("manifest dir"));
    manifest
        .join("../..")
        .join("target/native/highs-1.11.0/install")
}
