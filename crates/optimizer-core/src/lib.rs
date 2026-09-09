//! Original linear models and candidate validation under SPEC-0001.
//!
//! Construction validates structure; evaluation checks a supplied candidate using
//! explicit tolerances. Neither operation solves a model or establishes a proof.

mod document;
mod evaluate;
mod serde_strict;
mod solve;

pub use document::*;
pub use evaluate::*;
pub use solve::{
    Backend, Basis, BasisStatus, CancellationToken, SOLVE_SCHEMA_VERSION, SolveOptions,
    SolveRecord, Termination, WarmStart, finite_or_absent,
};

use std::fmt;

/// Machine-readable category of a validation failure.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum ErrorKind {
    /// Invalid JSON or an unsupported document version.
    Document,
    /// Invalid original model structure.
    Structural,
    /// Invalid candidate identity, coverage, or values.
    Candidate,
    /// Invalid explicit tolerance policy.
    Tolerance,
    /// Arithmetic cannot safely produce a finite result.
    Numerical,
    /// Valid input that the selected backend cannot honor.
    Unsupported,
    /// A backend or native API call failed.
    Backend,
}

impl ErrorKind {
    /// Stable lowercase diagnostic category.
    pub fn as_str(self) -> &'static str {
        match self {
            Self::Document => "document",
            Self::Structural => "structural",
            Self::Candidate => "candidate",
            Self::Tolerance => "tolerance",
            Self::Numerical => "numerical",
            Self::Unsupported => "unsupported",
            Self::Backend => "backend",
        }
    }
}

/// A categorized failure; no partial evaluation report accompanies an error.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct ValidationError {
    /// Stable error category.
    pub kind: ErrorKind,
    /// Human-readable context, including relevant IDs or fields.
    pub message: String,
}

impl ValidationError {
    /// Construct a categorized failure.
    ///
    /// Backends outside this crate use this to report unsupported input,
    /// native API failures, and rejected numerical output in the same
    /// taxonomy the core and CLI already agree on.
    pub fn new(kind: ErrorKind, message: impl Into<String>) -> Self {
        Self {
            kind,
            message: message.into(),
        }
    }
}

impl fmt::Display for ValidationError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{}: {}", self.kind.as_str(), self.message)
    }
}

impl std::error::Error for ValidationError {}

fn zero(value: f64) -> f64 {
    if value == 0.0 { 0.0 } else { value }
}

/// Reject a nested versioned document whose version is not the expected one.
///
/// A record's own version says nothing about the documents inside it. The
/// version-1 JSON Schemas already pin every nested `schema_version`, so a
/// parser that checked only the outer version would accept documents
/// `tools/validate_artifacts.py` rejects, leaving two normative enforcement
/// paths disagreeing.
///
/// # Errors
///
/// Returns a document failure naming the nested field and both versions.
pub fn nested_version(field: &str, found: u32, expected: u32) -> Result<(), ValidationError> {
    if found != expected {
        return Err(ValidationError::new(
            ErrorKind::Document,
            format!("{field}: unsupported nested schema_version {found}, expected {expected}"),
        ));
    }
    Ok(())
}

fn finite(value: f64, kind: ErrorKind, context: &str) -> Result<f64, ValidationError> {
    if value.is_finite() {
        Ok(zero(value))
    } else {
        Err(ValidationError::new(
            kind,
            format!("{context}: nonfinite value"),
        ))
    }
}
