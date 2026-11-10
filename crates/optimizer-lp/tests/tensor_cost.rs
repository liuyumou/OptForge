//! ADR-0044 interval norm regression cases.
#![cfg(feature = "precision-research")]
use optimizer_lp::tensor_cost::norm_block;

#[test]
fn interval_gram_retains_cancellation_and_zero() {
    assert_eq!(norm_block(&[0.; 1024]), Some(0.));
    let mut block = [0.; 1024];
    block[0] = 1.;
    block[1] = 1.;
    block[32] = 1.;
    block[33] = -1.;
    let bound = norm_block(&block).unwrap();
    assert!(bound >= 2f64.sqrt() && bound < 1.415);
}
#[test]
fn interval_gram_refuses_nonfinite_overflow_and_wrong_shapes() {
    assert!(norm_block(&[1.; 3]).is_none());
    assert!(norm_block(&[f64::INFINITY; 1024]).is_none());
    assert!(norm_block(&[1e308; 1024]).is_none());
}
#[test]
fn interval_gram_encloses_subnormal_products() {
    let bound = norm_block(&[f64::from_bits(1); 1024]).unwrap();
    assert!(bound >= 32. * f64::from_bits(1) && bound.is_finite());
}
