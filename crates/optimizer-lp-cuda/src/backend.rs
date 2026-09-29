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
    precision: Option<optimizer_core::LpPrecisionSettings>,
    adaptive: Option<optimizer_core::LpAdaptiveSettings>,
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
            precision: None,
            adaptive: None,
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
        let bytes = {
            let _cost = optimizer_core::lp_cost::scope("code_image_read");
            std::fs::read(&path).map_err(|e| {
                ValidationError::new(optimizer_core::ErrorKind::Document, e.to_string())
            })?
        };
        let mut backend = Self::open_with_code_object(context, settings, path)?;
        backend.matched = true;
        backend.execution = Some(optimizer_core::LpExecutionRecord {
            settings: execution,
            code_object_sha256: {
                let _cost = optimizer_core::lp_cost::scope("code_image_hash");
                optimizer_core::sha256::hex(&bytes)
            },
        });
        backend.code_image = Some(bytes);
        Ok(backend)
    }

    /// Open the versioned precision path; old tuned construction is unchanged.
    pub fn open_precision(
        context: Rc<Context>,
        settings: LpSettings,
        execution: optimizer_core::Fp64ExecutionSettings,
        precision: optimizer_core::LpPrecisionSettings,
    ) -> Result<Self, ValidationError> {
        precision.validate_execution(execution)?;
        let mut backend = Self::open_tuned_with_code_object(
            context,
            settings,
            execution,
            crate::precision::code_object_path(),
        )?;
        backend.precision = Some(precision);
        Ok(backend)
    }

    /// Open explicitly configured adaptive audits and recovery using unchanged precision kernels.
    pub fn open_adaptive(
        context: Rc<Context>,
        settings: LpSettings,
        execution: optimizer_core::Fp64ExecutionSettings,
        adaptive: optimizer_core::LpAdaptiveSettings,
    ) -> Result<Self, ValidationError> {
        adaptive.validate_execution(execution)?;
        let mut backend = Self::open_tuned_with_code_object(
            context,
            settings,
            execution,
            crate::precision::code_object_path(),
        )?;
        backend.adaptive = Some(adaptive);
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
        let component_preparation = optimizer_core::lp_cost::scope("preconditioning");
        let mut settings = self.settings;
        if self.matched {
            settings.iteration_limit = settings.iteration_limit.min(work_limit.unwrap_or(u64::MAX));
        }
        let mut engine = Engine::new(program, settings);
        if let Some(adaptive) = &self.adaptive {
            drop(component_preparation);
            diagnostics.finish("preconditioning", preparation);
            return crate::adaptive::iterate(
                Rc::clone(&self.context),
                &mut engine,
                adaptive.clone(),
                self.code_image
                    .as_deref()
                    .expect("identified precision object"),
                cancel,
                diagnostics,
                check,
                deadline,
            );
        }
        if let Some(precision) = &self.precision {
            drop(component_preparation);
            diagnostics.finish("preconditioning", preparation);
            return crate::precision::iterate(
                Rc::clone(&self.context),
                &mut engine,
                precision.clone(),
                self.code_image
                    .as_deref()
                    .expect("identified precision object"),
                cancel,
                diagnostics,
                check,
                deadline,
            );
        }
        drop(component_preparation);
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
        let component_allocation = optimizer_core::lp_cost::scope("invariant_allocation_upload");
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

        drop(component_allocation);
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
        check: impl FnMut(&[f64], &[f64], &mut optimizer_core::LpDiagnostics) -> bool,
        deadline: Option<Instant>,
    ) -> Result<(Vec<f64>, Vec<f64>, u64), DeviceError> {
        run_matched(
            engine,
            residency,
            self.execution.as_ref().map(|e| e.settings),
            self.settings.check_interval,
            cancel,
            diagnostics,
            check,
            deadline,
        )
    }
}

impl Backend for CudaLpBackend {
    fn capabilities(&self) -> BackendCapabilities {
        BackendCapabilities::declare(
            self.name(),
            BACKEND_VERSION.to_string(),
            vec![ProblemClass::Continuous],
            if self.precision.as_ref().is_some_and(|p| p.mixed())
                || self.adaptive.as_ref().is_some_and(|a| {
                    a.ladder.first() != Some(&optimizer_core::LpAdaptiveRung::Fp64)
                })
            {
                Arithmetic::MixedF32F64
            } else {
                Arithmetic::F64
            },
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
        if let Some(p) = &self.precision {
            diagnostics.precision = Some(optimizer_core::LpPrecisionDiagnostics::new(p.clone()));
        }
        if let Some(a) = &self.adaptive {
            diagnostics.adaptive = Some(optimizer_core::LpAdaptiveDiagnostics::new(a.clone()));
        }
        let mut record = self.solve_observed(model, options, cancel, warm_start, diagnostics)?;
        record.backend = self.name().into();
        if let Some(e) = &self.execution {
            record.schema_version = if self.adaptive.is_some() {
                5
            } else if self.precision.is_some() {
                4
            } else {
                3
            };
            record.lp_adaptive = self.adaptive.clone();
            record.lp_precision = self.precision.clone();
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
        let mut closed_early = false;
        let (primal, dual, iterations) = match self.iterate(
            &program,
            cancel,
            diagnostics,
            |primal, dual, diagnostics| {
                let checking = diagnostics.start();
                let component_checking = optimizer_core::lp_cost::scope("host_checks");
                let stop = assess(model, &program, options.tolerances, primal, dual)
                    .is_some_and(|(_, _, _, _, closed)| closed);
                drop(component_checking);
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
        assess_and_record(
            model,
            &program,
            options,
            &primal,
            &dual,
            iterations,
            closed_early,
            self.settings,
            warnings,
            started,
            diagnostics,
        )
    }
}

/// The matched iteration loop, shared by [`CudaLpBackend::iterate_matched`]
/// and by a repeated-solve session (SPEC-0014).
///
/// Every call starts from a fresh controller — the cold iterate — and, when
/// `execution` is present, a fresh [`crate::tuned::TunedExecutor`], so no
/// primal, dual, anchor or upload-gating state can carry over between solves
/// (requirements 8 and 10). Launch counts are reported relative to the
/// residency's count at entry: a fresh residency starts at zero, so the
/// single-solve path reports exactly what it always has, while a session's
/// reused residency attributes each solve's launches to that solve.
#[allow(clippy::too_many_arguments)]
pub(crate) fn run_matched(
    engine: &Engine<'_>,
    residency: &LpResidency,
    execution: Option<optimizer_core::Fp64ExecutionSettings>,
    check_interval: u64,
    cancel: &CancellationToken,
    diagnostics: &mut optimizer_core::LpDiagnostics,
    mut check: impl FnMut(&[f64], &[f64], &mut optimizer_core::LpDiagnostics) -> bool,
    deadline: Option<Instant>,
) -> Result<(Vec<f64>, Vec<f64>, u64), DeviceError> {
    let initial = diagnostics.start();
    let component_initial = optimizer_core::lp_cost::scope("controller");
    let mut control = optimizer_lp::control::Fp64Controller::new(engine);
    control.set_deadline(deadline);
    drop(component_initial);
    diagnostics.finish("controller", initial);
    let mut tuned = execution
        .map(|settings| crate::tuned::TunedExecutor::new(residency, settings))
        .transpose()?;
    let launch_base = residency.launches();
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
        let chunk = control.next_chunk(check_interval);
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
            diagnostics.kernel_launches = Some(residency.launches() - launch_base);
        }
        let result = match result {
            Ok(result) => result,
            Err(error) => {
                diagnostics.iterations = None;
                diagnostics.control = Some(optimizer_core::LpControlDiagnostics {
                    controller: "host-restart-weight-v1".into(),
                    logical_iterations: control.state().iterations,
                    physical_iterations: None,
                    device_kernel_launches: residency.launches() - launch_base,
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
            let component_phase = optimizer_core::lp_cost::scope("controller");
            control.continue_after_check();
            drop(component_phase);
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
        device_kernel_launches: residency.launches() - launch_base,
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

/// The host's assessment of one iterate: rebuild the candidate, evaluate it
/// against the original model, certify a bound from the model's own
/// coefficients and check the gap.
///
/// Shared by the single-solve termination check and a session solve so a
/// batch solve is assessed by exactly the code a fresh solve is (SPEC-0014
/// requirement 5).
pub(crate) fn assess(
    model: &Model,
    program: &LinearProgram,
    tolerances: optimizer_core::Tolerances,
    primal: &[f64],
    dual: &[f64],
) -> Option<(Candidate, f64, bool, Option<f64>, bool)> {
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
    let report = model.evaluate(&candidate, tolerances).ok()?;
    let bound = certify(program, dual).ok().map(|c| c.bound);
    let closed = report.feasible
        && bound
            .and_then(|bound| assess_gap(program, primal, bound, tolerances))
            .is_some_and(|gap| gap.closed);
    Some((candidate, report.objective, report.feasible, bound, closed))
}

/// Build the record for a completed matched iteration: the final candidate,
/// its host validation and certification, and the termination mapping.
///
/// Extracted verbatim from [`CudaLpBackend::solve_observed`] so a session
/// solve records exactly what a fresh single solve records (SPEC-0014
/// requirement 5). `closed_early` is whether any in-loop assessment already
/// closed the gap; `settings` is the backend's or session's, deliberately not
/// clamped by the solve options' iteration limit, which is what the
/// termination mapping has always read.
#[allow(clippy::too_many_arguments)]
pub(crate) fn assess_and_record(
    model: &Model,
    program: &LinearProgram,
    options: &SolveOptions,
    primal: &[f64],
    dual: &[f64],
    iterations: u64,
    closed_early: bool,
    settings: LpSettings,
    mut warnings: Vec<String>,
    started: Instant,
    diagnostics: &mut optimizer_core::LpDiagnostics,
) -> Result<SolveRecord, ValidationError> {
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
    let checking = diagnostics.start();
    let component_checking = optimizer_core::lp_cost::scope("host_checks");
    diagnostics.capture(dual, iterations);
    if let Some(control) = &mut diagnostics.control {
        control.assessments += 1;
    }
    let report = model.evaluate(&candidate, options.tolerances)?;
    let bound = certify(program, dual).ok().map(|c| c.bound);
    let gap = report
        .feasible
        .then(|| bound.and_then(|bound| assess_gap(program, primal, bound, options.tolerances)))
        .flatten();
    let closed = closed_early && gap.is_some_and(|gap| gap.closed);

    let control_stop = diagnostics.control.as_ref().map(|c| c.stop.as_str());
    let termination = if control_stop == Some("numerical_failure") {
        if let Some(reason) = diagnostics.precision.as_ref().and_then(|p| p.guard.clone()) {
            warnings.push(reason);
        }
        Termination::NumericalFailure
    } else if control_stop == Some("interrupted") {
        Termination::Interrupted
    } else if control_stop == Some("time_limit") {
        Termination::TimeLimit
    } else if closed {
        Termination::Optimal
    } else if control_stop == Some("iteration_limit") || iterations >= settings.iteration_limit {
        Termination::IterationLimit
    } else if report.feasible {
        Termination::Feasible
    } else {
        Termination::IterationLimit
    };

    drop(component_checking);
    diagnostics.finish("host_checks", checking);
    let objective = report.feasible.then_some(report.objective);
    Ok(SolveRecord {
        lp_execution: None,
        lp_precision: None,
        lp_adaptive: None,
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
        lp_settings: Some(settings),
    })
}

/// A record for an outcome reached before any iterate existed.
#[allow(clippy::too_many_arguments)]
pub(crate) fn bare(
    model: &Model,
    options: &SolveOptions,
    termination: Termination,
    warnings: Vec<String>,
    started: Instant,
    settings: LpSettings,
) -> SolveRecord {
    SolveRecord {
        lp_execution: None,
        lp_precision: None,
        lp_adaptive: None,
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
