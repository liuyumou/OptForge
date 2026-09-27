//! Study-only lossless LP endpoint encoding under SPEC-0015.
//!
//! Compact output omits a validation report, never its mathematical checks. Loading
//! untrusted evidence reconstructs that report and invokes the legacy verifier.
use crate::lp::{LpEndpoint, unique_json};
use optimizer_core::{ErrorKind, Model, ValidationError};
use serde::Serialize;

/// Explicit study wire format; ordinary solves always retain legacy output.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum EvidenceFormat {
    /// Original endpoint version and pretty JSON output.
    Legacy,
    /// Minified envelope with independently reconstructible validation.
    CompactV1,
}

impl EvidenceFormat {
    /// Parse the exact study flag value.
    ///
    /// # Errors
    /// Rejects unsupported output formats.
    pub fn parse(value: &str) -> Result<Self, ValidationError> {
        match value {
            "legacy" => Ok(Self::Legacy),
            "compact-v1" => Ok(Self::CompactV1),
            _ => Err(invalid("evidence format must be legacy or compact-v1")),
        }
    }
}

/// Version-one compact envelope. Its embedded endpoint is deliberately private:
/// it is incomplete until host reconstruction and verification have succeeded.
#[derive(Clone, Debug, Serialize)]
pub struct CompactEndpoint {
    schema_version: u32,
    format: String,
    endpoint: LpEndpoint,
    validation_sha256: Option<String>,
}

fn invalid(message: impl Into<String>) -> ValidationError {
    ValidationError::new(ErrorKind::Document, message)
}

fn validation_hash(value: &optimizer_core::ValidationReport) -> Result<String, ValidationError> {
    let bytes = serde_json::to_vec(value).map_err(|e| invalid(e.to_string()))?;
    Ok(crate::sha256::hex(&bytes))
}

impl CompactEndpoint {
    /// Encode an existing endpoint without granting it any new authority.
    /// Untrusted source endpoints must be independently verified before conversion.
    ///
    /// # Errors
    /// Rejects unsupported versions, a report without a candidate or invalid JSON.
    pub fn from_endpoint(mut endpoint: LpEndpoint) -> Result<Self, ValidationError> {
        if !(1..=5).contains(&endpoint.schema_version) {
            return Err(invalid("unsupported legacy endpoint version"));
        }
        if endpoint.record.validation.is_some() && endpoint.record.candidate.is_none() {
            return Err(invalid("validation digest requires a candidate"));
        }
        let validation_sha256 = endpoint
            .record
            .validation
            .take()
            .as_ref()
            .map(validation_hash)
            .transpose()?;
        Ok(Self {
            schema_version: 1,
            format: "lp-compact-v1".into(),
            endpoint,
            validation_sha256,
        })
    }

    /// Parse strict finite object-form JSON, including the original endpoint shape.
    /// Verification remains a separate mandatory step for untrusted evidence.
    ///
    /// # Errors
    /// Rejects malformed, duplicated, missing, unknown or inconsistent fields.
    pub fn from_json(bytes: &[u8]) -> Result<Self, ValidationError> {
        unique_json(bytes)?;
        let shape: serde_json::Value =
            serde_json::from_slice(bytes).map_err(|e| invalid(e.to_string()))?;
        let fields = ["schema_version", "format", "endpoint", "validation_sha256"];
        let map = shape
            .as_object()
            .ok_or_else(|| invalid("compact evidence requires an object"))?;
        if map.len() != fields.len() || fields.iter().any(|key| !map.contains_key(*key)) {
            return Err(invalid("missing or unknown compact evidence field"));
        }
        if shape["schema_version"].as_u64() != Some(1)
            || shape["format"].as_str() != Some("lp-compact-v1")
        {
            return Err(invalid("unsupported compact evidence version/format"));
        }
        if shape["endpoint"]["record"]
            .as_object()
            .is_some_and(|r| r.contains_key("validation"))
        {
            return Err(invalid("compact record must omit validation"));
        }
        let validation_sha256 = match &shape["validation_sha256"] {
            serde_json::Value::Null => None,
            serde_json::Value::String(hash)
                if hash.len() == 64
                    && hash
                        .bytes()
                        .all(|b| b.is_ascii_digit() || (b'a'..=b'f').contains(&b)) =>
            {
                Some(hash.clone())
            }
            _ => return Err(invalid("invalid validation digest")),
        };
        let embedded =
            serde_json::to_vec(&shape["endpoint"]).map_err(|e| invalid(e.to_string()))?;
        let endpoint = LpEndpoint::from_json(&embedded)?;
        if validation_sha256.is_some() && endpoint.record.candidate.is_none() {
            return Err(invalid("validation digest requires a candidate"));
        }
        Ok(Self {
            schema_version: 1,
            format: "lp-compact-v1".into(),
            endpoint,
            validation_sha256,
        })
    }

    /// Reconstruct a report from the exact model and return only verified legacy evidence.
    ///
    /// # Errors
    /// Rejects changed model bytes, validation digests or any legacy verification failure.
    pub fn verify(mut self, model_bytes: &[u8]) -> Result<LpEndpoint, ValidationError> {
        if self.endpoint.model_sha256 != crate::sha256::hex(model_bytes) {
            return Err(invalid("compact model hash differs"));
        }
        if let Some(expected) = &self.validation_sha256 {
            let model = Model::from_json(model_bytes)?;
            let candidate = self
                .endpoint
                .record
                .candidate
                .as_ref()
                .ok_or_else(|| invalid("validation digest requires a candidate"))?;
            let report = model.evaluate(candidate, self.endpoint.record.options.tolerances)?;
            if validation_hash(&report)? != *expected {
                return Err(invalid("recomputed validation digest differs"));
            }
            self.endpoint.record.validation = Some(report);
        }
        self.endpoint.verify(model_bytes)?;
        Ok(self.endpoint)
    }

    /// Serialize minified JSON; this operation alone makes no correctness claim.
    ///
    /// # Errors
    /// Reports serialization failures.
    pub fn to_json(&self) -> Result<Vec<u8>, ValidationError> {
        serde_json::to_vec(self).map_err(|e| invalid(e.to_string()))
    }
}

/// Parse, independently verify and normalize either study evidence format.
///
/// # Errors
/// Rejects malformed documents and every underlying host-verification failure.
pub fn read_verified(
    bytes: &[u8],
    model_bytes: &[u8],
) -> Result<(LpEndpoint, EvidenceFormat), ValidationError> {
    unique_json(bytes)?;
    let shape: serde_json::Value =
        serde_json::from_slice(bytes).map_err(|e| invalid(e.to_string()))?;
    if shape.get("format").is_some() {
        Ok((
            CompactEndpoint::from_json(bytes)?.verify(model_bytes)?,
            EvidenceFormat::CompactV1,
        ))
    } else {
        let endpoint = LpEndpoint::from_json(bytes)?;
        endpoint.verify(model_bytes)?;
        Ok((endpoint, EvidenceFormat::Legacy))
    }
}

/// Encode an endpoint in the requested format without changing legacy serializers.
///
/// # Errors
/// Reports unsupported compact source shapes or serialization failures.
pub fn encode(endpoint: LpEndpoint, format: EvidenceFormat) -> Result<Vec<u8>, ValidationError> {
    match format {
        EvidenceFormat::Legacy => {
            serde_json::to_vec_pretty(&endpoint).map_err(|e| invalid(e.to_string()))
        }
        EvidenceFormat::CompactV1 => CompactEndpoint::from_endpoint(endpoint)?.to_json(),
    }
}
