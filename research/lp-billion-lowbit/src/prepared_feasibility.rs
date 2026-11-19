//! Isolated derivative of lp-fp4-checker/src/prepared_feasibility.rs.
//! Borrow immutable original data; dense IDs avoid repeated binary searches.
//! Original feasibility arithmetic with immutable variable lookup indices.
//! Every operation, bound check and first numerical error stays in original order.
use optimizer_core::{
    Bound, BoundCheck, ConstraintCheck, Domain, DomainCheck, ErrorKind, LinearTerm, Model,
    SCHEMA_VERSION, Tolerances, ValidationError, ValidationReport, VariableCheck,
};
fn zero(value: f64) -> f64 {
    if value == 0.0 { 0.0 } else { value }
}
fn finite(value: f64, kind: ErrorKind, context: &str) -> Result<f64, ValidationError> {
    finite_with(value, kind, || context.to_owned())
}
fn finite_with<F: FnOnce() -> String>(
    value: f64,
    kind: ErrorKind,
    context: F,
) -> Result<f64, ValidationError> {
    if value.is_finite() {
        Ok(zero(value))
    } else {
        Err(ValidationError::new(
            kind,
            format!("{}: nonfinite value", context()),
        ))
    }
}
pub struct Prepared<'a> {
    model: &'a Model,
    objective_indices: Vec<usize>,
    row_indices: Vec<Vec<usize>>,
}
impl<'a> Prepared<'a> {
    pub fn original(
        &self,
        primal: &[f64],
        tolerances: Tolerances,
    ) -> Result<ValidationReport, ValidationError> {
        let candidate = optimizer_core::Candidate {
            schema_version: 1,
            model_id: self.model.document().model_id.clone(),
            values: self
                .model
                .document()
                .variables
                .iter()
                .zip(primal)
                .map(|(v, &value)| optimizer_core::Assignment {
                    variable_id: v.id,
                    value,
                })
                .collect(),
        };
        self.model.evaluate(&candidate, tolerances)
    }
    pub fn new(model: &'a Model) -> Self {
        let doc = model.document();
        let indices = |terms: &[LinearTerm]| {
            terms
                .iter()
                .map(|t| {
                    let direct = t.variable_id as usize;
                    if doc
                        .variables
                        .get(direct)
                        .is_some_and(|v| v.id == t.variable_id)
                    {
                        direct
                    } else {
                        doc.variables
                            .binary_search_by_key(&t.variable_id, |v| v.id)
                            .expect("validated original variable")
                    }
                })
                .collect()
        };
        let objective_indices = indices(&doc.objective.terms);
        let row_indices = doc.constraints.iter().map(|r| indices(&r.terms)).collect();
        Self {
            model,
            objective_indices,
            row_indices,
        }
    }

    /// Evaluate an original candidate using explicit tolerances and checked f64 arithmetic.
    pub fn evaluate(
        &self,
        primal: &[f64],
        tolerances: Tolerances,
    ) -> Result<ValidationReport, ValidationError> {
        let _component_scope = optimizer_core::lp_cost::scope("candidate_feasibility_objective");
        let tolerances = tolerances.validate()?;
        let document = self.model.document();
        if primal.len() != document.variables.len() || primal.iter().any(|v| !v.is_finite()) {
            return Err(ValidationError::new(
                ErrorKind::Candidate,
                "invalid canonical primal",
            ));
        }
        // The endpoint has already been identity/length/finite checked. Match
        // Candidate::canonical's observable signed-zero normalization exactly.
        let values: Vec<f64> = primal.iter().map(|v| zero(*v)).collect();
        let mut variables = Vec::with_capacity(document.variables.len());
        let mut feasible = true;
        for (variable, assignment) in document.variables.iter().zip(&values) {
            let context = format!("variable {}", variable.id);
            let value = *assignment;
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
        let (objective, _) = expression(
            &document.objective.terms,
            &self.objective_indices,
            &values,
            false,
            "objective",
        )?;
        let objective = checked(
            objective + document.objective.offset,
            "objective offset addition",
        )?;
        let row = |i: usize| -> Result<ConstraintCheck, ValidationError> {
            let constraint = &document.constraints[i];
            let indices = &self.row_indices[i];
            let context = format!("constraint {}", constraint.id);
            let (activity, magnitude) =
                expression(&constraint.terms, indices, &values, true, &context)?;
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
            Ok(ConstraintCheck {
                constraint_id: constraint.id,
                activity,
                lower,
                upper,
            })
        };
        let n = document.constraints.len();
        let constraints = if self.row_indices.iter().map(Vec::len).sum::<usize>() >= 65536 {
            std::thread::scope(|scope| {
                let workers: Vec<_> = (0..4)
                    .map(|w| {
                        let row = &row;
                        scope.spawn(move || {
                            (n * w / 4..n * (w + 1) / 4)
                                .map(row)
                                .collect::<Result<Vec<_>, _>>()
                        })
                    })
                    .collect();
                let mut ordered = Vec::with_capacity(n);
                for worker in workers {
                    ordered.extend(worker.join().expect("feasibility worker panicked")?);
                }
                Ok::<_, ValidationError>(ordered)
            })?
        } else {
            (0..n).map(row).collect::<Result<Vec<_>, _>>()?
        };
        for c in &constraints {
            feasible &= satisfied(&c.lower) && satisfied(&c.upper);
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
    indices: &[usize],
    values: &[f64],
    track_magnitude: bool,
    context: &str,
) -> Result<(f64, f64), ValidationError> {
    let mut sum = 0.0;
    let mut magnitude = 0.0;
    for (term, &index) in terms.iter().zip(indices) {
        // The per-term context is built inside each closure rather than once
        // before them. It is the same text either way; the difference is that on
        // the success path, which is every path that matters, it is never built.
        let id = term.variable_id;
        let product = checked_with(term.coefficient * values[index], || {
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

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;
    #[test]
    fn cached_indices_preserve_complete_reports_and_first_errors() {
        let finite = |value| json!({"kind":"finite","value":value});
        let mut cases = 0;
        for n in [1, 7, 33, 128, 256] {
            for variant in 0..8 {
                let doc = json!({"schema_version":1,"model_id":"indexed-feasibility",
                    "variables":(0..n).map(|j|json!({"id":j*7+13,"domain":if variant==7 {"integer"} else {"continuous"},
                        "lower":if variant==2 {json!({"kind":"negative_infinity"})}else{finite(-2.0)},
                        "upper":if variant==3 {json!({"kind":"positive_infinity"})}else{finite(2.0)}})).collect::<Vec<_>>(),
                    "objective":{"sense":if variant%2==0 {"minimize"}else{"maximize"},"offset":-3.25,
                        "terms":(0..n).map(|j|json!({"variable_id":j*7+13,"coefficient":(j%7) as f64-2.25})).collect::<Vec<_>>()},
                    "constraints":(0..n).map(|i|json!({"id":i*11+19,"lower":finite(-3.0),"upper":finite(3.0),
                        "terms":(0..n).filter(|j|variant!=4 || (i+j)%3==0).map(|j|json!({"variable_id":j*7+13,
                            "coefficient":if variant==5 {f64::MAX/2.0}else if variant==6 {f64::from_bits((i+j+1) as u64)}else{((i*13+j*7)%31) as f64/31.0-0.5}})).collect::<Vec<_>>()})).collect::<Vec<_>>()});
                let model = Model::from_json(&serde_json::to_vec(&doc).unwrap()).unwrap();
                let p = Prepared::new(&model);
                for sample in 0..24 {
                    let x: Vec<_> = (0..n)
                        .map(|j| match sample {
                            0 => -0.0,
                            1 => f64::from_bits((j + 1) as u64),
                            2 => f64::MAX,
                            3 => -f64::MAX,
                            4 => 2.0 + 1e-8,
                            5 => -2.0 - 1e-10,
                            _ => ((j * 13 + sample * 17) % 97) as f64 / 32.0 - 1.5,
                        })
                        .collect();
                    for tol in [0.0, 1e-9, 1e-7] {
                        let t = Tolerances {
                            absolute: tol,
                            relative: tol,
                            integrality: tol,
                        };
                        match (p.original(&x, t), p.evaluate(&x, t)) {
                            (Ok(a), Ok(b)) => assert_eq!(
                                serde_json::to_vec(&a).unwrap(),
                                serde_json::to_vec(&b).unwrap()
                            ),
                            (Err(a), Err(b)) => assert_eq!(a, b),
                            pair => panic!("n={n} variant={variant} sample={sample}: {pair:?}"),
                        }
                        cases += 1;
                    }
                }
            }
        }
        assert_eq!(cases, 2880);
    }
}
