//! Native HiGHS solve path: loading, status mapping, cancellation, extraction.
//!
//! Every function here assumes the pinned 1.11.0 CPU build is linked. The
//! `Highs` handle owns its native instance and releases it on every return
//! path, including unwinds.

use std::ffi::{CStr, c_char, c_double, c_int, c_void};
use std::panic::{AssertUnwindSafe, catch_unwind};
use std::sync::{Mutex, MutexGuard, OnceLock};
use std::time::Instant;

use optimizer_core::{
    Assignment, Basis, BasisStatus, Bound, CancellationToken, Candidate, Domain, ErrorKind, Model,
    SOLVE_SCHEMA_VERSION, SolveOptions, SolveRecord, Termination, ValidationError, WarmStart,
    finite_or_absent,
};

use crate::ffi::{self, HighsInt};
use crate::{BACKEND_NAME, PINNED_VERSION};

/// HiGHS treats matrix entries below a fixed threshold as structurally absent.
/// Rejecting them keeps the loaded model equal to the original rather than
/// letting the library silently drop coefficients.
const SMALL_MATRIX_VALUE: f64 = 1e-9;

fn error(kind: ErrorKind, message: impl Into<String>) -> ValidationError {
    ValidationError::new(kind, message)
}

fn backend_error(context: &str, status: HighsInt) -> ValidationError {
    error(
        ErrorKind::Backend,
        format!("{context}: HiGHS returned status {status}"),
    )
}

/// ADR-0003 requires serialized use of the native global scheduler.
fn native_lock() -> MutexGuard<'static, ()> {
    static LOCK: OnceLock<Mutex<()>> = OnceLock::new();
    LOCK.get_or_init(|| Mutex::new(()))
        .lock()
        .unwrap_or_else(|poisoned| poisoned.into_inner())
}

/// Native library version string.
pub(crate) fn version() -> String {
    // Safety: HiGHS returns a static NUL-terminated string.
    let raw = unsafe { ffi::Highs_version() };
    if raw.is_null() {
        return PINNED_VERSION.to_string();
    }
    unsafe { CStr::from_ptr(raw) }
        .to_string_lossy()
        .into_owned()
}

/// Owned native instance. Private field; destroyed exactly once on drop.
struct Highs {
    handle: *mut c_void,
}

impl Highs {
    fn new() -> Result<Self, ValidationError> {
        // Safety: no arguments; returns an owned instance or null.
        let handle = unsafe { ffi::Highs_create() };
        if handle.is_null() {
            return Err(error(
                ErrorKind::Backend,
                "HiGHS instance could not be created",
            ));
        }
        Ok(Self { handle })
    }

    fn as_ptr(&self) -> *mut c_void {
        self.handle
    }

    fn infinity(&self) -> f64 {
        // Safety: valid handle.
        unsafe { ffi::Highs_getInfinity(self.handle) }
    }

    fn set_bool(&self, option: &CStr, value: bool) -> Result<(), ValidationError> {
        // Safety: valid handle and NUL-terminated option name.
        let status = unsafe {
            ffi::Highs_setBoolOptionValue(self.handle, option.as_ptr(), c_int::from(value))
        };
        check(status, "set bool option")
    }

    fn set_int(&self, option: &CStr, value: HighsInt) -> Result<(), ValidationError> {
        // Safety: valid handle and NUL-terminated option name.
        let status = unsafe { ffi::Highs_setIntOptionValue(self.handle, option.as_ptr(), value) };
        check(status, "set int option")
    }

    fn set_double(&self, option: &CStr, value: f64) -> Result<(), ValidationError> {
        // Safety: valid handle and NUL-terminated option name.
        let status =
            unsafe { ffi::Highs_setDoubleOptionValue(self.handle, option.as_ptr(), value) };
        check(status, "set double option")
    }

    fn set_string(&self, option: &CStr, value: &CStr) -> Result<(), ValidationError> {
        // Safety: valid handle and NUL-terminated strings.
        let status = unsafe {
            ffi::Highs_setStringOptionValue(self.handle, option.as_ptr(), value.as_ptr())
        };
        check(status, "set string option")
    }

    fn double_info(&self, name: &CStr) -> Option<f64> {
        let mut value = 0.0f64;
        // Safety: valid handle; writes at most one f64.
        let status =
            unsafe { ffi::Highs_getDoubleInfoValue(self.handle, name.as_ptr(), &raw mut value) };
        (status == ffi::K_HIGHS_STATUS_OK)
            .then_some(value)
            .and_then(finite_or_absent)
    }

    fn int_info(&self, name: &CStr) -> Option<i64> {
        let mut value: c_int = 0;
        // Safety: valid handle; writes at most one c_int.
        let status =
            unsafe { ffi::Highs_getIntInfoValue(self.handle, name.as_ptr(), &raw mut value) };
        (status == ffi::K_HIGHS_STATUS_OK).then_some(i64::from(value))
    }
}

impl Drop for Highs {
    fn drop(&mut self) {
        // Safety: the handle was created by Highs_create and is destroyed once.
        unsafe { ffi::Highs_destroy(self.handle) };
    }
}

fn check(status: HighsInt, context: &str) -> Result<(), ValidationError> {
    match status {
        ffi::K_HIGHS_STATUS_OK | ffi::K_HIGHS_STATUS_WARNING => Ok(()),
        ffi::K_HIGHS_STATUS_ERROR => Err(backend_error(context, status)),
        other => Err(backend_error(context, other)),
    }
}

/// Cancellation state handed to the native callback.
struct Interrupt {
    cancel: CancellationToken,
}

/// Native interrupt trampoline.
///
/// This runs on a native stack, so it must never unwind. `catch_unwind` turns a
/// panic into a no-op rather than undefined behavior.
unsafe extern "C" fn interrupt_callback(
    _callback_type: c_int,
    _message: *const c_char,
    _data_out: *const ffi::HighsCallbackDataOut,
    data_in: *mut ffi::HighsCallbackDataIn,
    user_data: *mut c_void,
) {
    let _ = catch_unwind(AssertUnwindSafe(|| {
        if data_in.is_null() || user_data.is_null() {
            return;
        }
        // Safety: HiGHS passes our own Interrupt pointer, valid for the solve.
        let interrupt = unsafe { &*user_data.cast::<Interrupt>() };
        if interrupt.cancel.is_cancelled() {
            // Safety: non-null callback input owned by the caller for this call.
            unsafe { (*data_in).user_interrupt = 1 };
        }
    }));
}

/// Column-wise model data converted to native layout in original ID order.
struct Loaded {
    num_col: HighsInt,
    num_row: HighsInt,
    cost: Vec<f64>,
    col_lower: Vec<f64>,
    col_upper: Vec<f64>,
    row_lower: Vec<f64>,
    row_upper: Vec<f64>,
    start: Vec<HighsInt>,
    index: Vec<HighsInt>,
    value: Vec<f64>,
    integrality: Vec<HighsInt>,
    discrete: bool,
    sense: HighsInt,
    offset: f64,
}

fn native_index(value: usize, context: &str) -> Result<HighsInt, ValidationError> {
    HighsInt::try_from(value).map_err(|_| {
        error(
            ErrorKind::Unsupported,
            format!("{context}: {value} exceeds the native 32-bit index range"),
        )
    })
}

fn convert(model: &Model, infinity: f64) -> Result<Loaded, ValidationError> {
    let document = model.document();
    let num_col = native_index(document.variables.len(), "variable count")?;
    let num_row = native_index(document.constraints.len(), "constraint count")?;

    // Extended-real bounds become the backend's own infinity sentinels; finite
    // values are passed through unchanged.
    let bound_value = |bound: Bound| match bound {
        Bound::Finite { value } => value,
        Bound::NegativeInfinity => -infinity,
        Bound::PositiveInfinity => infinity,
    };

    let mut col_lower = Vec::with_capacity(document.variables.len());
    let mut col_upper = Vec::with_capacity(document.variables.len());
    let mut integrality = Vec::with_capacity(document.variables.len());
    let mut discrete = false;

    for variable in &document.variables {
        let mut lower = bound_value(variable.lower);
        let mut upper = bound_value(variable.upper);
        // A binary variable is in {0,1} regardless of its declared bounds, so
        // the native domain is the intersection with [0,1].
        if variable.domain == Domain::Binary {
            lower = lower.max(0.0);
            upper = upper.min(1.0);
            if lower > upper {
                return Err(error(
                    ErrorKind::Structural,
                    format!(
                        "variable {}: binary bounds do not intersect [0,1]",
                        variable.id
                    ),
                ));
            }
        }
        col_lower.push(lower);
        col_upper.push(upper);
        integrality.push(match variable.domain {
            Domain::Continuous => ffi::K_HIGHS_VAR_TYPE_CONTINUOUS,
            Domain::Integer | Domain::Binary => {
                discrete = true;
                ffi::K_HIGHS_VAR_TYPE_INTEGER
            }
        });
    }

    // Objective coefficients in original variable order; absent terms are zero.
    let mut cost = vec![0.0; document.variables.len()];
    for term in &document.objective.terms {
        let position = document
            .variables
            .binary_search_by_key(&term.variable_id, |v| v.id)
            .map_err(|_| {
                error(
                    ErrorKind::Structural,
                    format!("objective references unknown variable {}", term.variable_id),
                )
            })?;
        cost[position] = term.coefficient;
    }

    let mut row_lower = Vec::with_capacity(document.constraints.len());
    let mut row_upper = Vec::with_capacity(document.constraints.len());
    let mut start = Vec::with_capacity(document.constraints.len() + 1);
    let mut index = Vec::new();
    let mut value = Vec::new();

    for constraint in &document.constraints {
        row_lower.push(bound_value(constraint.lower));
        row_upper.push(bound_value(constraint.upper));
        start.push(native_index(index.len(), "matrix start")?);
        for term in &constraint.terms {
            // Zero coefficients are structural in the original model and are
            // preserved by the core, but HiGHS would drop them. Skipping an
            // exact zero changes no activity; a small nonzero would change the
            // model silently, so reject it instead.
            if term.coefficient == 0.0 {
                continue;
            }
            if term.coefficient.abs() < SMALL_MATRIX_VALUE {
                return Err(error(
                    ErrorKind::Unsupported,
                    format!(
                        "constraint {}, variable {}: coefficient {} is below the native small-matrix threshold {SMALL_MATRIX_VALUE}",
                        constraint.id, term.variable_id, term.coefficient
                    ),
                ));
            }
            let position = document
                .variables
                .binary_search_by_key(&term.variable_id, |v| v.id)
                .map_err(|_| {
                    error(
                        ErrorKind::Structural,
                        format!(
                            "constraint {} references unknown variable {}",
                            constraint.id, term.variable_id
                        ),
                    )
                })?;
            index.push(native_index(position, "matrix index")?);
            value.push(term.coefficient);
        }
    }
    let num_nz = native_index(index.len(), "matrix nonzeros")?;
    start.push(num_nz);

    Ok(Loaded {
        num_col,
        num_row,
        cost,
        col_lower,
        col_upper,
        row_lower,
        row_upper,
        start,
        index,
        value,
        integrality,
        discrete,
        sense: match document.objective.sense {
            optimizer_core::ObjectiveSense::Minimize => ffi::K_HIGHS_OBJ_SENSE_MINIMIZE,
            optimizer_core::ObjectiveSense::Maximize => ffi::K_HIGHS_OBJ_SENSE_MAXIMIZE,
        },
        offset: document.objective.offset,
    })
}

/// Map every native model status explicitly.
///
/// There is deliberately no catch-all arm: a HiGHS upgrade that adds a status
/// must fail to compile rather than be silently mis-classified.
fn map_status(status: HighsInt) -> Result<(Termination, &'static str), ValidationError> {
    let mapped = match status {
        ffi::K_HIGHS_MODEL_STATUS_OPTIMAL => (Termination::Optimal, "optimal"),
        ffi::K_HIGHS_MODEL_STATUS_INFEASIBLE => (Termination::Infeasible, "infeasible"),
        ffi::K_HIGHS_MODEL_STATUS_UNBOUNDED => (Termination::Unbounded, "unbounded"),
        ffi::K_HIGHS_MODEL_STATUS_UNBOUNDED_OR_INFEASIBLE => (
            Termination::UnboundedOrInfeasible,
            "unbounded_or_infeasible",
        ),
        ffi::K_HIGHS_MODEL_STATUS_TIME_LIMIT => (Termination::TimeLimit, "time_limit"),
        ffi::K_HIGHS_MODEL_STATUS_ITERATION_LIMIT => {
            (Termination::IterationLimit, "iteration_limit")
        }
        ffi::K_HIGHS_MODEL_STATUS_SOLUTION_LIMIT => (Termination::NodeLimit, "solution_limit"),
        ffi::K_HIGHS_MODEL_STATUS_INTERRUPT => (Termination::Interrupted, "interrupt"),
        // A bound/target stop is a limit, not a completed proof.
        ffi::K_HIGHS_MODEL_STATUS_OBJECTIVE_BOUND => (Termination::NodeLimit, "objective_bound"),
        ffi::K_HIGHS_MODEL_STATUS_OBJECTIVE_TARGET => (Termination::NodeLimit, "objective_target"),
        // An empty native model is classified from the original model instead.
        ffi::K_HIGHS_MODEL_STATUS_MODEL_EMPTY => (Termination::Feasible, "model_empty"),
        ffi::K_HIGHS_MODEL_STATUS_UNKNOWN => (Termination::NumericalFailure, "unknown"),
        ffi::K_HIGHS_MODEL_STATUS_NOTSET => (Termination::BackendFailure, "notset"),
        ffi::K_HIGHS_MODEL_STATUS_LOAD_ERROR => (Termination::BackendFailure, "load_error"),
        ffi::K_HIGHS_MODEL_STATUS_MODEL_ERROR => (Termination::BackendFailure, "model_error"),
        ffi::K_HIGHS_MODEL_STATUS_PRESOLVE_ERROR => (Termination::BackendFailure, "presolve_error"),
        ffi::K_HIGHS_MODEL_STATUS_SOLVE_ERROR => (Termination::BackendFailure, "solve_error"),
        ffi::K_HIGHS_MODEL_STATUS_POSTSOLVE_ERROR => {
            (Termination::BackendFailure, "postsolve_error")
        }
        other => {
            return Err(error(
                ErrorKind::Backend,
                format!("unrecognized native model status {other}"),
            ));
        }
    };
    Ok(mapped)
}

fn basis_status(native: HighsInt) -> Option<BasisStatus> {
    match native {
        ffi::K_HIGHS_BASIS_STATUS_LOWER => Some(BasisStatus::Lower),
        ffi::K_HIGHS_BASIS_STATUS_BASIC => Some(BasisStatus::Basic),
        ffi::K_HIGHS_BASIS_STATUS_UPPER => Some(BasisStatus::Upper),
        ffi::K_HIGHS_BASIS_STATUS_ZERO => Some(BasisStatus::Zero),
        ffi::K_HIGHS_BASIS_STATUS_NONBASIC => Some(BasisStatus::Nonbasic),
        _ => None,
    }
}

fn native_basis(status: BasisStatus) -> HighsInt {
    match status {
        BasisStatus::Lower => ffi::K_HIGHS_BASIS_STATUS_LOWER,
        BasisStatus::Basic => ffi::K_HIGHS_BASIS_STATUS_BASIC,
        BasisStatus::Upper => ffi::K_HIGHS_BASIS_STATUS_UPPER,
        BasisStatus::Zero => ffi::K_HIGHS_BASIS_STATUS_ZERO,
        BasisStatus::Nonbasic => ffi::K_HIGHS_BASIS_STATUS_NONBASIC,
    }
}

/// Read the current basis, when one is available and fully recognized.
fn extract_basis(
    highs: &Highs,
    model: &Model,
    loaded: &Loaded,
) -> Result<Option<Basis>, ValidationError> {
    let mut columns = vec![0 as HighsInt; loaded.col_lower.len()];
    let mut rows = vec![0 as HighsInt; loaded.row_lower.len()];
    // Safety: valid handle; buffers sized to the loaded dimensions.
    let status =
        unsafe { ffi::Highs_getBasis(highs.as_ptr(), columns.as_mut_ptr(), rows.as_mut_ptr()) };
    if status != ffi::K_HIGHS_STATUS_OK {
        return Ok(None);
    }
    let (Some(columns), Some(rows)) = (
        columns
            .iter()
            .copied()
            .map(basis_status)
            .collect::<Option<Vec<_>>>(),
        rows.iter()
            .copied()
            .map(basis_status)
            .collect::<Option<Vec<_>>>(),
    ) else {
        return Ok(None);
    };
    Ok(Some(Basis {
        schema_version: SOLVE_SCHEMA_VERSION,
        model_id: model.document().model_id.clone(),
        model_fingerprint: model.fingerprint()?,
        columns,
        rows,
    }))
}

fn apply_warm_start(
    highs: &Highs,
    model: &Model,
    loaded: &Loaded,
    warm_start: WarmStart<'_>,
    warnings: &mut Vec<String>,
    tolerances: optimizer_core::Tolerances,
) -> Result<(), ValidationError> {
    match warm_start {
        WarmStart::Candidate(candidate) => {
            // Only a candidate that is valid for this exact model may be passed.
            let report = model.evaluate(candidate, tolerances)?;
            if !report.feasible {
                return Err(error(
                    ErrorKind::Candidate,
                    "warm-start candidate is infeasible for the original model",
                ));
            }
            let values: Vec<c_double> = report.variables.iter().map(|check| check.value).collect();
            // Safety: valid handle; column buffer matches the loaded columns.
            let status = unsafe {
                ffi::Highs_setSolution(
                    highs.as_ptr(),
                    values.as_ptr(),
                    std::ptr::null(),
                    std::ptr::null(),
                    std::ptr::null(),
                )
            };
            check(status, "set warm-start solution")?;
        }
        WarmStart::Basis(basis) => {
            if basis.schema_version != SOLVE_SCHEMA_VERSION {
                return Err(error(
                    ErrorKind::Document,
                    format!("unsupported basis schema_version {}", basis.schema_version),
                ));
            }
            let document = model.document();
            if basis.model_id != document.model_id {
                return Err(error(
                    ErrorKind::Unsupported,
                    "basis model_id does not match the model",
                ));
            }
            // A basis is bound to exact canonical data, not just an identity.
            if basis.model_fingerprint != model.fingerprint()? {
                return Err(error(
                    ErrorKind::Unsupported,
                    "basis does not match the canonical model fingerprint",
                ));
            }
            if basis.columns.len() != loaded.col_lower.len()
                || basis.rows.len() != loaded.row_lower.len()
            {
                return Err(error(
                    ErrorKind::Unsupported,
                    "basis dimensions do not match the model",
                ));
            }
            if loaded.discrete {
                warnings.push("basis warm start ignored for a discrete model".to_string());
                return Ok(());
            }
            let columns: Vec<HighsInt> = basis.columns.iter().copied().map(native_basis).collect();
            let rows: Vec<HighsInt> = basis.rows.iter().copied().map(native_basis).collect();
            // Safety: valid handle; buffers match the loaded dimensions.
            let status =
                unsafe { ffi::Highs_setBasis(highs.as_ptr(), columns.as_ptr(), rows.as_ptr()) };
            check(status, "set warm-start basis")?;
        }
    }
    Ok(())
}

/// Whether a caller wants the final LP basis alongside the record.
///
/// Extracting one is not free: it reads the native basis and computes the
/// model's canonical fingerprint, which serializes the whole model. On a
/// branch-and-bound node that cost is pure waste, because node relaxations are
/// always continuous so the basis is always extracted, `Backend::solve` discards
/// it immediately, and SPEC-0003 requirement 23 forbids reusing one across nodes
/// anyway.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) enum BasisRequest {
    /// Extract the basis, for a caller that will warm start from it.
    Extract,
    /// Skip extraction; the caller discards the basis.
    Skip,
}

/// Solve one model with the pinned native library.
///
/// The returned basis accompanies an accepted LP incumbent so a later solve can
/// warm start from it; it is `None` whenever no usable basis exists, and whenever
/// the caller asked for [`BasisRequest::Skip`].
pub(crate) fn solve(
    model: &Model,
    options: &SolveOptions,
    cancel: &CancellationToken,
    warm_start: Option<WarmStart<'_>>,
    basis_request: BasisRequest,
) -> Result<(SolveRecord, Option<Basis>), ValidationError> {
    let started = Instant::now();
    let mut warnings = Vec::new();

    // Every non-final return path reports no basis; the accepted-incumbent
    // path below attaches one when the backend produced it.
    let record = |termination: Termination,
                  native_status: Option<&str>,
                  objective: Option<f64>,
                  best_bound: Option<f64>,
                  gap: Option<f64>,
                  candidate: Option<Candidate>,
                  validation: Option<optimizer_core::ValidationReport>,
                  warnings: Vec<String>,
                  backend_version: String|
     -> (SolveRecord, Option<Basis>) {
        (
            SolveRecord {
                schema_version: SOLVE_SCHEMA_VERSION,
                model_id: model.document().model_id.clone(),
                backend: BACKEND_NAME.to_string(),
                backend_version,
                termination,
                native_status: native_status.map(str::to_string),
                objective,
                best_bound,
                gap,
                candidate,
                validation,
                warnings,
                elapsed_ms: u64::try_from(started.elapsed().as_millis()).unwrap_or(u64::MAX),
                options: options.clone(),
            },
            None,
        )
    };

    // Cancellation before any native work is handled by the caller, so a
    // solve reaching this point creates native state.
    let _guard = native_lock();
    let highs = Highs::new()?;
    let backend_version = version();

    // Silence native logging and pin determinism and thread count. The log file
    // is disabled explicitly: HiGHS otherwise writes HiGHS.log into the current
    // working directory, which would litter the workspace during tests.
    highs.set_bool(c"output_flag", false)?;
    highs.set_bool(c"log_to_console", false)?;
    highs.set_string(c"log_file", c"")?;
    highs.set_int(c"threads", 1)?;
    highs.set_string(c"solver", c"choose")?;
    highs.set_int(c"random_seed", seed_for_native(options.seed))?;
    highs.set_double(c"primal_feasibility_tolerance", options.tolerances.absolute)?;
    highs.set_double(c"dual_feasibility_tolerance", options.tolerances.absolute)?;
    // Native integrality tolerance is configured separately from the
    // original-model validation policy applied after extraction.
    highs.set_double(
        c"mip_feasibility_tolerance",
        options.tolerances.integrality.max(1e-9),
    )?;
    if let Some(limit) = options.time_limit_ms {
        #[expect(clippy::cast_precision_loss, reason = "millisecond limit to seconds")]
        highs.set_double(c"time_limit", limit as f64 / 1000.0)?;
    }
    if let Some(limit) = options.iteration_limit {
        highs.set_int(c"simplex_iteration_limit", clamp_limit(limit))?;
    }
    if let Some(limit) = options.node_limit {
        highs.set_int(c"mip_max_nodes", clamp_limit(limit))?;
    }

    let infinity = highs.infinity();
    let loaded = convert(model, infinity)?;

    // Safety: buffers outlive the call and match the declared dimensions.
    let status = unsafe {
        if loaded.discrete {
            ffi::Highs_passMip(
                highs.as_ptr(),
                loaded.num_col,
                loaded.num_row,
                native_index(loaded.index.len(), "matrix nonzeros")?,
                ffi::K_HIGHS_MATRIX_FORMAT_ROWWISE,
                loaded.sense,
                loaded.offset,
                loaded.cost.as_ptr(),
                loaded.col_lower.as_ptr(),
                loaded.col_upper.as_ptr(),
                loaded.row_lower.as_ptr(),
                loaded.row_upper.as_ptr(),
                loaded.start.as_ptr(),
                loaded.index.as_ptr(),
                loaded.value.as_ptr(),
                loaded.integrality.as_ptr(),
            )
        } else {
            ffi::Highs_passLp(
                highs.as_ptr(),
                loaded.num_col,
                loaded.num_row,
                native_index(loaded.index.len(), "matrix nonzeros")?,
                ffi::K_HIGHS_MATRIX_FORMAT_ROWWISE,
                loaded.sense,
                loaded.offset,
                loaded.cost.as_ptr(),
                loaded.col_lower.as_ptr(),
                loaded.col_upper.as_ptr(),
                loaded.row_lower.as_ptr(),
                loaded.row_upper.as_ptr(),
                loaded.start.as_ptr(),
                loaded.index.as_ptr(),
                loaded.value.as_ptr(),
            )
        }
    };
    check(status, "load model")?;

    if let Some(warm_start) = warm_start {
        apply_warm_start(
            &highs,
            model,
            &loaded,
            warm_start,
            &mut warnings,
            options.tolerances,
        )?;
    }

    // The interrupt state must outlive every native callback invocation.
    let interrupt = Box::new(Interrupt {
        cancel: cancel.clone(),
    });
    let interrupt_ptr: *const Interrupt = &raw const *interrupt;
    // Safety: the callback and its data stay valid until after Highs_run
    // returns, and the trampoline cannot unwind.
    unsafe {
        check(
            ffi::Highs_setCallback(
                highs.as_ptr(),
                Some(interrupt_callback),
                interrupt_ptr.cast_mut().cast::<c_void>(),
            ),
            "register interrupt callback",
        )?;
        for kind in [
            ffi::K_HIGHS_CALLBACK_SIMPLEX_INTERRUPT,
            ffi::K_HIGHS_CALLBACK_IPM_INTERRUPT,
            ffi::K_HIGHS_CALLBACK_MIP_INTERRUPT,
        ] {
            check(
                ffi::Highs_startCallback(highs.as_ptr(), kind),
                "start interrupt callback",
            )?;
        }
    }

    // Safety: valid handle; the callback data is still alive.
    let run_status = unsafe { ffi::Highs_run(highs.as_ptr()) };
    // Safety: valid handle.
    let model_status = unsafe { ffi::Highs_getModelStatus(highs.as_ptr()) };
    drop(interrupt);

    if run_status == ffi::K_HIGHS_STATUS_ERROR {
        return Ok(record(
            Termination::BackendFailure,
            Some("run_error"),
            None,
            None,
            None,
            None,
            None,
            warnings,
            backend_version,
        ));
    }
    if run_status == ffi::K_HIGHS_STATUS_WARNING {
        warnings.push("HiGHS reported a warning status for this solve".to_string());
    }

    let (mut termination, native_name) = map_status(model_status)?;

    // Cancellation observed during the solve outranks a native limit label.
    if cancel.is_cancelled() && !termination.is_complete() {
        termination = Termination::Interrupted;
    }

    // Unboundedness and infeasibility are backend evidence, not incumbents.
    if matches!(
        termination,
        Termination::Infeasible
            | Termination::Unbounded
            | Termination::UnboundedOrInfeasible
            | Termination::BackendFailure
            | Termination::NumericalFailure
    ) {
        return Ok(record(
            termination,
            Some(native_name),
            None,
            None,
            None,
            None,
            None,
            warnings,
            backend_version,
        ));
    }

    // Extract the primal solution and re-validate it against the original
    // model. Native output is never published unchecked.
    let mut values = vec![0.0f64; loaded.col_lower.len()];
    // Safety: valid handle; buffer matches the loaded column count.
    let extract = unsafe {
        ffi::Highs_getSolution(
            highs.as_ptr(),
            values.as_mut_ptr(),
            std::ptr::null_mut(),
            std::ptr::null_mut(),
            std::ptr::null_mut(),
        )
    };

    if extract != ffi::K_HIGHS_STATUS_OK {
        // No usable primal solution. A limit stays a limit; anything else that
        // claimed completion without a solution is a numerical failure.
        let termination = if termination.is_complete() {
            Termination::NumericalFailure
        } else {
            termination
        };
        return Ok(record(
            termination,
            Some(native_name),
            None,
            highs.double_info(c"mip_dual_bound"),
            None,
            None,
            None,
            warnings,
            backend_version,
        ));
    }

    let candidate = Candidate {
        schema_version: optimizer_core::SCHEMA_VERSION,
        model_id: model.document().model_id.clone(),
        values: model
            .document()
            .variables
            .iter()
            .zip(&values)
            .map(|(variable, value)| Assignment {
                variable_id: variable.id,
                value: *value,
            })
            .collect(),
    };

    let validation = match model.evaluate(&candidate, options.tolerances) {
        Ok(report) => report,
        Err(failure) => {
            // Native output that cannot even be evaluated is a numerical
            // failure, never an optimality claim.
            warnings.push(format!("native solution rejected: {failure}"));
            return Ok(record(
                Termination::NumericalFailure,
                Some(native_name),
                None,
                None,
                None,
                None,
                None,
                warnings,
                backend_version,
            ));
        }
    };

    if !validation.feasible {
        warnings
            .push("native solution violates the original model under recorded tolerances".into());
        return Ok(record(
            Termination::NumericalFailure,
            Some(native_name),
            None,
            None,
            None,
            Some(candidate),
            Some(validation),
            warnings,
            backend_version,
        ));
    }

    // A validated incumbent under a limit or interruption is feasible, not
    // optimal: only a native optimality claim may be reported as such.
    if termination != Termination::Optimal {
        termination = match termination {
            Termination::TimeLimit
            | Termination::IterationLimit
            | Termination::NodeLimit
            | Termination::Interrupted => termination,
            _ => Termination::Feasible,
        };
    }

    let objective = finite_or_absent(validation.objective);
    let best_bound =
        highs
            .double_info(c"mip_dual_bound")
            .or(if loaded.discrete { None } else { objective });
    let gap = highs.double_info(c"mip_gap");

    // Retain the native work counters so a record states how much search the
    // reported outcome actually took.
    if let Some(nodes) = highs.int_info(c"mip_node_count") {
        warnings.push(format!("native mip_node_count={nodes}"));
    }
    if let Some(iterations) = highs.int_info(c"simplex_iteration_count") {
        warnings.push(format!("native simplex_iteration_count={iterations}"));
    }

    // A basis is only meaningful for a continuous relaxation, and only worth
    // extracting when a caller asked for one. The discrete arm is kept even
    // though every branch-and-bound node relaxation is continuous: this is
    // backend code and must not depend on a solver-side invariant, and
    // `solve_with_basis` is reachable with a discrete model.
    let basis = match (loaded.discrete, basis_request) {
        (true, _) | (_, BasisRequest::Skip) => None,
        (false, BasisRequest::Extract) => extract_basis(&highs, model, &loaded)?,
    };

    let (accepted, _) = record(
        termination,
        Some(native_name),
        objective,
        best_bound,
        gap,
        Some(candidate),
        Some(validation),
        warnings,
        backend_version,
    );
    Ok((accepted, basis))
}

/// HiGHS takes a 32-bit seed; fold the recorded 64-bit seed deterministically.
fn seed_for_native(seed: u64) -> HighsInt {
    let folded = (seed ^ (seed >> 32)) & 0x7fff_ffff;
    HighsInt::try_from(folded).unwrap_or(HighsInt::MAX)
}

/// Saturate a 64-bit limit into the native 32-bit option range.
fn clamp_limit(limit: u64) -> HighsInt {
    HighsInt::try_from(limit).unwrap_or(HighsInt::MAX)
}
