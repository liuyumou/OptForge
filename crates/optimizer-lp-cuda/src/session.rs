//! Repeated-solve sessions over one resident matrix (SPEC-0014).
//!
//! A session pays the single-solve setup costs once — code object read and
//! hash, preconditioning, memory admission and the invariant upload — and then
//! solves a batch of models that differ, if at all, only in variable bounds.
//! Per solve it runs exactly the code the fresh single-solve path runs: a
//! fresh controller from the cold iterate, a fresh
//! [`crate::tuned::TunedExecutor`], the shared `run_matched` loop and the
//! shared `assess_and_record` tail of `backend`, so a batch solve's bits,
//! counts and termination are the fresh solve's (requirement 15).
//!
//! The reuse boundary is requirement 7's: the preconditioner, the scaled
//! matrix in both orientations, the scaled objective and the spectral step are
//! prepared once; nothing derived from variable bounds survives a variant
//! boundary without a rebind, and the column-bound buffers are the only
//! resident state a variant may replace (requirement 12). A device fault other
//! than cancellation poisons the session: later solves are refused and the
//! batch driver records them `not_attempted`, while records for completed
//! solves are unaffected (requirement 13).
//!
//! A session is `!Send` through its `Rc<Context>` and bound to the one device
//! that context leases; there is deliberately no API to seed a solve from a
//! previous solve's state.

use std::rc::Rc;
use std::time::Instant;

use optimizer_core::{
    CancellationToken, ErrorKind, Fp64ExecutionSettings, LpDiagnostics, LpExecutionDiagnostics,
    LpExecutionRecord, LpSettings, Model, SessionSetup, SolveOptions, SolveRecord, Termination,
    ValidationError,
};
use optimizer_cuda_sys::{Context, DeviceError};
use optimizer_lp::PreparedMatrix;
use optimizer_lp::pdhg::Engine;
use optimizer_lp::problem::LinearProgram;

use crate::backend::{assess, assess_and_record, bare, run_matched};
use crate::residency::LpResidency;

/// The scaled column-bound pair currently resident, compared bitwise.
///
/// Bitwise rather than `==`: a variant whose bound differs only in a zero's
/// sign is a different resident state, and the rebind counter must describe
/// what the device actually holds.
pub(crate) fn bounds_match(loaded: &[(f64, f64)], lower: &[f64], upper: &[f64]) -> bool {
    loaded.len() == lower.len()
        && loaded
            .iter()
            .zip(lower.iter().zip(upper))
            .all(|((l, u), (lower, upper))| {
                l.to_bits() == lower.to_bits() && u.to_bits() == upper.to_bits()
            })
}

/// A repeated-solve session for tuned FP64 execution (SPEC-0014).
///
/// Opened explicitly with one device context, one code object, one matrix,
/// one objective, one set of row bounds and one settings document — all fixed
/// for the session's life (requirement 6). Never constructed by a selector or
/// default: only a caller that names the session API reaches it.
pub struct TunedSession {
    context: Rc<Context>,
    execution: LpExecutionRecord,
    model: Model,
    program: LinearProgram,
    prepared: PreparedMatrix,
    residency: LpResidency,
    loaded_bounds: Vec<(f64, f64)>,
    poisoned: Option<String>,
    setup: SessionSetup,
    solve_phases: SessionSetup,
}

impl TunedSession {
    /// Open a session: precondition once, admit memory once, upload the
    /// invariant data once.
    ///
    /// The code object is read and hashed once, after the buffer budget is
    /// decided from the program and before the module load, the same order
    /// [`LpResidency::open_tuned`] uses. The caller creates the context and
    /// may time that as the batch record's `device_context` setup phase; the
    /// phases this open measures — `preconditioning`, `module_load` and
    /// `invariant_allocation_upload` — land in [`TunedSession::setup`]. The
    /// invariant allocation and upload counters land in `diagnostics.execution`,
    /// once, and are never repeated into a per-solve record.
    ///
    /// # Errors
    ///
    /// Returns the settings', model's or budget's validation failures, and a
    /// backend failure when the device or the code object is unavailable.
    /// Nothing falls back: a session failure is reported, never substituted.
    pub fn open(
        context: Rc<Context>,
        settings: LpSettings,
        execution: Fp64ExecutionSettings,
        model: Model,
        diagnostics: &mut LpDiagnostics,
    ) -> Result<Self, ValidationError> {
        settings.validate()?;
        execution.validate()?;
        let device = |e: DeviceError| ValidationError::new(ErrorKind::Backend, e.to_string());
        let mut setup = SessionSetup::default();
        let program = LinearProgram::new(&model)?;
        let phase = setup.start();
        let prepared = PreparedMatrix::new(&program, &settings);
        setup.finish("preconditioning", phase);
        // Admission is decided from the program before the code object is
        // read, exactly as open_tuned decides it before reading.
        let peak = crate::tuned::peak_buffer_bytes(&program, execution).map_err(device)?;
        if diagnostics
            .device_buffer_limit_bytes
            .is_some_and(|limit| peak > limit)
        {
            return Err(ValidationError::new(
                ErrorKind::Backend,
                format!("LP device buffer budget: {peak} bytes"),
            ));
        }
        let phase = setup.start();
        let image = std::fs::read(crate::tuned::code_object_path())
            .map_err(|e| device(DeviceError::CodeObjectMissing(e.to_string())))?;
        let image_sha256 = optimizer_core::sha256::hex(&image);
        setup.finish("module_load", phase);
        let execution = LpExecutionRecord {
            settings: execution,
            code_object_sha256: image_sha256,
        };
        let mut counters = LpExecutionDiagnostics::new(execution.settings);
        counters.code_object_sha256 = Some(execution.code_object_sha256.clone());
        diagnostics.execution = Some(counters);
        let phase = setup.start();
        // The base engine's bound-derived half supplies the initially resident
        // column bounds; everything else it would compute is the prepared
        // matrix's, so it is built here and not kept.
        let base = Engine::from_prepared(&program, &prepared);
        let residency = LpResidency::open_prepared_tuned(
            Rc::clone(&context),
            &program,
            &prepared,
            base.scaled_column_bounds(),
            execution.settings,
            Some(&image),
            diagnostics.execution.as_mut(),
        )
        .map_err(device)?;
        setup.finish("invariant_allocation_upload", phase);
        if diagnostics.enabled {
            diagnostics.device_buffer_peak_bytes =
                diagnostics.execution.as_ref().map(|e| e.allocated_bytes);
        }
        let (lower, upper) = base.scaled_column_bounds();
        let loaded_bounds = lower.iter().copied().zip(upper.iter().copied()).collect();
        Ok(Self {
            context,
            execution,
            model,
            program,
            prepared,
            residency,
            loaded_bounds,
            poisoned: None,
            setup,
            solve_phases: SessionSetup::default(),
        })
    }

    /// Solve the base model, or a variant differing only in variable bounds.
    ///
    /// Every solve runs from the cold iterate with a fresh controller, a
    /// fresh executor and fresh per-solve execution counters (requirements 8
    /// to 10), and is assessed and recorded by the single-solve path's own
    /// code (requirement 5). A variant is admitted only if its matrix,
    /// objective, row bounds, variable IDs and domains are the session's, and
    /// the refusal happens before any allocation or upload for that solve
    /// (requirement 11); only the column-bound buffers are re-uploaded, and
    /// only when the scaled bounds actually changed (requirement 12).
    ///
    /// The per-solve session phases — `variant_rebind`, `engine_rebind` and,
    /// when bounds changed, `bound_upload` — land in
    /// [`TunedSession::solve_phases`], never in the endpoint's phase
    /// vocabulary (requirement 24).
    ///
    /// # Errors
    ///
    /// Returns a validation failure for invalid options, an unsupported
    /// failure for an inadmissible variant, and a backend failure naming the
    /// original fault when the session is poisoned. A device fault within a
    /// solve poisons the session and is reported in that solve's record
    /// exactly as the single-solve path reports it; cancellation maps to the
    /// existing interrupted record and does not poison.
    pub fn solve(
        &mut self,
        variant: Option<&Model>,
        options: &SolveOptions,
        cancel: &CancellationToken,
        diagnostics: &mut LpDiagnostics,
    ) -> Result<SolveRecord, ValidationError> {
        options.validate()?;
        if let Some(reason) = &self.poisoned {
            return Err(ValidationError::new(
                ErrorKind::Backend,
                format!("the session is poisoned by an earlier device fault: {reason}"),
            ));
        }
        let settings = self.prepared.settings();
        let started = Instant::now();
        let mut phases = SessionSetup::default();
        self.solve_phases = SessionSetup::default();
        let mut warnings = Vec::new();

        let phase = phases.start();
        let mut variant_program = None;
        if let Some(variant) = variant {
            // Admission compares the variant's own canonical program against
            // the session's: the bounds-only rebind inherits this program's
            // matrix, objective and row bounds, so comparing against it alone
            // could never see a changed coefficient (requirement 11).
            let canonical = LinearProgram::new(variant)?;
            let rebound = self.program.with_variable_bounds(variant)?;
            let same_domains = variant
                .document()
                .variables
                .iter()
                .zip(&self.model.document().variables)
                .all(|(v, b)| v.domain == b.domain);
            if !same_domains || !self.program.same_matrix_objective_rows(&canonical) {
                return Err(ValidationError::new(
                    ErrorKind::Unsupported,
                    "a session variant must differ from the session model only in variable bounds",
                ));
            }
            variant_program = Some(rebound);
        }
        phases.finish("variant_rebind", phase);
        let program = variant_program.as_ref().unwrap_or(&self.program);
        let model = variant.unwrap_or(&self.model);

        // Fresh per-solve execution counters (requirement 9): this solve's
        // working-state uploads, bound rebinds, readbacks and launches. The
        // invariant upload was counted once at open, not here, and a refused
        // variant never reaches this point.
        let mut counters = LpExecutionDiagnostics::new(self.execution.settings);
        counters.code_object_sha256 = Some(self.execution.code_object_sha256.clone());
        diagnostics.execution = Some(counters);

        let phase = phases.start();
        let mut engine = Engine::from_prepared(program, &self.prepared);
        if let Some(limit) = options.iteration_limit {
            engine.clamp_iteration_limit(limit);
        }
        phases.finish("engine_rebind", phase);

        let (lower, upper) = engine.scaled_column_bounds();
        if !bounds_match(&self.loaded_bounds, lower, upper) {
            let phase = phases.start();
            let result = self.residency.rebind_column_bounds(
                lower,
                upper,
                diagnostics.execution.as_mut().expect("per-solve counters"),
            );
            if let Err(error) = result {
                self.poisoned = Some(error.to_string());
                warnings.push(format!("device unavailable: {error}"));
                self.solve_phases = phases;
                return Ok(bare(
                    model,
                    options,
                    Termination::BackendFailure,
                    warnings,
                    started,
                    settings,
                ));
            }
            phases.finish("bound_upload", phase);
            self.loaded_bounds = lower.iter().copied().zip(upper.iter().copied()).collect();
        }

        if diagnostics.enabled {
            diagnostics.restarts = Some(0);
            diagnostics.device_buffer_peak_bytes = Some(self.residency.buffer_bytes());
        }
        let deadline = options
            .time_limit_ms
            .and_then(|ms| started.checked_add(std::time::Duration::from_millis(ms)));
        let mut closed_early = false;
        let result = run_matched(
            &engine,
            &self.residency,
            Some(self.execution.settings),
            settings.check_interval,
            cancel,
            diagnostics,
            |primal, dual, diagnostics| {
                let checking = diagnostics.start();
                let stop = assess(model, program, options.tolerances, primal, dual)
                    .is_some_and(|(_, _, _, _, closed)| closed);
                diagnostics.finish("host_checks", checking);
                closed_early |= stop;
                stop
            },
            deadline,
        );
        let (primal, dual, iterations) = match result {
            Ok(iterate) => iterate,
            Err(DeviceError::Cancelled) => {
                self.solve_phases = phases;
                return Ok(bare(
                    model,
                    options,
                    Termination::Interrupted,
                    warnings,
                    started,
                    settings,
                ));
            }
            Err(error) => {
                // The existing single-solve mapping: an availability failure
                // is reported, never answered by another implementation. The
                // session additionally poisons, so later solves are refused
                // and recorded not_attempted (requirement 13).
                self.poisoned = Some(error.to_string());
                warnings.push(format!("device unavailable: {error}"));
                self.solve_phases = phases;
                return Ok(bare(
                    model,
                    options,
                    Termination::BackendFailure,
                    warnings,
                    started,
                    settings,
                ));
            }
        };
        let mut record = assess_and_record(
            model,
            program,
            options,
            &primal,
            &dual,
            iterations,
            closed_early,
            settings,
            warnings,
            started,
            diagnostics,
        )?;
        // The session runs tuned execution only, so its records carry the
        // tuned identity exactly as solve_with_diagnostics writes it.
        record.backend = "cuda-lp-tuned".into();
        record.schema_version = 3;
        record.lp_settings = Some(settings);
        record.lp_execution = Some(self.execution.clone());
        self.solve_phases = phases;
        Ok(record)
    }

    /// The model this session was opened with.
    #[must_use]
    pub fn model(&self) -> &Model {
        &self.model
    }

    /// The session's canonical program, with the base model's column bounds.
    #[must_use]
    pub fn program(&self) -> &LinearProgram {
        &self.program
    }

    /// The matrix-only state prepared once at open (requirement 7).
    #[must_use]
    pub fn prepared(&self) -> &PreparedMatrix {
        &self.prepared
    }

    /// The resident device state; its `uploads()` stays 1 for the session's
    /// life and `bound_rebinds()` counts variant rebinds separately.
    #[must_use]
    pub fn residency(&self) -> &LpResidency {
        &self.residency
    }

    /// The tuned execution this session runs, with the code-object hash
    /// recorded once at open.
    #[must_use]
    pub fn execution(&self) -> &LpExecutionRecord {
        &self.execution
    }

    /// The one-time setup phases measured at open.
    #[must_use]
    pub fn setup(&self) -> &SessionSetup {
        &self.setup
    }

    /// The session phases of the most recent solve.
    #[must_use]
    pub fn solve_phases(&self) -> &SessionSetup {
        &self.solve_phases
    }

    /// The fault that poisoned this session, if one did.
    #[must_use]
    pub fn poisoned(&self) -> Option<&str> {
        self.poisoned.as_deref()
    }

    /// Mark the session poisoned after a device fault the caller observed
    /// between solves; later solves are refused (requirement 13). Faults
    /// observed by [`TunedSession::solve`] itself poison the session without
    /// this call.
    pub fn poison(&mut self, reason: impl Into<String>) {
        self.poisoned = Some(reason.into());
    }

    /// The device this session is bound to, for a record that must name it.
    #[must_use]
    pub fn device(&self) -> &optimizer_cuda_sys::DeviceInfo {
        self.context.device()
    }
}
