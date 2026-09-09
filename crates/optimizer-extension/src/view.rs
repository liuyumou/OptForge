//! Read-only snapshots handed to an extension under SPEC-0004.
//!
//! An extension observes owned values and returns owned values. Nothing here
//! borrows executive state, so an extension cannot mutate the node store, the
//! incumbent, the budgets or the counters, and a panic inside an extension
//! cannot leave engine state partially modified.
//!
//! The frontier summary deliberately omits per-node restriction lists.
//! SPEC-0003 bounds search memory by the open-node limit times the per-node
//! restrictions; copying every restriction of every open node on every
//! iteration would exceed that bound.

use serde::Serialize;

use optimizer_core::{Model, ObjectiveSense, Tolerances};

/// One open node, described by identity and priority rather than by content.
#[derive(Clone, Copy, Debug, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct OpenNodeSummary {
    /// Deterministic node identity, assigned in creation order.
    pub node_id: u64,
    /// Valid dual bound inherited from the parent relaxation, when one exists.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub parent_bound: Option<f64>,
    /// Number of branching restrictions on the path to this node.
    pub depth: u32,
}

/// One discrete variable whose relaxation value is not integral.
///
/// The executive computes this set with the same integrality tolerance that
/// governs incumbent acceptance, and advice is validated against this very set,
/// so an adviser cannot name a variable the executive would not have branched
/// on.
#[derive(Clone, Copy, Debug, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct FractionalVariable {
    /// Original variable identity.
    pub variable_id: u32,
    /// Relaxation value of that variable.
    pub value: f64,
    /// Distance to the nearest permitted domain value.
    pub distance: f64,
}

/// Everything an extension is allowed to see about a running search.
#[derive(Clone, Copy, Debug)]
pub struct SearchSnapshot<'a> {
    /// The original model. Immutable by construction.
    pub model: &'a Model,
    /// Objective sense of the original model.
    pub sense: ObjectiveSense,
    /// Seed recorded for this search.
    pub seed: u64,
    /// Validation policy in force for this search.
    pub tolerances: Tolerances,
    /// Recomputed objective of the current incumbent, when one exists.
    pub incumbent_objective: Option<f64>,
    /// Best valid dual bound proven so far, when one exists.
    pub dual_bound: Option<f64>,
    /// Nodes whose relaxation has been dispatched.
    pub nodes_explored: u64,
    /// The open frontier, in the executive's own order.
    pub open_nodes: &'a [OpenNodeSummary],
    /// Fractional variables at the current node, empty outside a branching decision.
    pub fractional: &'a [FractionalVariable],
}
