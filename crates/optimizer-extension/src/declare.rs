//! Extension declarations and the authority model under SPEC-0004.
//!
//! A declaration is what an extension says about itself. Nothing in it is
//! trusted: the category determines the authority the core grants, the host
//! contract version must match exactly, and the transformation category is
//! refused outright because its mathematical validity has no contract yet.

use serde::{Deserialize, Serialize};

use optimizer_core::{Domain, ErrorKind, Model, ValidationError};

use crate::serde_strict::deserialize_object;

/// Current extension document wire version, and the host contract version.
///
/// One scalar covers both deliberately: an extension declaring a different
/// number is refused, so a document-shape change and a contract change are the
/// same event.
pub const EXTENSION_SCHEMA_VERSION: u32 = 1;

/// Longest accepted extension identifier, in bytes.
///
/// Identifiers reach records and diagnostics, so their length is bounded rather
/// than caller-controlled.
pub const MAX_EXTENSION_ID_BYTES: usize = 64;

/// What an extension produces, and therefore what the core must check.
///
/// This mirrors the acceptance boundaries in the research plan's authority
/// table. There is deliberately no backend variant: replaceable numerical
/// backends already exist under SPEC-0002's public `Backend` trait, and
/// restating them here would suggest that contract had been narrowed.
#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum Category {
    /// Proposes complete candidate assignments.
    CandidateProducer,
    /// Proposes search actions such as node or branching-variable choices.
    SearchAdviser,
    /// Cuts, presolve, bound tightening and reformulations.
    ///
    /// Refused at registration. Validity and solution-space preservation
    /// require their own contract, so no code path applies one.
    Transformation,
}

impl<'de> Deserialize<'de> for Category {
    fn deserialize<D: serde::Deserializer<'de>>(deserializer: D) -> Result<Self, D::Error> {
        const NAMES: &[&str] = &["candidate_producer", "search_adviser", "transformation"];
        match String::deserialize(deserializer)?.as_str() {
            "candidate_producer" => Ok(Self::CandidateProducer),
            "search_adviser" => Ok(Self::SearchAdviser),
            "transformation" => Ok(Self::Transformation),
            other => Err(serde::de::Error::unknown_variant(other, NAMES)),
        }
    }
}

impl Category {
    /// Stable lowercase diagnostic name.
    pub fn as_str(self) -> &'static str {
        match self {
            Self::CandidateProducer => "candidate_producer",
            Self::SearchAdviser => "search_adviser",
            Self::Transformation => "transformation",
        }
    }

    /// The consequence the core permits this category's output to have.
    ///
    /// Authority is derived from the category, never chosen by the extension,
    /// so an extension cannot widen its own acceptance boundary.
    pub fn authority(self) -> Option<Authority> {
        match self {
            Self::CandidateProducer => Some(Authority::ProposeValidatedCandidate),
            Self::SearchAdviser => Some(Authority::ProposeCheckedAction),
            Self::Transformation => None,
        }
    }
}

/// The acceptance boundary the core applies to an extension's output.
#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum Authority {
    /// A candidate is published only after original-model validation.
    ProposeValidatedCandidate,
    /// An action takes effect only after the executive checks it against state.
    ProposeCheckedAction,
}

impl<'de> Deserialize<'de> for Authority {
    fn deserialize<D: serde::Deserializer<'de>>(deserializer: D) -> Result<Self, D::Error> {
        const NAMES: &[&str] = &["propose_validated_candidate", "propose_checked_action"];
        match String::deserialize(deserializer)?.as_str() {
            "propose_validated_candidate" => Ok(Self::ProposeValidatedCandidate),
            "propose_checked_action" => Ok(Self::ProposeCheckedAction),
            other => Err(serde::de::Error::unknown_variant(other, NAMES)),
        }
    }
}

/// A model class an extension states it supports.
///
/// The core checks a declaration against the model's actual domains, so an
/// extension cannot be invoked on a class it did not claim.
#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum ProblemClass {
    /// Every variable is continuous.
    Continuous,
    /// At least one variable is integer or binary.
    Discrete,
}

impl<'de> Deserialize<'de> for ProblemClass {
    fn deserialize<D: serde::Deserializer<'de>>(deserializer: D) -> Result<Self, D::Error> {
        const NAMES: &[&str] = &["continuous", "discrete"];
        match String::deserialize(deserializer)?.as_str() {
            "continuous" => Ok(Self::Continuous),
            "discrete" => Ok(Self::Discrete),
            other => Err(serde::de::Error::unknown_variant(other, NAMES)),
        }
    }
}

impl ProblemClass {
    /// The class of an original model, decided by its variable domains.
    pub fn of(model: &Model) -> Self {
        let discrete = model
            .document()
            .variables
            .iter()
            .any(|variable| variable.domain != Domain::Continuous);
        if discrete {
            Self::Discrete
        } else {
            Self::Continuous
        }
    }
}

/// Counted budgets an extension declares it needs.
///
/// Budgets are counts, never durations. A wall-clock extension budget would
/// make the search path depend on machine speed, which would break SPEC-0003
/// requirement 21's replay guarantee.
#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct DeclaredLimits {
    /// Maximum invocations this extension expects to need.
    pub max_invocations: u64,
    /// Maximum candidates it expects to propose in total.
    pub max_proposals: u64,
}

deserialize_object!(DeclaredLimits {
    max_invocations: u64,
    max_proposals: u64,
});

impl DeclaredLimits {
    /// Validate declared budgets; a zero budget cannot be honored.
    ///
    /// # Errors
    ///
    /// Returns an unsupported failure when either budget is zero.
    pub fn validate(self) -> Result<Self, ValidationError> {
        for (name, limit) in [
            ("max_invocations", self.max_invocations),
            ("max_proposals", self.max_proposals),
        ] {
            if limit == 0 {
                return Err(ValidationError::new(
                    ErrorKind::Unsupported,
                    format!("{name} must be positive"),
                ));
            }
        }
        Ok(self)
    }
}

/// What an extension states about itself before it is ever invoked.
///
/// Fields that nothing in C3 reads are deliberately absent. Data needs,
/// hardware requirements and inter-extension dependencies belong to the C4
/// registry; in an all-fields-required document they would force every author
/// to fill in values no code checks.
#[derive(Clone, Debug, PartialEq, Eq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct ExtensionDeclaration {
    /// Must equal [`EXTENSION_SCHEMA_VERSION`].
    pub schema_version: u32,
    /// Stable identity, unique within one search's policy.
    pub extension_id: String,
    /// The extension's own version, recorded for provenance.
    pub version: String,
    /// Must equal [`EXTENSION_SCHEMA_VERSION`] for the extension to be admitted.
    pub host_contract_version: u32,
    /// What this extension produces.
    pub category: Category,
    /// Model classes this extension states it supports.
    pub problem_classes: Vec<ProblemClass>,
    /// Whether identical inputs always produce identical output.
    pub deterministic: bool,
    /// Counted budgets this extension declares it needs.
    pub limits: DeclaredLimits,
}

deserialize_object!(ExtensionDeclaration {
    schema_version: u32,
    extension_id: String,
    version: String,
    host_contract_version: u32,
    category: Category,
    problem_classes: Vec<ProblemClass>,
    deterministic: bool,
    limits: DeclaredLimits,
});

impl ExtensionDeclaration {
    /// Validate a declaration's own shape, keeping each failure categorized.
    ///
    /// Host contract compatibility and category admission are deliberately not
    /// checked here: they are registration decisions the host records as typed
    /// failures rather than errors, so a caller supplying a well-formed but
    /// incompatible extension gets a record entry, not a dead search.
    ///
    /// # Errors
    ///
    /// Returns a categorized [`ValidationError`] for an unsupported schema
    /// version, a malformed identifier or version string, an empty or
    /// duplicated problem-class list, or a zero budget.
    pub fn validate(&self) -> Result<Self, ValidationError> {
        if self.schema_version != EXTENSION_SCHEMA_VERSION {
            return Err(ValidationError::new(
                ErrorKind::Document,
                format!(
                    "unsupported extension schema_version {}",
                    self.schema_version
                ),
            ));
        }
        for (name, text) in [
            ("extension_id", &self.extension_id),
            ("version", &self.version),
        ] {
            if text.is_empty() || text.len() > MAX_EXTENSION_ID_BYTES {
                return Err(ValidationError::new(
                    ErrorKind::Structural,
                    format!("{name} must be 1..={MAX_EXTENSION_ID_BYTES} bytes"),
                ));
            }
            // Identifiers reach diagnostics and records; keep them printable
            // and free of the control characters a log reader cannot see.
            if text.chars().any(char::is_control) {
                return Err(ValidationError::new(
                    ErrorKind::Structural,
                    format!("{name} must not contain control characters"),
                ));
            }
        }
        if self.problem_classes.is_empty() {
            return Err(ValidationError::new(
                ErrorKind::Structural,
                "problem_classes must not be empty",
            ));
        }
        let mut sorted = self.problem_classes.clone();
        sorted.sort_unstable();
        let unique = sorted.len();
        sorted.dedup();
        if sorted.len() != unique {
            return Err(ValidationError::new(
                ErrorKind::Structural,
                "problem_classes must not repeat a class",
            ));
        }
        Ok(Self {
            problem_classes: sorted,
            limits: self.limits.validate()?,
            ..self.clone()
        })
    }

    /// Whether this declaration claims support for `model`'s class.
    pub fn supports(&self, model: &Model) -> bool {
        self.problem_classes.contains(&ProblemClass::of(model))
    }

    /// Serialize a declaration.
    ///
    /// # Errors
    ///
    /// Returns a document failure when serialization fails.
    pub fn to_json(&self) -> Result<String, ValidationError> {
        serde_json::to_string_pretty(self)
            .map_err(|error| ValidationError::new(ErrorKind::Document, error.to_string()))
    }

    /// Parse one complete versioned declaration.
    ///
    /// # Errors
    ///
    /// Returns a document failure for malformed JSON or an unsupported version.
    pub fn from_json(bytes: &[u8]) -> Result<Self, ValidationError> {
        let declaration: Self = serde_json::from_slice(bytes)
            .map_err(|error| ValidationError::new(ErrorKind::Document, error.to_string()))?;
        if declaration.schema_version != EXTENSION_SCHEMA_VERSION {
            return Err(ValidationError::new(
                ErrorKind::Document,
                format!(
                    "unsupported extension schema_version {}",
                    declaration.schema_version
                ),
            ));
        }
        Ok(declaration)
    }
}
