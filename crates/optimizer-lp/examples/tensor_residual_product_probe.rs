//! CPU product enclosure witnesses for the independent Fraction oracle.
use optimizer_core::{LpSettings, Model};
use optimizer_lp::{Engine, LinearProgram, tensor_residual::*};
fn main() {
    let a = std::env::args().skip(1).collect::<Vec<_>>();
    let bytes = std::fs::read(&a[0]).unwrap();
    let m = Model::from_json(&bytes).unwrap();
    let p = LinearProgram::new(&m).unwrap();
    let e = Engine::new(&p, LpSettings::published(480, 200));
    let op = Operator::new(
        &e,
        Settings::new(Format::Fp64, Policy::Uniform),
        Layout::Int8,
    )
    .unwrap();
    let mut rows = vec![];
    for native in [false, true] {
        let mut promotion = op.initial();
        if native && !promotion.native {
            promotion.promote(&op, &[0]);
        }
        let g = op.generation(promotion).unwrap();
        for t in [false, true] {
            for exponent in [-30, 0, 30] {
                let v=(0..if t{op.rows}else{op.columns}).map(|i|if i%3==0{-1.}else{1.}*(if i%7==0 {2f64.powi(-70)} else {1.+(i%7) as f64/17.})*2f64.powi(exponent)).collect::<Vec<_>>();
                let r = op.product(&g, t, &v).unwrap();
                rows.push(serde_json::json!({"native":native,"transpose":t,"vector":v,"output":r.output,"bounds":r.bounds,"flags":r.flags}));
            }
        }
    }
    println!(
        "{}",
        serde_json::json!({"row_scale":op.row_scale,"column_scale":op.column_scale,"rows":rows})
    );
}
