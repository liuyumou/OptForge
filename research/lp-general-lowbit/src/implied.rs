//! Original-row implications for missing finite variable bounds.
//! Every operation rounds outward; unresolved directions remain infinite.
//! These are certificate aids, not guesses or changes to the numerical engine.
use crate::Result;
use optimizer_core::{Bound, Model};
use optimizer_lp::LinearProgram;
use serde::Serialize;

#[derive(Clone, Debug, Serialize)]
pub struct Step {
    pub row_id: u32,
    pub variable_id: u32,
    pub side: &'static str,
    pub row_side: &'static str,
    pub value: f64,
}

fn finite(bound: Bound) -> Option<f64> {
    match bound {
        Bound::Finite { value } => Some(value),
        _ => None,
    }
}
fn round(value: f64, upper: bool) -> Option<f64> {
    let v = if upper {
        value.next_up()
    } else {
        value.next_down()
    };
    v.is_finite().then_some(v)
}
fn product(a: f64, b: f64, upper: bool) -> Option<f64> {
    if a == 0. || b == 0. {
        Some(0.)
    } else {
        round(a * b, upper)
    }
}

/// At most two missing endpoints per variable can be filled, in 16 sparse
/// passes. Bounds and row identities remain in the original model's units.
pub fn derive(model: &Model) -> Result<(Option<Model>, Vec<Step>)> {
    if model
        .document()
        .variables
        .iter()
        .all(|v| finite(v.lower).is_some() && finite(v.upper).is_some())
    {
        return Ok((None, Vec::new()));
    }
    let mut doc = model.document().clone();
    let ids: Vec<_> = doc.variables.iter().map(|v| v.id).collect();
    let mut proof = Vec::new();
    for _ in 0..16 {
        let count = proof.len();
        for row in &doc.constraints {
            let indices: Vec<_> = row
                .terms
                .iter()
                .map(|t| {
                    let direct = t.variable_id as usize;
                    if ids.get(direct) == Some(&t.variable_id) {
                        direct
                    } else {
                        ids.binary_search(&t.variable_id).expect("validated ID")
                    }
                })
                .collect();
            // Each product has both endpoints so subtracting its own term from
            // an outward row sum also encloses the remaining contributions.
            let products: Vec<_> = row
                .terms
                .iter()
                .zip(&indices)
                .map(|(t, &j)| {
                    let v = &doc.variables[j];
                    [false, true].map(|upper| {
                        let b = if (t.coefficient > 0.) == upper {
                            v.upper
                        } else {
                            v.lower
                        };
                        if t.coefficient == 0. {
                            Some([0., 0.])
                        } else {
                            finite(b).and_then(|b| {
                                Some([
                                    product(t.coefficient, b, false)?,
                                    product(t.coefficient, b, true)?,
                                ])
                            })
                        }
                    })
                })
                .collect();
            let mut sums = [Some(0.), Some(0.)];
            let mut missing = [0usize; 2];
            for p in &products {
                for k in 0..2 {
                    if let Some(v) = p[k] {
                        sums[k] = sums[k].and_then(|s| round(s + v[k], k == 1));
                    } else {
                        missing[k] += 1;
                    }
                }
            }
            let mut proposed = Vec::new();
            for (j, (term, &column)) in row.terms.iter().zip(&indices).enumerate() {
                let a = term.coefficient;
                if a == 0. {
                    continue;
                }
                for (k, rhs) in [row.upper, row.lower].into_iter().enumerate() {
                    let row_upper = k == 0;
                    let upper = row_upper == (a > 0.);
                    let v = &doc.variables[column];
                    if finite(if upper { v.upper } else { v.lower }).is_some()
                        || missing[k] != usize::from(products[j][k].is_none())
                    {
                        continue;
                    }
                    let value = (|| {
                        let rhs = finite(rhs)?;
                        let total = sums[k]?;
                        let others = if let Some(own) = products[j][k] {
                            round(total - own[1 - k], k == 1)?
                        } else {
                            total
                        };
                        let numerator = round(rhs - others, row_upper)?;
                        round(numerator / a, upper)
                    })();
                    if let Some(value) = value {
                        // A contradictory implication is not an infeasibility
                        // certificate here. Leave it unresolved for this path.
                        let compatible = if upper {
                            finite(v.lower).is_none_or(|b| value >= b)
                        } else {
                            finite(v.upper).is_none_or(|b| value <= b)
                        };
                        if compatible {
                            proposed.push((column, upper, row_upper, value));
                        }
                    }
                }
            }
            for (column, upper, row_upper, value) in proposed {
                let v = &mut doc.variables[column];
                let bound = if upper { &mut v.upper } else { &mut v.lower };
                if finite(*bound).is_none() {
                    *bound = Bound::Finite { value };
                    proof.push(Step {
                        row_id: row.id,
                        variable_id: v.id,
                        side: if upper { "upper" } else { "lower" },
                        row_side: if row_upper { "upper" } else { "lower" },
                        value,
                    });
                }
            }
        }
        if proof.len() == count {
            break;
        }
    }
    if proof.is_empty() {
        Ok((None, proof))
    } else {
        Ok((Some(Model::new(doc)?), proof))
    }
}

pub struct Context {
    pub program: Option<LinearProgram>,
    pub proof: Vec<Step>,
}
impl Context {
    pub fn new(model: &Model, original: &LinearProgram) -> Result<Self> {
        let (tightened, proof) = derive(model)?;
        let program = tightened
            .as_ref()
            .map(|m| original.with_variable_bounds(m))
            .transpose()?;
        Ok(Self { program, proof })
    }
    pub fn program<'a>(&'a self, original: &'a LinearProgram) -> &'a LinearProgram {
        self.program.as_ref().unwrap_or(original)
    }
}
