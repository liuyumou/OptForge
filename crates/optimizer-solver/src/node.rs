//! Node representation and relaxation construction under SPEC-0003.
//!
//! A node is the original model plus tightened bounds on discrete variables.
//! Nodes store only their restrictions, never a copy of the model, so frontier
//! memory is bounded by the open-node limit times the branching depth.
//! Relaxations preserve every original identity, so an extracted candidate
//! evaluates directly against the original model without renumbering.

use optimizer_core::{Bound, Domain, ErrorKind, Model, ModelDocument, ValidationError, Variable};

use crate::search::Restriction;

/// SPEC-0001's discrete magnitude limit; a branch beyond it is unrepresentable.
pub(crate) const DISCRETE_MAGNITUDE_LIMIT: f64 = 9_007_199_254_740_992.0;

/// One subproblem: the original model restricted by branching bounds.
#[derive(Clone, Debug)]
pub(crate) struct Node {
    /// Deterministic identity, assigned in creation order.
    pub(crate) node_id: u64,
    /// Valid dual bound inherited from the parent relaxation, when one exists.
    pub(crate) parent_bound: Option<f64>,
    /// Branching restrictions in increasing original variable-ID order.
    pub(crate) restrictions: Vec<Restriction>,
}

impl Node {
    /// The root node imposes no restriction.
    pub(crate) fn root() -> Self {
        Self {
            node_id: 0,
            parent_bound: None,
            restrictions: Vec::new(),
        }
    }

    /// Restriction for one variable, when this node imposes any.
    fn restriction(&self, variable_id: u32) -> Option<&Restriction> {
        self.restrictions
            .binary_search_by_key(&variable_id, |r| r.variable_id)
            .ok()
            .map(|index| &self.restrictions[index])
    }

    /// A child with one additional bound merged into the restriction list.
    ///
    /// Merging keeps at most one restriction per variable, so repeated
    /// branching on the same variable cannot grow the list without limit.
    pub(crate) fn child(
        &self,
        node_id: u64,
        parent_bound: Option<f64>,
        variable_id: u32,
        lower: Option<f64>,
        upper: Option<f64>,
    ) -> Self {
        let mut restrictions = self.restrictions.clone();
        match restrictions.binary_search_by_key(&variable_id, |r| r.variable_id) {
            Ok(index) => {
                let existing = &mut restrictions[index];
                // A child only ever tightens: keep the stronger of the two.
                if let Some(lower) = lower {
                    existing.lower = Some(existing.lower.map_or(lower, |old| old.max(lower)));
                }
                if let Some(upper) = upper {
                    existing.upper = Some(existing.upper.map_or(upper, |old| old.min(upper)));
                }
            }
            Err(index) => restrictions.insert(
                index,
                Restriction {
                    variable_id,
                    lower,
                    upper,
                },
            ),
        }
        Self {
            node_id,
            parent_bound,
            restrictions,
        }
    }
}

/// Effective bounds of one variable at a node, as finite-or-infinite pairs.
///
/// A binary variable is in {0,1} regardless of its declared bounds, so its
/// relaxed domain is the intersection with [0,1].
fn effective_bounds(variable: &Variable, node: &Node) -> (Option<f64>, Option<f64>) {
    let mut lower = match variable.lower {
        Bound::Finite { value } => Some(value),
        Bound::NegativeInfinity => None,
        // Construction rejects this combination; treat it as maximally tight.
        Bound::PositiveInfinity => Some(f64::INFINITY),
    };
    let mut upper = match variable.upper {
        Bound::Finite { value } => Some(value),
        Bound::PositiveInfinity => None,
        Bound::NegativeInfinity => Some(f64::NEG_INFINITY),
    };
    if variable.domain == Domain::Binary {
        lower = Some(lower.map_or(0.0, |value| value.max(0.0)));
        upper = Some(upper.map_or(1.0, |value| value.min(1.0)));
    }
    if let Some(restriction) = node.restriction(variable.id) {
        if let Some(value) = restriction.lower {
            lower = Some(lower.map_or(value, |old| old.max(value)));
        }
        if let Some(value) = restriction.upper {
            upper = Some(upper.map_or(value, |old| old.min(value)));
        }
    }
    (lower, upper)
}

/// Whether a node's restrictions leave some variable with an empty domain.
pub(crate) fn is_empty(model: &Model, node: &Node) -> bool {
    model
        .document()
        .variables
        .iter()
        .any(|variable| match effective_bounds(variable, node) {
            (Some(lower), Some(upper)) => lower > upper,
            _ => false,
        })
}

/// Build the continuous relaxation of one node.
///
/// Original model ID, variable IDs, constraint IDs, coefficients, objective and
/// objective sense are preserved exactly; only variable domains and bounds
/// change. Returns `Ok(None)` when the node's domain is empty, which is node
/// infeasibility established without dispatching a relaxation.
pub(crate) fn relaxation(model: &Model, node: &Node) -> Result<Option<Model>, ValidationError> {
    if is_empty(model, node) {
        return Ok(None);
    }
    let document = model.document();
    let mut variables = Vec::with_capacity(document.variables.len());
    for variable in &document.variables {
        let (lower, upper) = effective_bounds(variable, node);
        variables.push(Variable {
            id: variable.id,
            // Dropping integrality is what makes this a relaxation.
            domain: Domain::Continuous,
            lower: lower.map_or(Bound::NegativeInfinity, |value| Bound::Finite { value }),
            upper: upper.map_or(Bound::PositiveInfinity, |value| Bound::Finite { value }),
        });
    }
    Model::new(ModelDocument {
        schema_version: document.schema_version,
        model_id: document.model_id.clone(),
        variables,
        constraints: document.constraints.clone(),
        objective: document.objective.clone(),
    })
    .map(Some)
}

/// Round a branching bound, rejecting one that cannot be represented exactly.
///
/// A bound outside the discrete magnitude limit is an explicit unsupported
/// failure rather than a silently widened or clamped branch.
pub(crate) fn branch_bound(value: f64, variable_id: u32) -> Result<f64, ValidationError> {
    if !value.is_finite() || value.abs() > DISCRETE_MAGNITUDE_LIMIT {
        return Err(ValidationError::new(
            ErrorKind::Unsupported,
            format!("variable {variable_id}: branching bound {value} is not representable"),
        ));
    }
    Ok(value)
}
