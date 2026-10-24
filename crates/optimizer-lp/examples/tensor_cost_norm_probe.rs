//! Independent Fraction adapter for ADR-0044 interval Gram bounds.
use optimizer_lp::tensor_cost;
use std::io::{self, BufRead};
fn main() {
    for line in io::stdin().lock().lines() {
        let bits: Vec<String> = serde_json::from_str(&line.unwrap()).unwrap();
        let block = bits
            .iter()
            .map(|s| f64::from_bits(u64::from_str_radix(s, 16).unwrap()))
            .collect::<Vec<_>>();
        let norm = tensor_cost::norm_block(&block);
        println!(
            "{}",
            serde_json::json!({"norm_bits":norm.map(|v|format!("{:016x}",v.to_bits()))})
        );
    }
}
