//! `lp-study materialize`/`verify-batch` contracts under SPEC-0014:
//! materialization is deterministic and verification runs from the retained
//! evidence alone, with no device involved.

use std::path::PathBuf;
use std::process::Command;
use std::sync::atomic::{AtomicUsize, Ordering};

/// Isolated temporary directory removed on drop.
struct Sandbox {
    path: PathBuf,
}

impl Sandbox {
    fn new() -> Self {
        static COUNTER: AtomicUsize = AtomicUsize::new(0);
        let path = std::env::temp_dir().join(format!(
            "ai-optimizer-lp-study-{}-{}",
            std::process::id(),
            COUNTER.fetch_add(1, Ordering::SeqCst)
        ));
        std::fs::create_dir_all(&path).expect("sandbox");
        Self { path }
    }

    fn write(&self, name: &str, contents: &str) -> PathBuf {
        let path = self.path.join(name);
        std::fs::write(&path, contents).expect("write fixture");
        path
    }

    fn command(&self) -> Command {
        Command::new(env!("CARGO_BIN_EXE_optimizer"))
    }
}

impl Drop for Sandbox {
    fn drop(&mut self) {
        std::fs::remove_dir_all(&self.path).ok();
    }
}

fn repository_root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("../..")
        .canonicalize()
        .expect("repository root")
}

/// A two-solve variant batch over the continuous example model, whose
/// variables are 0 and 1 with bounds [0, 1].
const VARIANT_BATCH: &str = r#"{
  "schema_version": 1,
  "kind": "variant",
  "solves": 2,
  "variants": [
    {"index": 0, "changes": [{"variable_id": 0, "lower": 0.25, "upper": 1.0}]},
    {"index": 1, "changes": [{"variable_id": 1, "lower": 0.0, "upper": 0.75}]}
  ],
  "generator": {"seed": 7, "changes": 1},
  "batch_time_limit_ms": 60000
}"#;

/// Requirement 16: materialization is one deterministic pure function, so two
/// invocations produce identical bytes and the printed SHA-256 is the hash of
/// the written file.
#[test]
fn materialize_is_deterministic_and_prints_the_materialized_hash() {
    let sandbox = Sandbox::new();
    let model = repository_root().join("examples/lp-model-v1.json");
    let batch = sandbox.write("batch.json", VARIANT_BATCH);

    let mut outputs = Vec::new();
    for name in ["first.json", "second.json"] {
        let out = sandbox.path.join(name);
        let output = sandbox
            .command()
            .arg("lp-study")
            .arg("materialize")
            .arg("--model")
            .arg(&model)
            .arg("--batch")
            .arg(&batch)
            .arg("--index")
            .arg("1")
            .arg("--out")
            .arg(&out)
            .output()
            .expect("run materialize");
        assert_eq!(
            output.status.code(),
            Some(0),
            "{}",
            String::from_utf8_lossy(&output.stderr)
        );
        let bytes = std::fs::read(&out).expect("materialized model");
        let printed = String::from_utf8(output.stdout).expect("utf-8 hash");
        assert_eq!(printed.trim(), optimizer_core::sha256::hex(&bytes));
        outputs.push(bytes);
    }
    assert_eq!(
        outputs[0], outputs[1],
        "materialized bytes are deterministic"
    );
    // The materialized variant is not the base model's bytes.
    assert_ne!(outputs[0], std::fs::read(&model).expect("base model"));
}

/// Materialization refusals and strict flags are argument/document errors
/// that write no output file.
#[test]
fn materialize_refusals_write_no_output() {
    let sandbox = Sandbox::new();
    let model = repository_root().join("examples/lp-model-v1.json");
    let batch = sandbox.write("batch.json", VARIANT_BATCH);

    let cases: Vec<Vec<String>> = vec![
        // An index outside the batch.
        vec!["--index".into(), "2".into()],
        // An index that is not a number.
        vec!["--index".into(), "k".into()],
        // An unknown flag.
        vec!["--index".into(), "1".into(), "--unknown".into(), "x".into()],
    ];
    for (case, extra) in cases.into_iter().enumerate() {
        let out = sandbox.path.join(format!("out-{case}.json"));
        let output = sandbox
            .command()
            .arg("lp-study")
            .arg("materialize")
            .arg("--model")
            .arg(&model)
            .arg("--batch")
            .arg(&batch)
            .arg("--out")
            .arg(&out)
            .args(&extra)
            .output()
            .expect("run materialize");
        assert_eq!(output.status.code(), Some(2), "case {case}");
        assert!(!out.exists(), "case {case}: no output is written");
    }
}

/// Verification over a directory that does not exist fails cleanly as an I/O
/// error, not a panic or a silent pass.
#[test]
fn verify_batch_over_a_missing_directory_fails_cleanly() {
    let sandbox = Sandbox::new();
    let batch = sandbox.write("batch.json", VARIANT_BATCH);

    let output = sandbox
        .command()
        .arg("lp-study")
        .arg("verify-batch")
        .arg("--model")
        .arg(repository_root().join("examples/lp-model-v1.json"))
        .arg("--batch")
        .arg(&batch)
        .arg("--evidence")
        .arg(sandbox.path.join("absent"))
        .output()
        .expect("run verify-batch");

    assert_eq!(output.status.code(), Some(2));
    assert!(output.stdout.is_empty(), "no success line on a failure");
    let stderr = String::from_utf8_lossy(&output.stderr);
    assert!(stderr.contains("io:"), "{stderr}");
}

/// A recorded batch directory verifies from the retained evidence alone, and
/// verification detects a request that no longer matches the record.
#[test]
fn verify_batch_accepts_a_recorded_directory_and_detects_tampering() {
    use optimizer_experiment::lp_batch::{
        BatchEndpoint, BatchRequest, NO_RECORD, SolveSummary, materialize, write_evidence_file,
    };
    let sandbox = Sandbox::new();
    let model_path = repository_root().join("examples/lp-model-v1.json");
    let model_bytes = std::fs::read(&model_path).expect("model");
    let batch = sandbox.write("batch.json", VARIANT_BATCH);
    let base = optimizer_core::Model::from_json(&model_bytes).expect("base model");
    let request = BatchRequest::from_json(VARIANT_BATCH.as_bytes()).expect("request");
    let solves = (0..request.solves)
        .map(|index| {
            let (_, _, model_sha256) = materialize(&base, &request, index).expect("materialize");
            SolveSummary {
                index,
                model_sha256,
                endpoint_sha256: NO_RECORD.to_owned(),
                status: "not_attempted".to_string(),
                solve_elapsed_ns: 0,
                session_phases_ns: std::collections::BTreeMap::new(),
                reason: Some("cancelled".to_string()),
            }
        })
        .collect();
    let endpoint = BatchEndpoint::new(
        VARIANT_BATCH.as_bytes(),
        &model_bytes,
        "cuda-lp-tuned".to_string(),
        optimizer_core::SessionSetup::default(),
        solves,
    )
    .expect("batch endpoint");
    let evidence = sandbox.path.join("evidence");
    std::fs::create_dir_all(&evidence).expect("evidence dir");
    write_evidence_file(
        &evidence.join("batch.json"),
        &serde_json::to_vec_pretty(&endpoint).expect("json"),
    )
    .expect("write batch.json");

    let verify = |batch: &PathBuf| {
        sandbox
            .command()
            .arg("lp-study")
            .arg("verify-batch")
            .arg("--model")
            .arg(&model_path)
            .arg("--batch")
            .arg(batch)
            .arg("--evidence")
            .arg(&evidence)
            .output()
            .expect("run verify-batch")
    };
    let accepted = verify(&batch);
    assert_eq!(
        accepted.status.code(),
        Some(0),
        "{}",
        String::from_utf8_lossy(&accepted.stderr)
    );
    let stdout: serde_json::Value = serde_json::from_slice(&accepted.stdout).expect("success json");
    assert_eq!(stdout["verified"], true);
    assert_eq!(stdout["solves"], 2);

    // A request whose bytes differ from the recorded batch hash is refused.
    let tampered = sandbox.write("tampered.json", &VARIANT_BATCH.replace("60000", "30000"));
    let refused = verify(&tampered);
    assert_eq!(refused.status.code(), Some(2));
    assert!(refused.stdout.is_empty());
}
