//! Extension policy, summaries and typed failures under SPEC-0004.
//!
//! These are the structured artifacts the closing evidence requires. An
//! extension that misbehaves produces a typed entry here rather than a silent
//! degradation, and the search that contained it still reports the outcome it
//! would have reported without it.
//!
//! Diagnostics are bounded independently of node count: counters accumulate,
//! but distinct failure entries are capped, because an extension rejecting once
//! per node would otherwise grow memory with the search.

use serde::{Deserialize, Serialize};

use optimizer_core::{ErrorKind, ValidationError};

use crate::declare::{Authority, Category, EXTENSION_SCHEMA_VERSION};
use crate::serde_strict::deserialize_object;

/// Distinct failure entries retained per extension.
///
/// Counters remain exact; only the retained messages are capped, so a hostile
/// extension cannot grow a record with the node count.
pub const MAX_RETAINED_FAILURES: usize = 8;

/// Longest retained failure message, in bytes.
pub const MAX_FAILURE_MESSAGE_BYTES: usize = 200;

/// Why an extension's output was refused, or why it was disabled.
///
/// Matched exhaustively everywhere, with no catch-all arm, so a later variant
/// fails to compile rather than being silently absorbed.
#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum FailureKind {
    /// The declaration itself did not validate.
    DeclarationInvalid,
    /// The declared host contract version is not this host's.
    IncompatibleContract,
    /// The declared category is not admitted in a proving search.
    UnsupportedCategory,
    /// The declaration does not claim support for this model's class.
    UnsupportedProblemClass,
    /// A proposed candidate failed original-model validation.
    InvalidCandidate,
    /// Proposed advice did not match the executive's real state.
    InvalidAdvice,
    /// A declared or policy budget was exhausted.
    BudgetExhausted,
    /// The extension panicked and was contained.
    Panicked,
}

impl<'de> Deserialize<'de> for FailureKind {
    fn deserialize<D: serde::Deserializer<'de>>(deserializer: D) -> Result<Self, D::Error> {
        const NAMES: &[&str] = &[
            "declaration_invalid",
            "incompatible_contract",
            "unsupported_category",
            "unsupported_problem_class",
            "invalid_candidate",
            "invalid_advice",
            "budget_exhausted",
            "panicked",
        ];
        match String::deserialize(deserializer)?.as_str() {
            "declaration_invalid" => Ok(Self::DeclarationInvalid),
            "incompatible_contract" => Ok(Self::IncompatibleContract),
            "unsupported_category" => Ok(Self::UnsupportedCategory),
            "unsupported_problem_class" => Ok(Self::UnsupportedProblemClass),
            "invalid_candidate" => Ok(Self::InvalidCandidate),
            "invalid_advice" => Ok(Self::InvalidAdvice),
            "budget_exhausted" => Ok(Self::BudgetExhausted),
            "panicked" => Ok(Self::Panicked),
            other => Err(serde::de::Error::unknown_variant(other, NAMES)),
        }
    }
}

impl FailureKind {
    /// Stable lowercase diagnostic name.
    pub fn as_str(self) -> &'static str {
        match self {
            Self::DeclarationInvalid => "declaration_invalid",
            Self::IncompatibleContract => "incompatible_contract",
            Self::UnsupportedCategory => "unsupported_category",
            Self::UnsupportedProblemClass => "unsupported_problem_class",
            Self::InvalidCandidate => "invalid_candidate",
            Self::InvalidAdvice => "invalid_advice",
            Self::BudgetExhausted => "budget_exhausted",
            Self::Panicked => "panicked",
        }
    }

    /// Whether this failure permanently excludes the extension from a search.
    ///
    /// A rejected proposal or a rejected action is a normal event: the core
    /// refused an opinion and continues. A panic, an exhausted budget or a
    /// refused registration ends the extension's participation. Disabling a
    /// panicked extension is required for soundness, not policy: it may have
    /// left its own state unusable, so a further call could panic forever.
    pub fn disables(self) -> bool {
        match self {
            Self::InvalidCandidate | Self::InvalidAdvice => false,
            Self::DeclarationInvalid
            | Self::IncompatibleContract
            | Self::UnsupportedCategory
            | Self::UnsupportedProblemClass
            | Self::BudgetExhausted
            | Self::Panicked => true,
        }
    }
}

/// One retained failure: a category and a bounded explanation.
#[derive(Clone, Debug, PartialEq, Eq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct ExtensionFailure {
    /// Machine-readable failure category.
    pub kind: FailureKind,
    /// Bounded human-readable detail.
    pub message: String,
}

deserialize_object!(ExtensionFailure {
    kind: FailureKind,
    message: String,
});

impl ExtensionFailure {
    /// Build a failure, truncating the message at a character boundary.
    pub fn new(kind: FailureKind, message: impl Into<String>) -> Self {
        let mut message = message.into();
        if message.len() > MAX_FAILURE_MESSAGE_BYTES {
            // Truncate on a character boundary; a byte split would panic.
            let mut end = MAX_FAILURE_MESSAGE_BYTES;
            while end > 0 && !message.is_char_boundary(end) {
                end -= 1;
            }
            message.truncate(end);
        }
        Self { kind, message }
    }
}

/// The caller's permission for one extension in one search.
///
/// Budgets are counted, never timed, and there are deliberately no defaults, so
/// a record always states the budgets that produced it.
#[derive(Clone, Debug, PartialEq, Eq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct ExtensionPolicy {
    /// Must equal [`EXTENSION_SCHEMA_VERSION`].
    pub schema_version: u32,
    /// Identity of the permitted extension.
    pub extension_id: String,
    /// Maximum invocations permitted across the whole search.
    pub invocation_budget: u64,
    /// Maximum candidates permitted across the whole search.
    pub proposal_budget: u64,
}

deserialize_object!(ExtensionPolicy {
    schema_version: u32,
    extension_id: String,
    invocation_budget: u64,
    proposal_budget: u64,
});

impl ExtensionPolicy {
    /// Validate one policy entry, keeping each failure categorized.
    ///
    /// # Errors
    ///
    /// Returns a categorized [`ValidationError`] for an unsupported version, an
    /// empty identifier, or a zero budget.
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
        if self.extension_id.is_empty() {
            return Err(ValidationError::new(
                ErrorKind::Structural,
                "extension_id must not be empty",
            ));
        }
        for (name, budget) in [
            ("invocation_budget", self.invocation_budget),
            ("proposal_budget", self.proposal_budget),
        ] {
            if budget == 0 {
                return Err(ValidationError::new(
                    ErrorKind::Unsupported,
                    format!("{name} must be positive"),
                ));
            }
        }
        Ok(self.clone())
    }
}

/// Validate a whole policy list, rejecting duplicate identities.
///
/// A duplicate identity would make the recorded summary ambiguous about which
/// entry governed which invocation.
///
/// # Errors
///
/// Returns a categorized [`ValidationError`] when an entry is invalid or an
/// identity repeats.
pub fn validate_policies(
    policies: &[ExtensionPolicy],
) -> Result<Vec<ExtensionPolicy>, ValidationError> {
    let validated: Vec<ExtensionPolicy> = policies
        .iter()
        .map(ExtensionPolicy::validate)
        .collect::<Result<_, _>>()?;
    let mut identities: Vec<&str> = validated
        .iter()
        .map(|policy| policy.extension_id.as_str())
        .collect();
    identities.sort_unstable();
    let total = identities.len();
    identities.dedup();
    if identities.len() != total {
        return Err(ValidationError::new(
            ErrorKind::Structural,
            "extension policy must not repeat an extension_id",
        ));
    }
    Ok(validated)
}

/// What one registered extension did during one search.
///
/// This is what makes an extension-influenced record honest: a reader can see
/// which extensions participated, what they were permitted to do, how much of
/// their output was accepted, and why any of them stopped being consulted.
#[derive(Clone, Debug, PartialEq, Eq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct ExtensionSummary {
    /// Must equal [`EXTENSION_SCHEMA_VERSION`].
    pub schema_version: u32,
    /// Identity of the extension this entry describes.
    pub extension_id: String,
    /// The extension's own reported version.
    pub version: String,
    /// The declared category.
    pub category: Category,
    /// The acceptance boundary the core applied, absent for a refused category.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub authority: Option<Authority>,
    /// Whether the extension declared itself deterministic.
    pub deterministic: bool,
    /// Whether registration admitted it at all.
    pub registered: bool,
    /// Invocations actually dispatched.
    pub invocations: u64,
    /// Candidates or actions offered.
    pub proposals: u64,
    /// Proposals or actions the core accepted.
    pub accepted: u64,
    /// Proposals or actions the core rejected.
    pub rejected: u64,
    /// Whether the extension was disabled before the search ended.
    pub disabled: bool,
    /// Bounded distinct failures, capped at [`MAX_RETAINED_FAILURES`].
    pub failures: Vec<ExtensionFailure>,
}

deserialize_object!(ExtensionSummary {
    schema_version: u32,
    extension_id: String,
    version: String,
    category: Category,
    authority: Option<Authority>,
    deterministic: bool,
    registered: bool,
    invocations: u64,
    proposals: u64,
    accepted: u64,
    rejected: u64,
    disabled: bool,
    failures: Vec<ExtensionFailure>,
});

impl ExtensionSummary {
    /// Serialize a summary.
    ///
    /// # Errors
    ///
    /// Returns a document failure when serialization fails.
    pub fn to_json(&self) -> Result<String, ValidationError> {
        serde_json::to_string_pretty(self)
            .map_err(|error| ValidationError::new(ErrorKind::Document, error.to_string()))
    }

    /// Parse one complete versioned summary.
    ///
    /// # Errors
    ///
    /// Returns a document failure for malformed JSON or an unsupported version.
    pub fn from_json(bytes: &[u8]) -> Result<Self, ValidationError> {
        let summary: Self = serde_json::from_slice(bytes)
            .map_err(|error| ValidationError::new(ErrorKind::Document, error.to_string()))?;
        if summary.schema_version != EXTENSION_SCHEMA_VERSION {
            return Err(ValidationError::new(
                ErrorKind::Document,
                format!(
                    "unsupported extension schema_version {}",
                    summary.schema_version
                ),
            ));
        }
        Ok(summary)
    }
}
