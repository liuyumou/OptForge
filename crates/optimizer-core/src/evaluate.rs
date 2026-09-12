use serde::Serialize;

use crate::serde_strict::deserialize_object;
use crate::{
    Bound, Candidate, Domain, ErrorKind, LinearTerm, Model, SCHEMA_VERSION, ValidationError,
    finite, finite_with, zero,
};

/// Explicit caller policy. There are deliberately no default numerical tolerances.
#[derive(Clone, Copy, Debug, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct Tolerances {
    /// Nonnegative finite absolute feasibility allowance.
    pub absolute: f64,
    /// Nonnegative finite relative feasibility multiplier.
    pub relative: f64,
    /// Absolute discrete-domain allowance in [0, 0.5).
    pub integrality: f64,
}

deserialize_object!(Tolerances {
    absolute: f64,
    relative: f64,
    integrality: f64,
});

impl Tolerances {
    /// Validate explicit numerical policy and normalize signed zeros.
    pub fn validate(self) -> Result<Self, ValidationError> {
        for (name, value) in [
            ("absolute", self.absolute),
            ("relative", self.relative),
            ("integrality", self.integrality),
        ] {
            finite(value, ErrorKind::Tolerance, name)?;
            if value < 0.0 || (name == "integrality" && value >= 0.5) {
                return Err(ValidationError::new(
                    ErrorKind::Tolerance,
                    format!("invalid {name} tolerance"),
                ));
            }
        }
        Ok(Self {
            absolute: zero(self.absolute),
            relative: zero(self.relative),
            integrality: zero(self.integrality),
        })
    }
}

/// Inspectable check against one finite bound.
#[derive(Clone, Debug, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct BoundCheck {
    /// Original finite bound.
    pub bound: f64,
    /// Nonnegative raw violation in the expression's units.
    pub violation: f64,
    /// Applied absolute plus relative allowance.
    pub allowance: f64,
    /// Whether the violation is at most the allowance.
    pub satisfied: bool,
}

deserialize_object!(BoundCheck {
    bound: f64,
    violation: f64,
    allowance: f64,
    satisfied: bool,
});

/// Inspectable distance to an integer or to {0, 1}.
#[derive(Clone, Debug, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct DomainCheck {
    /// Distance to the nearest permitted domain value.
    pub violation: f64,
    /// Caller-supplied integrality tolerance.
    pub allowance: f64,
    /// Whether the domain distance is at most the allowance.
    pub satisfied: bool,
}

deserialize_object!(DomainCheck {
    violation: f64,
    allowance: f64,
    satisfied: bool,
});

/// Original variable value, independent bound checks, and optional domain check.
#[derive(Clone, Debug, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct VariableCheck {
    /// Original variable ID.
    pub variable_id: u32,
    /// Unmodified candidate value, apart from signed-zero normalization.
    pub value: f64,
    /// Lower finite bound check, or null for an unbounded side.
    pub lower: Option<BoundCheck>,
    /// Upper finite bound check, or null for an unbounded side.
    pub upper: Option<BoundCheck>,
    /// Integer/binary domain check, or null for a continuous variable.
    pub domain: Option<DomainCheck>,
}

deserialize_object!(VariableCheck {
    variable_id: u32,
    value: f64,
    lower: Option<BoundCheck>,
    upper: Option<BoundCheck>,
    domain: Option<DomainCheck>,
});

/// Original row activity and bound checks.
#[derive(Clone, Debug, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct ConstraintCheck {
    /// Original constraint ID.
    pub constraint_id: u32,
    /// Original row activity.
    pub activity: f64,
    /// Lower finite bound check.
    pub lower: Option<BoundCheck>,
    /// Upper finite bound check.
    pub upper: Option<BoundCheck>,
}

deserialize_object!(ConstraintCheck {
    constraint_id: u32,
    activity: f64,
    lower: Option<BoundCheck>,
    upper: Option<BoundCheck>,
});

/// Complete candidate assessment, never an optimality or infeasibility proof.
#[derive(Clone, Debug, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct ValidationReport {
    /// Report wire format version.
    pub schema_version: u32,
    /// Original model identity.
    pub model_id: String,
    /// Explicit policy used for this evaluation.
    pub tolerances: Tolerances,
    /// Recomputed original objective, including its offset, even if infeasible.
    pub objective: f64,
    /// Whether all candidate checks pass the supplied tolerances.
    pub feasible: bool,
    /// Checks in increasing original variable-ID order.
    pub variables: Vec<VariableCheck>,
    /// Checks in increasing original constraint-ID order.
    pub constraints: Vec<ConstraintCheck>,
}

deserialize_object!(ValidationReport {
    schema_version: u32,
    model_id: String,
    tolerances: Tolerances,
    objective: f64,
    feasible: bool,
    variables: Vec<VariableCheck>,
    constraints: Vec<ConstraintCheck>,
});

impl Model {
    /// Evaluate an original candidate using explicit tolerances and checked f64 arithmetic.
    pub fn evaluate(
        &self,
        candidate: &Candidate,
        tolerances: Tolerances,
    ) -> Result<ValidationReport, ValidationError> {
        let tolerances = tolerances.validate()?;
        let candidate = candidate.canonical()?;
        let document = self.document();
        if candidate.model_id != document.model_id {
            return Err(ValidationError::new(
                ErrorKind::Candidate,
                "model_id mismatch",
            ));
        }
        if candidate.values.len() != document.variables.len() {
            return Err(ValidationError::new(
                ErrorKind::Candidate,
                "assignment count does not match variables",
            ));
        }
        for (variable, assignment) in document.variables.iter().zip(&candidate.values) {
            if variable.id != assignment.variable_id {
                return Err(ValidationError::new(
                    ErrorKind::Candidate,
                    format!(
                        "expected variable {}, found {}",
                        variable.id, assignment.variable_id
                    ),
                ));
            }
        }
        let mut variables = Vec::with_capacity(document.variables.len());
        let mut feasible = true;
        for (variable, assignment) in document.variables.iter().zip(&candidate.values) {
            let context = format!("variable {}", variable.id);
            let value = assignment.value;
            let domain = match variable.domain {
                Domain::Continuous => None,
                Domain::Integer | Domain::Binary => {
                    if value.abs() > 9_007_199_254_740_992.0 {
                        return Err(ValidationError::new(
                            ErrorKind::Numerical,
                            format!("{context}: discrete magnitude exceeds 2^53"),
                        ));
                    }
                    let violation = zero(match variable.domain {
                        Domain::Binary => value.abs().min(checked(value - 1.0, &context)?.abs()),
                        _ => checked(value - value.round(), &context)?.abs(),
                    });
                    let satisfied = violation <= tolerances.integrality;
                    feasible &= satisfied;
                    Some(DomainCheck {
                        violation,
                        allowance: tolerances.integrality,
                        satisfied,
                    })
                }
            };
            let lower = check_bound(
                variable.lower,
                true,
                value,
                value.abs(),
                tolerances,
                &context,
            )?;
            let upper = check_bound(
                variable.upper,
                false,
                value,
                value.abs(),
                tolerances,
                &context,
            )?;
            feasible &= satisfied(&lower) && satisfied(&upper);
            variables.push(VariableCheck {
                variable_id: variable.id,
                value,
                lower,
                upper,
                domain,
            });
        }
        let (objective, _) = expression(&document.objective.terms, &candidate, false, "objective")?;
        let objective = checked(
            objective + document.objective.offset,
            "objective offset addition",
        )?;
        let mut constraints = Vec::with_capacity(document.constraints.len());
        for constraint in &document.constraints {
            let context = format!("constraint {}", constraint.id);
            let (activity, magnitude) = expression(&constraint.terms, &candidate, true, &context)?;
            let lower = check_bound(
                constraint.lower,
                true,
                activity,
                magnitude,
                tolerances,
                &context,
            )?;
            let upper = check_bound(
                constraint.upper,
                false,
                activity,
                magnitude,
                tolerances,
                &context,
            )?;
            feasible &= satisfied(&lower) && satisfied(&upper);
            constraints.push(ConstraintCheck {
                constraint_id: constraint.id,
                activity,
                lower,
                upper,
            });
        }
        Ok(ValidationReport {
            schema_version: SCHEMA_VERSION,
            model_id: document.model_id.clone(),
            tolerances,
            objective,
            feasible,
            variables,
            constraints,
        })
    }
}

fn checked(value: f64, context: &str) -> Result<f64, ValidationError> {
    finite(value, ErrorKind::Numerical, context)
}

/// [`checked`] with the diagnostic context built only on failure.
fn checked_with<F>(value: f64, context: F) -> Result<f64, ValidationError>
where
    F: FnOnce() -> String,
{
    finite_with(value, ErrorKind::Numerical, context)
}

fn satisfied(check: &Option<BoundCheck>) -> bool {
    check.as_ref().is_none_or(|check| check.satisfied)
}

fn expression(
    terms: &[LinearTerm],
    candidate: &Candidate,
    track_magnitude: bool,
    context: &str,
) -> Result<(f64, f64), ValidationError> {
    let mut sum = 0.0;
    let mut magnitude = 0.0;
    for term in terms {
        let index = candidate
            .values
            .binary_search_by_key(&term.variable_id, |v| v.variable_id)
            .map_err(|_| {
                ValidationError::new(
                    ErrorKind::Candidate,
                    format!("missing variable {}", term.variable_id),
                )
            })?;
        // The per-term context is built inside each closure rather than once
        // before them. It is the same text either way; the difference is that on
        // the success path, which is every path that matters, it is never built.
        let id = term.variable_id;
        let product = checked_with(term.coefficient * candidate.values[index].value, || {
            format!("{context}, variable {id} product")
        })?;
        sum = checked_with(sum + product, || format!("{context}, variable {id} sum"))?;
        if track_magnitude {
            magnitude = checked_with(magnitude + product.abs(), || {
                format!("{context}, variable {id} term magnitude")
            })?;
        }
    }
    Ok((sum, magnitude))
}

fn check_bound(
    bound: Bound,
    lower: bool,
    activity: f64,
    magnitude: f64,
    tolerances: Tolerances,
    context: &str,
) -> Result<Option<BoundCheck>, ValidationError> {
    let Bound::Finite { value: bound } = bound else {
        return Ok(None);
    };
    let violation = if lower && activity < bound {
        checked_with(bound - activity, || format!("{context} lower residual"))?
    } else if !lower && activity > bound {
        checked_with(activity - bound, || format!("{context} upper residual"))?
    } else {
        0.0
    };
    let scale = activity.abs().max(bound.abs()).max(magnitude);
    let relative = checked_with(tolerances.relative * scale, || {
        format!("{context} relative allowance")
    })?;
    let allowance = checked_with(tolerances.absolute + relative, || {
        format!("{context} allowance sum")
    })?;
    Ok(Some(BoundCheck {
        bound,
        violation,
        allowance,
        satisfied: violation <= allowance,
    }))
}
