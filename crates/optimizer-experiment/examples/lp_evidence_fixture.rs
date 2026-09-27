//! CPU-only synthetic codec fixture; never a solver result or performance sample.
use optimizer_core::{
    Assignment, Candidate, LpDiagnostics, LpSettings, Model, SolveOptions, SolveRecord, Termination,
};
use optimizer_experiment::lp::LpEndpoint;
use optimizer_lp::{LinearProgram, certify, certify::assess_gap};
use std::io::Write;

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args: Vec<_> = std::env::args_os().skip(1).collect();
    if args.len() != 3 {
        return Err("expected model, solve configuration and new output path".into());
    }
    let bytes = std::fs::read(&args[0])?;
    let model = Model::from_json(&bytes)?;
    let options: SolveOptions = serde_json::from_slice(&std::fs::read(&args[1])?)?;
    options.validate()?;
    let program = LinearProgram::new(&model)?;
    let candidate = Candidate {
        schema_version: 1,
        model_id: model.document().model_id.clone(),
        values: program
            .variable_ids()
            .iter()
            .map(|id| Assignment {
                variable_id: *id,
                value: 0.0,
            })
            .collect(),
    };
    let validation = model.evaluate(&candidate, options.tolerances)?;
    let dual = vec![0.0; program.row_count()];
    let bound = certify(&program, &dual).ok().map(|c| c.bound);
    let gap = if validation.feasible {
        bound
            .and_then(|b| {
                assess_gap(
                    &program,
                    &vec![0.0; program.variable_ids().len()],
                    b,
                    options.tolerances,
                )
            })
            .map(|g| g.upper)
    } else {
        None
    };
    let record = SolveRecord {
        schema_version: 2,
        model_id: model.document().model_id.clone(),
        backend: "host-lp".into(),
        backend_version: "synthetic-codec-fixture-no-solve".into(),
        termination: Termination::IterationLimit,
        native_status: None,
        objective: Some(validation.objective),
        best_bound: bound,
        gap,
        candidate: Some(candidate),
        validation: Some(validation),
        warnings: vec!["Synthetic canonical-zero candidate/dual; no solve was executed".into()],
        elapsed_ms: 0,
        options,
        lp_settings: Some(LpSettings::published(50000, 200)),
        lp_execution: None,
        lp_precision: None,
        lp_adaptive: None,
    };
    let mut diagnostics = LpDiagnostics::new(true, false);
    diagnostics.capture(&dual, 0);
    diagnostics.iterations = Some(0);
    diagnostics.restarts = Some(0);
    let endpoint = LpEndpoint::new(&bytes, "host-lp".into(), record, diagnostics, None)?;
    endpoint.verify(&bytes)?;
    let mut output = std::fs::OpenOptions::new()
        .create_new(true)
        .write(true)
        .open(&args[2])?;
    output.write_all(&serde_json::to_vec_pretty(&endpoint)?)?;
    output.sync_all()?;
    println!("{}", serde_json::to_string(&endpoint.assessment)?);
    Ok(())
}
