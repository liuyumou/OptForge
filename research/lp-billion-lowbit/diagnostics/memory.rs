//! A single CPU preparation in a fresh process; bounded digest scratch only.
use lp_billion_lowbit::{
    Result,
    array_input::{Original, Store},
    operator::Operator,
    solve::Settings,
    tensor::{Config, Packed, Tiles},
};
use serde_json::{Value, json};
use sha2::{Digest, Sha256};
use std::{path::Path, time::Instant};

fn memory() -> Value {
    let text = std::fs::read_to_string("/proc/self/status").expect("self status");
    let get = |name: &str| {
        text.lines()
            .find(|l| l.starts_with(name))
            .unwrap()
            .split_whitespace()
            .nth(1)
            .unwrap()
            .parse::<u64>()
            .unwrap()
            * 1024
    };
    json!({"rss_bytes":get("VmRSS:"),"hwm_bytes":get("VmHWM:")})
}
fn hash(h: &mut Sha256, name: &str, len: usize, mut bytes: impl Iterator<Item = u8>) {
    h.update(name.as_bytes());
    h.update((len as u64).to_le_bytes());
    let mut buffer = Vec::with_capacity(1 << 20);
    loop {
        buffer.clear();
        buffer.extend(bytes.by_ref().take(1 << 20));
        if buffer.is_empty() {
            break;
        }
        h.update(&buffer);
    }
}
fn tiles(h: &mut Sha256, t: &Tiles) {
    let fields: [(&str, &[u32]); 7] = [
        ("offsets", &t.offsets),
        ("columns", &t.columns),
        ("fragments", &t.fragments),
        ("covered", &t.covered),
        ("residual.offsets", &t.residual.offsets),
        ("residual.indices", t.residual.indices.as_ref()),
        ("residual.ids", &t.residual.ids),
    ];
    for (name, v) in fields {
        hash(h, name, v.len(), v.iter().flat_map(|v| v.to_le_bytes()));
    }
    hash(
        h,
        "exponents",
        t.exponents.len(),
        t.exponents.iter().flat_map(|v| v.to_le_bytes()),
    );
    for (name, v) in [
        ("metadata", t.metadata.as_slice()),
        ("residual.original", t.residual.original.as_ref()),
    ] {
        hash(
            h,
            name,
            v.len(),
            v.iter().flat_map(|v| v.to_bits().to_le_bytes()),
        );
    }
}
fn fingerprint(p: &Option<Packed>) -> String {
    let mut h = Sha256::new();
    if let Some(p) = p {
        for v in [p.components, p.tile_count, usize::from(p.compact_fragments)] {
            h.update((v as u64).to_le_bytes());
        }
        tiles(&mut h, &p.rows);
        tiles(&mut h, &p.columns);
    } else {
        h.update(b"no canonical tiles");
    }
    format!("{:x}", h.finalize())
}
fn run() -> Result<()> {
    let a: Vec<_> = std::env::args().collect();
    if a.len() != 5 || !["reference", "candidate"].contains(&a[4].as_str()) {
        return Err("usage: memory MODEL STORE REQUEST reference|candidate".into());
    }
    let all = Instant::now();
    let store = Store::new(Path::new(&a[2]))?;
    let original = Original::load(Path::new(&a[1]), &store)?;
    let input_ns = all.elapsed().as_nanos();
    let after_input = memory();
    let request: Value = serde_json::from_slice(&std::fs::read(&a[3])?)?;
    let settings: Settings = serde_json::from_value(request["settings"].clone())?;
    settings.validate()?;
    let mut config: Config = serde_json::from_value(request["tensor"].clone())?;
    config.components = settings.format.components();
    config.validate()?;
    let mut control = settings.clone();
    control.check_interval = config.control_interval;
    let start = Instant::now();
    let engine = lp_billion_lowbit::host::engine(&original.program, control.lp());
    let engine_ns = start.elapsed().as_nanos();
    let after_engine = memory();
    let start = Instant::now();
    let op = Operator::borrowed_native(&engine)?;
    let operator_ns = start.elapsed().as_nanos();
    let start = Instant::now();
    let packed = if a[4] == "candidate" {
        lp_billion_lowbit::tensor_prepare::prepare(&op, &config)?
    } else {
        lp_billion_lowbit::tensor_prepare_reference::prepare(&op, &config)?
    };
    let packing_ns = start.elapsed().as_nanos();
    let after_packing = memory();
    let packed_bytes = packed.as_ref().map_or(0, Packed::storage_bytes);
    let tile_count = packed.as_ref().map_or(0, |p| p.tile_count);
    let start = Instant::now();
    let sha256 = fingerprint(&packed);
    let fingerprint_ns = start.elapsed().as_nanos();
    drop(packed);
    let after_drop = memory();
    println!(
        "{}",
        json!({"status":"passed","implementation":a[4],"model_sha256":original.sha256,
        "rows":original.program.row_count(),"columns":original.program.column_count(),"nonzeros":original.program.nonzeros(),
        "packed_sha256":sha256,"packed_bytes":packed_bytes,"tile_count":tile_count,
        "input_ns":input_ns,"engine_ns":engine_ns,"operator_ns":operator_ns,"packing_ns":packing_ns,
        "preparation_ns":engine_ns+operator_ns+packing_ns,"fingerprint_ns":fingerprint_ns,"process_body_ns":all.elapsed().as_nanos(),
        "after_input":after_input,"after_engine":after_engine,"after_packing":after_packing,"after_drop":after_drop,
        "cuda_context_created":false,"lp_solve_executed":false})
    );
    Ok(())
}
fn main() {
    if let Err(e) = run() {
        eprintln!("{e}");
        std::process::exit(2);
    }
}
