//! Independent acceptance contracts for the SPEC-0003 search executive.
//!
//! Every test states an externally observable contract and maps to a
//! requirement number. No native library is used: relaxations are solved by an
//! independent exact vertex-enumeration LP solver written for these tests, and
//! termination rules are driven by a scripted backend. That keeps the pruning
//! and forfeiture contracts covered even when HiGHS is not provisioned, and it
//! proves the executive is genuinely backend-neutral.

use std::cell::RefCell;

use optimizer_core::{
    Assignment, Backend, Bound, CancellationToken, Candidate, Constraint, Device, Domain,
    ErrorKind, LinearTerm, Model, ModelDocument, Objective, ObjectiveSense, SOLVE_SCHEMA_VERSION,
    SolveOptions, SolveRecord, Termination, Tolerances, ValidationError, Variable, WarmStart,
};
use optimizer_solver::{
    SEARCH_SCHEMA_VERSION, SearchOptions, SearchOutcome, SearchRecord, initial_checkpoint, search,
};

const EPSILON: f64 = 1e-9;

fn tolerances() -> Tolerances {
    Tolerances {
        absolute: 1e-7,
        relative: 1e-9,
        integrality: 1e-7,
    }
}

fn relaxation_options() -> SolveOptions {
    SolveOptions {
        schema_version: SOLVE_SCHEMA_VERSION,
        seed: 17,
        time_limit_ms: None,
        iteration_limit: None,
        node_limit: None,
        tolerances: tolerances(),
        threads: 1,
    }
}

fn options() -> SearchOptions {
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
        relaxation: relaxation_options(),
        // C2's contracts run with no extension permitted, so every assertion
        // below describes the executive's own behavior.
        extensions: Vec::new(),
    }
}

fn finite(value: f64) -> Bound {
    Bound::Finite { value }
}

/// A version this crate will never accept, for negative version tests.
///
/// Written as an offset rather than a literal so a later version bump cannot
/// silently turn a rejection case into an accepted one.
const UNSUPPORTED_SCHEMA_VERSION: u32 = SEARCH_SCHEMA_VERSION + 1;

/// Set only the top-level `schema_version` of a serialized document.
///
/// Replacing the first `"schema_version": 1` occurrence in the text would be
/// wrong: a record's nested `candidate` and `options` carry their own versions,
/// and which appears first depends on which optional fields are present. It
/// would also silently become a no-op for a document with no nested versions at
/// all. Mutating the parsed value targets the document's own field by name, so
/// neither the field order nor the serializer's formatting can make an assertion
/// vacuous.
fn retarget_version(json: &str, version: u32) -> String {
    let mut document: serde_json::Value = serde_json::from_str(json).expect("valid JSON");
    let object = document.as_object_mut().expect("a JSON object");
    let previous = object.insert("schema_version".to_string(), version.into());
    assert!(
        previous.is_some(),
        "the document must already carry a schema_version to retarget"
    );
    serde_json::to_string_pretty(&document).expect("serializable")
}

/// One compact constraint: id, optional lower bound, optional upper bound, terms.
type ConstraintSpec<'a> = (u32, Option<f64>, Option<f64>, &'a [(u32, f64)]);

/// Build a model from compact parts.
fn model(
    model_id: &str,
    variables: &[(u32, Domain, f64, f64)],
    constraints: &[ConstraintSpec<'_>],
    sense: ObjectiveSense,
    offset: f64,
    objective_terms: &[(u32, f64)],
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
        schema_version: optimizer_core::SCHEMA_VERSION,
        model_id: model_id.to_string(),
        variables: variables
            .iter()
            .map(|(id, domain, lower, upper)| Variable {
                id: *id,
                domain: *domain,
                lower: finite(*lower),
                upper: finite(*upper),
            })
            .collect(),
        constraints: constraints
            .iter()
            .map(|(id, lower, upper, pairs)| Constraint {
                id: *id,
                lower: lower.map_or(Bound::NegativeInfinity, finite),
                upper: upper.map_or(Bound::PositiveInfinity, finite),
                terms: terms(pairs),
            })
            .collect(),
        objective: Objective {
            sense,
            offset,
            terms: terms(objective_terms),
        },
    })
    .expect("model")
}

// ---------------------------------------------------------------------------
// An independent exact LP backend, by vertex enumeration.
//
// Every test model has finite variable bounds, so the feasible region is a
// polytope and an optimum, if one exists, lies at a vertex. Enumerating all
// n-subsets of the half-planes and solving each square system is exponential
// but exact, and it is written independently of the executive it checks.
// ---------------------------------------------------------------------------

/// One half-plane `coefficients . x <= rhs`.
struct HalfPlane {
    coefficients: Vec<f64>,
    rhs: f64,
}

fn half_planes(model: &Model) -> Vec<HalfPlane> {
    let document = model.document();
    let count = document.variables.len();
    let index = |variable_id: u32| {
        document
            .variables
            .binary_search_by_key(&variable_id, |v| v.id)
            .expect("known variable")
    };
    let mut planes = Vec::new();
    for (position, variable) in document.variables.iter().enumerate() {
        if let Bound::Finite { value } = variable.upper {
            let mut coefficients = vec![0.0; count];
            coefficients[position] = 1.0;
            planes.push(HalfPlane {
                coefficients,
                rhs: value,
            });
        }
        if let Bound::Finite { value } = variable.lower {
            let mut coefficients = vec![0.0; count];
            coefficients[position] = -1.0;
            planes.push(HalfPlane {
                coefficients,
                rhs: -value,
            });
        }
    }
    for constraint in &document.constraints {
        let mut row = vec![0.0; count];
        for term in &constraint.terms {
            row[index(term.variable_id)] += term.coefficient;
        }
        if let Bound::Finite { value } = constraint.upper {
            planes.push(HalfPlane {
                coefficients: row.clone(),
                rhs: value,
            });
        }
        if let Bound::Finite { value } = constraint.lower {
            planes.push(HalfPlane {
                coefficients: row.iter().map(|c| -c).collect(),
                rhs: -value,
            });
        }
    }
    planes
}

/// Solve a square system by Gaussian elimination with partial pivoting.
fn solve_square(mut matrix: Vec<Vec<f64>>, mut rhs: Vec<f64>) -> Option<Vec<f64>> {
    let n = rhs.len();
    for column in 0..n {
        let pivot = (column..n)
            .max_by(|a, b| {
                matrix[*a][column]
                    .abs()
                    .partial_cmp(&matrix[*b][column].abs())
                    .unwrap_or(std::cmp::Ordering::Equal)
            })
            .expect("nonempty");
        if matrix[pivot][column].abs() < 1e-12 {
            return None;
        }
        matrix.swap(column, pivot);
        rhs.swap(column, pivot);
        // Split so the pivot row and the rows below it are borrowed separately.
        let (upper, lower) = matrix.split_at_mut(column + 1);
        let pivot_row = &upper[column];
        let pivot_rhs = rhs[column];
        for (offset, row) in lower.iter_mut().enumerate() {
            let factor = row[column] / pivot_row[column];
            for (target, source) in row.iter_mut().zip(pivot_row).skip(column) {
                *target -= factor * source;
            }
            rhs[column + 1 + offset] -= factor * pivot_rhs;
        }
    }
    let mut solution = vec![0.0; n];
    for row in (0..n).rev() {
        let mut sum = rhs[row];
        for column in row + 1..n {
            sum -= matrix[row][column] * solution[column];
        }
        solution[row] = sum / matrix[row][row];
    }
    Some(solution)
}

/// Exact LP optimum over a bounded polytope, or `None` when infeasible.
fn lp_optimum(model: &Model) -> Option<Vec<f64>> {
    let document = model.document();
    let n = document.variables.len();
    let planes = half_planes(model);

    let feasible = |point: &[f64]| {
        planes.iter().all(|plane| {
            let activity: f64 = plane
                .coefficients
                .iter()
                .zip(point)
                .map(|(c, x)| c * x)
                .sum();
            activity <= plane.rhs + 1e-7
        })
    };
    let objective = |point: &[f64]| {
        let mut total = document.objective.offset;
        for term in &document.objective.terms {
            let position = document
                .variables
                .binary_search_by_key(&term.variable_id, |v| v.id)
                .expect("known variable");
            total += term.coefficient * point[position];
        }
        total
    };

    if n == 0 {
        return Some(Vec::new());
    }
    if planes.len() < n {
        return None;
    }

    let mut best: Option<Vec<f64>> = None;
    let mut indices: Vec<usize> = (0..n).collect();
    loop {
        let matrix: Vec<Vec<f64>> = indices
            .iter()
            .map(|i| planes[*i].coefficients.clone())
            .collect();
        let rhs: Vec<f64> = indices.iter().map(|i| planes[*i].rhs).collect();
        if let Some(point) = solve_square(matrix, rhs)
            && feasible(&point)
        {
            let better = best
                .as_ref()
                .is_none_or(|current| match document.objective.sense {
                    ObjectiveSense::Minimize => objective(&point) < objective(current) - 1e-12,
                    ObjectiveSense::Maximize => objective(&point) > objective(current) + 1e-12,
                });
            if better {
                best = Some(point);
            }
        }
        // Advance the combination in lexicographic order.
        let mut position = n;
        loop {
            if position == 0 {
                return best;
            }
            position -= 1;
            if indices[position] < planes.len() - (n - position) {
                indices[position] += 1;
                for later in position + 1..n {
                    indices[later] = indices[later - 1] + 1;
                }
                break;
            }
        }
    }
}

/// A backend that solves each relaxation exactly, independently of the engine.
#[derive(Default)]
struct ExactBackend {
    solves: RefCell<u32>,
}

impl Backend for ExactBackend {
    fn solve(
        &self,
        model: &Model,
        options: &SolveOptions,
        _cancel: &CancellationToken,
        _warm_start: Option<WarmStart<'_>>,
    ) -> Result<SolveRecord, ValidationError> {
        *self.solves.borrow_mut() += 1;
        let record = |termination, candidate: Option<Candidate>, objective| SolveRecord {
            schema_version: SOLVE_SCHEMA_VERSION,
            model_id: model.document().model_id.clone(),
            backend: "exact-test-lp".to_string(),
            backend_version: "1.0.0".to_string(),
            termination,
            native_status: None,
            objective,
            best_bound: objective,
            gap: None,
            candidate,
            validation: None,
            warnings: Vec::new(),
            elapsed_ms: 0,
            options: options.clone(),
        };
        match lp_optimum(model) {
            None => Ok(record(Termination::Infeasible, None, None)),
            Some(point) => {
                let candidate = Candidate {
                    schema_version: optimizer_core::SCHEMA_VERSION,
                    model_id: model.document().model_id.clone(),
                    values: model
                        .document()
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
                Ok(record(
                    Termination::Optimal,
                    Some(candidate),
                    Some(report.objective),
                ))
            }
        }
    }
}

/// A backend that returns scripted terminations, to drive the bound rules.
struct ScriptedBackend {
    script: Vec<Termination>,
    calls: RefCell<usize>,
}

impl ScriptedBackend {
    fn new(script: &[Termination]) -> Self {
        Self {
            script: script.to_vec(),
            calls: RefCell::new(0),
        }
    }
}

impl Backend for ScriptedBackend {
    fn solve(
        &self,
        model: &Model,
        options: &SolveOptions,
        _cancel: &CancellationToken,
        _warm_start: Option<WarmStart<'_>>,
    ) -> Result<SolveRecord, ValidationError> {
        let mut calls = self.calls.borrow_mut();
        let termination = *self
            .script
            .get(*calls)
            .unwrap_or(self.script.last().expect("a nonempty script"));
        *calls += 1;
        drop(calls);

        // A scripted solution is deliberately fractional, so an engine that
        // wrongly accepted it would be caught by the original-model check.
        let candidate = Candidate {
            schema_version: optimizer_core::SCHEMA_VERSION,
            model_id: model.document().model_id.clone(),
            values: model
                .document()
                .variables
                .iter()
                .map(|variable| Assignment {
                    variable_id: variable.id,
                    value: 0.5,
                })
                .collect(),
        };
        let objective = model
            .evaluate(&candidate, options.tolerances)
            .map(|report| report.objective)
            .ok();
        Ok(SolveRecord {
            schema_version: SOLVE_SCHEMA_VERSION,
            model_id: model.document().model_id.clone(),
            backend: "scripted".to_string(),
            backend_version: "0.0.0".to_string(),
            termination,
            native_status: None,
            objective,
            best_bound: objective,
            gap: None,
            candidate: Some(candidate),
            validation: None,
            warnings: Vec::new(),
            elapsed_ms: 0,
            options: options.clone(),
        })
    }
}

// ---------------------------------------------------------------------------
// Independent brute-force reference over the discrete box.
// ---------------------------------------------------------------------------

/// Exhaustively enumerate every integer assignment and return the true optimum.
///
/// This is the independent oracle: it shares no code with the executive.
fn brute_force(model: &Model) -> Option<(Vec<f64>, f64)> {
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

    let mut best: Option<(Vec<f64>, f64)> = None;
    let mut assignment: Vec<f64> = ranges.iter().map(|(lower, _)| *lower).collect();
    loop {
        let candidate = Candidate {
            schema_version: optimizer_core::SCHEMA_VERSION,
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
            let better =
                best.as_ref()
                    .is_none_or(|(_, objective)| match document.objective.sense {
                        ObjectiveSense::Minimize => report.objective < *objective,
                        ObjectiveSense::Maximize => report.objective > *objective,
                    });
            if better {
                best = Some((assignment.clone(), report.objective));
            }
        }
        // Odometer over the integer box.
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

fn run(model: &Model, options: &SearchOptions) -> SearchRecord {
    search(
        model,
        options,
        &ExactBackend::default(),
        &CancellationToken::new(),
    )
    .expect("search")
}

// ---------------------------------------------------------------------------
// Requirements 1-4: ownership, node shape, identity preservation, neutrality.
// ---------------------------------------------------------------------------

/// Requirements 2-3: branching restricts discrete bounds only, and the
/// incumbent comes back in original variable IDs against the original model.
#[test]
fn incumbent_uses_original_identities() {
    // Deliberately non-contiguous IDs: a renumbering bug cannot hide.
    let discrete = model(
        "identity",
        &[
            (7, Domain::Integer, 0.0, 3.0),
            (11, Domain::Integer, 0.0, 3.0),
        ],
        &[(4, None, Some(3.5), &[(7, 1.0), (11, 1.0)])],
        ObjectiveSense::Maximize,
        0.0,
        &[(7, 1.0), (11, 1.0)],
    );
    let record = run(&discrete, &options());

    assert_eq!(record.outcome, SearchOutcome::ProvenOptimal);
    assert_eq!(record.model_id, "identity");
    let candidate = record.candidate.expect("incumbent");
    let ids: Vec<u32> = candidate.values.iter().map(|v| v.variable_id).collect();
    assert_eq!(ids, vec![7, 11], "original IDs must survive the search");
    // x7 + x11 <= 3.5 over integers maximizes at 3.
    assert_eq!(record.objective, Some(3.0));
}

/// Requirement 4: the executive drives whatever backend it is handed.
#[test]
fn search_is_backend_neutral() {
    let discrete = model(
        "neutral",
        &[(0, Domain::Integer, 0.0, 4.0)],
        &[(0, None, Some(2.5), &[(0, 1.0)])],
        ObjectiveSense::Maximize,
        0.0,
        &[(0, 1.0)],
    );
    let exact = run(&discrete, &options());
    assert_eq!(exact.outcome, SearchOutcome::ProvenOptimal);
    assert_eq!(exact.objective, Some(2.0));

    // A different backend implementation drives the same executive.
    let scripted = search(
        &discrete,
        &options(),
        &ScriptedBackend::new(&[Termination::Infeasible]),
        &CancellationToken::new(),
    )
    .expect("search");
    assert_eq!(scripted.outcome, SearchOutcome::ProvenInfeasible);
    assert_eq!(scripted.backend, optimizer_solver::RELAXATION_BACKEND);
}

// ---------------------------------------------------------------------------
// Requirements 5-8: bound validity, forfeiture, and the pruning rules.
// ---------------------------------------------------------------------------

/// Requirements 5 and 6, the central contract: a relaxation that did not prove
/// optimality yields no usable bound, so the search must forfeit its proof
/// claim rather than presenting a limited solve as a completed one.
#[test]
fn unproven_relaxation_forfeits_the_proof_claim() {
    let discrete = model(
        "forfeit",
        &[
            (0, Domain::Integer, 0.0, 4.0),
            (1, Domain::Integer, 0.0, 4.0),
        ],
        &[(0, None, Some(5.0), &[(0, 1.0), (1, 1.0)])],
        ObjectiveSense::Maximize,
        0.0,
        &[(0, 1.0), (1, 1.0)],
    );

    for termination in [
        Termination::TimeLimit,
        Termination::IterationLimit,
        Termination::NodeLimit,
        Termination::Interrupted,
        Termination::Feasible,
        Termination::NumericalFailure,
        Termination::BackendFailure,
        Termination::Unsupported,
    ] {
        let record = search(
            &discrete,
            &options(),
            &ScriptedBackend::new(&[termination]),
            &CancellationToken::new(),
        )
        .expect("search");

        assert!(
            record.forfeited,
            "{termination:?} must forfeit the proof claim"
        );
        assert!(
            !record.outcome.proves_completion(),
            "{termination:?} must never report a completed proof, got {:?}",
            record.outcome
        );
        assert_eq!(
            record.nodes_pruned_bound, 0,
            "{termination:?} supplies no valid bound, so nothing may be pruned by bound"
        );
    }
}

/// Requirement 5: only a proven relaxation contributes a dual bound.
#[test]
fn only_proven_relaxations_supply_a_dual_bound() {
    let continuous = model(
        "bounded",
        &[(0, Domain::Continuous, 0.0, 2.0)],
        &[],
        ObjectiveSense::Maximize,
        0.0,
        &[(0, 1.0)],
    );
    let proven = run(&continuous, &options());
    assert_eq!(proven.outcome, SearchOutcome::ProvenOptimal);
    assert_eq!(proven.dual_bound, Some(2.0));
    assert!(!proven.forfeited);

    let limited = search(
        &continuous,
        &options(),
        &ScriptedBackend::new(&[Termination::TimeLimit]),
        &CancellationToken::new(),
    )
    .expect("search");
    assert!(limited.forfeited);
    assert_eq!(
        limited.dual_bound, None,
        "an unproven relaxation must not leave a dual bound behind"
    );
}

/// Requirement 7: only a proven infeasible relaxation closes a node.
#[test]
fn only_proven_infeasibility_prunes_a_node() {
    let discrete = model(
        "infeasible-vs-limit",
        &[(0, Domain::Integer, 0.0, 2.0)],
        &[(0, Some(5.0), None, &[(0, 1.0)])],
        ObjectiveSense::Minimize,
        0.0,
        &[(0, 1.0)],
    );

    let proven = search(
        &discrete,
        &options(),
        &ScriptedBackend::new(&[Termination::Infeasible]),
        &CancellationToken::new(),
    )
    .expect("search");
    assert_eq!(proven.outcome, SearchOutcome::ProvenInfeasible);
    assert_eq!(proven.nodes_pruned_infeasible, 1);
    assert!(!proven.forfeited);

    let limited = search(
        &discrete,
        &options(),
        &ScriptedBackend::new(&[Termination::TimeLimit]),
        &CancellationToken::new(),
    )
    .expect("search");
    assert_eq!(
        limited.nodes_pruned_infeasible, 0,
        "a limit is not evidence of infeasibility"
    );
    assert_ne!(limited.outcome, SearchOutcome::ProvenInfeasible);
}

/// Requirement 16: an unbounded relaxation is never a feasible incumbent.
#[test]
fn unbounded_relaxation_is_not_an_incumbent() {
    let discrete = model(
        "unbounded",
        &[(0, Domain::Integer, 0.0, 4.0)],
        &[],
        ObjectiveSense::Maximize,
        0.0,
        &[(0, 1.0)],
    );
    for termination in [Termination::Unbounded, Termination::UnboundedOrInfeasible] {
        let record = search(
            &discrete,
            &options(),
            &ScriptedBackend::new(&[termination]),
            &CancellationToken::new(),
        )
        .expect("search");
        assert_eq!(record.outcome, SearchOutcome::UnboundedOrInfeasible);
        assert!(
            record.candidate.is_none(),
            "unboundedness is backend evidence, not an incumbent"
        );
        assert!(record.objective.is_none());
    }
}

/// Requirement 8: an exhausted proof leaves no open node behind.
#[test]
fn proven_bounds_prune_dominated_subtrees() {
    let discrete = model(
        "prune",
        &[
            (0, Domain::Integer, 0.0, 6.0),
            (1, Domain::Integer, 0.0, 6.0),
        ],
        &[(0, None, Some(6.0), &[(0, 1.0), (1, 1.0)])],
        ObjectiveSense::Maximize,
        0.0,
        &[(0, 1.0), (1, 2.0)],
    );
    let record = run(&discrete, &options());
    assert_eq!(record.outcome, SearchOutcome::ProvenOptimal);
    assert_eq!(record.objective, Some(12.0));
    assert!(!record.forfeited);
    assert_eq!(record.open_nodes_remaining, 0);
}

// ---------------------------------------------------------------------------
// Requirements 9-13: branching, validation, incumbent acceptance.
// ---------------------------------------------------------------------------

/// Requirements 9-10: a fractional relaxation forces covering branches.
#[test]
fn fractional_relaxations_force_covering_branches() {
    let discrete = model(
        "branching",
        &[(0, Domain::Integer, 0.0, 10.0)],
        &[(0, None, Some(3.5), &[(0, 1.0)])],
        ObjectiveSense::Maximize,
        0.0,
        &[(0, 1.0)],
    );
    let record = run(&discrete, &options());
    assert_eq!(record.outcome, SearchOutcome::ProvenOptimal);
    assert_eq!(record.objective, Some(3.0));
    assert!(
        record.nodes_explored > 1,
        "a fractional root must produce child nodes"
    );
}

/// Requirement 12: an incumbent is validated against the original model, which
/// still carries the integrality the relaxation dropped.
#[test]
fn fractional_solutions_never_become_incumbents() {
    let discrete = model(
        "fractional-claim",
        &[(0, Domain::Integer, 0.0, 1.0)],
        &[],
        ObjectiveSense::Maximize,
        0.0,
        &[(0, 1.0)],
    );
    let record = search(
        &discrete,
        &options(),
        &ScriptedBackend::new(&[Termination::Optimal]),
        &CancellationToken::new(),
    )
    .expect("search");

    if let Some(candidate) = &record.candidate {
        let report = discrete
            .evaluate(candidate, tolerances())
            .expect("published incumbents must evaluate");
        assert!(
            report.feasible,
            "a published incumbent must satisfy the original model"
        );
    }
}

/// Requirement 11: an unrepresentable branch bound is an explicit failure.
#[test]
fn unrepresentable_branch_bounds_are_rejected() {
    let huge = 9_007_199_254_740_993.0;
    let discrete = model(
        "huge",
        &[(0, Domain::Integer, 0.0, huge)],
        &[(0, None, Some(huge - 0.5), &[(0, 1.0)])],
        ObjectiveSense::Maximize,
        0.0,
        &[(0, 1.0)],
    );
    let outcome = search(
        &discrete,
        &options(),
        &ScriptedBackend::new(&[Termination::Optimal]),
        &CancellationToken::new(),
    );
    match outcome {
        Err(error) => assert!(
            matches!(error.kind, ErrorKind::Unsupported | ErrorKind::Numerical),
            "unexpected category {:?}",
            error.kind
        ),
        Ok(record) => assert!(
            !record.outcome.proves_completion(),
            "an unrepresentable branch must not yield a proof"
        ),
    }
}

// ---------------------------------------------------------------------------
// Requirements 14-16: exhaustive correctness against an independent oracle.
// ---------------------------------------------------------------------------

/// Requirement 14: over a family of tiny discrete models, the executive's
/// proven optimum equals a brute-force enumeration of the whole assignment
/// space. This is the contract that would catch an unsound prune.
#[test]
fn exhaustive_tiny_models_match_brute_force() {
    let mut checked = 0;
    for (index, sense) in [ObjectiveSense::Minimize, ObjectiveSense::Maximize]
        .into_iter()
        .enumerate()
    {
        // A fixed finite grid; no randomness, so a failure reproduces exactly.
        for c0 in [-2.0_f64, -1.0, 1.0, 3.0] {
            for c1 in [-1.0_f64, 1.0, 2.0] {
                for limit in [1.5_f64, 3.0, 4.5, 7.0] {
                    for domain in [Domain::Integer, Domain::Binary] {
                        let upper = if domain == Domain::Binary { 1.0 } else { 3.0 };
                        let name = format!("grid-{index}-{c0}-{c1}-{limit}");
                        let discrete = model(
                            &name,
                            &[(0, domain, 0.0, upper), (1, domain, 0.0, upper)],
                            &[
                                (0, None, Some(limit), &[(0, 1.0), (1, 1.0)]),
                                (1, Some(-limit), Some(limit), &[(0, 2.0), (1, -1.0)]),
                            ],
                            sense,
                            0.25,
                            &[(0, c0), (1, c1)],
                        );

                        let record = run(&discrete, &options());
                        let expected = brute_force(&discrete);
                        checked += 1;

                        match expected {
                            None => assert_eq!(
                                record.outcome,
                                SearchOutcome::ProvenInfeasible,
                                "{name}: the oracle found no feasible assignment"
                            ),
                            Some((_, objective)) => {
                                assert_eq!(
                                    record.outcome,
                                    SearchOutcome::ProvenOptimal,
                                    "{name}: the oracle found a feasible assignment"
                                );
                                let found = record.objective.expect("an optimum has an objective");
                                assert!(
                                    (found - objective).abs() <= 1e-6,
                                    "{name}: engine {found} vs oracle {objective}"
                                );
                                let candidate = record.candidate.expect("incumbent");
                                let report =
                                    discrete.evaluate(&candidate, tolerances()).expect("report");
                                assert!(report.feasible, "{name}: incumbent must be feasible");
                                assert!(
                                    (report.objective - objective).abs() <= 1e-6,
                                    "{name}: recomputed objective disagrees with the oracle"
                                );
                            }
                        }
                        assert!(!record.forfeited, "{name}: a clean search must not forfeit");
                    }
                }
            }
        }
    }
    assert_eq!(checked, 192, "the fixed grid must stay fixed");
}

/// Requirement 14: proven infeasibility carries no incumbent.
#[test]
fn proven_infeasibility_carries_no_incumbent() {
    let discrete = model(
        "contradiction",
        &[(0, Domain::Integer, 0.0, 2.0)],
        // x >= 2 and x <= 1 cannot both hold.
        &[
            (0, Some(2.0), None, &[(0, 1.0)]),
            (1, None, Some(1.0), &[(0, 1.0)]),
        ],
        ObjectiveSense::Minimize,
        0.0,
        &[(0, 1.0)],
    );
    assert!(brute_force(&discrete).is_none(), "the oracle agrees");

    let record = run(&discrete, &options());
    assert_eq!(record.outcome, SearchOutcome::ProvenInfeasible);
    assert!(record.candidate.is_none());
    assert!(record.objective.is_none());
    assert!(record.outcome.proves_completion());
}

// ---------------------------------------------------------------------------
// Requirements 17-20: budgets, cancellation, continuous pass-through.
// ---------------------------------------------------------------------------

/// Requirement 19: a pre-cancelled search dispatches no relaxation at all.
#[test]
fn pre_cancelled_search_does_no_backend_work() {
    let discrete = model(
        "cancelled",
        &[(0, Domain::Integer, 0.0, 4.0)],
        &[],
        ObjectiveSense::Maximize,
        0.0,
        &[(0, 1.0)],
    );
    let cancel = CancellationToken::new();
    cancel.cancel();
    let backend = ExactBackend::default();
    let record = search(&discrete, &options(), &backend, &cancel).expect("search");

    assert_eq!(record.outcome, SearchOutcome::Interrupted);
    assert_eq!(
        *backend.solves.borrow(),
        0,
        "no relaxation may be dispatched"
    );
    assert_eq!(record.relaxations_solved, 0);
    assert!(!record.outcome.proves_completion());
}

/// Requirements 17-18: each budget produces its own outcome.
#[test]
fn each_budget_has_its_own_outcome() {
    let discrete = model(
        "budgets",
        &[
            (0, Domain::Integer, 0.0, 20.0),
            (1, Domain::Integer, 0.0, 20.0),
        ],
        &[(0, None, Some(20.5), &[(0, 2.0), (1, 3.0)])],
        ObjectiveSense::Maximize,
        0.0,
        &[(0, 1.0), (1, 1.0)],
    );

    let mut node_limited = options();
    node_limited.node_limit = Some(1);
    let record = run(&discrete, &node_limited);
    assert_eq!(record.outcome, SearchOutcome::NodeLimit);
    assert!(!record.outcome.proves_completion());
    assert_eq!(record.nodes_explored, 1);

    let mut open_limited = options();
    open_limited.open_node_limit = Some(1);
    let record = run(&discrete, &open_limited);
    assert!(
        matches!(
            record.outcome,
            SearchOutcome::OpenNodeLimit | SearchOutcome::ProvenOptimal
        ),
        "unexpected outcome {:?}",
        record.outcome
    );
}

/// Requirement 17: each invalid budget keeps its own diagnostic category.
#[test]
fn invalid_budgets_are_categorized() {
    let discrete = model(
        "invalid",
        &[(0, Domain::Integer, 0.0, 1.0)],
        &[],
        ObjectiveSense::Maximize,
        0.0,
        &[(0, 1.0)],
    );

    let mut version = options();
    version.schema_version = UNSUPPORTED_SCHEMA_VERSION;
    assert_eq!(
        search(
            &discrete,
            &version,
            &ExactBackend::default(),
            &CancellationToken::new()
        )
        .unwrap_err()
        .kind,
        ErrorKind::Document
    );

    for mutate in [
        (|o: &mut SearchOptions| o.node_limit = Some(0)) as fn(&mut SearchOptions),
        |o: &mut SearchOptions| o.time_limit_ms = Some(0),
        |o: &mut SearchOptions| o.open_node_limit = Some(0),
    ] {
        let mut invalid = options();
        mutate(&mut invalid);
        assert_eq!(
            search(
                &discrete,
                &invalid,
                &ExactBackend::default(),
                &CancellationToken::new()
            )
            .unwrap_err()
            .kind,
            ErrorKind::Unsupported,
            "a zero budget must be rejected"
        );
    }

    let mut tolerance = options();
    tolerance.improvement_tolerance = -1.0;
    assert_eq!(
        search(
            &discrete,
            &tolerance,
            &ExactBackend::default(),
            &CancellationToken::new()
        )
        .unwrap_err()
        .kind,
        ErrorKind::Tolerance
    );
}

/// Requirement 20: a continuous model performs no branching and solves once.
#[test]
fn continuous_models_solve_without_branching() {
    let continuous = model(
        "continuous",
        &[
            (0, Domain::Continuous, 0.0, 1.0),
            (1, Domain::Continuous, 0.0, 1.0),
        ],
        &[(0, None, Some(1.5), &[(0, 1.0), (1, 1.0)])],
        ObjectiveSense::Maximize,
        0.0,
        &[(0, 1.0), (1, 1.0)],
    );
    let backend = ExactBackend::default();
    let record =
        search(&continuous, &options(), &backend, &CancellationToken::new()).expect("search");

    assert_eq!(record.outcome, SearchOutcome::ProvenOptimal);
    assert_eq!(record.objective, Some(1.5));
    assert_eq!(
        *backend.solves.borrow(),
        1,
        "a continuous model needs exactly one relaxation"
    );
    assert_eq!(record.nodes_explored, 1);
}

// ---------------------------------------------------------------------------
// Requirements 21-23: determinism, records, checkpoints.
// ---------------------------------------------------------------------------

/// Requirement 21: two identical searches explore identically.
#[test]
fn identical_searches_replay_identically() {
    let discrete = model(
        "replay",
        &[
            (0, Domain::Integer, 0.0, 5.0),
            (1, Domain::Integer, 0.0, 5.0),
        ],
        &[(0, None, Some(7.5), &[(0, 2.0), (1, 3.0)])],
        ObjectiveSense::Maximize,
        0.0,
        &[(0, 3.0), (1, 4.0)],
    );
    let first = run(&discrete, &options());
    let second = run(&discrete, &options());

    assert_eq!(first.outcome, second.outcome);
    assert_eq!(first.objective, second.objective);
    assert_eq!(first.nodes_explored, second.nodes_explored);
    assert_eq!(first.nodes_pruned_bound, second.nodes_pruned_bound);
    assert_eq!(
        first.nodes_pruned_infeasible,
        second.nodes_pruned_infeasible
    );
    assert_eq!(first.relaxations_solved, second.relaxations_solved);
    assert_eq!(first.candidate, second.candidate);
}

/// Requirement 22: an absent measurement is omitted, not serialized as null.
#[test]
fn records_omit_absent_measurements() {
    let discrete = model(
        "record",
        &[(0, Domain::Integer, 0.0, 3.0)],
        &[(0, Some(9.0), None, &[(0, 1.0)])],
        ObjectiveSense::Minimize,
        0.0,
        &[(0, 1.0)],
    );
    let record = run(&discrete, &options());
    assert_eq!(record.outcome, SearchOutcome::ProvenInfeasible);

    let json = record.to_json().expect("serializable");
    // Absent *measurements* are omitted entirely. An absent budget inside
    // `options` is still an explicit null, matching the C1 configuration
    // convention where null means "unlimited" rather than a missing number.
    for measurement in ["objective", "dual_bound", "gap", "candidate", "validation"] {
        assert!(
            !json.contains(&format!("\"{measurement}\"")),
            "absent {measurement} must be omitted, not null: {json}"
        );
    }
    assert!(json.contains("\"forfeited\""));
    assert!(
        json.contains("\"node_limit\": null"),
        "an unlimited budget stays an explicit null in configuration"
    );
    // An extension-free search says so with an empty list rather than by
    // omitting the field, so a reader can tell "none participated" from
    // "this record predates extensions".
    assert!(
        json.contains("\"extensions\": []"),
        "an extension-free search records an empty list: {json}"
    );

    let parsed = SearchRecord::from_json(json.as_bytes()).expect("round trip");
    assert_eq!(parsed, record);
}

/// Requirement 22: bad versions and nonfinite measurements are rejected.
#[test]
fn records_reject_bad_versions_and_nonfinite_values() {
    let discrete = model(
        "versions",
        &[(0, Domain::Integer, 0.0, 1.0)],
        &[],
        ObjectiveSense::Maximize,
        0.0,
        &[(0, 1.0)],
    );
    let mut record = run(&discrete, &options());

    record.objective = Some(f64::INFINITY);
    assert_eq!(
        record.to_json().unwrap_err().kind,
        ErrorKind::Numerical,
        "a nonfinite measurement must not serialize"
    );

    record.objective = Some(1.0);
    let json = record.to_json().expect("serializable");
    // The record's own version, not the nested candidate's or its options'.
    // Which of those appears first in the text depends on which optional fields
    // are present, so anchoring on position would silently stop testing this.
    let bumped = retarget_version(&json, UNSUPPORTED_SCHEMA_VERSION);
    assert_ne!(bumped, json, "the version must actually have been changed");
    assert_eq!(
        SearchRecord::from_json(bumped.as_bytes()).unwrap_err().kind,
        ErrorKind::Document
    );

    // The unmutated record still round trips, so the rejection above is caused
    // by the version and not by the retargeting having damaged the document.
    assert_eq!(
        SearchRecord::from_json(json.as_bytes()).expect("round trip"),
        record
    );
}

/// Requirement 22: a record's nested versioned documents are validated on
/// parse, not only its own version.
///
/// This is the contract whose absence let the version assertion above be
/// mutated on a nested field and still appear to pass. The version-1 schemas
/// already pin every nested `schema_version`, so a parser that checked only
/// the outer version would be laxer than the artifact validation tooling.
#[test]
fn nested_document_versions_are_validated_on_parse() {
    let discrete = model(
        "nested",
        &[(0, Domain::Integer, 0.0, 3.0)],
        &[(0, None, Some(2.0), &[(0, 1.0)])],
        ObjectiveSense::Maximize,
        0.0,
        &[(0, 1.0)],
    );
    let record = run(&discrete, &options());
    assert_eq!(record.outcome, SearchOutcome::ProvenOptimal);
    assert!(
        record.candidate.is_some() && record.validation.is_some(),
        "this record must carry the nested documents under test"
    );

    let json = record.to_json().expect("serializable");
    assert_eq!(
        SearchRecord::from_json(json.as_bytes()).expect("round trip"),
        record,
        "the intact record round trips, so each rejection below is the version"
    );

    // Every nested versioned document is rejected on its own. Mutation targets
    // a parsed field by path, so no assertion depends on serialized position.
    for path in [
        vec!["candidate"],
        vec!["validation"],
        vec!["options", "relaxation"],
    ] {
        let mut document: serde_json::Value = serde_json::from_str(&json).expect("valid JSON");
        let mut cursor = &mut document;
        for step in &path {
            cursor = &mut cursor[*step];
        }
        cursor["schema_version"] = serde_json::json!(9);
        let mutated = serde_json::to_string(&document).expect("serializable");

        let error = SearchRecord::from_json(mutated.as_bytes())
            .expect_err("a wrongly versioned nested document must be rejected");
        assert_eq!(error.kind, ErrorKind::Document, "{path:?}: {error}");
    }

    // A checkpoint's nested incumbent is checked the same way. The initial
    // checkpoint has none, so one is attached deliberately.
    let mut checkpoint = initial_checkpoint(&discrete, &options()).expect("checkpoint");
    checkpoint.incumbent = record.candidate.clone();
    let json = checkpoint.to_json().expect("serializable");
    assert!(
        optimizer_solver::Checkpoint::from_json(json.as_bytes()).is_ok(),
        "a checkpoint carrying a current-version incumbent parses"
    );

    let mut document: serde_json::Value = serde_json::from_str(&json).expect("valid JSON");
    document["incumbent"]["schema_version"] = serde_json::json!(9);
    let mutated = serde_json::to_string(&document).expect("serializable");
    assert_eq!(
        optimizer_solver::Checkpoint::from_json(mutated.as_bytes())
            .unwrap_err()
            .kind,
        ErrorKind::Document
    );
}

/// Requirement 22: search documents reject positional arrays and unknown fields.
#[test]
fn search_documents_require_strict_objects() {
    let positional = b"[2, 17, null, null, null, 0.0, {}, []]";
    assert!(
        serde_json::from_slice::<SearchOptions>(positional).is_err(),
        "a positional record must be rejected"
    );

    // A complete, currently valid configuration is the only useful base for an
    // unknown-field test. A hand-written literal drifts as soon as a field is
    // added: it would then be rejected for the *missing* field while the
    // assertion still passed, silently ceasing to test unknown-field rejection.
    let valid = serde_json::to_string(&options()).expect("serializable");
    assert!(
        serde_json::from_str::<SearchOptions>(&valid).is_ok(),
        "the base document must be accepted: {valid}"
    );
    let unknown = format!("{},\"surprise\":true}}", &valid[..valid.len() - 1]);
    assert!(
        serde_json::from_str::<SearchOptions>(&unknown).is_err(),
        "an unknown field must be rejected: {unknown}"
    );

    // A missing required field is rejected too, and for its own reason.
    let missing = valid.replace("\"seed\":17,", "");
    assert_ne!(missing, valid, "the seed field must actually be removed");
    assert!(
        serde_json::from_str::<SearchOptions>(&missing).is_err(),
        "a missing required field must be rejected"
    );

    assert!(
        serde_json::from_slice::<SearchOutcome>(b"\"not_an_outcome\"").is_err(),
        "an unknown outcome variant must be rejected"
    );
}

/// Requirement 22: the checkpoint shape is versioned and bound to the model.
#[test]
fn checkpoints_serialize_and_bind_to_the_model() {
    let discrete = model(
        "checkpoint",
        &[(0, Domain::Integer, 0.0, 2.0)],
        &[],
        ObjectiveSense::Maximize,
        0.0,
        &[(0, 1.0)],
    );
    let checkpoint = initial_checkpoint(&discrete, &options()).expect("checkpoint");

    assert_eq!(checkpoint.schema_version, SEARCH_SCHEMA_VERSION);
    assert_eq!(checkpoint.model_id, "checkpoint");
    assert_eq!(
        checkpoint.model_fingerprint,
        discrete.fingerprint().expect("fingerprint"),
        "a checkpoint is bound to exact canonical data, not just an identity"
    );
    assert_eq!(checkpoint.open_nodes.len(), 1, "the root is the frontier");
    assert!(!checkpoint.forfeited);

    let json = checkpoint.to_json().expect("serializable");
    let parsed = optimizer_solver::Checkpoint::from_json(json.as_bytes()).expect("round trip");
    assert_eq!(parsed, checkpoint);

    let bumped = retarget_version(&json, UNSUPPORTED_SCHEMA_VERSION);
    assert_ne!(bumped, json, "the version must actually have been changed");
    assert_eq!(
        optimizer_solver::Checkpoint::from_json(bumped.as_bytes())
            .unwrap_err()
            .kind,
        ErrorKind::Document
    );
}

/// Requirement 14: `proves_completion` is true for exactly the completed
/// outcomes, so a limit can never be read as a finished proof.
#[test]
fn only_completed_outcomes_prove_completion() {
    for outcome in [
        SearchOutcome::ProvenOptimal,
        SearchOutcome::ProvenInfeasible,
        SearchOutcome::UnboundedOrInfeasible,
    ] {
        assert!(outcome.proves_completion(), "{outcome:?}");
    }
    for outcome in [
        SearchOutcome::Feasible,
        SearchOutcome::NodeLimit,
        SearchOutcome::TimeLimit,
        SearchOutcome::OpenNodeLimit,
        SearchOutcome::Interrupted,
        SearchOutcome::NumericalFailure,
        SearchOutcome::BackendFailure,
        SearchOutcome::Unsupported,
    ] {
        assert!(!outcome.proves_completion(), "{outcome:?}");
    }
}

// ---- SPEC-0010 requirements 6, 40 and 41: the recorded device ----

/// A tiny discrete model for the device contracts below, whose optimum is known.
fn device_fixture() -> Model {
    model(
        "device-fixture",
        &[
            (0, Domain::Integer, 0.0, 3.0),
            (1, Domain::Integer, 0.0, 3.0),
        ],
        &[(0, None, Some(3.5), &[(0, 1.0), (1, 1.0)])],
        ObjectiveSense::Maximize,
        0.0,
        &[(0, 1.0), (1, 1.0)],
    )
}

/// Requirement 40: the device is part of the configuration, so it round-trips
/// through a record and is available to whatever re-executes it.
///
/// Recording it in provenance instead would have avoided a schema version, and
/// would also have put it somewhere verification never reads: SPEC-0005 re-runs a
/// search from the embedded configuration alone.
#[test]
fn the_selected_device_round_trips_through_a_record() {
    let fixture = device_fixture();
    let record = run(&fixture, &options());
    assert_eq!(record.options.device, Device::Cpu);

    let text = record.to_json().expect("serialize");
    assert!(text.contains(r#""device": "cpu""#), "{text}");
    let reparsed = SearchRecord::from_json(text.as_bytes()).expect("reparse");
    assert_eq!(reparsed.options.device, Device::Cpu);
}

/// Requirement 6: a configuration naming a device is refused, not run on the CPU.
///
/// This is the case that would be invisible if it were wrong. A search that ran on
/// the CPU while its record said `GPU-...` would verify: verification re-runs from
/// the same configuration, would also run on the CPU, and the two would agree. The
/// agreement would then certify a hardware claim nothing ever checked.
#[test]
fn a_device_this_build_cannot_honour_is_refused_rather_than_run_on_the_cpu() {
    let fixture = device_fixture();
    let mut named = options();
    named.device = Device::Gpu("GPU-dfb2449a-9eff-e868-3597-2c448c9a8e48".into());

    let error = search(
        &fixture,
        &named,
        &ExactBackend::default(),
        &CancellationToken::new(),
    )
    .expect_err("a device this build cannot dispatch to must be refused");
    assert_eq!(error.kind, ErrorKind::Unsupported);
    assert!(
        error.message.contains("GPU-dfb2449a"),
        "the refusal must name the device it refused: {}",
        error.message
    );

    // And the CPU configuration that differs only in this field still succeeds, so
    // the refusal is discriminating rather than a blanket failure.
    let plain = run(&fixture, &options());
    assert_eq!(plain.outcome, SearchOutcome::ProvenOptimal);
}

/// Requirement 41: an earlier configuration version is refused, never migrated.
///
/// Defaulting an absent device to `cpu` would read as harmless. It is not: a
/// version-2 record of a device run and a version-2 record of a CPU run are the
/// same bytes, so a migration would have to invent the fact that distinguishes
/// them.
#[test]
fn an_earlier_search_document_version_is_refused_rather_than_migrated() {
    for version in [1u32, 2, SEARCH_SCHEMA_VERSION + 1] {
        let mut stale = options();
        stale.schema_version = version;
        let error = stale.validate().expect_err("a wrong version is refused");
        assert_eq!(error.kind, ErrorKind::Document, "version {version}");
    }

    // A version-2 document is exactly a version-3 one without the device, which is
    // what makes silently accepting it tempting and wrong.
    let text = serde_json::to_string(&options()).expect("serialize");
    let without_device = text.replace(r#""device":"cpu","#, "").replace(
        &format!(r#""schema_version":{SEARCH_SCHEMA_VERSION}"#),
        r#""schema_version":2"#,
    );
    assert!(
        serde_json::from_str::<SearchOptions>(&without_device).is_err(),
        "a version-2 configuration must not parse as version 3"
    );
}

/// Requirement 2: a device is named by UUID, and nothing else is accepted.
#[test]
fn a_device_is_named_by_uuid_and_nothing_else_parses() {
    assert_eq!(Device::parse("cpu").expect("cpu parses"), Device::Cpu);
    let uuid = "GPU-dfb2449a-9eff-e868-3597-2c448c9a8e48";
    assert_eq!(
        Device::parse(uuid).expect("a uuid parses"),
        Device::Gpu(uuid.to_string())
    );

    for rejected in [
        // An enumeration index, which CUDA_VISIBLE_DEVICES renumbers per process,
        // so a record carrying one could not be re-executed.
        "0",
        "gpu:0",
        // Case matters: the driver prints an uppercase prefix and accepting both
        // would make two spellings of one device compare unequal in a record.
        "gpu-dfb2449a",
        "GPU-",
        "",
        "CPU",
        "cuda",
        // A UUID with a character the driver never emits.
        "GPU-dfb2449a_9eff",
    ] {
        assert!(
            Device::parse(rejected).is_err(),
            "{rejected:?} must be refused"
        );
    }
}
