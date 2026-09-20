//! Isolated GPUP-5B research solve/verification; never a runtime backend.
//!
//! Actions: `solve`/`verify` handle one fresh research-v1/v2 solve;
//! `batch`/`verify-batch` handle one SPEC-0014 repeated-solve batch (modes
//! intguard-fp64 and fused-fp64 only), writing one research-v2 record per
//! solve plus `batch.json` into the evidence directory.
use optimizer_experiment::lp_research::{
    Evidence, Request, ResearchBatchEvidence, ResearchBatchRequest, solve, solve_batch,
};
use std::io::Write;

const USAGE: &str = "usage: lp_precision_research solve|verify MODEL REQUEST EVIDENCE | batch|verify-batch MODEL BATCH-REQUEST EVIDENCE-DIR";

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args = std::env::args().skip(1).collect::<Vec<_>>();
    let Some(action) = args.first() else {
        return Err(USAGE.into());
    };
    match action.as_str() {
        "solve" | "verify" => {
            if args.len() != 4 {
                return Err(USAGE.into());
            }
            let bytes = std::fs::read(&args[1])?;
            let request = Request::from_json(&std::fs::read(&args[2])?)?;
            if action == "solve" {
                let result = solve(&bytes, request, &optimizer_core::CancellationToken::new())?;
                let mut file = std::fs::OpenOptions::new()
                    .create_new(true)
                    .write(true)
                    .open(&args[3])?;
                file.write_all(&serde_json::to_vec_pretty(&result)?)?;
                file.sync_all()?;
                println!("{}", serde_json::to_string(&result.assessment)?);
            } else {
                Evidence::from_json(&std::fs::read(&args[3])?)?.verify(&bytes, &request)?;
                println!("verified");
            }
        }
        "batch" => {
            if args.len() != 4 {
                return Err(USAGE.into());
            }
            let bytes = std::fs::read(&args[1])?;
            let request = ResearchBatchRequest::from_json(&std::fs::read(&args[2])?)?;
            let dir = std::path::Path::new(&args[3]);
            // The directory is created if needed; every file inside it —
            // solve-NNN.json from solve_batch and batch.json here — is
            // create_new + rename and never replaces an existing record
            // (SPEC-0014 requirement 25).
            std::fs::create_dir_all(dir)?;
            let evidence = solve_batch(
                &bytes,
                &request,
                dir,
                &optimizer_core::CancellationToken::new(),
            )?;
            optimizer_experiment::lp_batch::write_evidence_file(
                &dir.join("batch.json"),
                &serde_json::to_vec_pretty(&evidence)?,
            )?;
            let mut statuses = std::collections::BTreeMap::new();
            for solve in &evidence.solves {
                *statuses.entry(solve.status.clone()).or_insert(0_u32) += 1;
            }
            println!(
                "{}",
                serde_json::to_string(&serde_json::json!({
                    "solves": evidence.solves.len(),
                    "statuses": statuses,
                    "payload_sha256": evidence.payload_sha256,
                }))?
            );
        }
        "verify-batch" => {
            if args.len() != 4 {
                return Err(USAGE.into());
            }
            let bytes = std::fs::read(&args[1])?;
            let request = ResearchBatchRequest::from_json(&std::fs::read(&args[2])?)?;
            let dir = std::path::Path::new(&args[3]);
            let evidence =
                ResearchBatchEvidence::from_json(&std::fs::read(dir.join("batch.json"))?)?;
            if evidence.request != request {
                return Err("batch request differs".into());
            }
            evidence.verify(&bytes, dir)?;
            println!("verified");
        }
        _ => return Err(USAGE.into()),
    }
    Ok(())
}
