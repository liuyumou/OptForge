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
use optimizer_experiment::lp_compact::EvidenceFormat;

pub(crate) fn solve(options: &[OsString]) -> io::Result<u8> {
    solve_with_model_limit(options, crate::input::MAX_INPUT_BYTES)
}

pub(crate) fn solve_with_model_limit(options: &[OsString], model_limit: u64) -> io::Result<u8> {
    solve_with_output(options, model_limit, EvidenceFormat::Legacy)
}

pub(crate) fn solve_with_output(
    options: &[OsString],
    model_limit: u64,
    format: EvidenceFormat,
) -> io::Result<u8> {
    solve_with_setup(
        options,
        model_limit,
        format,
        optimizer_cuda::setup::ContextMode::User,
    )
}

pub(crate) fn solve_with_setup(
    options: &[OsString],
    model_limit: u64,
    format: EvidenceFormat,
    mode: optimizer_cuda::setup::ContextMode,
) -> io::Result<u8> {
    let _cost = optimizer_core::lp_cost::scope("solve");
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
    let mut execution_path = None;
    let mut precision_path = None;
    let mut adaptive_path = None;
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
            "--lp-execution" => &mut execution_path,
            "--lp-precision" => &mut precision_path,
            "--lp-adaptive" => &mut adaptive_path,
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
    let compact_output = if format == EvidenceFormat::CompactV1 {
        let path =
            evidence_path.ok_or_else(|| argument("compact output requires --lp-evidence"))?;
        Some(crate::study_output::AtomicOutput::new(
            std::path::Path::new(path),
        )?)
    } else {
        None
    };
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
    let model_bytes = crate::input::read_with_limit(model_path, model_limit)?;
    let input =
        optimizer_experiment::lp::LpInput::from_bytes(&model_bytes).map_err(io::Error::other)?;
    let model = input.model();
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
    let execution = match (selected, execution_path) {
        ("cuda-lp-tuned", Some(path)) => Some(
            optimizer_core::Fp64ExecutionSettings::from_json(&read(path)?)
                .map_err(io::Error::other)?,
        ),
        ("cuda-lp-tuned", None) => return Err(argument("cuda-lp-tuned requires --lp-execution")),
        (_, Some(_)) => return Err(argument("--lp-execution requires cuda-lp-tuned")),
        (_, None) => None,
    };
    if adaptive_path.is_some() && precision_path.is_some() {
        return Err(argument(
            "--lp-adaptive and --lp-precision are mutually exclusive",
        ));
    }
    let adaptive = adaptive_path
        .map(|path| {
            if selected != "cuda-lp-tuned" {
                return Err(argument("--lp-adaptive requires cuda-lp-tuned"));
            }
            let value = optimizer_core::LpAdaptiveSettings::from_json(&read(path)?)
                .map_err(io::Error::other)?;
            value
                .validate_execution(execution.expect("explicit tuned execution"))
                .map_err(io::Error::other)?;
            Ok(value)
        })
        .transpose()?;
    diagnostics.adaptive = adaptive.map(optimizer_core::LpAdaptiveDiagnostics::new);
    let precision = precision_path
        .map(|path| {
            if selected != "cuda-lp-tuned" {
                return Err(argument("--lp-precision requires cuda-lp-tuned"));
            }
            let p = optimizer_core::LpPrecisionSettings::from_json(&read(path)?)
                .map_err(io::Error::other)?;
            p.validate_execution(execution.expect("explicit tuned settings"))
                .map_err(io::Error::other)?;
            Ok(p)
        })
        .transpose()?;
    diagnostics.precision = precision.map(optimizer_core::LpPrecisionDiagnostics::new);
    diagnostics.execution = execution.map(optimizer_core::LpExecutionDiagnostics::new);
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
                    model,
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
                    model,
                    &configuration,
                    &cancel,
                    warm_start,
                    &mut diagnostics,
                )
                .map_err(io::Error::other)?
        }
        "cuda-lp" | "cuda-lp-matched" | "cuda-lp-tuned" => {
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
            let session_result = crate::registry::open_device_with_context(&device, mode);
            diagnostics.finish("device_context", opening);
            match session_result? {
                Some(session) => {
                    match device_solve(
                        &session,
                        selected == "cuda-lp-matched",
                        execution,
                        settings,
                        model,
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
                                    model,
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
                            model,
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
                "unknown backend {other}; expected highs, host-lp, cuda-lp, cuda-lp-matched or cuda-lp-tuned"
            )));
        }
    };
    let mut output = if format == EvidenceFormat::Legacy {
        let serialization = diagnostics.start();
        let _cost = optimizer_core::lp_cost::scope("solve_record_serialization");
        let output = record.to_json().map_err(io::Error::other)?;
        diagnostics.finish("solve_record_serialization", serialization);
        Some(output)
    } else {
        None
    };
    if let Some(path) = evidence_path {
        let endpoint = input
            .into_endpoint(
                selected.to_string(),
                record.clone(),
                diagnostics,
                fallback_reason,
            )
            .map_err(io::Error::other)?;
        if format == EvidenceFormat::CompactV1 {
            output = Some(serde_json::to_string(&endpoint.assessment).map_err(io::Error::other)?);
        }
        let bytes = {
            let _cost = optimizer_core::lp_cost::scope("endpoint_serialization");
            optimizer_experiment::lp_compact::encode(endpoint, format).map_err(io::Error::other)?
        };
        let _cost = optimizer_core::lp_cost::scope("endpoint_write");
        if let Some(destination) = compact_output {
            destination.publish(&bytes)?;
        } else {
            let destination = std::path::Path::new(path);
            let partial = destination.with_extension("partial");
            std::fs::write(&partial, bytes)?;
            std::fs::rename(partial, destination)?;
        }
    }

    let code = exit_code(record.termination);

    let _cost = optimizer_core::lp_cost::scope("record_output");
    let mut stdout = io::stdout().lock();
    let output = output.expect("legacy record or compact assessment prepared");
    writeln!(stdout, "{output}")
        .and_then(|()| stdout.flush())
        .map_err(|error| io::Error::other(format!("io: stdout: {error}")))?;
    Ok(code)
}

/// The exit status of one solve outcome, shared by `solve` and `solve-batch`
/// so both map the same termination the same way.
pub(crate) fn exit_code(termination: Termination) -> u8 {
    match termination {
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
    }
}

/// Run one solve on an opened device, reporting an availability failure as text.
///
/// The error is a string rather than a typed failure because the caller's only
/// response is to fall back and record why; a richer type would suggest a decision
/// that is not available here.
#[allow(clippy::too_many_arguments)]
pub(crate) fn device_solve(
    session: &optimizer_cuda::session::DeviceSession,
    matched: bool,
    execution: Option<optimizer_core::Fp64ExecutionSettings>,
    settings: LpSettings,
    model: &Model,
    configuration: &SolveOptions,
    cancel: &CancellationToken,
    diagnostics: &mut optimizer_core::LpDiagnostics,
) -> Result<optimizer_core::SolveRecord, String> {
    let context = session.context();
    let backend = if let Some(execution) = execution {
        if let Some(a) = &diagnostics.adaptive {
            CudaLpBackend::open_adaptive(context, settings, execution, a.settings.clone())
        } else if let Some(p) = &diagnostics.precision {
            CudaLpBackend::open_precision(context, settings, execution, p.settings.clone())
        } else {
            CudaLpBackend::open_tuned(context, settings, execution)
        }
    } else if matched {
        CudaLpBackend::open_matched(context, settings)
    } else {
        CudaLpBackend::open(context, settings)
    }
    .map_err(|error| error.to_string())?;
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
