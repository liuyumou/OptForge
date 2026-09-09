//! Executive-side extension integration under SPEC-0004.
//!
//! This module is where untrusted output meets owned state. It builds the
//! read-only snapshots an extension sees, and it recomputes the sets an
//! extension's advice must belong to.
//!
//! One rule here carries the contract: an advised branching variable must lie
//! in the executive's own fractional set. Branching on an integral value would
//! produce two children that do not tighten the node, so the search could
//! regenerate an identical child forever. That is SPEC-0003 requirement 12a's
//! hazard arriving from a second untrusted source.
//!
//! Nothing in this module can forfeit the proof claim, end the search, or
//! return an error.

use optimizer_core::{Candidate, Domain, Model, Tolerances};
use optimizer_extension::{FractionalVariable, OpenNodeSummary};

use crate::node::{self, Node};

/// Summarize the open frontier into a reused buffer.
///
/// Only identity, inherited bound and depth are copied. SPEC-0003 bounds search
/// memory by the open-node limit times the per-node restrictions, so copying
/// every restriction of every open node on every iteration would breach that
/// bound.
pub(crate) fn frontier(open: &[Node], out: &mut Vec<OpenNodeSummary>) {
    out.clear();
    out.reserve(open.len());
    for node in open {
        out.push(OpenNodeSummary {
            node_id: node.node_id,
            parent_bound: node.parent_bound,
            // A node's restriction list holds one entry per branched variable,
            // so its length is the branching depth.
            depth: u32::try_from(node.restrictions.len()).unwrap_or(u32::MAX),
        });
    }
}

/// Recompute every discrete variable that is branchable at this node.
///
/// This is the set an advised branching variable must belong to. A variable
/// whose value cannot be represented as a branch bound is excluded rather than
/// reported as an error: it cannot be branched on at all, so it must not be
/// advisable either, and the executive's own default decision keeps its
/// unchanged error behavior for that case.
pub(crate) fn branchable(
    model: &Model,
    candidate: &Candidate,
    tolerances: Tolerances,
    out: &mut Vec<FractionalVariable>,
) {
    out.clear();
    for variable in &model.document().variables {
        if variable.domain == Domain::Continuous {
            continue;
        }
        let Ok(index) = candidate
            .values
            .binary_search_by_key(&variable.id, |value| value.variable_id)
        else {
            continue;
        };
        let value = candidate.values[index].value;
        if !value.is_finite() || value.abs() > node::DISCRETE_MAGNITUDE_LIMIT {
            continue;
        }
        let distance = match variable.domain {
            Domain::Binary => value.abs().min((value - 1.0).abs()),
            _ => (value - value.round()).abs(),
        };
        // The same tolerance that governs incumbent acceptance governs whether
        // a variable is branchable, so the two decisions cannot disagree.
        if distance > tolerances.integrality {
            out.push(FractionalVariable {
                variable_id: variable.id,
                value,
                distance,
            });
        }
    }
}
