//! Bounded CPU-only microbenchmark; never a solver or GPU-utilization measurement.
use lp_billion_lowbit::{bounded_certificate, scratch_certificate};
use optimizer_core::ObjectiveSense;
use optimizer_lp::{Certificate, LinearProgram, Range};
use serde_json::json;
use std::{hint::black_box, time::Instant};

fn bits(c: Certificate) -> (u64, u64, u64, usize) {
    (
        c.bound.to_bits(),
        c.unadjusted.to_bits(),
        c.allowance.to_bits(),
        c.repaired,
    )
}

fn main() {
    let mut results = Vec::new();
    for (name, n, m, width) in [
        ("short_columns", 65536usize, 8192usize, 128usize),
        ("balanced", 4096, 4096, 256),
        ("long_columns", 257, 8192, 128),
    ] {
        let construction = Instant::now();
        let mut offsets = vec![0];
        let mut indices = Vec::with_capacity(m * width);
        let mut values = Vec::with_capacity(m * width);
        for row in 0..m {
            let mut columns = (0..width).map(|j| (row * 17 + j) % n).collect::<Vec<_>>();
            columns.sort_unstable();
            for column in columns {
                indices.push(column as u32);
                values.push(((row * 7 + column * 11) % 31) as f64 / 29. - 0.5);
            }
            offsets.push(values.len());
        }
        let program = LinearProgram::from_csr(
            (0..n as u32).collect(),
            vec![
                Range {
                    lower: -2.,
                    upper: 3.
                };
                n
            ],
            vec![
                Range {
                    lower: -1.,
                    upper: 2.
                };
                m
            ],
            offsets,
            indices,
            values,
            &(0..n as u32).collect::<Vec<_>>(),
            &(0..n)
                .map(|j| (j % 7) as f64 / 17. - 0.125)
                .collect::<Vec<_>>(),
            ObjectiveSense::Minimize,
            3.25,
        )
        .unwrap();
        let y = (0..m)
            .map(|i| (i % 19) as f64 / 13. - 0.75)
            .collect::<Vec<_>>();
        let construction_ns = construction.elapsed().as_nanos();
        let mut samples = Vec::new();
        // First pair is cold with respect to this model; subsequent order alternates.
        for repetition in 0..6 {
            let mut times = [0u128; 2];
            let mut certificates = Vec::new();
            for index in if repetition % 2 == 0 { [0, 1] } else { [1, 0] } {
                let start = Instant::now();
                let certificate = if index == 0 {
                    bounded_certificate::certify(black_box(&program), black_box(&y))
                } else {
                    scratch_certificate::certify(black_box(&program), black_box(&y))
                }
                .expect("finite benchmark certificate");
                times[index] = start.elapsed().as_nanos();
                certificates.push(bits(certificate));
            }
            assert_eq!(certificates[0], certificates[1]);
            samples.push(json!({"repetition": repetition, "reference_ns": times[0], "candidate_ns": times[1], "exact": true}));
        }
        results.push(
            json!({"case": name, "rows": m, "columns": n, "nonzeros": m * width,
            "construction_ns": construction_ns, "samples": samples}),
        );
    }
    println!(
        "{}",
        json!({"status": "passed", "rows": results,
        "scope": "CPU certificate microbenchmark; no solver, certification acceptance or GPU utilization speedup claim"})
    );
}
