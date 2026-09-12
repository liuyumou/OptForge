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
use optimizer_experiment::{
    ExtensionDifference, InputDocument, InputRole, RUN_SCHEMA_VERSION, RunRecord, sha256,
};
use optimizer_highs::HighsBackend;
use optimizer_solver::{SearchOptions, SearchOutcome, SearchRecord};

use crate::input::{argument, read};
use crate::provenance;
use crate::registry::RegistryArguments;

pub(crate) fn search(options: &[OsString]) -> io::Result<u8> {
    let (registry, options) = crate::registry::take_arguments(options)?;
    let options = options.as_slice();
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

    let (record, _) = run(model_path, config_path, &registry)?;
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
fn run(
    model_path: &OsStr,
    config_path: &OsStr,
    registry: &RegistryArguments,
) -> io::Result<(RunRecord, Model)> {
    let model_bytes = read(model_path)?;
    let config_bytes = read(config_path)?;
    let model = Model::from_json(&model_bytes).map_err(io::Error::other)?;
    let configuration: SearchOptions = serde_json::from_slice(&config_bytes)
        .map_err(|error| io::Error::other(format!("document: search configuration: {error}")))?;

    // SPEC-0009 requirement 18: a policy naming an extension is resolved through a
    // registry the caller named explicitly, and refused when none was named.
    // Running without the named extension would record a search the caller did not
    // ask for, which is what the pre-registry refusal existed to prevent.
    let resolved = registry.resolve(&configuration.extensions, &model, None)?;

    // The revision is required before the search so a run that cannot produce a
    // valid record fails before spending the budget.
    let revision = provenance::revision()?;
    let fingerprint = model.fingerprint().map_err(io::Error::other)?;

    let cancel = CancellationToken::new();
    let signalled = Arc::new(AtomicBool::new(false));
    crate::solve::install_signal_handler(&cancel, &signalled)?;

    let backend = HighsBackend::new();
    // Requirement 17: an empty policy takes the extension-free entry point, so a
    // search with a registry supplied but no extension named produces the record
    // it would have produced without one.
    let search: SearchRecord = match &resolved {
        Some(resolved) => optimizer_solver::search_with_extensions(
            &model,
            &configuration,
            &resolved.registrations(),
            &backend,
            &cancel,
        )
        .map_err(io::Error::other)?,
        None => optimizer_solver::search(&model, &configuration, &backend, &cancel)
            .map_err(io::Error::other)?,
    };

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
        // Requirement 12: a registered experimental extension is named here, so a
        // record cannot conceal that something without conformance evidence
        // participated in the search it describes.
        warnings: resolved
            .as_ref()
            .map(|resolved| resolved.warnings().to_vec())
            .unwrap_or_default(),
    };
    Ok((record, model))
}

/// Re-run one search from a record and compare the two.
pub(crate) fn verify(options: &[OsString]) -> io::Result<u8> {
    let (registry, options) = crate::registry::take_arguments(options)?;
    let options = options.as_slice();
    let mut record_path = None;
    let mut model_path = None;
    let mut instance_argument = None;
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
            // A scheduling producer is constructed from its instance, which a run
            // record does not embed. Supplying it is how a registry-backed
            // scheduling record becomes verifiable.
            "--instance" => &mut instance_argument,
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

    // SPEC-0009 requirement 20: a record naming a nondeterministic extension is
    // refused as unsupported rather than compared. SPEC-0004 requirement 18
    // withholds replay equality for such a search, so agreement or divergence
    // would both be meaningless, and calling it divergence would blame the record
    // for a property it honestly reported.
    if let Some(summary) = record
        .search
        .extensions
        .iter()
        .find(|summary| summary.registered && !summary.deterministic)
    {
        return Err(io::Error::other(format!(
            "unsupported: extension {} declared itself nondeterministic, \
             so this record does not claim replay equality and cannot be verified \
             by re-execution",
            summary.extension_id
        )));
    }

    // Requirement 19: the named extensions are resolved through the caller's
    // registry and the record is re-executed with them. Before SPEC-0009 this was
    // a blanket refusal, which is why a scheduling run performed with a producer
    // was not verifiable at all.
    let instance_bytes;
    let instance = match &registry.path {
        // A scheduling producer needs its instance and a run record does not embed
        // one, so the caller supplies it the same way it supplies the model. An
        // entry declaring that need is refused without it rather than resolved
        // against a default.
        Some(_) => {
            instance_bytes = instance_argument.map(read).transpose()?;
            instance_bytes.as_deref()
        }
        None => None,
    };
    let resolved = registry.resolve(&record.search.options.extensions, &model, instance)?;

    // A resolved extension whose version differs from the one the record names is
    // refused as unsupported, not compared: re-executing against a different
    // version would reproduce a search the record does not describe, and its
    // counters would differ for that reason alone.
    if let Some(resolved) = resolved.as_ref() {
        for summary in &record.search.extensions {
            if !summary.registered {
                continue;
            }
            let Some(declaration) = resolved.declaration(&summary.extension_id) else {
                continue;
            };
            if declaration.version != summary.version {
                return Err(io::Error::other(format!(
                    "unsupported: extension {} resolves to version {}, but the record \
                     names version {}; re-execution would describe a different search",
                    summary.extension_id, declaration.version, summary.version
                )));
            }
        }
    }

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
    let fresh = match &resolved {
        Some(resolved) => optimizer_solver::search_with_extensions(
            &model,
            &record.search.options,
            &resolved.registrations(),
            &backend,
            &cancel,
        )
        .map_err(io::Error::other)?,
        None => optimizer_solver::search(&model, &record.search.options, &backend, &cancel)
            .map_err(io::Error::other)?,
    };

    // The environment is compared for diagnosis only, after the search has run
    // and never as an input to the agreement decision. A changed library is a
    // likely cause of divergence, not an excuse for it.
    let environment = record.environment_difference(
        &fresh.backend_version,
        &provenance::revision().unwrap_or_else(|_| "unavailable".to_owned()),
        &provenance::toolchain().rustc,
    );
    // SPEC-0009 requirement 21: the same separation applied to extensions. A
    // resolved extension that behaved differently already moves the compared node
    // counters, so this explains a divergence rather than deciding one, and adding
    // it to agreement would change what agreement means.
    let extensions = ExtensionDifference::between(&record.search.extensions, &fresh.extensions);

    if let Err(error) = record.verify_agreement(&fresh) {
        let mut report = format!("divergence: {error}");
        for line in environment
            .describe()
            .into_iter()
            .chain(extensions.describe())
        {
            report.push_str(&format!("\n  note: {line}"));
        }
        return Err(io::Error::other(report));
    }

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
        // Recorded even when the run agreed, so a reader can see that it agreed
        // despite a different build rather than having to infer it.
        "environment_differs": !environment.is_empty(),
        "environment": environment.describe(),
        // Named so a reader can see which extensions were reconstructed, and
        // whether any of them behaved differently while the search still agreed.
        "extensions": resolved
            .as_ref()
            .map(|resolved| resolved.identities())
            .unwrap_or_default(),
        "extensions_differ": !extensions.is_empty(),
        "extension_differences": extensions.describe(),
        "note": "Agreement establishes determinism under this host and library, not optimality."
    }))?;

    let mut stdout = io::stdout().lock();
    writeln!(stdout, "{verdict}")
        .and_then(|()| stdout.flush())
        .map_err(|error| io::Error::other(format!("io: stdout: {error}")))?;
    Ok(exit_code(fresh.outcome))
}
