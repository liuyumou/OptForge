//! Retain the first exact lost-nonzero witness from a frozen development trajectory.
use optimizer_core::{LpSettings, Model};
use optimizer_lp::{Engine, LinearProgram, control::Fp64Controller, tensor::*};
fn witnesses(v: &[f64]) -> Vec<serde_json::Value> {
    let mut rows = vec![];
    for (block, values) in v.chunks(32).enumerate() {
        let exponent = block_exponent(values.iter().copied()).unwrap();
        for (i, &x) in values.iter().enumerate() {
            if encode(x, exponent).is_err() {
                rows.push(serde_json::json!({"index":block*32+i,"bits":format!("{:016x}",x.to_bits()),"value":x,"block_exponent":exponent}));
            }
        }
    }
    rows
}
fn main() {
    let arg = std::env::args().nth(1).unwrap();
    let m = Model::from_json(&std::fs::read(arg).unwrap()).unwrap();
    let p = LinearProgram::new(&m).unwrap();
    let mut e = Engine::new(&p, LpSettings::published(480, 200));
    let op = Operator::new(
        &e,
        Settings::new(Format::Fp64, Policy::Uniform),
        Layout::Int8,
    )
    .unwrap();
    e.restrict_step(op.step).unwrap();
    let controller = Fp64Controller::new(&e);
    let initial = controller.state();
    let g = op.generation(op.initial()).unwrap();
    let w = HostOracle.window(&e, &op, &g, initial, 32).unwrap();
    let mut pre = initial.clone();
    pre.primal = w.primal;
    pre.dual = w.dual;
    pre.iterations += w.started - 1;
    pre.since_restart += w.started - 1;
    let mut rows = witnesses(&pre.dual);
    let orientation = if rows.is_empty() {
        let aty = op.product(&g, true, &pre.dual).unwrap();
        let (lo, hi) = e.scaled_column_bounds();
        let step = e.step() / pre.weight;
        let bar = (0..pre.primal.len())
            .map(|j| {
                let next = (pre.primal[j] - step * (e.scaled_objective()[j] - aty.output[j]))
                    .max(lo[j])
                    .min(hi[j]);
                2. * next - pre.primal[j]
            })
            .collect::<Vec<_>>();
        rows = witnesses(&bar);
        "primal_extrapolation"
    } else {
        "dual"
    };
    println!(
        "{}",
        serde_json::json!({"started":w.started,"failure":w.failure,"orientation":orientation,"lost_nonzeros":rows})
    );
}
