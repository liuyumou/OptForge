//! Caller-supplied settings for the first-order method, under SPEC-0011
//! requirements 9 and 10.
//!
//! Every field here changes the iterates, and therefore changes the result. That
//! is why requirement 10 forbids hiding the termination check interval and
//! requirement 9 requires the preconditioner to be recorded: a record that did not
//! name them would not describe the solve it came from.
//!
//! There are deliberately no defaults for the recorded fields. The project's
//! existing solve configuration takes the same position -- every limit and
//! tolerance is caller-supplied, so a record always states what was run -- and a
//! default here would let two solves with different behavior produce records that
//! look identical.
//!
//! These types are documents rather than algorithms, which is why they live here
//! beside every other wire format the project defines and not in the crate that
//! implements the method. A solve record carries them, records are core types, and
//! a second copy in the implementing crate would be the drift hazard SPEC-0008
//! requirement 8 exists to prevent. The method itself stays in `optimizer-lp`.

use serde::{Deserialize, Serialize};

use crate::{ErrorKind, ValidationError};

/// How the preconditioner was configured, recorded with every solve.
#[derive(Clone, Copy, Debug, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct PreconditionerSettings {
    /// Number of Ruiz equilibration passes. Fixed, never convergence-driven: a
    /// pass count that stopped on a measured criterion would vary with rounding
    /// and take the iterates with it.
    pub ruiz_passes: u32,
    /// Pock-Chambolle exponent. `1.0` is the balanced choice; `0.0` disables the
    /// pass.
    pub pock_chambolle_alpha: f64,
}

impl PreconditionerSettings {
    /// Whether these settings are usable.
    ///
    /// # Errors
    ///
    /// Returns a document failure for a nonfinite or out-of-range exponent, or a
    /// pass count large enough to be a mistake rather than a choice.
    pub fn validate(&self) -> Result<(), ValidationError> {
        if self.ruiz_passes > 100 {
            return Err(ValidationError::new(
                ErrorKind::Document,
                format!("ruiz_passes {} exceeds 100", self.ruiz_passes),
            ));
        }
        if !self.pock_chambolle_alpha.is_finite()
            || self.pock_chambolle_alpha < 0.0
            || self.pock_chambolle_alpha > 2.0
        {
            return Err(ValidationError::new(
                ErrorKind::Document,
                format!(
                    "pock_chambolle_alpha {} must be finite in [0, 2]",
                    self.pock_chambolle_alpha
                ),
            ));
        }
        Ok(())
    }
}

/// Current settings document wire version.
pub const LP_SETTINGS_SCHEMA_VERSION: u32 = 1;

/// Adaptive restart thresholds.
///
/// These are constants of the algorithm rather than of an instance, but they are
/// settings rather than literals because CONTRIBUTING.md forbids changing a
/// threshold silently and a restart criterion is one. The defaults in
/// [`RestartSettings::published`] are the values the published method uses.
#[derive(Clone, Copy, Debug, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct RestartSettings {
    /// Restart when the error has fallen to this fraction of its value at the
    /// last restart, regardless of anything else.
    pub sufficient: f64,
    /// Restart at this larger fraction, but only when the error also stopped
    /// improving.
    pub necessary: f64,
    /// Restart when this fraction of all iterations so far has elapsed since the
    /// last restart, so a run that never triggers the other two still restarts.
    pub artificial: f64,
}

impl RestartSettings {
    /// The thresholds the published method uses.
    #[must_use]
    pub fn published() -> Self {
        Self {
            sufficient: 0.2,
            necessary: 0.8,
            artificial: 0.36,
        }
    }
}

/// Gains for the primal weight controller.
///
/// The weight balances the primal and dual step sizes. With
/// `integral` and `derivative` zero this reduces exactly to the published
/// smoothed update with `theta = proportional`, which
/// `the_primal_weight_reduces_to_the_smoothed_rule_when_the_other_gains_are_zero`
/// asserts. Shipping the general controller with its default at a known-good
/// special case is what gives a later tuning experiment something to be measured
/// against.
#[derive(Clone, Copy, Debug, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct PrimalWeightSettings {
    /// Proportional gain.
    pub proportional: f64,
    /// Integral gain.
    pub integral: f64,
    /// Derivative gain.
    pub derivative: f64,
}

impl PrimalWeightSettings {
    /// The gains that reproduce the published smoothed update.
    #[must_use]
    pub fn published() -> Self {
        Self {
            proportional: 0.5,
            integral: 0.0,
            derivative: 0.0,
        }
    }
}

/// One complete first-order method configuration.
#[derive(Clone, Copy, Debug, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct LpSettings {
    /// Must equal [`LP_SETTINGS_SCHEMA_VERSION`].
    pub schema_version: u32,
    /// Diagonal preconditioning, recorded under requirement 9.
    pub preconditioner: PreconditionerSettings,
    /// Maximum iterations, recorded under requirement 10.
    pub iteration_limit: u64,
    /// Iterations between termination checks, recorded under requirement 10.
    ///
    /// A method that checks every iteration synchronizes the device every
    /// iteration, so this is a real parameter with a real cost and it must not be
    /// hidden. Cancellation latency is bounded by it too.
    pub check_interval: u64,
    /// Power-iteration count used to estimate the step size.
    ///
    /// Fixed rather than convergence-driven, and that is a determinism choice: a
    /// count that stopped on a measured criterion would vary with rounding and
    /// take every later iterate with it.
    pub power_iterations: u32,
    /// Adaptive restart thresholds.
    pub restart: RestartSettings,
    /// Primal weight controller gains.
    pub primal_weight: PrimalWeightSettings,
}

impl LpSettings {
    /// Settings matching the published method, for a caller that wants them.
    ///
    /// Not a `Default` implementation. `Default` would make it possible to run
    /// without stating anything, and requirement 10's point is that these numbers
    /// are chosen rather than assumed; a caller naming this function has named it.
    #[must_use]
    pub fn published(iteration_limit: u64, check_interval: u64) -> Self {
        Self {
            schema_version: LP_SETTINGS_SCHEMA_VERSION,
            preconditioner: PreconditionerSettings {
                ruiz_passes: 10,
                pock_chambolle_alpha: 1.0,
            },
            iteration_limit,
            check_interval,
            power_iterations: 20,
            restart: RestartSettings::published(),
            primal_weight: PrimalWeightSettings::published(),
        }
    }

    /// Check that these settings can be run and recorded.
    ///
    /// # Errors
    ///
    /// Returns a document failure for a wrong version, a zero limit or interval,
    /// a nonfinite gain, or a restart threshold outside `(0, 1]`.
    pub fn validate(&self) -> Result<(), ValidationError> {
        let refuse = |message: String| Err(ValidationError::new(ErrorKind::Document, message));
        if self.schema_version != LP_SETTINGS_SCHEMA_VERSION {
            return refuse(format!(
                "unsupported lp settings schema_version {}",
                self.schema_version
            ));
        }
        self.preconditioner.validate()?;
        if self.iteration_limit == 0 {
            return refuse("iteration_limit must be at least 1".to_string());
        }
        // Zero would mean "never check", which is a solve that cannot terminate
        // by tolerance and cannot observe cancellation.
        if self.check_interval == 0 {
            return refuse("check_interval must be at least 1".to_string());
        }
        if self.power_iterations == 0 {
            return refuse("power_iterations must be at least 1".to_string());
        }
        for (name, value) in [
            ("restart.sufficient", self.restart.sufficient),
            ("restart.necessary", self.restart.necessary),
            ("restart.artificial", self.restart.artificial),
        ] {
            if !value.is_finite() || value <= 0.0 || value > 1.0 {
                return refuse(format!("{name} {value} must be finite in (0, 1]"));
            }
        }
        for (name, value) in [
            (
                "primal_weight.proportional",
                self.primal_weight.proportional,
            ),
            ("primal_weight.integral", self.primal_weight.integral),
            ("primal_weight.derivative", self.primal_weight.derivative),
        ] {
            if !value.is_finite() {
                return refuse(format!("{name} {value} must be finite"));
            }
        }
        Ok(())
    }

    /// Parse one settings document.
    ///
    /// # Errors
    ///
    /// Returns a document failure for malformed JSON, an unknown field or a
    /// document that does not validate.
    pub fn from_json(bytes: &[u8]) -> Result<Self, ValidationError> {
        let settings: Self = serde_json::from_slice(bytes)
            .map_err(|error| ValidationError::new(ErrorKind::Document, error.to_string()))?;
        settings.validate()?;
        Ok(settings)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn settings() -> LpSettings {
        LpSettings::published(1_000, 40)
    }

    #[test]
    fn published_settings_validate() {
        settings().validate().expect("the published settings run");
    }

    /// Requirement 10: a settings document missing the check interval is refused
    /// rather than defaulted, so a record can always state what was run.
    #[test]
    fn a_document_missing_a_recorded_field_is_refused() {
        let complete = serde_json::to_value(settings()).unwrap();
        for absent in ["check_interval", "preconditioner", "iteration_limit"] {
            let mut partial = complete.clone();
            partial.as_object_mut().unwrap().remove(absent);
            let bytes = serde_json::to_vec(&partial).unwrap();
            assert!(
                LpSettings::from_json(&bytes).is_err(),
                "a document without {absent} must be refused"
            );
        }
    }

    #[test]
    fn an_unknown_field_is_refused_rather_than_ignored() {
        let mut document = serde_json::to_value(settings()).unwrap();
        document
            .as_object_mut()
            .unwrap()
            .insert("step_size".to_string(), 0.5.into());
        let bytes = serde_json::to_vec(&document).unwrap();
        assert!(LpSettings::from_json(&bytes).is_err());
    }

    #[test]
    fn a_zero_interval_or_limit_is_refused() {
        let mut zero_interval = settings();
        zero_interval.check_interval = 0;
        assert!(zero_interval.validate().is_err());
        let mut zero_limit = settings();
        zero_limit.iteration_limit = 0;
        assert!(zero_limit.validate().is_err());
    }

    #[test]
    fn a_wrong_version_is_refused_rather_than_migrated() {
        let mut wrong = settings();
        wrong.schema_version = LP_SETTINGS_SCHEMA_VERSION + 1;
        assert!(wrong.validate().is_err());
    }

    #[test]
    fn a_restart_threshold_outside_the_unit_interval_is_refused() {
        let mut wrong = settings();
        wrong.restart.sufficient = 1.5;
        assert!(wrong.validate().is_err());
        let mut negative = settings();
        negative.restart.artificial = -0.1;
        assert!(negative.validate().is_err());
    }

    #[test]
    fn settings_round_trip_through_json() {
        let original = settings();
        let bytes = serde_json::to_vec(&original).unwrap();
        assert_eq!(LpSettings::from_json(&bytes).unwrap(), original);
    }
}
