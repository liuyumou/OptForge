//! C3 acceptance: adversarial extensions cannot change a search's conclusion.
//!
//! These tests live in the examples crate, which depends on the executive only
//! as a dev-dependency. That is the point: the extensions under test are built
//! from the published [`optimizer_extension`] and [`optimizer_core`] APIs
//! alone, so "an independently authored extension runs without engine-internal
//! changes" is established by the workspace build rather than asserted.
//!
//! The central assertion is negative. For every hostile extension, the search
//! must report the same outcome, the same proven optimum, the same forfeiture
//! state and the same prune counters as the extension-free run. Budgets are
//! left unlimited on purpose: a hostile adviser that spends a node budget on
//! unpromising nodes legitimately changes which outcome a *budgeted* search
//! reaches, and that is exploration quality rather than correctness.

use std::cell::RefCell;

use optimizer_core::{
    Assignment, Backend, Bound, CancellationToken, Candidate, Constraint, Domain, LinearTerm,
    Model, ModelDocument, Objective, ObjectiveSense, SCHEMA_VERSION, SOLVE_SCHEMA_VERSION,
    SolveOptions, SolveRecord, Termination, Tolerances, ValidationError, Variable, WarmStart,
};
use optimizer_extension::{EXTENSION_SCHEMA_VERSION, ExtensionPolicy, FailureKind, Registration};
use optimizer_extension_examples::{
    BadAdvice, BadDeclaration, BadProposal, HostileAdviser, HostileProducer, LowerBoundRounder,
    MostFractional, NondeterministicAdviser, Unadmittable,
};
use optimizer_solver::{
    SEARCH_SCHEMA_VERSION, SearchOptions, SearchOutcome, SearchRecord, search,
    search_with_extensions,
};

const EPSILON: f64 = 1e-9;

fn tolerances() -> Tolerances {
    Tolerances {
        absolute: 1e-7,
        relative: 1e-9,
        integrality: 1e-7,
    }
}

/// Unlimited budgets, so an outcome difference can only be a correctness bug.
fn options(policies: Vec<ExtensionPolicy>) -> SearchOptions {
    SearchOptions {
        schema_version: SEARCH_SCHEMA_VERSION,
        seed: 17,
        node_limit: None,
        time_limit_ms: None,
        open_node_limit: None,
        improvement_tolerance: 1e-9,
        // These contracts are about search behaviour, which SPEC-0010
        // requirement 26 requires a device not to change. Running them on the
        // CPU is what keeps them a statement about the executive.
        device: optimizer_core::Device::Cpu,
        relaxation: SolveOptions {
            schema_version: SOLVE_SCHEMA_VERSION,
            seed: 17,
            time_limit_ms: None,
            iteration_limit: None,
            node_limit: None,
            tolerances: tolerances(),
            threads: 1,
        },
        extensions: policies,
    }
}

fn policy(extension_id: &str) -> ExtensionPolicy {
    ExtensionPolicy {
        schema_version: EXTENSION_SCHEMA_VERSION,
        extension_id: extension_id.to_string(),
        invocation_budget: 100_000,
        proposal_budget: 100_000,
    }
}

// ---------------------------------------------------------------------------
// Model construction and an independent exact LP relaxation service.
//
// The backend is written for these tests by vertex enumeration. It shares no
// code with the executive, so agreement between them is real evidence.
// ---------------------------------------------------------------------------

type VariableSpec = (u32, Domain, f64, f64);
type ConstraintSpec<'a> = (u32, Option<f64>, Option<f64>, &'a [(u32, f64)]);

fn model(
    model_id: &str,
    variables: &[VariableSpec],
    constraints: &[ConstraintSpec<'_>],
    sense: ObjectiveSense,
    objective: &[(u32, f64)],
) -> Model {
    let terms = |pairs: &[(u32, f64)]| {
        pairs
            .iter()
            .map(|(variable_id, coefficient)| LinearTerm {
                variable_id: *variable_id,
                coefficient: *coefficient,
            })
            .collect::<Vec<_>>()
    };
    Model::new(ModelDocument {
        schema_version: SCHEMA_VERSION,
        model_id: model_id.to_string(),
        variables: variables
            .iter()
            .map(|(id, domain, lower, upper)| Variable {
                id: *id,
                domain: *domain,
                lower: Bound::Finite { value: *lower },
                upper: Bound::Finite { value: *upper },
            })
            .collect(),
        constraints: constraints
            .iter()
            .map(|(id, lower, upper, pairs)| Constraint {
                id: *id,
                lower: lower.map_or(Bound::NegativeInfinity, |value| Bound::Finite { value }),
                upper: upper.map_or(Bound::PositiveInfinity, |value| Bound::Finite { value }),
                terms: terms(pairs),
            })
            .collect(),
        objective: Objective {
            sense,
            offset: 0.0,
            terms: terms(objective),
        },
    })
    .expect("model")
}

/// One inequality `sum(coefficients * x) <= bound`.
struct HalfPlane {
    coefficients: Vec<f64>,
    bound: f64,
}

/// Every bound and row of a model, as half-planes over its variable order.
fn half_planes(model: &Model) -> Vec<HalfPlane> {
    let document = model.document();
    let width = document.variables.len();
    let mut planes = Vec::new();
    let mut unit = |index: usize, sign: f64, bound: f64| {
        let mut coefficients = vec![0.0; width];
        coefficients[index] = sign;
        planes.push(HalfPlane {
            coefficients,
            bound,
        });
    };
    for (index, variable) in document.variables.iter().enumerate() {
        if let Bound::Finite { value } = variable.upper {
            unit(index, 1.0, value);
        }
        if let Bound::Finite { value } = variable.lower {
            unit(index, -1.0, -value);
        }
    }
    for constraint in &document.constraints {
        let mut row = vec![0.0; width];
        for term in &constraint.terms {
            let position = document
                .variables
                .iter()
                .position(|variable| variable.id == term.variable_id)
                .expect("a constraint references a declared variable");
            row[position] += term.coefficient;
        }
        if let Bound::Finite { value } = constraint.upper {
            planes.push(HalfPlane {
                coefficients: row.clone(),
                bound: value,
            });
        }
        if let Bound::Finite { value } = constraint.lower {
            planes.push(HalfPlane {
                coefficients: row.iter().map(|entry| -entry).collect(),
                bound: -value,
            });
        }
    }
    planes
}

/// Solve a square system by Gaussian elimination with partial pivoting.
fn solve_square(mut matrix: Vec<Vec<f64>>, mut rhs: Vec<f64>) -> Option<Vec<f64>> {
    let size = rhs.len();
    for column in 0..size {
        let pivot = (column..size)
            .max_by(|left, right| {
                matrix[*left][column]
                    .abs()
                    .partial_cmp(&matrix[*right][column].abs())
                    .unwrap_or(std::cmp::Ordering::Equal)
            })
            .expect("a nonempty column");
        if matrix[pivot][column].abs() < 1e-12 {
            return None;
        }
        matrix.swap(column, pivot);
        rhs.swap(column, pivot);
        for row in column + 1..size {
            let factor = matrix[row][column] / matrix[column][column];
            // The pivot row is copied out so the elimination borrows one row
            // mutably without also borrowing the matrix immutably.
            let pivot_row: Vec<f64> = matrix[column][column..].to_vec();
            for (target, source) in matrix[row][column..].iter_mut().zip(&pivot_row) {
                *target -= factor * source;
            }
            rhs[row] -= factor * rhs[column];
        }
    }
    let mut solution = vec![0.0; size];
    for row in (0..size).rev() {
        let mut value = rhs[row];
        for column in row + 1..size {
            value -= matrix[row][column] * solution[column];
        }
        solution[row] = value / matrix[row][row];
    }
    Some(solution)
}

/// The exact LP optimum of a relaxation, by enumerating vertices.
fn lp_optimum(model: &Model) -> Option<Vec<f64>> {
    let document = model.document();
    let width = document.variables.len();
    let planes = half_planes(model);
    let feasible = |point: &[f64]| {
        planes.iter().all(|plane| {
            let activity: f64 = plane
                .coefficients
                .iter()
                .zip(point)
                .map(|(coefficient, value)| coefficient * value)
                .sum();
            activity <= plane.bound + 1e-7
        })
    };
    let objective = |point: &[f64]| -> f64 {
        document
            .objective
            .terms
            .iter()
            .map(|term| {
                let position = document
                    .variables
                    .iter()
                    .position(|variable| variable.id == term.variable_id)
                    .expect("declared");
                term.coefficient * point[position]
            })
            .sum()
    };

    let mut best: Option<Vec<f64>> = None;
    let mut consider = |point: Vec<f64>| {
        if !feasible(&point) {
            return;
        }
        let better = best.as_ref().is_none_or(|incumbent| {
            let (new, old) = (objective(&point), objective(incumbent));
            match document.objective.sense {
                ObjectiveSense::Minimize => new < old - EPSILON,
                ObjectiveSense::Maximize => new > old + EPSILON,
            }
        });
        if better {
            best = Some(point);
        }
    };

    // Every LP vertex is the intersection of `width` active constraints.
    let total = planes.len();
    let mut choice = (0..width).collect::<Vec<_>>();
    if width == 0 {
        return Some(Vec::new());
    }
    loop {
        let matrix: Vec<Vec<f64>> = choice
            .iter()
            .map(|index| planes[*index].coefficients.clone())
            .collect();
        let rhs: Vec<f64> = choice.iter().map(|index| planes[*index].bound).collect();
        if let Some(point) = solve_square(matrix, rhs) {
            consider(point);
        }
        // Odometer over increasing index combinations.
        let mut position = width;
        loop {
            if position == 0 {
                return best;
            }
            position -= 1;
            if choice[position] < total - (width - position) {
                choice[position] += 1;
                for later in position + 1..width {
                    choice[later] = choice[later - 1] + 1;
                }
                break;
            }
        }
    }
}

/// An exact relaxation service, independent of the executive.
#[derive(Default)]
struct ExactBackend {
    solves: RefCell<u32>,
}

impl Backend for ExactBackend {
    fn solve(
        &self,
        model: &Model,
        options: &SolveOptions,
        cancel: &CancellationToken,
        warm_start: Option<WarmStart<'_>>,
    ) -> Result<SolveRecord, ValidationError> {
        assert!(
            warm_start.is_none(),
            "SPEC-0003 requirement 23: no cross-node warm start"
        );
        *self.solves.borrow_mut() += 1;
        let document = model.document();
        let mut record = SolveRecord {
            schema_version: SOLVE_SCHEMA_VERSION,
            model_id: document.model_id.clone(),
            backend: "exact".to_string(),
            backend_version: "test".to_string(),
            termination: Termination::Infeasible,
            native_status: None,
            objective: None,
            best_bound: None,
            gap: None,
            candidate: None,
            validation: None,
            warnings: Vec::new(),
            elapsed_ms: 0,
            options: options.clone(),
        };
        if cancel.is_cancelled() {
            record.termination = Termination::Interrupted;
            return Ok(record);
        }
        if let Some(point) = lp_optimum(model) {
            let candidate = Candidate {
                schema_version: SCHEMA_VERSION,
                model_id: document.model_id.clone(),
                values: document
                    .variables
                    .iter()
                    .zip(&point)
                    .map(|(variable, value)| Assignment {
                        variable_id: variable.id,
                        value: *value,
                    })
                    .collect(),
            };
            let report = model.evaluate(&candidate, options.tolerances)?;
            record.termination = Termination::Optimal;
            record.objective = Some(report.objective);
            record.candidate = Some(candidate);
            record.validation = Some(report);
        }
        Ok(record)
    }
}

/// Exhaustively enumerate the discrete box; the independent oracle.
fn brute_force(model: &Model) -> Option<f64> {
    let document = model.document();
    let ranges: Vec<(f64, f64)> = document
        .variables
        .iter()
        .map(|variable| {
            let (Bound::Finite { value: lower }, Bound::Finite { value: upper }) =
                (variable.lower, variable.upper)
            else {
                panic!("the oracle requires finite bounds");
            };
            match variable.domain {
                Domain::Binary => (lower.max(0.0).ceil(), upper.min(1.0).floor()),
                _ => (lower.ceil(), upper.floor()),
            }
        })
        .collect();
    if ranges.iter().any(|(lower, upper)| lower > upper) {
        return None;
    }

    let mut best: Option<f64> = None;
    let mut assignment: Vec<f64> = ranges.iter().map(|(lower, _)| *lower).collect();
    loop {
        let candidate = Candidate {
            schema_version: SCHEMA_VERSION,
            model_id: document.model_id.clone(),
            values: document
                .variables
                .iter()
                .zip(&assignment)
                .map(|(variable, value)| Assignment {
                    variable_id: variable.id,
                    value: *value,
                })
                .collect(),
        };
        if let Ok(report) = model.evaluate(&candidate, tolerances())
            && report.feasible
        {
            let better = best.is_none_or(|objective| match document.objective.sense {
                ObjectiveSense::Minimize => report.objective < objective,
                ObjectiveSense::Maximize => report.objective > objective,
            });
            if better {
                best = Some(report.objective);
            }
        }
        let mut position = 0;
        loop {
            if position == assignment.len() {
                return best;
            }
            assignment[position] += 1.0;
            if assignment[position] <= ranges[position].1 + EPSILON {
                break;
            }
            assignment[position] = ranges[position].0;
            position += 1;
        }
    }
}

/// The fixed model grid every equivalence assertion runs over.
///
/// Fixed, not random: a failure reproduces exactly. Both senses, both discrete
/// domains, feasible and infeasible cases.
fn grid() -> Vec<Model> {
    let mut models = Vec::new();
    for (index, sense) in [ObjectiveSense::Minimize, ObjectiveSense::Maximize]
        .into_iter()
        .enumerate()
    {
        for (domain, upper) in [(Domain::Binary, 1.0), (Domain::Integer, 3.0)] {
            for capacity in [1.0, 2.0, 5.0] {
                for coefficient in [1.0, 2.0] {
                    models.push(model(
                        &format!("grid-{index}-{upper}-{capacity}-{coefficient}"),
                        &[
                            (0, domain, 0.0, upper),
                            (1, domain, 0.0, upper),
                            (2, domain, 0.0, upper),
                        ],
                        &[
                            (
                                0,
                                None,
                                Some(capacity),
                                &[(0, 1.0), (1, coefficient), (2, 1.0)],
                            ),
                            (1, Some(0.0), None, &[(0, 1.0), (2, -1.0)]),
                        ],
                        sense,
                        &[(0, 3.0), (1, 2.0), (2, coefficient)],
                    ));
                }
            }
        }
    }
    // A model whose discrete restrictions cannot be satisfied at all.
    models.push(model(
        "grid-infeasible",
        &[(0, Domain::Binary, 0.0, 1.0), (1, Domain::Binary, 0.0, 1.0)],
        &[(0, Some(3.0), None, &[(0, 1.0), (1, 1.0)])],
        ObjectiveSense::Minimize,
        &[(0, 1.0)],
    ));
    models
}

/// A model whose LP relaxation is genuinely fractional, so branching happens.
///
/// An adviser is only consulted where a real decision exists: a frontier with
/// more than one open node, or a node with a branchable variable. A model whose
/// relaxation is already integral is solved without branching, so registering
/// an adviser against one would assert nothing. The ratios here are deliberately
/// close enough that the LP optimum splits a variable.
fn branching_model(model_id: &str) -> Model {
    model(
        model_id,
        &[
            (0, Domain::Integer, 0.0, 6.0),
            (1, Domain::Integer, 0.0, 6.0),
            (2, Domain::Integer, 0.0, 6.0),
        ],
        &[(0, None, Some(7.0), &[(0, 2.0), (1, 3.0), (2, 3.0)])],
        ObjectiveSense::Maximize,
        &[(0, 3.0), (1, 4.0), (2, 2.0)],
    )
}

/// A record shorn of what may legitimately differ between two runs.
///
/// Only elapsed time and the extension summaries may differ; everything that
/// describes the mathematics must be identical.
fn conclusion(record: &SearchRecord) -> (SearchOutcome, Option<f64>, Option<f64>, bool, u64, u64) {
    (
        record.outcome,
        record.objective,
        record.dual_bound,
        record.forfeited,
        record.nodes_pruned_infeasible,
        record.nodes_pruned_bound,
    )
}

fn run_plain(model: &Model) -> SearchRecord {
    search(
        model,
        &options(Vec::new()),
        &ExactBackend::default(),
        &CancellationToken::new(),
    )
    .expect("a search must not fail")
}

fn run_with(
    model: &Model,
    registry: &[Registration<'_>],
    policies: Vec<ExtensionPolicy>,
) -> SearchRecord {
    search_with_extensions(
        model,
        &options(policies),
        registry,
        &ExactBackend::default(),
        &CancellationToken::new(),
    )
    .expect("an extension must never make a search fail")
}

// ---------------------------------------------------------------------------
// Requirement 22: an empty policy changes nothing at all.
// ---------------------------------------------------------------------------

/// The extension-free entry point and an empty registry agree exactly.
///
/// This is the cheapest proof that C3 did not perturb C2: every field except
/// measured time must match.
#[test]
fn an_empty_policy_reproduces_the_extension_free_record() {
    for instance in grid() {
        let plain = run_plain(&instance);
        let hosted = run_with(&instance, &[], Vec::new());

        assert!(
            hosted.extensions.is_empty(),
            "no extension participated, so the summary list is empty"
        );
        assert_eq!(
            SearchRecord {
                elapsed_ms: plain.elapsed_ms,
                ..hosted
            },
            plain,
            "{}: an empty policy must reproduce the extension-free record",
            instance.document().model_id
        );
    }
}

// ---------------------------------------------------------------------------
// Requirement 13: the conclusion is independent of extension behavior.
// ---------------------------------------------------------------------------

/// Every hostile extension leaves the proven optimum and the proof untouched.
///
/// The comparison is against both the extension-free run and an independent
/// brute-force enumeration, over a fixed grid, with unlimited budgets.
#[test]
fn hostile_extensions_cannot_change_the_conclusion() {
    let producers = [
        BadProposal::OutOfBounds,
        BadProposal::Fractional,
        BadProposal::WrongModel,
        BadProposal::Incomplete,
        BadProposal::Nonfinite,
        BadProposal::Flood,
        BadProposal::Panic,
    ];
    let advisers = [
        BadAdvice::NonexistentNode,
        BadAdvice::IntegralVariable,
        BadAdvice::UnknownVariable,
        BadAdvice::Panic,
    ];

    for instance in grid() {
        let model_id = instance.document().model_id.clone();
        let plain = run_plain(&instance);
        let expected = brute_force(&instance);

        // The oracle and the extension-free executive must agree first, or the
        // comparisons below would be against an unverified baseline.
        match plain.outcome {
            SearchOutcome::ProvenOptimal => {
                let found = plain.objective.expect("an optimum has an objective");
                let expected = expected.expect("enumeration found a feasible point");
                assert!(
                    (found - expected).abs() <= 1e-6,
                    "{model_id}: executive {found} vs enumeration {expected}"
                );
            }
            SearchOutcome::ProvenInfeasible => assert!(
                expected.is_none(),
                "{model_id}: enumeration found a point the executive proved absent"
            ),
            other => panic!("{model_id}: unlimited budgets must prove something, got {other:?}"),
        }

        for kind in producers {
            let hostile = HostileProducer::new(kind);
            let record = run_with(
                &instance,
                &[Registration::Producer(&hostile)],
                vec![policy(hostile.declare_id())],
            );
            assert_eq!(
                conclusion(&record),
                conclusion(&plain),
                "{model_id}: producer {kind:?} changed the conclusion"
            );
            assert!(
                record.candidate == plain.candidate,
                "{model_id}: producer {kind:?} changed the published incumbent"
            );
        }

        for kind in advisers {
            let hostile = HostileAdviser::new(kind);
            let record = run_with(
                &instance,
                &[Registration::Adviser(&hostile)],
                vec![policy(hostile.declare_id())],
            );
            assert_eq!(
                record.outcome, plain.outcome,
                "{model_id}: adviser {kind:?} changed the outcome"
            );
            assert!(
                !record.forfeited,
                "{model_id}: adviser {kind:?} must not forfeit the proof"
            );
            assert_eq!(
                record.objective, plain.objective,
                "{model_id}: adviser {kind:?} changed the proven optimum"
            );
        }
    }
}

// ---------------------------------------------------------------------------
// Requirements 5-8: proposals are validated by the core.
// ---------------------------------------------------------------------------

/// Each bad proposal is refused in its own right and never published.
#[test]
fn bad_proposals_are_refused_and_recorded() {
    let instance = model(
        "refusal",
        &[
            (0, Domain::Integer, 0.0, 3.0),
            (1, Domain::Integer, 0.0, 3.0),
        ],
        &[(0, None, Some(4.0), &[(0, 1.0), (1, 1.0)])],
        ObjectiveSense::Maximize,
        &[(0, 2.0), (1, 1.0)],
    );

    for kind in [
        BadProposal::OutOfBounds,
        BadProposal::Fractional,
        BadProposal::WrongModel,
        BadProposal::Incomplete,
        BadProposal::Nonfinite,
    ] {
        let hostile = HostileProducer::new(kind);
        let record = run_with(
            &instance,
            &[Registration::Producer(&hostile)],
            vec![policy(hostile.declare_id())],
        );

        let summary = record
            .extensions
            .first()
            .expect("a permitted extension is summarized");
        assert!(summary.registered, "{kind:?} was admitted");
        assert!(summary.proposals > 0, "{kind:?} did propose something");
        assert_eq!(summary.accepted, 0, "{kind:?} had nothing accepted");
        assert!(summary.rejected > 0, "{kind:?} was refused");
        assert!(
            summary
                .failures
                .iter()
                .any(|failure| failure.kind == FailureKind::InvalidCandidate),
            "{kind:?} must be recorded as an invalid candidate: {:?}",
            summary.failures
        );
        assert_eq!(
            record.outcome,
            SearchOutcome::ProvenOptimal,
            "{kind:?} must not prevent the proof"
        );
        assert!(!record.forfeited);
    }
}

/// A producer's claimed objective is never read; only the recomputation counts.
#[test]
fn a_recorded_objective_is_always_the_recomputed_one() {
    let instance = model(
        "recomputed",
        &[(0, Domain::Binary, 0.0, 1.0), (1, Domain::Binary, 0.0, 1.0)],
        &[(0, None, Some(1.0), &[(0, 1.0), (1, 1.0)])],
        ObjectiveSense::Maximize,
        &[(0, 5.0), (1, 3.0)],
    );

    // The out-of-bounds producer's candidate has an enormous objective. If any
    // path trusted a proposal's own numbers it would surface here.
    let hostile = HostileProducer::new(BadProposal::OutOfBounds);
    let record = run_with(
        &instance,
        &[Registration::Producer(&hostile)],
        vec![policy(hostile.declare_id())],
    );

    assert_eq!(record.outcome, SearchOutcome::ProvenOptimal);
    let validation = record
        .validation
        .as_ref()
        .expect("an incumbent carries its report");
    assert!(validation.feasible);
    assert_eq!(
        record.objective,
        Some(validation.objective),
        "the record's objective is the independent recomputation"
    );
    assert_eq!(
        record.objective,
        Some(5.0),
        "the true optimum, not the proposal's claim"
    );
}

/// A useful producer's candidate is accepted, and validated before publication.
#[test]
fn a_valid_proposal_is_accepted_after_validation() {
    // Every lower bound is zero and feasible, so the rounder's proposal is a
    // genuine feasible point and becomes the first incumbent.
    let instance = model(
        "accepted",
        &[
            (0, Domain::Integer, 0.0, 3.0),
            (1, Domain::Integer, 0.0, 3.0),
        ],
        &[(0, None, Some(4.0), &[(0, 1.0), (1, 1.0)])],
        ObjectiveSense::Minimize,
        &[(0, 1.0), (1, 1.0)],
    );

    let record = run_with(
        &instance,
        &[Registration::Producer(&LowerBoundRounder)],
        vec![policy("example.lower-bound-rounder")],
    );

    let summary = record.extensions.first().expect("summarized");
    assert!(summary.registered);
    assert!(
        summary.accepted > 0,
        "a feasible improving proposal is accepted: {summary:?}"
    );
    assert!(!summary.disabled);
    assert_eq!(record.outcome, SearchOutcome::ProvenOptimal);
    assert_eq!(record.objective, Some(0.0));
    assert_eq!(record.objective, brute_force(&instance));
}

// ---------------------------------------------------------------------------
// Requirements 9-12: advice is checked against real state.
// ---------------------------------------------------------------------------

/// Bad advice is refused, recorded, and falls back to the C2 default.
#[test]
fn bad_advice_is_refused_and_recorded() {
    let instance = branching_model("advice");
    let plain = run_plain(&instance);
    assert!(
        plain.nodes_explored > 1,
        "this model must actually branch, or an adviser is never consulted"
    );

    for kind in [
        BadAdvice::NonexistentNode,
        BadAdvice::UnknownVariable,
        BadAdvice::IntegralVariable,
    ] {
        let hostile = HostileAdviser::new(kind);
        let record = run_with(
            &instance,
            &[Registration::Adviser(&hostile)],
            vec![policy(hostile.declare_id())],
        );

        let summary = record.extensions.first().expect("summarized");
        assert!(summary.registered, "{kind:?} was admitted");
        assert!(
            summary
                .failures
                .iter()
                .any(|failure| failure.kind == FailureKind::InvalidAdvice),
            "{kind:?} must be recorded as invalid advice: {:?}",
            summary.failures
        );
        assert!(
            !summary.disabled,
            "{kind:?}: rejected advice is a normal event, not a disable"
        );
        assert_eq!(
            record.outcome, plain.outcome,
            "{kind:?}: the fallback is the unmodified C2 decision"
        );
        assert_eq!(record.objective, plain.objective);
    }
}

/// An adviser that always names an integral variable must terminate.
///
/// This is requirement 10's reason for existing. Honoring such advice would
/// produce two children identical to their parent, and the search would
/// regenerate them forever. The test passing at all is the assertion.
#[test]
fn advice_naming_an_integral_variable_terminates() {
    let instance = model(
        "termination",
        &[
            (0, Domain::Integer, 0.0, 6.0),
            (1, Domain::Integer, 0.0, 6.0),
        ],
        &[(0, None, Some(7.0), &[(0, 2.0), (1, 3.0)])],
        ObjectiveSense::Maximize,
        &[(0, 3.0), (1, 4.0)],
    );

    let hostile = HostileAdviser::new(BadAdvice::IntegralVariable);
    let record = run_with(
        &instance,
        &[Registration::Adviser(&hostile)],
        vec![policy(hostile.declare_id())],
    );

    assert_eq!(record.outcome, SearchOutcome::ProvenOptimal);
    assert_eq!(record.objective, brute_force(&instance));
    assert!(hostile.calls() > 0, "the adviser really was consulted");
}

/// A legitimate adviser is accepted and proves the same optimum.
///
/// Most-fractional branching is a different exploration order, not a different
/// answer, so the proven optimum must be identical to the default's.
#[test]
fn a_valid_adviser_changes_order_but_not_the_answer() {
    for instance in grid() {
        let plain = run_plain(&instance);
        let record = run_with(
            &instance,
            &[Registration::Adviser(&MostFractional)],
            vec![policy("example.most-fractional")],
        );

        assert_eq!(
            record.outcome,
            plain.outcome,
            "{}: a valid adviser must not change the outcome",
            instance.document().model_id
        );
        assert_eq!(record.objective, plain.objective);
        assert!(!record.forfeited);

        let summary = record.extensions.first().expect("summarized");
        assert_eq!(
            summary.rejected,
            0,
            "{}: this adviser only names variables the executive supplied: {:?}",
            instance.document().model_id,
            summary.failures
        );
    }
}

// ---------------------------------------------------------------------------
// Requirements 14-16: containment and counted budgets, end to end.
// ---------------------------------------------------------------------------

/// A panicking extension is contained, disabled, recorded, and harmless.
#[test]
fn panicking_extensions_are_contained_end_to_end() {
    let instance = model(
        "contained",
        &[
            (0, Domain::Integer, 0.0, 3.0),
            (1, Domain::Integer, 0.0, 3.0),
        ],
        &[(0, None, Some(4.0), &[(0, 1.0), (1, 1.0)])],
        ObjectiveSense::Maximize,
        &[(0, 2.0), (1, 1.0)],
    );
    let plain = run_plain(&instance);

    let producer = HostileProducer::new(BadProposal::Panic);
    let producer_record = run_with(
        &instance,
        &[Registration::Producer(&producer)],
        vec![policy(producer.declare_id())],
    );
    let summary = producer_record.extensions.first().expect("summarized");
    assert!(summary.disabled, "a panicked producer is disabled");
    assert!(
        summary
            .failures
            .iter()
            .any(|failure| failure.kind == FailureKind::Panicked)
    );
    assert_eq!(
        producer.calls(),
        1,
        "a disabled extension is not invoked again"
    );
    assert_eq!(conclusion(&producer_record), conclusion(&plain));

    let adviser = HostileAdviser::new(BadAdvice::Panic);
    let branching = branching_model("contained-branching");
    let branching_plain = run_plain(&branching);
    let adviser_record = run_with(
        &branching,
        &[Registration::Adviser(&adviser)],
        vec![policy(adviser.declare_id())],
    );
    let summary = adviser_record.extensions.first().expect("summarized");
    assert!(summary.disabled, "a panicked adviser is disabled");
    assert_eq!(
        adviser.calls(),
        1,
        "a disabled adviser is not consulted again"
    );
    assert_eq!(adviser_record.outcome, branching_plain.outcome);
    assert_eq!(adviser_record.objective, branching_plain.objective);
    assert!(!adviser_record.forfeited);
}

/// A budget-abusing producer is disabled without affecting the outcome.
#[test]
fn budget_abuse_is_recorded_and_harmless() {
    let instance = model(
        "budget",
        &[
            (0, Domain::Integer, 0.0, 3.0),
            (1, Domain::Integer, 0.0, 3.0),
        ],
        &[(0, None, Some(4.0), &[(0, 1.0), (1, 1.0)])],
        ObjectiveSense::Maximize,
        &[(0, 2.0), (1, 1.0)],
    );
    let plain = run_plain(&instance);

    let hostile = HostileProducer::new(BadProposal::Flood);
    let record = run_with(
        &instance,
        &[Registration::Producer(&hostile)],
        vec![policy(hostile.declare_id())],
    );

    let summary = record.extensions.first().expect("summarized");
    assert!(
        summary
            .failures
            .iter()
            .any(|failure| failure.kind == FailureKind::BudgetExhausted),
        "a flood must exhaust its declared proposal budget: {:?}",
        summary.failures
    );
    assert!(summary.disabled);
    assert!(
        summary.proposals <= 4,
        "the declared budget bounds the accepted proposals, got {}",
        summary.proposals
    );
    assert_eq!(conclusion(&record), conclusion(&plain));
}

/// A caller's tighter budget also bounds an otherwise honest extension.
#[test]
fn a_caller_can_bound_an_honest_extension() {
    let instance = branching_model("caller-budget");

    let mut tight = policy("example.most-fractional");
    tight.invocation_budget = 1;
    let record = run_with(
        &instance,
        &[Registration::Adviser(&MostFractional)],
        vec![tight],
    );

    let summary = record.extensions.first().expect("summarized");
    assert_eq!(summary.invocations, 1, "the caller's budget is honored");
    assert!(
        summary.disabled,
        "an extension at its budget stops being consulted"
    );
    assert_eq!(record.outcome, SearchOutcome::ProvenOptimal);
    assert_eq!(record.objective, brute_force(&instance));
}

// ---------------------------------------------------------------------------
// Requirements 1-3, 18-21: registration, determinism and records.
// ---------------------------------------------------------------------------

/// An unadmittable extension is recorded and never invoked.
#[test]
fn unadmittable_extensions_are_never_invoked() {
    let instance = model(
        "unadmittable",
        &[(0, Domain::Binary, 0.0, 1.0)],
        &[(0, None, Some(1.0), &[(0, 1.0)])],
        ObjectiveSense::Maximize,
        &[(0, 1.0)],
    );
    let plain = run_plain(&instance);

    let cases = [
        (
            BadDeclaration::NewerContract,
            FailureKind::IncompatibleContract,
        ),
        (
            BadDeclaration::OlderContract,
            FailureKind::IncompatibleContract,
        ),
        (
            BadDeclaration::Transformation,
            FailureKind::UnsupportedCategory,
        ),
        (BadDeclaration::ZeroBudget, FailureKind::DeclarationInvalid),
        (
            BadDeclaration::ContinuousOnly,
            FailureKind::UnsupportedProblemClass,
        ),
    ];

    for (kind, expected) in cases {
        let unadmittable = Unadmittable::new(kind);
        let record = run_with(
            &instance,
            &[Registration::Producer(&unadmittable)],
            vec![policy(unadmittable.extension_id())],
        );

        let summary = record
            .extensions
            .first()
            .expect("a refusal is still recorded");
        assert!(!summary.registered, "{kind:?} must not be admitted");
        assert_eq!(
            summary.failures.first().map(|failure| failure.kind),
            Some(expected),
            "{kind:?} must be recorded as {expected:?}"
        );
        assert_eq!(
            unadmittable.calls(),
            0,
            "{kind:?} must never be invoked at all"
        );
        assert_eq!(conclusion(&record), conclusion(&plain));
    }
}

/// Requirement 18: two identical searches with deterministic extensions agree.
#[test]
fn identical_searches_with_extensions_replay_identically() {
    let instance = model(
        "replay",
        &[
            (0, Domain::Integer, 0.0, 3.0),
            (1, Domain::Integer, 0.0, 3.0),
            (2, Domain::Integer, 0.0, 3.0),
        ],
        &[(0, None, Some(5.0), &[(0, 1.0), (1, 2.0), (2, 1.0)])],
        ObjectiveSense::Maximize,
        &[(0, 3.0), (1, 2.0), (2, 2.0)],
    );

    let first = run_with(
        &instance,
        &[
            Registration::Adviser(&MostFractional),
            Registration::Producer(&LowerBoundRounder),
        ],
        vec![
            policy("example.most-fractional"),
            policy("example.lower-bound-rounder"),
        ],
    );
    let second = run_with(
        &instance,
        &[
            Registration::Adviser(&MostFractional),
            Registration::Producer(&LowerBoundRounder),
        ],
        vec![
            policy("example.most-fractional"),
            policy("example.lower-bound-rounder"),
        ],
    );

    assert_eq!(
        SearchRecord {
            elapsed_ms: first.elapsed_ms,
            ..second
        },
        first,
        "deterministic extensions must leave the search replayable"
    );
    assert!(
        first.extensions.iter().all(|summary| summary.deterministic),
        "both extensions declare determinism"
    );

    // Requirement 18's ordering: summaries are in extension-identity order,
    // whatever order the caller supplied.
    let identities: Vec<&str> = first
        .extensions
        .iter()
        .map(|summary| summary.extension_id.as_str())
        .collect();
    assert_eq!(
        identities,
        vec!["example.lower-bound-rounder", "example.most-fractional"]
    );
}

/// A nondeterministic declaration is visible in the record.
#[test]
fn nondeterminism_is_stated_in_the_record() {
    let instance = model(
        "nondeterministic",
        &[(0, Domain::Binary, 0.0, 1.0)],
        &[(0, None, Some(1.0), &[(0, 1.0)])],
        ObjectiveSense::Maximize,
        &[(0, 1.0)],
    );

    let record = run_with(
        &instance,
        &[Registration::Adviser(&NondeterministicAdviser)],
        vec![policy("example.nondeterministic")],
    );

    let summary = record.extensions.first().expect("summarized");
    assert!(summary.registered);
    assert!(
        !summary.deterministic,
        "a reader must be able to see that replay equality is not claimed"
    );
}

/// Requirement 21: an extension-influenced record round trips at version 2.
#[test]
fn extension_influenced_records_round_trip() {
    let instance = model(
        "round-trip",
        &[
            (0, Domain::Integer, 0.0, 3.0),
            (1, Domain::Integer, 0.0, 3.0),
        ],
        &[(0, None, Some(4.0), &[(0, 1.0), (1, 1.0)])],
        ObjectiveSense::Minimize,
        &[(0, 1.0), (1, 1.0)],
    );

    let record = run_with(
        &instance,
        &[Registration::Producer(&LowerBoundRounder)],
        vec![policy("example.lower-bound-rounder")],
    );

    assert_eq!(record.schema_version, SEARCH_SCHEMA_VERSION);
    let json = record.to_json().expect("serializable");
    assert_eq!(
        SearchRecord::from_json(json.as_bytes()).expect("round trip"),
        record
    );
    assert!(
        json.contains("\"extension_id\": \"example.lower-bound-rounder\""),
        "the record names the extension that influenced it: {json}"
    );
    assert!(
        json.contains("\"authority\": \"propose_validated_candidate\""),
        "the record states the acceptance boundary that applied"
    );

    // The extension documents nested in a record are versioned too, and their
    // versions are validated on parse rather than deferred. Mutation targets a
    // parsed field by path, so the assertion cannot depend on serialized
    // position or on the pretty-printer's formatting.
    for path in [vec!["extensions", "0"], vec!["options", "extensions", "0"]] {
        let mut document: serde_json::Value = serde_json::from_str(&json).expect("valid JSON");
        let mut cursor = &mut document;
        for step in &path {
            cursor = match step.parse::<usize>() {
                Ok(index) => &mut cursor[index],
                Err(_) => &mut cursor[*step],
            };
        }
        assert!(
            cursor["schema_version"].is_u64(),
            "{path:?} must be a versioned document in the serialized record"
        );
        cursor["schema_version"] = serde_json::json!(9);
        let mutated = serde_json::to_string(&document).expect("serializable");
        assert!(
            SearchRecord::from_json(mutated.as_bytes()).is_err(),
            "{path:?}: a wrongly versioned extension document must be rejected"
        );
    }
}

/// Requirement 20: a continuous model consults no adviser and solves once.
#[test]
fn continuous_models_consult_no_adviser() {
    let continuous = model(
        "continuous",
        &[
            (0, Domain::Continuous, 0.0, 4.0),
            (1, Domain::Continuous, 0.0, 4.0),
        ],
        &[(0, None, Some(3.0), &[(0, 1.0), (1, 1.0)])],
        ObjectiveSense::Maximize,
        &[(0, 2.0), (1, 1.0)],
    );

    let hostile = HostileAdviser::new(BadAdvice::IntegralVariable);
    let record = run_with(
        &continuous,
        &[Registration::Adviser(&hostile)],
        vec![policy(hostile.declare_id())],
    );

    assert_eq!(record.outcome, SearchOutcome::ProvenOptimal);
    assert_eq!(
        record.nodes_explored, 1,
        "a continuous model performs no branching"
    );
    assert_eq!(record.relaxations_solved, 1);
    assert_eq!(
        hostile.calls(),
        0,
        "with no branching decision to make, no adviser is consulted"
    );
}

/// An invalid extension policy is a caller error, not a recorded failure.
#[test]
fn an_invalid_policy_is_a_configuration_error() {
    let instance = model(
        "policy",
        &[(0, Domain::Binary, 0.0, 1.0)],
        &[],
        ObjectiveSense::Maximize,
        &[(0, 1.0)],
    );

    let mut zero = policy("example.most-fractional");
    zero.invocation_budget = 0;
    assert!(
        search_with_extensions(
            &instance,
            &options(vec![zero]),
            &[Registration::Adviser(&MostFractional)],
            &ExactBackend::default(),
            &CancellationToken::new(),
        )
        .is_err(),
        "a malformed policy the caller supplied is an error, not an extension failure"
    );

    let duplicated = vec![
        policy("example.most-fractional"),
        policy("example.most-fractional"),
    ];
    assert!(
        search_with_extensions(
            &instance,
            &options(duplicated),
            &[Registration::Adviser(&MostFractional)],
            &ExactBackend::default(),
            &CancellationToken::new(),
        )
        .is_err(),
        "a duplicated identity makes the summary ambiguous"
    );
}

/// A pre-cancelled search does no extension work and no backend work.
#[test]
fn a_pre_cancelled_search_consults_nothing() {
    let instance = model(
        "cancelled",
        &[(0, Domain::Binary, 0.0, 1.0)],
        &[],
        ObjectiveSense::Maximize,
        &[(0, 1.0)],
    );

    let hostile = HostileProducer::new(BadProposal::Panic);
    let cancel = CancellationToken::new();
    cancel.cancel();

    let record = search_with_extensions(
        &instance,
        &options(vec![policy(hostile.declare_id())]),
        &[Registration::Producer(&hostile)],
        &ExactBackend::default(),
        &cancel,
    )
    .expect("a cancelled search still returns a record");

    assert_eq!(record.outcome, SearchOutcome::Interrupted);
    assert_eq!(record.relaxations_solved, 0);
    assert_eq!(hostile.calls(), 0, "a cancelled search consults nothing");
    assert!(!record.outcome.proves_completion());
}
