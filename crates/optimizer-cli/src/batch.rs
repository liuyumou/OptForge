//! Repeated-solve batch command under SPEC-0014: `optimizer solve-batch`.
//!
//! One explicit [`TunedSession`] pays the single-solve setup costs once for an
//! ordered batch of solves over one fixed matrix: device context, module load,
//! preconditioning and the invariant allocation and upload. Every solve runs
//! the single-solve path's own code from the cold iterate with fresh
//! diagnostics and writes an individually verifiable lp-endpoint-v3 record,
//! and the batch record separates the one-time setup phases from the per-solve
//! session phases and binds every per-solve record hash and status in order
//! (requirements 23 to 26). There is no HiGHS fallback: a session failure is
//! reported in `batch.json` with every remaining solve `not_attempted`, never
//! substituted by another implementation.

use std::collections::BTreeMap;
use std::ffi::OsString;
use std::io;
use std::time::{Duration, Instant};

use optimizer_core::{
    CancellationToken, LpDiagnostics, LpSettings, Model, SessionSetup, SolveOptions,
};
use optimizer_experiment::lp_batch::{self, BatchEndpoint, BatchKind, BatchRequest, SolveSummary};
use optimizer_lp_cuda::TunedSession;

use crate::input::{argument, read};

/// The per-solve record file name, the pinned `solve-NNN.json` layout
/// (requirement 23); lp_batch's own helper is crate-private.
fn solve_file_name(index: u32) -> String {
    format!("solve-{index:03}.json")
}

/// One `not_attempted` summary: no record file and an explicit reason
/// (requirement 27).
fn not_attempted(index: u32, model_sha256: &str, reason: &str) -> SolveSummary {
    SolveSummary {
        index,
        model_sha256: model_sha256.to_owned(),
        endpoint_sha256: lp_batch::NO_RECORD.to_owned(),
        status: "not_attempted".into(),
        solve_elapsed_ns: 0,
        session_phases_ns: BTreeMap::new(),
        reason: Some(reason.to_owned()),
    }
}

/// Every solve recorded `not_attempted` for one shared reason: the session
/// never opened, so no per-solve record exists.
fn unattempted(materialized: &[String], reason: &str) -> Vec<SolveSummary> {
    materialized
        .iter()
        .enumerate()
        .map(|(index, hash)| not_attempted(index as u32, hash, reason))
        .collect()
}

/// The exit code of a solve that never ran, mirroring the termination mapping
/// in [`crate::solve::exit_code`]: interruption is distinct, a limit is not
/// success and a fault is an error.
fn unattempted_code(reason: &str) -> u8 {
    match reason {
        "cancelled" => 130,
        "batch_time_limit" => 1,
        _ => 2,
    }
}

/// Build, write and print the batch record. The constructor recomputes the
/// identity and payload hashes and checks every directory-independent
/// invariant, so a producer inconsistency fails here rather than in a later
/// verifier.
fn write_batch_record(
    dir: &std::path::Path,
    batch_bytes: &[u8],
    model_bytes: &[u8],
    setup: SessionSetup,
    solves: Vec<SolveSummary>,
) -> io::Result<()> {
    let endpoint = BatchEndpoint::new(
        batch_bytes,
        model_bytes,
        "cuda-lp-tuned".to_string(),
        setup,
        solves,
    )
    .map_err(io::Error::other)?;
    let bytes = serde_json::to_vec_pretty(&endpoint).map_err(io::Error::other)?;
    lp_batch::write_evidence_file(&dir.join("batch.json"), &bytes).map_err(io::Error::other)?;
    let mut statuses = BTreeMap::new();
    for solve in &endpoint.solves {
        *statuses.entry(solve.status.clone()).or_insert(0_u32) += 1;
    }
    println!(
        "{}",
        serde_json::json!({
            "solves": endpoint.solves.len(),
            "statuses": statuses,
            "payload_sha256": endpoint.payload_sha256,
        })
    );
    Ok(())
}

pub(crate) fn run(options: &[OsString]) -> io::Result<u8> {
    let mut evidence_dir = None;
    let mut profile_mode = None;
    let mut memory_limit = None;
    let mut model_path = None;
    let mut batch_path = None;
    let mut config_path = None;
    let mut settings_path = None;
    let mut execution_path = None;
    let mut device_name = None;
    for pair in options.chunks(2) {
        let [key, value] = pair else {
            return Err(argument("each flag requires a value"));
        };
        let key = key
            .to_str()
            .ok_or_else(|| argument("flag names must be UTF-8 text"))?;
        let slot = match key {
            "--lp-evidence" => &mut evidence_dir,
            "--lp-profile" => &mut profile_mode,
            "--lp-device-memory-bytes" => &mut memory_limit,
            "--model" => &mut model_path,
            "--batch" => &mut batch_path,
            "--config" => &mut config_path,
            "--lp-settings" => &mut settings_path,
            "--lp-execution" => &mut execution_path,
            "--device" => &mut device_name,
            _ => return Err(argument(&format!("unknown flag {key}"))),
        };
        if slot.replace(value.as_os_str()).is_some() {
            return Err(argument(&format!("duplicate flag {key}")));
        }
    }
    let model_path = model_path.ok_or_else(|| argument("--model is required"))?;
    let batch_path = batch_path.ok_or_else(|| argument("--batch is required"))?;
    let config_path = config_path.ok_or_else(|| argument("--config is required"))?;
    let settings_path = settings_path.ok_or_else(|| argument("--lp-settings is required"))?;
    let execution_path = execution_path.ok_or_else(|| argument("--lp-execution is required"))?;
    let evidence_dir = evidence_dir.ok_or_else(|| argument("--lp-evidence is required"))?;
    let device_name = device_name.ok_or_else(|| argument("--device is required"))?;
    // Spelled exactly as solve.rs spells it, so both commands read one flag.
    let profile = match profile_mode.and_then(|value| value.to_str()) {
        None | Some("false") => false,
        Some("true") => true,
        _ => return Err(argument("--lp-profile requires true or false")),
    };
    let memory_limit = memory_limit
        .map(|value| {
            value
                .to_str()
                .and_then(|value| value.parse::<u64>().ok())
                .filter(|value| *value > 0)
                .ok_or_else(|| argument("invalid LP device memory limit"))
        })
        .transpose()?;

    // Every input document is read and validated under the existing 16 MiB
    // per-document limit before any device is opened (requirement 35), and
    // the up-front materialization below refuses a variant naming a variable
    // the model lacks at the same point, so a malformed batch never reaches
    // the lease or the driver.
    let model_bytes = read(model_path)?;
    let batch_bytes = read(batch_path)?;
    let model = Model::from_json(&model_bytes).map_err(io::Error::other)?;
    let configuration: SolveOptions = serde_json::from_slice(&read(config_path)?)
        .map_err(|error| io::Error::other(format!("document: solve configuration: {error}")))?;
    configuration.validate().map_err(io::Error::other)?;
    let settings = LpSettings::from_json(&read(settings_path)?).map_err(io::Error::other)?;
    settings.validate().map_err(io::Error::other)?;
    let execution = optimizer_core::Fp64ExecutionSettings::from_json(&read(execution_path)?)
        .map_err(io::Error::other)?;
    execution.validate().map_err(io::Error::other)?;
    let request = BatchRequest::from_json(&batch_bytes).map_err(io::Error::other)?;
    let device = device_name
        .to_str()
        .ok_or_else(|| argument("--device must be UTF-8 text"))?;
    let device = optimizer_core::Device::parse(device).map_err(io::Error::other)?;
    // Every per-solve record is an lp-endpoint-v3, whose verification requires
    // observations over a continuous original model: the same refusal solve
    // applies when evidence is requested.
    if !model
        .document()
        .variables
        .iter()
        .all(|v| v.domain == optimizer_core::Domain::Continuous)
    {
        return Err(argument("LP evidence requires a continuous original model"));
    }
    let mut materialized = Vec::with_capacity(request.solves as usize);
    for index in 0..request.solves {
        materialized.push(
            lp_batch::materialize(&model, &request, index)
                .map_err(io::Error::other)?
                .2,
        );
    }

    // Interruption is cooperative, exactly as in solve: the signal sets the
    // shared token and a solve observes it at its chunk boundaries.
    let cancel = CancellationToken::new();
    let signalled = std::sync::Arc::new(std::sync::atomic::AtomicBool::new(false));
    crate::solve::install_signal_handler(&cancel, &signalled)?;

    // The directory is created if needed; every file inside it is create_new
    // plus rename and never replaces an existing record (requirement 25).
    let dir = std::path::Path::new(evidence_dir);
    std::fs::create_dir_all(dir)?;

    // The CLI's contribution to the setup record is the device context; the
    // session's own open measures module_load, preconditioning and
    // invariant_allocation_upload (requirement 24).
    let mut setup = SessionSetup::default();
    let phase = setup.start();
    let opened = crate::registry::open_device(&device);
    setup.finish("device_context", phase);
    let device_session = match opened {
        Ok(Some(session)) => session,
        Ok(None) => {
            let reason = "no device was opened".to_string();
            eprintln!("solve-batch: session unavailable: {reason}");
            write_batch_record(
                dir,
                &batch_bytes,
                &model_bytes,
                setup,
                unattempted(&materialized, &reason),
            )?;
            return Ok(2);
        }
        Err(error) => {
            let reason = error.to_string();
            eprintln!("solve-batch: session unavailable: {reason}");
            write_batch_record(
                dir,
                &batch_bytes,
                &model_bytes,
                setup,
                unattempted(&materialized, &reason),
            )?;
            return Ok(2);
        }
    };
    let mut open_diagnostics = LpDiagnostics::new(true, profile);
    open_diagnostics.device_buffer_limit_bytes = memory_limit;
    let mut session = match TunedSession::open(
        device_session.context(),
        settings,
        execution,
        model.clone(),
        &mut open_diagnostics,
    ) {
        Ok(session) => session,
        Err(error) => {
            let reason = error.to_string();
            eprintln!("solve-batch: session unavailable: {reason}");
            write_batch_record(
                dir,
                &batch_bytes,
                &model_bytes,
                setup,
                unattempted(&materialized, &reason),
            )?;
            return Ok(2);
        }
    };
    for (name, ns) in &session.setup().phases_ns {
        setup.phases_ns.insert(name.clone(), *ns);
    }

    let deadline = Instant::now().checked_add(Duration::from_millis(request.batch_time_limit_ms));
    let mut solves = Vec::with_capacity(request.solves as usize);
    let mut worst = 0_u8;
    for index in 0..request.solves {
        // Cancellation, the batch time limit and a poisoned session are
        // observed between solves; records for completed solves are retained
        // and every remaining solve is recorded not_attempted with the reason
        // (requirements 13, 14 and 27).
        let blocked = if cancel.is_cancelled() {
            Some("cancelled".to_owned())
        } else if deadline.is_some_and(|deadline| Instant::now() >= deadline) {
            Some("batch_time_limit".to_owned())
        } else {
            session.poisoned().map(str::to_owned)
        };
        if let Some(reason) = blocked {
            worst = worst.max(unattempted_code(&reason));
            for remaining in index..request.solves {
                solves.push(not_attempted(
                    remaining,
                    &materialized[remaining as usize],
                    &reason,
                ));
            }
            break;
        }
        // Re-materialized per solve; the up-front pass makes this infallible
        // in practice, and a failure here is a document error, not a solve
        // outcome.
        let (variant, variant_bytes, model_sha256) =
            lp_batch::materialize(&model, &request, index).map_err(io::Error::other)?;
        // Fresh per-solve diagnostics (requirement 9); batch-level aggregates
        // live only in the batch record.
        let mut diagnostics = LpDiagnostics::new(true, profile);
        diagnostics.device_buffer_limit_bytes = memory_limit;
        let admitted = match request.kind {
            BatchKind::Repeat => None,
            BatchKind::Variant => Some(&variant),
        };
        let started = Instant::now();
        let outcome = session.solve(admitted, &configuration, &cancel, &mut diagnostics);
        let solve_elapsed_ns = u64::try_from(started.elapsed().as_nanos()).unwrap_or(u64::MAX);
        let session_phases_ns = session.solve_phases().phases_ns.clone();
        let record = match outcome {
            Ok(record) => record,
            // A refused solve (for example an inadmissible variant) is a
            // failed solve with an explicit reason; the session itself decides
            // whether a device fault poisons it, and the loop top records the
            // rest.
            Err(error) => {
                worst = worst.max(2);
                solves.push(SolveSummary {
                    index,
                    model_sha256,
                    endpoint_sha256: lp_batch::NO_RECORD.to_owned(),
                    status: "failed".into(),
                    solve_elapsed_ns,
                    session_phases_ns,
                    reason: Some(error.to_string()),
                });
                continue;
            }
        };
        worst = worst.max(crate::solve::exit_code(record.termination));
        // The per-solve endpoint is built exactly as solve.rs builds one for
        // cuda-lp-tuned: the materialized model bytes, the tuned identity, the
        // session's execution record and this solve's diagnostics, and never a
        // fallback reason.
        let endpoint = optimizer_experiment::lp::LpEndpoint::new(
            &variant_bytes,
            "cuda-lp-tuned".to_string(),
            record,
            diagnostics,
            None,
        );
        match endpoint {
            Ok(endpoint) => {
                let status = endpoint.assessment.classification.clone();
                let bytes = serde_json::to_vec_pretty(&endpoint).map_err(io::Error::other)?;
                lp_batch::write_evidence_file(&dir.join(solve_file_name(index)), &bytes)
                    .map_err(io::Error::other)?;
                solves.push(SolveSummary {
                    index,
                    model_sha256,
                    endpoint_sha256: optimizer_core::sha256::hex(&bytes),
                    status,
                    solve_elapsed_ns,
                    session_phases_ns,
                    reason: None,
                });
            }
            // A solve whose endpoint cannot be constructed is failed, recorded
            // explicitly; the session is unaffected.
            Err(reason) => {
                worst = worst.max(2);
                solves.push(SolveSummary {
                    index,
                    model_sha256,
                    endpoint_sha256: lp_batch::NO_RECORD.to_owned(),
                    status: "failed".into(),
                    solve_elapsed_ns,
                    session_phases_ns,
                    reason: Some(reason.to_string()),
                });
            }
        }
    }
    write_batch_record(dir, &batch_bytes, &model_bytes, setup, solves)?;
    Ok(worst)
}
