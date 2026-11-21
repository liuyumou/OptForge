//! Independent CPU/GPU canonical packing comparison, including invalid inputs.
use lp_billion_lowbit::{
    Result, gpu_packing,
    operator::{Format, Operator, Orientation},
    tensor::{Config, Packed},
};
use serde_json::json;
use std::{borrow::Cow, path::Path};
fn operator(m: usize, n: usize, entries: Vec<(usize, usize, f64)>) -> Operator<'static> {
    let mut rows = vec![Vec::new(); m];
    let mut cols = vec![Vec::new(); n];
    for (i, j, v) in entries {
        rows[i].push((j as u32, v));
        cols[j].push((i as u32, v));
    }
    let compress = |lines: Vec<Vec<(u32, f64)>>| {
        let mut offsets = vec![0];
        let mut indices = Vec::new();
        let mut values = Vec::new();
        for mut line in lines {
            line.sort_by_key(|v| v.0);
            for (j, v) in line {
                indices.push(j);
                values.push(v);
            }
            offsets.push(indices.len() as u32);
        }
        Orientation {
            offsets,
            indices: Cow::Owned(indices),
            original: Cow::Owned(values),
            ids: Vec::new(),
        }
    };
    Operator {
        prepared: Format::Native,
        rows: compress(rows),
        columns: compress(cols),
        codes: Vec::new(),
        exponents: Vec::new(),
        fp32: Vec::new(),
    }
}
fn equal(a: Option<Packed>, b: Option<Packed>) -> Result<()> {
    match (a, b) {
        (None, None) => Ok(()),
        (Some(a), Some(b)) => {
            for (x, y) in [(&a.rows, &b.rows), (&a.columns, &b.columns)] {
                if x.residual
                    .original
                    .iter()
                    .zip(y.residual.original.iter())
                    .any(|(x, y)| x.to_bits() != y.to_bits())
                {
                    return Err("residual bits differ".into());
                }
            }
            if serde_json::to_value(a)? != serde_json::to_value(b)? {
                return Err("canonical packing differs".into());
            }
            Ok(())
        }
        _ => Err("packing eligibility differs".into()),
    }
}
fn run() -> Result<()> {
    let args: Vec<_> = std::env::args().collect();
    let image = Path::new(args.get(1).ok_or("packing image")?);
    let mut count = 0;
    for (m, n, sparse) in [
        (1usize, 1usize, false),
        (17, 65, false),
        (49, 67, false),
        (65, 33, false),
        (129, 129, true),
        (0, 17, true),
        (3, 0, true),
    ] {
        for k in 1..=4 {
            for compact in [false, true] {
                let entries = (0..m)
                    .flat_map(|i| {
                        (0..n).filter_map(move |j| {
                            if sparse && !(i * 7 + j * 11).is_multiple_of(53) {
                                None
                            } else {
                                Some((i, j, ((i * 13 + j * 3) % 37) as f64 / 7. - 2.))
                            }
                        })
                    })
                    .collect();
                let op = operator(m, n, entries);
                let c = Config {
                    components: k,
                    compact_fragments: compact,
                    min_tile_nnz: if sparse { 128 } else { 1 },
                    ..Config::default()
                };
                let cpu = lp_billion_lowbit::tensor_prepare::prepare(&op, &c)?;
                let (gpu, metrics) = gpu_packing::prepare(&op, &c, image)?;
                equal(cpu, gpu)?;
                count += 1;
                println!(
                    "{}",
                    json!({"case":count,"m":m,"n":n,"components":k,"compact":compact,"exact":true,"metrics":metrics})
                );
            }
        }
    }
    // Every normal-code midpoint, sign, subnormal, and exponent-clamp boundary.
    for power in [-48, -40, 0, 37] {
        let mut values = Vec::new();
        for x in [0f64, 0.5, 1.25, 1.75, 2.5, 3.5, 5., 6.] {
            for v in [x.next_down(), x, x.next_up()] {
                values.extend([v * 2f64.powi(power), -v * 2f64.powi(power)]);
            }
        }
        for k in 1..=4 {
            let op = operator(
                32,
                32,
                (0..1024)
                    .map(|i| (i / 32, i % 32, values[i % values.len()]))
                    .collect(),
            );
            let c = Config {
                components: k,
                ..Config::default()
            };
            equal(
                lp_billion_lowbit::tensor_prepare::prepare(&op, &c)?,
                gpu_packing::prepare(&op, &c, image)?.0,
            )?;
            count += 1;
            println!(
                "{}",
                json!({"case":count,"power":power,"components":k,"exact":true})
            );
        }
    }
    // Exercise the ilogb/log2 exponent equivalence immediately around powers
    // of two and six, including the smallest subnormal and the -48 clamp.
    let mut boundary_values = Vec::new();
    for power in [-1074, -1022, -100].into_iter().chain(-49..=40) {
        let unit = if power == -1074 {
            f64::from_bits(1)
        } else {
            f64::from_bits(((power + 1023) as u64) << 52)
        };
        for maximum in [unit, 6. * unit] {
            for value in [maximum.next_down(), maximum, maximum.next_up()] {
                if value >= 0. && value <= 2f64.powi(40) {
                    boundary_values.push(value);
                }
            }
        }
    }
    let dim = boundary_values.len() * 32;
    for k in 1..=4 {
        for compact in [false, true] {
            let entries = boundary_values
                .iter()
                .enumerate()
                .flat_map(|(i, &v)| [(i * 32, i * 32, v), (i * 32 + 1, i * 32 + 1, -v)])
                .collect();
            let op = operator(dim, dim, entries);
            let c = Config {
                components: k,
                compact_fragments: compact,
                min_tile_nnz: 1,
                ..Config::default()
            };
            equal(
                lp_billion_lowbit::tensor_prepare::prepare(&op, &c)?,
                gpu_packing::prepare(&op, &c, image)?.0,
            )?;
            count += 1;
            println!(
                "{}",
                json!({"case":count,"exponent_boundary_tiles":boundary_values.len(),"components":k,"compact":compact,"exact":true})
            );
        }
    }
    let op = operator(
        32,
        4097 * 32,
        (0..4097).map(|i| (i % 32, i * 32, 1.)).collect(),
    );
    let c = Config {
        min_tile_nnz: 1,
        ..Config::default()
    };
    let (after, metrics) = gpu_packing::prepare(&op, &c, image)?;
    if metrics["backend"] != "host_hash_overflow" {
        return Err("hash-overflow fallback missing".into());
    }
    equal(lp_billion_lowbit::tensor_prepare::prepare(&op, &c)?, after)?;
    count += 1;
    println!("{}", json!({"case":count,"exact":true,"metrics":metrics}));
    let mut rejected = 0;
    for fault in 0..6 {
        let mut op = operator(32, 32, vec![(0, 0, 1.), (0, 1, -0.), (1, 0, 2.)]);
        match fault {
            0 => op.columns.original.to_mut()[0] = 3.,
            1 => op.rows.indices.to_mut()[0] = 32,
            2 => op.rows.original.to_mut()[0] = f64::NAN,
            3 => op.rows.offsets[1] = 4,
            4 => op.columns.original.to_mut()[2] = 0.,
            _ => op.rows.indices.to_mut()[1] = 0,
        }
        if gpu_packing::prepare(&op, &Config::default(), image).is_ok() {
            return Err("invalid packing accepted".into());
        }
        rejected += 1;
    }
    println!(
        "{}",
        json!({"status":"passed","bitwise_comparisons":count,"invalid_inputs_rejected":rejected})
    );
    Ok(())
}
fn main() {
    if let Err(e) = run() {
        eprintln!("{e}");
        std::process::exit(2);
    }
}
