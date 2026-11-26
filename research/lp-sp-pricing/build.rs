use std::{env, path::PathBuf, process::Command};

fn main() {
    println!("cargo:rerun-if-changed=native/batch.cu");
    println!("cargo:rerun-if-env-changed=CUDA_HOME");
    if env::var_os("CARGO_FEATURE_CUDA").is_none() { return; }
    let cuda = PathBuf::from(env::var("CUDA_HOME").unwrap_or("/usr/local/cuda".into()));
    let out = PathBuf::from(env::var_os("OUT_DIR").unwrap());
    let status = Command::new(cuda.join("bin/nvcc"))
        .args(["-std=c++17", "-O3", "--fmad=false", "-Xcompiler", "-fPIC", "-lib"])
        .arg("native/batch.cu").arg("-o").arg(out.join("libsp_batch.a"))
        .status().expect("CUDA compiler unavailable");
    assert!(status.success(), "CUDA compilation failed");
    println!("cargo:rustc-link-search=native={}", out.display());
    println!("cargo:rustc-link-search=native={}", cuda.join("lib64").display());
    println!("cargo:rustc-link-lib=static=sp_batch");
    println!("cargo:rustc-link-lib=dylib=cudart");
    println!("cargo:rustc-link-lib=dylib=stdc++");
    println!("cargo:rustc-link-arg=-Wl,-rpath,{}", cuda.join("lib64").display());
}
