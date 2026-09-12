//! Conformance suite CLI contracts mapped to SPEC-0009 requirement numbers.
//!
//! The suite is what a promoted entry cites, so a suite nothing exercises would
//! make promotion a claim about an unrun program. Requirement 24 exists because a
//! conformance record can pass for the wrong reason — the extension was never
//! consulted — and that is precisely the failure mode an untested suite hides.
//!
//! The load-bearing case here is byte equality. `examples/conformance-record-v1.json`
//! is not a shape: `examples/extension-registry-v1.json` promotes `flow-shop-neh`
//! by citing that file's SHA-256, and resolution refuses the entry when the bytes
//! do not match. Regenerating the record through `optimizer registry check` and
//! comparing it to the committed bytes therefore establishes two things at once,
//! that the suite runs and that the committed promotion evidence is reproducible
//! rather than hand-written.

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
            "ai-optimizer-registry-{}-{}",
            std::process::id(),
            COUNTER.fetch_add(1, Ordering::SeqCst)
        ));
        std::fs::create_dir_all(&path).expect("sandbox");
        Self { path }
    }

    fn at(&self, name: &str) -> PathBuf {
        self.path.join(name)
    }

    /// A command rooted at the repository, so the committed examples resolve.
    fn command(&self) -> Command {
        let mut command = Command::new(env!("CARGO_BIN_EXE_optimizer"));
        command.current_dir(root());
        command
    }
}

impl Drop for Sandbox {
    fn drop(&mut self) {
        std::fs::remove_dir_all(&self.path).ok();
    }
}

/// The repository root, which is where the committed examples live.
fn root() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR")).join("../..")
}

/// Skip a native-only test loudly rather than reporting false coverage.
///
/// The suite runs the real executive over the pinned relaxation backend, and the
/// record it writes carries that backend's own reported version, so without the
/// library there is nothing to compare against the committed bytes.
fn require_native(test: &str) -> bool {
    if native_available() {
        return true;
    }
    eprintln!("SKIP {test}: HiGHS not provisioned; run bash tools/setup_highs.sh");
    false
}

/// Whether the built binary links the pinned library.
///
/// This probes the binary rather than calling `optimizer_highs::is_native()`,
/// because this test's own feature flags do not determine the binary's. The run
/// surface and scheduling suites establish the same pattern for the same reason.
fn native_available() -> bool {
    let sandbox = Sandbox::new();
    let output = sandbox
        .command()
        .args([
            "registry",
            "check",
            "--registry",
            "examples/extension-registry-v1.json",
            "--extension",
            "flow-shop-neh",
            "--instance",
            "examples/flow-shop-v1.json",
        ])
        .output()
        .expect("run registry check");
    !String::from_utf8_lossy(&output.stderr).contains("not provisioned")
}

/// Run `registry check` for one identity and return its exit code and record.
fn check(sandbox: &Sandbox, extension: &str, output: &PathBuf) -> (Option<i32>, serde_json::Value) {
    let completed = sandbox
        .command()
        .args([
            "registry",
            "check",
            "--registry",
            "examples/extension-registry-v1.json",
            "--extension",
            extension,
            "--instance",
            "examples/flow-shop-v1.json",
            "--output",
        ])
        .arg(output)
        .output()
        .expect("run registry check");
    let written = std::fs::read(output).unwrap_or_else(|error| {
        panic!(
            "expected a record at {}, found {error}: {}",
            output.display(),
            String::from_utf8_lossy(&completed.stderr)
        )
    });
    let record = serde_json::from_slice(&written).expect("the record parses");
    (completed.status.code(), record)
}

/// Requirements 23-25: the suite runs, and the committed evidence reproduces.
#[test]
fn conformance_reproduces_the_committed_record_byte_for_byte() {
    if !require_native("conformance_reproduces_the_committed_record_byte_for_byte") {
        return;
    }
    let sandbox = Sandbox::new();
    let output = sandbox.at("conformance.json");
    let (code, record) = check(&sandbox, "flow-shop-neh", &output);
    assert_eq!(code, Some(0), "an honest producer conforms");

    // Requirement 24 first, and deliberately before any claim about effect: a
    // record reporting zero invocations would mean the suite concluded invariance
    // about an extension the host never consulted.
    let invoked = record["checks"]
        .as_array()
        .expect("checks is an array")
        .iter()
        .find(|check| check["name"] == "invoked")
        .expect("the invoked check is recorded");
    assert_eq!(invoked["passed"], true, "the producer must be consulted");
    assert!(
        invoked["detail"]
            .as_str()
            .expect("detail is text")
            .starts_with("6 invocations"),
        "the producer was consulted once per grid model, found {}",
        invoked["detail"]
    );

    // Requirement 25: the grid size is recorded so it cannot silently shrink.
    assert_eq!(
        record["grid_size"], 6,
        "the conformance grid must stay fixed"
    );
    assert_eq!(record["outcome"], true);
    assert_eq!(record["extension_id"], "flow-shop-neh");
    assert_eq!(record["host_contract_version"], 1);
    assert_ne!(
        record["backend_version"], "unavailable",
        "a native run records the backend's own reported version"
    );

    // The committed record is promotion evidence cited by SHA-256, so equality
    // here is what establishes that the evidence was produced rather than written.
    let committed = std::fs::read(root().join("examples/conformance-record-v1.json"))
        .expect("the committed conformance record exists");
    let produced = std::fs::read(&output).expect("the produced record exists");
    assert_eq!(
        String::from_utf8_lossy(&produced),
        String::from_utf8_lossy(&committed),
        "regenerating the committed conformance record must reproduce it exactly; \
         if the suite changed, the record and the registry's recorded checksum \
         must be regenerated with it"
    );
}

/// Requirement 23: a producer whose every proposal is refused still conforms.
///
/// This is the case the invariance claim is actually about. An accepted proposal
/// legitimately prunes more by bound, so a producer that changes nothing a search
/// concludes while having every proposal refused is the cleanest evidence that the
/// suite compares conclusions rather than effort.
#[test]
fn a_producer_whose_proposals_are_all_refused_conforms() {
    if !require_native("a_producer_whose_proposals_are_all_refused_conforms") {
        return;
    }
    let sandbox = Sandbox::new();
    let output = sandbox.at("refused.json");
    let (code, record) = check(&sandbox, "flow-shop-refused", &output);
    assert_eq!(code, Some(0), "a refused producer changes no conclusion");
    assert_eq!(record["extension_id"], "flow-shop-refused");
    assert_eq!(record["grid_size"], 6);
    assert_eq!(record["outcome"], true);

    let checks = record["checks"].as_array().expect("checks is an array");
    let named = |name: &str| {
        checks
            .iter()
            .find(|check| check["name"] == name)
            .unwrap_or_else(|| panic!("the {name} check is recorded"))
            .clone()
    };
    assert_eq!(named("resolves")["passed"], true);
    assert_eq!(
        named("invoked")["passed"],
        true,
        "the refusal evidence is worthless if the producer was never consulted"
    );
    assert_eq!(named("conclusions_invariant")["passed"], true);
}

/// Requirement 25: every check is named, and the three the suite defines are present.
///
/// Asserted against the record's own list rather than against prose, so a check
/// that stops being recorded fails here instead of quietly leaving the evidence.
#[test]
fn a_conformance_record_names_every_check_it_ran() {
    if !require_native("a_conformance_record_names_every_check_it_ran") {
        return;
    }
    let sandbox = Sandbox::new();
    let output = sandbox.at("named.json");
    let (_, record) = check(&sandbox, "flow-shop-neh", &output);
    let names: Vec<&str> = record["checks"]
        .as_array()
        .expect("checks is an array")
        .iter()
        .map(|check| check["name"].as_str().expect("a check name is text"))
        .collect();
    assert_eq!(names, ["resolves", "invoked", "conclusions_invariant"]);
}

/// Requirement 27: a conformance record carries nothing readable as a measurement.
#[test]
fn a_conformance_record_records_no_timing() {
    if !require_native("a_conformance_record_records_no_timing") {
        return;
    }
    let sandbox = Sandbox::new();
    let output = sandbox.at("timing.json");
    let (_, record) = check(&sandbox, "flow-shop-neh", &output);
    let object = record.as_object().expect("a record is an object");
    for forbidden in ["elapsed_ms", "elapsed_ns", "duration", "timing", "samples"] {
        assert!(
            !object.contains_key(forbidden),
            "a conformance record must not carry {forbidden}: a duration here \
             would be read as a performance result"
        );
    }
}

/// An identity the registry does not record has no conformance result to report.
#[test]
fn check_refuses_an_identity_the_registry_does_not_record() {
    let sandbox = Sandbox::new();
    let completed = sandbox
        .command()
        .args([
            "registry",
            "check",
            "--registry",
            "examples/extension-registry-v1.json",
            "--extension",
            "not-recorded",
        ])
        .output()
        .expect("run registry check");
    assert_eq!(completed.status.code(), Some(2));
    let stderr = String::from_utf8_lossy(&completed.stderr);
    assert!(
        stderr.contains("unsupported:") && stderr.contains("not-recorded"),
        "the refusal must name the identity, found {stderr}"
    );
}

/// Requirement 18's rule that there is no implicit registry applies here too.
#[test]
fn check_requires_an_explicitly_named_registry() {
    let sandbox = Sandbox::new();
    let completed = sandbox
        .command()
        .args(["registry", "check", "--extension", "flow-shop-neh"])
        .output()
        .expect("run registry check");
    assert_eq!(completed.status.code(), Some(2));
    assert!(
        String::from_utf8_lossy(&completed.stderr).contains("--registry is required"),
        "there is deliberately no default registry location"
    );
}

/// Requirement 8: an entry needing an instance is refused without one.
///
/// The suite builds its own models but cannot invent a caller's auxiliary input,
/// so this refusal arrives from resolution before any search runs.
#[test]
fn check_refuses_an_entry_whose_data_requirement_is_unmet() {
    let sandbox = Sandbox::new();
    let completed = sandbox
        .command()
        .args([
            "registry",
            "check",
            "--registry",
            "examples/extension-registry-v1.json",
            "--extension",
            "flow-shop-neh",
        ])
        .output()
        .expect("run registry check");
    assert_eq!(completed.status.code(), Some(2));
    assert!(
        String::from_utf8_lossy(&completed.stderr).contains("unsupported:"),
        "an unmet data requirement is an unsupported failure"
    );
}
