//! Study-only ADR-0037 fresh solve, independent verification and same-device replay.
use optimizer_experiment::lp_refine::{Evidence, Request, solve};
use std::io::Write;
fn read_bounded(path: &str, limit: u64) -> Result<Vec<u8>, Box<dyn std::error::Error>> {
    if std::fs::metadata(path)?.len() > limit {
        return Err("refinement input byte limit".into());
    }
    let bytes = std::fs::read(path)?;
    if bytes.len() as u64 > limit {
        return Err("refinement input byte limit".into());
    }
    Ok(bytes)
}
fn main() -> Result<(), Box<dyn std::error::Error>> {
    let a = std::env::args().skip(1).collect::<Vec<_>>();
    if a.len() != 4 || !["solve", "verify", "replay"].contains(&a[0].as_str()) {
        return Err("usage: lp_precision_refine solve|verify|replay MODEL REQUEST EVIDENCE".into());
    }
    let bytes = read_bounded(&a[1], 128 << 20)?;
    let request = Request::from_json(&read_bounded(&a[2], 1 << 20)?)?;
    if a[0] == "solve" {
        let result = solve(&bytes, request, &optimizer_core::CancellationToken::new())?;
        let mut file = std::fs::OpenOptions::new()
            .create_new(true)
            .write(true)
            .open(&a[3])?;
        file.write_all(&serde_json::to_vec_pretty(&result)?)?;
        file.sync_all()?;
        println!("{}", serde_json::to_string(&result.assessment)?);
    } else {
        let evidence = Evidence::from_json(&read_bounded(&a[3], 32 << 20)?)?;
        evidence.verify(&bytes, &request)?;
        if a[0] == "replay" {
            let again = solve(&bytes, request, &optimizer_core::CancellationToken::new())?;
            let mut replay = std::fs::OpenOptions::new()
                .create_new(true)
                .write(true)
                .open(format!("{}.replay.json", a[3]))?;
            replay.write_all(&serde_json::to_vec_pretty(&again)?)?;
            replay.sync_all()?;
            if serde_json::to_vec(&evidence.witness.outcome)?
                != serde_json::to_vec(&again.witness.outcome)?
                || serde_json::to_vec(&evidence.assessment)?
                    != serde_json::to_vec(&again.assessment)?
            {
                return Err("same-device refinement replay differs".into());
            }
        }
        println!("verified");
    }
    Ok(())
}
