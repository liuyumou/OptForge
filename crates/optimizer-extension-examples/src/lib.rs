//! Independently authored extensions under SPEC-0004.
//!
//! This crate depends only on the published [`optimizer_extension`] and
//! [`optimizer_core`] APIs. It never depends on the executive outside its own
//! tests, so the fact that these extensions build and run at all is the
//! evidence that a third-party extension needs no engine-internal change.
//!
//! Two of these are useful. The rest are deliberately hostile: they return
//! infeasible candidates, lie about objectives, name nodes that do not exist,
//! advise branching on integral variables, panic, and burn their budgets. They
//! exist so the core's refusal of each can be asserted rather than assumed. A
//! search over any of them must still report the outcome it would have reported
//! with no extension at all.

use std::cell::Cell;

use optimizer_core::{Assignment, Candidate, Domain, SCHEMA_VERSION};
use optimizer_extension::{
    Advice, CandidateProducer, Category, DeclaredLimits, EXTENSION_SCHEMA_VERSION, Extension,
    ExtensionDeclaration, ProblemClass, SearchAdviser, SearchSnapshot,
};

/// Build a declaration with generous counted budgets.
fn declaration(id: &str, category: Category) -> ExtensionDeclaration {
    ExtensionDeclaration {
        schema_version: EXTENSION_SCHEMA_VERSION,
        extension_id: id.to_string(),
        version: "0.1.0".to_string(),
        host_contract_version: EXTENSION_SCHEMA_VERSION,
        category,
        problem_classes: vec![ProblemClass::Continuous, ProblemClass::Discrete],
        deterministic: true,
        limits: DeclaredLimits {
            max_invocations: 100_000,
            max_proposals: 100_000,
        },
    }
}

/// Rounds each discrete variable of the incumbent-free model to its lower bound.
///
/// A genuinely useful producer: for a model whose lower bounds are feasible this
/// supplies an incumbent before the first relaxation, which lets bound pruning
/// start immediately. When the rounded point is infeasible the core refuses it
/// and the search proceeds exactly as it would have.
#[derive(Debug, Default)]
pub struct LowerBoundRounder;

impl Extension for LowerBoundRounder {
    fn declare(&self) -> ExtensionDeclaration {
        declaration("example.lower-bound-rounder", Category::CandidateProducer)
    }
}

impl CandidateProducer for LowerBoundRounder {
    fn propose(&self, snapshot: &SearchSnapshot<'_>) -> Vec<Candidate> {
        let document = snapshot.model.document();
        let values = document
            .variables
            .iter()
            .map(|variable| {
                let lower = match variable.lower {
                    optimizer_core::Bound::Finite { value } => value,
                    _ => 0.0,
                };
                let value = match variable.domain {
                    Domain::Continuous => lower,
                    Domain::Binary => lower.max(0.0).ceil().min(1.0),
                    Domain::Integer => lower.ceil(),
                };
                Assignment {
                    variable_id: variable.id,
                    value,
                }
            })
            .collect();
        vec![Candidate {
            schema_version: SCHEMA_VERSION,
            model_id: document.model_id.clone(),
            values,
        }]
    }
}

/// Branches on the variable furthest from a permitted domain value.
///
/// A conventional most-fractional rule, and a legitimate alternative to the
/// executive's lowest-identity default. It only ever names a variable the
/// executive itself supplied in the snapshot, so it is always accepted.
#[derive(Debug, Default)]
pub struct MostFractional;

impl Extension for MostFractional {
    fn declare(&self) -> ExtensionDeclaration {
        declaration("example.most-fractional", Category::SearchAdviser)
    }
}

impl SearchAdviser for MostFractional {
    fn advise(&self, snapshot: &SearchSnapshot<'_>) -> Advice {
        snapshot
            .fractional
            .iter()
            // Ties break by the lower identity, so the choice is total and the
            // search stays replayable.
            .max_by(|left, right| {
                left.distance
                    .partial_cmp(&right.distance)
                    .unwrap_or(std::cmp::Ordering::Equal)
                    .then_with(|| right.variable_id.cmp(&left.variable_id))
            })
            .map_or(Advice::Abstain, |variable| {
                Advice::BranchVariable(variable.variable_id)
            })
    }
}

/// How a hostile producer misbehaves.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum BadProposal {
    /// Every variable set far outside its bounds.
    OutOfBounds,
    /// A discrete variable given a fractional value.
    Fractional,
    /// A candidate stamped with a different model identity.
    WrongModel,
    /// A candidate missing one variable.
    Incomplete,
    /// A candidate containing a nonfinite value.
    Nonfinite,
    /// A flood of candidates, to exhaust a proposal budget.
    Flood,
    /// A panic instead of a proposal.
    Panic,
}

/// A producer that returns output the core must refuse.
///
/// Each variant targets one refusal path. None of them may become an incumbent,
/// change an outcome, or turn into an error out of the search entry point.
#[derive(Debug)]
pub struct HostileProducer {
    kind: BadProposal,
    /// Invocations observed, so a test can assert the extension was disabled.
    calls: Cell<u64>,
}

impl HostileProducer {
    /// A hostile producer of one kind.
    pub fn new(kind: BadProposal) -> Self {
        Self {
            kind,
            calls: Cell::new(0),
        }
    }

    /// Invocations this producer observed.
    pub fn calls(&self) -> u64 {
        self.calls.get()
    }

    /// The identifier this producer declares, for building a policy.
    pub fn declare_id(&self) -> &'static str {
        match self.kind {
            BadProposal::OutOfBounds => "hostile.out-of-bounds",
            BadProposal::Fractional => "hostile.fractional",
            BadProposal::WrongModel => "hostile.wrong-model",
            BadProposal::Incomplete => "hostile.incomplete",
            BadProposal::Nonfinite => "hostile.nonfinite",
            BadProposal::Flood => "hostile.flood",
            BadProposal::Panic => "hostile.panic",
        }
    }
}

impl Extension for HostileProducer {
    fn declare(&self) -> ExtensionDeclaration {
        let mut declaration = declaration(self.declare_id(), Category::CandidateProducer);
        if self.kind == BadProposal::Flood {
            // Declare a small proposal budget so exhaustion is reached quickly
            // and deterministically rather than after a hundred thousand
            // allocations.
            declaration.limits.max_proposals = 4;
        }
        declaration
    }
}

impl CandidateProducer for HostileProducer {
    fn propose(&self, snapshot: &SearchSnapshot<'_>) -> Vec<Candidate> {
        self.calls.set(self.calls.get() + 1);
        let document = snapshot.model.document();
        let assignment = |value: f64| -> Vec<Assignment> {
            document
                .variables
                .iter()
                .map(|variable| Assignment {
                    variable_id: variable.id,
                    value,
                })
                .collect()
        };
        let candidate = |model_id: String, values: Vec<Assignment>| Candidate {
            schema_version: SCHEMA_VERSION,
            model_id,
            values,
        };

        match self.kind {
            // A value far outside every bound: validation reports infeasible.
            BadProposal::OutOfBounds => {
                vec![candidate(document.model_id.clone(), assignment(1.0e9))]
            }
            // Integral domains reject this, so it can never be an incumbent
            // even though its objective may look attractive.
            BadProposal::Fractional => {
                vec![candidate(document.model_id.clone(), assignment(0.5))]
            }
            BadProposal::WrongModel => vec![candidate(
                format!("{}-impostor", document.model_id),
                assignment(0.0),
            )],
            BadProposal::Incomplete => {
                let mut values = assignment(0.0);
                values.pop();
                vec![candidate(document.model_id.clone(), values)]
            }
            BadProposal::Nonfinite => {
                vec![candidate(
                    document.model_id.clone(),
                    assignment(f64::INFINITY),
                )]
            }
            BadProposal::Flood => (0..64)
                .map(|_| candidate(document.model_id.clone(), assignment(1.0e9)))
                .collect(),
            BadProposal::Panic => panic!("deliberate producer panic for SPEC-0004 requirement 14"),
        }
    }
}

/// How a hostile adviser misbehaves.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum BadAdvice {
    /// A node identity far beyond any the search created.
    NonexistentNode,
    /// The lowest variable identity, whether or not it is branchable.
    ///
    /// At a node-selection hook this is the wrong kind of advice entirely; at a
    /// branching hook it names a variable that may well be integral. Either way
    /// it must be refused, and refusing it is what keeps the search finite.
    IntegralVariable,
    /// A variable identity no model in these tests contains.
    UnknownVariable,
    /// A panic instead of advice.
    Panic,
}

/// An adviser that proposes actions the executive must refuse.
#[derive(Debug)]
pub struct HostileAdviser {
    kind: BadAdvice,
    calls: Cell<u64>,
}

impl HostileAdviser {
    /// A hostile adviser of one kind.
    pub fn new(kind: BadAdvice) -> Self {
        Self {
            kind,
            calls: Cell::new(0),
        }
    }

    /// Invocations this adviser observed.
    pub fn calls(&self) -> u64 {
        self.calls.get()
    }

    /// The identifier this adviser declares, for building a policy.
    pub fn declare_id(&self) -> &'static str {
        match self.kind {
            BadAdvice::NonexistentNode => "hostile.nonexistent-node",
            BadAdvice::IntegralVariable => "hostile.integral-variable",
            BadAdvice::UnknownVariable => "hostile.unknown-variable",
            BadAdvice::Panic => "hostile.panicking-adviser",
        }
    }
}

impl Extension for HostileAdviser {
    fn declare(&self) -> ExtensionDeclaration {
        declaration(self.declare_id(), Category::SearchAdviser)
    }
}

impl SearchAdviser for HostileAdviser {
    fn advise(&self, snapshot: &SearchSnapshot<'_>) -> Advice {
        self.calls.set(self.calls.get() + 1);
        match self.kind {
            BadAdvice::NonexistentNode => Advice::SelectNode(u64::MAX),
            BadAdvice::IntegralVariable => snapshot
                .model
                .document()
                .variables
                .first()
                .map_or(Advice::Abstain, |variable| {
                    Advice::BranchVariable(variable.id)
                }),
            BadAdvice::UnknownVariable => Advice::BranchVariable(u32::MAX),
            BadAdvice::Panic => panic!("deliberate adviser panic for SPEC-0004 requirement 14"),
        }
    }
}

/// A producer whose declaration cannot be admitted.
///
/// Registration must refuse each of these without ever calling `propose`.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum BadDeclaration {
    /// A host contract version above this host's.
    NewerContract,
    /// A host contract version below this host's.
    OlderContract,
    /// The transformation category, which has no validity contract yet.
    Transformation,
    /// An empty extension identifier.
    EmptyIdentity,
    /// A zero budget, which cannot be honored.
    ZeroBudget,
    /// Support claimed only for continuous models.
    ContinuousOnly,
}

/// An extension that must never be invoked.
#[derive(Debug)]
pub struct Unadmittable {
    kind: BadDeclaration,
    calls: Cell<u64>,
}

impl Unadmittable {
    /// An unadmittable extension of one kind.
    pub fn new(kind: BadDeclaration) -> Self {
        Self {
            kind,
            calls: Cell::new(0),
        }
    }

    /// Invocations observed. A refused extension must leave this at zero.
    pub fn calls(&self) -> u64 {
        self.calls.get()
    }

    /// The identifier this extension declares, for building a policy.
    pub fn extension_id(&self) -> &'static str {
        match self.kind {
            BadDeclaration::NewerContract => "unadmittable.newer",
            BadDeclaration::OlderContract => "unadmittable.older",
            BadDeclaration::Transformation => "unadmittable.transformation",
            // A policy cannot name an empty identity, so this one is
            // deliberately unreachable through a policy lookup and is refused
            // by validation when named directly.
            BadDeclaration::EmptyIdentity => "",
            BadDeclaration::ZeroBudget => "unadmittable.zero-budget",
            BadDeclaration::ContinuousOnly => "unadmittable.continuous-only",
        }
    }
}

impl Extension for Unadmittable {
    fn declare(&self) -> ExtensionDeclaration {
        let mut declaration = declaration(self.extension_id(), Category::CandidateProducer);
        match self.kind {
            BadDeclaration::NewerContract => {
                declaration.host_contract_version = EXTENSION_SCHEMA_VERSION + 1;
            }
            BadDeclaration::OlderContract => {
                // Version zero is below every released contract.
                declaration.host_contract_version = 0;
            }
            BadDeclaration::Transformation => declaration.category = Category::Transformation,
            BadDeclaration::EmptyIdentity => {}
            BadDeclaration::ZeroBudget => declaration.limits.max_invocations = 0,
            BadDeclaration::ContinuousOnly => {
                declaration.problem_classes = vec![ProblemClass::Continuous];
            }
        }
        declaration
    }
}

impl CandidateProducer for Unadmittable {
    fn propose(&self, _snapshot: &SearchSnapshot<'_>) -> Vec<Candidate> {
        // Reaching this at all is a contract violation; the counter is what a
        // test asserts against.
        self.calls.set(self.calls.get() + 1);
        Vec::new()
    }
}

/// An adviser that declares itself nondeterministic without misbehaving.
///
/// Used to check that a record states when replay equality is not claimed.
#[derive(Debug, Default)]
pub struct NondeterministicAdviser;

impl Extension for NondeterministicAdviser {
    fn declare(&self) -> ExtensionDeclaration {
        let mut declaration = declaration("example.nondeterministic", Category::SearchAdviser);
        declaration.deterministic = false;
        declaration
    }
}

impl SearchAdviser for NondeterministicAdviser {
    fn advise(&self, _snapshot: &SearchSnapshot<'_>) -> Advice {
        Advice::Abstain
    }
}
