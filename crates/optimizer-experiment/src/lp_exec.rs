//! Strict study-only ADR-0035 requests and independently assessed witnesses.
#![allow(missing_docs)]
use crate::{lp::Assessment, serde_strict::deserialize_required_object};
use optimizer_core::{
    Assignment, CancellationToken, Candidate, ErrorKind, Fp64ExecutionSettings, LpDiagnostics,
    LpExecutionDiagnostics, LpSettings, Model, SolveOptions, SolveRecord, Termination,
    ValidationError,
};
use optimizer_lp::{
    Engine, LinearProgram, certify,
    certify::assess_gap,
    control::Fp64Controller,
    exec::{Mode, PEAK_CAP, RESIDENT_CAP, Receipt, prepare_operator},
};
use optimizer_lp_cuda::exec::{Executor, code_object_path};
use serde::Serialize;
use std::{
    rc::Rc,
    time::{Duration, Instant},
};

#[derive(Clone, Debug, PartialEq, Serialize)]
pub struct Request {
    pub schema_version: u32,
    pub mode: Mode,
    pub model_sha256: String,
    pub source_tree_sha256: String,
    pub executable_sha256: String,
    pub code_object_sha256: String,
    pub device: String,
    pub options: SolveOptions,
    pub method: LpSettings,
    pub profile: bool,
    pub device_buffer_bytes: u64,
}
deserialize_required_object!(Request {
    schema_version: u32,
    mode: Mode,
    model_sha256: String,
    source_tree_sha256: String,
    executable_sha256: String,
    code_object_sha256: String,
    device: String,
    options: SolveOptions,
    method: LpSettings,
    profile: bool,
    device_buffer_bytes: u64
});
#[derive(Clone, Debug, PartialEq, Serialize)]
pub struct Witness {
    pub request: Request,
    pub executed_device: Option<String>,
    pub variable_ids: Vec<u32>,
    pub row_ids: Vec<u32>,
    pub primal: Option<Vec<f64>>,
    pub dual: Option<Vec<f64>>,
    pub status: String,
    pub failure: Option<String>,
    pub proposed_steps: u64,
    pub committed_steps: u64,
    pub physical_steps: Option<u64>,
    pub witness_iteration: u64,
    pub vector_decodes: u64,
    pub proposed_products: u64,
    pub rounding_flags: u32,
    pub allocation_upload_ns: Option<u64>,
    pub diagnostics: LpDiagnostics,
    pub execution: Option<LpExecutionDiagnostics>,
    pub operator_bounds: Option<[f64; 2]>,
    pub step: Option<f64>,
    pub scaling_error_max: Option<f64>,
    pub scaling_sha256: Option<String>,
    pub operator_receipt: Option<Receipt>,
}
deserialize_required_object!(Witness {request:Request,executed_device:Option<String>,variable_ids:Vec<u32>,row_ids:Vec<u32>,primal:Option<Vec<f64>>,dual:Option<Vec<f64>>,status:String,failure:Option<String>,proposed_steps:u64,committed_steps:u64,physical_steps:Option<u64>,witness_iteration:u64,vector_decodes:u64,proposed_products:u64,rounding_flags:u32,allocation_upload_ns:Option<u64>,diagnostics:LpDiagnostics,execution:Option<LpExecutionDiagnostics>,operator_bounds:Option<[f64;2]>,step:Option<f64>,scaling_error_max:Option<f64>,scaling_sha256:Option<String>,operator_receipt:Option<Receipt>});
#[derive(Clone, Debug, PartialEq, Serialize)]
pub struct Evidence {
    pub schema_version: u32,
    pub witness: Witness,
    pub assessment: Assessment,
    pub payload_sha256: String,
}
deserialize_required_object!(Evidence {
    schema_version: u32,
    witness: Witness,
    assessment: Assessment,
    payload_sha256: String
});
fn invalid(s: impl ToString) -> ValidationError {
    ValidationError::new(ErrorKind::Document, s.to_string())
}
fn hash_ok(s: &str) -> bool {
    s.len() == 64
        && s.bytes()
            .all(|b| b.is_ascii_digit() || (b'a'..=b'f').contains(&b))
}
impl Request {
    pub fn from_json(bytes: &[u8]) -> Result<Self, ValidationError> {
        crate::lp::unique_json(bytes)?;
        let r: Self = serde_json::from_slice(bytes).map_err(invalid)?;
        r.validate()?;
        Ok(r)
    }
    pub fn validate(&self) -> Result<(), ValidationError> {
        self.options.validate()?;
        self.method.validate()?;
        if self.schema_version != 1
            || !self.device.starts_with("GPU-")
            || self.device_buffer_bytes == 0
            || [
                &self.model_sha256,
                &self.source_tree_sha256,
                &self.executable_sha256,
                &self.code_object_sha256,
            ]
            .into_iter()
            .any(|s| !hash_ok(s))
            || self.options.iteration_limit != Some(self.method.iteration_limit)
            || self
                .options
                .time_limit_ms
                .is_none_or(|v| v == 0 || v > 30000)
            || self.method.iteration_limit > 50000
            || self.device_buffer_bytes > RESIDENT_CAP
        {
            return Err(invalid("research request identity/limits"));
        }
        Ok(())
    }
}
// A private, independently constructed host input. Its model, canonical LP and
// exact-byte identity are inseparable; neither device data nor evidence supplies
// them. A batch holds one base and at most one materialized bounds variant.
struct HostInput {
    model: Model,
    program: LinearProgram,
    model_sha256: String,
}

impl HostInput {
    fn from_bytes(bytes: &[u8]) -> Result<Self, ValidationError> {
        let model = Model::from_json(bytes)?;
        let program = LinearProgram::new(&model)?;
        Ok(Self {
            model,
            program,
            model_sha256: crate::sha256::hex(bytes),
        })
    }
}

fn assessment(input: &HostInput, w: &Witness) -> Result<Assessment, ValidationError> {
    let model = &input.model;
    let program = &input.program;
    let candidate = w.primal.as_ref().map(|p| Candidate {
        schema_version: 1,
        model_id: model.document().model_id.clone(),
        values: program
            .variable_ids()
            .iter()
            .zip(p)
            .map(|(&variable_id, &value)| Assignment { variable_id, value })
            .collect(),
    });
    let report = candidate
        .as_ref()
        .map(|c| model.evaluate(c, w.request.options.tolerances))
        .transpose()?;
    let bound = w
        .dual
        .as_ref()
        .and_then(|v| certify(program, v).ok())
        .map(|c| c.bound);
    let gap = report
        .as_ref()
        .filter(|v| v.feasible)
        .and(w.primal.as_ref())
        .and_then(|p| bound.and_then(|b| assess_gap(program, p, b, w.request.options.tolerances)))
        .map(|g| g.upper);
    let termination = match w.status.as_str() {
        "accepted" => Termination::Feasible,
        "iteration_limit" => Termination::IterationLimit,
        "time_limit" => Termination::TimeLimit,
        "interrupted" => Termination::Interrupted,
        "numerical_failure" => Termination::NumericalFailure,
        "device_failure" => Termination::BackendFailure,
        "unsupported" => Termination::Unsupported,
        _ => return Err(invalid("research status")),
    };
    let record = SolveRecord {
        schema_version: 2,
        model_id: model.document().model_id.clone(),
        backend: "lp-exec-v1-witness".into(),
        backend_version: "1".into(),
        termination,
        native_status: None,
        objective: report.as_ref().filter(|r| r.feasible).map(|r| r.objective),
        best_bound: bound,
        gap,
        candidate,
        validation: report,
        warnings: vec![],
        elapsed_ms: 0,
        options: w.request.options.clone(),
        lp_settings: None,
        lp_execution: None,
        lp_precision: None,
        lp_adaptive: None,
    };
    let mut d = LpDiagnostics::new(true, false);
    d.dual = w.dual.clone();
    crate::lp::assess_program(model, program, &record, &d)
}
// Only matrix-derived verification metadata is reusable. This cache is private,
// rebuilt from the original host model (never session/device observations), and
// checked against each record's complete method, mode and canonical program.
// Candidate evaluation, bound certification and gap assessment remain per solve.
struct OperatorVerification {
    bounds: [f64; 2],
    step: f64,
    scaling_error_max: f64,
    scaling_sha256: String,
    receipt: Receipt,
}

impl OperatorVerification {
    fn new(
        program: &LinearProgram,
        method: LpSettings,
        _mode: Mode,
    ) -> Result<Self, ValidationError> {
        let engine = Engine::new(program, method);
        let op = prepare_operator(&engine, RESIDENT_CAP, PEAK_CAP).map_err(invalid)?;
        let scales = crate::sha256::hex(
            &serde_json::to_vec(&(
                engine.preconditioner().row(),
                engine.preconditioner().column(),
            ))
            .map_err(invalid)?,
        );
        Ok(Self {
            bounds: op.bounds(),
            step: op.step(),
            scaling_error_max: op
                .receipt()
                .original_error_infinity
                .max(op.receipt().original_error_one),
            receipt: op.receipt().clone(),
            scaling_sha256: scales,
        })
    }
}

#[derive(Default)]
struct OperatorCache {
    entry: Option<(LinearProgram, LpSettings, Mode, OperatorVerification)>,
    #[cfg(test)]
    preparations: usize,
}

impl OperatorCache {
    fn get(
        &mut self,
        program: &LinearProgram,
        request: &Request,
    ) -> Result<&OperatorVerification, ValidationError> {
        let matches = self
            .entry
            .as_ref()
            .is_some_and(|(cached, method, mode, _)| {
                *method == request.method
                    && *mode == request.mode
                    && cached.same_matrix_objective_rows(program)
            });
        if !matches {
            let verified = OperatorVerification::new(program, request.method, request.mode)?;
            self.entry = Some((program.clone(), request.method, request.mode, verified));
            #[cfg(test)]
            {
                self.preparations += 1;
            }
        }
        Ok(&self.entry.as_ref().expect("verified operator").3)
    }
}

impl Evidence {
    pub fn from_json(bytes: &[u8]) -> Result<Self, ValidationError> {
        crate::lp::unique_json(bytes)?;
        serde_json::from_slice(bytes).map_err(invalid)
    }
    pub fn new(bytes: &[u8], witness: Witness) -> Result<Self, ValidationError> {
        Self::new_with_cache(bytes, witness, None)
    }
    fn new_with_cache(
        bytes: &[u8],
        witness: Witness,
        operator_cache: Option<&mut OperatorCache>,
    ) -> Result<Self, ValidationError> {
        let input = HostInput::from_bytes(bytes)?;
        Self::new_for_input(&input, witness, operator_cache)
    }
    fn new_for_input(
        input: &HostInput,
        witness: Witness,
        operator_cache: Option<&mut OperatorCache>,
    ) -> Result<Self, ValidationError> {
        let result = Self {
            schema_version: witness.request.schema_version,
            assessment: assessment(input, &witness)?,
            payload_sha256: crate::sha256::hex(&serde_json::to_vec(&witness).map_err(invalid)?),
            witness,
        };
        result.verify_for_input(input, &result.witness.request, operator_cache)?;
        Ok(result)
    }
    pub fn verify(&self, bytes: &[u8], expected: &Request) -> Result<(), ValidationError> {
        self.verify_with_cache(bytes, expected, None)
    }
    fn verify_with_cache(
        &self,
        bytes: &[u8],
        expected: &Request,
        operator_cache: Option<&mut OperatorCache>,
    ) -> Result<(), ValidationError> {
        let input = HostInput::from_bytes(bytes)?;
        self.verify_for_input(&input, expected, operator_cache)
    }
    fn verify_for_input(
        &self,
        input: &HostInput,
        expected: &Request,
        operator_cache: Option<&mut OperatorCache>,
    ) -> Result<(), ValidationError> {
        let w = &self.witness;
        w.request.validate()?;
        let model = &input.model;
        let p = &input.program;
        if self.schema_version != w.request.schema_version
            || &w.request != expected
            || !w.diagnostics.enabled
            || w.diagnostics.profile != w.request.profile
            || w.diagnostics.device_buffer_limit_bytes != Some(w.request.device_buffer_bytes)
            || w.request.model_sha256 != input.model_sha256
            || self.payload_sha256 != crate::sha256::hex(&serde_json::to_vec(w).map_err(invalid)?)
            || w.variable_ids != p.variable_ids()
            || w.row_ids
                != model
                    .document()
                    .constraints
                    .iter()
                    .map(|r| r.id)
                    .collect::<Vec<_>>()
            || w.executed_device
                .as_ref()
                .is_some_and(|d| d != &w.request.device)
            || (w.proposed_steps > 0 && w.executed_device.is_none())
            || w.proposed_steps > w.request.method.iteration_limit
            || w.committed_steps > w.proposed_steps
            || w.witness_iteration > w.committed_steps
            || w.physical_steps.is_some_and(|v| v != w.proposed_steps)
            || (w.physical_steps.is_none() && w.status != "device_failure")
            || w.primal
                .as_ref()
                .is_some_and(|v| v.len() != p.column_count() || v.iter().any(|x| !x.is_finite()))
            || w.dual
                .as_ref()
                .is_some_and(|v| v.len() != p.row_count() || v.iter().any(|x| !x.is_finite()))
            || w.primal.is_some() != w.dual.is_some()
            || self.assessment != assessment(input, w)?
        {
            return Err(invalid(
                "exec evidence identity, work or assessment differs",
            ));
        }
        let products = w
            .proposed_steps
            .checked_mul(2)
            .and_then(|n| n.checked_mul(p.nonzeros() as u64))
            .ok_or_else(|| invalid("work overflow"))?;
        if w.rounding_flags & !7 != 0 {
            return Err(invalid("rounding flags differ"));
        }
        let decodes = w
            .proposed_steps
            .checked_mul(if w.request.mode == Mode::Cached {
                (p.row_count() + p.column_count()) as u64
            } else {
                4 * p.nonzeros() as u64
            })
            .ok_or_else(|| invalid("work overflow"))?;
        let launches = w
            .proposed_steps
            .checked_mul(if w.request.mode == Mode::Cached { 8 } else { 6 })
            .ok_or_else(|| invalid("work overflow"))?;
        let fusion = optimizer_core::Fp64Fusion::Separate;
        if w.vector_decodes != decodes || w.proposed_products != products {
            return Err(invalid("exec work differs"));
        }

        if let Some(exec) = &w.execution
            && (exec.settings
                != Fp64ExecutionSettings {
                    schema_version: 1,
                    allocation: optimizer_core::WorkingAllocation::Resident,
                    uploads: optimizer_core::StateUploads::Necessary,
                    reduction: optimizer_core::Fp64Reduction::Warp32V1,
                    fusion,
                }
                || exec.code_object_sha256.as_ref() != Some(&w.request.code_object_sha256)
                || (w.physical_steps.is_some() && exec.kernel_launches != launches)
                || w.diagnostics
                    .device_buffer_peak_bytes
                    .is_some_and(|n| n > w.request.device_buffer_bytes))
        {
            return Err(invalid("exec execution differs"));
        }
        if w.operator_bounds.is_some()
            || w.executed_device.is_some()
            || w.operator_receipt.is_some()
        {
            let uncached;
            let op = if let Some(cache) = operator_cache {
                cache.get(p, &w.request)?
            } else {
                uncached = OperatorVerification::new(p, w.request.method, w.request.mode)?;
                &uncached
            };
            if w.operator_bounds != Some(op.bounds)
                || w.step != Some(op.step)
                || w.scaling_error_max != Some(op.scaling_error_max)
                || w.scaling_sha256.as_ref() != Some(&op.scaling_sha256)
                || w.operator_receipt.as_ref() != Some(&op.receipt)
            {
                return Err(invalid("operator/scaling provenance differs"));
            }
            if let Some(peak) = w.diagnostics.device_buffer_peak_bytes {
                let expected = optimizer_lp::exec::device_bytes(
                    p.row_count(),
                    p.column_count(),
                    p.nonzeros(),
                    w.request.mode,
                )
                .map_err(invalid)?;
                if peak != expected
                    || w.execution
                        .as_ref()
                        .is_none_or(|e| e.allocated_bytes != peak)
                {
                    return Err(invalid("allocation accounting differs"));
                }
            }
        }
        if w.proposed_steps > 0
            && (w.execution.is_none()
                || w.allocation_upload_ns.is_none()
                || w.diagnostics.device_buffer_peak_bytes.is_none()
                || w.diagnostics.iterations != w.physical_steps
                || w.diagnostics.kernel_launches != w.execution.as_ref().map(|e| e.kernel_launches))
        {
            return Err(invalid("missing or inconsistent execution observations"));
        }
        if w.status == "accepted" && (!self.assessment.gap_closed || w.executed_device.is_none()) {
            return Err(invalid("uncertified accepted research endpoint"));
        }
        Ok(())
    }
}
/// Cold-start controller, chunk-bounded proposals and fresh host assessments.
#[allow(clippy::too_many_arguments)]
fn run_research_loop(
    controller: &mut Fp64Controller<'_, '_>,
    executor: &mut Executor,
    engine: &Engine<'_>,
    model: &Model,
    program: &LinearProgram,
    cancel: &CancellationToken,
    w: &mut Witness,
) -> Result<(), String> {
    let mut saved = None;
    let mut valid = None;
    while controller.remaining() > 0 {
        if cancel.is_cancelled() {
            w.status = "interrupted".into();
            break;
        }
        if controller.expired() {
            w.status = "time_limit".into();
            break;
        }
        let primal_step = engine.step() / controller.state().weight;
        let dual_step = engine.step() * controller.state().weight;
        if !primal_step.is_finite()
            || !dual_step.is_finite()
            || primal_step == 0.0
            || dual_step == 0.0
        {
            w.status = "numerical_failure".into();
            w.failure = Some("update_step_range".into());
            break;
        }
        let chunk = controller.next_chunk(64);
        let phase = w.diagnostics.start();
        let outcome = executor.advance(
            controller,
            chunk,
            engine.step(),
            w.diagnostics.execution.as_mut().unwrap(),
        );
        w.diagnostics.finish("kernels_and_synchronization", phase);
        // An attempted chunk is charged; unknown device completion is explicit.
        w.proposed_steps += chunk;
        w.rounding_flags = executor.rounding_flags;
        match outcome {
            Err(e) => {
                w.status = "device_failure".into();
                w.failure = Some(e.to_string());
                w.physical_steps = None;
                break;
            }
            Ok(Some(reason)) => {
                controller.charge_extra(chunk)?;
                w.status = "numerical_failure".into();
                w.failure = Some(reason);
                break;
            }
            Ok(None) => controller.commit_steps(chunk)?,
        }
        if controller.check_pending() {
            let point = controller.iterate();
            let phase = w.diagnostics.start();
            let candidate = Candidate {
                schema_version: 1,
                model_id: model.document().model_id.clone(),
                values: program
                    .variable_ids()
                    .iter()
                    .zip(&point.primal)
                    .map(|(&variable_id, &value)| Assignment { variable_id, value })
                    .collect(),
            };
            let feasible = model
                .evaluate(&candidate, w.request.options.tolerances)
                .map_err(|e| e.to_string())?
                .feasible;
            let bound = certify(program, &point.dual).ok().map(|v| v.bound);
            let closed = feasible
                && bound
                    .and_then(|b| {
                        assess_gap(program, &point.primal, b, w.request.options.tolerances)
                    })
                    .is_some_and(|g| g.closed);
            if feasible {
                valid = Some(point.clone());
            }
            saved = Some(point);
            w.diagnostics.finish("host_certification", phase);
            if closed {
                w.status = "accepted".into();
                break;
            }
            w.status = "iteration_limit".into();
            let phase = w.diagnostics.start();
            controller.continue_after_check();
            w.diagnostics.finish("controller", phase);
        }
    }
    w.committed_steps = controller.state().iterations;
    if w.physical_steps.is_some() {
        w.physical_steps = Some(controller.physical_iterations());
    }
    let point = valid.or(saved).unwrap_or_else(|| controller.iterate());
    w.witness_iteration = point.iterations;
    w.primal = Some(point.primal);
    w.dual = Some(point.dual);
    w.diagnostics.iterations = w.physical_steps;
    w.diagnostics.restarts = Some(controller.state().restarts);
    w.diagnostics.kernel_launches = Some(w.diagnostics.execution.as_ref().unwrap().kernel_launches);
    Ok(())
}

/// The witness work counters derived after any solve, fresh or batched.
fn finish_witness(program: &LinearProgram, w: &mut Witness) {
    w.proposed_products = w.proposed_steps * 2 * program.nonzeros() as u64;
    w.vector_decodes = w.proposed_steps
        * if w.request.mode == Mode::Cached {
            (program.row_count() + program.column_count()) as u64
        } else {
            4 * program.nonzeros() as u64
        };
    w.execution = w.diagnostics.execution.clone();
}

/// Run only under the supervising shared host lease; all endpoints remain untrusted.
pub fn solve(
    bytes: &[u8],
    request: Request,
    cancel: &CancellationToken,
) -> Result<Evidence, ValidationError> {
    request.validate()?;
    if request.model_sha256 != crate::sha256::hex(bytes) {
        return Err(invalid("model hash differs"));
    }
    let model = Model::from_json(bytes)?;
    let p = LinearProgram::new(&model)?;
    let mut w = Witness {
        request,
        executed_device: None,
        variable_ids: p.variable_ids().to_vec(),
        row_ids: model.document().constraints.iter().map(|r| r.id).collect(),
        primal: None,
        dual: None,
        status: "iteration_limit".into(),
        failure: None,
        proposed_steps: 0,
        committed_steps: 0,
        physical_steps: Some(0),
        witness_iteration: 0,
        vector_decodes: 0,
        proposed_products: 0,
        rounding_flags: 0,
        allocation_upload_ns: None,
        diagnostics: LpDiagnostics::new(true, false),
        execution: None,
        operator_bounds: None,
        step: None,
        scaling_error_max: None,
        scaling_sha256: None,
        operator_receipt: None,
    };
    w.diagnostics = LpDiagnostics::new(true, w.request.profile);
    w.diagnostics.device_buffer_limit_bytes = Some(w.request.device_buffer_bytes);
    let start = Instant::now();
    let deadline = start + Duration::from_millis(w.request.options.time_limit_ms.unwrap());
    let outcome = (|| -> Result<(), String> {
        if cancel.is_cancelled() {
            w.status = "interrupted".into();
            return Ok(());
        }
        if std::env::var("AI_OPTIMIZER_GPU_LEASE").ok().as_deref() != Some("inherited") {
            return Err("shared host lease required".into());
        }
        let image = std::fs::read(code_object_path()).map_err(|e| e.to_string())?;
        if crate::sha256::hex(&image) != w.request.code_object_sha256 {
            return Err("code object mismatch".into());
        }
        let binary = std::fs::read(std::env::current_exe().map_err(|e| e.to_string())?)
            .map_err(|e| e.to_string())?;
        if crate::sha256::hex(&binary) != w.request.executable_sha256 {
            return Err("executable mismatch".into());
        }
        let phase = w.diagnostics.start();
        let (resident, _) =
            optimizer_lp::exec::memory_bytes(p.row_count(), p.column_count(), p.nonzeros())?;
        if resident > w.request.device_buffer_bytes {
            return Err("operator_memory".into());
        }
        let mut engine = Engine::new(&p, w.request.method);
        w.diagnostics.finish("preconditioning", phase);
        let phase = w.diagnostics.start();
        let op = prepare_operator(
            &engine,
            w.request.device_buffer_bytes.min(RESIDENT_CAP),
            PEAK_CAP,
        )?;
        engine.restrict_step(op.step())?;
        w.operator_bounds = Some(op.bounds());
        w.step = Some(op.step());
        w.scaling_error_max = Some(
            op.receipt()
                .original_error_infinity
                .max(op.receipt().original_error_one),
        );
        w.operator_receipt = Some(op.receipt().clone());
        w.scaling_sha256 = Some(crate::sha256::hex(
            &serde_json::to_vec(&(
                engine.preconditioner().row(),
                engine.preconditioner().column(),
            ))
            .unwrap(),
        ));
        w.diagnostics.finish("exec_preparation", phase);
        if Instant::now() >= deadline {
            w.status = "time_limit".into();
            return Ok(());
        }
        let phase = w.diagnostics.start();
        let context = Rc::new(
            optimizer_cuda_sys::Context::create(&w.request.device).map_err(|e| e.to_string())?,
        );
        w.executed_device = Some(context.device().uuid.clone());
        w.diagnostics.finish("context", phase);
        let mut e = LpExecutionDiagnostics::new(
            Fp64ExecutionSettings::from_json(include_bytes!(
                "../../../examples/lp-execution-v1.json"
            ))
            .map_err(|e| e.to_string())?,
        );
        e.settings.fusion = optimizer_core::Fp64Fusion::Separate;
        e.code_object_sha256 = Some(w.request.code_object_sha256.clone());
        w.diagnostics.execution = Some(e);
        let phase = w.diagnostics.start();
        let mut executor = Executor::new(
            context,
            &engine,
            &op,
            w.request.mode,
            &image,
            &mut w.diagnostics,
        )
        .map_err(|e| e.to_string())?;
        w.allocation_upload_ns = Some(executor.allocation_upload_ns);
        w.diagnostics.finish("invariant_allocation_upload", phase);
        let mut c = Fp64Controller::new(&engine);
        c.set_deadline(Some(deadline));
        run_research_loop(&mut c, &mut executor, &engine, &model, &p, cancel, &mut w)
    })();
    if let Err(reason) = outcome {
        w.status = "unsupported".into();
        w.failure = Some(reason);
    }
    finish_witness(&p, &mut w);
    Evidence::new(bytes, w)
}

#[cfg(test)]
mod tests {
    use super::*;
    fn request() -> Request {
        let config: serde_json::Value = serde_json::from_slice(include_bytes!(
            "../../../benchmarks/configs/lp-exec-v1.json"
        ))
        .unwrap();
        let value = serde_json::json!({"schema_version":1,"mode":"cached","model_sha256":crate::sha256::hex(include_bytes!("../../../examples/lp-model-v1.json")),"source_tree_sha256":"a".repeat(64),"executable_sha256":"b".repeat(64),"code_object_sha256":"c".repeat(64),"device":config["device"],"options":config["solve"],"method":config["lp_settings"],"profile":false,"device_buffer_bytes":1073741824});
        Request::from_json(&serde_json::to_vec(&value).unwrap()).unwrap()
    }
    fn cancelled() -> Evidence {
        let token = CancellationToken::new();
        token.cancel();
        solve(
            include_bytes!("../../../examples/lp-model-v1.json"),
            request(),
            &token,
        )
        .unwrap()
    }
    #[test]
    fn exec_cancelled_evidence_roundtrip_and_strict_requests() {
        let r = request();
        let bytes = serde_json::to_vec(&r).unwrap();
        assert_eq!(Request::from_json(&bytes).unwrap(), r);
        for value in [serde_json::json!([]), serde_json::json!({"cached":null})] {
            let mut altered = serde_json::to_value(&r).unwrap();
            altered["mode"] = value;
            assert!(Request::from_json(&serde_json::to_vec(&altered).unwrap()).is_err());
        }
        let e = cancelled();
        assert_eq!(e.witness.status, "interrupted");
        assert_eq!(e.witness.proposed_steps, 0);
        let parsed = Evidence::from_json(&serde_json::to_vec(&e).unwrap()).unwrap();
        parsed
            .verify(include_bytes!("../../../examples/lp-model-v1.json"), &r)
            .unwrap();
        let mut absent = serde_json::to_value(e).unwrap();
        absent["witness"]
            .as_object_mut()
            .unwrap()
            .remove("operator_receipt");
        assert!(Evidence::from_json(&serde_json::to_vec(&absent).unwrap()).is_err());
    }
    #[test]
    fn exec_verifier_rejects_rehashed_identity_work_and_profile_mutations() {
        for mutation in 0..7 {
            let mut e = cancelled();
            match mutation {
                0 => e.witness.rounding_flags = 8,
                1 => e.witness.vector_decodes = 1,
                2 => e.witness.proposed_products = 1,
                3 => e.witness.diagnostics.profile = true,
                4 => e.witness.executed_device = Some("GPU-other".into()),
                5 => e.witness.diagnostics.device_buffer_limit_bytes = Some(1),
                _ => e.witness.witness_iteration = 1,
            }
            e.payload_sha256 = crate::sha256::hex(&serde_json::to_vec(&e.witness).unwrap());
            assert!(
                e.verify(
                    include_bytes!("../../../examples/lp-model-v1.json"),
                    &request()
                )
                .is_err(),
                "mutation {mutation}"
            );
        }
    }
}
