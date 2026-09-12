use serde::{Deserialize, Serialize};

use crate::serde_strict::{deserialize_object, object};
use crate::{ErrorKind, ValidationError, finite};

/// Current model, candidate and validation report wire version.
pub const SCHEMA_VERSION: u32 = 1;

/// Explicit extended-real bound; finite payloads are checked during construction.
#[derive(Clone, Copy, Debug, PartialEq, Serialize)]
#[serde(tag = "kind", rename_all = "snake_case", deny_unknown_fields)]
pub enum Bound {
    /// No finite lower bound.
    NegativeInfinity,
    /// A finite bound in the variable or row's units.
    Finite {
        /// Bound value.
        value: f64,
    },
    /// No finite upper bound.
    PositiveInfinity,
}

impl<'de> Deserialize<'de> for Bound {
    fn deserialize<D: serde::Deserializer<'de>>(deserializer: D) -> Result<Self, D::Error> {
        // Empty struct variants enforce unknown-field rejection; unit variants do not.
        #[derive(Deserialize)]
        #[serde(tag = "kind", rename_all = "snake_case", deny_unknown_fields)]
        enum Input {
            NegativeInfinity {},
            Finite { value: f64 },
            PositiveInfinity {},
        }
        Ok(match object(deserializer)? {
            Input::NegativeInfinity {} => Self::NegativeInfinity,
            Input::Finite { value } => Self::Finite { value },
            Input::PositiveInfinity {} => Self::PositiveInfinity,
        })
    }
}

/// Supported linear variable domains.
#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum Domain {
    /// Real-valued variable.
    Continuous,
    /// Integer-valued variable.
    Integer,
    /// Variable in the set {0, 1}, independently of its bounds.
    Binary,
}

impl<'de> Deserialize<'de> for Domain {
    fn deserialize<D: serde::Deserializer<'de>>(deserializer: D) -> Result<Self, D::Error> {
        match String::deserialize(deserializer)?.as_str() {
            "continuous" => Ok(Self::Continuous),
            "integer" => Ok(Self::Integer),
            "binary" => Ok(Self::Binary),
            other => Err(serde::de::Error::unknown_variant(
                other,
                &["continuous", "integer", "binary"],
            )),
        }
    }
}

/// Original variable with a stable ID and explicit bounds.
#[derive(Clone, Debug, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct Variable {
    /// Stable caller-assigned identity.
    pub id: u32,
    /// Allowed numerical domain.
    pub domain: Domain,
    /// Lower bound.
    pub lower: Bound,
    /// Upper bound.
    pub upper: Bound,
}

deserialize_object!(Variable {
    id: u32,
    domain: Domain,
    lower: Bound,
    upper: Bound
});

/// One original sparse coefficient; duplicate variable IDs are rejected.
#[derive(Clone, Debug, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct LinearTerm {
    /// Referenced original variable ID.
    pub variable_id: u32,
    /// Finite coefficient, including zero.
    pub coefficient: f64,
}

deserialize_object!(LinearTerm {
    variable_id: u32,
    coefficient: f64
});

/// Original ranged linear constraint, including equalities and free rows.
#[derive(Clone, Debug, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct Constraint {
    /// Stable caller-assigned identity.
    pub id: u32,
    /// Lower activity bound.
    pub lower: Bound,
    /// Upper activity bound.
    pub upper: Bound,
    /// Sparse expression in original variables.
    pub terms: Vec<LinearTerm>,
}

deserialize_object!(Constraint { id: u32, lower: Bound, upper: Bound, terms: Vec<LinearTerm> });

/// Objective direction; recomputation never negates the original objective.
#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum ObjectiveSense {
    /// Minimize the original expression.
    Minimize,
    /// Maximize the original expression.
    Maximize,
}

impl<'de> Deserialize<'de> for ObjectiveSense {
    fn deserialize<D: serde::Deserializer<'de>>(deserializer: D) -> Result<Self, D::Error> {
        match String::deserialize(deserializer)?.as_str() {
            "minimize" => Ok(Self::Minimize),
            "maximize" => Ok(Self::Maximize),
            other => Err(serde::de::Error::unknown_variant(
                other,
                &["minimize", "maximize"],
            )),
        }
    }
}

/// Original linear objective.
#[derive(Clone, Debug, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct Objective {
    /// Optimization direction, retained even though M1 does not solve.
    pub sense: ObjectiveSense,
    /// Finite constant added after the sparse sum.
    pub offset: f64,
    /// Original sparse coefficients.
    pub terms: Vec<LinearTerm>,
}

deserialize_object!(Objective { sense: ObjectiveSense, offset: f64, terms: Vec<LinearTerm> });

/// Unvalidated model input. Use [`Model::new`] before evaluation or canonical output.
#[derive(Clone, Debug, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct ModelDocument {
    /// Must equal [`SCHEMA_VERSION`].
    pub schema_version: u32,
    /// Nonempty caller-assigned model identity.
    pub model_id: String,
    /// Original variables, canonicalized by ID on construction.
    pub variables: Vec<Variable>,
    /// Original constraints, canonicalized by ID on construction.
    pub constraints: Vec<Constraint>,
    /// Original objective.
    pub objective: Objective,
}

deserialize_object!(ModelDocument {
    schema_version: u32,
    model_id: String,
    variables: Vec<Variable>,
    constraints: Vec<Constraint>,
    objective: Objective,
});

/// Immutable structurally valid original model. This is not a feasibility proof.
#[derive(Clone, Debug, PartialEq)]
pub struct Model {
    document: ModelDocument,
}

impl Model {
    /// Validate and canonicalize original model data without modifying coefficients.
    pub fn new(mut document: ModelDocument) -> Result<Self, ValidationError> {
        version(document.schema_version)?;
        identity(&document.model_id, ErrorKind::Structural)?;
        document.variables.sort_by_key(|v| v.id);
        document.constraints.sort_by_key(|c| c.id);
        unique(
            document.variables.iter().map(|v| v.id),
            ErrorKind::Structural,
            "variable",
        )?;
        unique(
            document.constraints.iter().map(|c| c.id),
            ErrorKind::Structural,
            "constraint",
        )?;
        for variable in &mut document.variables {
            bounds(
                &mut variable.lower,
                &mut variable.upper,
                &format!("variable {}", variable.id),
            )?;
        }
        for constraint in &mut document.constraints {
            let context = format!("constraint {}", constraint.id);
            bounds(&mut constraint.lower, &mut constraint.upper, &context)?;
            terms(&mut constraint.terms, &document.variables, &context)?;
        }
        document.objective.offset = finite(
            document.objective.offset,
            ErrorKind::Structural,
            "objective offset",
        )?;
        terms(
            &mut document.objective.terms,
            &document.variables,
            "objective",
        )?;
        Ok(Self { document })
    }

    /// Read-only access to the canonical original document.
    pub fn document(&self) -> &ModelDocument {
        &self.document
    }

    /// Parse one complete versioned JSON document and validate model structure.
    pub fn from_json(bytes: &[u8]) -> Result<Self, ValidationError> {
        Self::new(serde_json::from_slice(bytes).map_err(json_error)?)
    }

    /// Serialize canonical model data with stable ordering and f64 round trips.
    pub fn to_json(&self) -> Result<String, ValidationError> {
        serde_json::to_string_pretty(&self.document).map_err(json_error)
    }

    /// Stable fingerprint of the canonical model document.
    ///
    /// Warm starts are bound to this value rather than to `model_id` alone, so a
    /// basis cannot be replayed against changed data under the same identity.
    /// This identifies canonical bytes; it is not a cryptographic commitment.
    pub fn fingerprint(&self) -> Result<String, ValidationError> {
        let canonical = self.to_json()?;
        // FNV-1a over the canonical bytes: deterministic and dependency-free.
        let mut hash: u64 = 0xcbf2_9ce4_8422_2325;
        for byte in canonical.as_bytes() {
            hash ^= u64::from(*byte);
            hash = hash.wrapping_mul(0x0000_0100_0000_01b3);
        }
        Ok(format!("fnv1a64:{hash:016x}"))
    }
}

/// One supplied original-variable value.
#[derive(Clone, Debug, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct Assignment {
    /// Stable original variable identity.
    pub variable_id: u32,
    /// Supplied finite value, never rounded or clamped.
    pub value: f64,
}

deserialize_object!(Assignment {
    variable_id: u32,
    value: f64
});

/// Candidate input; identity and variable coverage are verified during evaluation.
#[derive(Clone, Debug, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct Candidate {
    /// Must equal [`SCHEMA_VERSION`].
    pub schema_version: u32,
    /// Original model identity.
    pub model_id: String,
    /// Exactly one assignment per original variable.
    pub values: Vec<Assignment>,
}

deserialize_object!(Candidate { schema_version: u32, model_id: String, values: Vec<Assignment> });

impl Candidate {
    pub(crate) fn canonical(&self) -> Result<Self, ValidationError> {
        version(self.schema_version)?;
        identity(&self.model_id, ErrorKind::Candidate)?;
        let mut candidate = self.clone();
        candidate.values.sort_by_key(|v| v.variable_id);
        unique(
            candidate.values.iter().map(|v| v.variable_id),
            ErrorKind::Candidate,
            "assignment",
        )?;
        for assignment in &mut candidate.values {
            assignment.value = finite(
                assignment.value,
                ErrorKind::Candidate,
                &format!("variable {}", assignment.variable_id),
            )?;
        }
        Ok(candidate)
    }

    /// Parse and canonicalize candidate shape and values; evaluation checks coverage.
    pub fn from_json(bytes: &[u8]) -> Result<Self, ValidationError> {
        let candidate: Self = serde_json::from_slice(bytes).map_err(json_error)?;
        candidate.canonical()
    }

    /// Validate and serialize candidate data in variable-ID order.
    pub fn to_json(&self) -> Result<String, ValidationError> {
        serde_json::to_string_pretty(&self.canonical()?).map_err(json_error)
    }
}

fn json_error(error: serde_json::Error) -> ValidationError {
    ValidationError::new(ErrorKind::Document, error.to_string())
}

fn version(value: u32) -> Result<(), ValidationError> {
    if value != SCHEMA_VERSION {
        return Err(ValidationError::new(
            ErrorKind::Document,
            format!("unsupported schema_version {value}"),
        ));
    }
    Ok(())
}

fn identity(value: &str, kind: ErrorKind) -> Result<(), ValidationError> {
    if value.is_empty() {
        return Err(ValidationError::new(kind, "model_id must not be empty"));
    }
    Ok(())
}

fn unique(
    ids: impl Iterator<Item = u32>,
    kind: ErrorKind,
    context: &str,
) -> Result<(), ValidationError> {
    let mut previous = None;
    for id in ids {
        if previous == Some(id) {
            return Err(ValidationError::new(
                kind,
                format!("duplicate {context} ID {id}"),
            ));
        }
        previous = Some(id);
    }
    Ok(())
}

fn bounds(lower: &mut Bound, upper: &mut Bound, context: &str) -> Result<(), ValidationError> {
    for bound in [&mut *lower, &mut *upper] {
        if let Bound::Finite { value } = bound {
            *value = finite(*value, ErrorKind::Structural, context)?;
        }
    }
    let invalid = matches!(lower, Bound::PositiveInfinity)
        || matches!(upper, Bound::NegativeInfinity)
        || matches!((&*lower, &*upper), (Bound::Finite { value: l }, Bound::Finite { value: u }) if l > u);
    if invalid {
        return Err(ValidationError::new(
            ErrorKind::Structural,
            format!("{context}: invalid bounds"),
        ));
    }
    Ok(())
}

fn terms(
    terms: &mut [LinearTerm],
    variables: &[Variable],
    context: &str,
) -> Result<(), ValidationError> {
    terms.sort_by_key(|t| t.variable_id);
    unique(
        terms.iter().map(|t| t.variable_id),
        ErrorKind::Structural,
        context,
    )?;
    for term in terms {
        // Built inside the closures rather than once per term. `Model::new` runs
        // once per branch-and-bound node through `node::relaxation`, so this loop
        // is on the node path and allocated one `String` per nonzero for text
        // that a valid model never produces.
        let id = term.variable_id;
        if variables.binary_search_by_key(&id, |v| v.id).is_err() {
            return Err(ValidationError::new(
                ErrorKind::Structural,
                format!("{context}, variable {id}: unknown variable"),
            ));
        }
        term.coefficient = crate::finite_with(term.coefficient, ErrorKind::Structural, || {
            format!("{context}, variable {id}")
        })?;
    }
    Ok(())
}
