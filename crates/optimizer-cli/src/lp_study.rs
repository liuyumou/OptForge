//! Bounded study preparation and independent endpoint verification (SPEC-0013).
use crate::input::{argument, read};
use std::ffi::OsString;
use std::io;

pub(crate) fn run(command: &std::ffi::OsStr, args: &[OsString]) -> io::Result<u8> {
    let mut model = None;
    let mut evidence = None;
    let mut instance = None;
    let mut output = None;
    let mut device = None;
    for pair in args.chunks(2) {
        let [key, value] = pair else {
            return Err(argument("each flag requires a value"));
        };
        let slot = match key.to_str() {
            Some("--model") => &mut model,
            Some("--evidence") => &mut evidence,
            Some("--instance") => &mut instance,
            Some("--output") => &mut output,
            Some("--device") => &mut device,
            _ => return Err(argument("unknown LP study flag")),
        };
        if slot.replace(value.as_os_str()).is_some() {
            return Err(argument("duplicate flag"));
        }
    }
    if command == "verify" && instance.is_none() && output.is_none() && device.is_none() {
        let bytes = read(model.ok_or_else(|| argument("--model is required"))?)?;
        let endpoint = optimizer_experiment::lp::LpEndpoint::from_json(&read(
            evidence.ok_or_else(|| argument("--evidence is required"))?,
        )?)
        .map_err(io::Error::other)?;
        endpoint.verify(&bytes).map_err(io::Error::other)?;
        println!("{}", serde_json::to_string(&endpoint.assessment)?);
    } else if command == "replay" && instance.is_none() {
        return replay(
            model.ok_or_else(|| argument("--model is required"))?,
            evidence.ok_or_else(|| argument("--evidence is required"))?,
            output.ok_or_else(|| argument("--output is required"))?,
            device,
        );
    } else if command == "prepare" && model.is_none() && evidence.is_none() && device.is_none() {
        let instance = optimizer_schedule::FlowShopInstance::from_json(&read(
            instance.ok_or_else(|| argument("--instance is required"))?,
        )?)
        .map_err(io::Error::other)?;
        let original = optimizer_schedule::model(&instance).map_err(io::Error::other)?;
        let variables = original
            .document()
            .variables
            .iter()
            .cloned()
            .map(|mut v| {
                v.domain = optimizer_core::Domain::Continuous;
                v
            })
            .collect();
        let relaxed = original.rebound(variables).map_err(io::Error::other)?;
        let json = relaxed.to_json().map_err(io::Error::other)?;
        if json.len() as u64 > crate::input::MAX_INPUT_BYTES {
            return Err(argument("prepared model exceeds input byte limit"));
        }
        std::fs::write(
            output.ok_or_else(|| argument("--output is required"))?,
            json,
        )?;
    } else {
        return Err(argument(
            "expected lp-study prepare, verify or replay with matching flags",
        ));
    }
    Ok(0)
}

/// Re-execute the actually recorded implementation after checking its source evidence.
/// A fallback record replays HiGHS; it cannot reconstruct missing device settings.
fn replay(
    model_path: &std::ffi::OsStr,
    evidence_path: &std::ffi::OsStr,
    output_path: &std::ffi::OsStr,
    device: Option<&std::ffi::OsStr>,
) -> io::Result<u8> {
    use optimizer_core::{CancellationToken, LpDiagnostics, Model, Termination};
    use optimizer_experiment::lp::LpEndpoint;
    use std::io::Write;
    let bytes = read(model_path)?;
    let original = LpEndpoint::from_json(&read(evidence_path)?).map_err(io::Error::other)?;
    original.verify(&bytes).map_err(io::Error::other)?;
    let selected = original.record.backend.as_str();
    let model = Model::from_json(&bytes).map_err(io::Error::other)?;
    let token = CancellationToken::new();
    crate::solve::install_signal_handler(
        &token,
        &std::sync::Arc::new(std::sync::atomic::AtomicBool::new(false)),
    )?;
    let mut diagnostics = LpDiagnostics::new(true, false);
    diagnostics.device_buffer_limit_bytes = original.diagnostics.device_buffer_limit_bytes;
    if let Some(execution) = &original.record.lp_execution {
        let image = std::fs::read(optimizer_lp_cuda::tuned::code_object_path())?;
        if optimizer_core::sha256::hex(&image) != execution.code_object_sha256 {
            return Err(argument("recorded tuned code object differs"));
        }
        diagnostics.execution = Some(optimizer_core::LpExecutionDiagnostics::new(
            execution.settings,
        ));
    }
    let options = &original.record.options;
    let settings = || {
        original
            .record
            .lp_settings
            .ok_or_else(|| argument("record lacks LP settings"))
    };
    let mut fallback = None;
    // Refuse an existing destination before any device work, preserving source artifacts.
    if std::path::Path::new(output_path).exists() {
        return Err(argument("replay output already exists"));
    }
    let record = match selected {
        "highs" => optimizer_highs::HighsBackend::new()
            .solve_with_diagnostics(&model, options, &token, None, &mut diagnostics)
            .map_err(io::Error::other)?,
        "host-lp" => optimizer_lp::HostLpBackend::new(settings()?)
            .map_err(io::Error::other)?
            .solve_with_diagnostics(&model, options, &token, None, &mut diagnostics)
            .map_err(io::Error::other)?,
        "cuda-lp" | "cuda-lp-matched" | "cuda-lp-tuned" => {
            let name = device
                .and_then(|d| d.to_str())
                .ok_or_else(|| argument("device replay requires --device"))?;
            let device = optimizer_core::Device::parse(name).map_err(io::Error::other)?;
            let settings = settings()?;
            let result = match crate::registry::open_device(&device)? {
                Some(session) => crate::solve::device_solve(
                    &session,
                    selected == "cuda-lp-matched",
                    original.record.lp_execution.as_ref().map(|e| e.settings),
                    settings,
                    &model,
                    options,
                    &token,
                    &mut diagnostics,
                ),
                None => Err("no device was opened".into()),
            };
            match result {
                Ok(record) => record,
                Err(reason) => {
                    fallback = Some(reason);
                    diagnostics.dual = None;
                    optimizer_highs::HighsBackend::new()
                        .solve_with_diagnostics(&model, options, &token, None, &mut diagnostics)
                        .map_err(io::Error::other)?
                }
            }
        }
        _ => return Err(argument("unknown recorded LP backend")),
    };
    let endpoint = LpEndpoint::new(&bytes, selected.into(), record, diagnostics, fallback)
        .map_err(io::Error::other)?;
    endpoint.verify(&bytes).map_err(io::Error::other)?;
    let output = serde_json::to_vec_pretty(&endpoint).map_err(io::Error::other)?;
    let mut file = std::fs::OpenOptions::new()
        .write(true)
        .create_new(true)
        .open(output_path)?;
    file.write_all(&output)?;
    file.sync_all()?;
    println!("{}", serde_json::to_string(&endpoint.assessment)?);
    Ok(match endpoint.record.termination {
        Termination::Optimal => 0,
        Termination::Interrupted => 130,
        Termination::TimeLimit | Termination::IterationLimit | Termination::Feasible => 1,
        _ => 2,
    })
}
