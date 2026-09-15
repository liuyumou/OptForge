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
use optimizer_lp::certify::{assess_gap, certify};
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
    matched: bool,
    execution: Option<optimizer_core::LpExecutionRecord>,
    code_image: Option<Vec<u8>>,
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
            matched: false,
            execution: None,
            code_image: None,
        })
    }

    /// Opt into the shared host restart/weight controller using existing FP64 kernels.
    ///
    /// # Errors
    /// Returns invalid LP settings, as for the legacy constructor.
    pub fn open_matched(
        context: Rc<Context>,
        settings: LpSettings,
    ) -> Result<Self, ValidationError> {
        let mut backend = Self::open(context, settings)?;
        backend.matched = true;
        Ok(backend)
    }

    /// Open explicitly configured experimental FP64 execution.
    /// The code-object hash records the actual bytes subsequently loaded.
    pub fn open_tuned(
        context: Rc<Context>,
        settings: LpSettings,
        execution: optimizer_core::Fp64ExecutionSettings,
    ) -> Result<Self, ValidationError> {
        Self::open_tuned_with_code_object(
            context,
            settings,
            execution,
            crate::tuned::code_object_path(),
        )
    }

    /// Open tuned execution against an explicit provisioned code object.
    pub fn open_tuned_with_code_object(
        context: Rc<Context>,
        settings: LpSettings,
        execution: optimizer_core::Fp64ExecutionSettings,
        path: std::path::PathBuf,
    ) -> Result<Self, ValidationError> {
        execution.validate()?;
        let bytes = std::fs::read(&path).map_err(|e| {
            ValidationError::new(optimizer_core::ErrorKind::Document, e.to_string())
        })?;
        let mut backend = Self::open_with_code_object(context, settings, path)?;
        backend.matched = true;
        backend.execution = Some(optimizer_core::LpExecutionRecord {
            settings: execution,
            code_object_sha256: optimizer_core::sha256::hex(&bytes),
        });
        backend.code_image = Some(bytes);
        Ok(backend)
    }

    fn name(&self) -> &'static str {
        if self.execution.is_some() {
            "cuda-lp-tuned"
        } else if self.matched {
            "cuda-lp-matched"
        } else {
            BACKEND_NAME
        }
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
        diagnostics: &mut optimizer_core::LpDiagnostics,
        mut check: impl FnMut(&[f64], &[f64], &mut optimizer_core::LpDiagnostics) -> bool,
        deadline: Option<Instant>,
        work_limit: Option<u64>,
    ) -> Result<(Vec<f64>, Vec<f64>, u64), DeviceError> {
        // The host engine owns the scaling and the step size, and the device
        // uploads exactly what it computed. Recomputing the scaling here would
        // create a second thing that must agree with the first, and the host engine
        // exists precisely to be the one the device is checked against.
        let preparation = diagnostics.start();
        let mut settings = self.settings;
        if self.matched {
            settings.iteration_limit = settings.iteration_limit.min(work_limit.unwrap_or(u64::MAX));
        }
        let engine = Engine::new(program, settings);
        diagnostics.finish("preconditioning", preparation);
        let (row_values, column_values) = engine.scaled_matrix();
        let peak = match &self.execution {
            Some(e) => crate::tuned::peak_buffer_bytes(program, e.settings)?,
            None => LpResidency::peak_buffer_bytes(program),
        };
        if diagnostics
            .device_buffer_limit_bytes
            .is_some_and(|limit| peak > limit)
        {
            return Err(DeviceError::Unsupported(format!(
                "LP device buffer budget: {peak} bytes"
            )));
        }
        let allocation = diagnostics.start();
        let residency = LpResidency::open_for_execution(
            Rc::clone(&self.context),
            program,
            row_values,
            column_values,
            engine.scaled_objective(),
            engine.scaled_row_bounds(),
            engine.scaled_column_bounds(),
            &self.code_object,
            self.execution.as_ref().map(|e| e.settings),
            self.code_image.as_deref(),
            diagnostics.execution.as_mut(),
        );
        if diagnostics.enabled && self.execution.is_some() {
            diagnostics.device_buffer_peak_bytes =
                diagnostics.execution.as_ref().map(|e| e.allocated_bytes);
        }
        let residency = residency?;

        diagnostics.finish("invariant_allocation_upload", allocation);
        if diagnostics.enabled {
            if self.execution.is_none() {
                diagnostics.device_buffer_peak_bytes = Some(peak);
            }
            diagnostics.restarts = Some(0);
        }
        if self.matched {
            return self.iterate_matched(&engine, &residency, cancel, diagnostics, check, deadline);
        }
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
            let result = residency.advance_with_diagnostics(
                &mut x,
                &mut y,
                &anchor_x,
                &anchor_y,
                done,
                chunk,
                engine.step(),
                1.0,
                cancel,
                diagnostics,
            );
            if diagnostics.enabled {
                diagnostics.kernel_launches = Some(residency.launches());
                diagnostics.iterations = Some(residency.launches() / 6);
            }
            result?;
            done += chunk;

            let primal = engine.unscale_primal(&x);
            let dual = engine.unscale_dual(&y);
            diagnostics.capture(&dual, done);
            if check(&primal, &dual, diagnostics) {
                return Ok((primal, dual, done));
            }
        }

        Ok((engine.unscale_primal(&x), engine.unscale_dual(&y), done))
    }
    #[allow(clippy::too_many_arguments)]
    fn iterate_matched(
        &self,
        engine: &Engine<'_>,
        residency: &LpResidency,
        cancel: &CancellationToken,
        diagnostics: &mut optimizer_core::LpDiagnostics,
        mut check: impl FnMut(&[f64], &[f64], &mut optimizer_core::LpDiagnostics) -> bool,
        deadline: Option<Instant>,
    ) -> Result<(Vec<f64>, Vec<f64>, u64), DeviceError> {
        let initial = diagnostics.start();
        let mut control = optimizer_lp::control::Fp64Controller::new(engine);
        control.set_deadline(deadline);
        diagnostics.finish("controller", initial);
        let mut tuned = self
            .execution
            .as_ref()
            .map(|e| crate::tuned::TunedExecutor::new(residency, e.settings))
            .transpose()?;
        let mut assessed = None;
        let mut assessments = 0;
        let mut stop = "iteration_limit";
        while control.remaining() > 0 {
            if cancel.is_cancelled() {
                stop = "interrupted";
                break;
            }
            if control.expired() {
                stop = "time_limit";
                break;
            }
            let chunk = control.next_chunk(self.settings.check_interval);
            let since_restart = control.state().since_restart;
            let weight = control.state().weight;
            let generation = control.generation();
            let restarts = control.state().restarts;
            let (x, y, anchor_x, anchor_y) = control.buffers();
            let result = if let Some(tuned) = &mut tuned {
                tuned.advance(
                    x,
                    y,
                    anchor_x,
                    anchor_y,
                    generation,
                    restarts,
                    since_restart,
                    chunk,
                    engine.step(),
                    weight,
                    |_| cancel.is_cancelled() || deadline.is_some_and(|d| Instant::now() >= d),
                    diagnostics,
                )
            } else {
                residency.advance_resumable(
                    x,
                    y,
                    anchor_x,
                    anchor_y,
                    since_restart,
                    chunk,
                    engine.step(),
                    weight,
                    |_| cancel.is_cancelled() || deadline.is_some_and(|d| Instant::now() >= d),
                    diagnostics,
                )
            };
            if diagnostics.enabled {
                diagnostics.kernel_launches = Some(residency.launches());
            }
            let result = match result {
                Ok(result) => result,
                Err(error) => {
                    diagnostics.iterations = None;
                    diagnostics.control = Some(optimizer_core::LpControlDiagnostics {
                        controller: "host-restart-weight-v1".into(),
                        logical_iterations: control.state().iterations,
                        physical_iterations: None,
                        device_kernel_launches: residency.launches(),
                        assessments,
                        kkt_evaluations: control.kkt_evaluations(),
                        restarts: control.state().restarts,
                        weight: control.state().weight,
                        stop: "device_failure".into(),
                    });
                    diagnostics
                        .unavailable
                        .push("completed device work after fault is unavailable".into());
                    return Err(error);
                }
            };
            control
                .commit_steps(result.completed)
                .expect("admitted device chunk");
            if diagnostics.enabled {
                diagnostics.iterations = Some(control.physical_iterations());
            }
            if result.interrupted || cancel.is_cancelled() || control.expired() {
                stop = if cancel.is_cancelled() {
                    "interrupted"
                } else {
                    "time_limit"
                };
                break;
            }
            if control.check_pending() {
                let iterate = control.iterate();
                assessments += 1;
                let accepted = check(&iterate.primal, &iterate.dual, diagnostics);
                assessed = Some(iterate);
                if accepted {
                    stop = "accepted";
                    break;
                }
                let phase = diagnostics.start();
                control.continue_after_check();
                diagnostics.finish("controller", phase);
            }
        }
        if diagnostics.enabled {
            diagnostics.iterations = Some(control.physical_iterations());
            diagnostics.restarts = Some(control.state().restarts);
        }
        diagnostics.control = Some(optimizer_core::LpControlDiagnostics {
            controller: "host-restart-weight-v1".into(),
            logical_iterations: control.state().iterations,
            physical_iterations: Some(control.physical_iterations()),
            device_kernel_launches: residency.launches(),
            assessments,
            kkt_evaluations: control.kkt_evaluations(),
            restarts: control.state().restarts,
            weight: control.state().weight,
            stop: stop.into(),
        });
        if control.physical_iterations() == 0 && stop == "interrupted" {
            return Err(DeviceError::Cancelled);
        }
        let iterate = assessed.unwrap_or_else(|| control.iterate());
        Ok((iterate.primal, iterate.dual, iterate.iterations))
    }
}

impl Backend for CudaLpBackend {
    fn capabilities(&self) -> BackendCapabilities {
        BackendCapabilities::declare(
            self.name(),
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
        self.solve_with_diagnostics(
            model,
            options,
            cancel,
            warm_start,
            &mut optimizer_core::LpDiagnostics::new(false, false),
        )
    }
}

impl CudaLpBackend {
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
        if let Some(e) = &self.execution {
            let mut observations = optimizer_core::LpExecutionDiagnostics::new(e.settings);
            observations.code_object_sha256 = Some(e.code_object_sha256.clone());
            diagnostics.execution = Some(observations);
        }
        let mut record = self.solve_observed(model, options, cancel, warm_start, diagnostics)?;
        record.backend = self.name().into();
        if let Some(e) = &self.execution {
            record.schema_version = 3;
            record.lp_settings = Some(self.settings);
            record.lp_execution = Some(e.clone());
        }
        Ok(record)
    }

    fn solve_observed(
        &self,
        model: &Model,
        options: &SolveOptions,
        cancel: &CancellationToken,
        warm_start: Option<WarmStart<'_>>,
        diagnostics: &mut optimizer_core::LpDiagnostics,
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
        let assess =
            |primal: &[f64], dual: &[f64]| -> Option<(Candidate, f64, bool, Option<f64>, bool)> {
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
                let closed = report.feasible
                    && bound
                        .and_then(|bound| assess_gap(&program, primal, bound, options.tolerances))
                        .is_some_and(|gap| gap.closed);
                Some((candidate, report.objective, report.feasible, bound, closed))
            };

        let mut closed_early = false;
        let (primal, dual, iterations) = match self.iterate(
            &program,
            cancel,
            diagnostics,
            |primal, dual, diagnostics| {
                let checking = diagnostics.start();
                let stop = assess(primal, dual).is_some_and(|(_, _, _, _, closed)| closed);
                diagnostics.finish("host_checks", checking);
                closed_early |= stop;
                stop
            },
            options
                .time_limit_ms
                .and_then(|ms| started.checked_add(std::time::Duration::from_millis(ms))),
            options.iteration_limit,
        ) {
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
        let checking = diagnostics.start();
        diagnostics.capture(&dual, iterations);
        if let Some(control) = &mut diagnostics.control {
            control.assessments += 1;
        }
        let report = model.evaluate(&candidate, options.tolerances)?;
        let bound = certify(&program, &dual).ok().map(|c| c.bound);
        let gap = report
            .feasible
            .then(|| {
                bound.and_then(|bound| assess_gap(&program, &primal, bound, options.tolerances))
            })
            .flatten();
        let closed = closed_early && gap.is_some_and(|gap| gap.closed);

        let control_stop = diagnostics.control.as_ref().map(|c| c.stop.as_str());
        let termination = if control_stop == Some("interrupted") {
            Termination::Interrupted
        } else if control_stop == Some("time_limit") {
            Termination::TimeLimit
        } else if closed {
            Termination::Optimal
        } else if control_stop == Some("iteration_limit")
            || iterations >= self.settings.iteration_limit
        {
            Termination::IterationLimit
        } else if report.feasible {
            Termination::Feasible
        } else {
            Termination::IterationLimit
        };

        diagnostics.finish("host_checks", checking);
        let objective = report.feasible.then_some(report.objective);
        Ok(SolveRecord {
            lp_execution: None,
            schema_version: SOLVE_RECORD_SCHEMA_VERSION,
            model_id: model.document().model_id.clone(),
            backend: BACKEND_NAME.to_string(),
            backend_version: BACKEND_VERSION.to_string(),
            termination,
            native_status: None,
            objective: objective.and_then(finite_or_absent),
            best_bound: bound.and_then(finite_or_absent),
            gap: gap.map(|gap| gap.upper),
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
        lp_execution: None,
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
