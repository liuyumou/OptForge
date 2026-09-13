//! Solve CLI contracts under SPEC-0002 requirement 10 and its exit semantics.

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
            "ai-optimizer-solve-{}-{}",
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

const CONFIG: &str = r#"{
  "schema_version": 1,
  "seed": 17,
  "time_limit_ms": 10000,
  "iteration_limit": null,
  "node_limit": null,
  "tolerances": {"absolute": 1e-9, "relative": 1e-9, "integrality": 1e-9},
  "threads": 1
}"#;

/// `min 2 x3 + x8 + 0.5` subject to `x3 + x8 >= 2`, x3 binary, x8 >= 0.
const MODEL: &str = r#"{
  "schema_version": 1,
  "model_id": "cli-solve",
  "variables": [
    {"id": 3, "domain": "binary", "lower": {"kind": "finite", "value": 0.0}, "upper": {"kind": "finite", "value": 1.0}},
    {"id": 8, "domain": "continuous", "lower": {"kind": "finite", "value": 0.0}, "upper": {"kind": "positive_infinity"}}
  ],
  "constraints": [
    {"id": 12, "lower": {"kind": "finite", "value": 2.0}, "upper": {"kind": "positive_infinity"}, "terms": [
      {"variable_id": 3, "coefficient": 1.0},
      {"variable_id": 8, "coefficient": 1.0}
    ]}
  ],
  "objective": {"sense": "minimize", "offset": 0.5, "terms": [
    {"variable_id": 3, "coefficient": 2.0},
    {"variable_id": 8, "coefficient": 1.0}
  ]}
}"#;

fn native_available() -> bool {
    if optimizer_highs_is_native() {
        return true;
    }
    eprintln!("SKIP: HiGHS not provisioned; run bash tools/setup_highs.sh");
    false
}

/// The CLI binary is built with the same features as this test, so the adapter's
/// native state is observable through a trial solve rather than a linked flag.
fn optimizer_highs_is_native() -> bool {
    let sandbox = Sandbox::new();
    let model = sandbox.write("model.json", MODEL);
    let config = sandbox.write("config.json", CONFIG);
    let output = sandbox
        .command()
        .arg("solve")
        .arg("--model")
        .arg(&model)
        .arg("--config")
        .arg(&config)
        .output()
        .expect("run solve");
    !String::from_utf8_lossy(&output.stderr).contains("not provisioned")
}

// Requirement 10: a completed solve prints a version-1 record and exits 0.
#[test]
fn completed_solve_prints_a_record_and_exits_zero() {
    if !native_available() {
        return;
    }
    let sandbox = Sandbox::new();
    let model = sandbox.write("model.json", MODEL);
    let config = sandbox.write("config.json", CONFIG);

    let output = sandbox
        .command()
        .arg("solve")
        .arg("--model")
        .arg(&model)
        .arg("--config")
        .arg(&config)
        .output()
        .expect("run solve");

    assert_eq!(output.status.code(), Some(0));
    let text = String::from_utf8(output.stdout).expect("utf-8 record");
    let record: serde_json::Value = serde_json::from_str(&text).expect("json record");
    // The record is version 2 while the configuration it embeds stays version 1.
    // The two are separate documents with separate versions, and this asserts
    // both rather than only the outer one.
    assert_eq!(record["schema_version"], 2);
    assert_eq!(record["options"]["schema_version"], 1);
    assert_eq!(record["model_id"], "cli-solve");
    assert_eq!(record["backend"], "highs");
    assert_eq!(record["termination"], "optimal");
    // The published objective is the core's own recomputation.
    assert_eq!(record["objective"], 2.5);
    assert_eq!(record["validation"]["feasible"], true);
    // Enough configuration to repeat the solve.
    assert_eq!(record["options"]["seed"], 17);
    assert_eq!(record["options"]["threads"], 1);
}

// Requirement 10: flags are strict and errors write no partial record.
#[test]
fn argument_errors_are_categorized_without_partial_output() {
    let sandbox = Sandbox::new();
    let model = sandbox.write("model.json", MODEL);
    let config = sandbox.write("config.json", CONFIG);

    let cases: Vec<Vec<String>> = vec![
        // Missing required flags.
        vec!["solve".into()],
        vec![
            "solve".into(),
            "--config".into(),
            config.display().to_string(),
        ],
        // Unknown and duplicate flags.
        vec![
            "solve".into(),
            "--model".into(),
            model.display().to_string(),
            "--config".into(),
            config.display().to_string(),
            "--unknown".into(),
            "x".into(),
        ],
        vec![
            "solve".into(),
            "--model".into(),
            model.display().to_string(),
            "--model".into(),
            model.display().to_string(),
            "--config".into(),
            config.display().to_string(),
        ],
        // A flag without a value.
        vec![
            "solve".into(),
            "--model".into(),
            model.display().to_string(),
            "--config".into(),
        ],
    ];

    for args in cases {
        let output = sandbox.command().args(&args).output().expect("run solve");
        assert_eq!(output.status.code(), Some(2), "args {args:?}");
        assert!(
            output.stdout.is_empty(),
            "no partial record for {args:?}: {}",
            String::from_utf8_lossy(&output.stdout)
        );
        assert!(
            String::from_utf8_lossy(&output.stderr).contains("argument:"),
            "expected an argument category for {args:?}"
        );
    }
}

// Requirement 10: unreadable and malformed inputs are categorized I/O and
// document errors, never backend failures.
#[test]
fn input_errors_are_categorized_and_never_reach_the_backend() {
    let sandbox = Sandbox::new();
    let model = sandbox.write("model.json", MODEL);
    let config = sandbox.write("config.json", CONFIG);
    let malformed = sandbox.write("malformed.json", "{ not json");
    // A configuration with an unsupported version must fail as a document.
    let wrong_version = sandbox.write(
        "wrong-version.json",
        &CONFIG.replace("\"schema_version\": 1", "\"schema_version\": 2"),
    );
    let missing = sandbox.path.join("absent.json");

    for (args, expected) in [
        (
            vec![
                "--model",
                missing.to_str().unwrap(),
                "--config",
                config.to_str().unwrap(),
            ],
            "io:",
        ),
        (
            vec![
                "--model",
                malformed.to_str().unwrap(),
                "--config",
                config.to_str().unwrap(),
            ],
            "document:",
        ),
        (
            vec![
                "--model",
                model.to_str().unwrap(),
                "--config",
                malformed.to_str().unwrap(),
            ],
            "document:",
        ),
        (
            vec![
                "--model",
                model.to_str().unwrap(),
                "--config",
                wrong_version.to_str().unwrap(),
            ],
            "document:",
        ),
    ] {
        let output = sandbox
            .command()
            .arg("solve")
            .args(&args)
            .output()
            .expect("run solve");
        assert_eq!(output.status.code(), Some(2), "args {args:?}");
        assert!(output.stdout.is_empty(), "no partial record for {args:?}");
        let stderr = String::from_utf8_lossy(&output.stderr);
        assert!(
            stderr.contains(expected),
            "expected {expected} for {args:?}, found {stderr}"
        );
    }
}

// Requirement 5: an unsupported thread count is rejected before any solve.
#[test]
fn unsupported_configuration_is_rejected() {
    let sandbox = Sandbox::new();
    let model = sandbox.write("model.json", MODEL);
    let threaded = sandbox.write(
        "threaded.json",
        &CONFIG.replace("\"threads\": 1", "\"threads\": 8"),
    );

    let output = sandbox
        .command()
        .arg("solve")
        .arg("--model")
        .arg(&model)
        .arg("--config")
        .arg(&threaded)
        .output()
        .expect("run solve");
    assert_eq!(output.status.code(), Some(2));
    assert!(output.stdout.is_empty());
    assert!(
        String::from_utf8_lossy(&output.stderr).contains("unsupported:"),
        "expected the unsupported category"
    );
}

// Requirement 9: the two warm-start forms are mutually exclusive.
#[test]
fn candidate_and_basis_warm_starts_are_mutually_exclusive() {
    let sandbox = Sandbox::new();
    let model = sandbox.write("model.json", MODEL);
    let config = sandbox.write("config.json", CONFIG);
    let candidate = sandbox.write(
        "candidate.json",
        r#"{"schema_version": 1, "model_id": "cli-solve", "values": [
             {"variable_id": 3, "value": 0.0}, {"variable_id": 8, "value": 2.0}]}"#,
    );
    let basis = sandbox.write(
        "basis.json",
        r#"{"schema_version": 1, "model_id": "cli-solve", "model_fingerprint": "x",
            "columns": ["basic", "basic"], "rows": ["lower"]}"#,
    );

    let output = sandbox
        .command()
        .arg("solve")
        .arg("--model")
        .arg(&model)
        .arg("--config")
        .arg(&config)
        .arg("--candidate")
        .arg(&candidate)
        .arg("--basis")
        .arg(&basis)
        .output()
        .expect("run solve");
    assert_eq!(output.status.code(), Some(2));
    assert!(output.stdout.is_empty());
    assert!(String::from_utf8_lossy(&output.stderr).contains("argument:"));
}

// Requirement 9: a valid candidate warm start still produces a solved record.
#[test]
fn candidate_warm_start_is_accepted() {
    if !native_available() {
        return;
    }
    let sandbox = Sandbox::new();
    let model = sandbox.write("model.json", MODEL);
    let config = sandbox.write("config.json", CONFIG);
    let candidate = sandbox.write(
        "candidate.json",
        r#"{"schema_version": 1, "model_id": "cli-solve", "values": [
             {"variable_id": 3, "value": 0.0}, {"variable_id": 8, "value": 2.0}]}"#,
    );

    let output = sandbox
        .command()
        .arg("solve")
        .arg("--model")
        .arg(&model)
        .arg("--config")
        .arg(&config)
        .arg("--candidate")
        .arg(&candidate)
        .output()
        .expect("run solve");
    assert_eq!(output.status.code(), Some(0));
    let record: serde_json::Value = serde_json::from_slice(&output.stdout).expect("json record");
    assert_eq!(record["termination"], "optimal");
    assert_eq!(record["objective"], 2.5);
}

// Requirement 8: an infeasible model is a completed outcome with no incumbent.
#[test]
fn infeasible_models_complete_without_an_incumbent() {
    if !native_available() {
        return;
    }
    let sandbox = Sandbox::new();
    // Require x3 + x8 >= 2 while both variables are pinned to zero.
    let infeasible = MODEL
        .replace(
            r#"{"id": 8, "domain": "continuous", "lower": {"kind": "finite", "value": 0.0}, "upper": {"kind": "positive_infinity"}}"#,
            r#"{"id": 8, "domain": "continuous", "lower": {"kind": "finite", "value": 0.0}, "upper": {"kind": "finite", "value": 0.0}}"#,
        )
        .replace(
            r#"{"id": 3, "domain": "binary", "lower": {"kind": "finite", "value": 0.0}, "upper": {"kind": "finite", "value": 1.0}}"#,
            r#"{"id": 3, "domain": "binary", "lower": {"kind": "finite", "value": 0.0}, "upper": {"kind": "finite", "value": 0.0}}"#,
        );
    let model = sandbox.write("infeasible.json", &infeasible);
    let config = sandbox.write("config.json", CONFIG);

    let output = sandbox
        .command()
        .arg("solve")
        .arg("--model")
        .arg(&model)
        .arg("--config")
        .arg(&config)
        .output()
        .expect("run solve");

    assert_eq!(output.status.code(), Some(0));
    let record: serde_json::Value = serde_json::from_slice(&output.stdout).expect("json record");
    assert_eq!(record["termination"], "infeasible");
    // An absent measurement is omitted, not null.
    assert!(record.get("objective").is_none());
    assert!(record.get("candidate").is_none());
}

// ---------------------------------------------------------------------------
// SPEC-0011 requirements 18 and 25: backend selection at the run surface.
// ---------------------------------------------------------------------------

fn repository_root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("../..")
        .canonicalize()
        .expect("repository root")
}

fn solve_example(backend: Option<&str>, settings: bool) -> std::process::Output {
    let root = repository_root();
    let mut command = Command::new(env!("CARGO_BIN_EXE_optimizer"));
    command
        .arg("solve")
        .arg("--model")
        .arg(root.join("examples/lp-model-v1.json"))
        .arg("--config")
        .arg(root.join("examples/solve-config-v1.json"));
    if let Some(backend) = backend {
        command.arg("--backend").arg(backend);
    }
    if settings {
        command
            .arg("--lp-settings")
            .arg(root.join("examples/lp-settings-v1.json"));
    }
    command.output().expect("run solve")
}

/// Requirement 18: the pinned CPU backend is the default.
///
/// Asserted positively, on the backend named in the record, rather than by
/// observing that nothing else happened. Nothing in the run surface can promote
/// a solve to another backend: there is no threshold, so the default holds
/// because no number could say otherwise.
#[test]
fn the_default_configuration_reaches_the_pinned_backend() {
    let output = solve_example(None, false);
    let text = String::from_utf8(output.stdout).expect("utf-8");
    let record: serde_json::Value = serde_json::from_str(&text).expect("json");
    assert_eq!(record["backend"], "highs");
    assert!(
        record["lp_settings"].is_null(),
        "the pinned backend records no first-order settings"
    );
}

/// Requirement 25: the first-order backend is reachable by explicit selection,
/// and the record names it rather than the default.
#[test]
fn naming_the_first_order_backend_reaches_it_and_records_its_settings() {
    let output = solve_example(Some("host-lp"), true);
    let text = String::from_utf8(output.stdout).expect("utf-8");
    let record: serde_json::Value = serde_json::from_str(&text).expect("json");
    assert_eq!(record["backend"], "host-lp");
    // Requirements 9 and 10: the settings that produced the record are in it.
    assert_eq!(record["lp_settings"]["check_interval"], 200);
    assert_eq!(record["lp_settings"]["preconditioner"]["ruiz_passes"], 10);
    // The embedded configuration stays at version 1 while the record is 2.
    assert_eq!(record["schema_version"], 2);
    assert_eq!(record["options"]["schema_version"], 1);
}

/// The two backends agree on this model, which is what makes selecting one a
/// choice of implementation rather than a choice of answer.
#[test]
fn both_backends_agree_on_the_example_model() {
    let pinned = solve_example(None, false);
    let first_order = solve_example(Some("host-lp"), true);
    let parse = |output: std::process::Output| -> f64 {
        let text = String::from_utf8(output.stdout).expect("utf-8");
        let record: serde_json::Value = serde_json::from_str(&text).expect("json");
        record["objective"].as_f64().expect("an objective")
    };
    let expected = parse(pinned);
    let actual = parse(first_order);
    assert!(
        (expected - actual).abs() <= 1e-6 * expected.abs().max(1.0),
        "{actual} disagrees with the pinned backend's {expected}"
    );
}

/// Settings are required rather than defaulted, because requirements 9 and 10
/// make them recorded state and a default would let two different solves write
/// records that look identical.
#[test]
fn the_first_order_backend_requires_its_settings() {
    let output = solve_example(Some("host-lp"), false);
    assert_eq!(output.status.code(), Some(2));
    let stderr = String::from_utf8(output.stderr).expect("utf-8");
    assert!(stderr.contains("--lp-settings"), "{stderr}");
}

/// A flag that cannot apply is refused rather than ignored, so a caller who
/// thinks they configured something is told they did not.
#[test]
fn settings_are_refused_for_a_backend_that_has_none() {
    let output = solve_example(Some("highs"), true);
    assert_eq!(output.status.code(), Some(2));
    let stderr = String::from_utf8(output.stderr).expect("utf-8");
    assert!(stderr.contains("--lp-settings"), "{stderr}");
}

#[test]
fn an_unknown_backend_is_refused_by_name() {
    // Deliberately not one of the three real names. `cuda-lp` was used here until
    // it became a backend, which is the kind of drift a name-based negative test
    // invites; `pdlp` is close enough to be a plausible typo and is not a backend.
    let output = solve_example(Some("pdlp"), true);
    assert_eq!(output.status.code(), Some(2));
    let stderr = String::from_utf8(output.stderr).expect("utf-8");
    assert!(stderr.contains("unknown backend"), "{stderr}");
}

/// The device backend needs a device named, and says so rather than picking one.
///
/// SPEC-0010 requirement 5 leaves device selection to the caller: there is no
/// default device, and no measurement or availability check promotes a run to one.
/// A backend whose name implies a device still has to be told which.
#[test]
fn the_device_backend_requires_a_device_to_be_named() {
    let output = solve_example(Some("cuda-lp"), true);
    assert_eq!(output.status.code(), Some(2));
    let stderr = String::from_utf8(output.stderr).expect("utf-8");
    assert!(stderr.contains("--device"), "{stderr}");
}

/// A malformed device identity is refused before anything is opened.
///
/// An enumeration index is the specific shape refused: `CUDA_VISIBLE_DEVICES`
/// renumbers devices per process, so an index names different hardware in different
/// runs and a record carrying one could not be re-executed.
#[test]
fn an_enumeration_index_is_not_a_device_identity() {
    let root = repository_root();
    let output = Command::new(env!("CARGO_BIN_EXE_optimizer"))
        .arg("solve")
        .arg("--model")
        .arg(root.join("examples/lp-model-v1.json"))
        .arg("--config")
        .arg(root.join("examples/solve-config-v1.json"))
        .arg("--backend")
        .arg("cuda-lp")
        .arg("--lp-settings")
        .arg(root.join("examples/lp-settings-v1.json"))
        .arg("--device")
        .arg("0")
        .output()
        .expect("run solve");
    assert_eq!(output.status.code(), Some(2));
    let stderr = String::from_utf8(output.stderr).expect("utf-8");
    assert!(stderr.contains("device must be"), "{stderr}");
}

/// Requirement 3 end to end: the example discrete model is refused by the
/// first-order backend and solved by the pinned one, at the run surface rather
/// than only in a unit test.
#[test]
fn a_discrete_model_is_refused_by_the_first_order_backend_at_the_run_surface() {
    let root = repository_root();
    let refused = Command::new(env!("CARGO_BIN_EXE_optimizer"))
        .arg("solve")
        .arg("--model")
        .arg(root.join("examples/model-v1.json"))
        .arg("--config")
        .arg(root.join("examples/solve-config-v1.json"))
        .arg("--backend")
        .arg("host-lp")
        .arg("--lp-settings")
        .arg(root.join("examples/lp-settings-v1.json"))
        .output()
        .expect("run solve");
    assert_eq!(refused.status.code(), Some(2));
    let text = String::from_utf8(refused.stdout).expect("utf-8");
    let record: serde_json::Value = serde_json::from_str(&text).expect("json");
    assert_eq!(record["termination"], "unsupported");
    assert_eq!(record["backend"], "host-lp");
}
