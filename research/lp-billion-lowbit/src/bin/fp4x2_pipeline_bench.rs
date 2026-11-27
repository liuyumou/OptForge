//! Bounded CPU-only microbenchmark; never a solver or GPU-utilization measurement.
#[allow(dead_code)]
#[path = "../../../../crates/optimizer-lp/src/outward.rs"]
mod outward;
#[path = "../../diagnostics/fp4x2_workspace_v1.rs"]
mod previous;
pub use optimizer_lp::tree_sum;
#[allow(dead_code)]
#[path = "../../../../crates/optimizer-lp/src/reduce.rs"]
mod reduce;
use lp_billion_lowbit::bounded_certificate;
// Both compared implementations compile in the same crate and optimization
// context; compare the solver's exact source, not a hand-translated algorithm.
#[path = "../certificate_workspace.rs"]
mod candidate;
#[path = "../certificate_staged.rs"]
mod certificate_staged;
#[path = "../work_partition.rs"]
mod work_partition;
mod scratch_certificate {
    pub(crate) use super::previous::{endpoint, sum_in_place};
}
use candidate::Workspace;
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
    for seed in [2026112731usize, 2026112732, 2026112733] {
        for (name, n, m, width) in [
            ("short_columns", 65536usize, 8192usize, 128usize),
            ("balanced", 4096, 4096, 256),
            ("long_columns", 257, 8192, 128),
            ("skew_columns", 8192, 8192, 128),
        ] {
            let construction = Instant::now();
            let mut offsets = vec![0];
            let mut indices = Vec::with_capacity(m * width);
            let mut values = Vec::with_capacity(m * width);
            for row in 0..m {
                let domain = if name == "skew_columns" && row % 8 != 0 {
                    256
                } else {
                    n
                };
                let mut columns = (0..width)
                    .map(|j| (row * 17 + j + seed % 127) % domain)
                    .collect::<Vec<_>>();
                columns.sort_unstable();
                for column in columns {
                    indices.push(column as u32);
                    values.push(((row * 7 + column * 11 + seed % 29) % 31) as f64 / 29. - 0.5);
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
            let mut previous4 = previous::Workspace::new(4);
            let mut workspace4 = Workspace::new(4);
            let mut workspace3 = Workspace::new(3);
            // First pair is cold with respect to this model; subsequent order alternates.
            for repetition in 0..6 {
                let y: Vec<_> = y.iter().map(|v| v + repetition as f64 / 128.).collect();
                let mut times = [0u128; 4];
                let mut certificates = Vec::new();
                for offset in 0..4 {
                    let index = (offset + repetition) % 4;
                    let start = Instant::now();
                    let certificate = if index == 0 {
                        bounded_certificate::certify(black_box(&program), black_box(&y))
                    } else if index == 1 {
                        previous4.certify(black_box(&program), black_box(&y))
                    } else if index == 2 {
                        workspace4.certify(black_box(&program), black_box(&y))
                    } else {
                        workspace3.certify(black_box(&program), black_box(&y))
                    }
                    .expect("finite benchmark certificate");
                    times[index] = start.elapsed().as_nanos();
                    certificates.push(bits(certificate));
                }
                assert!(certificates.iter().all(|c| c == &certificates[0]));
                samples.push(json!({"repetition": repetition, "bounded_ns": times[0], "previous4_ns": times[1], "workspace4_ns":times[2],"workspace3_ns":times[3], "exact": true,"retained_bytes":workspace4.retained_bytes(),"previous_retained_bytes":previous4.retained_bytes()}));
            }
            results.push(
                json!({"case": name, "seed":seed, "rows": m, "columns": n, "nonzeros": m * width,
            "construction_ns": construction_ns, "weighted_columns":work_partition::weighted_columns(program.column_major().arrays().0,4), "samples": samples}),
            );
        }
    }
    println!(
        "{}",
        json!({"status": "passed", "rows": results,
        "scope": "CPU certificate microbenchmark; no solver, certification acceptance or GPU utilization speedup claim"})
    );
}
