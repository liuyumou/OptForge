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
  "schema_version": 3,
  "seed": 17,
  "node_limit": 50000,
  "time_limit_ms": 120000,
  "open_node_limit": 50000,
  "improvement_tolerance": 1e-9,
  "device": "cpu",
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
  "schema_version": 3,
  "seed": 17,
  "node_limit": 50000,
  "time_limit_ms": 120000,
  "open_node_limit": 50000,
  "improvement_tolerance": 1e-9,
  "device": "cpu",
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

/// A registry recording the NEH producer exactly as it declares itself.
///
/// The version, category, host contract version, problem class, determinism and
/// limits all match `SchedulingProducer`'s own declaration, because resolution
/// refuses a mismatch. `data_requirement` is `flow_shop_instance` because the
/// producer is built from an instance and cannot be constructed from a model.
const REGISTRY: &str = r#"{
  "schema_version": 1,
  "registry_id": "schedule-cli-fixture",
  "entries": [
    {
      "schema_version": 1,
      "extension_id": "flow-shop-neh",
      "version": "0.1.0",
      "license": "MIT",
      "category": "candidate_producer",
      "authority_basis": "propose_validated_candidate",
      "host_contract_version": 1,
      "problem_classes": ["discrete"],
      "deterministic": true,
      "limits": {"max_invocations": 1, "max_proposals": 2},
      "data_requirement": "flow_shop_instance",
      "hardware_requirement": "cpu",
      "requires": [],
      "conflicts_with": [],
      "promotion": {"state": "experimental"}
    }
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

/// Requirement 18 and SPEC-0009 requirement 5: a configuration naming an extension
/// the registry does not record is refused, naming it.
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
    let registry = sandbox.write("registry.json", REGISTRY);
    let output = sandbox
        .command()
        .args(["schedule", "solve", "--instance"])
        .arg(&instance)
        .arg("--config")
        .arg(&config)
        .arg("--registry")
        .arg(&registry)
        .arg("--allow-experimental")
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

/// SPEC-0009 requirement 18: a non-empty policy with no registry is refused, and the
/// diagnostic says what to do about it.
///
/// There is deliberately no default registry location, so this refusal is the only
/// thing standing between a caller and a search whose extensions depend on the
/// filesystem rather than on the command.
#[test]
fn solve_refuses_an_extension_policy_without_a_registry() {
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
    let config = sandbox.write("config.json", CONFIG_WITH_PRODUCER);
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
        stderr.contains("unsupported") && stderr.contains("--registry"),
        "the refusal must name the remedy, got {stderr}"
    );
}

/// SPEC-0009 requirement 12: an experimental entry needs explicit permission, and
/// the record it produces says so.
#[test]
fn an_experimental_entry_needs_permission_and_is_recorded() {
    if !require_native("an_experimental_entry_needs_permission_and_is_recorded") {
        return;
    }
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
    let config = sandbox.write("config.json", CONFIG_WITH_PRODUCER);
    let registry = sandbox.write("registry.json", REGISTRY);

    // Without permission the entry is refused before any search runs.
    let refused = sandbox
        .command()
        .args(["schedule", "solve", "--instance"])
        .arg(&instance)
        .arg("--config")
        .arg(&config)
        .arg("--registry")
        .arg(&registry)
        .output()
        .expect("run solve");
    assert_eq!(refused.status.code(), Some(2));
    let stderr = String::from_utf8_lossy(&refused.stderr);
    assert!(
        stderr.contains("--allow-experimental"),
        "the refusal must name the remedy, got {stderr}"
    );

    // With permission it runs, and the record carries the warning.
    let record = sandbox.at("run.json");
    let status = sandbox
        .command()
        .args(["schedule", "solve", "--instance"])
        .arg(&instance)
        .arg("--config")
        .arg(&config)
        .arg("--registry")
        .arg(&registry)
        .arg("--allow-experimental")
        .arg("--output")
        .arg(&record)
        .status()
        .expect("solve");
    assert_eq!(status.code(), Some(0));
    let written: serde_json::Value =
        serde_json::from_slice(&std::fs::read(&record).expect("read")).expect("parse");
    let warnings = written["warnings"]
        .as_array()
        .expect("warnings is an array");
    assert_eq!(warnings.len(), 1, "found {warnings:?}");
    assert!(
        warnings[0]
            .as_str()
            .expect("warning text")
            .contains("flow-shop-neh"),
        "the warning must name the extension: {warnings:?}"
    );
}

/// SPEC-0009 requirement 19: a scheduling record produced **with** the NEH producer
/// re-executes and verifies through a registry.
///
/// This is the property that did not exist before C8, and the reason the registry is
/// the seam two known-failures pointed at. Before SPEC-0009 this same record was
/// refused as unsupported, because re-execution loaded no extension and the counters
/// would have differed for that reason alone.
///
/// Both directions are asserted: the record verifies with the registry, and is still
/// refused without one, so the pass is not the only thing checked.
#[test]
fn a_producer_backed_record_verifies_through_a_registry() {
    if !require_native("a_producer_backed_record_verifies_through_a_registry") {
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
    let registry = sandbox.write("registry.json", REGISTRY);
    let record = sandbox.at("run.json");
    let model = sandbox.at("model.json");
    let status = sandbox
        .command()
        .args(["schedule", "solve", "--instance"])
        .arg(&instance)
        .arg("--config")
        .arg(&config)
        .arg("--registry")
        .arg(&registry)
        .arg("--allow-experimental")
        .arg("--output")
        .arg(&record)
        .arg("--output-model")
        .arg(&model)
        .status()
        .expect("solve");
    assert_eq!(status.code(), Some(0), "the producer run itself succeeds");

    // The producer was registered and its proposals were accepted. Asserting this
    // first is what stops the verification below from passing because the producer
    // was never actually consulted.
    let written: serde_json::Value =
        serde_json::from_slice(&std::fs::read(&record).expect("read")).expect("parse");
    assert_eq!(written["search"]["outcome"], "proven_optimal");
    let summary = &written["search"]["extensions"][0];
    assert_eq!(summary["extension_id"], "flow-shop-neh");
    assert_eq!(summary["registered"], true);
    assert!(summary["accepted"].as_u64().expect("accepted count") > 0);

    // The headline: the record re-executes and agrees.
    let output = sandbox
        .command()
        .arg("verify")
        .arg("--record")
        .arg(&record)
        .arg("--model")
        .arg(&model)
        .arg("--instance")
        .arg(&instance)
        .arg("--registry")
        .arg(&registry)
        .arg("--allow-experimental")
        .output()
        .expect("run verify");
    let stderr = String::from_utf8_lossy(&output.stderr);
    assert_eq!(
        output.status.code(),
        Some(0),
        "a producer-backed record must verify: {stderr}"
    );
    let verdict: serde_json::Value =
        serde_json::from_slice(&output.stdout).expect("verdict parses");
    assert_eq!(verdict["agreement"], true);
    assert_eq!(verdict["outcome"], "proven_optimal");
    assert_eq!(verdict["extensions"][0], "flow-shop-neh");
    // Requirement 21: agreement is decided by the ten compared fields alone, and a
    // registry-backed run that agrees reports no extension difference.
    assert_eq!(verdict["extensions_differ"], false);
    assert_eq!(
        verdict["compared"].as_array().expect("compared list").len(),
        10,
        "the compared field list must be unchanged by C8"
    );

    // Without a registry the same record is still refused, because nothing can
    // reconstruct the producer it names. The refusal is unsupported rather than
    // divergence: re-executing without the producer would reproduce a search the
    // record does not describe.
    let refused = sandbox
        .command()
        .arg("verify")
        .arg("--record")
        .arg(&record)
        .arg("--model")
        .arg(&model)
        .output()
        .expect("run verify");
    assert_eq!(refused.status.code(), Some(2));
    let stderr = String::from_utf8_lossy(&refused.stderr);
    assert!(
        stderr.contains("unsupported") && stderr.contains("--registry"),
        "expected an unsupported refusal naming the remedy, got {stderr}"
    );
    assert!(
        !stderr.contains("divergence"),
        "a missing registry must not be reported as divergence: {stderr}"
    );
}

/// SPEC-0009 requirement 20: a registry resolving a different version is refused as
/// unsupported rather than reported as divergence.
///
/// The distinction matters. Re-executing against another version would reproduce a
/// search the record does not describe, so its counters would differ for that reason
/// alone, and calling that divergence would blame the record.
#[test]
fn verification_refuses_a_registry_naming_another_version() {
    if !require_native("verification_refuses_a_registry_naming_another_version") {
        return;
    }
    let sandbox = Sandbox::new();
    let config = sandbox.write("config.json", CONFIG_WITH_PRODUCER);
    let registry = sandbox.write("registry.json", REGISTRY);
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
    let record = sandbox.at("run.json");
    let model = sandbox.at("model.json");
    let status = sandbox
        .command()
        .args(["schedule", "solve", "--instance"])
        .arg(&instance)
        .arg("--config")
        .arg(&config)
        .arg("--registry")
        .arg(&registry)
        .arg("--allow-experimental")
        .arg("--output")
        .arg(&record)
        .arg("--output-model")
        .arg(&model)
        .status()
        .expect("solve");
    assert_eq!(status.code(), Some(0));

    // A registry claiming a version the extension does not report is refused at
    // resolution, before the version comparison against the record is reached.
    let restamped = sandbox.write(
        "restamped-registry.json",
        &REGISTRY.replace(r#""version": "0.1.0""#, r#""version": "9.9.9""#),
    );
    let output = sandbox
        .command()
        .arg("verify")
        .arg("--record")
        .arg(&record)
        .arg("--model")
        .arg(&model)
        .arg("--instance")
        .arg(&instance)
        .arg("--registry")
        .arg(&restamped)
        .arg("--allow-experimental")
        .output()
        .expect("run verify");
    assert_eq!(output.status.code(), Some(2));
    let stderr = String::from_utf8_lossy(&output.stderr);
    assert!(
        stderr.contains("unsupported") && stderr.contains("9.9.9"),
        "expected an unsupported refusal naming the version, got {stderr}"
    );
    assert!(
        !stderr.contains("divergence"),
        "a version mismatch must not be reported as divergence: {stderr}"
    );
}

/// Requirement 20: the record-versus-resolved version comparison, reached.
///
/// The test above cannot reach it, and says so: restamping the *registry* is
/// refused by the declaration check first, because the extension still reports
/// the version it always did. The comparison requirement 20 actually describes
/// comes from the other direction — the record names a version the current build
/// no longer declares, which is what happens when a record outlives the build
/// that produced it and the extension's own version has since moved.
///
/// Editing the summary in the record simulates exactly that, the same way the run
/// surface contracts mutate a record to exercise divergence. Without this, the
/// branch at `search.rs` has no test and its reachability is a matter of opinion.
#[test]
fn verification_refuses_a_record_naming_another_extension_version() {
    if !require_native("verification_refuses_a_record_naming_another_extension_version") {
        return;
    }
    let sandbox = Sandbox::new();
    let config = sandbox.write("config.json", CONFIG_WITH_PRODUCER);
    let registry = sandbox.write("registry.json", REGISTRY);
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
    let record_path = sandbox.at("run.json");
    let model = sandbox.at("model.json");
    let status = sandbox
        .command()
        .args(["schedule", "solve", "--instance"])
        .arg(&instance)
        .arg("--config")
        .arg(&config)
        .arg("--registry")
        .arg(&registry)
        .arg("--allow-experimental")
        .arg("--output")
        .arg(&record_path)
        .arg("--output-model")
        .arg(&model)
        .status()
        .expect("solve");
    assert_eq!(status.code(), Some(0));

    // The record claims a version the build does not declare. The registry is
    // left alone, so resolution succeeds and the comparison is actually reached.
    let mut record: serde_json::Value =
        serde_json::from_slice(&std::fs::read(&record_path).expect("read")).expect("parse");
    let summary = &mut record["search"]["extensions"][0];
    assert_eq!(summary["extension_id"], "flow-shop-neh");
    assert_eq!(
        summary["registered"], true,
        "an unregistered summary is skipped"
    );
    assert_eq!(summary["version"], "0.1.0");
    summary["version"] = serde_json::json!("9.9.9");
    let restated = sandbox.write("restated.json", &record.to_string());

    let output = sandbox
        .command()
        .arg("verify")
        .arg("--record")
        .arg(&restated)
        .arg("--model")
        .arg(&model)
        .arg("--instance")
        .arg(&instance)
        .arg("--registry")
        .arg(&registry)
        .arg("--allow-experimental")
        .output()
        .expect("run verify");
    assert_eq!(output.status.code(), Some(2));
    let stderr = String::from_utf8_lossy(&output.stderr);
    assert!(
        stderr.contains("unsupported:") && stderr.contains("9.9.9") && stderr.contains("0.1.0"),
        "the refusal must name both versions, got {stderr}"
    );
    assert!(
        !stderr.contains("divergence"),
        "a version mismatch must not be reported as divergence: {stderr}"
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
