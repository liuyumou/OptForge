use lp_billion_lowbit::{
    array_assessment::{Assessor, feasibility},
    array_input::{Original, Store},
};
use optimizer_core::{Model, PreconditionerSettings};
use optimizer_lp::{LinearProgram, Preconditioner};
use serde_json::json;
use std::sync::atomic::{AtomicUsize, Ordering};
pub mod problem {
    pub use optimizer_lp::LinearProgram;
}
pub mod reduce {
    pub use optimizer_lp::tree_sum;
}
#[allow(dead_code, unexpected_cfgs)]
#[path = "../../../crates/optimizer-lp/src/precondition.rs"]
mod original_precondition;
static NEXT: AtomicUsize = AtomicUsize::new(0);

#[test]
fn owned_preparation_preserves_original_engine_geometry_and_rejects_invalid_data() {
    let bits = |v: &[f64]| v.iter().map(|v| v.to_bits()).collect::<Vec<_>>();
    for (n, m) in [(0, 0), (0, 3), (3, 0), (7, 11), (33, 9)] {
        for sense in ["minimize", "maximize"] {
            let model = fixture(n, m, sense, 0);
            let p = LinearProgram::new(&model).unwrap();
            let s = optimizer_lp::LpSettings::published(100, 100);
            let reference = lp_billion_lowbit::host::engine(&p, s);
            let make = |row: Vec<f64>, step: f64| {
                optimizer_lp::Engine::from_device_preparation(
                    &p,
                    s,
                    row,
                    reference.preconditioner().column().to_vec(),
                    reference.scaled_matrix().0.to_vec(),
                    reference.scaled_matrix().1.to_vec(),
                    step,
                )
            };
            let candidate =
                make(reference.preconditioner().row().to_vec(), reference.step()).unwrap();
            assert_eq!(reference.step().to_bits(), candidate.step().to_bits());
            assert_eq!(
                reference.preconditioner().digest(),
                candidate.preconditioner().digest()
            );
            for (a, b) in [
                (reference.scaled_matrix().0, candidate.scaled_matrix().0),
                (reference.scaled_matrix().1, candidate.scaled_matrix().1),
                (reference.scaled_objective(), candidate.scaled_objective()),
                (
                    reference.scaled_row_bounds().0,
                    candidate.scaled_row_bounds().0,
                ),
                (
                    reference.scaled_row_bounds().1,
                    candidate.scaled_row_bounds().1,
                ),
                (
                    reference.scaled_column_bounds().0,
                    candidate.scaled_column_bounds().0,
                ),
                (
                    reference.scaled_column_bounds().1,
                    candidate.scaled_column_bounds().1,
                ),
            ] {
                assert_eq!(bits(a), bits(b));
            }
            assert!(make(vec![1.; m + 1], reference.step()).is_err());
            assert!(make(reference.preconditioner().row().to_vec(), f64::NAN).is_err());
            if m > 0 {
                assert!(make(vec![0.; m], reference.step()).is_err());
            }
        }
    }
}
fn fixture(n: usize, m: usize, sense: &str, special: usize) -> Model {
    let b = |v| json!({"kind":"finite","value":v});
    Model::from_json(&serde_json::to_vec(&json!({"schema_version":1,"model_id":"arrays",
        "variables":(0..n).map(|j|json!({"id":j*13+7,"domain":"continuous","lower":b(-2.),"upper":b(3.)})).collect::<Vec<_>>(),
        "constraints":(0..m).map(|i|json!({"id":i*17+9,"lower":b(-3.),"upper":b(5.),"terms":(0..n).filter(|j|(j+i)%3==0).map(|j|json!({"variable_id":j*13+7,"coefficient":match special {1=>-0.,2=>f64::from_bits((i+j+1) as u64),3=>f64::MAX/2.,_=>((i*7+j*11)%23) as f64/13.-0.75}})).collect::<Vec<_>>()})).collect::<Vec<_>>(),
        "objective":{"sense":sense,"offset":-3.25,"terms":(0..n).filter(|j|j%2==0).map(|j|json!({"variable_id":j*13+7,"coefficient":j as f64/17.-1.})).collect::<Vec<_>>()}
    })).unwrap()).unwrap()
}
fn roundtrip(model: &Model) -> (Original, Store, std::path::PathBuf) {
    let root = std::env::temp_dir().join(format!(
        "billion-arrays-{}-{}",
        std::process::id(),
        NEXT.fetch_add(1, Ordering::Relaxed)
    ));
    let store = Store::new(&root).unwrap();
    let manifest = Original::convert(model, &store).unwrap();
    let path = root.join("model.json");
    std::fs::write(&path, serde_json::to_vec(&manifest).unwrap()).unwrap();
    (Original::load(&path, &store).unwrap(), store, root)
}
#[test]
fn original_arrays_preparation_and_certificates_match() {
    for (n, m) in [(0, 0), (0, 3), (3, 0), (7, 11), (33, 9), (129, 65)] {
        for sense in ["minimize", "maximize"] {
            for special in 0..4 {
                let model = fixture(n, m, sense, special);
                let p = LinearProgram::new(&model).unwrap();
                let (original, store, root) = roundtrip(&model);
                assert_eq!(p, original.program);
                assert_eq!(p.matrix_sha256(), original.program.matrix_sha256());
                for alpha in [0., 0.5, 1., 1.75, 2.] {
                    let settings = PreconditionerSettings {
                        ruiz_passes: 3,
                        pock_chambolle_alpha: alpha,
                    };
                    let a = Preconditioner::new(&p, settings);
                    let b = original_precondition::Preconditioner::new(&p, settings);
                    assert_eq!(
                        a.digest(),
                        b.digest(),
                        "n={n} m={m} special={special} alpha={alpha}"
                    );
                }
                for v in [-0., 0.25, 3.000000001, f64::from_bits(1), f64::MAX] {
                    let x = vec![v; n];
                    let y = vec![0.125; m];
                    let a = lp_billion_lowbit::solve::assess(&model, &p, &x, &y, 1e-9);
                    let b = Assessor::new(&original, &store, true).evaluate(&x, &y, 1e-9, false);
                    match (a, b) {
                        (Ok(a), Ok(b)) => assert_eq!(a, b),
                        (Err(_), Err(_)) => (),
                        pair => panic!("assessment difference {pair:?}"),
                    }
                }
                drop(store);
                drop(original);
                std::fs::remove_dir_all(root).unwrap();
            }
        }
    }
}
#[test]
fn parallel_feasibility_preserves_finite_reports_and_refusal() {
    let model = fixture(1025, 257, "maximize", 0);
    let (a, _, root) = roundtrip(&model);
    for v in [-0., 0.125, 3., f64::MAX, f64::NAN] {
        let x = vec![v; 1025];
        assert_eq!(
            feasibility(&a, &x, 1e-9, false).map_err(|e| e.to_string()),
            feasibility(&a, &x, 1e-9, true).map_err(|e| e.to_string())
        );
    }
    std::fs::remove_dir_all(root).unwrap();
}
#[test]
fn malformed_chunks_and_shapes_are_refused() {
    let model = fixture(7, 11, "minimize", 0);
    let (a, store, root) = roundtrip(&model);
    let mut manifest = Original::convert(&model, &store).unwrap();
    manifest.arrays.get_mut("indices").unwrap().count += 1;
    std::fs::write(
        root.join("bad.json"),
        serde_json::to_vec(&manifest).unwrap(),
    )
    .unwrap();
    assert!(Original::load(&root.join("bad.json"), &store).is_err());
    let endpoint = store.write(&[0.25f64, -0., f64::from_bits(1)]).unwrap();
    let decoded: Vec<f64> = store.read(&endpoint, 3).unwrap();
    assert_eq!(
        decoded.iter().map(|v| v.to_bits()).collect::<Vec<_>>(),
        vec![0.25f64.to_bits(), (-0f64).to_bits(), 1]
    );
    std::fs::write(
        root.join("objects")
            .join(format!("{}.bin", endpoint.chunks[0].sha256)),
        vec![0u8; 24],
    )
    .unwrap();
    assert!(store.read::<f64>(&endpoint, 3).is_err());
    drop(a);
    std::fs::remove_dir_all(root).unwrap();
}
