//! Flow-shop CLI contracts mapped to SPEC-0008 requirement numbers.
//!
//! The load-bearing cases are the refusals. A generated instance that could not be
//! rejected when wrong, and a record that verified whatever model it was handed,
//! would establish nothing about requirements 22 to 26.

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
            "ai-optimizer-schedule-{}-{}",
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

    fn at(&self, name: &str) -> PathBuf {
        self.path.join(name)
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

/// A budgeted configuration with no extension policy.
const CONFIG: &str = r#"{
  "schema_version": 2,
  "seed": 17,
  "node_limit": 50000,
  "time_limit_ms": 120000,
  "open_node_limit": 50000,
  "improvement_tolerance": 1e-9,
  "relaxation": {
    "schema_version": 1,
    "seed": 17,
    "time_limit_ms": null,
    "iteration_limit": null,
    "node_limit": null,
    "tolerances": {"absolute": 1e-7, "relative": 1e-9, "integrality": 1e-6},
    "threads": 1
  },
  "extensions": []
}"#;

/// The same configuration registering the one producer this surface knows.
const CONFIG_WITH_PRODUCER: &str = r#"{
  "schema_version": 2,
  "seed": 17,
  "node_limit": 50000,
  "time_limit_ms": 120000,
  "open_node_limit": 50000,
  "improvement_tolerance": 1e-9,
  "relaxation": {
    "schema_version": 1,
    "seed": 17,
    "time_limit_ms": null,
    "iteration_limit": null,
    "node_limit": null,
    "tolerances": {"absolute": 1e-7, "relative": 1e-9, "integrality": 1e-6},
    "threads": 1
  },
  "extensions": [
    {"schema_version": 1, "extension_id": "flow-shop-neh", "invocation_budget": 8, "proposal_budget": 8}
  ]
}"#;

/// Skip a native-only test loudly rather than reporting false coverage.
fn require_native(test: &str) -> bool {
    if native_available() {
        return true;
    }
    eprintln!("SKIP {test}: HiGHS not provisioned; run bash tools/setup_highs.sh");
    false
}

/// Whether the built binary links the pinned library.
///
/// This probes the binary rather than calling `optimizer_highs::is_native()`
/// directly, because this test's own feature flags do not determine the binary's:
/// linking the adapter here would report the library's state under *these* features
/// and the guard would never fire when the binary lacked it. The existing run
/// surface tests establish the same pattern for the same reason.
fn native_available() -> bool {
    let sandbox = Sandbox::new();
    let instance = sandbox.at("probe-instance.json");
    let generated = sandbox
        .command()
        .args([
            "schedule",
            "generate",
            "--instance-id",
            "probe",
            "--seed",
            "1",
        ])
        .args(["--jobs", "2", "--machines", "1", "--output"])
        .arg(&instance)
        .status()
        .expect("run generate");
    assert_eq!(
        generated.code(),
        Some(0),
        "generation needs no native library"
    );
    let config = sandbox.write("probe-config.json", CONFIG);
    let output = sandbox
        .command()
        .args(["schedule", "solve", "--instance"])
        .arg(&instance)
        .arg("--config")
        .arg(&config)
        .output()
        .expect("run solve");
    !String::from_utf8_lossy(&output.stderr).contains("not provisioned")
}

/// Requirement 21: generation writes an instance from a published seed.
#[test]
fn generate_writes_a_published_instance() {
    let sandbox = Sandbox::new();
    let output = sandbox.at("ta001.json");
    let status = sandbox
        .command()
        .args([
            "schedule",
            "generate",
            "--instance-id",
            "ta001",
            "--seed",
            "873654221",
        ])
        .args(["--jobs", "20", "--machines", "5", "--output"])
        .arg(&output)
        .status()
        .expect("run generate");
    assert_eq!(status.code(), Some(0));

    let document: serde_json::Value =
        serde_json::from_slice(&std::fs::read(&output).expect("read")).expect("parse");
    assert_eq!(document["instance_id"], "ta001");
    assert_eq!(document["jobs"], 20);
    assert_eq!(document["machines"], 5);
    // The published verification row, so the CLI path is checked against the
    // source rather than only the library being checked.
    assert_eq!(document["processing_times"][0][0], 54);
    assert_eq!(document["processing_times"][0][1], 83);
    assert_eq!(document["processing_times"][4][19], 28);
}

/// Requirement 21: generation refuses an unusable shape and a bad flag.
#[test]
fn generate_refuses_invalid_arguments() {
    let sandbox = Sandbox::new();
    for args in [
        vec![
            "schedule",
            "generate",
            "--instance-id",
            "x",
            "--seed",
            "1",
            "--jobs",
            "0",
            "--machines",
            "2",
        ],
        vec![
            "schedule",
            "generate",
            "--instance-id",
            "x",
            "--seed",
            "1",
            "--jobs",
            "4",
            "--machines",
            "999",
        ],
        vec![
            "schedule",
            "generate",
            "--instance-id",
            "x",
            "--seed",
            "notanumber",
            "--jobs",
            "4",
            "--machines",
            "2",
        ],
        vec![
            "schedule",
            "generate",
            "--seed",
            "1",
            "--jobs",
            "4",
            "--machines",
            "2",
        ],
        vec![
            "schedule",
            "generate",
            "--instance-id",
            "x",
            "--seed",
            "1",
            "--jobs",
            "4",
            "--machines",
            "2",
            "--nope",
            "1",
        ],
    ] {
        let output = sandbox
            .command()
            .args(&args)
            .output()
            .expect("run generate");
        assert_eq!(output.status.code(), Some(2), "{args:?} must be refused");
        assert!(
            output.stdout.is_empty(),
            "{args:?} must not write a partial document"
        );
    }
}

/// Requirements 25 and 26: a scheduling run writes a verifiable run record.
#[test]
fn a_scheduling_run_writes_a_verifiable_record() {
    if !require_native("a_scheduling_run_writes_a_verifiable_record") {
        return;
    }
    let sandbox = Sandbox::new();
    let config = sandbox.write("config.json", CONFIG);
    let instance = sandbox.at("tiny.json");
    assert_eq!(
        sandbox
            .command()
            .args([
                "schedule",
                "generate",
                "--instance-id",
                "tiny",
                "--seed",
                "873654221"
            ])
            .args(["--jobs", "4", "--machines", "3", "--output"])
            .arg(&instance)
            .status()
            .expect("generate")
            .code(),
        Some(0)
    );

    let record_path = sandbox.at("run.json");
    let model_path = sandbox.at("model.json");
    let status = sandbox
        .command()
        .args(["schedule", "solve", "--instance"])
        .arg(&instance)
        .arg("--config")
        .arg(&config)
        .arg("--output")
        .arg(&record_path)
        .arg("--output-model")
        .arg(&model_path)
        .status()
        .expect("run solve");
    assert_eq!(status.code(), Some(0), "a proven scheduling run exits 0");

    let record: serde_json::Value =
        serde_json::from_slice(&std::fs::read(&record_path).expect("read")).expect("parse");
    assert_eq!(record["search"]["outcome"], "proven_optimal");
    assert_eq!(record["search"]["forfeited"], false);
    // The optimum of this instance is 349, confirmed independently by exhaustive
    // enumeration of all 24 permutations in the schedule crate's own tests.
    assert_eq!(record["search"]["objective"], 349.0);
    assert!(
        record["model_fingerprint"]
            .as_str()
            .expect("a fingerprint")
            .starts_with("fnv1a64:")
    );
    assert_eq!(record["inputs"].as_array().expect("inputs").len(), 2);

    // Requirement 25: the record verifies by re-execution, using the encoded model
    // the command wrote. Without --output-model there would be nothing to verify
    // against, which is why the flag exists.
    let verify = sandbox
        .command()
        .arg("verify")
        .arg("--record")
        .arg(&record_path)
        .arg("--model")
        .arg(&model_path)
        .output()
        .expect("run verify");
    assert_eq!(verify.status.code(), Some(0), "the record must verify");
    let verdict: serde_json::Value = serde_json::from_slice(&verify.stdout).expect("parse verdict");
    assert_eq!(verdict["agreement"], true);
    assert_eq!(verdict["outcome"], "proven_optimal");
}

/// Requirement 25: verification refuses a model whose data changed.
///
/// Both instances carry the same `instance_id`, so this checks the fingerprint
/// rather than the identity, which is the distinction SPEC-0005 requirement 10
/// exists to make.
#[test]
fn verification_refuses_a_changed_instance_under_one_identity() {
    if !require_native("verification_refuses_a_changed_instance_under_one_identity") {
        return;
    }
    let sandbox = Sandbox::new();
    let config = sandbox.write("config.json", CONFIG);
    let mut produced = Vec::new();
    for (name, seed) in [("first", "873654221"), ("second", "379008056")] {
        let instance = sandbox.at(&format!("{name}-instance.json"));
        sandbox
            .command()
            .args([
                "schedule",
                "generate",
                "--instance-id",
                "shared-id",
                "--seed",
                seed,
            ])
            .args(["--jobs", "4", "--machines", "3", "--output"])
            .arg(&instance)
            .status()
            .expect("generate");
        let record = sandbox.at(&format!("{name}-run.json"));
        let model = sandbox.at(&format!("{name}-model.json"));
        sandbox
            .command()
            .args(["schedule", "solve", "--instance"])
            .arg(&instance)
            .arg("--config")
            .arg(&config)
            .arg("--output")
            .arg(&record)
            .arg("--output-model")
            .arg(&model)
            .status()
            .expect("solve");
        produced.push((record, model));
    }

    // Cross the first record with the second model: same model_id, different data.
    let output = sandbox
        .command()
        .arg("verify")
        .arg("--record")
        .arg(&produced[0].0)
        .arg("--model")
        .arg(&produced[1].1)
        .output()
        .expect("run verify");
    assert_eq!(
        output.status.code(),
        Some(2),
        "a changed model must be refused"
    );
    let stderr = String::from_utf8_lossy(&output.stderr);
    assert!(
        stderr.contains("fingerprint mismatch"),
        "expected a fingerprint refusal, got {stderr}"
    );
}

/// Requirement 18: a configuration naming an unregistered extension is refused.
#[test]
fn solve_refuses_an_unregistered_extension_policy() {
    let sandbox = Sandbox::new();
    let instance = sandbox.at("tiny.json");
    sandbox
        .command()
        .args([
            "schedule",
            "generate",
            "--instance-id",
            "tiny",
            "--seed",
            "873654221",
        ])
        .args(["--jobs", "3", "--machines", "2", "--output"])
        .arg(&instance)
        .status()
        .expect("generate");
    let config = sandbox.write(
        "config.json",
        &CONFIG_WITH_PRODUCER.replace("flow-shop-neh", "somebody-elses-extension"),
    );
    let output = sandbox
        .command()
        .args(["schedule", "solve", "--instance"])
        .arg(&instance)
        .arg("--config")
        .arg(&config)
        .output()
        .expect("run solve");
    assert_eq!(output.status.code(), Some(2));
    assert!(output.stdout.is_empty(), "no partial record on refusal");
    let stderr = String::from_utf8_lossy(&output.stderr);
    assert!(
        stderr.contains("unsupported") && stderr.contains("somebody-elses-extension"),
        "expected an unsupported refusal naming the extension, got {stderr}"
    );
}

/// Requirement 25 and SPEC-0005 requirement 14: a record naming an extension
/// policy cannot be re-executed by a surface that loads none.
///
/// This is reported as unsupported rather than as divergence. Re-execution loads no
/// extension, so the counters would differ for that reason alone, and calling that
/// a divergence would blame the record for a limitation of the verifier.
#[test]
fn verification_refuses_a_record_naming_an_extension_policy() {
    if !require_native("verification_refuses_a_record_naming_an_extension_policy") {
        return;
    }
    let sandbox = Sandbox::new();
    let config = sandbox.write("config.json", CONFIG_WITH_PRODUCER);
    let instance = sandbox.at("tiny.json");
    sandbox
        .command()
        .args([
            "schedule",
            "generate",
            "--instance-id",
            "tiny",
            "--seed",
            "873654221",
        ])
        .args(["--jobs", "4", "--machines", "3", "--output"])
        .arg(&instance)
        .status()
        .expect("generate");
    let record = sandbox.at("run.json");
    let model = sandbox.at("model.json");
    let status = sandbox
        .command()
        .args(["schedule", "solve", "--instance"])
        .arg(&instance)
        .arg("--config")
        .arg(&config)
        .arg("--output")
        .arg(&record)
        .arg("--output-model")
        .arg(&model)
        .status()
        .expect("solve");
    assert_eq!(status.code(), Some(0), "the producer run itself succeeds");

    // The producer was registered and did its work, which is what makes the
    // refusal below about re-execution rather than about a failed search.
    let written: serde_json::Value =
        serde_json::from_slice(&std::fs::read(&record).expect("read")).expect("parse");
    assert_eq!(written["search"]["outcome"], "proven_optimal");
    let summary = &written["search"]["extensions"][0];
    assert_eq!(summary["extension_id"], "flow-shop-neh");
    assert_eq!(summary["registered"], true);
    assert!(summary["accepted"].as_u64().expect("accepted count") > 0);

    let output = sandbox
        .command()
        .arg("verify")
        .arg("--record")
        .arg(&record)
        .arg("--model")
        .arg(&model)
        .output()
        .expect("run verify");
    assert_eq!(output.status.code(), Some(2));
    let stderr = String::from_utf8_lossy(&output.stderr);
    assert!(
        stderr.contains("unsupported") && stderr.contains("flow-shop-neh"),
        "expected an unsupported refusal, got {stderr}"
    );
    assert!(
        !stderr.contains("divergence"),
        "a surface limitation must not be reported as divergence: {stderr}"
    );
}

/// Requirement 1: a malformed instance is an input error, and no record is written.
#[test]
fn solve_refuses_a_malformed_instance() {
    let sandbox = Sandbox::new();
    let config = sandbox.write("config.json", CONFIG);
    for (name, body) in [
        (
            "ragged.json",
            r#"{"schema_version":1,"instance_id":"r","jobs":3,"machines":2,"processing_times":[[1,2,3],[1,2]]}"#,
        ),
        (
            "zero.json",
            r#"{"schema_version":1,"instance_id":"z","jobs":2,"machines":1,"processing_times":[[0,4]]}"#,
        ),
        (
            "version.json",
            r#"{"schema_version":2,"instance_id":"v","jobs":1,"machines":1,"processing_times":[[4]]}"#,
        ),
        (
            "unknown.json",
            r#"{"schema_version":1,"instance_id":"u","jobs":1,"machines":1,"processing_times":[[4]],"extra":1}"#,
        ),
        ("garbage.json", "not json at all"),
    ] {
        let instance = sandbox.write(name, body);
        let output = sandbox
            .command()
            .args(["schedule", "solve", "--instance"])
            .arg(&instance)
            .arg("--config")
            .arg(&config)
            .output()
            .expect("run solve");
        assert_eq!(output.status.code(), Some(2), "{name} must be refused");
        assert!(output.stdout.is_empty(), "{name} must write no record");
    }
}

/// Requirement 26: a node-limited run reports its limit and exits 1.
#[test]
fn a_node_limited_scheduling_run_reports_its_limit() {
    if !require_native("a_node_limited_scheduling_run_reports_its_limit") {
        return;
    }
    let sandbox = Sandbox::new();
    // A 20x5 Taillard instance is 400 binaries with a weak relaxation, which is
    // exactly the case requirement 26 refuses to let anyone call optimal.
    let instance = sandbox.at("ta001.json");
    sandbox
        .command()
        .args([
            "schedule",
            "generate",
            "--instance-id",
            "ta001",
            "--seed",
            "873654221",
        ])
        .args(["--jobs", "20", "--machines", "5", "--output"])
        .arg(&instance)
        .status()
        .expect("generate");
    let config = sandbox.write(
        "config.json",
        &CONFIG.replace("\"node_limit\": 50000", "\"node_limit\": 4"),
    );
    let record_path = sandbox.at("run.json");
    let output = sandbox
        .command()
        .args(["schedule", "solve", "--instance"])
        .arg(&instance)
        .arg("--config")
        .arg(&config)
        .arg("--output")
        .arg(&record_path)
        .output()
        .expect("run solve");
    assert_eq!(
        output.status.code(),
        Some(1),
        "a limited run exits 1: {}",
        String::from_utf8_lossy(&output.stderr)
    );
    let record: serde_json::Value =
        serde_json::from_slice(&std::fs::read(&record_path).expect("read")).expect("parse");
    // The record exists and says what happened, rather than being suppressed.
    let outcome = record["search"]["outcome"].as_str().expect("an outcome");
    assert!(
        outcome == "node_limit" || outcome == "feasible",
        "expected a limited outcome, got {outcome}"
    );
    assert_ne!(
        outcome, "proven_optimal",
        "a 4-node search proves nothing here"
    );
}
