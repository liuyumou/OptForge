//! Separate study setup receipts; numerical endpoints keep their old formats.
use optimizer_cuda::setup::{ContextMode, SetupEvent, SetupObservation};
use serde::{Deserialize, Serialize};
use std::io;
use std::path::Path;

#[derive(Debug, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub(crate) struct Receipt {
    schema_version: u32,
    requested: ContextMode,
    observed: Option<ContextMode>,
    device: String,
    events: Vec<SetupEvent>,
    status: String,
    endpoint_sha256: Option<String>,
    #[serde(deserialize_with = "Option::<String>::deserialize")]
    error: Option<String>,
}
pub(crate) fn parse_mode(value: &std::ffi::OsStr) -> io::Result<ContextMode> {
    match value.to_str() {
        Some("user") => Ok(ContextMode::User),
        Some("primary-experimental") => Ok(ContextMode::PrimaryExperimental),
        _ => Err(io::Error::other(
            "expected CUDA context user|primary-experimental",
        )),
    }
}
pub(crate) fn source_mode(path: &Path, endpoint: &Path) -> io::Result<ContextMode> {
    let receipt: Receipt = serde_json::from_slice(&crate::input::read(path.as_os_str())?)?;
    if receipt.schema_version != 1
        || receipt.events.len() > 4096
        || receipt.status != "passed"
        || receipt.observed != Some(receipt.requested)
        || !optimizer_cuda::setup::complete(receipt.requested, &receipt.events)
        || receipt.error.is_some()
        || receipt.endpoint_sha256
            != Some(optimizer_core::sha256::hex(&crate::input::read_with_limit(
                endpoint.as_os_str(),
                128 * 1024 * 1024,
            )?))
    {
        return Err(io::Error::other(
            "setup source receipt does not bind a completed lifecycle and endpoint",
        ));
    }
    Ok(receipt.requested)
}
pub(crate) fn finish(
    observer: SetupObservation,
    mode: ContextMode,
    device: String,
    receipt_path: &Path,
    endpoint_path: Option<&Path>,
    result: &io::Result<u8>,
) -> io::Result<()> {
    let events = observer.finish();
    let complete = optimizer_cuda::setup::complete(mode, &events);
    let receipt = Receipt {
        schema_version: 1,
        requested: mode,
        observed: complete.then_some(mode),
        device,
        events,
        status: if complete && result.is_ok() {
            "passed"
        } else {
            "failed"
        }
        .into(),
        endpoint_sha256: endpoint_path
            .filter(|p| p.is_file())
            .map(std::fs::read)
            .transpose()?
            .map(|b| optimizer_core::sha256::hex(&b)),
        error: result.as_ref().err().map(ToString::to_string),
    };
    let output = crate::study_output::AtomicOutput::new(receipt_path)?;
    output.publish(&serde_json::to_vec_pretty(&receipt)?)?;
    if !complete && result.is_ok() {
        return Err(io::Error::other(
            "incomplete or failed setup lifecycle; see setup receipt",
        ));
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn setup_source_binds_policy_bits_and_cleanup_order() {
        let root =
            std::env::temp_dir().join(format!("optimizer-setup-replay-{}", std::process::id()));
        std::fs::create_dir(&root).unwrap();
        let endpoint = root.join("endpoint.json");
        let path = root.join("setup.json");
        std::fs::write(&endpoint, b"{}").unwrap();
        let mut receipt = Receipt {
            schema_version: 1,
            requested: ContextMode::User,
            observed: Some(ContextMode::User),
            device: "GPU-test".into(),
            events: vec![
                SetupEvent {
                    operation: "context_create_user".into(),
                    ok: true,
                    detail: "GPU-test".into(),
                },
                SetupEvent {
                    operation: "context_destroy_user".into(),
                    ok: true,
                    detail: "0".into(),
                },
            ],
            status: "passed".into(),
            endpoint_sha256: Some(optimizer_core::sha256::hex(b"{}")),
            error: None,
        };
        let save = |r: &Receipt| std::fs::write(&path, serde_json::to_vec(r).unwrap()).unwrap();
        save(&receipt);
        assert_eq!(source_mode(&path, &endpoint).unwrap(), ContextMode::User);
        let mut missing = serde_json::to_value(&receipt).unwrap();
        missing.as_object_mut().unwrap().remove("error");
        std::fs::write(&path, serde_json::to_vec(&missing).unwrap()).unwrap();
        assert!(source_mode(&path, &endpoint).is_err());
        let mut oversized = serde_json::to_value(&receipt).unwrap();
        let events = oversized["events"].as_array_mut().unwrap();
        for _ in 0..4095 {
            events.insert(
                1,
                serde_json::json!({"operation": "memory_free", "ok": true, "detail": "0"}),
            );
        }
        std::fs::write(&path, serde_json::to_vec(&oversized).unwrap()).unwrap();
        assert!(source_mode(&path, &endpoint).is_err());
        oversized["events"].as_array_mut().unwrap().remove(1);
        std::fs::write(&path, serde_json::to_vec(&oversized).unwrap()).unwrap();
        assert_eq!(source_mode(&path, &endpoint).unwrap(), ContextMode::User);
        receipt.events.reverse();
        save(&receipt);
        assert!(source_mode(&path, &endpoint).is_err());
        receipt.events.reverse();
        receipt.events[1].ok = false;
        save(&receipt);
        assert!(source_mode(&path, &endpoint).is_err());
        receipt.events[1].ok = true;
        save(&receipt);
        std::fs::write(&endpoint, b"{ }").unwrap();
        assert!(source_mode(&path, &endpoint).is_err());
        std::fs::write(&endpoint, b"{}").unwrap();
        let mut unknown = serde_json::to_value(&receipt).unwrap();
        unknown["extra"] = true.into();
        std::fs::write(&path, serde_json::to_vec(&unknown).unwrap()).unwrap();
        assert!(source_mode(&path, &endpoint).is_err());
        std::fs::remove_dir_all(root).unwrap();
    }
}
