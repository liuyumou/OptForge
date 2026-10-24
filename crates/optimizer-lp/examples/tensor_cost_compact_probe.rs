//! Streaming exact compact-preparation comparison adapter for ADR-0044.
use optimizer_core::{LpSettings, Model};
use optimizer_lp::{Engine, LinearProgram, quant, tensor_cost, tensor_residual};
use std::io::{self, Write};
macro_rules! dump {
    ($op:expr,$path:expr) => {{
        let op = $op;
        let file = std::fs::OpenOptions::new()
            .write(true)
            .create_new(true)
            .open($path)
            .unwrap();
        let mut out = io::BufWriter::new(file);
        macro_rules! row {
            ($v:expr) => {{
                serde_json::to_writer(&mut out, &$v).unwrap();
                out.write_all(b"\n").unwrap();
            }};
        }
        for v in [
            &op.values,
            &op.quantized,
            &op.represented,
            &op.low_error,
            &op.native_error,
            &op.representation_error,
            &op.row_scale,
            &op.column_scale,
        ] {
            row!(v);
        }
        for v in [
            &op.line,
            &op.group,
            &op.group_tiles,
            &op.ids,
            &op.inputs,
            &op.entries,
            &op.dense_rows,
            &op.dense_columns,
        ] {
            row!(v);
        }
        row!(&op.row_of);
        row!(&op.column_of);
        row!(&op.tile_of);
        row!(&op.selected);
        row!(&op.dense);
        row!(&op.dense_exponents);
        row!(op.initial());
        for groups in op.row_groups.iter().chain(&op.column_groups) {
            row!(groups.len());
            for g in groups {
                row!((
                    g.tile,
                    &g.ids,
                    g.error,
                    g.original_error,
                    g.mass,
                    g.original_mass
                ));
            }
        }
        out.flush().unwrap();
    }};
}
fn main() {
    let args = std::env::args().skip(1).collect::<Vec<_>>();
    assert_eq!(args.len(), 3);
    let model = Model::from_json(&std::fs::read(&args[1]).unwrap()).unwrap();
    let p = LinearProgram::new(&model).unwrap();
    let settings =
        LpSettings::from_json(include_bytes!("../../../examples/lp-settings-v1.json")).unwrap();
    let e = Engine::new(&p, settings);
    let q = quant::Settings::new(quant::Format::Fp64, quant::Policy::Uniform);
    let metadata = if args[0] == "old" {
        match tensor_residual::Operator::new(&e, q, tensor_residual::Layout::Int8) {
            Ok(op) => {
                dump!(&op, &args[2]);
                serde_json::json!({"status":"prepared","legacy_bound":op.norm,"step":op.step})
            }
            Err(error) => serde_json::json!({"status":"refused","error":error}),
        }
    } else {
        assert_eq!(args[0], "new");
        match tensor_cost::Operator::new(&e, q, tensor_cost::Layout::Int8) {
            Ok(op) => {
                dump!(&op, &args[2]);
                serde_json::json!({"status":"prepared","legacy_bound":op.norm_proof.legacy_bound,"norm_proof":op.norm_proof,"step":op.step})
            }
            Err(error) => serde_json::json!({"status":"refused","error":error}),
        }
    };
    println!("{metadata}");
}
