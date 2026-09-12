//! Flow-shop scheduling commands under SPEC-0008 requirements 21 to 26.
//!
//! `schedule generate` writes an instance document from a published seed.
//! `schedule solve` encodes an instance, registers exactly the NEH producer, runs
//! the executive and writes a SPEC-0005 run record.
//!
//! `solve` also writes the encoded model, because that is what makes verification
//! work unchanged: a run record's fingerprint is computed from the model that was
//! searched, and for a scheduling run that is the encoded model rather than the
//! instance. Without the encoded model on disk a caller would have nothing to hand
//! `optimizer verify`, so requirement 25 would be unreachable in practice.
//!
//! Nothing here reports a runtime or a solution-quality comparison. A search that
//! reached a limit reports the limit, and its incumbent is a validated feasible
//! schedule rather than an optimum, which is requirement 26.

use std::ffi::{OsStr, OsString};
use std::io::{self, Write};
use std::sync::Arc;
use std::sync::atomic::AtomicBool;

use optimizer_core::CancellationToken;
use optimizer_experiment::{InputDocument, InputRole, RUN_SCHEMA_VERSION, RunRecord, sha256};
use optimizer_highs::HighsBackend;
use optimizer_schedule::FlowShopInstance;
use optimizer_solver::{SearchOptions, SearchRecord};

use crate::input::{argument, read};
use crate::provenance;
use crate::search::exit_code;

/// Write an instance generated from a published Taillard seed.
pub(crate) fn generate(options: &[OsString]) -> io::Result<u8> {
    let mut instance_id = None;
    let mut seed = None;
    let mut jobs = None;
    let mut machines = None;
    let mut output_path = None;
    for pair in options.chunks(2) {
        let [key, value] = pair else {
            return Err(argument("each flag requires a value"));
        };
        let key = key
            .to_str()
            .ok_or_else(|| argument("flag names must be UTF-8 text"))?;
        let slot = match key {
            "--instance-id" => &mut instance_id,
            "--seed" => &mut seed,
            "--jobs" => &mut jobs,
            "--machines" => &mut machines,
            "--output" => &mut output_path,
            _ => return Err(argument(&format!("unknown flag {key}"))),
        };
        if slot.replace(value.as_os_str()).is_some() {
            return Err(argument(&format!("duplicate flag {key}")));
        }
    }
    let instance_id = text(instance_id.ok_or_else(|| argument("--instance-id is required"))?)?;
    let seed = number(
        seed.ok_or_else(|| argument("--seed is required"))?,
        "--seed",
    )?;
    let jobs = number(
        jobs.ok_or_else(|| argument("--jobs is required"))?,
        "--jobs",
    )?;
    let machines = number(
        machines.ok_or_else(|| argument("--machines is required"))?,
        "--machines",
    )?;

    let instance = optimizer_schedule::taillard_instance(instance_id, seed, jobs, machines)
        .map_err(io::Error::other)?;
    write_document(&instance.to_json().map_err(io::Error::other)?, output_path)?;
    Ok(0)
}

/// Encode an instance, search it with the NEH producer, and write a run record.
pub(crate) fn solve(options: &[OsString]) -> io::Result<u8> {
    let (registry, options) = crate::registry::take_arguments(options)?;
    let options = options.as_slice();
    let mut instance_path = None;
    let mut config_path = None;
    let mut output_path = None;
    let mut model_output = None;
    for pair in options.chunks(2) {
        let [key, value] = pair else {
            return Err(argument("each flag requires a value"));
        };
        let key = key
            .to_str()
            .ok_or_else(|| argument("flag names must be UTF-8 text"))?;
        let slot = match key {
            "--instance" => &mut instance_path,
            "--config" => &mut config_path,
            "--output" => &mut output_path,
            "--output-model" => &mut model_output,
            _ => return Err(argument(&format!("unknown flag {key}"))),
        };
        if slot.replace(value.as_os_str()).is_some() {
            return Err(argument(&format!("duplicate flag {key}")));
        }
    }
    let instance_path = instance_path.ok_or_else(|| argument("--instance is required"))?;
    let config_path = config_path.ok_or_else(|| argument("--config is required"))?;

    let instance_bytes = read(instance_path)?;
    let config_bytes = read(config_path)?;
    let instance = FlowShopInstance::from_json(&instance_bytes).map_err(io::Error::other)?;
    let configuration: SearchOptions = serde_json::from_slice(&config_bytes)
        .map_err(|error| io::Error::other(format!("document: search configuration: {error}")))?;

    let model = optimizer_schedule::model(&instance).map_err(io::Error::other)?;

    // SPEC-0009 requirement 18 replaces what used to be a single hardcoded
    // identity here. Any extension the caller's registry records and this build
    // provides can now be registered, and the instance travels in the provider
    // context because a scheduling producer cannot be built from a model alone.
    let resolved = registry.resolve(&configuration.extensions, &model, Some(&instance_bytes))?;
    // Provenance is collected before the search so a run that cannot produce a
    // valid record fails before spending the budget.
    let revision = provenance::revision()?;
    let fingerprint = model.fingerprint().map_err(io::Error::other)?;
    let encoded_model = model.to_json().map_err(io::Error::other)?;

    let cancel = CancellationToken::new();
    let signalled = Arc::new(AtomicBool::new(false));
    crate::solve::install_signal_handler(&cancel, &signalled)?;

    let backend = HighsBackend::new();
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

    let instance_sha = sha256::hex(&instance_bytes);
    let config_sha = sha256::hex(&config_bytes);
    let record = RunRecord {
        schema_version: RUN_SCHEMA_VERSION,
        // Requirement 1a: derived from the inputs, never from measured time.
        record_id: provenance::record_id(
            "schedule",
            &search.model_id,
            &[&instance_sha, &config_sha],
        ),
        revision,
        dirty: provenance::dirty(),
        hardware: provenance::hardware(),
        toolchain: provenance::toolchain(),
        model_fingerprint: fingerprint,
        inputs: vec![
            InputDocument {
                role: InputRole::Model,
                path: std::path::Path::new(instance_path).display().to_string(),
                sha256: instance_sha,
            },
            InputDocument {
                role: InputRole::Config,
                path: std::path::Path::new(config_path).display().to_string(),
                sha256: config_sha,
            },
        ],
        search,
        warnings: resolved
            .as_ref()
            .map(|resolved| resolved.warnings().to_vec())
            .unwrap_or_default(),
    };

    // The encoded model is written first. A record naming a fingerprint whose
    // model was never persisted would be unverifiable, and failing after the
    // record is written would leave exactly that.
    if let Some(path) = model_output {
        std::fs::write(path, format!("{encoded_model}\n")).map_err(|error| {
            io::Error::other(format!(
                "io: {}: {error}",
                std::path::Path::new(path).display()
            ))
        })?;
    }

    let outcome = record.search.outcome;
    write_document(&record.to_json().map_err(io::Error::other)?, output_path)?;
    Ok(exit_code(outcome))
}

/// Write one document to a path or to standard output.
fn write_document(document: &str, path: Option<&OsStr>) -> io::Result<()> {
    match path {
        Some(path) => std::fs::write(path, format!("{document}\n")).map_err(|error| {
            io::Error::other(format!(
                "io: {}: {error}",
                std::path::Path::new(path).display()
            ))
        }),
        None => {
            let mut stdout = io::stdout().lock();
            writeln!(stdout, "{document}")
                .and_then(|()| stdout.flush())
                .map_err(|error| io::Error::other(format!("io: stdout: {error}")))
        }
    }
}

/// Require UTF-8 text for a value that reaches a document field.
fn text(value: &OsStr) -> io::Result<String> {
    value
        .to_str()
        .map(str::to_owned)
        .ok_or_else(|| argument("instance identifiers must be UTF-8 text"))
}

/// Parse a required unsigned numeric flag.
fn number(value: &OsStr, flag: &str) -> io::Result<u32> {
    value
        .to_str()
        .and_then(|text| text.parse::<u32>().ok())
        .ok_or_else(|| argument(&format!("{flag} requires a nonnegative integer")))
}
