//! `solve-batch` contracts under SPEC-0014: input refusals fire before any
//! device open, and a session failure is recorded, never substituted.

use std::path::{Path, PathBuf};
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
            "ai-optimizer-batch-{}-{}",
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
        let mut command = Command::new(env!("CARGO_BIN_EXE_optimizer"));
        // The lock path is sandboxed so a test never waits on or disturbs a
        // real lease holder.
        command.env("AI_OPTIMIZER_GPU_LOCK", self.path.join("gpu.lock"));
        command
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

/// A well-formed device identity no host has: discovery never matches it, so
/// these tests never touch hardware.
const ABSENT_DEVICE: &str = "GPU-00000000-0000-0000-0000-000000000000";

const REPEAT_BATCH: &str = r#"{
  "schema_version": 1,
  "kind": "repeat",
  "solves": 2,
  "variants": [],
  "generator": null,
  "batch_time_limit_ms": 60000
}"#;

/// A variant batch whose one change names a variable the example model lacks.
const UNKNOWN_VARIABLE_BATCH: &str = r#"{
  "schema_version": 1,
  "kind": "variant",
  "solves": 1,
  "variants": [
    {"index": 0, "changes": [{"variable_id": 999999, "lower": 0.0, "upper": 1.0}]}
  ],
  "generator": {"seed": 7, "changes": 1},
  "batch_time_limit_ms": 60000
}"#;

fn solve_batch(sandbox: &Sandbox, batch: &Path, evidence: &Path) -> std::process::Output {
    let root = repository_root();
    sandbox
        .command()
        .arg("solve-batch")
        .arg("--model")
        .arg(root.join("examples/lp-model-v1.json"))
        .arg("--batch")
        .arg(batch)
        .arg("--config")
        .arg(root.join("examples/solve-config-v1.json"))
        .arg("--lp-settings")
        .arg(root.join("examples/lp-settings-v1.json"))
        .arg("--lp-execution")
        .arg(root.join("examples/lp-execution-v1.json"))
        .arg("--device")
        .arg(ABSENT_DEVICE)
        .arg("--lp-evidence")
        .arg(evidence)
        .output()
        .expect("run solve-batch")
}

/// Requirement 35: the 16 MiB per-document limit refuses the batch request
/// before any device is opened. The ordering is what is asserted: had the
/// device been opened first, the error would name the device rather than the
/// limit.
#[test]
fn an_oversized_batch_document_is_refused_before_any_device_open() {
    let sandbox = Sandbox::new();
    let oversized = sandbox.path.join("oversized.json");
    std::fs::write(&oversized, vec![b' '; 16 * 1024 * 1024 + 1]).expect("write fixture");
    let evidence = sandbox.path.join("evidence");

    let output = solve_batch(&sandbox, &oversized, &evidence);

    assert_eq!(output.status.code(), Some(2));
    assert!(output.stdout.is_empty(), "no summary on a refusal");
    let stderr = String::from_utf8_lossy(&output.stderr);
    assert!(stderr.contains("input exceeds 16 MiB"), "{stderr}");
    assert!(
        !stderr.contains("unsupported: device"),
        "the refusal precedes any device open: {stderr}"
    );
    assert!(!evidence.exists(), "no evidence is written");
}

/// A variant naming a variable the base model lacks is refused by the
/// up-front materialization pass, before the device is opened; on this
/// deviceless host an open attempt would otherwise report the device.
#[test]
fn a_variant_naming_an_unknown_variable_is_refused_before_any_device_open() {
    let sandbox = Sandbox::new();
    let batch = sandbox.write("batch.json", UNKNOWN_VARIABLE_BATCH);
    let evidence = sandbox.path.join("evidence");

    let output = solve_batch(&sandbox, &batch, &evidence);

    assert_eq!(output.status.code(), Some(2));
    assert!(output.stdout.is_empty());
    let stderr = String::from_utf8_lossy(&output.stderr);
    assert!(stderr.contains("unknown variable 999999"), "{stderr}");
    assert!(
        !stderr.contains("unsupported: device"),
        "the refusal precedes any device open: {stderr}"
    );
    assert!(!evidence.exists(), "no evidence is written");
}

/// Flags are strict: unknown, duplicate, missing or malformed flags are
/// categorized argument errors that write no evidence.
#[test]
fn argument_errors_are_categorized_without_evidence() {
    let sandbox = Sandbox::new();
    let root = repository_root();
    let model = root.join("examples/lp-model-v1.json");
    let config = root.join("examples/solve-config-v1.json");
    let settings = root.join("examples/lp-settings-v1.json");
    let execution = root.join("examples/lp-execution-v1.json");

    for (case, extra) in [
        // A required flag missing (--batch).
        vec![],
        // An unknown flag.
        vec!["--batch", "x", "--unknown", "x"],
        // A duplicate flag.
        vec!["--batch", "x", "--batch", "y"],
        // A flag without a value.
        vec!["--batch", "x", "--lp-profile"],
        // A profile flag value that is neither true nor false.
        vec!["--batch", "x", "--lp-profile", "maybe"],
    ]
    .into_iter()
    .enumerate()
    {
        let evidence = sandbox.path.join(format!("evidence-{case}"));
        let output = sandbox
            .command()
            .arg("solve-batch")
            .arg("--model")
            .arg(&model)
            .arg("--config")
            .arg(&config)
            .arg("--lp-settings")
            .arg(&settings)
            .arg("--lp-execution")
            .arg(&execution)
            .arg("--device")
            .arg(ABSENT_DEVICE)
            .arg("--lp-evidence")
            .arg(&evidence)
            .args(&extra)
            .output()
            .expect("run solve-batch");
        assert_eq!(output.status.code(), Some(2), "case {case}");
        assert!(output.stdout.is_empty(), "case {case}: no summary");
        assert!(
            String::from_utf8_lossy(&output.stderr).contains("argument:"),
            "case {case}: expected an argument category"
        );
        assert!(!evidence.exists(), "case {case}: no evidence is written");
    }
}

/// There is no HiGHS fallback: a session that cannot be opened is reported in
/// `batch.json` with every solve `not_attempted` and an explicit reason, the
/// command exits non-zero, and the recorded directory verifies from the
/// retained evidence alone (requirements 13, 17 and 27).
#[test]
fn a_session_open_failure_is_recorded_never_substituted_and_verifies() {
    let sandbox = Sandbox::new();
    let batch = sandbox.write("batch.json", REPEAT_BATCH);
    let evidence = sandbox.path.join("evidence");

    let output = solve_batch(&sandbox, &batch, &evidence);

    assert_eq!(output.status.code(), Some(2));
    let record: serde_json::Value =
        serde_json::from_slice(&std::fs::read(evidence.join("batch.json")).expect("batch record"))
            .expect("batch record json");
    assert_eq!(record["schema_version"], 1);
    assert_eq!(record["requested_backend"], "cuda-lp-tuned");
    let solves = record["solves"].as_array().expect("solve summaries");
    assert_eq!(solves.len(), 2);
    for (index, solve) in solves.iter().enumerate() {
        assert_eq!(solve["index"], index as u64);
        assert_eq!(solve["status"], "not_attempted");
        assert_eq!(solve["endpoint_sha256"], "-");
        assert!(solve["reason"].is_string(), "an explicit reason");
    }
    assert_eq!(
        record["payload_sha256"]
            .as_str()
            .expect("payload hash")
            .len(),
        64
    );
    // No solve ran: no per-solve record exists and nothing fell back.
    assert!(!evidence.join("solve-000.json").exists());
    let summary: serde_json::Value = serde_json::from_slice(&output.stdout).expect("summary json");
    assert_eq!(summary["solves"], 2);
    assert_eq!(summary["statuses"]["not_attempted"], 2);

    // The recorded directory verifies from the retained evidence alone.
    let verified = sandbox
        .command()
        .arg("lp-study")
        .arg("verify-batch")
        .arg("--model")
        .arg(repository_root().join("examples/lp-model-v1.json"))
        .arg("--batch")
        .arg(&batch)
        .arg("--evidence")
        .arg(&evidence)
        .output()
        .expect("run verify-batch");
    assert_eq!(
        verified.status.code(),
        Some(0),
        "{}",
        String::from_utf8_lossy(&verified.stderr)
    );
}
