//! Bitwise control/norm and original-feasibility diagnostics, separate from solves.
use lp_billion_lowbit::{
    Result,
    array_assessment::feasibility,
    array_input::Original,
    control::Fp64Controller,
    engine::Engine,
    fast_device::{Config, Device},
    host,
    operator::{Format, Operator},
    tensor,
};
use optimizer_core::ObjectiveSense;
use optimizer_lp::{LinearProgram, LpSettings, Range, tree_sum};
use serde_json::json;
use std::path::Path;

fn original(m: usize, n: usize, degree: usize) -> Original {
    let mut offsets = vec![0];
    let mut indices = Vec::new();
    let mut values = Vec::new();
    for i in 0..m {
        let mut columns = (0..degree.min(n))
            .map(|j| (i * 17 + j) % n)
            .collect::<Vec<_>>();
        columns.sort_unstable();
        for j in columns {
            indices.push(j as u32);
            values.push(match (i + j) % 13 {
                0 => -0.,
                1 => f64::from_bits(1),
                _ => ((i * 7 + j * 11) % 29) as f64 / 17. - 0.75,
            });
        }
        offsets.push(indices.len());
    }
    let objective_indices = (0..n.min(17) as u32).collect::<Vec<_>>();
    let objective_values = vec![0.125; objective_indices.len()];
    let columns = (0..n)
        .map(|j| Range {
            lower: if j.is_multiple_of(3) {
                f64::NEG_INFINITY
            } else {
                -1.
            },
            upper: if j.is_multiple_of(5) {
                f64::INFINITY
            } else {
                3.
            },
        })
        .collect();
    let rows = (0..m)
        .map(|i| Range {
            lower: if i.is_multiple_of(3) {
                f64::NEG_INFINITY
            } else {
                -2.
            },
            upper: if i.is_multiple_of(5) {
                f64::INFINITY
            } else {
                2.
            },
        })
        .collect();
    let program = LinearProgram::from_csr(
        (0..n as u32).collect(),
        columns,
        rows,
        offsets,
        indices,
        values,
        &objective_indices,
        &objective_values,
        if m.is_multiple_of(2) {
            ObjectiveSense::Maximize
        } else {
            ObjectiveSense::Minimize
        },
        3.25,
    )
    .unwrap();
    Original {
        program,
        row_ids: (0..m as u32).collect(),
        model_id: "control-check".into(),
        objective_indices,
        objective_values,
        offset: 3.25,
        sha256: String::new(),
    }
}
fn run() -> Result<()> {
    let args = std::env::args().collect::<Vec<_>>();
    let image = Path::new(args.get(1).ok_or("tensor image")?);
    let (mut merits, mut fallbacks, mut movements, mut feasibilities, mut errors) = (0, 0, 0, 0, 0);
    for (m, n, degree) in [
        (0, 0, 0),
        (0, 17, 0),
        (17, 0, 0),
        (1, 1, 1),
        (7, 33, 33),
        (33, 65, 65),
        (17, 1023, 1023),
        (5, 1024, 1024),
        (3, 1025, 1025),
        (4097, 129, 5),
        (129, 4097, 7),
        (1, 1_048_577, 1),
    ] {
        let original = original(m, n, degree);
        let settings = LpSettings {
            power_iterations: 0,
            preconditioner: optimizer_lp::PreconditionerSettings {
                ruiz_passes: 0,
                pock_chambolle_alpha: 0.,
            },
            ..LpSettings::published(100, 100)
        };
        let engine = Engine::new(&original.program, settings);
        let op = Operator::borrowed_native(&engine)?;
        let config = Config {
            gpu_control: true,
            gpu_feasibility: true,
            ..Config::default()
        };
        let mut device = Device::new(
            &engine,
            &op,
            None,
            image,
            Format::Native,
            &tensor::Config::default(),
            &config,
        )?;
        for pattern in 0..3 {
            let value = |i: usize| match pattern {
                0 => (i % 31) as f64 / 8. - 1.,
                1 => -0.,
                _ => {
                    if i.is_multiple_of(2) {
                        f64::from_bits(1)
                    } else {
                        -f64::from_bits(1)
                    }
                }
            };
            let x = (0..n).map(value).collect::<Vec<_>>();
            let y = (0..m).map(value).collect::<Vec<_>>();
            let weight = [0.5, 1., 2.][pattern];
            let expected = host::projected_residual(&engine, &x, &y, weight);
            match device.gpu_merit(&x, &y, engine.step(), weight)? {
                Some(actual) => {
                    if actual.to_bits() != expected.to_bits() {
                        return Err(format!(
                            "merit mismatch {m}/{n}/{degree}/{pattern}: {actual:?} != {expected:?}"
                        )
                        .into());
                    }
                    merits += 1;
                }
                None => {
                    if degree <= 1024 {
                        return Err("unexpected control fallback".into());
                    }
                    fallbacks += 1;
                }
            }
            let mut state = Fp64Controller::new(&engine).state().clone();
            state.primal = x;
            state.dual = y;
            state.anchor_primal = (0..n)
                .map(|i| if i.is_multiple_of(2) { 0.25 } else { -0. })
                .collect();
            state.anchor_dual = (0..m)
                .map(|i| if i.is_multiple_of(2) { -0.125 } else { 0. })
                .collect();
            let norm = |x: &[f64], a: &[f64]| {
                tree_sum(
                    &x.iter()
                        .zip(a)
                        .map(|(v, w)| {
                            let d = v - w;
                            d * d
                        })
                        .collect::<Vec<_>>(),
                )
                .sqrt()
            };
            let expected = (
                norm(&state.primal, &state.anchor_primal),
                norm(&state.dual, &state.anchor_dual),
            );
            let actual = device
                .gpu_movements(&state)?
                .ok_or("movement GPU missing")?;
            if (actual.0.to_bits(), actual.1.to_bits())
                != (expected.0.to_bits(), expected.1.to_bits())
            {
                return Err(format!("movement mismatch {m}/{n}/{pattern}").into());
            }
            movements += 1;
        }
        for pattern in 0..5 {
            let x = (0..n)
                .map(|i| match pattern {
                    0 => (i % 31) as f64 / 8. - 1.,
                    1 => -0.,
                    2 => f64::from_bits((i % 17 + 1) as u64),
                    3 => 3. + 4e-9,
                    _ => f64::MAX / 16.,
                })
                .collect::<Vec<_>>();
            for t in [0., 1e-9, 1e-3] {
                let expected = feasibility(&original, &x, t, false);
                let actual = device.gpu_feasible(&x, t);
                match (expected, actual) {
                    (Ok((a, _)), Ok(Some(b))) if a == b => {}
                    (Err(_), Err(_)) => {}
                    pair => {
                        return Err(format!(
                            "feasibility mismatch {m}/{n}/{pattern}/{t}: {pair:?}"
                        )
                        .into());
                    }
                }
                feasibilities += 1;
            }
        }
        for t in [-1., f64::NAN, f64::INFINITY] {
            if device.gpu_feasible(&vec![0.; n], t).is_ok() {
                return Err("invalid tolerance accepted".into());
            }
            errors += 1;
        }
        if n > 0 {
            for v in [f64::NAN, f64::INFINITY, f64::NEG_INFINITY] {
                let mut x = vec![0.; n];
                x[n - 1] = v;
                if device.gpu_feasible(&x, 1e-9).is_ok() {
                    return Err("invalid iterate accepted".into());
                }
                errors += 1;
            }
        }
        if device.gpu_feasible(&vec![0.; n + 1], 1e-9).is_ok() {
            return Err("wrong dimensions accepted".into());
        }
        errors += 1;
        println!(
            "{}",
            json!({"m":m,"n":n,"degree":degree,"status":"passed","metrics":device.support_metrics()})
        );
    }
    println!(
        "{}",
        json!({"status":"passed","merit_comparisons":merits,"host_fallbacks":fallbacks,"movement_comparisons":movements,"feasibility_comparisons":feasibilities,"invalid_inputs_rejected":errors})
    );
    Ok(())
}
fn main() {
    if let Err(error) = run() {
        eprintln!("{error}");
        std::process::exit(1)
    }
}
