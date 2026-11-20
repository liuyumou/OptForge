//! CPU-only stage diagnostic; does not execute a solve or create a CUDA context.
use lp_billion_lowbit::{
    Result,
    array_input::{Original, Store},
    operator::{Operator, Orientation},
    solve::Settings,
    tensor::{Config, Packed, Tiles},
};
use serde_json::{Value, json};
use std::{path::Path, time::Instant};

fn bits(a: &[f64], b: &[f64]) -> bool {
    a.len() == b.len() && a.iter().zip(b).all(|(a, b)| a.to_bits() == b.to_bits())
}
fn orientation(a: &Orientation<'_>, b: &Orientation<'_>) -> bool {
    a.offsets == b.offsets
        && a.indices == b.indices
        && a.ids == b.ids
        && bits(&a.original, &b.original)
}
fn tiles(a: &Tiles, b: &Tiles) -> bool {
    a.offsets == b.offsets
        && a.columns == b.columns
        && a.fragments == b.fragments
        && a.exponents == b.exponents
        && a.covered == b.covered
        && bits(&a.metadata, &b.metadata)
        && orientation(&a.residual, &b.residual)
}
fn exact(a: &Option<Packed>, b: &Option<Packed>) -> bool {
    match (a, b) {
        (None, None) => true,
        (Some(a), Some(b)) => {
            a.components == b.components
                && a.tile_count == b.tile_count
                && a.compact_fragments == b.compact_fragments
                && tiles(&a.rows, &b.rows)
                && tiles(&a.columns, &b.columns)
        }
        _ => false,
    }
}
fn run() -> Result<()> {
    let a: Vec<_> = std::env::args().collect();
    if a.len() != 5 || !["reference-first", "candidate-first"].contains(&a[4].as_str()) {
        return Err("usage: packing MODEL STORE REQUEST reference-first|candidate-first".into());
    }
    let store = Store::new(Path::new(&a[2]))?;
    let started = Instant::now();
    let original = Original::load(Path::new(&a[1]), &store)?;
    let input_ns = started.elapsed().as_nanos();
    let request: Value = serde_json::from_slice(&std::fs::read(&a[3]).map_err(|e| e.to_string())?)?;
    let settings: Settings = serde_json::from_value(request["settings"].clone())?;
    settings.validate()?;
    let mut config: Config = serde_json::from_value(request["tensor"].clone())?;
    config.components = settings.format.components();
    config.validate()?;
    let mut control = settings.clone();
    control.check_interval = config.control_interval;
    let started = Instant::now();
    let engine = lp_billion_lowbit::host::engine(&original.program, control.lp());
    let engine_ns = started.elapsed().as_nanos();
    let started = Instant::now();
    let op = Operator::borrowed_native(&engine)?;
    let operator_ns = started.elapsed().as_nanos();
    let reference = || -> Result<(Option<Packed>, u128)> {
        let started = Instant::now();
        // Include destruction of the discarded zero-tile arrays, just as v4 does.
        let packed = Some(Packed::proposal(&op, &config)?).filter(|p| p.tile_count > 0);
        Ok((packed, started.elapsed().as_nanos()))
    };
    let candidate = || -> Result<(Option<Packed>, u128)> {
        let started = Instant::now();
        let packed = lp_billion_lowbit::tensor_prepare::prepare(&op, &config)?;
        Ok((packed, started.elapsed().as_nanos()))
    };
    let (before, after) = if a[4] == "reference-first" {
        (reference()?, candidate()?)
    } else {
        let after = candidate()?;
        (reference()?, after)
    };
    if !exact(&before.0, &after.0) {
        return Err("complete packed representation differs".into());
    }
    println!(
        "{}",
        json!({"status":"passed","exact":true,"order":a[4],"model_sha256":original.sha256,
            "nonzeros":original.program.nonzeros(),"rows":original.program.row_count(),
            "columns":original.program.column_count(),"tile_count":after.0.as_ref().map_or(0,|p|p.tile_count),
            "input_ns":input_ns,"engine_ns":engine_ns,"operator_ns":operator_ns,
            "reference_packing_ns":before.1,"candidate_packing_ns":after.1,
            "cuda_context_created":false,"lp_solve_executed":false})
    );
    Ok(())
}
fn main() {
    if let Err(error) = run() {
        eprintln!("{error}");
        std::process::exit(2);
    }
}
