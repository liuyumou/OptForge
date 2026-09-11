//! Run surface CLI contracts mapped to SPEC-0005 requirement numbers.
//!
//! Verification is only worth something if it can fail, so the negative cases
//! here matter more than the agreeing one: a changed model under an unchanged
//! identity, and a mutated measurement, must both be refused.

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
            "ai-optimizer-search-{}-{}",
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

    /// Run one search and return its parsed record with the exit code.
    fn search(&self, model: &PathBuf, config: &PathBuf) -> (Option<i32>, serde_json::Value) {
        let output = self
            .command()
            .arg("search")
            .arg("--model")
            .arg(model)
            .arg("--config")
            .arg(config)
            .output()
            .expect("run search");
        let code = output.status.code();
        let record = serde_json::from_slice(&output.stdout).unwrap_or_else(|error| {
            panic!(
                "expected a record, found {error}: {}{}",
                String::from_utf8_lossy(&output.stdout),
                String::from_utf8_lossy(&output.stderr)
            )
        });
        (code, record)
    }
}

impl Drop for Sandbox {
    fn drop(&mut self) {
        std::fs::remove_dir_all(&self.path).ok();
    }
}

const CONFIG: &str = r#"{
  "schema_version": 2,
  "seed": 17,
  "node_limit": null,
  "time_limit_ms": 10000,
  "open_node_limit": null,
  "improvement_tolerance": 1e-9,
  "relaxation": {
    "schema_version": 1,
    "seed": 17,
    "time_limit_ms": 10000,
    "iteration_limit": null,
    "node_limit": null,
    "tolerances": {"absolute": 1e-9, "relative": 1e-9, "integrality": 1e-9},
    "threads": 1
  },
  "extensions": []
}"#;

/// `min 2 x3 + x8 + 0.5` subject to `x3 + x8 >= 2`, x3 binary, x8 >= 0.
const MODEL: &str = r#"{
  "schema_version": 1,
  "model_id": "cli-search",
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
/// native state is observable through a trial search rather than a linked flag.
fn optimizer_highs_is_native() -> bool {
    let sandbox = Sandbox::new();
    let model = sandbox.write("model.json", MODEL);
    let config = sandbox.write("config.json", CONFIG);
    let output = sandbox
        .command()
        .arg("search")
        .arg("--model")
        .arg(&model)
        .arg("--config")
        .arg(&config)
        .output()
        .expect("run search");
    !String::from_utf8_lossy(&output.stderr).contains("not provisioned")
}

// Requirements 1, 4, 6: a completed search writes a record carrying complete
// provenance and the canonical model fingerprint, and exits 0.
#[test]
fn completed_search_writes_a_record_with_provenance() {
    if !native_available() {
        return;
    }
    let sandbox = Sandbox::new();
    let model = sandbox.write("model.json", MODEL);
    let config = sandbox.write("config.json", CONFIG);

    let (code, record) = sandbox.search(&model, &config);
    assert_eq!(code, Some(0));
    assert_eq!(record["schema_version"], 1);
    assert_eq!(record["search"]["outcome"], "proven_optimal");
    // The published objective is the core's own recomputation.
    assert_eq!(record["search"]["objective"], 2.5);
    assert_eq!(record["search"]["forfeited"], false);

    // Provenance is present and shaped as the schema requires.
    assert_eq!(record["revision"].as_str().expect("revision").len(), 40);
    assert!(record["hardware"]["cpu"].is_string());
    assert!(
        record["hardware"]["gpu_uuid"].is_null(),
        "a CPU run claims no GPU"
    );
    assert!(record["toolchain"]["rustc"].is_string());
    assert!(
        record["model_fingerprint"]
            .as_str()
            .expect("fingerprint")
            .starts_with("fnv1a64:")
    );

    // Inputs identify the bytes consumed, not only their paths.
    let inputs = record["inputs"].as_array().expect("inputs");
    assert_eq!(inputs.len(), 2);
    for input in inputs {
        assert_eq!(input["sha256"].as_str().expect("sha256").len(), 64);
    }
}

// Requirement 6: --output writes the record to a file rather than stdout.
#[test]
fn output_flag_writes_the_record_to_a_file() {
    if !native_available() {
        return;
    }
    let sandbox = Sandbox::new();
    let model = sandbox.write("model.json", MODEL);
    let config = sandbox.write("config.json", CONFIG);
    let destination = sandbox.path.join("run.json");

    let output = sandbox
        .command()
        .arg("search")
        .arg("--model")
        .arg(&model)
        .arg("--config")
        .arg(&config)
        .arg("--output")
        .arg(&destination)
        .output()
        .expect("run search");
    assert_eq!(output.status.code(), Some(0));
    assert!(output.stdout.is_empty(), "the record went to the file");
    let written = std::fs::read(&destination).expect("record file");
    let record: serde_json::Value = serde_json::from_slice(&written).expect("json record");
    assert_eq!(record["search"]["outcome"], "proven_optimal");
}

// Requirements 9-11: a freshly produced record verifies, and the verdict states
// what was compared without claiming a proof.
#[test]
fn a_fresh_record_verifies() {
    if !native_available() {
        return;
    }
    let sandbox = Sandbox::new();
    let model = sandbox.write("model.json", MODEL);
    let config = sandbox.write("config.json", CONFIG);
    let (_, record) = sandbox.search(&model, &config);
    let record_path = sandbox.write("run.json", &record.to_string());

    let output = sandbox
        .command()
        .arg("verify")
        .arg("--record")
        .arg(&record_path)
        .arg("--model")
        .arg(&model)
        .output()
        .expect("run verify");
    assert_eq!(output.status.code(), Some(0));
    let verdict: serde_json::Value = serde_json::from_slice(&output.stdout).expect("json verdict");
    assert_eq!(verdict["agreement"], true);
    assert_eq!(verdict["outcome"], "proven_optimal");
    assert_eq!(verdict["forfeited"], false);
    // Ten fields are compared, and the verdict names them.
    assert_eq!(verdict["compared"].as_array().expect("compared").len(), 10);
    // Agreement is explicitly not reported as optimality.
    assert!(
        verdict["note"]
            .as_str()
            .expect("note")
            .contains("not optimality")
    );
}

// Requirement 10: a changed model under an unchanged model_id is refused before
// any search runs. This is the check that makes a record bound to bytes.
#[test]
fn a_changed_model_is_refused_on_its_fingerprint() {
    if !native_available() {
        return;
    }
    let sandbox = Sandbox::new();
    let model = sandbox.write("model.json", MODEL);
    let config = sandbox.write("config.json", CONFIG);
    let (_, record) = sandbox.search(&model, &config);
    let record_path = sandbox.write("run.json", &record.to_string());

    // Same model_id, different coefficient.
    let changed = sandbox.write(
        "changed.json",
        &MODEL.replace(r#""coefficient": 2.0"#, r#""coefficient": 2.5"#),
    );
    let output = sandbox
        .command()
        .arg("verify")
        .arg("--record")
        .arg(&record_path)
        .arg("--model")
        .arg(&changed)
        .output()
        .expect("run verify");
    assert_eq!(output.status.code(), Some(2));
    assert!(output.stdout.is_empty(), "no verdict for a refused record");
    let stderr = String::from_utf8_lossy(&output.stderr);
    assert!(stderr.contains("fingerprint mismatch"), "found {stderr}");
}

// Requirement 11: a mutated measurement in the record is reported as divergence
// naming the field, so verification is shown to be able to fail.
#[test]
fn a_mutated_record_diverges_and_names_the_field() {
    if !native_available() {
        return;
    }
    let sandbox = Sandbox::new();
    let model = sandbox.write("model.json", MODEL);
    let config = sandbox.write("config.json", CONFIG);
    let (_, record) = sandbox.search(&model, &config);

    for (field, mutate) in [
        ("objective", r#""objective":1.5"#),
        ("nodes_explored", r#""nodes_explored":999"#),
        ("forfeited", r#""forfeited":true"#),
    ] {
        let mut mutated = record.clone();
        let replacement: serde_json::Value =
            serde_json::from_str(&format!("{{{mutate}}}")).expect("mutation");
        let value = replacement[field].clone();
        mutated["search"][field] = value;
        let record_path = sandbox.write(&format!("mutated-{field}.json"), &mutated.to_string());

        let output = sandbox
            .command()
            .arg("verify")
            .arg("--record")
            .arg(&record_path)
            .arg("--model")
            .arg(&model)
            .output()
            .expect("run verify");
        assert_eq!(output.status.code(), Some(2), "{field}");
        let stderr = String::from_utf8_lossy(&output.stderr);
        assert!(stderr.contains("divergence:"), "{field}: found {stderr}");
        assert!(
            stderr.contains(field),
            "{field} must be named, found {stderr}"
        );
    }
}

// Requirement 12: a record differing only in elapsed time still verifies.
#[test]
fn elapsed_time_alone_still_verifies() {
    if !native_available() {
        return;
    }
    let sandbox = Sandbox::new();
    let model = sandbox.write("model.json", MODEL);
    let config = sandbox.write("config.json", CONFIG);
    let (_, mut record) = sandbox.search(&model, &config);

    record["search"]["elapsed_ms"] = serde_json::json!(987_654);
    let record_path = sandbox.write("slow.json", &record.to_string());
    let output = sandbox
        .command()
        .arg("verify")
        .arg("--record")
        .arg(&record_path)
        .arg("--model")
        .arg(&model)
        .output()
        .expect("run verify");
    assert_eq!(
        output.status.code(),
        Some(0),
        "elapsed time must not fail verification: {}",
        String::from_utf8_lossy(&output.stderr)
    );
}

// Requirements 7 and 15: a node-limited search still writes a record, exits 1,
// and that record verifies. An unfinished search is a fact, not a suppression.
#[test]
fn a_node_limited_search_records_and_verifies() {
    if !native_available() {
        return;
    }
    let sandbox = Sandbox::new();
    // A model needing more than one node to prove anything.
    let model = sandbox.write(
        "wide.json",
        &MODEL.replace(
            r#"{"id": 8, "domain": "continuous", "lower": {"kind": "finite", "value": 0.0}, "upper": {"kind": "positive_infinity"}}"#,
            r#"{"id": 8, "domain": "integer", "lower": {"kind": "finite", "value": 0.0}, "upper": {"kind": "finite", "value": 40.0}}"#,
        ),
    );
    let config = sandbox.write(
        "limited.json",
        &CONFIG.replace(r#""node_limit": null"#, r#""node_limit": 1"#),
    );

    let output = sandbox
        .command()
        .arg("search")
        .arg("--model")
        .arg(&model)
        .arg("--config")
        .arg(&config)
        .output()
        .expect("run search");
    let record: serde_json::Value = serde_json::from_slice(&output.stdout).expect("json record");
    // A limit is never a completed proof, and the record says so.
    assert_eq!(output.status.code(), Some(1));
    assert_eq!(record["search"]["outcome"], "node_limit");

    let record_path = sandbox.write("limited-run.json", &record.to_string());
    let verified = sandbox
        .command()
        .arg("verify")
        .arg("--record")
        .arg(&record_path)
        .arg("--model")
        .arg(&model)
        .output()
        .expect("run verify");
    // Verification reproduces the limited search and preserves its exit code.
    assert_eq!(verified.status.code(), Some(1));
    let verdict: serde_json::Value =
        serde_json::from_slice(&verified.stdout).expect("json verdict");
    assert_eq!(verdict["agreement"], true);
    assert_eq!(verdict["outcome"], "node_limit");
}

// Requirement 14: a configuration naming an extension policy is refused rather
// than run without the extension it names.
#[test]
fn an_extension_policy_is_refused_as_unsupported() {
    let sandbox = Sandbox::new();
    let model = sandbox.write("model.json", MODEL);
    let config = sandbox.write(
        "with-extension.json",
        &CONFIG.replace(
            r#""extensions": []"#,
            r#""extensions": [{"schema_version": 1, "extension_id": "absent",
                 "invocation_budget": 4, "proposal_budget": 4}]"#,
        ),
    );

    let output = sandbox
        .command()
        .arg("search")
        .arg("--model")
        .arg(&model)
        .arg("--config")
        .arg(&config)
        .output()
        .expect("run search");
    assert_eq!(output.status.code(), Some(2));
    assert!(output.stdout.is_empty(), "no record for a refused run");
    let stderr = String::from_utf8_lossy(&output.stderr);
    assert!(stderr.contains("unsupported:"), "found {stderr}");
}

// Requirements 8 and 16: argument failures are categorized and write no record.
#[test]
fn argument_errors_are_categorized_without_partial_output() {
    let sandbox = Sandbox::new();
    let model = sandbox.write("model.json", MODEL);
    let config = sandbox.write("config.json", CONFIG);

    let cases: Vec<Vec<String>> = vec![
        vec!["search".into()],
        vec![
            "search".into(),
            "--config".into(),
            config.display().to_string(),
        ],
        vec![
            "search".into(),
            "--model".into(),
            model.display().to_string(),
            "--config".into(),
            config.display().to_string(),
            "--unknown".into(),
            "x".into(),
        ],
        vec![
            "search".into(),
            "--model".into(),
            model.display().to_string(),
            "--model".into(),
            model.display().to_string(),
            "--config".into(),
            config.display().to_string(),
        ],
        vec!["verify".into()],
        vec![
            "verify".into(),
            "--model".into(),
            model.display().to_string(),
        ],
    ];

    for args in cases {
        let output = sandbox.command().args(&args).output().expect("run command");
        assert_eq!(output.status.code(), Some(2), "args {args:?}");
        assert!(output.stdout.is_empty(), "no partial output for {args:?}");
        assert!(
            String::from_utf8_lossy(&output.stderr).contains("argument:"),
            "expected an argument category for {args:?}"
        );
    }
}

// Requirements 8, 16 and 18: unreadable and malformed inputs are categorized I/O
// and document errors, and no record is written.
#[test]
fn input_errors_are_categorized_and_write_no_record() {
    let sandbox = Sandbox::new();
    let model = sandbox.write("model.json", MODEL);
    let config = sandbox.write("config.json", CONFIG);
    let malformed = sandbox.write("malformed.json", "{ not json");
    // A version-1 search configuration is rejected rather than migrated.
    let old_version = sandbox.write(
        "v1.json",
        &CONFIG.replacen(r#""schema_version": 2"#, r#""schema_version": 1"#, 1),
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
                old_version.to_str().unwrap(),
            ],
            "document:",
        ),
    ] {
        let output = sandbox
            .command()
            .arg("search")
            .args(&args)
            .output()
            .expect("run search");
        assert_eq!(output.status.code(), Some(2), "args {args:?}");
        assert!(output.stdout.is_empty(), "no record for {args:?}");
        let stderr = String::from_utf8_lossy(&output.stderr);
        assert!(
            stderr.contains(expected),
            "expected {expected} for {args:?}, found {stderr}"
        );
    }
}

// Requirements 1 and 3: verify refuses a record whose own or nested version is
// wrong, and one missing provenance, before running anything.
#[test]
fn verify_refuses_malformed_records() {
    if !native_available() {
        return;
    }
    let sandbox = Sandbox::new();
    let model = sandbox.write("model.json", MODEL);
    let config = sandbox.write("config.json", CONFIG);
    let (_, record) = sandbox.search(&model, &config);
    let text = record.to_string();

    for (name, mutated) in [
        (
            "outer version",
            text.replacen(r#""schema_version":1"#, r#""schema_version":7"#, 1),
        ),
        (
            "nested version",
            text.replace(r#""schema_version":2"#, r#""schema_version":3"#),
        ),
        ("missing provenance", {
            let mut stripped = record.clone();
            stripped
                .as_object_mut()
                .expect("object")
                .remove("toolchain");
            stripped.to_string()
        }),
        (
            "unknown field",
            text.replacen(r#"{"#, r#"{"unexpected":true,"#, 1),
        ),
    ] {
        let path = sandbox.write("bad.json", &mutated);
        let output = sandbox
            .command()
            .arg("verify")
            .arg("--record")
            .arg(&path)
            .arg("--model")
            .arg(&model)
            .output()
            .expect("run verify");
        assert_eq!(output.status.code(), Some(2), "{name}");
        assert!(output.stdout.is_empty(), "{name}: no verdict");
        assert!(
            String::from_utf8_lossy(&output.stderr).contains("document:"),
            "{name} must be a document failure"
        );
    }
}

// The environment comparison explains a divergence without deciding it: a record
// from another build still verifies when its search agrees, and a divergence
// gains a note naming what else changed.
#[test]
fn an_environment_difference_explains_but_does_not_decide() {
    if !native_available() {
        return;
    }
    let sandbox = Sandbox::new();
    let model = sandbox.write("model.json", MODEL);
    let config = sandbox.write("config.json", CONFIG);
    let (_, record) = sandbox.search(&model, &config);

    // A record naming another revision and compiler, with its search untouched.
    let mut foreign = record.clone();
    foreign["revision"] = serde_json::json!("f".repeat(40));
    foreign["toolchain"]["rustc"] = serde_json::json!("rustc 1.0.0 (ancient)");
    let path = sandbox.write("foreign.json", &foreign.to_string());

    let output = sandbox
        .command()
        .arg("verify")
        .arg("--record")
        .arg(&path)
        .arg("--model")
        .arg(&model)
        .output()
        .expect("run verify");
    // Agreement is unchanged: the environment is not a compared field.
    assert_eq!(
        output.status.code(),
        Some(0),
        "a different build must not fail verification: {}",
        String::from_utf8_lossy(&output.stderr)
    );
    let verdict: serde_json::Value = serde_json::from_slice(&output.stdout).expect("json verdict");
    assert_eq!(verdict["agreement"], true);
    // But it is reported, so agreement despite a different build is visible.
    assert_eq!(verdict["environment_differs"], true);
    let notes = verdict["environment"].as_array().expect("environment");
    assert!(
        notes.iter().any(|note| {
            note.as_str()
                .is_some_and(|text| text.contains("source revision differs"))
        }),
        "the changed revision must be named: {notes:?}"
    );

    // A divergence in the same record carries the note alongside the field.
    let mut diverging = foreign.clone();
    diverging["search"]["nodes_explored"] = serde_json::json!(4242);
    let path = sandbox.write("diverging.json", &diverging.to_string());
    let output = sandbox
        .command()
        .arg("verify")
        .arg("--record")
        .arg(&path)
        .arg("--model")
        .arg(&model)
        .output()
        .expect("run verify");
    assert_eq!(output.status.code(), Some(2));
    let stderr = String::from_utf8_lossy(&output.stderr);
    assert!(stderr.contains("nodes_explored"), "found {stderr}");
    assert!(
        stderr.contains("note:"),
        "the note must accompany it: {stderr}"
    );
}
