//! Bounded study preparation and independent endpoint verification (SPEC-0013).
use crate::input::{argument, read};
use optimizer_experiment::lp_compact::{EvidenceFormat, read_verified};
use std::ffi::OsString;
use std::io;

pub(crate) fn run(command: &std::ffi::OsStr, args: &[OsString]) -> io::Result<u8> {
    let mut model_limit = None;
    let mut costs = None;
    let mut format = None;
    let mut context_mode = None;
    let mut setup_receipt = None;
    let mut setup_source = None;
    let mut filtered = Vec::new();
    for pair in args.chunks(2) {
        let [key, value] = pair else {
            return Err(argument("each flag requires a value"));
        };
        match key.to_str() {
            Some("--cuda-context") => {
                if context_mode
                    .replace(crate::lp_setup::parse_mode(value)?)
                    .is_some()
                {
                    return Err(argument("duplicate CUDA context"));
                }
            }
            Some("--setup-receipt") => {
                if setup_receipt.replace(std::path::Path::new(value)).is_some() {
                    return Err(argument("duplicate setup receipt"));
                }
            }
            Some("--setup-source") => {
                if setup_source.replace(std::path::Path::new(value)).is_some() {
                    return Err(argument("duplicate setup source"));
                }
            }

            Some("--model-byte-limit") => {
                let limit = value
                    .to_str()
                    .and_then(|v| v.parse::<u64>().ok())
                    .filter(|v| *v > 0 && *v <= 128 * 1024 * 1024)
                    .ok_or_else(|| {
                        argument("study model limit must be between 1 and 134217728 bytes")
                    })?;
                if model_limit.replace(limit).is_some() {
                    return Err(argument("duplicate model limit"));
                }
            }
            Some("--evidence-format") => {
                let value = value
                    .to_str()
                    .ok_or_else(|| argument("evidence format must be UTF-8"))?;
                let value = EvidenceFormat::parse(value).map_err(io::Error::other)?;
                if format.replace(value).is_some() {
                    return Err(argument("duplicate evidence format"));
                }
            }
            Some("--cost-profile") => {
                if costs.replace(value).is_some() {
                    return Err(argument("duplicate cost profile"));
                }
            }
            _ => filtered.extend_from_slice(pair),
        }
    }
    let supported = matches!(
        command.to_str(),
        Some("solve" | "verify" | "external-certify" | "external-verify")
    );
    if (!supported && costs.is_some())
        || (!supported && command != "replay" && command != "transcode" && model_limit.is_some())
    {
        return Err(argument(
            "unsupported study input/profile options for this command",
        ));
    }
    if format.is_some() && !matches!(command.to_str(), Some("solve" | "replay" | "transcode")) {
        return Err(argument(
            "evidence format requires solve, replay or transcode",
        ));
    }
    if command == "transcode" && format.is_none() {
        return Err(argument("transcode requires --evidence-format"));
    }
    if command == "solve" && !filtered.iter().any(|v| v == "--lp-evidence") {
        return Err(argument("study solve requires --lp-evidence"));
    }
    let flag = |name: &str| {
        filtered
            .chunks(2)
            .find(|pair| pair[0] == name)
            .map(|pair| pair[1].as_os_str())
    };
    if let Some(source) = setup_source {
        if command != "replay" {
            return Err(argument("setup source requires replay"));
        }
        let evidence =
            flag("--evidence").ok_or_else(|| argument("setup replay requires evidence"))?;
        let recorded = crate::lp_setup::source_mode(source, std::path::Path::new(evidence))?;
        if context_mode.is_some_and(|m| m != recorded) {
            return Err(argument("CUDA context differs from setup source"));
        }
        context_mode = Some(recorded);
    }
    if context_mode.is_some() != setup_receipt.is_some() {
        return Err(argument(
            "explicit CUDA context and setup receipt are required together",
        ));
    }
    if let Some(path) = setup_receipt {
        if !matches!(command.to_str(), Some("solve" | "replay")) || path.exists() {
            return Err(argument(
                "setup receipt requires solve/replay and a new output path",
            ));
        }
        if command == "solve" && flag("--backend") != Some(std::ffi::OsStr::new("cuda-lp-tuned")) {
            return Err(argument("setup observation requires cuda-lp-tuned"));
        }
    }
    if setup_receipt.is_some() && command == "replay" {
        let path = flag("--evidence").ok_or_else(|| argument("setup replay requires evidence"))?;
        let bytes = crate::input::read_with_limit(
            path,
            model_limit.unwrap_or(crate::input::MAX_INPUT_BYTES),
        )?;
        let value: serde_json::Value = serde_json::from_slice(&bytes)?;
        let payload = value.get("endpoint").unwrap_or(&value);
        if payload
            .get("record")
            .and_then(|r| r.get("backend"))
            .and_then(|b| b.as_str())
            != Some("cuda-lp-tuned")
        {
            return Err(argument("setup replay requires tuned evidence"));
        }
    }
    let mode = context_mode.unwrap_or_default();
    if mode == optimizer_cuda::setup::ContextMode::PrimaryExperimental
        && std::env::var("AI_OPTIMIZER_GPU_LEASE").as_deref() != Ok("inherited")
    {
        return Err(argument(
            "primary-context study requires inherited shared host lease",
        ));
    }
    let endpoint_path = flag(if command == "solve" {
        "--lp-evidence"
    } else {
        "--output"
    })
    .map(std::path::Path::new);
    if setup_receipt.is_some_and(|p| Some(p) == endpoint_path) {
        return Err(argument("setup receipt and endpoint must differ"));
    }
    let device = flag("--device")
        .map(|v| v.to_string_lossy().into_owned())
        .unwrap_or_default();
    let setup = setup_receipt
        .map(|_| optimizer_cuda::setup::SetupObservation::begin().map_err(io::Error::other))
        .transpose()?;
    let session = costs
        .map(|_| optimizer_core::lp_cost::Session::begin().map_err(io::Error::other))
        .transpose()?;
    let result = if command == "solve" {
        crate::solve::solve_with_setup(
            &filtered,
            model_limit.unwrap_or(crate::input::MAX_INPUT_BYTES),
            format.unwrap_or(EvidenceFormat::Legacy),
            mode,
        )
    } else {
        run_inner(
            command,
            &filtered,
            model_limit.unwrap_or(crate::input::MAX_INPUT_BYTES),
            format,
            mode,
        )
    };
    let setup_result = if let (Some(observer), Some(path)) = (setup, setup_receipt) {
        crate::lp_setup::finish(observer, mode, device, path, endpoint_path, &result)
    } else {
        Ok(())
    };
    if let (Some(session), Some(path)) = (session, costs) {
        let profile = session.finish();
        let mut file = std::fs::OpenOptions::new()
            .write(true)
            .create_new(true)
            .open(path)?;
        std::io::Write::write_all(
            &mut file,
            &serde_json::to_vec(&profile).map_err(io::Error::other)?,
        )?;
    }
    setup_result?;
    result
}

fn run_inner(
    command: &std::ffi::OsStr,
    args: &[OsString],
    model_limit: u64,
    format: Option<EvidenceFormat>,
    mode: optimizer_cuda::setup::ContextMode,
) -> io::Result<u8> {
    let _cost = optimizer_core::lp_cost::scope("study_verification");
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
        let bytes = crate::input::read_with_limit(
            model.ok_or_else(|| argument("--model required"))?,
            model_limit,
        )?;
        let evidence = crate::input::read_with_limit(
            evidence.ok_or_else(|| argument("--evidence required"))?,
            model_limit,
        )?;
        let version = serde_json::from_slice::<serde_json::Value>(&evidence)
            .map_err(io::Error::other)?
            .get("schema_version")
            .and_then(|v| v.as_u64());
        use optimizer_experiment::lp_external::{ExternalEndpoint, ExternalWitness};
        use optimizer_experiment::lp_external_v2::{ExternalEndpointV2, ExternalWitnessV2};
        let serialized = if command == "external-certify" {
            match version {
                Some(1) => serde_json::to_vec_pretty(
                    &ExternalEndpoint::new(
                        ExternalWitness::from_json(&evidence).map_err(io::Error::other)?,
                        &bytes,
                    )
                    .map_err(io::Error::other)?,
                )?,
                Some(2) => serde_json::to_vec_pretty(
                    &ExternalEndpointV2::new(
                        ExternalWitnessV2::from_json(&evidence).map_err(io::Error::other)?,
                        &bytes,
                    )
                    .map_err(io::Error::other)?,
                )?,
                _ => return Err(argument("unsupported external witness version")),
            }
        } else {
            match version {
                Some(1) => {
                    let e = ExternalEndpoint::from_json(&evidence).map_err(io::Error::other)?;
                    e.verify(&bytes).map_err(io::Error::other)?;
                    serde_json::to_vec(&e.assessment)?
                }
                Some(2) => {
                    let e = ExternalEndpointV2::from_json(&evidence).map_err(io::Error::other)?;
                    e.verify(&bytes).map_err(io::Error::other)?;
                    serde_json::to_vec(&e.assessment)?
                }
                _ => return Err(argument("unsupported external endpoint version")),
            }
        };
        if command == "external-certify" {
            let _cost = optimizer_core::lp_cost::scope("endpoint_write");
            let mut file = std::fs::OpenOptions::new()
                .write(true)
                .create_new(true)
                .open(output.ok_or_else(|| argument("--output required"))?)?;
            std::io::Write::write_all(&mut file, &serialized)?;
        } else {
            println!("{}", String::from_utf8_lossy(&serialized));
        }
    } else if command == "verify"
        && instance.is_none()
        && output.is_none()
        && device.is_none()
        && batch.is_none()
        && index.is_none()
        && out.is_none()
    {
        let bytes = crate::input::read_with_limit(
            model.ok_or_else(|| argument("--model is required"))?,
            model_limit,
        )?;
        let (endpoint, _) = read_verified(
            &crate::input::read_with_limit(
                evidence.ok_or_else(|| argument("--evidence is required"))?,
                model_limit,
            )?,
            &bytes,
        )
        .map_err(io::Error::other)?;
        println!("{}", serde_json::to_string(&endpoint.assessment)?);
    } else if command == "transcode"
        && instance.is_none()
        && device.is_none()
        && batch.is_none()
        && index.is_none()
        && out.is_none()
    {
        let destination = crate::study_output::AtomicOutput::new(std::path::Path::new(
            output.ok_or_else(|| argument("--output is required"))?,
        ))?;
        let bytes = crate::input::read_with_limit(
            model.ok_or_else(|| argument("--model is required"))?,
            model_limit,
        )?;
        let source = crate::input::read_with_limit(
            evidence.ok_or_else(|| argument("--evidence is required"))?,
            model_limit,
        )?;
        let (endpoint, _) = read_verified(&source, &bytes).map_err(io::Error::other)?;
        let summary = serde_json::to_string(&endpoint.assessment).map_err(io::Error::other)?;
        let encoded = optimizer_experiment::lp_compact::encode(
            endpoint,
            format.expect("transcode format checked"),
        )
        .map_err(io::Error::other)?;
        destination.publish(&encoded)?;
        println!("{summary}");
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
            model_limit,
            format,
            mode,
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
            "expected lp-study prepare, solve, verify, replay, transcode, materialize or verify-batch with matching flags",
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
    model_limit: u64,
    format: Option<EvidenceFormat>,
    mode: optimizer_cuda::setup::ContextMode,
) -> io::Result<u8> {
    use optimizer_core::{CancellationToken, LpDiagnostics, Model, Termination};
    use optimizer_experiment::lp::LpEndpoint;
    use std::io::Write;
    let bytes = crate::input::read_with_limit(model_path, model_limit)?;
    let (original, source_format) = read_verified(
        &crate::input::read_with_limit(evidence_path, model_limit)?,
        &bytes,
    )
    .map_err(io::Error::other)?;
    let format = format.unwrap_or(source_format);
    let compact_output = if format == EvidenceFormat::CompactV1 {
        Some(crate::study_output::AtomicOutput::new(
            std::path::Path::new(output_path),
        )?)
    } else {
        None
    };
    let selected = original.record.backend.as_str();
    if mode != optimizer_cuda::setup::ContextMode::User && selected != "cuda-lp-tuned" {
        return Err(argument("primary-context replay requires tuned evidence"));
    }
    let model = Model::from_json(&bytes).map_err(io::Error::other)?;
    let token = CancellationToken::new();
    crate::solve::install_signal_handler(
        &token,
        &std::sync::Arc::new(std::sync::atomic::AtomicBool::new(false)),
    )?;
    let mut diagnostics = LpDiagnostics::new(true, false);
    diagnostics.device_buffer_limit_bytes = original.diagnostics.device_buffer_limit_bytes;
    if let Some(execution) = &original.record.lp_execution {
        let path =
            if original.record.lp_precision.is_some() || original.record.lp_adaptive.is_some() {
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
    diagnostics.adaptive = original
        .record
        .lp_adaptive
        .clone()
        .map(optimizer_core::LpAdaptiveDiagnostics::new);
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
            let result = match crate::registry::open_device_with_context(&device, mode)? {
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
    let summary = serde_json::to_string(&endpoint.assessment)?;
    let termination = endpoint.record.termination;
    let output =
        optimizer_experiment::lp_compact::encode(endpoint, format).map_err(io::Error::other)?;
    if let Some(destination) = compact_output {
        destination.publish(&output)?;
    } else {
        let mut file = std::fs::OpenOptions::new()
            .write(true)
            .create_new(true)
            .open(output_path)?;
        file.write_all(&output)?;
        file.sync_all()?;
    }
    println!("{summary}");
    Ok(match termination {
        Termination::Optimal => 0,
        Termination::Interrupted => 130,
        Termination::TimeLimit | Termination::IterationLimit | Termination::Feasible => 1,
        _ => 2,
    })
}
