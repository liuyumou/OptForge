//! ADR-0035 host admission and identity regressions.
#![cfg(feature = "precision-research")]
use optimizer_core::{LpSettings, Model};
use optimizer_lp::{Engine, LinearProgram, exec::*};
#[test]
fn exec_operator_transpose_and_cache_epochs() {
    let m = Model::from_json(include_bytes!("../../../examples/lp-model-v1.json")).unwrap();
    let p = LinearProgram::new(&m).unwrap();
    let e = Engine::new(&p, LpSettings::published(40, 8));
    let op = prepare_operator(&e, RESIDENT_CAP, PEAK_CAP).unwrap();
    assert!(prepare_operator(&e, 1, PEAK_CAP).is_err());
    assert!(prepare_operator(&e, RESIDENT_CAP, 1).is_err());
    assert!(prepare_vector(&op, &[], 0, false).is_err());
    let v = prepare_vector(&op, &vec![1.0_f64.to_bits(); p.column_count()], 7, false).unwrap();
    assert_eq!(op.apply(&v, 7).unwrap().len(), p.row_count());
    assert_eq!(op.apply(&v, 8).unwrap_err(), "stale_vector");
    assert_eq!(op.apply_transpose(&v, 7).unwrap_err(), "stale_vector");
    for column in 0..p.column_count() {
        for k in op.column_offsets()[column] as usize..op.column_offsets()[column + 1] as usize {
            let canonical = op.permutation()[k] as usize;
            assert_eq!(op.row_indices()[canonical] as usize, column);
            let row = op.column_indices()[k] as usize;
            assert!(
                (op.row_offsets()[row] as usize..op.row_offsets()[row + 1] as usize)
                    .contains(&canonical)
            );
        }
    }
    let altered = Engine::with_power2_scaling(
        &p,
        e.settings(),
        &vec![0; p.row_count()],
        &vec![1; p.column_count()],
    )
    .unwrap();
    let other = prepare_operator(&altered, RESIDENT_CAP, PEAK_CAP).unwrap();
    assert_ne!(op.receipt().identity, other.receipt().identity);
    assert!(op.validate_engine(&altered).is_err());
    op.validate_engine(&e).unwrap();
    assert!(other.apply(&v, 7).is_err());
    assert_eq!(other.receipt().original_error_infinity, 0.0);
    assert_eq!(other.receipt().original_error_one, 0.0);
    assert!(prepare_vector(&op, &vec![f64::NAN.to_bits(); p.column_count()], 0, false).is_err());
}
#[test]
fn exec_modes_are_strict_strings() {
    assert!(serde_json::from_str::<Mode>("{\"cached\":null}").is_err());
    assert!(serde_json::from_str::<Mode>("\"other\"").is_err());
}
