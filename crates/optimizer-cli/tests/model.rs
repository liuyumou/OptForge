//! Process-level acceptance for SPEC-0001, using only CPU work.

use std::fs;
use std::path::{Path, PathBuf};
use std::process::{Command, Output};
use std::sync::atomic::{AtomicUsize, Ordering};

use serde_json::{Value, json};

static NEXT: AtomicUsize = AtomicUsize::new(0);

struct Sandbox(PathBuf);

impl Sandbox {
    fn new() -> Self {
        let path = std::env::temp_dir().join(format!(
            "optimizer-model-test-{}-{}",
            std::process::id(),
            NEXT.fetch_add(1, Ordering::SeqCst)
        ));
        fs::create_dir(&path).unwrap();
        Self(path)
    }

    fn write(&self, name: &str, bytes: impl AsRef<[u8]>) -> PathBuf {
        let path = self.0.join(name);
        fs::write(&path, bytes).unwrap();
        path
    }
}

impl Drop for Sandbox {
    fn drop(&mut self) {
        fs::remove_dir_all(&self.0).unwrap();
    }
}

fn root() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR")).join("../..")
}

fn run(args: &[&str]) -> Output {
    Command::new(env!("CARGO_BIN_EXE_optimizer"))
        .args(["model", "validate"])
        .args(args)
        .output()
        .unwrap()
}

fn evaluate(model: &Path, candidate: &Path) -> Output {
    Command::new(env!("CARGO_BIN_EXE_optimizer"))
        .args(["model", "validate", "--candidate"])
        .arg(candidate)
        .args(["--relative-tolerance", "0", "--model"])
        .arg(model)
        .args(["--integrality-tolerance", "0", "--absolute-tolerance", "0"])
        .output()
        .unwrap()
}

fn error(output: Output, category: &str) {
    assert_eq!(
        output.status.code(),
        Some(2),
        "{}",
        String::from_utf8_lossy(&output.stdout)
    );
    assert!(output.stdout.is_empty());
    assert!(
        String::from_utf8_lossy(&output.stderr).contains(category),
        "{}",
        String::from_utf8_lossy(&output.stderr)
    );
}

#[test]
fn structure_and_candidate_commands_produce_versioned_reports_and_exit_codes() {
    let model = root().join("examples/model-v1.json");
    let candidate = root().join("examples/candidate-v1.json");
    let output = run(&["--model", model.to_str().unwrap()]);
    assert!(output.status.success());
    assert!(output.stderr.is_empty());
    let report: Value = serde_json::from_slice(&output.stdout).unwrap();
    assert_eq!(
        report,
        json!({"schema_version":1,"model_id":"tiny-mixed","status":"structurally_valid"})
    );
    let output = evaluate(&model, &candidate);
    assert!(output.status.success());
    assert!(output.stderr.is_empty());
    let report: Value = serde_json::from_slice(&output.stdout).unwrap();
    assert_eq!(report["schema_version"], 1);
    assert_eq!(report["feasible"], true);
    assert_eq!(report["objective"], 3.5);
    assert_eq!(report["constraints"][0]["activity"], 2.0);
    assert_eq!(
        report["tolerances"],
        json!({"absolute":0.0,"relative":0.0,"integrality":0.0})
    );
    let sandbox = Sandbox::new();
    let mut c: Value = serde_json::from_slice(&fs::read(candidate).unwrap()).unwrap();
    c["values"][0]["value"] = json!(0.5);
    let path = sandbox.write("infeasible.json", serde_json::to_vec(&c).unwrap());
    let output = evaluate(&model, &path);
    assert_eq!(output.status.code(), Some(1));
    assert!(output.stderr.is_empty());
    let report: Value = serde_json::from_slice(&output.stdout).unwrap();
    assert_eq!(report["feasible"], false);
    assert_eq!(report["objective"], 2.5);
    assert_eq!(report["variables"][0]["domain"]["violation"], 0.5);
    assert_eq!(report["constraints"][0]["lower"]["violation"], 0.5);
    assert!(report.get("status").is_none());
}

#[test]
fn incomplete_and_unknown_model_commands_are_argument_errors() {
    for args in [
        vec!["model"],
        vec!["model", "unknown"],
        vec!["model", "--model", "x"],
    ] {
        error(
            Command::new(env!("CARGO_BIN_EXE_optimizer"))
                .args(args)
                .output()
                .unwrap(),
            "argument:",
        );
    }
}

#[test]
fn cli_rejects_missing_duplicate_unknown_and_invalid_tolerance_flags() {
    let path = root().join("examples/model-v1.json");
    let model = path.to_str().unwrap();
    for args in [
        vec![],
        vec!["--model"],
        vec!["--unknown", "x"],
        vec!["--model", model, "--model", model],
        vec!["--model", model, "--absolute-tolerance", "0"],
        vec!["--model", model, "--candidate", "x"],
        vec![
            "--model",
            model,
            "--candidate",
            "x",
            "--absolute-tolerance",
            "garbage",
        ],
        vec!["--model", model, "--candidate", "x", "--candidate", "y"],
        vec![
            "--model",
            model,
            "--relative-tolerance",
            "0",
            "--relative-tolerance",
            "1",
        ],
    ] {
        error(run(&args), "argument:");
    }
    for (absolute, relative, integrality) in [
        ("NaN", "0", "0"),
        ("0", "inf", "0"),
        ("-1", "0", "0"),
        ("0", "0", "0.5"),
    ] {
        error(
            run(&[
                "--model",
                model,
                "--candidate",
                "x",
                "--absolute-tolerance",
                absolute,
                "--relative-tolerance",
                relative,
                "--integrality-tolerance",
                integrality,
            ]),
            "tolerance:",
        );
    }
}

#[test]
fn input_errors_are_categorized_and_never_write_partial_reports() {
    let sandbox = Sandbox::new();
    let model = root().join("examples/model-v1.json");
    let candidate = root().join("examples/candidate-v1.json");
    let missing = sandbox.0.join("missing");
    error(run(&["--model", missing.to_str().unwrap()]), "io:");
    error(evaluate(&model, &missing), "io:");
    let malformed = sandbox.write("malformed.json", b"{broken}");
    error(run(&["--model", malformed.to_str().unwrap()]), "document:");
    error(evaluate(&model, &malformed), "document:");
    let mut d: Value = serde_json::from_slice(&fs::read(&model).unwrap()).unwrap();
    d["variables"][0]["lower"] = json!({"kind":"finite","value":2.0});
    let invalid = sandbox.write("invalid-model.json", serde_json::to_vec(&d).unwrap());
    error(run(&["--model", invalid.to_str().unwrap()]), "structural:");
    let mut c: Value = serde_json::from_slice(&fs::read(&candidate).unwrap()).unwrap();
    c["model_id"] = json!("other");
    let invalid = sandbox.write("invalid-candidate.json", serde_json::to_vec(&c).unwrap());
    error(evaluate(&model, &invalid), "candidate:");
    let overflow = root().join("tests/fixtures/models/overflow-prone.json");
    let c = sandbox.write("overflow-candidate.json", serde_json::to_vec(&json!({"schema_version":1,"model_id":"overflow-prone","values":[{"variable_id":0,"value":2.0}]})).unwrap());
    error(evaluate(&overflow, &c), "numerical:");
}

#[test]
#[cfg(unix)]
fn native_paths_preserve_non_utf8_bytes() {
    use std::ffi::OsString;
    use std::os::unix::ffi::OsStringExt;

    let sandbox = Sandbox::new();
    let model = sandbox
        .0
        .join(OsString::from_vec(b"model-\xff.json".to_vec()));
    let candidate = sandbox
        .0
        .join(OsString::from_vec(b"candidate-\xfe.json".to_vec()));
    fs::copy(root().join("examples/model-v1.json"), &model).unwrap();
    fs::copy(root().join("examples/candidate-v1.json"), &candidate).unwrap();
    let structure = || {
        Command::new(env!("CARGO_BIN_EXE_optimizer"))
            .args(["model", "validate", "--model"])
            .arg(&model)
            .output()
            .unwrap()
    };
    let output = structure();
    assert!(
        output.status.success(),
        "{}",
        String::from_utf8_lossy(&output.stderr)
    );
    let report: Value = serde_json::from_slice(&output.stdout).unwrap();
    assert_eq!(report["model_id"], "tiny-mixed");
    let output = evaluate(&model, &candidate);
    assert!(
        output.status.success(),
        "{}",
        String::from_utf8_lossy(&output.stderr)
    );
    let report: Value = serde_json::from_slice(&output.stdout).unwrap();
    assert_eq!(report["feasible"], true);
    assert_eq!(report["objective"], 3.5);
    fs::remove_file(&candidate).unwrap();
    error(evaluate(&model, &candidate), "io:");
    fs::remove_file(&model).unwrap();
    error(structure(), "io:");
}

#[test]
#[cfg(unix)]
fn non_utf8_command_flag_and_tolerance_text_is_an_argument_error() {
    use std::ffi::OsString;
    use std::os::unix::ffi::OsStringExt;

    for index in [0, 1, 2, 4, 6, 7, 8, 9, 10, 11] {
        let mut args: Vec<OsString> = [
            "model",
            "validate",
            "--model",
            "examples/model-v1.json",
            "--candidate",
            "examples/candidate-v1.json",
            "--absolute-tolerance",
            "0",
            "--relative-tolerance",
            "0",
            "--integrality-tolerance",
            "0",
        ]
        .into_iter()
        .map(OsString::from)
        .collect();
        args[index] = OsString::from_vec(vec![0xff]);
        error(
            Command::new(env!("CARGO_BIN_EXE_optimizer"))
                .args(args)
                .current_dir(root())
                .output()
                .unwrap(),
            "argument:",
        );
    }
}

#[test]
fn alternate_json_representations_are_document_errors() {
    for fixture in ["positional-model.json", "object-enum-model.json"] {
        let path = root().join("tests/regression").join(fixture);
        error(run(&["--model", path.to_str().unwrap()]), "document:");
    }
}

#[test]
#[cfg(target_os = "linux")]
fn failed_report_output_is_an_io_error_for_both_modes() {
    for candidate_mode in [false, true] {
        for closed_pipe in [false, true] {
            let stdout = if closed_pipe {
                let (reader, writer) = std::io::pipe().unwrap();
                drop(reader);
                std::process::Stdio::from(writer)
            } else {
                std::process::Stdio::from(
                    fs::OpenOptions::new()
                        .write(true)
                        .open("/dev/full")
                        .unwrap(),
                )
            };
            let mut command = Command::new(env!("CARGO_BIN_EXE_optimizer"));
            command
                .args(["model", "validate", "--model"])
                .arg(root().join("examples/model-v1.json"));
            if candidate_mode {
                command
                    .arg("--candidate")
                    .arg(root().join("examples/candidate-v1.json"))
                    .args([
                        "--absolute-tolerance",
                        "0",
                        "--relative-tolerance",
                        "0",
                        "--integrality-tolerance",
                        "0",
                    ]);
            }
            error(command.stdout(stdout).output().unwrap(), "io: stdout:");
        }
    }
}

#[test]
fn file_limits_accept_exact_limit_and_reject_one_byte_over_for_both_inputs() {
    let sandbox = Sandbox::new();
    let mut bytes = fs::read(root().join("examples/model-v1.json")).unwrap();
    bytes.resize(16 * 1024 * 1024, b' ');
    let model = sandbox.write("model.json", &bytes);
    assert!(run(&["--model", model.to_str().unwrap()]).status.success());
    bytes.push(b' ');
    let oversized = sandbox.write("oversized.json", &bytes);
    error(
        run(&["--model", oversized.to_str().unwrap()]),
        "exceeds 16 MiB",
    );
    error(evaluate(&model, &oversized), "exceeds 16 MiB");
    let mut bytes = fs::read(root().join("examples/candidate-v1.json")).unwrap();
    bytes.resize(16 * 1024 * 1024, b' ');
    let candidate = sandbox.write("candidate.json", &bytes);
    assert!(evaluate(&model, &candidate).status.success());
}
