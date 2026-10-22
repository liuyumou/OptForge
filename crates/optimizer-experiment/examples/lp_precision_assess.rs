//! ADR-0039 isolated assessment study and CPU-only trace verification.
use optimizer_experiment::lp_assess::{Evidence, Request, execute};
use std::path::Path;
fn bounded(path: &str, limit: u64) -> Result<Vec<u8>, Box<dyn std::error::Error>> {
    if std::fs::metadata(path)?.len() > limit {
        return Err("assessment input byte limit".into());
    }
    let bytes = std::fs::read(path)?;
    if bytes.len() as u64 > limit {
        return Err("assessment input byte limit".into());
    }
    Ok(bytes)
}
fn main() -> Result<(), Box<dyn std::error::Error>> {
    let a = std::env::args().skip(1).collect::<Vec<_>>();
    if a.len() != 4
        || !["solve", "verify", "replay", "trace-cpu", "replay-trace"].contains(&a[0].as_str())
    {
        return Err("usage: lp_precision_assess solve|verify|replay|trace-cpu|replay-trace MODEL REQUEST EVIDENCE".into());
    }
    let bytes = bounded(&a[1], 128 << 20)?;
    let request = Request::from_json(&bounded(&a[2], 1 << 20)?)?;
    let path = Path::new(&a[3]);
    let directory = path.parent().unwrap_or_else(|| Path::new("."));
    if a[0] == "solve" || a[0] == "trace-cpu" {
        let evidence = execute(
            &bytes,
            request,
            a[0] == "trace-cpu",
            &optimizer_core::CancellationToken::new(),
        )?
        .write(path)?;
        println!("{}", serde_json::to_string(&evidence.assessment)?);
    } else {
        let evidence = Evidence::from_json(&bounded(&a[3], 32 << 20)?)?;
        evidence.verify(&bytes, &request, directory)?;
        if a[0] == "replay" {
            if evidence.witness.executor != "gpu" {
                return Err("device replay requires GPU evidence".into());
            }
            let replay = execute(
                &bytes,
                request.clone(),
                false,
                &optimizer_core::CancellationToken::new(),
            )?
            .write(&path.with_file_name(format!(
                "{}.replay.json",
                path.file_name().unwrap().to_str().unwrap()
            )))?;
            if !optimizer_experiment::lp_assess::replay_matches(&evidence, &replay, directory)? {
                return Err("assessment same-device replay differs".into());
            }
        }
        if a[0] == "replay-trace" {
            let model = optimizer_core::Model::from_json(&bytes)?;
            let p = optimizer_lp::LinearProgram::new(&model)?;
            let rows = evidence
                .read_frames(directory)?
                .iter()
                .map(|f| {
                    optimizer_experiment::lp_assess::assessment(
                        &model,
                        &p,
                        Some(&f.point),
                        &request.options,
                    )
                })
                .collect::<Result<Vec<_>, _>>()?;
            println!("{}", serde_json::to_string(&rows)?);
        } else {
            println!("verified");
        }
    }
    Ok(())
}
