//! Explicit experimental FP64 execution contract (SPEC-0012, ADR-0017).
use crate::serde_strict::deserialize_object;
use crate::{ErrorKind, ValidationError};
use serde::{Deserialize, Serialize};

/// Working-buffer allocation lifetime.
#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum WorkingAllocation {
    /// Reallocate at each host check.
    PerCheck,
    /// Retain buffers for the solve.
    Resident,
}
/// Host-to-device state upload policy.
#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum StateUploads {
    /// Upload x/y and anchors at each check.
    EveryCheck,
    /// Upload initialization/restoration and changed restart anchors only.
    Necessary,
}
/// Explicit deterministic sparse arithmetic.
#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum Fp64Reduction {
    /// The original padded 1024-element halving tree.
    #[serde(rename = "legacy_1024")]
    Legacy1024,
    /// Lane-strided sums followed by a fixed 32-lane halving tree.
    #[serde(rename = "warp32_v1")]
    Warp32V1,
}
/// Kernel fusion policy.
#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum Fp64Fusion {
    /// Six original-order kernel launches per step.
    Separate,
    /// Two launches with primal and dual updates fused into products.
    PrimalDual,
}
/// Required versioned settings; there are no implicit execution defaults.
#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize)]
pub struct Fp64ExecutionSettings {
    /// Must be one.
    pub schema_version: u32,
    /// Working allocation lifetime.
    pub allocation: WorkingAllocation,
    /// Upload policy.
    pub uploads: StateUploads,
    /// Sparse reduction arithmetic.
    pub reduction: Fp64Reduction,
    /// Fusion policy.
    pub fusion: Fp64Fusion,
}
deserialize_object!(Fp64ExecutionSettings {
    schema_version: u32,
    allocation: WorkingAllocation,
    uploads: StateUploads,
    reduction: Fp64Reduction,
    fusion: Fp64Fusion
});
impl Fp64ExecutionSettings {
    /// Validate the supported version and combinations.
    pub fn validate(&self) -> Result<(), ValidationError> {
        if self.schema_version != 1
            || (self.uploads == StateUploads::Necessary
                && self.allocation != WorkingAllocation::Resident)
        {
            return Err(ValidationError::new(
                ErrorKind::Document,
                "unsupported FP64 execution version or upload/allocation combination",
            ));
        }
        Ok(())
    }
    /// Parse a strict object-form settings document.
    pub fn from_json(bytes: &[u8]) -> Result<Self, ValidationError> {
        let value: Self = serde_json::from_slice(bytes)
            .map_err(|e| ValidationError::new(ErrorKind::Document, e.to_string()))?;
        value.validate()?;
        Ok(value)
    }
}
/// Explicit tuned execution recorded in solve-record v3.
#[derive(Clone, Debug, PartialEq, Eq, Serialize)]
pub struct LpExecutionRecord {
    /// Caller-selected execution settings.
    pub settings: Fp64ExecutionSettings,
    /// Exact code-object bytes selected for this execution.
    pub code_object_sha256: String,
}
deserialize_object!(LpExecutionRecord {
    settings: Fp64ExecutionSettings,
    code_object_sha256: String
});
/// Requested execution and actual device work, retained on fallback.
#[derive(Clone, Debug, PartialEq, Eq, Serialize)]
pub struct LpExecutionDiagnostics {
    /// Requested settings, even when no code object could be opened.
    pub settings: Fp64ExecutionSettings,
    /// Selected code object, unavailable before successful identification.
    pub code_object_sha256: Option<String>,
    /// Successful allocation calls, including invariant buffers.
    pub allocations: u64,
    /// Total allocated bytes over the execution, including repeated allocation.
    pub allocated_bytes: u64,
    /// Successful host-to-device copy calls.
    pub upload_calls: u64,
    /// Bytes actually uploaded.
    pub upload_bytes: u64,
    /// Successful device-to-host copy calls.
    pub readback_calls: u64,
    /// Bytes actually read back.
    pub readback_bytes: u64,
    /// Successful explicit synchronizations, including synchronous copy completion.
    pub synchronizations: u64,
    /// Successfully submitted iteration kernels.
    pub kernel_launches: u64,
}
deserialize_object!(LpExecutionDiagnostics { settings: Fp64ExecutionSettings, code_object_sha256: Option<String>,
    allocations: u64, allocated_bytes: u64, upload_calls: u64, upload_bytes: u64,
    readback_calls: u64, readback_bytes: u64, synchronizations: u64, kernel_launches: u64 });
impl LpExecutionDiagnostics {
    /// Begin observations before opening the requested device backend.
    #[must_use]
    pub fn new(settings: Fp64ExecutionSettings) -> Self {
        Self {
            settings,
            code_object_sha256: None,
            allocations: 0,
            allocated_bytes: 0,
            upload_calls: 0,
            upload_bytes: 0,
            readback_calls: 0,
            readback_bytes: 0,
            synchronizations: 0,
            kernel_launches: 0,
        }
    }
}

impl<'de> Deserialize<'de> for WorkingAllocation {
    fn deserialize<D: serde::Deserializer<'de>>(deserializer: D) -> Result<Self, D::Error> {
        match String::deserialize(deserializer)?.as_str() {
            "per_check" => Ok(Self::PerCheck),
            "resident" => Ok(Self::Resident),
            other => Err(serde::de::Error::unknown_variant(
                other,
                &["per_check", "resident"],
            )),
        }
    }
}

impl<'de> Deserialize<'de> for StateUploads {
    fn deserialize<D: serde::Deserializer<'de>>(deserializer: D) -> Result<Self, D::Error> {
        match String::deserialize(deserializer)?.as_str() {
            "every_check" => Ok(Self::EveryCheck),
            "necessary" => Ok(Self::Necessary),
            other => Err(serde::de::Error::unknown_variant(
                other,
                &["every_check", "necessary"],
            )),
        }
    }
}

impl<'de> Deserialize<'de> for Fp64Reduction {
    fn deserialize<D: serde::Deserializer<'de>>(deserializer: D) -> Result<Self, D::Error> {
        match String::deserialize(deserializer)?.as_str() {
            "legacy_1024" => Ok(Self::Legacy1024),
            "warp32_v1" => Ok(Self::Warp32V1),
            other => Err(serde::de::Error::unknown_variant(
                other,
                &["legacy_1024", "warp32_v1"],
            )),
        }
    }
}

impl<'de> Deserialize<'de> for Fp64Fusion {
    fn deserialize<D: serde::Deserializer<'de>>(deserializer: D) -> Result<Self, D::Error> {
        match String::deserialize(deserializer)?.as_str() {
            "separate" => Ok(Self::Separate),
            "primal_dual" => Ok(Self::PrimalDual),
            other => Err(serde::de::Error::unknown_variant(
                other,
                &["separate", "primal_dual"],
            )),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::Fp64ExecutionSettings;

    #[test]
    fn execution_enum_names_require_strings() {
        let settings = serde_json::json!({
            "schema_version": 1,
            "allocation": "resident",
            "uploads": "necessary",
            "reduction": "warp32_v1",
            "fusion": "primal_dual"
        });
        assert!(Fp64ExecutionSettings::from_json(&serde_json::to_vec(&settings).unwrap()).is_ok());
        for key in ["allocation", "uploads", "reduction", "fusion"] {
            let mut invalid = settings.clone();
            let name = settings[key].as_str().unwrap();
            invalid[key] = serde_json::json!({name: null});
            assert!(
                Fp64ExecutionSettings::from_json(&serde_json::to_vec(&invalid).unwrap()).is_err(),
                "{key}"
            );
        }
    }
}
