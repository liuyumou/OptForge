//! Backend-neutral solve contracts and reproducible records under SPEC-0002.
//!
//! These types describe what a backend is asked to do and what it reported. They
//! carry no mathematical authority: a termination is native evidence recorded
//! under explicit numerical settings, never an exact-arithmetic certificate. The
//! core re-validates every published candidate against the original model.

use serde::{Deserialize, Serialize};
use std::sync::Arc;
use std::sync::atomic::{AtomicBool, Ordering};
use std::time::Duration;

use crate::serde_strict::deserialize_object;
use crate::{Candidate, ErrorKind, Tolerances, ValidationError, ValidationReport};

/// Current solve configuration and record wire version.
pub const SOLVE_SCHEMA_VERSION: u32 = 1;

/// Explicit solve configuration. Every limit and tolerance is caller-supplied;
/// there are deliberately no defaults, so a record always states what was run.
#[derive(Clone, Debug, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct SolveOptions {
    /// Must equal [`SOLVE_SCHEMA_VERSION`].
    pub schema_version: u32,
    /// Deterministic seed recorded and passed to the backend.
    pub seed: u64,
    /// Optional wall-clock limit in milliseconds; `None` means unlimited.
    pub time_limit_ms: Option<u64>,
    /// Optional simplex/interior-point iteration limit.
    pub iteration_limit: Option<u64>,
    /// Optional branch-and-bound node limit.
    pub node_limit: Option<u64>,
    /// Original-model validation policy applied to extracted candidates.
    pub tolerances: Tolerances,
    /// Native worker threads. Only one CPU thread is supported.
    pub threads: u32,
}

deserialize_object!(SolveOptions {
    schema_version: u32,
    seed: u64,
    time_limit_ms: Option<u64>,
    iteration_limit: Option<u64>,
    node_limit: Option<u64>,
    tolerances: Tolerances,
    threads: u32,
});

impl SolveOptions {
    /// Validate configuration and normalize tolerances, keeping each failure in
    /// its own diagnostic category.
    pub fn validate(&self) -> Result<Self, ValidationError> {
        if self.schema_version != SOLVE_SCHEMA_VERSION {
            return Err(ValidationError::new(
                ErrorKind::Document,
                format!("unsupported solve schema_version {}", self.schema_version),
            ));
        }
        if self.threads != 1 {
            return Err(ValidationError::new(
                ErrorKind::Unsupported,
                format!("threads must be 1, found {}", self.threads),
            ));
        }
        for (name, limit) in [
            ("time_limit_ms", self.time_limit_ms),
            ("iteration_limit", self.iteration_limit),
            ("node_limit", self.node_limit),
        ] {
            if limit == Some(0) {
                return Err(ValidationError::new(
                    ErrorKind::Unsupported,
                    format!("{name} must be positive when present"),
                ));
            }
        }
        Ok(Self {
            tolerances: self.tolerances.validate()?,
            ..self.clone()
        })
    }

    /// Wall-clock limit as a duration, when one was configured.
    pub fn time_limit(&self) -> Option<Duration> {
        self.time_limit_ms.map(Duration::from_millis)
    }
}

/// Cooperative cancellation shared with a running solve.
///
/// Cancellation is observed through native interrupt callbacks, so latency is
/// bounded by callback availability rather than by wall time. A pre-cancelled
/// token must terminate a solve before any native work begins.
#[derive(Clone, Debug, Default)]
pub struct CancellationToken(Arc<AtomicBool>);

impl CancellationToken {
    /// Create an uncancelled token.
    pub fn new() -> Self {
        Self::default()
    }

    /// Request cancellation. This is visible to every clone of the token.
    pub fn cancel(&self) {
        self.0.store(true, Ordering::Release);
    }

    /// Whether cancellation has been requested.
    pub fn is_cancelled(&self) -> bool {
        self.0.load(Ordering::Acquire)
    }
}

/// Native basis status of one column or row in an LP warm start.
#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum BasisStatus {
    /// Nonbasic at its lower bound.
    Lower,
    /// Basic.
    Basic,
    /// Nonbasic at its upper bound.
    Upper,
    /// Nonbasic at zero.
    Zero,
    /// Nonbasic without a specified bound.
    Nonbasic,
}

impl<'de> Deserialize<'de> for BasisStatus {
    fn deserialize<D: serde::Deserializer<'de>>(deserializer: D) -> Result<Self, D::Error> {
        match String::deserialize(deserializer)?.as_str() {
            "lower" => Ok(Self::Lower),
            "basic" => Ok(Self::Basic),
            "upper" => Ok(Self::Upper),
            "zero" => Ok(Self::Zero),
            "nonbasic" => Ok(Self::Nonbasic),
            other => Err(serde::de::Error::unknown_variant(
                other,
                &["lower", "basic", "upper", "zero", "nonbasic"],
            )),
        }
    }
}

/// Opaque LP warm start bound to one exact canonical model.
///
/// The fingerprint covers the canonical model document, not only its ID, so a
/// basis cannot be replayed against a model whose data changed under the same
/// identity.
#[derive(Clone, Debug, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct Basis {
    /// Must equal [`SOLVE_SCHEMA_VERSION`].
    pub schema_version: u32,
    /// Original model identity.
    pub model_id: String,
    /// Fingerprint of the canonical model document.
    pub model_fingerprint: String,
    /// Column statuses in increasing original variable-ID order.
    pub columns: Vec<BasisStatus>,
    /// Row statuses in increasing original constraint-ID order.
    pub rows: Vec<BasisStatus>,
}

deserialize_object!(Basis {
    schema_version: u32,
    model_id: String,
    model_fingerprint: String,
    columns: Vec<BasisStatus>,
    rows: Vec<BasisStatus>,
});

/// Supported warm-start forms. Both are checked before use.
#[derive(Clone, Copy, Debug)]
pub enum WarmStart<'a> {
    /// A complete candidate assignment validated against the original model.
    Candidate(&'a Candidate),
    /// A model-bound LP basis.
    Basis(&'a Basis),
}

/// Engine-owned outcome of a solve.
///
/// A limit, interruption or failure never implies proof completion, and
/// `Optimal` means the backend reported optimality under the recorded numerical
/// settings with any primal solution passing original-model validation.
#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum Termination {
    /// Backend reported optimality and the candidate validated.
    Optimal,
    /// A validated feasible candidate exists without a proof of optimality.
    Feasible,
    /// Backend reported the model infeasible.
    Infeasible,
    /// Backend could not distinguish unboundedness from infeasibility.
    UnboundedOrInfeasible,
    /// Backend reported the model unbounded. This is not a feasible incumbent.
    Unbounded,
    /// Cancellation was observed.
    Interrupted,
    /// The configured time limit was reached.
    TimeLimit,
    /// The configured iteration limit was reached.
    IterationLimit,
    /// The configured node limit was reached.
    NodeLimit,
    /// Native output could not be accepted numerically.
    NumericalFailure,
    /// A backend or native API call failed.
    BackendFailure,
    /// The backend does not support this request.
    Unsupported,
}

impl<'de> Deserialize<'de> for Termination {
    fn deserialize<D: serde::Deserializer<'de>>(deserializer: D) -> Result<Self, D::Error> {
        const NAMES: &[&str] = &[
            "optimal",
            "feasible",
            "infeasible",
            "unbounded_or_infeasible",
            "unbounded",
            "interrupted",
            "time_limit",
            "iteration_limit",
            "node_limit",
            "numerical_failure",
            "backend_failure",
            "unsupported",
        ];
        match String::deserialize(deserializer)?.as_str() {
            "optimal" => Ok(Self::Optimal),
            "feasible" => Ok(Self::Feasible),
            "infeasible" => Ok(Self::Infeasible),
            "unbounded_or_infeasible" => Ok(Self::UnboundedOrInfeasible),
            "unbounded" => Ok(Self::Unbounded),
            "interrupted" => Ok(Self::Interrupted),
            "time_limit" => Ok(Self::TimeLimit),
            "iteration_limit" => Ok(Self::IterationLimit),
            "node_limit" => Ok(Self::NodeLimit),
            "numerical_failure" => Ok(Self::NumericalFailure),
            "backend_failure" => Ok(Self::BackendFailure),
            "unsupported" => Ok(Self::Unsupported),
            other => Err(serde::de::Error::unknown_variant(other, NAMES)),
        }
    }
}

impl Termination {
    /// Whether this outcome completed with an accepted mathematical conclusion.
    ///
    /// Limits, interruptions and failures are deliberately excluded, so a
    /// timeout can never be presented as a completed solve.
    pub fn is_complete(self) -> bool {
        matches!(
            self,
            Self::Optimal | Self::Infeasible | Self::Unbounded | Self::UnboundedOrInfeasible
        )
    }

    /// Whether the engine claims a finished proof for this outcome.
    pub fn proves_completion(self) -> bool {
        matches!(
            self,
            Self::Optimal | Self::Infeasible | Self::Unbounded | Self::UnboundedOrInfeasible
        )
    }
}

/// Immutable record of one solve, sufficient to repeat it.
///
/// Measurements that are absent stay absent: a nonfinite or unavailable bound is
/// omitted rather than serialized as a null standing in for a real number.
#[derive(Clone, Debug, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct SolveRecord {
    /// Must equal [`SOLVE_SCHEMA_VERSION`].
    pub schema_version: u32,
    /// Original model identity.
    pub model_id: String,
    /// Backend identifier, for example `highs`.
    pub backend: String,
    /// Backend version as reported by the backend itself.
    pub backend_version: String,
    /// Engine-owned outcome.
    pub termination: Termination,
    /// Native status name, retained verbatim for diagnosis.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub native_status: Option<String>,
    /// Recomputed original objective of an accepted incumbent.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub objective: Option<f64>,
    /// Best proven bound, when the backend supplied a finite one.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub best_bound: Option<f64>,
    /// Relative gap, when finite.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub gap: Option<f64>,
    /// Accepted incumbent in original variable IDs.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub candidate: Option<Candidate>,
    /// Independent original-model validation of the incumbent.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub validation: Option<ValidationReport>,
    /// Native and adapter warnings, retained even on success.
    pub warnings: Vec<String>,
    /// Measured elapsed wall-clock time in milliseconds.
    pub elapsed_ms: u64,
    /// Explicit configuration this solve actually used.
    pub options: SolveOptions,
}

deserialize_object!(SolveRecord {
    schema_version: u32,
    model_id: String,
    backend: String,
    backend_version: String,
    termination: Termination,
    native_status: Option<String>,
    objective: Option<f64>,
    best_bound: Option<f64>,
    gap: Option<f64>,
    candidate: Option<Candidate>,
    validation: Option<ValidationReport>,
    warnings: Vec<String>,
    elapsed_ms: u64,
    options: SolveOptions,
});

impl SolveRecord {
    /// Serialize a record, rejecting nonfinite measurements rather than emitting
    /// a null in place of an allegedly finite number.
    pub fn to_json(&self) -> Result<String, ValidationError> {
        for (name, value) in [
            ("objective", self.objective),
            ("best_bound", self.best_bound),
            ("gap", self.gap),
        ] {
            if let Some(value) = value
                && !value.is_finite()
            {
                return Err(ValidationError::new(
                    ErrorKind::Numerical,
                    format!("{name}: nonfinite value must be absent, not null"),
                ));
            }
        }
        serde_json::to_string_pretty(self)
            .map_err(|error| ValidationError::new(ErrorKind::Document, error.to_string()))
    }

    /// Parse one complete versioned solve record.
    ///
    /// Nested documents are versioned too, and their versions are checked here
    /// rather than deferred: the version-1 schemas pin them, so accepting a
    /// wrongly versioned incumbent or configuration would make this parser
    /// laxer than `tools/validate_artifacts.py`.
    pub fn from_json(bytes: &[u8]) -> Result<Self, ValidationError> {
        let record: Self = serde_json::from_slice(bytes)
            .map_err(|error| ValidationError::new(ErrorKind::Document, error.to_string()))?;
        if record.schema_version != SOLVE_SCHEMA_VERSION {
            return Err(ValidationError::new(
                ErrorKind::Document,
                format!("unsupported solve schema_version {}", record.schema_version),
            ));
        }
        record.check_nested_versions()?;
        Ok(record)
    }

    /// Check every nested versioned document this record carries.
    ///
    /// `Candidate::canonical` is deliberately not used: it also sorts and
    /// range-checks values, and parsing a record must reject a wrong version
    /// without silently rewriting the document it was handed.
    fn check_nested_versions(&self) -> Result<(), ValidationError> {
        if let Some(candidate) = &self.candidate {
            crate::nested_version("candidate", candidate.schema_version, crate::SCHEMA_VERSION)?;
        }
        if let Some(validation) = &self.validation {
            crate::nested_version(
                "validation",
                validation.schema_version,
                crate::SCHEMA_VERSION,
            )?;
        }
        crate::nested_version("options", self.options.schema_version, SOLVE_SCHEMA_VERSION)
    }
}

/// Represent a measurement that must be finite to be reported at all.
///
/// Backends use this so an unavailable or nonfinite native value becomes an
/// absent field instead of a null pretending to be a number.
pub fn finite_or_absent(value: f64) -> Option<f64> {
    value.is_finite().then_some(crate::zero(value))
}

/// A replaceable numerical backend.
///
/// Implementations own their native resources privately and never hand raw
/// handles across this boundary. They must not report proof completion for a
/// limit, interruption or failure.
pub trait Backend {
    /// Solve one original model under explicit options and cooperative cancellation.
    fn solve(
        &self,
        model: &crate::Model,
        options: &SolveOptions,
        cancel: &CancellationToken,
        warm_start: Option<WarmStart<'_>>,
    ) -> Result<SolveRecord, ValidationError>;
}
