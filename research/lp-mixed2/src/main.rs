//! JSON-lines differential-test interface; never issues a certificate.
use lp_mixed2::{Csr, Prepared};
use serde::Deserialize;
use std::io::{self, BufRead, Write};
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Request {
    matrix: Csr,
    x: Vec<f64>,
    transpose: bool,
}
fn main() -> Result<(), Box<dyn std::error::Error>> {
    let mut out = io::BufWriter::new(io::stdout().lock());
    for line in io::stdin().lock().lines() {
        let request: Request = serde_json::from_str(&line?)?;
        let result =
            Prepared::new(request.matrix).and_then(|p| p.product(&request.x, request.transpose));
        let value = match result {
            Ok(p) => serde_json::json!({"status":"enclosed","product":p}),
            Err(e) => serde_json::json!({"status":"refused","reason":format!("{e:?}")}),
        };
        serde_json::to_writer(&mut out, &value)?;
        writeln!(out)?;
    }
    out.flush()?;
    Ok(())
}
