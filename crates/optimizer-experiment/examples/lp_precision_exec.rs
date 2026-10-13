//! Study-only ADR-0035 fresh solve, independent verification and same-device replay.
use optimizer_experiment::lp_exec::{Evidence, Request, solve};
use std::io::Write;
fn main() -> Result<(), Box<dyn std::error::Error>> {
    let a = std::env::args().skip(1).collect::<Vec<_>>();
    if a.len() != 4 || !["solve", "verify", "replay"].contains(&a[0].as_str()) {
        return Err("usage: lp_precision_exec solve|verify|replay MODEL REQUEST EVIDENCE".into());
    }
    let bytes = std::fs::read(&a[1])?;
    let request = Request::from_json(&std::fs::read(&a[2])?)?;
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
        let evidence = Evidence::from_json(&std::fs::read(&a[3])?)?;
        evidence.verify(&bytes, &request)?;
        if a[0] == "replay" {
            let again = solve(&bytes, request, &optimizer_core::CancellationToken::new())?;
            let mut replay = std::fs::OpenOptions::new()
                .create_new(true)
                .write(true)
                .open(format!("{}.replay.json", a[3]))?;
            replay.write_all(&serde_json::to_vec_pretty(&again)?)?;
            replay.sync_all()?;
            let (x, y) = (&evidence.witness, &again.witness);
            let bits = |v: &Option<Vec<f64>>| {
                v.as_ref()
                    .map(|v| v.iter().map(|x| x.to_bits()).collect::<Vec<_>>())
            };
            if bits(&x.primal) != bits(&y.primal)
                || bits(&x.dual) != bits(&y.dual)
                || x.status != y.status
                || x.failure != y.failure
                || x.proposed_steps != y.proposed_steps
                || x.committed_steps != y.committed_steps
                || x.rounding_flags != y.rounding_flags
                || evidence.assessment != again.assessment
            {
                return Err("same-device replay differs".into());
            }
        }
        println!("verified");
    }
    Ok(())
}
