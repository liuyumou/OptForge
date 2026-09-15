//! Pinned solve command over the backend-neutral contract.
//!
//! Configuration is a strict versioned JSON document, so a record always states
//! the seed, limits and tolerances that produced it. Exit status distinguishes a
//! completed outcome from a limit: a timeout is never reported as success.

use std::ffi::OsString;
use std::io::{self, Write};
use std::sync::Arc;
use std::sync::atomic::{AtomicBool, Ordering};

use optimizer_core::{
    Basis, CancellationToken, Candidate, LpSettings, Model, SolveOptions, Termination,
};
use optimizer_highs::HighsBackend;
use optimizer_lp::HostLpBackend;
use optimizer_lp_cuda::CudaLpBackend;

use crate::input::{argument, read};

pub(crate) fn solve(options: &[OsString]) -> io::Result<u8> {
    let input_started = std::time::Instant::now();
    let mut evidence_path = None;
    let mut profile_mode = None;
    let mut memory_limit = None;
    let mut model_path = None;
    let mut config_path = None;
    let mut candidate_path = None;
    let mut basis_path = None;
    let mut backend_name = None;
    let mut settings_path = None;
    let mut device_name = None;
    for pair in options.chunks(2) {
        let [key, value] = pair else {
            return Err(argument("each flag requires a value"));
        };
        let key = key
            .to_str()
            .ok_or_else(|| argument("flag names must be UTF-8 text"))?;
        let slot = match key {
            "--lp-evidence" => &mut evidence_path,
            "--lp-profile" => &mut profile_mode,
            "--lp-device-memory-bytes" => &mut memory_limit,
            "--model" => &mut model_path,
            "--config" => &mut config_path,
            "--candidate" => &mut candidate_path,
            "--basis" => &mut basis_path,
            "--backend" => &mut backend_name,
            "--lp-settings" => &mut settings_path,
            "--device" => &mut device_name,
            _ => return Err(argument(&format!("unknown flag {key}"))),
        };
        if slot.replace(value.as_os_str()).is_some() {
            return Err(argument(&format!("duplicate flag {key}")));
        }
    }
    let model_path = model_path.ok_or_else(|| argument("--model is required"))?;
    let config_path = config_path.ok_or_else(|| argument("--config is required"))?;
    if candidate_path.is_some() && basis_path.is_some() {
        return Err(argument(
            "--candidate and --basis are mutually exclusive warm starts",
        ));
    }

    if evidence_path.is_none() && (profile_mode.is_some() || memory_limit.is_some()) {
        return Err(argument("LP profiling/memory limits require --lp-evidence"));
    }
    let profile = match profile_mode.and_then(|v| v.to_str()) {
        None | Some("false") => false,
        Some("true") => true,
        _ => return Err(argument("--lp-profile requires true or false")),
    };
    let mut diagnostics = optimizer_core::LpDiagnostics::new(evidence_path.is_some(), profile);
    diagnostics.device_buffer_limit_bytes = memory_limit
        .map(|v| {
            v.to_str()
                .and_then(|v| v.parse::<u64>().ok())
                .filter(|v| *v > 0)
                .ok_or_else(|| argument("invalid LP device memory limit"))
        })
        .transpose()?;
    let model_bytes = read(model_path)?;
    let model = Model::from_json(&model_bytes).map_err(io::Error::other)?;
    let configuration: SolveOptions = serde_json::from_slice(&read(config_path)?)
        .map_err(|error| io::Error::other(format!("document: solve configuration: {error}")))?;

    // Warm starts are parsed before the solve so a malformed one is an input
    // error rather than a backend failure.
    let candidate = candidate_path
        .map(|path| Candidate::from_json(&read(path)?).map_err(io::Error::other))
        .transpose()?;
    let basis = basis_path
        .map(|path| -> io::Result<Basis> {
            serde_json::from_slice(&read(path)?)
                .map_err(|error| io::Error::other(format!("document: basis: {error}")))
        })
        .transpose()?;
    let warm_start = match (&candidate, &basis) {
        (Some(candidate), _) => Some(optimizer_core::WarmStart::Candidate(candidate)),
        (_, Some(basis)) => Some(optimizer_core::WarmStart::Basis(basis)),
        _ => None,
    };

    // Interruption is cooperative: the signal sets the shared token and the
    // backend observes it through its native callback.
    let cancel = CancellationToken::new();
    let signalled = Arc::new(AtomicBool::new(false));
    install_signal_handler(&cancel, &signalled)?;

    // SPEC-0011 requirement 18: the pinned CPU backend is the default, and it is
    // the default because nothing else can be reached without being named. There
    // is deliberately no threshold here that could promote a solve to another
    // backend: a dispatch threshold is a recorded measurement under requirements
    // 18 and 19, and state/known-failures.md already records that this project
    // commits no such number without an ADR and held-out evidence.
    let selected = backend_name
        .map(|name| {
            name.to_str()
                .ok_or_else(|| argument("--backend must be UTF-8 text"))
        })
        .transpose()?
        .unwrap_or("highs");

    if diagnostics.enabled
        && !model
            .document()
            .variables
            .iter()
            .all(|v| v.domain == optimizer_core::Domain::Continuous)
    {
        return Err(argument("LP evidence requires a continuous original model"));
    }
    diagnostics.finish("input_preparation", profile.then_some(input_started));
    let mut fallback_reason = None;
    let record = match selected {
        "highs" => {
            if settings_path.is_some() {
                return Err(argument(
                    "--lp-settings applies only to a first-order backend",
                ));
            }
            HighsBackend::new()
                .solve_with_diagnostics(
                    &model,
                    &configuration,
                    &cancel,
                    warm_start,
                    &mut diagnostics,
                )
                .map_err(io::Error::other)?
        }
        "host-lp" => {
            // Settings are required rather than defaulted. Requirements 9 and 10
            // make the preconditioner and the check interval recorded state, and
            // a default would let two solves with different behaviour write
            // records that look identical.
            let path = settings_path
                .ok_or_else(|| argument("--backend host-lp requires --lp-settings"))?;
            let settings = LpSettings::from_json(&read(path)?).map_err(io::Error::other)?;
            HostLpBackend::new(settings)
                .map_err(io::Error::other)?
                .solve_with_diagnostics(
                    &model,
                    &configuration,
                    &cancel,
                    warm_start,
                    &mut diagnostics,
                )
                .map_err(io::Error::other)?
        }
        "cuda-lp" => {
            let path = settings_path
                .ok_or_else(|| argument("--backend cuda-lp requires --lp-settings"))?;
            let settings = LpSettings::from_json(&read(path)?).map_err(io::Error::other)?;
            let device = device_name
                .ok_or_else(|| argument("--backend cuda-lp requires --device"))?
                .to_str()
                .ok_or_else(|| argument("--device must be UTF-8 text"))?
                .to_string();
            let device = optimizer_core::Device::parse(&device).map_err(io::Error::other)?;

            // SPEC-0011 requirement 20 and SPEC-0010 requirement 24: an
            // availability failure falls back to the CPU backend. The fallback is
            // the pinned adapter, never the host first-order method -- SPEC-0010
            // requirement 23 requires a fallback to be the implementation the
            // project already treats as authoritative, and requirement 26 keeps
            // the host method a differential oracle rather than a second engine
            // the run surface may quietly substitute.
            //
            // The decision lives here because only here are both backends in
            // scope. A backend that answered with a different implementation would
            // write a record naming itself for work it did not do.
            let opening = diagnostics.start();
            let session_result = crate::registry::open_device(&device);
            diagnostics.finish("device_context", opening);
            match session_result? {
                Some(session) => {
                    match device_solve(
                        &session,
                        settings,
                        &model,
                        &configuration,
                        &cancel,
                        &mut diagnostics,
                    ) {
                        Ok(record) => record,
                        Err(reason) => {
                            fallback_reason = Some(reason.clone());
                            diagnostics.dual = None;
                            eprintln!("solve: falling back to the pinned CPU backend: {reason}");
                            HighsBackend::new()
                                .solve_with_diagnostics(
                                    &model,
                                    &configuration,
                                    &cancel,
                                    warm_start,
                                    &mut diagnostics,
                                )
                                .map_err(io::Error::other)?
                        }
                    }
                }
                None => {
                    fallback_reason = Some("no device was opened".to_string());
                    eprintln!(
                        "solve: falling back to the pinned CPU backend: no device was opened"
                    );
                    HighsBackend::new()
                        .solve_with_diagnostics(
                            &model,
                            &configuration,
                            &cancel,
                            warm_start,
                            &mut diagnostics,
                        )
                        .map_err(io::Error::other)?
                }
            }
        }
        other => {
            return Err(argument(&format!(
                "unknown backend {other}; expected highs, host-lp or cuda-lp"
            )));
        }
    };
    let serialization = diagnostics.start();
    let output = record.to_json().map_err(io::Error::other)?;
    diagnostics.finish("solve_record_serialization", serialization);
    if let Some(path) = evidence_path {
        let endpoint = optimizer_experiment::lp::LpEndpoint::new(
            &model_bytes,
            selected.to_string(),
            record.clone(),
            diagnostics,
            fallback_reason,
        )
        .map_err(io::Error::other)?;
        let bytes = serde_json::to_vec_pretty(&endpoint).map_err(io::Error::other)?;
        let destination = std::path::Path::new(path);
        let partial = destination.with_extension("partial");
        std::fs::write(&partial, bytes)?;
        std::fs::rename(partial, destination)?;
    }

    let code = match record.termination {
        // A completed mathematical outcome.
        Termination::Optimal
        | Termination::Infeasible
        | Termination::Unbounded
        | Termination::UnboundedOrInfeasible => 0,
        // Interruption is reported distinctly so it is never read as success.
        Termination::Interrupted => 130,
        // A limit or an unresolved outcome.
        Termination::Feasible
        | Termination::TimeLimit
        | Termination::IterationLimit
        | Termination::NodeLimit => 1,
        // A failure is an error, not a solve outcome.
        Termination::NumericalFailure | Termination::BackendFailure | Termination::Unsupported => 2,
    };

    let mut stdout = io::stdout().lock();
    writeln!(stdout, "{output}")
        .and_then(|()| stdout.flush())
        .map_err(|error| io::Error::other(format!("io: stdout: {error}")))?;
    Ok(code)
}

/// Run one solve on an opened device, reporting an availability failure as text.
///
/// The error is a string rather than a typed failure because the caller's only
/// response is to fall back and record why; a richer type would suggest a decision
/// that is not available here.
fn device_solve(
    session: &optimizer_cuda::session::DeviceSession,
    settings: LpSettings,
    model: &Model,
    configuration: &SolveOptions,
    cancel: &CancellationToken,
    diagnostics: &mut optimizer_core::LpDiagnostics,
) -> Result<optimizer_core::SolveRecord, String> {
    let context = session.context();
    let backend = CudaLpBackend::open(context, settings).map_err(|error| error.to_string())?;
    let record = backend
        .solve_with_diagnostics(model, configuration, cancel, None, diagnostics)
        .map_err(|error| error.to_string())?;
    if record.termination == Termination::BackendFailure {
        return Err(record
            .warnings
            .first()
            .cloned()
            .unwrap_or_else(|| "the device backend failed".to_string()));
    }
    Ok(record)
}

pub(crate) fn install_signal_handler(
    cancel: &CancellationToken,
    signalled: &Arc<AtomicBool>,
) -> io::Result<()> {
    let cancel = cancel.clone();
    let signalled = Arc::clone(signalled);
    ctrlc::set_handler(move || {
        signalled.store(true, Ordering::SeqCst);
        cancel.cancel();
    })
    .map_err(io::Error::other)
}
