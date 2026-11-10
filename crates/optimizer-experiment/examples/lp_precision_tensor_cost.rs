//! Isolated strict GPUP-8 solve/verify/replay and CPU admission.
use optimizer_experiment::lp_tensor_cost::{Evidence, Request, execute, replay_matches};
fn read(p: &str, n: u64) -> Result<Vec<u8>, Box<dyn std::error::Error>> {
    if std::fs::metadata(p)?.len() > n {
        return Err("quant byte limit".into());
    }
    let b = std::fs::read(p)?;
    if b.len() as u64 > n {
        return Err("quant byte limit".into());
    }
    Ok(b)
}
fn main() -> Result<(), Box<dyn std::error::Error>> {
    let a = std::env::args().skip(1).collect::<Vec<_>>();
    if a.len() != 4 || !["solve", "verify", "replay", "trace-cpu"].contains(&a[0].as_str()) {
        return Err(
            "usage: lp_precision_tensor_cost solve|verify|replay|trace-cpu MODEL REQUEST EVIDENCE"
                .into(),
        );
    }
    let bytes = read(&a[1], 128 << 20)?;
    let request = Request::from_json(&read(&a[2], 1 << 20)?)?;
    if a[0] == "solve" || a[0] == "trace-cpu" {
        let e = execute(
            &bytes,
            request,
            a[0] == "trace-cpu",
            &optimizer_core::CancellationToken::new(),
        )?;
        e.write(std::path::Path::new(&a[3]))?;
        println!("{}", serde_json::to_string(&e.assessment)?);
    } else {
        let e = Evidence::from_json(&read(&a[3], 32 << 20)?)?;
        e.verify(&bytes, &request)?;
        if a[0] == "replay" {
            if e.executor != "gpu" {
                return Err("GPU replay requires GPU evidence".into());
            }
            let r = execute(
                &bytes,
                request,
                false,
                &optimizer_core::CancellationToken::new(),
            )?;
            r.write(std::path::Path::new(&(a[3].clone() + ".replay.json")))?;
            if !replay_matches(&e, &r) {
                return Err("quant replay differs".into());
            }
        }
        println!("verified");
    }
    Ok(())
}
