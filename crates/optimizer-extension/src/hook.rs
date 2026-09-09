//! Extension traits and the actions an extension may propose, under SPEC-0004.
//!
//! Every trait here is object-safe, so the executive holds registered
//! extensions the way it already holds `&dyn Backend`. Each method takes
//! `&self`: an extension needing interior state uses a cell, exactly as the
//! test backends do.
//!
//! No method can report an error, a status, an objective or a proof. An
//! extension that wants to say nothing abstains; an extension that produces
//! garbage has it rejected by the core.

use optimizer_core::Candidate;

use crate::declare::ExtensionDeclaration;
use crate::view::SearchSnapshot;

/// A search action an adviser proposes.
///
/// Note what is absent: there is no variant for splitting a node a different
/// way. An adviser chooses *which* variable to branch on, never *how*, so
/// SPEC-0003 requirement 10's covering children are preserved by construction.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Advice {
    /// Offer no opinion; the executive uses its own default.
    Abstain,
    /// Explore this open node next.
    SelectNode(u64),
    /// Branch on this discrete variable.
    BranchVariable(u32),
}

/// Anything the extension runtime can register.
pub trait Extension {
    /// State identity, category, contract version, determinism and budgets.
    ///
    /// Called once at registration, before any other method. A declaration that
    /// fails validation, names a different host contract version, or names the
    /// transformation category means the extension is never invoked.
    fn declare(&self) -> ExtensionDeclaration;
}

/// Proposes complete candidate assignments.
///
/// A proposal is a suggestion. The core validates every candidate against the
/// original model before it can become an incumbent, and the recorded objective
/// is that recomputation, so a producer gains nothing by lying.
pub trait CandidateProducer: Extension {
    /// Propose zero or more candidates for the original model.
    ///
    /// Returning an empty vector is the normal way to decline. Candidates are
    /// offered to the core in the returned order; invalid ones are rejected and
    /// recorded without affecting the search's outcome.
    fn propose(&self, snapshot: &SearchSnapshot<'_>) -> Vec<Candidate>;
}

/// Proposes search actions such as node and branching-variable choices.
///
/// Every action is checked against the executive's real state before it takes
/// effect, and a rejected action falls back to the SPEC-0003 default.
pub trait SearchAdviser: Extension {
    /// Offer one action, or abstain.
    fn advise(&self, snapshot: &SearchSnapshot<'_>) -> Advice;
}
