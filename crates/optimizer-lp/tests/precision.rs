//! Independent edge cases for represented arithmetic and conservative step admission.
use optimizer_core::{LpPrecisionSettings, LpSettings, LpWidth, Model};
use optimizer_lp::{
    LinearProgram,
    control::Fp64Controller,
    pdhg::Engine,
    precision::{PrecisionOperator, correction, narrow, product},
};
fn settings() -> LpPrecisionSettings {
    LpPrecisionSettings::from_json(include_bytes!(
        "../../../examples/lp-accumulation-fp32-v1.json"
    ))
    .unwrap()
}
#[test]
fn nearest_even_subnormal_and_overflow_boundaries() {
    assert_eq!(narrow(1.0 + 2_f64.powi(-24)).unwrap(), 1.0);
    assert_eq!(
        narrow(1.0 + 3.0 * 2_f64.powi(-24)).unwrap(),
        1.0 + 2_f64.powi(-22)
    );
    assert_eq!(narrow(2_f64.powi(-149)).unwrap(), 2_f64.powi(-149));
    assert!(narrow(2_f64.powi(-150)).is_err());
    assert!(narrow(f64::MAX).is_err());
    assert!(narrow(f64::NAN).is_err());
    assert_eq!(narrow(-0.0).unwrap().to_bits(), (-0.0_f64).to_bits());
}
#[test]
fn product_guards_precede_cancellation_and_projection() {
    use LpWidth::{F32, F64};
    assert!(product(&[1e30, -1e30], &[0, 0], &[1e30], F32, F64).is_err());
    assert!(product(&[2_f64.powi(-126)], &[0], &[2_f64.powi(-24)], F32, F64).is_err());
    let large = f64::from(f32::MAX);
    assert!(product(&[large, large], &[0, 0], &[1.0], F32, F32).is_err());
    assert_eq!(
        product(&[large, large], &[0, 0], &[1.0], F32, F64).unwrap(),
        2.0 * large
    );
    // 2^24 + 1 rounds in binary32; accumulation width is independently observable.
    assert_eq!(
        product(&[16777216.0, 1.0], &[0, 0], &[1.0], F32, F32).unwrap(),
        16777216.0
    );
    assert_eq!(
        product(&[16777216.0, 1.0], &[0, 0], &[1.0], F32, F64).unwrap(),
        16777217.0
    );
}
#[test]
fn canonical_transpose_and_step_cover_original_and_represented() {
    let model = Model::from_json(include_bytes!("../../../examples/lp-model-v1.json")).unwrap();
    let program = LinearProgram::new(&model).unwrap();
    let mut e = Engine::new(&program, LpSettings::published(20, 4));
    let op = PrecisionOperator::new(&e, &settings()).unwrap();
    let rows = program
        .row_major()
        .entries()
        .zip(&op.rows)
        .map(|((r, c, _), &v)| ((r, c as usize), v.to_bits()))
        .collect::<std::collections::BTreeMap<_, _>>();
    for ((c, r, _), &v) in program.column_major().entries().zip(&op.columns) {
        assert_eq!(rows[&(r as usize, c)], v.to_bits());
    }
    assert!(op.step <= e.step());
    assert!(op.step * op.bounds[0] <= 0.9);
    assert!(op.step * op.bounds[1] <= 0.9);
    e.restrict_step(op.step).unwrap();
    let mut c = Fp64Controller::new(&e);
    let cp = c.checkpoint();
    let (x, y) = correction(&e, c.state()).unwrap();
    c.commit_steps(1).unwrap();
    c.charge_extra(1).unwrap();
    c.replace_endpoint(x, y).unwrap();
    assert_eq!(c.state().iterations, 1);
    assert_eq!(c.physical_iterations(), 2);
    c.restore(&cp).unwrap();
    assert_eq!(c.state().iterations, 0);
    assert_eq!(c.physical_iterations(), 2);
}
