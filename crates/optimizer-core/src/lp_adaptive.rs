//! Explicit adaptive precision contracts under ADR-0025.
use crate::serde_strict::deserialize_required_object;
use crate::{ErrorKind, Fp64ExecutionSettings, LpPrecisionSettings, LpWidth, ValidationError};
use serde::{Deserialize, Serialize};

/// Increasing arithmetic precision; ordering is part of the v1 contract.
#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum LpAdaptiveRung {
    /// Binary32 iterates and anchors.
    WorkingFp32,
    /// Binary32 accumulation, binary64 iterates.
    AccumulationFp32,
    /// Binary32 products, binary64 accumulation.
    ProductsFp32,
    /// Binary32 matrix, binary64 arithmetic.
    StorageFp32,
    /// Original represented operator and binary64 arithmetic.
    Fp64,
}
impl<'de> Deserialize<'de> for LpAdaptiveRung {
    fn deserialize<D: serde::Deserializer<'de>>(d: D) -> Result<Self, D::Error> {
        match String::deserialize(d)?.as_str() {
            "working_fp32" => Ok(Self::WorkingFp32),
            "accumulation_fp32" => Ok(Self::AccumulationFp32),
            "products_fp32" => Ok(Self::ProductsFp32),
            "storage_fp32" => Ok(Self::StorageFp32),
            "fp64" => Ok(Self::Fp64),
            _ => Err(serde::de::Error::custom("unsupported adaptive rung")),
        }
    }
}
impl LpAdaptiveRung {
    /// Existing executor storage/arithmetic shape. Fixed correction is not run;
    /// its interval only satisfies the legacy working-state shape validator.
    #[must_use]
    pub fn precision(self) -> LpPrecisionSettings {
        use LpWidth::{F32, F64};
        LpPrecisionSettings {
            schema_version: 1,
            matrix: if self == Self::Fp64 { F64 } else { F32 },
            product_operands: if self <= Self::ProductsFp32 { F32 } else { F64 },
            products: if self <= Self::ProductsFp32 { F32 } else { F64 },
            accumulation: if self <= Self::AccumulationFp32 {
                F32
            } else {
                F64
            },
            working_state: if self == Self::WorkingFp32 { F32 } else { F64 },
            updates: F64,
            rounding: "nearest_even".into(),
            correction_interval: (self == Self::WorkingFp32).then_some(1),
        }
    }
}
/// Explicit hysteresis; the lower-rung probe must meet the stricter margin.
#[derive(Clone, Debug, PartialEq, Serialize)]
pub struct LpDemotionSettings {
    /// Successful windows required before probing.
    pub clean_windows: u64,
    /// Multiplier of the audit allowance, strictly between zero and one.
    pub margin_fraction: f64,
}
deserialize_required_object!(LpDemotionSettings {
    clean_windows: u64,
    margin_fraction: f64
});
/// No numerical defaults; all keys, including null demotion, are required.
#[derive(Clone, Debug, PartialEq, Serialize)]
pub struct LpAdaptiveSettings {
    /// Must equal one.
    pub schema_version: u32,
    /// Strictly increasing rungs ending in fp64.
    pub ladder: Vec<LpAdaptiveRung>,
    /// Maximum window length in logical proposals.
    pub audit_interval: u64,
    /// Original-unit primal absolute update allowance.
    pub primal_absolute: f64,
    /// Original-unit dual absolute update allowance.
    pub dual_absolute: f64,
    /// Relative update allowance, independent of final tolerances.
    pub relative: f64,
    /// Null keeps promotion sticky.
    pub demotion: Option<LpDemotionSettings>,
}
deserialize_required_object!(LpAdaptiveSettings { schema_version: u32, ladder: Vec<LpAdaptiveRung>, audit_interval: u64,
 primal_absolute: f64, dual_absolute: f64, relative: f64, demotion: Option<LpDemotionSettings> });
impl LpAdaptiveSettings {
    /// Validate the bounded v1 policy.
    pub fn validate(&self) -> Result<(), ValidationError> {
        if self.schema_version != 1
            || self.ladder.last() != Some(&LpAdaptiveRung::Fp64)
            || self.ladder.windows(2).any(|v| v[0] >= v[1])
            || self.audit_interval == 0
            || [self.primal_absolute, self.dual_absolute, self.relative]
                .iter()
                .any(|v| !v.is_finite() || *v < 0.0)
            || self.demotion.as_ref().is_some_and(|d| {
                d.clean_windows == 0
                    || !d.margin_fraction.is_finite()
                    || d.margin_fraction <= 0.0
                    || d.margin_fraction >= 1.0
            })
        {
            return Err(ValidationError::new(
                ErrorKind::Document,
                "unsupported adaptive precision policy",
            ));
        }
        Ok(())
    }
    /// Bind to the existing precision executor shape without changing it.
    pub fn validate_execution(&self, e: Fp64ExecutionSettings) -> Result<(), ValidationError> {
        self.validate()?;
        LpAdaptiveRung::Fp64.precision().validate_execution(e)
    }
    /// Parse a strict versioned policy.
    pub fn from_json(bytes: &[u8]) -> Result<Self, ValidationError> {
        let value: Self = serde_json::from_slice(bytes)
            .map_err(|e| ValidationError::new(ErrorKind::Document, e.to_string()))?;
        value.validate()?;
        Ok(value)
    }
}
/// Transition at a committed window boundary, after charging discarded work.
#[derive(Clone, Debug, PartialEq, Serialize)]
pub struct LpAdaptiveTransition {
    /// Restored/accepted logical boundary.
    pub iteration: u64,
    /// Total physical work at transition.
    pub physical_work: u64,
    /// Previous rung.
    pub from: LpAdaptiveRung,
    /// Next rung, or null for exhausted ladder.
    pub to: Option<LpAdaptiveRung>,
    /// Stable reason: preparation_guard, range_guard, audit_failed, reference_guard, demotion.
    pub reason: String,
}
deserialize_required_object!(LpAdaptiveTransition { iteration: u64, physical_work: u64,
 from: LpAdaptiveRung, to: Option<LpAdaptiveRung>, reason: String });
/// Work counters are completed work; rejected/replay are subsets of proposals.
#[derive(Clone, Debug, PartialEq, Serialize)]
pub struct LpAdaptiveDiagnostics {
    /// Versioned algorithm identity, independent of kernel identity.
    pub method: String,
    /// Complete requested policy.
    pub settings: LpAdaptiveSettings,
    /// Completed proposals, including rejected and replayed work.
    pub proposed_steps: u64,
    /// Host original-operator reference updates.
    pub audit_steps: u64,
    /// Host prospective lower-rung updates.
    pub probe_steps: u64,
    /// Discarded proposal work, including interrupted windows.
    pub rejected_steps: u64,
    /// Proposal subset spent replaying failed windows.
    pub replay_steps: u64,
    /// Successfully audited windows.
    pub accepted_windows: u64,
    /// Failed windows (range/reference/audit failures).
    pub rejected_windows: u64,
    /// Completed proposals per requested rung.
    pub rung_proposals: Vec<u64>,
    /// Preparation failure per rung; null means executable.
    pub unavailable_rungs: Vec<Option<String>>,
    /// Transitions in execution order.
    pub transitions: Vec<LpAdaptiveTransition>,
    /// Last active rung, including exhaustion.
    pub final_rung: LpAdaptiveRung,
    /// Common conservatively restricted step, absent before preparation.
    pub step: Option<f64>,
    /// Largest finite original-unit absolute audit discrepancy.
    pub max_audit_error: f64,
}
deserialize_required_object!(LpAdaptiveDiagnostics { method: String, settings: LpAdaptiveSettings,
 proposed_steps: u64, audit_steps: u64, probe_steps: u64, rejected_steps: u64, replay_steps: u64,
 accepted_windows: u64, rejected_windows: u64, rung_proposals: Vec<u64>, unavailable_rungs: Vec<Option<String>>,
 transitions: Vec<LpAdaptiveTransition>, final_rung: LpAdaptiveRung, step: Option<f64>, max_audit_error: f64 });
impl LpAdaptiveDiagnostics {
    /// Empty observations available even before opening a device.
    #[must_use]
    pub fn new(settings: LpAdaptiveSettings) -> Self {
        let n = settings.ladder.len();
        let final_rung = settings
            .ladder
            .first()
            .copied()
            .unwrap_or(LpAdaptiveRung::Fp64);
        Self {
            method: "adaptive-fp32-fp64-v1".into(),
            settings,
            proposed_steps: 0,
            audit_steps: 0,
            probe_steps: 0,
            rejected_steps: 0,
            replay_steps: 0,
            accepted_windows: 0,
            rejected_windows: 0,
            rung_proposals: vec![0; n],
            unavailable_rungs: vec![None; n],
            transitions: vec![],
            final_rung,
            step: None,
            max_audit_error: 0.0,
        }
    }
    /// Validate internally checkable identity, transition and work relationships.
    pub fn validate(&self) -> Result<(), ValidationError> {
        self.settings.validate()?;
        let bad = || ValidationError::new(ErrorKind::Document, "invalid adaptive observations");
        let physical = self
            .proposed_steps
            .checked_add(self.audit_steps)
            .and_then(|v| v.checked_add(self.probe_steps))
            .ok_or_else(bad)?;
        if self.method != "adaptive-fp32-fp64-v1"
            || self.rung_proposals.len() != self.settings.ladder.len()
            || self.unavailable_rungs.len() != self.settings.ladder.len()
            || self
                .rung_proposals
                .iter()
                .try_fold(0u64, |a, v| a.checked_add(*v))
                != Some(self.proposed_steps)
            || self.rejected_steps > self.proposed_steps
            || self.replay_steps > self.proposed_steps
            || self.accepted_windows > self.audit_steps
            || self.probe_steps > self.accepted_windows
            || !self.max_audit_error.is_finite()
            || self.max_audit_error < 0.0
            || self.step.is_some_and(|s| !s.is_finite() || s <= 0.0)
        {
            return Err(bad());
        }
        let mut index = 0;
        let mut previous = (0, 0);
        let mut exhausted = false;
        for t in &self.transitions {
            if exhausted
                || t.from != self.settings.ladder[index]
                || t.physical_work > physical
                || t.physical_work < previous.1
                || t.iteration < previous.0
                || t.iteration > self.proposed_steps - self.rejected_steps
            {
                return Err(bad());
            }
            let next = if t.reason == "demotion" {
                if self.settings.demotion.is_none() || index == 0 {
                    return Err(bad());
                }
                Some(index - 1)
            } else if [
                "preparation_guard",
                "range_guard",
                "audit_failed",
                "reference_guard",
            ]
            .contains(&t.reason.as_str())
            {
                (index + 1 < self.settings.ladder.len()).then_some(index + 1)
            } else {
                return Err(bad());
            };
            if t.to != next.map(|i| self.settings.ladder[i]) {
                return Err(bad());
            }
            if let Some(next) = next {
                index = next;
            } else {
                exhausted = true;
            }
            previous = (t.iteration, t.physical_work);
        }
        let failures = self
            .transitions
            .iter()
            .filter(|t| {
                matches!(
                    t.reason.as_str(),
                    "range_guard" | "audit_failed" | "reference_guard"
                )
            })
            .count() as u64;
        let reference_failures = self
            .transitions
            .iter()
            .filter(|t| matches!(t.reason.as_str(), "audit_failed" | "reference_guard"))
            .count() as u64;
        let demotions = self
            .transitions
            .iter()
            .filter(|t| t.reason == "demotion")
            .count() as u64;
        if self.final_rung != self.settings.ladder[index]
            || self.rejected_windows != failures
            || self.accepted_windows.checked_add(reference_failures) != Some(self.audit_steps)
            || demotions > self.probe_steps
            || (self.settings.demotion.is_none() && self.probe_steps != 0)
            || (physical > 0 && self.step.is_none())
            || self
                .unavailable_rungs
                .iter()
                .zip(&self.rung_proposals)
                .any(|(guard, proposals)| {
                    guard
                        .as_ref()
                        .is_some_and(|reason| reason.is_empty() || *proposals != 0)
                })
            || self.transitions.iter().any(|t| {
                t.reason == "preparation_guard"
                    && self.unavailable_rungs[self
                        .settings
                        .ladder
                        .iter()
                        .position(|r| *r == t.from)
                        .unwrap()]
                    .is_none()
            })
        {
            return Err(bad());
        }
        Ok(())
    }
}
