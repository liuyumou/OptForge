//! Explicit experimental precision under SPEC-0012 and ADR-0019.
use crate::serde_strict::deserialize_required_object;
use crate::{ErrorKind, Fp64ExecutionSettings, ValidationError};
use serde::{Deserialize, Serialize};

/// IEEE binary arithmetic/storage width.
#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum LpWidth {
    /// Binary32, nearest-even with gradual underflow.
    F32,
    /// Binary64, nearest-even with gradual underflow.
    F64,
}
impl<'de> Deserialize<'de> for LpWidth {
    fn deserialize<D: serde::Deserializer<'de>>(d: D) -> Result<Self, D::Error> {
        match String::deserialize(d)?.as_str() {
            "f32" => Ok(Self::F32),
            "f64" => Ok(Self::F64),
            _ => Err(serde::de::Error::custom("expected f32 or f64 string")),
        }
    }
}
/// Required precision document. No implicit numerical defaults.
#[derive(Clone, Debug, PartialEq, Eq, Serialize)]
pub struct LpPrecisionSettings {
    /// Must be one.
    pub schema_version: u32,
    /// Canonical represented matrix storage.
    pub matrix: LpWidth,
    /// Temporary operands presented to sparse products.
    pub product_operands: LpWidth,
    /// Rounded multiplication results.
    pub products: LpWidth,
    /// Lane sums and fixed reduction tree.
    pub accumulation: LpWidth,
    /// Primal, dual and restart anchor storage.
    pub working_state: LpWidth,
    /// Vector updates are always binary64 in this slice.
    pub updates: LpWidth,
    /// Must be nearest_even; explicit to bind future formats.
    pub rounding: String,
    /// Null disables correction; positive values schedule unconditional FP64 correction.
    pub correction_interval: Option<u64>,
}
deserialize_required_object!(LpPrecisionSettings { schema_version: u32, matrix: LpWidth,
    product_operands: LpWidth, products: LpWidth, accumulation: LpWidth,
    working_state: LpWidth, updates: LpWidth, rounding: String, correction_interval: Option<u64> });
impl LpPrecisionSettings {
    /// Refuse unsupported arithmetic combinations.
    pub fn validate(&self) -> Result<(), ValidationError> {
        use LpWidth::{F32, F64};
        let widths = (
            self.matrix,
            self.products,
            self.accumulation,
            self.working_state,
        );
        if self.schema_version != 1
            || self.rounding != "nearest_even"
            || self.updates != F64
            || self.product_operands != self.products
            || self.correction_interval == Some(0)
            || !matches!(
                widths,
                (F64, F64, F64, F64)
                    | (F32, F64, F64, F64)
                    | (F32, F32, F64, F64)
                    | (F32, F32, F32, F64)
                    | (F32, F32, F32, F32)
            )
            || (self.working_state == F32 && self.correction_interval.is_none())
        {
            return Err(ValidationError::new(
                ErrorKind::Document,
                "unsupported LP precision settings",
            ));
        }
        Ok(())
    }
    /// Bind precision to the bounded GPUP-5 executor.
    pub fn validate_execution(&self, e: Fp64ExecutionSettings) -> Result<(), ValidationError> {
        self.validate()?;
        e.validate()?;
        if e.allocation != crate::WorkingAllocation::Resident
            || e.uploads != crate::StateUploads::Necessary
            || e.reduction != crate::Fp64Reduction::Warp32V1
            || e.fusion != crate::Fp64Fusion::Separate
        {
            return Err(ValidationError::new(
                ErrorKind::Document,
                "precision requires resident/necessary/warp32_v1/separate",
            ));
        }
        Ok(())
    }
    /// Strict versioned parsing.
    pub fn from_json(bytes: &[u8]) -> Result<Self, ValidationError> {
        let s: Self = serde_json::from_slice(bytes)
            .map_err(|e| ValidationError::new(ErrorKind::Document, e.to_string()))?;
        s.validate()?;
        Ok(s)
    }
    /// Whether storage or arithmetic uses binary32.
    #[must_use]
    pub fn mixed(&self) -> bool {
        self.matrix == LpWidth::F32
    }
}
/// Precision work retained separately in endpoint v4, including before fallback.
#[derive(Clone, Debug, PartialEq, Serialize)]
pub struct LpPrecisionDiagnostics {
    /// Explicit requested settings.
    pub settings: LpPrecisionSettings,
    /// Successfully completed low/FP64 proposal steps, including rejected ones.
    pub proposed_steps: u64,
    /// Completed host reference corrections; also physical work.
    pub correction_steps: u64,
    /// Proposals rejected by a range guard.
    pub rejected_steps: u64,
    /// First deterministic guard diagnostic, or absence.
    pub guard: Option<String>,
    /// Conservative original and represented operator norm bounds.
    pub operator_bounds: Option<[f64; 2]>,
    /// Executed conservative step.
    pub step: Option<f64>,
    /// Largest original-unit component discrepancy at correction.
    pub correction_max_error: f64,
    /// Largest absolute matrix conversion error in scaled units.
    pub matrix_max_error: f64,
    /// Count of nonzero subnormal represented matrix entries.
    pub matrix_subnormals: u64,
}
deserialize_required_object!(LpPrecisionDiagnostics { settings: LpPrecisionSettings, proposed_steps: u64,
 correction_steps: u64, rejected_steps: u64, guard: Option<String>, operator_bounds: Option<[f64;2]>,
 step: Option<f64>, correction_max_error: f64, matrix_max_error: f64, matrix_subnormals: u64 });
impl LpPrecisionDiagnostics {
    /// Start before device availability is known.
    #[must_use]
    pub fn new(settings: LpPrecisionSettings) -> Self {
        Self {
            settings,
            proposed_steps: 0,
            correction_steps: 0,
            rejected_steps: 0,
            guard: None,
            operator_bounds: None,
            step: None,
            correction_max_error: 0.0,
            matrix_max_error: 0.0,
            matrix_subnormals: 0,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn precision_document_rejects_missing_unknown_and_unsupported_combinations() {
        let bytes = include_bytes!("../../../examples/lp-storage-fp32-v1.json");
        let value: serde_json::Value = serde_json::from_slice(bytes).unwrap();
        assert!(LpPrecisionSettings::from_json(bytes).is_ok());
        for key in value.as_object().unwrap().keys() {
            let mut bad = value.clone();
            bad.as_object_mut().unwrap().remove(key);
            assert!(
                LpPrecisionSettings::from_json(&serde_json::to_vec(&bad).unwrap()).is_err(),
                "{key}"
            );
        }
        for (key, v) in [
            ("schema_version", serde_json::json!(2)),
            ("matrix", serde_json::json!({"f32":null})),
            ("extra", serde_json::json!(1)),
            ("correction_interval", serde_json::json!(0)),
            ("accumulation", serde_json::json!("f32")),
        ] {
            let mut bad = value.clone();
            bad[key] = v;
            assert!(LpPrecisionSettings::from_json(&serde_json::to_vec(&bad).unwrap()).is_err());
        }
    }
}
