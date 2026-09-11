//! Owned search command producing a provenance-bearing run record.
//!
//! This is the first surface through which the C2 executive and the C3 extension
//! host are reachable outside Rust test code. A search that reached a limit or
//! was interrupted still writes its record: an unfinished search is a fact about
//! a run, and discarding it would leave the caller unable to see what a budget
//! bought.

use std::ffi::{OsStr, OsString};
use std::io::{self, Write};
use std::sync::Arc;
use std::sync::atomic::AtomicBool;

use optimizer_core::{CancellationToken, Model};
use optimizer_experiment::{InputDocument, InputRole, RUN_SCHEMA_VERSION, RunRecord, sha256};
use optimizer_highs::HighsBackend;
use optimizer_solver::{SearchOptions, SearchOutcome, SearchRecord};

use crate::input::{argument, read};
use crate::provenance;

pub(crate) fn search(options: &[OsString]) -> io::Result<u8> {
    let mut model_path = None;
    let mut config_path = None;
    let mut output_path = None;
    for pair in options.chunks(2) {
        let [key, value] = pair else {
            return Err(argument("each flag requires a value"));
        };
        let key = key
            .to_str()
            .ok_or_else(|| argument("flag names must be UTF-8 text"))?;
        let slot = match key {
            "--model" => &mut model_path,
            "--config" => &mut config_path,
            "--output" => &mut output_path,
            _ => return Err(argument(&format!("unknown flag {key}"))),
        };
        if slot.replace(value.as_os_str()).is_some() {
            return Err(argument(&format!("duplicate flag {key}")));
        }
    }
    let model_path = model_path.ok_or_else(|| argument("--model is required"))?;
    let config_path = config_path.ok_or_else(|| argument("--config is required"))?;

    let (record, _) = run(model_path, config_path)?;
    let outcome = record.search.outcome;
    let output = record.to_json().map_err(io::Error::other)?;

    match output_path {
        Some(path) => std::fs::write(path, format!("{output}\n")).map_err(|error| {
            io::Error::other(format!(
                "io: {}: {error}",
                std::path::Path::new(path).display()
            ))
        })?,
        None => {
            let mut stdout = io::stdout().lock();
            writeln!(stdout, "{output}")
                .and_then(|()| stdout.flush())
                .map_err(|error| io::Error::other(format!("io: stdout: {error}")))?;
        }
    }

    Ok(exit_code(outcome))
}

/// Exit code for one search outcome.
///
/// Matched exhaustively with no catch-all arm, so a later `SearchOutcome`
/// variant fails to compile rather than silently becoming a success.
pub(crate) fn exit_code(outcome: SearchOutcome) -> u8 {
    match outcome {
        // The executive exhausted its own node tree.
        SearchOutcome::ProvenOptimal
        | SearchOutcome::ProvenInfeasible
        | SearchOutcome::UnboundedOrInfeasible => 0,
        // Interruption is reported distinctly so it is never read as success.
        SearchOutcome::Interrupted => 130,
        // A budget ran out, or a feasible assignment exists without a proof.
        SearchOutcome::Feasible
        | SearchOutcome::NodeLimit
        | SearchOutcome::TimeLimit
        | SearchOutcome::OpenNodeLimit => 1,
        // A failure is an error, not a search outcome the caller asked for.
        SearchOutcome::NumericalFailure
        | SearchOutcome::BackendFailure
        | SearchOutcome::Unsupported => 2,
    }
}

/// Run one search and wrap it in a run record.
///
/// Inputs are read and parsed before the search starts, so a malformed document
/// is an input error rather than a backend failure. Returns the record and the
/// model it searched, so a caller that must compare fingerprints does not read
/// the model twice.
fn run(model_path: &OsStr, config_path: &OsStr) -> io::Result<(RunRecord, Model)> {
    let model_bytes = read(model_path)?;
    let config_bytes = read(config_path)?;
    let model = Model::from_json(&model_bytes).map_err(io::Error::other)?;
    let configuration: SearchOptions = serde_json::from_slice(&config_bytes)
        .map_err(|error| io::Error::other(format!("document: search configuration: {error}")))?;

    // No mechanism here loads an extension, so a policy naming one must be
    // refused. Running without it would record a search the caller did not ask
    // for; this is the seam the deferred registry fills.
    if !configuration.extensions.is_empty() {
        return Err(io::Error::other(
            "unsupported: this surface loads no extensions; \
             a configuration naming an extension policy cannot be honored",
        ));
    }

    // The revision is required before the search so a run that cannot produce a
    // valid record fails before spending the budget.
    let revision = provenance::revision()?;
    let fingerprint = model.fingerprint().map_err(io::Error::other)?;

    let cancel = CancellationToken::new();
    let signalled = Arc::new(AtomicBool::new(false));
    crate::solve::install_signal_handler(&cancel, &signalled)?;

    let backend = HighsBackend::new();
    let search: SearchRecord = optimizer_solver::search(&model, &configuration, &backend, &cancel)
        .map_err(io::Error::other)?;

    let record = RunRecord {
        schema_version: RUN_SCHEMA_VERSION,
        record_id: format!("run-{}-{}", search.model_id, search.elapsed_ms),
        revision,
        dirty: provenance::dirty(),
        hardware: provenance::hardware(),
        toolchain: provenance::toolchain(),
        model_fingerprint: fingerprint,
        inputs: vec![
            InputDocument {
                role: InputRole::Model,
                path: std::path::Path::new(model_path).display().to_string(),
                sha256: sha256::hex(&model_bytes),
            },
            InputDocument {
                role: InputRole::Config,
                path: std::path::Path::new(config_path).display().to_string(),
                sha256: sha256::hex(&config_bytes),
            },
        ],
        search,
        warnings: Vec::new(),
    };
    Ok((record, model))
}

/// Re-run one search from a record and compare the two.
pub(crate) fn verify(options: &[OsString]) -> io::Result<u8> {
    let mut record_path = None;
    let mut model_path = None;
    for pair in options.chunks(2) {
        let [key, value] = pair else {
            return Err(argument("each flag requires a value"));
        };
        let key = key
            .to_str()
            .ok_or_else(|| argument("flag names must be UTF-8 text"))?;
        let slot = match key {
            "--record" => &mut record_path,
            "--model" => &mut model_path,
            _ => return Err(argument(&format!("unknown flag {key}"))),
        };
        if slot.replace(value.as_os_str()).is_some() {
            return Err(argument(&format!("duplicate flag {key}")));
        }
    }
    let record_path = record_path.ok_or_else(|| argument("--record is required"))?;
    let model_path = model_path.ok_or_else(|| argument("--model is required"))?;

    let record = RunRecord::from_json(&read(record_path)?).map_err(io::Error::other)?;
    let model = Model::from_json(&read(model_path)?).map_err(io::Error::other)?;

    // The fingerprint is checked before spending a search budget, and it is
    // checked rather than model_id: a record whose model data changed under an
    // unchanged identity must not verify.
    let fingerprint = model.fingerprint().map_err(io::Error::other)?;
    if fingerprint != record.model_fingerprint {
        return Err(io::Error::other(format!(
            "document: model fingerprint mismatch: record {}, supplied {fingerprint}",
            record.model_fingerprint
        )));
    }

    let cancel = CancellationToken::new();
    let signalled = Arc::new(AtomicBool::new(false));
    crate::solve::install_signal_handler(&cancel, &signalled)?;

    // Only the recorded configuration is used as input. Reading the recorded
    // outcome here would let verification confirm its own input.
    let backend = HighsBackend::new();
    let fresh = optimizer_solver::search(&model, &record.search.options, &backend, &cancel)
        .map_err(io::Error::other)?;

    record
        .verify_agreement(&fresh)
        .map_err(|error| io::Error::other(format!("divergence: {error}")))?;

    // Agreement is evidence of determinism. It is deliberately not reported as
    // a proof: a forfeited search stays forfeited however often it is repeated.
    let verdict = serde_json::to_string_pretty(&serde_json::json!({
        "schema_version": RUN_SCHEMA_VERSION,
        "record_id": record.record_id,
        "model_id": record.search.model_id,
        "model_fingerprint": record.model_fingerprint,
        "agreement": true,
        "compared": RunRecord::compared_fields(),
        "outcome": fresh.outcome,
        "forfeited": fresh.forfeited,
        "evidence": record.is_evidence(),
        "note": "Agreement establishes determinism under this host and library, not optimality."
    }))?;

    let mut stdout = io::stdout().lock();
    writeln!(stdout, "{verdict}")
        .and_then(|()| stdout.flush())
        .map_err(|error| io::Error::other(format!("io: stdout: {error}")))?;
    Ok(exit_code(fresh.outcome))
}
