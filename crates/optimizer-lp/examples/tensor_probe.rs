//! CPU-only exact-rational proof adapter for ADR-0042.
use std::io::{self, BufRead};
fn main() {
    for line in io::stdin().lock().lines() {
        let v: serde_json::Value = serde_json::from_str(&line.unwrap()).unwrap();
        let out = if let Some(x) = v.get("bits") {
            let bits = u64::from_str_radix(x.as_str().unwrap(), 16).unwrap();
            let e = v["exponent"].as_i64().unwrap() as i32;
            match optimizer_lp::tensor::encode(f64::from_bits(bits), e) {
                Ok(q) => serde_json::json!({"q":q.to_string()}),
                Err(x) => serde_json::json!({"error":x}),
            }
        } else {
            let n = v["integer"].as_str().unwrap().parse::<i128>().unwrap();
            let e = v["base"].as_i64().unwrap() as i32;
            match optimizer_lp::tensor::round_dot(n, e) {
                Ok((x, b)) => serde_json::json!({"bits":format!("{:016x}",x.to_bits()),"bound":b}),
                Err(x) => serde_json::json!({"error":x}),
            }
        };
        println!("{}", out);
    }
}
