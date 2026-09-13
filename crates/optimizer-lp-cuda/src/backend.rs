//! The device first-order backend, under SPEC-0011 and ADR-0010.
//!
//! The device proposes; the host certifies. This backend runs the iteration's
//! kernels on a device SPEC-0010 selected and leased, and then hands the iterate to
//! exactly the same two host-side computations the host backend uses: `Model::evaluate`
//! decides feasibility and recomputes the objective, and `optimizer_lp::certify`
//! constructs any bound from the original model's own coefficients.
//!
//! Neither of those reads anything the device computed except the iterate itself,
//! and the certification is valid for an arbitrary vector. So a wrong kernel here
//! produces a refused candidate or a weak bound, never a wrong answer. That is the
//! whole of ADR-0010's safety argument, and it is why this module is allowed to be
//! the least trusted code in the project.
//!
//! # What this backend does not do
//!
//! It does not fall back. SPEC-0010 requirement 24 makes an availability failure
//! fall back to the CPU, and SPEC-0010 requirement 23 requires that CPU path to be
//! the implementation the project already treats as authoritative -- the pinned
//! HiGHS adapter, not the host first-order engine, which requirement 26 keeps as a
//! differential oracle. Choosing the fallback is therefore a caller's decision made
//! above this type, where both backends are in scope; a backend that silently
//! answered with a different implementation would write a record naming itself for
//! work it did not do.

use std::rc::Rc;
use std::time::Instant;

use optimizer_core::{
    Arithmetic, Backend, BackendCapabilities, CancellationToken, Candidate, DeviceClass,
    LpSettings, Model, ProblemClass, SOLVE_RECORD_SCHEMA_VERSION, SolveOptions, SolveRecord,
    Termination, ValidationError, WarmStart, finite_or_absent,
};
use optimizer_cuda_sys::{Context, DeviceError};
use optimizer_lp::certify::certify;
use optimizer_lp::pdhg::Engine;
use optimizer_lp::problem::LinearProgram;

use crate::residency::{LpResidency, code_object_path};

/// Backend identifier recorded in every record this backend writes.
pub const BACKEND_NAME: &str = "cuda-lp";

/// This implementation's version, which is the project's own.
pub const BACKEND_VERSION: &str = env!("CARGO_PKG_VERSION");

/// A first-order linear programming backend whose kernels run on a device.
pub struct CudaLpBackend {
    context: Rc<Context>,
    settings: LpSettings,
    code_object: std::path::PathBuf,
}

impl CudaLpBackend {
    /// Construct a backend against a device SPEC-0010 selected and leased.
    ///
    /// The context carries the lease: SPEC-0010 requirement 7 requires the lease to
    /// be held for the whole lifetime of a context, and requirement 9 forbids
    /// creating one without it, so taking a context here is taking a leased device.
    ///
    /// # Errors
    ///
    /// Returns a document failure when the settings do not validate.
    pub fn open(context: Rc<Context>, settings: LpSettings) -> Result<Self, ValidationError> {
        Self::open_with_code_object(context, settings, code_object_path())
    }

    /// Construct a backend against an explicit code object.
    ///
    /// Exists so an availability failure can be provoked without mutating a
    /// process-wide environment variable, which a parallel test harness would make
    /// racy. Requirement 20's fallback has to be exercised by a test that can
    /// actually cause the failure, and this is the narrowest way to cause one.
    ///
    /// # Errors
    ///
    /// Returns a document failure when the settings do not validate.
    pub fn open_with_code_object(
        context: Rc<Context>,
        settings: LpSettings,
        code_object: std::path::PathBuf,
    ) -> Result<Self, ValidationError> {
        settings.validate()?;
        Ok(Self {
            context,
            settings,
            code_object,
        })
    }

    /// The settings this backend runs with.
    #[must_use]
    pub fn settings(&self) -> LpSettings {
        self.settings
    }

    /// The device this backend is bound to, for a record that must name it.
    #[must_use]
    pub fn device(&self) -> &optimizer_cuda_sys::DeviceInfo {
        self.context.device()
    }

    /// Run the iteration on the device, consulting `check` every check interval.
    ///
    /// The interval is requirement 10's real parameter rather than a formality:
    /// each one costs a synchronization and two transfers, because the host cannot
    /// evaluate a candidate or certify a bound without the iterate. Running to the
    /// limit and assessing once would be cheaper and would make the interval a
    /// recorded number that changed nothing, which is exactly what requirement 10
    /// forbids hiding.
    fn iterate(
        &self,
        program: &LinearProgram,
        cancel: &CancellationToken,
        mut check: impl FnMut(&[f64], &[f64]) -> bool,
    ) -> Result<(Vec<f64>, Vec<f64>, u64), DeviceError> {
        // The host engine owns the scaling and the step size, and the device
        // uploads exactly what it computed. Recomputing the scaling here would
        // create a second thing that must agree with the first, and the host engine
        // exists precisely to be the one the device is checked against.
        let engine = Engine::new(program, self.settings);
        let (row_values, column_values) = engine.scaled_matrix();
        let residency = LpResidency::open(
            Rc::clone(&self.context),
            program,
            row_values,
            column_values,
            engine.scaled_objective(),
            engine.scaled_row_bounds(),
            engine.scaled_column_bounds(),
            &self.code_object,
        )?;

        let mut x = engine.start_primal();
        let mut y = engine.start_dual();
        let anchor_x = x.clone();
        let anchor_y = y.clone();
        let mut done = 0u64;

        while done < self.settings.iteration_limit {
            let remaining = self.settings.iteration_limit - done;
            let chunk = self.settings.check_interval.min(remaining);
            // `done` is passed as the Halpern iteration count, so restarting the
            // launch loop at each interval does not restart the coefficient
            // sequence. Getting that wrong would make the interval change the
            // answer, which is the one thing a termination check must not do.
            residency.advance(
                &mut x,
                &mut y,
                &anchor_x,
                &anchor_y,
                done,
                chunk,
                engine.step(),
                1.0,
                cancel,
            )?;
            done += chunk;

            let primal = engine.unscale_primal(&x);
            let dual = engine.unscale_dual(&y);
            if check(&primal, &dual) {
                return Ok((primal, dual, done));
            }
        }

        Ok((engine.unscale_primal(&x), engine.unscale_dual(&y), done))
    }
}

impl Backend for CudaLpBackend {
    fn capabilities(&self) -> BackendCapabilities {
        BackendCapabilities::declare(
            BACKEND_NAME,
            BACKEND_VERSION.to_string(),
            vec![ProblemClass::Continuous],
            Arithmetic::F64,
            true,
            DeviceClass::Gpu,
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
        options.validate()?;

        let declared = self.capabilities();
        if !declared.accepts(model) {
            return Ok(declared.refuse(model, options));
        }

        let started = Instant::now();
        let mut warnings = Vec::new();
        if matches!(warm_start, Some(WarmStart::Basis(_))) {
            warnings.push(
                "a basis warm start was ignored: a first-order method has no basis".to_string(),
            );
        }

        let program = LinearProgram::new(model)?;
        // Assessment is the host's, exactly as it is for the host backend: the
        // candidate is validated against the original model and any bound is
        // certified from the model's own coefficients. Nothing the device computed
        // is consulted except the iterate itself.
        let assess = |primal: &[f64],
                      dual: &[f64]|
         -> Option<(Candidate, f64, bool, Option<f64>, bool)> {
            let candidate = Candidate {
                schema_version: optimizer_core::SCHEMA_VERSION,
                model_id: model.document().model_id.clone(),
                values: program
                    .variable_ids()
                    .iter()
                    .zip(primal)
                    .map(|(variable_id, value)| optimizer_core::Assignment {
                        variable_id: *variable_id,
                        value: *value,
                    })
                    .collect(),
            };
            let report = model.evaluate(&candidate, options.tolerances).ok()?;
            let bound = certify(&program, dual).ok().map(|c| c.bound);
            let closed = match (report.feasible, bound) {
                (true, Some(bound)) => {
                    let gap = report.objective - bound;
                    let scale = report.objective.abs().max(bound.abs());
                    gap >= -options.tolerances.absolute
                        && gap <= options.tolerances.absolute + options.tolerances.relative * scale
                }
                _ => false,
            };
            Some((candidate, report.objective, report.feasible, bound, closed))
        };

        let mut closed_early = false;
        let (primal, dual, iterations) = match self.iterate(&program, cancel, |primal, dual| {
            let stop = assess(primal, dual).is_some_and(|(_, _, _, _, closed)| closed);
            closed_early |= stop;
            stop
        }) {
            Ok(iterate) => iterate,
            Err(DeviceError::Cancelled) => {
                return Ok(bare(
                    model,
                    options,
                    Termination::Interrupted,
                    warnings,
                    started,
                    self.settings,
                ));
            }
            Err(error) => {
                // An availability failure is reported as a backend failure rather
                // than answered by a different implementation. The caller chooses
                // the fallback, because only the caller holds both backends; see
                // the module header.
                warnings.push(format!("device unavailable: {error}"));
                return Ok(bare(
                    model,
                    options,
                    Termination::BackendFailure,
                    warnings,
                    started,
                    self.settings,
                ));
            }
        };

        // Requirement 34 of SPEC-0010 and requirement 15 here: every device-produced
        // candidate is validated against the original model before publication, and
        // the objective published is this validation's recomputation.
        let candidate = Candidate {
            schema_version: optimizer_core::SCHEMA_VERSION,
            model_id: model.document().model_id.clone(),
            values: program
                .variable_ids()
                .iter()
                .zip(&primal)
                .map(|(variable_id, value)| optimizer_core::Assignment {
                    variable_id: *variable_id,
                    value: *value,
                })
                .collect(),
        };
        let report = model.evaluate(&candidate, options.tolerances)?;
        let bound = certify(&program, &dual).ok().map(|c| c.bound);
        let closed = closed_early
            && match (report.feasible, bound) {
                (true, Some(bound)) => {
                    let gap = report.objective - bound;
                    let scale = report.objective.abs().max(bound.abs());
                    gap >= -options.tolerances.absolute
                        && gap <= options.tolerances.absolute + options.tolerances.relative * scale
                }
                _ => false,
            };

        let termination = if closed {
            Termination::Optimal
        } else if iterations >= self.settings.iteration_limit {
            Termination::IterationLimit
        } else if report.feasible {
            Termination::Feasible
        } else {
            Termination::IterationLimit
        };

        let objective = report.feasible.then_some(report.objective);
        Ok(SolveRecord {
            schema_version: SOLVE_RECORD_SCHEMA_VERSION,
            model_id: model.document().model_id.clone(),
            backend: BACKEND_NAME.to_string(),
            backend_version: BACKEND_VERSION.to_string(),
            termination,
            native_status: None,
            objective: objective.and_then(finite_or_absent),
            best_bound: bound.and_then(finite_or_absent),
            gap: match (objective, bound) {
                (Some(objective), Some(bound)) => finite_or_absent(objective - bound),
                _ => None,
            },
            candidate: Some(candidate),
            validation: Some(report),
            warnings,
            elapsed_ms: started.elapsed().as_millis().min(u128::from(u64::MAX)) as u64,
            options: options.clone(),
            lp_settings: Some(self.settings),
        })
    }
}

/// A record for an outcome reached before any iterate existed.
#[allow(clippy::too_many_arguments)]
fn bare(
    model: &Model,
    options: &SolveOptions,
    termination: Termination,
    warnings: Vec<String>,
    started: Instant,
    settings: LpSettings,
) -> SolveRecord {
    SolveRecord {
        schema_version: SOLVE_RECORD_SCHEMA_VERSION,
        model_id: model.document().model_id.clone(),
        backend: BACKEND_NAME.to_string(),
        backend_version: BACKEND_VERSION.to_string(),
        termination,
        native_status: None,
        objective: None,
        best_bound: None,
        gap: None,
        candidate: None,
        validation: None,
        warnings,
        elapsed_ms: started.elapsed().as_millis().min(u128::from(u64::MAX)) as u64,
        options: options.clone(),
        lp_settings: Some(settings),
    }
}
