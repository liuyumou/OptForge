//! CPU-only component and cold-process comparison, after separate correctness.
use lp_billion_lowbit::{
    array_input::{Manifest, Original, Store},
    certificate_fast, certificate_workspace,
};
use optimizer_core::ObjectiveSense;
use optimizer_lp::{Certificate, LinearProgram, Range};
use serde_json::{Value, json};
use std::{
    collections::BTreeMap,
    fs,
    io::Write,
    path::Path,
    process::{Command, Stdio},
    time::Instant,
};
fn bits(c: Certificate) -> (u64, u64, u64, usize) {
    (
        c.bound.to_bits(),
        c.unadjusted.to_bits(),
        c.allowance.to_bits(),
        c.repaired,
    )
}
fn generate(root: &Path, n: usize, m: usize, width: usize, skew: bool, seed: usize) -> Original {
    let store = Store::new(root).unwrap();
    let mut offsets = vec![0u64];
    let mut indices = Vec::with_capacity(m * width);
    let mut values = Vec::with_capacity(m * width);
    for row in 0..m {
        let domain = if skew && row % 8 != 0 { 256 } else { n };
        let mut cols = (0..width)
            .map(|j| ((row * 17 + j + seed % 127) % domain) as u32)
            .collect::<Vec<_>>();
        cols.sort_unstable();
        for j in cols {
            indices.push(j);
            values.push(((row * 7 + j as usize * 11 + seed % 29) % 31) as f64 / 29. - 0.5);
        }
        offsets.push(values.len() as u64);
    }
    let mut arrays = BTreeMap::new();
    arrays.insert(
        "column_ids".into(),
        store.write(&(0..n as u32).collect::<Vec<_>>()).unwrap(),
    );
    arrays.insert(
        "row_ids".into(),
        store.write(&(0..m as u32).collect::<Vec<_>>()).unwrap(),
    );
    for (name, count, lo, hi) in [("column", n, -2., 3.), ("row", m, -1., 2.)] {
        arrays.insert(
            format!("{name}_lower"),
            store.write(&vec![lo; count]).unwrap(),
        );
        arrays.insert(
            format!("{name}_upper"),
            store.write(&vec![hi; count]).unwrap(),
        );
    }
    arrays.insert("offsets".into(), store.write(&offsets).unwrap());
    arrays.insert("indices".into(), store.write(&indices).unwrap());
    arrays.insert("values".into(), store.write(&values).unwrap());
    let oi = (0..n as u32).collect::<Vec<_>>();
    let ov = (0..n)
        .map(|j| (j % 7) as f64 / 17. - 0.125)
        .collect::<Vec<_>>();
    arrays.insert("objective_indices".into(), store.write(&oi).unwrap());
    arrays.insert("objective_values".into(), store.write(&ov).unwrap());
    let manifest = Manifest {
        schema_version: 1,
        model_id: format!("fresh-io-{seed}-{n}-{skew}"),
        rows: m,
        columns: n,
        nonzeros: m * width,
        sense: ObjectiveSense::Minimize,
        offset: 3.25,
        arrays,
    };
    fs::write(
        root.join("model.json"),
        serde_json::to_vec(&manifest).unwrap(),
    )
    .unwrap();
    Original {
        program: LinearProgram::from_csr(
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
            offsets.into_iter().map(|v| v as usize).collect(),
            indices,
            values,
            &oi,
            &ov,
            ObjectiveSense::Minimize,
            3.25,
        )
        .unwrap(),
        row_ids: (0..m as u32).collect(),
        model_id: manifest.model_id,
        objective_indices: oi,
        objective_values: ov,
        offset: 3.25,
        sha256: String::new(),
    }
}
fn process(
    executable: &Path,
    root: &Path,
    request: &Value,
    fast: bool,
    input: bool,
) -> (u128, Value) {
    let start = Instant::now();
    let mut cmd = Command::new(executable);
    cmd.arg(if fast { "assess-fast" } else { "assess" })
        .arg(root.join("model.json"))
        .arg(root);
    if input {
        cmd.arg("--parallel-input");
    }
    let mut child = cmd
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .unwrap();
    writeln!(child.stdin.take().unwrap(), "{request}").unwrap();
    let out = child.wait_with_output().unwrap();
    let ns = start.elapsed().as_nanos();
    assert!(
        out.status.success(),
        "{}",
        String::from_utf8_lossy(&out.stderr)
    );
    (ns, serde_json::from_slice(&out.stdout).unwrap())
}
fn main() {
    let args = std::env::args().collect::<Vec<_>>();
    assert_eq!(args.len(), 3);
    let directory = Path::new(&args[1]);
    let executor = Path::new(&args[2]);
    fs::create_dir(directory).unwrap();
    for seed in [2026112801usize, 2026112802, 2026112803] {
        for (case, n, skew) in [
            ("short", 65536, false),
            ("balanced", 8192, false),
            ("long", 257, false),
            ("skew", 8192, true),
        ] {
            let m = 131072;
            let width = 128;
            let root = directory.join(format!("{case}-{seed}"));
            let generated = Instant::now();
            let original = generate(&root, n, m, width, skew, seed);
            let generation_ns = generated.elapsed().as_nanos();
            let store = Store::new(&root).unwrap();
            let parallel = Store::new(&root).unwrap().with_read_workers(4);
            let mut old = certificate_workspace::Workspace::new(4);
            let mut fast = certificate_fast::Workspace::new(4);
            let mut samples = Vec::new();
            for repetition in 0..3 {
                let y = (0..m)
                    .map(|i| (i % 19) as f64 / 13. - 0.75 + repetition as f64 / 128.)
                    .collect::<Vec<_>>();
                let mut inputs = vec![Value::Null; 4];
                for rotation in 0..4 {
                    let variant = (rotation + repetition) % 4;
                    let reader = if variant & 1 != 0 { &parallel } else { &store };
                    let (loaded, profile) =
                        Original::load_profiled(&root.join("model.json"), reader, variant & 2 != 0)
                            .unwrap();
                    assert_eq!(loaded.program, original.program);
                    assert_eq!(
                        loaded
                            .program
                            .column_major()
                            .arrays()
                            .2
                            .iter()
                            .map(|v| v.to_bits())
                            .collect::<Vec<_>>(),
                        original
                            .program
                            .column_major()
                            .arrays()
                            .2
                            .iter()
                            .map(|v| v.to_bits())
                            .collect::<Vec<_>>()
                    );
                    inputs[variant] = json!(profile);
                }
                let scalar = bits(optimizer_lp::certify(&original.program, &y).unwrap());
                let mut cert_ns = [0u128; 2];
                for rotation in 0..2 {
                    let variant = (rotation + repetition) % 2;
                    let start = Instant::now();
                    let result = if variant == 0 {
                        old.certify(&original.program, &y)
                    } else {
                        fast.certify(&original.program, &y)
                    }
                    .unwrap();
                    cert_ns[variant] = start.elapsed().as_nanos();
                    assert_eq!(bits(result), scalar);
                }
                let endpoint = store.endpoint(&vec![0.; n], &y).unwrap();
                let request = json!({"settings":{"format":"native","tolerance":1e-9,"iteration_limit":100,"check_interval":10,"reference_window":1,"wall_ms":60000,"equilibrate":false},"endpoint":endpoint});
                let mut processes = vec![Value::Null; 4];
                let mut proofs = Vec::new();
                for rotation in 0..4 {
                    let variant = (rotation + repetition) % 4;
                    let (ns, mut response) = process(
                        executor,
                        &root,
                        &request,
                        variant & 2 != 0,
                        variant & 1 != 0,
                    );
                    let profile = response.as_object_mut().unwrap().remove("input_profile");
                    let input_ns = response.as_object_mut().unwrap().remove("input_ns");
                    processes[variant] =
                        json!({"complete_ns":ns,"input_ns":input_ns,"profile":profile});
                    proofs.push(response);
                }
                assert!(proofs.iter().all(|proof| proof == &proofs[0]));
                samples.push(json!({"repetition":repetition,"inputs":inputs,"certificate_ns":cert_ns,"processes":processes,"exact":true,"proof":proofs[0]}));
            }
            let manifest: Value =
                serde_json::from_slice(&fs::read(root.join("model.json")).unwrap()).unwrap();
            drop(original);
            drop(parallel);
            drop(store);
            fs::remove_dir_all(&root).unwrap();
            println!(
                "{}",
                json!({"case":case,"seed":seed,"rows":m,"columns":n,"nonzeros":m*width,"generation_ns":generation_ns,"samples":samples,"manifest":manifest,"synthetic_data_removed_after_exact_checks":true})
            );
            std::io::stdout().flush().unwrap();
        }
    }
    fs::remove_dir(directory).unwrap();
}
