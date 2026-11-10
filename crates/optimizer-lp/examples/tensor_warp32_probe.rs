//! CPU-only access to the actual unchanged warp32 reference for ADR-0045.
#[cfg(feature = "precision-research")]
fn main() {
    use optimizer_core::LpWidth;
    use serde::Deserialize;
    use std::io::{self, BufRead};
    #[derive(Deserialize)]
    struct Request {
        values: Vec<u64>,
        indices: Vec<u32>,
        input: Vec<u64>,
    }
    for line in io::stdin().lock().lines() {
        let request: Request = serde_json::from_str(&line.unwrap()).unwrap();
        let values = request
            .values
            .into_iter()
            .map(f64::from_bits)
            .collect::<Vec<_>>();
        let input = request
            .input
            .into_iter()
            .map(f64::from_bits)
            .collect::<Vec<_>>();
        let result = optimizer_lp::precision::product(
            &values,
            &request.indices,
            &input,
            LpWidth::F64,
            LpWidth::F64,
        );
        let output = match result {
            Ok(value) => serde_json::json!({"bits": value.to_bits()}),
            Err(error) => serde_json::json!({"error": error}),
        };
        println!("{output}");
    }
}

#[cfg(not(feature = "precision-research"))]
fn main() {}
