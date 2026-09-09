//! The guarded invocation boundary under SPEC-0004.
//!
//! This module is the host. It admits extensions, counts their budgets,
//! contains their panics, disables the ones that misbehave, and assembles the
//! summary a search record carries.
//!
//! What it deliberately cannot do is affect a search's conclusion. Every method
//! here returns either an owned proposal for the core to validate or nothing at
//! all; none returns an error the caller must propagate, so no extension can
//! deny a proof the engine would otherwise complete.
//!
//! Containment is panic containment. `catch_unwind` does not catch a process
//! abort, stack exhaustion or a memory fault, and the host requires the unwind
//! panic strategy. Process isolation is deferred with its own decision record.

use std::panic::{AssertUnwindSafe, catch_unwind};

use optimizer_core::{Candidate, Model};

use crate::declare::{
    Authority, Category, EXTENSION_SCHEMA_VERSION, ExtensionDeclaration, ProblemClass,
};
use crate::hook::{Advice, CandidateProducer, Extension, SearchAdviser};
use crate::record::{
    ExtensionFailure, ExtensionPolicy, ExtensionSummary, FailureKind, MAX_RETAINED_FAILURES,
};
use crate::view::SearchSnapshot;

/// One extension offered to a search, tagged by the role it is offered in.
///
/// The caller states the role, so the host never has to downcast a trait
/// object, and a declaration whose category disagrees with the role it was
/// registered in is refused rather than silently reinterpreted.
#[derive(Clone, Copy)]
pub enum Registration<'a> {
    /// Offered as a candidate producer.
    Producer(&'a dyn CandidateProducer),
    /// Offered as a search adviser.
    Adviser(&'a dyn SearchAdviser),
}

impl Registration<'_> {
    /// The category this role corresponds to.
    fn category(&self) -> Category {
        match self {
            Self::Producer(_) => Category::CandidateProducer,
            Self::Adviser(_) => Category::SearchAdviser,
        }
    }

    /// The declaration, or `None` when `declare` itself panicked.
    fn declare(&self) -> Option<ExtensionDeclaration> {
        let extension: &dyn Extension = match self {
            Self::Producer(producer) => *producer,
            Self::Adviser(adviser) => *adviser,
        };
        catch_unwind(AssertUnwindSafe(|| extension.declare())).ok()
    }
}

/// One registered extension: its role, its declaration, its budgets, its tally.
///
/// The host owns the tally, never the extension, so an extension cannot
/// understate its own consumption.
struct Entry<'a> {
    registration: Registration<'a>,
    declaration: ExtensionDeclaration,
    authority: Option<Authority>,
    invocation_budget: u64,
    proposal_budget: u64,
    registered: bool,
    disabled: bool,
    invocations: u64,
    proposals: u64,
    accepted: u64,
    rejected: u64,
    failures: Vec<ExtensionFailure>,
}

impl<'a> Entry<'a> {
    /// Admit an extension for one search, or refuse it with a typed failure.
    ///
    /// Refusal is not an error: a caller who names a well-formed but
    /// incompatible extension gets a recorded entry and a search that still
    /// runs. Every refusal path leaves `registered` false, and a non-registered
    /// entry is never invoked.
    fn admit(
        registration: Registration<'a>,
        declaration: ExtensionDeclaration,
        policy: &ExtensionPolicy,
        model: &Model,
    ) -> Self {
        let mut entry = Self {
            registration,
            authority: declaration.category.authority(),
            invocation_budget: policy
                .invocation_budget
                .min(declaration.limits.max_invocations),
            proposal_budget: policy.proposal_budget.min(declaration.limits.max_proposals),
            declaration,
            registered: false,
            disabled: true,
            invocations: 0,
            proposals: 0,
            accepted: 0,
            rejected: 0,
            failures: Vec::new(),
        };

        // Its own shape first: an invalid declaration says nothing reliable
        // about the fields the later checks would read.
        match entry.declaration.validate() {
            Ok(validated) => entry.declaration = validated,
            Err(error) => {
                entry.record(FailureKind::DeclarationInvalid, error.to_string());
                return entry;
            }
        }

        // Requirement 2: an exact match in both directions. A newer extension
        // may assume operations this host does not provide, and an older one
        // may assume semantics this host has changed; neither is inferable
        // from a successful call.
        if entry.declaration.host_contract_version != EXTENSION_SCHEMA_VERSION {
            entry.record(
                FailureKind::IncompatibleContract,
                format!(
                    "declared host contract version {} is not {EXTENSION_SCHEMA_VERSION}",
                    entry.declaration.host_contract_version
                ),
            );
            return entry;
        }

        if entry.authority.is_none() {
            entry.record(
                FailureKind::UnsupportedCategory,
                format!(
                    "category {} is not admitted in a proving search",
                    entry.declaration.category.as_str()
                ),
            );
            return entry;
        }

        // A declaration that disagrees with the role it was registered in is
        // refused, not reinterpreted: the caller and the extension disagree
        // about what it is, and guessing would grant unintended authority.
        if entry.declaration.category != registration.category() {
            entry.record(
                FailureKind::UnsupportedCategory,
                format!(
                    "declared {} but was registered as {}",
                    entry.declaration.category.as_str(),
                    registration.category().as_str()
                ),
            );
            return entry;
        }

        if !entry.declaration.supports(model) {
            entry.record(
                FailureKind::UnsupportedProblemClass,
                format!(
                    "declaration does not claim {}",
                    match ProblemClass::of(model) {
                        ProblemClass::Continuous => "continuous",
                        ProblemClass::Discrete => "discrete",
                    }
                ),
            );
            return entry;
        }

        entry.registered = true;
        entry.disabled = false;
        entry
    }

    /// Record a failure, capping retained messages but never the counters.
    fn record(&mut self, kind: FailureKind, message: impl Into<String>) {
        if kind.disables() {
            self.disabled = true;
        } else {
            self.rejected += 1;
        }
        let failure = ExtensionFailure::new(kind, message);
        // Requirement 17: keep the first few *distinct* failures. An extension
        // rejecting once per node must not grow this vector with the search.
        if self.failures.len() < MAX_RETAINED_FAILURES && !self.failures.contains(&failure) {
            self.failures.push(failure);
        }
    }

    /// Whether this extension may be invoked once more right now.
    ///
    /// Budget exhaustion is checked before dispatch and disables on the spot,
    /// so a budget can be reached but never exceeded.
    fn may_invoke(&mut self) -> bool {
        if !self.registered || self.disabled {
            return false;
        }
        if self.invocations >= self.invocation_budget {
            self.record(
                FailureKind::BudgetExhausted,
                format!("invocation budget {} reached", self.invocation_budget),
            );
            return false;
        }
        true
    }

    fn is_active(&self) -> bool {
        self.registered && !self.disabled
    }

    /// The immutable summary of what this extension did.
    fn summary(&self) -> ExtensionSummary {
        ExtensionSummary {
            schema_version: EXTENSION_SCHEMA_VERSION,
            extension_id: self.declaration.extension_id.clone(),
            version: self.declaration.version.clone(),
            category: self.declaration.category,
            authority: self.authority,
            deterministic: self.declaration.deterministic,
            registered: self.registered,
            invocations: self.invocations,
            proposals: self.proposals,
            accepted: self.accepted,
            rejected: self.rejected,
            disabled: self.disabled,
            failures: self.failures.clone(),
        }
    }
}

/// Every extension registered for one search, in a deterministic order.
///
/// Order is by extension identity, so requirement 18's fixed invocation order
/// does not depend on the order a caller happened to build its policy in.
pub struct ExtensionHost<'a> {
    entries: Vec<Entry<'a>>,
}

impl<'a> ExtensionHost<'a> {
    /// A host that consults nothing.
    ///
    /// A search over this host must produce the record the extension-free entry
    /// point produces; that equivalence is requirement 22.
    pub fn empty() -> Self {
        Self {
            entries: Vec::new(),
        }
    }

    /// Register the caller's permitted extensions against one model.
    ///
    /// An extension absent from `policies` is not consulted and is not
    /// recorded: the caller never permitted it. A policy entry with no matching
    /// registration is likewise not an error; a caller may configure a policy
    /// wider than the registry it happens to supply.
    pub fn register(
        registry: &[Registration<'a>],
        policies: &[ExtensionPolicy],
        model: &Model,
    ) -> Self {
        let mut entries: Vec<Entry<'a>> = Vec::new();
        for registration in registry {
            // A panic inside `declare` must not escape registration, and an
            // extension that cannot state what it is cannot be admitted.
            let Some(declaration) = registration.declare() else {
                continue;
            };
            let Some(policy) = policies
                .iter()
                .find(|policy| policy.extension_id == declaration.extension_id)
            else {
                continue;
            };
            entries.push(Entry::admit(*registration, declaration, policy, model));
        }
        entries.sort_by(|left, right| {
            left.declaration
                .extension_id
                .cmp(&right.declaration.extension_id)
        });
        Self { entries }
    }

    /// Whether any registered extension still participates.
    pub fn is_empty(&self) -> bool {
        !self.entries.iter().any(Entry::is_active)
    }

    /// Whether every admitted extension declared itself deterministic.
    ///
    /// The executive records this so a reader can see whether requirement 18's
    /// replay equality is claimed for a given search.
    pub fn is_deterministic(&self) -> bool {
        self.entries
            .iter()
            .filter(|entry| entry.registered)
            .all(|entry| entry.declaration.deterministic)
    }

    /// Summaries for every extension the caller permitted, in identity order.
    pub fn summaries(&self) -> Vec<ExtensionSummary> {
        self.entries.iter().map(Entry::summary).collect()
    }

    /// Indices of active entries of one category, in identity order.
    fn active(&self, category: Category) -> Vec<usize> {
        self.entries
            .iter()
            .enumerate()
            .filter(|(_, entry)| entry.is_active() && entry.declaration.category == category)
            .map(|(index, _)| index)
            .collect()
    }

    /// Collect candidate proposals from every active producer.
    ///
    /// Each pair names the proposing entry so the caller can attribute an
    /// acceptance or a rejection. A panicking producer is contained, disabled
    /// and recorded, and this call still returns whatever the other producers
    /// offered.
    pub fn collect_proposals(&mut self, snapshot: &SearchSnapshot<'_>) -> Vec<(usize, Candidate)> {
        let mut collected = Vec::new();
        for index in self.active(Category::CandidateProducer) {
            if !self.entries[index].may_invoke() {
                continue;
            }
            let Registration::Producer(producer) = self.entries[index].registration else {
                // Unreachable: admission refuses a role/category disagreement.
                continue;
            };
            self.entries[index].invocations += 1;

            match catch_unwind(AssertUnwindSafe(|| producer.propose(snapshot))) {
                Ok(candidates) => {
                    for candidate in candidates {
                        let entry = &mut self.entries[index];
                        if entry.proposals >= entry.proposal_budget {
                            entry.record(
                                FailureKind::BudgetExhausted,
                                format!("proposal budget {} reached", entry.proposal_budget),
                            );
                            break;
                        }
                        entry.proposals += 1;
                        collected.push((index, candidate));
                    }
                }
                Err(_) => self.entries[index]
                    .record(FailureKind::Panicked, "propose panicked and was contained"),
            }
        }
        collected
    }

    /// Ask every active adviser for one action; the first opinion wins.
    ///
    /// Taking the first non-abstention in identity order keeps the decision
    /// total and reproducible. Combining several advisers' opinions would need
    /// a conflict rule this contract deliberately does not define.
    pub fn request_advice(&mut self, snapshot: &SearchSnapshot<'_>) -> Option<(usize, Advice)> {
        for index in self.active(Category::SearchAdviser) {
            if !self.entries[index].may_invoke() {
                continue;
            }
            let Registration::Adviser(adviser) = self.entries[index].registration else {
                // Unreachable: admission refuses a role/category disagreement.
                continue;
            };
            self.entries[index].invocations += 1;

            match catch_unwind(AssertUnwindSafe(|| adviser.advise(snapshot))) {
                Ok(Advice::Abstain) => {}
                Ok(advice) => {
                    self.entries[index].proposals += 1;
                    return Some((index, advice));
                }
                Err(_) => self.entries[index]
                    .record(FailureKind::Panicked, "advise panicked and was contained"),
            }
        }
        None
    }

    /// Record that the core accepted one proposal or action.
    pub fn accept(&mut self, index: usize) {
        if let Some(entry) = self.entries.get_mut(index) {
            entry.accepted += 1;
        }
    }

    /// Record that the core refused one proposal or action.
    ///
    /// This never disables and never affects the search's conclusion:
    /// requirement 13 makes the outcome independent of extension behavior.
    pub fn reject(&mut self, index: usize, kind: FailureKind, message: impl Into<String>) {
        debug_assert!(
            !kind.disables(),
            "a rejection must not use a disabling failure kind"
        );
        if let Some(entry) = self.entries.get_mut(index) {
            entry.record(kind, message);
        }
    }
}
