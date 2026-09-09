//! The owned branch-and-bound executive under SPEC-0003.
//!
//! The executive owns all search state. The backend is used only as a
//! relaxation service, and the single most important rule here is requirement
//! 5: a relaxation objective becomes a dual bound **only** when that relaxation
//! reported [`Termination::Optimal`]. Any other termination leaves the bound
//! unavailable, forbids pruning that node by bound, and permanently forfeits
//! the proof claim. That is what stops a timeout inside a child solve from
//! silently discarding an optimal solution.

use std::time::Instant;

use optimizer_core::{
    Backend, CancellationToken, Candidate, Domain, ErrorKind, Model, ObjectiveSense, Termination,
    ValidationError, ValidationReport,
};

use crate::node::{self, Node};
use crate::search::{
    Checkpoint, CheckpointNode, SEARCH_SCHEMA_VERSION, SearchOptions, SearchOutcome, SearchRecord,
    improves, is_better_bound,
};

/// Mutable search state, owned privately by one [`search`] call.
struct Executive<'a> {
    model: &'a Model,
    options: SearchOptions,
    sense: ObjectiveSense,
    started: Instant,

    /// Open frontier, kept in deterministic order by [`Self::select`].
    open: Vec<Node>,
    next_node_id: u64,

    incumbent: Option<Candidate>,
    incumbent_objective: Option<f64>,
    incumbent_validation: Option<ValidationReport>,

    /// Best valid dual bound proven over closed nodes.
    dual_bound: Option<f64>,
    /// Permanent loss of the proof claim; never cleared once set.
    forfeited: bool,

    nodes_explored: u64,
    nodes_pruned_infeasible: u64,
    nodes_pruned_bound: u64,
    relaxations_solved: u64,
    warnings: Vec<String>,
    backend_version: Option<String>,
}

impl<'a> Executive<'a> {
    fn new(model: &'a Model, options: SearchOptions) -> Self {
        Self {
            model,
            sense: model.document().objective.sense,
            options,
            started: Instant::now(),
            open: vec![Node::root()],
            next_node_id: 1,
            incumbent: None,
            incumbent_objective: None,
            incumbent_validation: None,
            dual_bound: None,
            forfeited: false,
            nodes_explored: 0,
            nodes_pruned_infeasible: 0,
            nodes_pruned_bound: 0,
            relaxations_solved: 0,
            warnings: Vec::new(),
            backend_version: None,
        }
    }

    /// Record the permanent loss of the proof claim, with its reason.
    fn forfeit(&mut self, reason: &str) {
        if !self.forfeited {
            self.forfeited = true;
            self.warnings
                .push(format!("proof claim forfeited: {reason}"));
        }
    }

    /// Select the next node: best parent bound first, ties by node identity.
    ///
    /// This is a total order over a `Vec`, never iteration order of an
    /// unordered collection, so two identical searches explore identically.
    fn select(&mut self) -> Option<Node> {
        let sense = self.sense;
        let best = self
            .open
            .iter()
            .enumerate()
            .min_by(|(_, left), (_, right)| {
                let key = |node: &Node| match (node.parent_bound, sense) {
                    // An absent parent bound sorts last, behind every proven bound.
                    (None, _) => f64::INFINITY,
                    (Some(bound), ObjectiveSense::Minimize) => bound,
                    (Some(bound), ObjectiveSense::Maximize) => -bound,
                };
                key(left)
                    .partial_cmp(&key(right))
                    .unwrap_or(std::cmp::Ordering::Equal)
                    .then_with(|| left.node_id.cmp(&right.node_id))
            })
            .map(|(index, _)| index)?;
        Some(self.open.remove(best))
    }

    /// Whether a valid bound permits pruning against the current incumbent.
    ///
    /// Requirement 8: a node is pruned only when its proven bound is not better
    /// than the incumbent by more than the improvement tolerance, and only
    /// against a validated incumbent.
    fn prunes(&self, bound: f64) -> bool {
        self.incumbent_objective.is_some_and(|incumbent| {
            !improves(
                bound,
                incumbent,
                self.sense,
                self.options.improvement_tolerance,
            )
        })
    }

    /// Accept a validated candidate as the incumbent when it improves.
    fn offer(&mut self, candidate: Candidate, validation: ValidationReport) {
        let objective = validation.objective;
        let better = self.incumbent_objective.is_none_or(|incumbent| {
            improves(
                objective,
                incumbent,
                self.sense,
                self.options.improvement_tolerance,
            )
        });
        if better {
            self.incumbent = Some(candidate);
            self.incumbent_objective = Some(objective);
            self.incumbent_validation = Some(validation);
        }
    }

    /// Merge a proven node bound into the global dual bound.
    ///
    /// The global bound is the most pessimistic of the proven node bounds still
    /// relevant, so it is only ever weakened as the search proceeds.
    fn observe_bound(&mut self, bound: f64) {
        self.dual_bound = Some(match self.dual_bound {
            Some(existing) if is_better_bound(existing, bound, self.sense) => existing,
            _ => bound,
        });
    }

    /// Whether a budget stopped the search, as its own outcome.
    fn exhausted(&self) -> Option<SearchOutcome> {
        if self
            .options
            .node_limit
            .is_some_and(|limit| self.nodes_explored >= limit)
        {
            return Some(SearchOutcome::NodeLimit);
        }
        if self.options.time_limit_ms.is_some_and(|limit| {
            u64::try_from(self.started.elapsed().as_millis()).unwrap_or(u64::MAX) >= limit
        }) {
            return Some(SearchOutcome::TimeLimit);
        }
        if self
            .options
            .open_node_limit
            .is_some_and(|limit| self.open.len() as u64 > limit)
        {
            return Some(SearchOutcome::OpenNodeLimit);
        }
        None
    }

    /// Snapshot the unfinished search. Restart is not implemented in C2.
    fn checkpoint(&self) -> Result<Checkpoint, ValidationError> {
        Ok(Checkpoint {
            schema_version: SEARCH_SCHEMA_VERSION,
            model_id: self.model.document().model_id.clone(),
            model_fingerprint: self.model.fingerprint()?,
            open_nodes: self
                .open
                .iter()
                .map(|node| CheckpointNode {
                    node_id: node.node_id,
                    parent_bound: node.parent_bound,
                    restrictions: node.restrictions.clone(),
                })
                .collect(),
            incumbent: self.incumbent.clone(),
            incumbent_objective: self.incumbent_objective,
            dual_bound: self.dual_bound,
            nodes_explored: self.nodes_explored,
            forfeited: self.forfeited,
        })
    }

    /// Assemble the final record.
    ///
    /// A forfeited search cannot report a completed proof, whatever the loop
    /// concluded; that downgrade happens here so there is exactly one place it
    /// can be got wrong.
    fn finish(mut self, outcome: SearchOutcome) -> SearchRecord {
        let outcome = if self.forfeited && outcome.proves_completion() {
            if self.incumbent.is_some() {
                SearchOutcome::Feasible
            } else {
                SearchOutcome::NumericalFailure
            }
        } else {
            outcome
        };

        // A proof of infeasibility must not carry an incumbent, and an
        // unbounded model has no validated incumbent to report.
        let publishes_incumbent = !matches!(
            outcome,
            SearchOutcome::ProvenInfeasible
                | SearchOutcome::UnboundedOrInfeasible
                | SearchOutcome::BackendFailure
                | SearchOutcome::NumericalFailure
        );
        let objective = publishes_incumbent
            .then_some(self.incumbent_objective)
            .flatten()
            .filter(|value| value.is_finite());
        let dual_bound = match outcome {
            // Only a completed proof may present the incumbent as its own bound.
            SearchOutcome::ProvenOptimal => objective,
            _ => self.dual_bound.filter(|value| value.is_finite()),
        };
        let gap = match (objective, dual_bound) {
            (Some(objective), Some(bound)) => {
                let denominator = objective.abs().max(1.0);
                Some((objective - bound).abs() / denominator).filter(|value| value.is_finite())
            }
            _ => None,
        };

        SearchRecord {
            schema_version: SEARCH_SCHEMA_VERSION,
            model_id: self.model.document().model_id.clone(),
            backend: crate::RELAXATION_BACKEND.to_string(),
            backend_version: self.backend_version.take().unwrap_or_default(),
            outcome,
            objective,
            dual_bound,
            gap,
            candidate: publishes_incumbent
                .then(|| self.incumbent.clone())
                .flatten(),
            validation: publishes_incumbent
                .then(|| self.incumbent_validation.clone())
                .flatten(),
            nodes_explored: self.nodes_explored,
            nodes_pruned_infeasible: self.nodes_pruned_infeasible,
            nodes_pruned_bound: self.nodes_pruned_bound,
            open_nodes_remaining: self.open.len() as u64,
            relaxations_solved: self.relaxations_solved,
            forfeited: self.forfeited,
            warnings: self.warnings,
            elapsed_ms: u64::try_from(self.started.elapsed().as_millis()).unwrap_or(u64::MAX),
            options: self.options,
        }
    }
}

/// Prove optimality of an original model by owned branch and bound.
///
/// The backend is used only to solve node relaxations. Cancellation is
/// cooperative and is propagated into every relaxation; a pre-cancelled search
/// dispatches none.
///
/// # Errors
///
/// Returns a categorized [`ValidationError`] for invalid configuration or for a
/// branch that cannot be represented. Search outcomes, including backend and
/// numerical failures, are reported in the record rather than as errors.
pub fn search(
    model: &Model,
    options: &SearchOptions,
    backend: &dyn Backend,
    cancel: &CancellationToken,
) -> Result<SearchRecord, ValidationError> {
    let options = options.validate()?;
    let mut state = Executive::new(model, options);

    // Requirement 19: a pre-cancelled search performs no backend work.
    if cancel.is_cancelled() {
        state.open.clear();
        return Ok(state.finish(SearchOutcome::Interrupted));
    }

    let discrete = model
        .document()
        .variables
        .iter()
        .any(|variable| variable.domain != Domain::Continuous);

    let outcome = loop {
        if cancel.is_cancelled() {
            break SearchOutcome::Interrupted;
        }
        if let Some(outcome) = state.exhausted() {
            break outcome;
        }
        let Some(node) = state.select() else {
            // Requirement 14: an exhausted tree is a completed proof.
            break if state.incumbent.is_some() {
                SearchOutcome::ProvenOptimal
            } else {
                SearchOutcome::ProvenInfeasible
            };
        };

        // An empty domain closes the node without dispatching a relaxation.
        let Some(relaxed) = node::relaxation(model, &node)? else {
            state.nodes_pruned_infeasible += 1;
            continue;
        };

        // Inherit the parent's proven bound: if it already cannot beat the
        // incumbent, the whole subtree is closed without a solve.
        if let Some(parent_bound) = node.parent_bound
            && state.prunes(parent_bound)
        {
            state.nodes_pruned_bound += 1;
            continue;
        }

        state.nodes_explored += 1;
        state.relaxations_solved += 1;
        let record = backend.solve(&relaxed, &state.options.relaxation, cancel, None)?;
        if state.backend_version.is_none() {
            state.backend_version = Some(record.backend_version.clone());
        }

        match record.termination {
            // Requirement 7: only a proven infeasible relaxation closes a node.
            Termination::Infeasible => {
                state.nodes_pruned_infeasible += 1;
                continue;
            }
            Termination::Unbounded | Termination::UnboundedOrInfeasible => {
                break SearchOutcome::UnboundedOrInfeasible;
            }
            Termination::BackendFailure => {
                state.forfeit("relaxation reported a backend failure");
                break SearchOutcome::BackendFailure;
            }
            Termination::NumericalFailure => {
                state.forfeit("relaxation reported a numerical failure");
                break SearchOutcome::NumericalFailure;
            }
            Termination::Unsupported => {
                state.forfeit("relaxation reported an unsupported request");
                break SearchOutcome::Unsupported;
            }
            Termination::Interrupted => {
                state.forfeit("relaxation was interrupted");
                break SearchOutcome::Interrupted;
            }
            // Requirement 5 and 6: a limited relaxation yields no usable bound,
            // so this node can neither be pruned nor left claiming a proof.
            Termination::TimeLimit => {
                state.forfeit("relaxation reached its time limit");
                break SearchOutcome::TimeLimit;
            }
            Termination::IterationLimit | Termination::NodeLimit => {
                state.forfeit("relaxation reached an iteration or node limit");
                break SearchOutcome::NodeLimit;
            }
            Termination::Feasible => {
                // A relaxation that did not prove optimality gives no bound.
                state.forfeit("relaxation did not prove optimality");
                break SearchOutcome::Feasible;
            }
            Termination::Optimal => {}
        }

        // Only here is the relaxation objective a valid dual bound.
        let Some(bound) = record.objective else {
            state.forfeit("proven relaxation reported no objective");
            break SearchOutcome::NumericalFailure;
        };
        state.observe_bound(bound);

        if state.prunes(bound) {
            state.nodes_pruned_bound += 1;
            continue;
        }

        let Some(candidate) = record.candidate else {
            state.forfeit("proven relaxation reported no candidate");
            break SearchOutcome::NumericalFailure;
        };

        // Never trust the backend to have respected the node it was handed. A
        // solution outside this node's own bounds is inconsistent output, and
        // branching on it would not tighten the domain, so the search could
        // regenerate the same child forever. Checking here both rejects the bad
        // output and guarantees that every branch strictly shrinks a finite
        // integer box, which is what makes the search terminate.
        match relaxed.evaluate(&candidate, state.options.relaxation.tolerances) {
            Ok(report) if report.feasible => {}
            _ => {
                state.forfeit("relaxation solution violates the node it was solved for");
                break SearchOutcome::NumericalFailure;
            }
        }

        // A continuous model has no branching decision to make.
        if !discrete {
            let validation = model.evaluate(&candidate, state.options.relaxation.tolerances)?;
            if !validation.feasible {
                state.forfeit("relaxation solution violates the original model");
                break SearchOutcome::NumericalFailure;
            }
            state.offer(candidate, validation);
            break SearchOutcome::ProvenOptimal;
        }

        match fractional(
            model,
            &candidate,
            state.options.relaxation.tolerances.integrality,
        )? {
            // Integral within tolerance: a candidate, not a branching point.
            None => {
                // Requirement 12: validate against the original model, which
                // still carries the integrality the relaxation dropped.
                let validation = model.evaluate(&candidate, state.options.relaxation.tolerances)?;
                if !validation.feasible {
                    state.forfeit("relaxation solution violates the original model");
                    break SearchOutcome::NumericalFailure;
                }
                state.offer(candidate, validation);
            }
            Some((variable_id, value)) => {
                let lower = node::branch_bound(value.ceil(), variable_id)?;
                let upper = node::branch_bound(value.floor(), variable_id)?;
                // Requirement 10: the two children cover the node's entire
                // discrete feasible set, so no solution is lost.
                let left = node.child(
                    state.next_node_id,
                    Some(bound),
                    variable_id,
                    None,
                    Some(upper),
                );
                let right = node.child(
                    state.next_node_id + 1,
                    Some(bound),
                    variable_id,
                    Some(lower),
                    None,
                );
                state.next_node_id += 2;
                for child in [left, right] {
                    if node::is_empty(model, &child) {
                        state.nodes_pruned_infeasible += 1;
                    } else {
                        state.open.push(child);
                    }
                }
            }
        }
    };

    Ok(state.finish(outcome))
}

/// Snapshot an unfinished search's shape without restarting it.
///
/// This exists so the checkpoint shape is exercised and serializable in C2.
/// Restart is deliberately unimplemented; no entry point consumes a checkpoint.
///
/// # Errors
///
/// Returns a categorized [`ValidationError`] when the model cannot be
/// fingerprinted.
pub fn initial_checkpoint(
    model: &Model,
    options: &SearchOptions,
) -> Result<Checkpoint, ValidationError> {
    Executive::new(model, options.validate()?).checkpoint()
}

/// The branching variable: lowest original ID whose value is not integral.
///
/// Requirement 9: the same integrality tolerance decides both acceptance and
/// whether a variable must be branched on, so the two cannot disagree.
fn fractional(
    model: &Model,
    candidate: &Candidate,
    integrality: f64,
) -> Result<Option<(u32, f64)>, ValidationError> {
    for variable in &model.document().variables {
        if variable.domain == Domain::Continuous {
            continue;
        }
        let assignment = candidate
            .values
            .binary_search_by_key(&variable.id, |value| value.variable_id)
            .map(|index| &candidate.values[index])
            .map_err(|_| {
                ValidationError::new(
                    ErrorKind::Candidate,
                    format!("relaxation omitted variable {}", variable.id),
                )
            })?;
        let value = assignment.value;
        if !value.is_finite() || value.abs() > node::DISCRETE_MAGNITUDE_LIMIT {
            return Err(ValidationError::new(
                ErrorKind::Numerical,
                format!("variable {}: discrete magnitude exceeds 2^53", variable.id),
            ));
        }
        let distance = match variable.domain {
            Domain::Binary => value.abs().min((value - 1.0).abs()),
            _ => (value - value.round()).abs(),
        };
        if distance > integrality {
            return Ok(Some((variable.id, value)));
        }
    }
    Ok(None)
}
