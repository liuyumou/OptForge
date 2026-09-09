//! Owned search contracts and reproducible records under SPEC-0003.
//!
//! These types express a claim the backend contract deliberately cannot make:
//! that the executive exhausted its own node tree. A relaxation's
//! [`optimizer_core::Termination`] describes one solve; [`SearchOutcome`]
//! describes a search. Neither implies the other, and neither is an
//! exact-arithmetic certificate.

use serde::{Deserialize, Serialize};

use optimizer_core::{
    Candidate, ErrorKind, ObjectiveSense, SolveOptions, ValidationError, ValidationReport,
};

use crate::serde_strict::deserialize_object;

/// Current search configuration, record and checkpoint wire version.
pub const SEARCH_SCHEMA_VERSION: u32 = 1;

/// Explicit search configuration.
///
/// Every budget is caller-supplied; there are deliberately no defaults, so a
/// record always states the budgets that produced it.
#[derive(Clone, Debug, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct SearchOptions {
    /// Must equal [`SEARCH_SCHEMA_VERSION`].
    pub schema_version: u32,
    /// Deterministic seed recorded for this search.
    pub seed: u64,
    /// Optional limit on explored nodes; `None` means unlimited.
    pub node_limit: Option<u64>,
    /// Optional wall-clock limit in milliseconds; `None` means unlimited.
    pub time_limit_ms: Option<u64>,
    /// Optional bound on the open-node frontier; `None` means unlimited.
    pub open_node_limit: Option<u64>,
    /// Absolute objective improvement required to accept or to refuse a prune.
    pub improvement_tolerance: f64,
    /// Configuration applied to every node relaxation.
    pub relaxation: SolveOptions,
}

deserialize_object!(SearchOptions {
    schema_version: u32,
    seed: u64,
    node_limit: Option<u64>,
    time_limit_ms: Option<u64>,
    open_node_limit: Option<u64>,
    improvement_tolerance: f64,
    relaxation: SolveOptions,
});

impl SearchOptions {
    /// Validate configuration, keeping each failure in its own category.
    pub fn validate(&self) -> Result<Self, ValidationError> {
        if self.schema_version != SEARCH_SCHEMA_VERSION {
            return Err(ValidationError::new(
                ErrorKind::Document,
                format!("unsupported search schema_version {}", self.schema_version),
            ));
        }
        for (name, limit) in [
            ("node_limit", self.node_limit),
            ("time_limit_ms", self.time_limit_ms),
            ("open_node_limit", self.open_node_limit),
        ] {
            if limit == Some(0) {
                return Err(ValidationError::new(
                    ErrorKind::Unsupported,
                    format!("{name} must be positive when present"),
                ));
            }
        }
        if !self.improvement_tolerance.is_finite() || self.improvement_tolerance < 0.0 {
            return Err(ValidationError::new(
                ErrorKind::Tolerance,
                "improvement_tolerance must be finite and nonnegative",
            ));
        }
        Ok(Self {
            improvement_tolerance: crate::positive_zero(self.improvement_tolerance),
            relaxation: self.relaxation.validate()?,
            ..self.clone()
        })
    }
}

/// Engine-owned outcome of one search.
///
/// Only an exhausted node tree whose every prune was justified by a proven
/// relaxation may report a completed proof. A limit, interruption or failure
/// never does.
#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum SearchOutcome {
    /// The node tree was exhausted and a validated incumbent is optimal.
    ProvenOptimal,
    /// The node tree was exhausted with no feasible assignment.
    ProvenInfeasible,
    /// A relaxation was unbounded, so the model is unbounded or infeasible.
    UnboundedOrInfeasible,
    /// A validated incumbent exists without a proof of optimality.
    Feasible,
    /// The configured node limit was reached.
    NodeLimit,
    /// The configured wall-clock limit was reached.
    TimeLimit,
    /// The configured open-node limit was reached.
    OpenNodeLimit,
    /// Cancellation was observed.
    Interrupted,
    /// A relaxation result could not be accepted numerically.
    NumericalFailure,
    /// A relaxation reported a backend failure.
    BackendFailure,
    /// The request is not supported by this executive.
    Unsupported,
}

impl<'de> Deserialize<'de> for SearchOutcome {
    fn deserialize<D: serde::Deserializer<'de>>(deserializer: D) -> Result<Self, D::Error> {
        const NAMES: &[&str] = &[
            "proven_optimal",
            "proven_infeasible",
            "unbounded_or_infeasible",
            "feasible",
            "node_limit",
            "time_limit",
            "open_node_limit",
            "interrupted",
            "numerical_failure",
            "backend_failure",
            "unsupported",
        ];
        match String::deserialize(deserializer)?.as_str() {
            "proven_optimal" => Ok(Self::ProvenOptimal),
            "proven_infeasible" => Ok(Self::ProvenInfeasible),
            "unbounded_or_infeasible" => Ok(Self::UnboundedOrInfeasible),
            "feasible" => Ok(Self::Feasible),
            "node_limit" => Ok(Self::NodeLimit),
            "time_limit" => Ok(Self::TimeLimit),
            "open_node_limit" => Ok(Self::OpenNodeLimit),
            "interrupted" => Ok(Self::Interrupted),
            "numerical_failure" => Ok(Self::NumericalFailure),
            "backend_failure" => Ok(Self::BackendFailure),
            "unsupported" => Ok(Self::Unsupported),
            other => Err(serde::de::Error::unknown_variant(other, NAMES)),
        }
    }
}

impl SearchOutcome {
    /// Whether the executive claims a finished proof for this outcome.
    ///
    /// Limits, interruptions and failures are excluded, so a search that ran
    /// out of budget can never be presented as a completed proof.
    pub fn proves_completion(self) -> bool {
        matches!(
            self,
            Self::ProvenOptimal | Self::ProvenInfeasible | Self::UnboundedOrInfeasible
        )
    }
}

/// Immutable record of one search, sufficient to repeat it.
///
/// An unavailable or nonfinite measurement is omitted rather than serialized as
/// a null standing in for a real number.
#[derive(Clone, Debug, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct SearchRecord {
    /// Must equal [`SEARCH_SCHEMA_VERSION`].
    pub schema_version: u32,
    /// Original model identity.
    pub model_id: String,
    /// Relaxation backend identifier.
    pub backend: String,
    /// Relaxation backend version as the backend reported it.
    pub backend_version: String,
    /// Engine-owned search outcome.
    pub outcome: SearchOutcome,
    /// Independently recomputed original objective of the incumbent.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub objective: Option<f64>,
    /// Best valid dual bound, when one is available.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub dual_bound: Option<f64>,
    /// Relative gap between incumbent and dual bound, when finite.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub gap: Option<f64>,
    /// Accepted incumbent in original variable IDs.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub candidate: Option<Candidate>,
    /// Independent original-model validation of the incumbent.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub validation: Option<ValidationReport>,
    /// Nodes whose relaxation was dispatched.
    pub nodes_explored: u64,
    /// Nodes closed by a proven infeasible relaxation or empty branch domain.
    pub nodes_pruned_infeasible: u64,
    /// Nodes closed by a valid dual bound against the incumbent.
    pub nodes_pruned_bound: u64,
    /// Nodes still open when the search stopped.
    pub open_nodes_remaining: u64,
    /// Relaxation solves dispatched to the backend.
    pub relaxations_solved: u64,
    /// Whether any node lost its proof claim under requirement 6.
    pub forfeited: bool,
    /// Executive warnings, retained even on success.
    pub warnings: Vec<String>,
    /// Measured elapsed wall-clock time in milliseconds.
    pub elapsed_ms: u64,
    /// Explicit configuration this search actually used.
    pub options: SearchOptions,
}

deserialize_object!(SearchRecord {
    schema_version: u32,
    model_id: String,
    backend: String,
    backend_version: String,
    outcome: SearchOutcome,
    objective: Option<f64>,
    dual_bound: Option<f64>,
    gap: Option<f64>,
    candidate: Option<Candidate>,
    validation: Option<ValidationReport>,
    nodes_explored: u64,
    nodes_pruned_infeasible: u64,
    nodes_pruned_bound: u64,
    open_nodes_remaining: u64,
    relaxations_solved: u64,
    forfeited: bool,
    warnings: Vec<String>,
    elapsed_ms: u64,
    options: SearchOptions,
});

impl SearchRecord {
    /// Serialize a record, rejecting nonfinite measurements rather than
    /// emitting a null in place of an allegedly finite number.
    pub fn to_json(&self) -> Result<String, ValidationError> {
        for (name, value) in [
            ("objective", self.objective),
            ("dual_bound", self.dual_bound),
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

    /// Parse one complete versioned search record.
    pub fn from_json(bytes: &[u8]) -> Result<Self, ValidationError> {
        let record: Self = serde_json::from_slice(bytes)
            .map_err(|error| ValidationError::new(ErrorKind::Document, error.to_string()))?;
        if record.schema_version != SEARCH_SCHEMA_VERSION {
            return Err(ValidationError::new(
                ErrorKind::Document,
                format!(
                    "unsupported search schema_version {}",
                    record.schema_version
                ),
            ));
        }
        Ok(record)
    }
}

/// One branching restriction on a single discrete variable.
///
/// A node stores only its restrictions, never a copy of the model, so the
/// frontier's memory is bounded by the open-node limit times the branching
/// depth rather than by the model size.
#[derive(Clone, Debug, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct Restriction {
    /// Original variable identity.
    pub variable_id: u32,
    /// Additional finite lower bound, when branching imposed one.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub lower: Option<f64>,
    /// Additional finite upper bound, when branching imposed one.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub upper: Option<f64>,
}

deserialize_object!(Restriction {
    variable_id: u32,
    lower: Option<f64>,
    upper: Option<f64>,
});

/// One open node in a serialized frontier.
#[derive(Clone, Debug, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct CheckpointNode {
    /// Deterministic node identity, assigned in creation order.
    pub node_id: u64,
    /// Valid dual bound inherited from the parent relaxation, when one exists.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub parent_bound: Option<f64>,
    /// Branching restrictions in increasing original variable-ID order.
    pub restrictions: Vec<Restriction>,
}

deserialize_object!(CheckpointNode {
    node_id: u64,
    parent_bound: Option<f64>,
    restrictions: Vec<Restriction>,
});

/// Versioned snapshot of an unfinished search.
///
/// C2 defines and serializes this shape. Restart from a checkpoint is
/// deliberately **not** implemented and requires its own acceptance evidence
/// before any public restart entry point exists.
#[derive(Clone, Debug, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct Checkpoint {
    /// Must equal [`SEARCH_SCHEMA_VERSION`].
    pub schema_version: u32,
    /// Original model identity.
    pub model_id: String,
    /// Fingerprint of the canonical original model document.
    pub model_fingerprint: String,
    /// Open frontier in deterministic node order.
    pub open_nodes: Vec<CheckpointNode>,
    /// Accepted incumbent, when one exists.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub incumbent: Option<Candidate>,
    /// Recomputed objective of the incumbent, when one exists.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub incumbent_objective: Option<f64>,
    /// Best valid dual bound over the frontier, when one exists.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub dual_bound: Option<f64>,
    /// Nodes whose relaxation was dispatched before the snapshot.
    pub nodes_explored: u64,
    /// Whether the search had already lost its proof claim.
    pub forfeited: bool,
}

deserialize_object!(Checkpoint {
    schema_version: u32,
    model_id: String,
    model_fingerprint: String,
    open_nodes: Vec<CheckpointNode>,
    incumbent: Option<Candidate>,
    incumbent_objective: Option<f64>,
    dual_bound: Option<f64>,
    nodes_explored: u64,
    forfeited: bool,
});

impl Checkpoint {
    /// Serialize a checkpoint, rejecting nonfinite measurements.
    pub fn to_json(&self) -> Result<String, ValidationError> {
        serde_json::to_string_pretty(self)
            .map_err(|error| ValidationError::new(ErrorKind::Document, error.to_string()))
    }

    /// Parse one complete versioned checkpoint.
    ///
    /// Parsing does not imply restart support; no entry point consumes a
    /// checkpoint in C2.
    pub fn from_json(bytes: &[u8]) -> Result<Self, ValidationError> {
        let checkpoint: Self = serde_json::from_slice(bytes)
            .map_err(|error| ValidationError::new(ErrorKind::Document, error.to_string()))?;
        if checkpoint.schema_version != SEARCH_SCHEMA_VERSION {
            return Err(ValidationError::new(
                ErrorKind::Document,
                format!(
                    "unsupported checkpoint schema_version {}",
                    checkpoint.schema_version
                ),
            ));
        }
        Ok(checkpoint)
    }
}

/// Whether `candidate` improves on `incumbent` by more than `tolerance`.
pub(crate) fn improves(
    candidate: f64,
    incumbent: f64,
    sense: ObjectiveSense,
    tolerance: f64,
) -> bool {
    match sense {
        ObjectiveSense::Minimize => candidate < incumbent - tolerance,
        ObjectiveSense::Maximize => candidate > incumbent + tolerance,
    }
}

/// Whether `left` is a more optimistic dual bound than `right`.
pub(crate) fn is_better_bound(left: f64, right: f64, sense: ObjectiveSense) -> bool {
    match sense {
        ObjectiveSense::Minimize => left < right,
        ObjectiveSense::Maximize => left > right,
    }
}
