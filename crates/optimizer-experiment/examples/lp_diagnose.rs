//! CPU-only diagnostic replay and component timings of frozen LP evidence.
//! This example uses existing numerical APIs; it is not another solver backend.
use optimizer_core::{Assignment, Candidate, Model, ValidationReport};
use optimizer_experiment::lp::LpEndpoint;
use optimizer_lp::{Engine, LinearProgram, certify};
use serde_json::json;
use std::hint::black_box;
use std::time::Instant;

fn timed(mut action: impl FnMut(), repeats: usize) -> Vec<u64> {
    (0..3)
        .map(|_| {
            let start = Instant::now();
            for _ in 0..repeats {
                action();
            }
            u64::try_from(start.elapsed().as_nanos() / repeats as u128).unwrap()
        })
        .collect()
}

fn validation(report: &ValidationReport) -> serde_json::Value {
    let checks = report
        .constraints
        .iter()
        .flat_map(|row| [row.lower.as_ref(), row.upper.as_ref()]);
    let mut max_violation = 0.0f64;
    let mut max_ratio = 0.0f64;
    let mut rejected = 0;
    for bound in checks.flatten() {
        max_violation = max_violation.max(bound.violation);
        max_ratio = max_ratio.max(bound.violation / bound.allowance.max(f64::MIN_POSITIVE));
        rejected += usize::from(!bound.satisfied);
    }
    json!({"feasible":report.feasible,"objective":report.objective,
        "max_row_violation":max_violation,"max_row_violation_over_allowance":max_ratio,
        "rejected_row_bounds":rejected})
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args: Vec<_> = std::env::args().collect();
    if args.len() != 4 || !["cost", "replay"].contains(&args[1].as_str()) {
        return Err("usage: lp_diagnose cost|replay MODEL ENDPOINT".into());
    }
    let model_bytes = std::fs::read(&args[2])?;
    let endpoint = LpEndpoint::from_json(&std::fs::read(&args[3])?)?;
    endpoint.verify(&model_bytes)?;
    let model = Model::from_json(&model_bytes)?;
    let program = LinearProgram::new(&model)?;
    let settings = endpoint.record.lp_settings.ok_or("LP settings required")?;
    let tolerances = endpoint.record.options.tolerances;
    let candidate = endpoint
        .record
        .candidate
        .as_ref()
        .ok_or("candidate required")?;
    let dual = endpoint.diagnostics.dual.as_ref().ok_or("dual required")?;
    let primal: Vec<_> = candidate.values.iter().map(|v| v.value).collect();
    let bound = certify(&program, dual).map_err(|e| e.to_string())?.bound;
    let mut output = json!({"schema_version":1,"kind":"diagnostic_only","model":model.document().model_id,
        "model_sha256":endpoint.model_sha256,"rows":program.row_count(),"columns":program.column_count(),
        "nonzeros":program.nonzeros(),"segment":optimizer_lp::SEGMENT,"settings":settings});
    if args[1] == "cost" {
        let repeats = 20;
        output["nanoseconds_per_call"] = json!({
            "model_evaluate":timed(|| {black_box(model.evaluate(black_box(candidate),tolerances).unwrap());},repeats),
            "certify":timed(|| {black_box(certify(&program,black_box(dual)).unwrap());},repeats),
            "gap":timed(|| {black_box(optimizer_lp::certify::assess_gap(&program,black_box(&primal),bound,tolerances));},repeats),
            "program_construction":timed(|| {black_box(LinearProgram::new(black_box(&model)).unwrap());},repeats),
            "endpoint_assessment":timed(|| {black_box(optimizer_experiment::lp::assess(&model,&endpoint.record,&endpoint.diagnostics).unwrap());},repeats)
        });
        output["blocks"] = json!(3);
        output["calls_per_block"] = json!(repeats);
        let mut reductions = Vec::new();
        for width in [4, 18, 32, 256, 1024] {
            let values: Vec<_> = (0..width).map(|i| f64::from(i % 7) / 8.0).collect();
            assert_eq!(
                optimizer_lp::tree_sum(&values),
                optimizer_lp::sequential_sum(&values)
            );
            reductions.push(json!({"width":width,"tree_ns":timed(|| {black_box(optimizer_lp::tree_sum(black_box(&values)));},10000),
                "sequential_ns":timed(|| {black_box(optimizer_lp::sequential_sum(black_box(&values)));},10000)}));
        }
        output["exact_dyadic_sum_microbench"] = json!(reductions);
    } else {
        if endpoint.requested_backend != "cuda-lp" || endpoint.record.backend != "cuda-lp" {
            return Err("fixed-control replay requires a CUDA endpoint".into());
        }
        let engine = Engine::new(&program, settings);
        let mut x = engine.start_primal();
        let mut y = engine.start_dual();
        let anchor_x = x.clone();
        let anchor_y = y.clone();
        let mut checkpoints = Vec::new();
        let start = Instant::now();
        let limit = endpoint
            .diagnostics
            .assessment_iteration
            .ok_or("assessment iteration required")?;
        for iteration in 0..limit {
            let (next_x, next_y) = engine.step_once(&x, &y, 1.0);
            let toward = (iteration + 1) as f64 / (iteration + 2) as f64;
            let back = 1.0 / (iteration + 2) as f64;
            for ((value, next), anchor) in x.iter_mut().zip(next_x).zip(&anchor_x) {
                *value = toward * next + back * anchor;
            }
            for ((value, next), anchor) in y.iter_mut().zip(next_y).zip(&anchor_y) {
                *value = toward * next + back * anchor;
            }
            let done = iteration + 1;
            if [200, 1000, 1200, 1400, 5000, 10000, 50000].contains(&done) || done == limit {
                let values = engine.unscale_primal(&x);
                let current = Candidate {
                    schema_version: 1,
                    model_id: model.document().model_id.clone(),
                    values: program
                        .variable_ids()
                        .iter()
                        .zip(values)
                        .map(|(id, value)| Assignment {
                            variable_id: *id,
                            value,
                        })
                        .collect(),
                };
                let mut point = validation(&model.evaluate(&current, tolerances)?);
                point["iteration"] = json!(done);
                point["bound"] = json!(
                    certify(&program, &engine.unscale_dual(&y))
                        .map_err(|e| e.to_string())?
                        .bound
                );
                checkpoints.push(point);
            }
        }
        let x = engine.unscale_primal(&x);
        let y = engine.unscale_dual(&y);
        let distance = |a: &[f64], b: &[f64]| {
            a.iter()
                .zip(b)
                .map(|(a, b)| (a - b).abs())
                .fold(0.0f64, f64::max)
        };
        let mismatch = |a: &[f64], b: &[f64]| {
            a.iter()
                .zip(b)
                .filter(|(a, b)| a.to_bits() != b.to_bits())
                .count()
        };
        output["elapsed_ns"] = json!(start.elapsed().as_nanos());
        output["checkpoints"] = json!(checkpoints);
        output["primal_max_difference"] = json!(distance(&x, &primal));
        output["dual_max_difference"] = json!(distance(&y, dual));
        output["primal_bit_mismatches"] = json!(mismatch(&x, &primal));
        output["dual_bit_mismatches"] = json!(mismatch(&y, dual));
        if mismatch(&x, &primal) != 0 || mismatch(&y, dual) != 0 {
            return Err(format!("fixed host replay differs from GPU: {output}").into());
        }
    }
    println!("{}", serde_json::to_string_pretty(&output)?);
    Ok(())
}
