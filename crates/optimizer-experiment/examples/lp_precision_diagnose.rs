//! Read-only export of represented operators from independently checked evidence.
//! This example performs no solve and adds no runtime arithmetic policy.
use optimizer_core::{LpPrecisionSettings, Model};
use optimizer_experiment::lp::LpEndpoint;
use optimizer_lp::{LinearProgram, pdhg::Engine, precision::PrecisionOperator};
use serde_json::json;

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args: Vec<_> = std::env::args().collect();
    if args.len() != 3 {
        return Err("usage: lp_precision_diagnose MODEL VERIFIED-ENDPOINT".into());
    }
    let bytes = std::fs::read(&args[1])?;
    let endpoint = LpEndpoint::from_json(&std::fs::read(&args[2])?)?;
    endpoint.verify(&bytes)?;
    let program = LinearProgram::new(&Model::from_json(&bytes)?)?;
    let engine = Engine::new(
        &program,
        endpoint.record.lp_settings.ok_or("method missing")?,
    );
    let settings = LpPrecisionSettings::from_json(include_bytes!(
        "../../../examples/lp-storage-fp32-v1.json"
    ))?;
    let op = PrecisionOperator::new(&engine, &settings)?;
    let (scaled, _) = engine.scaled_matrix();
    let entries: Vec<_> = program
        .row_major()
        .entries()
        .enumerate()
        .map(|(i, (row, column, original))| json!([row, column, original, scaled[i], op.rows[i]]))
        .collect();
    let original_exact = program
        .row_major()
        .entries()
        .filter(|(_, _, v)| f64::from(*v as f32) == *v)
        .count();
    let scaled_exact = scaled.iter().filter(|&&v| f64::from(v as f32) == v).count();
    println!(
        "{}",
        json!({"schema_version":1,"kind":"representation_diagnostic_only",
            "model_sha256":endpoint.model_sha256,"rows":program.row_count(),
            "columns":program.column_count(),"nonzeros":program.nonzeros(),
            "original_exact_fp32":original_exact,"scaled_exact_fp32":scaled_exact,
            "original_step":engine.step(),"precision_step":op.step,"operator_bounds":op.bounds,
            "max_scaled_conversion_error":op.max_error,"row_scale":engine.preconditioner().row(),
            "column_scale":engine.preconditioner().column(),
            "entry_fields":["row","column","original","scaled_original","scaled_fp32"],
            "entries":entries})
    );
    Ok(())
}
