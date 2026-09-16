//! Isolated GPUP-5B research solve/verification; never a runtime backend.
use optimizer_experiment::lp_research::{Evidence, Request, solve};
use std::io::Write;
fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args = std::env::args().skip(1).collect::<Vec<_>>();
    if args.len() != 4 {
        return Err("usage: lp_precision_research solve|verify MODEL REQUEST EVIDENCE".into());
    }
    let bytes = std::fs::read(&args[1])?;
    let request = Request::from_json(&std::fs::read(&args[2])?)?;
    match args[0].as_str() {
        "solve" => {
            let result = solve(&bytes, request, &optimizer_core::CancellationToken::new())?;
            let mut file = std::fs::OpenOptions::new()
                .create_new(true)
                .write(true)
                .open(&args[3])?;
            file.write_all(&serde_json::to_vec_pretty(&result)?)?;
            file.sync_all()?;
            println!("{}", serde_json::to_string(&result.assessment)?);
        }
        "verify" => {
            Evidence::from_json(&std::fs::read(&args[3])?)?.verify(&bytes, &request)?;
            println!("verified");
        }
        _ => return Err("unknown research action".into()),
    }
    Ok(())
}
