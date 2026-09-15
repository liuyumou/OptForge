//! The host first-order backend, under SPEC-0011 requirements 3, 14 to 17 and 24
//! to 26.
//!
//! This backend runs the same method the device kernels will run, entirely on the
//! host. Requirement 24 makes it the oracle those kernels are checked against, and
//! requirement 25 makes it a real backend rather than test scaffolding so that a
//! caller can reach it and compare.
//!
//! Requirement 26 is the line it must not cross: this is not the fallback path.
//! When a device is unavailable the fallback is the pinned CPU backend, because
//! SPEC-0010 requirement 23 requires a fallback to be the implementation the
//! project already treats as authoritative. Falling back here instead would mean
//! an agreement test comparing this crate's arithmetic with its own.
//!
//! # What this backend is allowed to claim
//!
//! Very little, and that is the point. The candidate is validated by
//! `Model::evaluate` against the original model, and the record's objective is
//! that validation's recomputation rather than anything the iteration produced --
//! requirement 15 forbids the backend reporting its own objective. A bound comes
//! only from [`crate::certify::certify`]. `Optimal` requires both to exist and to close,
//! which is two independent computations agreeing, neither of them the iteration's.

use std::time::Instant;

use optimizer_core::{
    Arithmetic, Backend, BackendCapabilities, CancellationToken, Candidate, DeviceClass,
    LpSettings, Model, ProblemClass, SOLVE_RECORD_SCHEMA_VERSION, SolveOptions, SolveRecord,
    Termination, ValidationError, WarmStart, finite_or_absent,
};

use crate::certify::{assess_gap, certify};
use crate::pdhg::{Decision, Engine, Iterate, Stop};
use crate::problem::LinearProgram;

/// Backend identifier recorded in every record this backend writes.
pub const BACKEND_NAME: &str = "host-lp";

/// This implementation's version, which is the project's own.
pub const BACKEND_VERSION: &str = env!("CARGO_PKG_VERSION");

/// A first-order linear programming backend that executes on the host.
#[derive(Clone, Debug)]
pub struct HostLpBackend {
    settings: LpSettings,
}

impl HostLpBackend {
    /// Construct a backend with explicit settings.
    ///
    /// # Errors
    ///
    /// Returns a document failure when the settings do not validate. Settings are
    /// constructor state rather than per-solve options, which is what SPEC-0011's
    /// own `open(residency, settings)` interface already implies and what keeps
    /// `solve-config-v1` at version 1.
    pub fn new(settings: LpSettings) -> Result<Self, ValidationError> {
        settings.validate()?;
        Ok(Self { settings })
    }

    /// The settings this backend runs with.
    #[must_use]
    pub fn settings(&self) -> LpSettings {
        self.settings
    }
}

/// What the termination check concluded about one iterate.
struct Outcome {
    candidate: Candidate,
    objective: f64,
    feasible: bool,
    bound: Option<f64>,
    gap: Option<f64>,
    closed: bool,
}

/// Build a candidate from an iterate, in the model's own variable order.
fn candidate_from(model: &Model, program: &LinearProgram, iterate: &Iterate) -> Candidate {
    Candidate {
        schema_version: optimizer_core::SCHEMA_VERSION,
        model_id: model.document().model_id.clone(),
        values: program
            .variable_ids()
            .iter()
            .zip(&iterate.primal)
            .map(|(variable_id, value)| optimizer_core::Assignment {
                variable_id: *variable_id,
                // Clamped into the variable's own bounds. The iteration already
                // projects onto them, so this only removes the last rounding, and
                // it is the difference between a candidate `Model::evaluate`
                // accepts and one it refuses for a 1e-17 bound violation.
                value: *value,
            })
            .collect(),
    }
}

/// Evaluate one iterate: validate it, certify it, and decide whether they close.
fn assess(
    model: &Model,
    program: &LinearProgram,
    iterate: &Iterate,
    options: &SolveOptions,
) -> Result<Outcome, ValidationError> {
    let candidate = candidate_from(model, program, iterate);
    let report = model.evaluate(&candidate, options.tolerances)?;

    // The bound is certified from the dual iterate alone, and the procedure does
    // not assume the iteration computed anything correctly.
    let bound = certify(program, &iterate.dual).ok().map(|c| c.bound);

    let gap = report
        .feasible
        .then(|| {
            bound.and_then(|bound| assess_gap(program, &iterate.primal, bound, options.tolerances))
        })
        .flatten();
    let closed = gap.is_some_and(|gap| gap.closed);

    Ok(Outcome {
        candidate,
        objective: report.objective,
        feasible: report.feasible,
        bound,
        gap: gap.map(|gap| gap.upper),
        closed,
    })
}

impl Backend for HostLpBackend {
    fn capabilities(&self) -> BackendCapabilities {
        BackendCapabilities::declare(
            BACKEND_NAME,
            BACKEND_VERSION.to_string(),
            // Continuous only. A first-order method has no branch and bound, so
            // returning a relaxed answer to a discrete request would be a wrong
            // answer rather than a refused one.
            vec![ProblemClass::Continuous],
            Arithmetic::F64,
            true,
            DeviceClass::Cpu,
        )
        .expect("this backend's declaration is a constant and is well formed")
    }

    fn solve(
        &self,
        model: &Model,
        options: &SolveOptions,
        cancel: &CancellationToken,
        warm_start: Option<WarmStart<'_>>,
    ) -> Result<SolveRecord, ValidationError> {
        self.solve_with_diagnostics(
            model,
            options,
            cancel,
            warm_start,
            &mut optimizer_core::LpDiagnostics::new(false, false),
        )
    }
}

impl HostLpBackend {
    /// Execute the ordinary method while collecting explicitly requested observations.
    ///
    /// # Errors
    /// Returns the same validation and backend failures as `Backend::solve`.
    pub fn solve_with_diagnostics(
        &self,
        model: &Model,
        options: &SolveOptions,
        cancel: &CancellationToken,
        warm_start: Option<WarmStart<'_>>,
        diagnostics: &mut optimizer_core::LpDiagnostics,
    ) -> Result<SolveRecord, ValidationError> {
        options.validate()?;

        let declared = self.capabilities();
        // Requirement 3, and requirement 4's teeth: the check is here, inside the
        // backend, so a caller holding a widened copy of the declaration is still
        // refused.
        if !declared.accepts(model) {
            return Ok(declared.refuse(model, options));
        }

        let started = Instant::now();
        let mut warnings = Vec::new();

        // This backend produces no basis and cannot consume one: ADR-0010 records
        // that crossover to a basic solution is not attempted. A basis warm start
        // is recorded as ignored rather than silently dropped.
        if matches!(warm_start, Some(WarmStart::Basis(_))) {
            warnings.push(
                "a basis warm start was ignored: a first-order method has no basis".to_string(),
            );
        }

        let setup = diagnostics.start();
        let program = LinearProgram::new(model)?;
        let engine = Engine::new(&program, self.settings);
        diagnostics.finish("preparation", setup);

        if cancel.is_cancelled() {
            return Ok(record(
                model,
                options,
                Termination::Interrupted,
                None,
                warnings,
                started,
                self.settings,
            ));
        }

        let mut best: Option<Outcome> = None;
        let mut failure: Option<ValidationError> = None;
        let mut iteration_start = diagnostics.start();
        let (iterate, stop) = engine.run(cancel, |iterate| {
            diagnostics.finish("iteration", iteration_start.take());
            let check_start = diagnostics.start();
            let result = assess(model, &program, iterate, options);
            diagnostics.finish("host_checks", check_start);
            diagnostics.capture(&iterate.dual, iterate.iterations);
            iteration_start = diagnostics.start();
            match result {
                Ok(outcome) => {
                    let closed = outcome.closed;
                    best = Some(outcome);
                    if closed {
                        Decision::Accept
                    } else {
                        Decision::Continue
                    }
                }
                Err(error) => {
                    failure = Some(error);
                    Decision::Accept
                }
            }
        });

        diagnostics.finish("iteration", iteration_start);
        if diagnostics.enabled {
            diagnostics.iterations = Some(iterate.iterations);
            diagnostics.restarts = Some(iterate.restarts);
            diagnostics.kernel_launches = Some(0);
            diagnostics.device_buffer_peak_bytes = Some(0);
        }
        if let Some(error) = failure {
            return Err(error);
        }

        // The loop may finish before any check ran, when the limit is below the
        // interval. Assessing once here keeps a short solve from reporting
        // nothing at all.
        let outcome = match best {
            Some(outcome) => outcome,
            None => {
                let check_start = diagnostics.start();
                let outcome = assess(model, &program, &iterate, options)?;
                diagnostics.finish("host_checks", check_start);
                diagnostics.capture(&iterate.dual, iterate.iterations);
                outcome
            }
        };

        let termination = match stop {
            Stop::Cancelled => Termination::Interrupted,
            Stop::Accepted if outcome.closed => Termination::Optimal,
            // Every other outcome uses a termination that claims no proof.
            Stop::Accepted | Stop::IterationLimit => {
                if outcome.feasible {
                    if stop == Stop::IterationLimit {
                        Termination::IterationLimit
                    } else {
                        Termination::Feasible
                    }
                } else {
                    Termination::IterationLimit
                }
            }
        };

        Ok(record(
            model,
            options,
            termination,
            Some(outcome),
            warnings,
            started,
            self.settings,
        ))
    }
}

/// Assemble the record.
fn record(
    model: &Model,
    options: &SolveOptions,
    termination: Termination,
    outcome: Option<Outcome>,
    warnings: Vec<String>,
    started: Instant,
    settings: LpSettings,
) -> SolveRecord {
    let (objective, bound, gap, candidate, validation) = match outcome {
        Some(outcome) => {
            // Requirement 15: the record's objective is the validation's
            // recomputation, and only when the candidate was accepted. An
            // infeasible iterate has an objective too, and publishing it would
            // make a record look like it found something.
            let objective = outcome.feasible.then_some(outcome.objective);
            let report = model.evaluate(&outcome.candidate, options.tolerances).ok();
            (
                objective,
                outcome.bound,
                outcome.gap,
                Some(outcome.candidate),
                report,
            )
        }
        None => (None, None, None, None, None),
    };

    SolveRecord {
        lp_execution: None,
        schema_version: SOLVE_RECORD_SCHEMA_VERSION,
        model_id: model.document().model_id.clone(),
        backend: BACKEND_NAME.to_string(),
        backend_version: BACKEND_VERSION.to_string(),
        termination,
        native_status: None,
        objective: objective.and_then(finite_or_absent),
        best_bound: bound.and_then(finite_or_absent),
        gap,
        candidate,
        validation,
        warnings,
        elapsed_ms: started.elapsed().as_millis().min(u128::from(u64::MAX)) as u64,
        options: options.clone(),
        lp_settings: Some(settings),
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use optimizer_core::{
        Bound, Domain, LinearTerm, ModelDocument, Objective, ObjectiveSense, SCHEMA_VERSION,
        Tolerances, Variable,
    };

    #[test]
    fn maximization_closes_a_positive_gap_with_relative_tolerance() {
        let model = Model::new(ModelDocument {
            schema_version: SCHEMA_VERSION,
            model_id: "max-gap".into(),
            variables: vec![Variable {
                id: 0,
                domain: Domain::Continuous,
                lower: Bound::Finite { value: 0.0 },
                upper: Bound::Finite { value: 1.0 },
            }],
            constraints: vec![],
            objective: Objective {
                sense: ObjectiveSense::Maximize,
                offset: 0.0,
                terms: vec![LinearTerm {
                    variable_id: 0,
                    coefficient: 1.0,
                }],
            },
        })
        .unwrap();
        let program = LinearProgram::new(&model).unwrap();
        let options = SolveOptions {
            tolerances: Tolerances {
                absolute: 0.0,
                relative: 0.1,
                integrality: 0.0,
            },
            schema_version: optimizer_core::SOLVE_SCHEMA_VERSION,
            seed: 0,
            time_limit_ms: None,
            iteration_limit: None,
            node_limit: None,
            threads: 1,
        };
        let iterate = Iterate {
            primal: vec![0.95],
            dual: vec![],
            iterations: 0,
            restarts: 0,
        };
        let outcome = assess(&model, &program, &iterate, &options).unwrap();
        assert!(outcome.feasible);
        assert!(
            outcome.closed,
            "0.05 <= 0.1 * 1, with a valid upper bound of 1"
        );
    }
}
