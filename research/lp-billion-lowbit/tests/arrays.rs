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
    let original = Original::load(&path, &store).unwrap();
    let parallel_store = Store::new(&root).unwrap().with_read_workers(4);
    let (parallel, _) = Original::load_profiled(&path, &parallel_store, true).unwrap();
    assert_eq!(original.program, parallel.program);
    assert_eq!(
        original.program.matrix_sha256(),
        parallel.program.matrix_sha256()
    );
    (original, store, root)
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

#[test]
fn parallel_chunks_keep_bits_and_ordered_corruption_refusals() {
    use lp_billion_lowbit::array_input::Array;
    let root = std::env::temp_dir().join(format!("parallel-chunks-{}", std::process::id()));
    let serial = Store::new(&root).unwrap();
    let parallel = Store::new(&root).unwrap().with_read_workers(4);
    let values = (0..(1 << 19))
        .map(|i| match i % 5 {
            0 => -0.,
            1 => f64::from_bits(i as u64),
            _ => i as f64 / 17.,
        })
        .collect::<Vec<_>>();
    let chunks = values
        .chunks(1 << 16)
        .map(|chunk| {
            let bytes = chunk
                .iter()
                .flat_map(|v| v.to_le_bytes())
                .collect::<Vec<_>>();
            serial.put(&bytes).unwrap()
        })
        .collect::<Vec<_>>();
    let array = Array {
        dtype: "f64le".into(),
        count: values.len(),
        chunks,
    };
    let bits = |x: Vec<f64>| x.into_iter().map(f64::to_bits).collect::<Vec<_>>();
    assert_eq!(
        bits(serial.read(&array, values.len()).unwrap()),
        bits(parallel.read(&array, values.len()).unwrap())
    );
    let first = root
        .join("objects")
        .join(format!("{}.bin", array.chunks[0].sha256));
    let last = root
        .join("objects")
        .join(format!("{}.bin", array.chunks.last().unwrap().sha256));
    std::fs::write(first, vec![0; array.chunks[0].bytes]).unwrap();
    std::fs::write(last, [0u8]).unwrap();
    assert_eq!(
        serial
            .read::<f64>(&array, values.len())
            .unwrap_err()
            .to_string(),
        "object digest"
    );
    assert_eq!(
        parallel
            .read::<f64>(&array, values.len())
            .unwrap_err()
            .to_string(),
        "object digest"
    );
    let mut bad = array.clone();
    bad.chunks[0].bytes += 1;
    assert!(parallel.read::<f64>(&bad, values.len()).is_err());
    std::fs::remove_dir_all(root).unwrap();
}

#[test]
fn parallel_transpose_preserves_original_entry_bits_and_validation() {
    use optimizer_core::ObjectiveSense;
    use optimizer_lp::Range;
    for (n, skew) in [(257usize, false), (8192, true), (8192, false)] {
        let m = 8192;
        let width = 128;
        let mut offsets = vec![0];
        let mut indices = Vec::new();
        let mut values = Vec::new();
        for row in 0..m {
            let domain = if skew && row % 8 != 0 { 256 } else { n };
            let mut cols = (0..width)
                .map(|j| ((row * 17 + j) % domain) as u32)
                .collect::<Vec<_>>();
            cols.sort_unstable();
            for &j in &cols {
                values.push(if row % 2 == 0 {
                    -0.
                } else {
                    f64::from_bits(j as u64 + 1)
                });
            }
            indices.extend(cols);
            offsets.push(values.len());
        }
        let build = |parallel: bool, indices: Vec<u32>, values: Vec<f64>| {
            let constructor = if parallel {
                LinearProgram::from_csr_parallel
            } else {
                LinearProgram::from_csr
            };
            constructor(
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
                offsets.clone(),
                indices,
                values,
                &[0],
                &[1.],
                ObjectiveSense::Maximize,
                -0.,
            )
        };
        let serial = build(false, indices.clone(), values.clone()).unwrap();
        let parallel = build(true, indices.clone(), values.clone()).unwrap();
        assert_eq!(serial, parallel);
        let bits = |p: &LinearProgram| {
            p.column_major()
                .arrays()
                .2
                .iter()
                .map(|v| v.to_bits())
                .collect::<Vec<_>>()
        };
        assert_eq!(bits(&serial), bits(&parallel));
        for malformed in 0..3 {
            let mut i = indices.clone();
            let mut v = values.clone();
            match malformed {
                0 => i[0] = n as u32,
                1 => i[1] = i[0],
                _ => v[0] = f64::NAN,
            }
            assert_eq!(
                build(false, i.clone(), v.clone()).unwrap_err(),
                build(true, i, v).unwrap_err()
            );
        }
    }
}

#[test]
fn accelerated_cold_assessor_matches_original_command() {
    use std::io::Write;
    use std::process::{Command, Stdio};
    for (n, m) in [(0, 0), (7, 11)] {
        let model = fixture(n, m, "maximize", 0);
        let (_, store, root) = roundtrip(&model);
        let endpoint = store.endpoint(&vec![0.25; n], &vec![0.125; m]).unwrap();
        let request = json!({"settings":json!({"format":"native","tolerance":1e-9,"iteration_limit":100,"check_interval":10,"reference_window":1,"wall_ms":60000,"equilibrate":false}),"endpoint":endpoint});
        let run = |accelerated: bool| {
            let mut command = Command::new(env!("CARGO_BIN_EXE_billion"));
            command
                .arg(if accelerated { "assess-fast" } else { "assess" })
                .arg(root.join("model.json"))
                .arg(&root);
            if accelerated {
                command.arg("--parallel-input");
            }
            let mut child = command
                .stdin(Stdio::piped())
                .stdout(Stdio::piped())
                .stderr(Stdio::piped())
                .spawn()
                .unwrap();
            writeln!(child.stdin.take().unwrap(), "{request}").unwrap();
            let output = child.wait_with_output().unwrap();
            assert!(output.status.success(), "{:?}", output);
            let mut result: serde_json::Value = serde_json::from_slice(&output.stdout).unwrap();
            result.as_object_mut().unwrap().remove("input_ns");
            result.as_object_mut().unwrap().remove("input_profile");
            result
        };
        assert_eq!(run(false), run(true));
        std::fs::remove_dir_all(root).unwrap();
    }
}
