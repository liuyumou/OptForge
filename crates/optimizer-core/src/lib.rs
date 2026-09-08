//! Original linear models and candidate validation under SPEC-0001.
//!
//! Construction validates structure; evaluation checks a supplied candidate using
//! explicit tolerances. Neither operation solves a model or establishes a proof.

mod document;
mod evaluate;

pub use document::*;
pub use evaluate::*;

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
    pub(crate) fn new(kind: ErrorKind, message: impl Into<String>) -> Self {
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
