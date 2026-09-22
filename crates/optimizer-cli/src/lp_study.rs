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
    let mut batch = None;
    let mut index = None;
    let mut out = None;
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
            Some("--batch") => &mut batch,
            Some("--index") => &mut index,
            Some("--out") => &mut out,
            _ => return Err(argument("unknown LP study flag")),
        };
        if slot.replace(value.as_os_str()).is_some() {
            return Err(argument("duplicate flag"));
        }
    }
    if command == "external-certify" || command == "external-verify" {
        let bytes = read(model.ok_or_else(|| argument("--model required"))?)?;
        let evidence = read(evidence.ok_or_else(|| argument("--evidence required"))?)?;
        if command == "external-certify" {
            let witness = optimizer_experiment::lp_external::ExternalWitness::from_json(&evidence)
                .map_err(io::Error::other)?;
            let endpoint =
                optimizer_experiment::lp_external::ExternalEndpoint::new(witness, &bytes)
                    .map_err(io::Error::other)?;
            let output = output.ok_or_else(|| argument("--output required"))?;
            let mut file = std::fs::OpenOptions::new()
                .write(true)
                .create_new(true)
                .open(output)?;
            std::io::Write::write_all(
                &mut file,
                &serde_json::to_vec_pretty(&endpoint).map_err(io::Error::other)?,
            )?;
        } else {
            let endpoint =
                optimizer_experiment::lp_external::ExternalEndpoint::from_json(&evidence)
                    .map_err(io::Error::other)?;
            endpoint.verify(&bytes).map_err(io::Error::other)?;
            println!("{}", serde_json::to_string(&endpoint.assessment)?);
        }
    } else if command == "verify"
        && instance.is_none()
        && output.is_none()
        && device.is_none()
        && batch.is_none()
        && index.is_none()
        && out.is_none()
    {
        let bytes = read(model.ok_or_else(|| argument("--model is required"))?)?;
        let endpoint = optimizer_experiment::lp::LpEndpoint::from_json(&read(
            evidence.ok_or_else(|| argument("--evidence is required"))?,
        )?)
        .map_err(io::Error::other)?;
        endpoint.verify(&bytes).map_err(io::Error::other)?;
        println!("{}", serde_json::to_string(&endpoint.assessment)?);
    } else if command == "replay"
        && instance.is_none()
        && batch.is_none()
        && index.is_none()
        && out.is_none()
    {
        return replay(
            model.ok_or_else(|| argument("--model is required"))?,
            evidence.ok_or_else(|| argument("--evidence is required"))?,
            output.ok_or_else(|| argument("--output is required"))?,
            device,
        );
    } else if command == "prepare"
        && model.is_none()
        && evidence.is_none()
        && device.is_none()
        && batch.is_none()
        && index.is_none()
        && out.is_none()
    {
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
    } else if command == "materialize"
        && evidence.is_none()
        && instance.is_none()
        && output.is_none()
        && device.is_none()
    {
        // SPEC-0014 requirement 16: the deterministic pure materialization
        // function, exposed so a variant's bytes can be inspected or hashed
        // without a device.
        let bytes = read(model.ok_or_else(|| argument("--model is required"))?)?;
        let base = optimizer_core::Model::from_json(&bytes).map_err(io::Error::other)?;
        let batch_bytes = read(batch.ok_or_else(|| argument("--batch is required"))?)?;
        let request = optimizer_experiment::lp_batch::BatchRequest::from_json(&batch_bytes)
            .map_err(io::Error::other)?;
        let index = index.ok_or_else(|| argument("--index is required"))?;
        let index = index
            .to_str()
            .and_then(|value| value.parse::<u32>().ok())
            .ok_or_else(|| argument("--index must be a solve index"))?;
        let (_, materialized, sha256) =
            optimizer_experiment::lp_batch::materialize(&base, &request, index)
                .map_err(io::Error::other)?;
        optimizer_experiment::lp_batch::write_evidence_file(
            std::path::Path::new(out.ok_or_else(|| argument("--out is required"))?),
            &materialized,
        )
        .map_err(io::Error::other)?;
        println!("{sha256}");
    } else if command == "verify-batch"
        && instance.is_none()
        && output.is_none()
        && device.is_none()
        && index.is_none()
        && out.is_none()
    {
        // Requirement 17: bitwise identity is decided from the retained
        // evidence directory alone.
        let model_bytes = read(model.ok_or_else(|| argument("--model is required"))?)?;
        let batch_bytes = read(batch.ok_or_else(|| argument("--batch is required"))?)?;
        let dir =
            std::path::PathBuf::from(evidence.ok_or_else(|| argument("--evidence is required"))?);
        let endpoint = optimizer_experiment::lp_batch::BatchEndpoint::from_json(&read(
            dir.join("batch.json").as_os_str(),
        )?)
        .map_err(io::Error::other)?;
        endpoint
            .verify(&model_bytes, &batch_bytes, &dir)
            .map_err(io::Error::other)?;
        println!(
            "{}",
            serde_json::json!({
                "verified": true,
                "solves": endpoint.solves.len(),
                "payload_sha256": endpoint.payload_sha256,
            })
        );
    } else {
        return Err(argument(
            "expected lp-study prepare, verify, replay, materialize or verify-batch with matching flags",
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
        let path = if original.record.lp_precision.is_some() {
            optimizer_lp_cuda::precision::code_object_path()
        } else {
            optimizer_lp_cuda::tuned::code_object_path()
        };
        let image = std::fs::read(path)?;
        if optimizer_core::sha256::hex(&image) != execution.code_object_sha256 {
            return Err(argument("recorded tuned code object differs"));
        }
        diagnostics.execution = Some(optimizer_core::LpExecutionDiagnostics::new(
            execution.settings,
        ));
    }
    diagnostics.precision = original
        .record
        .lp_precision
        .clone()
        .map(optimizer_core::LpPrecisionDiagnostics::new);
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
