//! Run record contracts mapped to SPEC-0005 requirement numbers.
//!
//! The central assertions here are negative: every field the specification says
//! verification compares must be shown to fail when it alone is mutated, and
//! every provenance field must be shown to be required. A comparison that
//! nominally covers a field while ignoring it would pass a test that only ever
//! checks the agreeing case.

use optimizer_core::{ErrorKind, SOLVE_SCHEMA_VERSION, SolveOptions, Tolerances};
use optimizer_experiment::{
    EXAMPLE_REVISION, Hardware, InputDocument, InputRole, RUN_SCHEMA_VERSION, RunRecord, Toolchain,
};
use optimizer_solver::{SEARCH_SCHEMA_VERSION, SearchOptions, SearchOutcome, SearchRecord};

fn options() -> SearchOptions {
    SearchOptions {
        schema_version: SEARCH_SCHEMA_VERSION,
        seed: 17,
        node_limit: None,
        time_limit_ms: Some(10_000),
        open_node_limit: None,
        improvement_tolerance: 1e-9,
        // These contracts are about search behaviour, which SPEC-0010
        // requirement 26 requires a device not to change. Running them on the
        // CPU is what keeps them a statement about the executive.
        device: optimizer_core::Device::Cpu,
        relaxation: SolveOptions {
            schema_version: SOLVE_SCHEMA_VERSION,
            seed: 17,
            time_limit_ms: Some(10_000),
            iteration_limit: None,
            node_limit: None,
            tolerances: Tolerances {
                absolute: 1e-9,
                relative: 1e-9,
                integrality: 1e-9,
            },
            threads: 1,
        },
        extensions: Vec::new(),
    }
}

fn search() -> SearchRecord {
    SearchRecord {
        schema_version: SEARCH_SCHEMA_VERSION,
        model_id: "contract".to_owned(),
        backend: "relaxation".to_owned(),
        backend_version: "1.11.0".to_owned(),
        outcome: SearchOutcome::ProvenOptimal,
        objective: Some(2.5),
        dual_bound: Some(2.5),
        gap: Some(0.0),
        candidate: None,
        validation: None,
        nodes_explored: 3,
        nodes_pruned_infeasible: 1,
        nodes_pruned_bound: 1,
        open_nodes_remaining: 0,
        relaxations_solved: 3,
        forfeited: false,
        warnings: Vec::new(),
        extensions: Vec::new(),
        elapsed_ms: 12,
        options: options(),
    }
}

fn record() -> RunRecord {
    RunRecord {
        schema_version: RUN_SCHEMA_VERSION,
        record_id: "run-contract".to_owned(),
        revision: "a".repeat(40),
        dirty: false,
        hardware: Hardware {
            os: "Linux (test)".to_owned(),
            cpu: "test CPU".to_owned(),
            logical_cpus: 1,
            gpu_uuid: None,
            gpu_name: None,
            driver: None,
        },
        toolchain: Toolchain {
            rustc: "rustc (test)".to_owned(),
            cargo: "cargo (test)".to_owned(),
        },
        model_fingerprint: "fnv1a64:0123456789abcdef".to_owned(),
        inputs: vec![
            InputDocument {
                role: InputRole::Model,
                path: "model.json".to_owned(),
                sha256: "b".repeat(64),
            },
            InputDocument {
                role: InputRole::Config,
                path: "config.json".to_owned(),
                sha256: "c".repeat(64),
            },
        ],
        search: search(),
        warnings: Vec::new(),
    }
}

// Requirements 1-2: a record round trips with its search record embedded
// verbatim, so nothing is summarized away.
#[test]
fn records_round_trip_with_the_search_embedded_verbatim() {
    let record = record();
    let text = record.to_json().expect("serialize");
    let parsed = RunRecord::from_json(text.as_bytes()).expect("parse");
    assert_eq!(parsed, record);
    assert_eq!(parsed.search, search());
    // The embedded configuration is what makes a repeat possible at all.
    assert_eq!(parsed.search.options.seed, 17);
    assert_eq!(parsed.search.options.relaxation.threads, 1);
}

// Requirement 1: every provenance field is required, and a malformed one is a
// document failure rather than a silently accepted record.
#[test]
fn malformed_provenance_is_refused() {
    let text = record().to_json().expect("serialize");

    for (name, mutated) in [
        (
            "record_id",
            text.replace(r#""record_id": "run-contract""#, r#""record_id": """#),
        ),
        (
            "revision",
            text.replace(
                &format!(r#""revision": "{}""#, "a".repeat(40)),
                r#""revision": "abc""#,
            ),
        ),
        (
            "revision case",
            text.replace(
                &format!(r#""revision": "{}""#, "a".repeat(40)),
                &format!(r#""revision": "{}""#, "A".repeat(40)),
            ),
        ),
        (
            "model_fingerprint",
            text.replace(
                r#""model_fingerprint": "fnv1a64:0123456789abcdef""#,
                r#""model_fingerprint": """#,
            ),
        ),
        (
            "sha256",
            text.replace(
                &format!(r#""sha256": "{}""#, "b".repeat(64)),
                r#""sha256": "short""#,
            ),
        ),
    ] {
        let error =
            RunRecord::from_json(mutated.as_bytes()).expect_err(&format!("{name} must be refused"));
        assert_eq!(error.kind, ErrorKind::Document, "{name}");
    }
}

// Requirement 1: inputs must name exactly one model and one config document, so
// a record cannot omit or duplicate what it consumed.
#[test]
fn inputs_must_name_one_model_and_one_config() {
    let mut record = record();

    record.inputs.remove(1);
    let error = RunRecord::from_json(record.to_json().expect("serialize").as_bytes())
        .expect_err("a missing config input must be refused");
    assert_eq!(error.kind, ErrorKind::Document);
    assert!(error.message.contains("config"), "{}", error.message);

    let mut duplicated = self::record();
    duplicated.inputs[1].role = InputRole::Model;
    let error = RunRecord::from_json(duplicated.to_json().expect("serialize").as_bytes())
        .expect_err("two model inputs must be refused");
    assert_eq!(error.kind, ErrorKind::Document);
    assert!(error.message.contains("model"), "{}", error.message);
}

// Requirement 3: a wrong nested version is rejected on the parse path, not only
// the record's own version.
#[test]
fn nested_document_versions_are_validated_on_parse() {
    let text = record().to_json().expect("serialize");

    // The outer version alone. It is the record's first serialized field, so the
    // first occurrence in the text is the outer one; matching on the value would
    // otherwise hit whichever nested document happens to share it.
    let outer = text.replacen(r#""schema_version": 2"#, r#""schema_version": 9"#, 1);
    let error = RunRecord::from_json(outer.as_bytes()).expect_err("outer version");
    assert_eq!(error.kind, ErrorKind::Document);
    assert!(
        error.message.contains("run schema_version"),
        "{}",
        error.message
    );

    // The embedded search record's version, which the outer check cannot catch.
    // Its configuration carries the same version, so this mutates both; either
    // alone is enough to make the document invalid.
    let nested = text.replace(r#""schema_version": 3"#, r#""schema_version": 1"#);
    let error = RunRecord::from_json(nested.as_bytes()).expect_err("nested version");
    assert_eq!(error.kind, ErrorKind::Document);
    assert!(error.message.contains("search"), "{}", error.message);
}

// Requirement 1: unknown fields, duplicate keys and positional arrays are all
// refused, matching every other document in the workspace.
#[test]
fn strict_object_shapes_are_required() {
    let text = record().to_json().expect("serialize");

    // The record's own field, which is the first one it serializes. A nested
    // document's unknown field would be refused too, but by a different parser.
    let extra = text.replacen(
        r#""schema_version": 2,"#,
        r#""schema_version": 2, "unexpected": true,"#,
        1,
    );
    assert!(
        RunRecord::from_json(extra.as_bytes()).is_err(),
        "unknown field"
    );

    let duplicate = text.replacen(
        r#""record_id": "run-contract","#,
        r#""record_id": "run-contract", "record_id": "other","#,
        1,
    );
    assert!(
        RunRecord::from_json(duplicate.as_bytes()).is_err(),
        "duplicate key"
    );

    assert!(
        RunRecord::from_json(b"[1, 2, 3]").is_err(),
        "a positional array is not a record"
    );
}

// Requirement 19: an absent measurement is omitted rather than serialized null.
#[test]
fn absent_measurements_are_omitted_not_null() {
    let mut record = record();
    record.search.objective = None;
    record.search.dual_bound = None;
    record.search.gap = None;
    record.search.outcome = SearchOutcome::ProvenInfeasible;

    let text = record.to_json().expect("serialize");
    // An absent measurement is omitted entirely. Configuration is different by
    // design: an absent budget is an explicit null meaning unlimited, which is
    // SPEC-0003's convention, so this checks the measurements specifically.
    for measurement in ["objective", "dual_bound", "gap"] {
        assert!(
            !text.contains(&format!("\"{measurement}\"")),
            "{measurement} must be omitted, found it in {text}"
        );
    }
    let parsed = RunRecord::from_json(text.as_bytes()).expect("parse");
    assert_eq!(parsed.search.objective, None);
    // The unlimited budget beside it is still an explicit null.
    assert!(text.contains(r#""node_limit": null"#));
}

// Requirement 11: every compared field is detected when it alone is mutated, so
// none is nominally compared and actually ignored.
#[test]
fn every_compared_field_detects_its_own_divergence() {
    let record = record();
    let mut mutations: Vec<(&str, SearchRecord)> = Vec::new();

    let mut outcome = search();
    outcome.outcome = SearchOutcome::Feasible;
    mutations.push(("outcome", outcome));

    let mut objective = search();
    objective.objective = Some(2.4999);
    mutations.push(("objective", objective));

    let mut dual = search();
    dual.dual_bound = Some(2.0);
    mutations.push(("dual_bound", dual));

    let mut gap = search();
    gap.gap = Some(0.5);
    mutations.push(("gap", gap));

    let mut forfeited = search();
    forfeited.forfeited = true;
    mutations.push(("forfeited", forfeited));

    let mut explored = search();
    explored.nodes_explored += 1;
    mutations.push(("nodes_explored", explored));

    let mut infeasible = search();
    infeasible.nodes_pruned_infeasible += 1;
    mutations.push(("nodes_pruned_infeasible", infeasible));

    let mut bound = search();
    bound.nodes_pruned_bound += 1;
    mutations.push(("nodes_pruned_bound", bound));

    let mut open = search();
    open.open_nodes_remaining += 1;
    mutations.push(("open_nodes_remaining", open));

    let mut relaxations = search();
    relaxations.relaxations_solved += 1;
    mutations.push(("relaxations_solved", relaxations));

    // The list must cover exactly what the specification says it covers.
    let named: Vec<&str> = mutations.iter().map(|(name, _)| *name).collect();
    assert_eq!(named, RunRecord::compared_fields());

    for (field, fresh) in mutations {
        let error = record
            .verify_agreement(&fresh)
            .expect_err(&format!("{field} must diverge"));
        assert_eq!(error.kind, ErrorKind::Numerical, "{field}");
        assert!(
            error.message.starts_with(field),
            "expected {field} to be named, found {}",
            error.message
        );
    }
}

// Requirement 11: an absent measurement and a present one are not the same, in
// either direction.
#[test]
fn presence_of_a_measurement_is_itself_compared() {
    let record = record();

    let mut absent = search();
    absent.objective = None;
    let error = record
        .verify_agreement(&absent)
        .expect_err("a vanished objective diverges");
    assert!(error.message.contains("absent"), "{}", error.message);

    let mut recorded_absent = self::record();
    recorded_absent.search.dual_bound = None;
    let error = recorded_absent
        .verify_agreement(&search())
        .expect_err("a newly appearing bound diverges");
    assert!(error.message.starts_with("dual_bound"), "{}", error.message);
}

// Requirement 12: elapsed time is recorded and never compared, because it
// measures the host rather than the search.
#[test]
fn elapsed_time_alone_is_not_divergence() {
    let record = record();
    let mut fresh = search();
    fresh.elapsed_ms = record.search.elapsed_ms + 5_000;
    record
        .verify_agreement(&fresh)
        .expect("elapsed time must not fail verification");
    assert!(!RunRecord::compared_fields().contains(&"elapsed_ms"));
}

// Requirement 13: agreement cannot clear a forfeited proof claim.
#[test]
fn agreement_does_not_clear_forfeiture() {
    let mut record = record();
    record.search.forfeited = true;
    record.search.outcome = SearchOutcome::Feasible;
    let mut fresh = search();
    fresh.forfeited = true;
    fresh.outcome = SearchOutcome::Feasible;

    record
        .verify_agreement(&fresh)
        .expect("forfeited runs agree");
    // Agreement is about repeatability; the claim itself is unchanged.
    assert!(record.search.forfeited);
    assert!(!record.search.outcome.proves_completion());
}

// Requirement 5: a dirty tree and the example revision each disqualify a record
// as evidence, however well it verifies.
#[test]
fn dirty_and_example_records_are_not_evidence() {
    let clean = record();
    assert!(clean.is_evidence());

    let mut dirty = record();
    dirty.dirty = true;
    assert!(!dirty.is_evidence());

    let mut example = record();
    example.revision = EXAMPLE_REVISION.to_owned();
    assert!(!example.is_evidence());
}

// The environment comparison is diagnostic only: it must never appear among the
// fields that decide agreement, or it would change what agreement means.
#[test]
fn environment_differences_are_diagnostic_not_compared() {
    let record = record();

    // An identical environment reports nothing.
    let same = record.environment_difference("1.11.0", &"a".repeat(40), "rustc (test)");
    assert!(same.is_empty());
    assert!(same.describe().is_empty());

    // A changed library, revision and compiler are each reported, and the
    // backend is named first because it is the one that can change the numbers.
    let changed = record.environment_difference("1.12.0", &"b".repeat(40), "rustc (other)");
    assert!(!changed.is_empty());
    let lines = changed.describe();
    assert_eq!(lines.len(), 3);
    assert!(lines[0].contains("backend library differs"), "{}", lines[0]);
    assert!(lines[0].contains("1.11.0") && lines[0].contains("1.12.0"));
    assert!(lines[1].contains("source revision differs"));
    assert!(lines[2].contains("compiler differs"));

    // None of these names is a compared field, so agreement is unaffected.
    for name in ["backend_version", "revision", "rustc", "toolchain"] {
        assert!(
            !RunRecord::compared_fields().contains(&name),
            "{name} must not decide agreement"
        );
    }

    // A record whose environment changed still agrees when its search agrees.
    record
        .verify_agreement(&search())
        .expect("a changed environment is not divergence");
}

// Only the backend version speaks to numerical behavior, so it is reported
// distinctly rather than lumped in with the source and compiler.
#[test]
fn only_the_backend_difference_claims_numerical_relevance() {
    let record = record();

    let backend = record.environment_difference("1.12.0", &"a".repeat(40), "rustc (test)");
    let line = &backend.describe()[0];
    assert!(line.contains("can change a search's counters"), "{line}");

    let source = record.environment_difference("1.11.0", &"b".repeat(40), "rustc (test)");
    let line = &source.describe()[0];
    assert!(
        !line.contains("can change a search's counters"),
        "a moved revision alone makes no numerical claim: {line}"
    );
}
