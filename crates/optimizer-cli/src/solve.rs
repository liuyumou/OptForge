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
    Backend, Basis, CancellationToken, Candidate, Model, SolveOptions, Termination,
};
use optimizer_highs::HighsBackend;

use crate::input::{argument, read};

pub(crate) fn solve(options: &[OsString]) -> io::Result<u8> {
    let mut model_path = None;
    let mut config_path = None;
    let mut candidate_path = None;
    let mut basis_path = None;
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
            "--candidate" => &mut candidate_path,
            "--basis" => &mut basis_path,
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

    let model = Model::from_json(&read(model_path)?).map_err(io::Error::other)?;
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

    let record = HighsBackend::new()
        .solve(&model, &configuration, &cancel, warm_start)
        .map_err(io::Error::other)?;
    let output = record.to_json().map_err(io::Error::other)?;

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
