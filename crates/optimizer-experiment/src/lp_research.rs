//! Strict study-only ADR-0021 requests and independently assessed witnesses.
#![allow(missing_docs)]
use crate::{lp::Assessment, serde_strict::deserialize_required_object};
use optimizer_core::{
    Assignment, CancellationToken, Candidate, ErrorKind, Fp64ExecutionSettings, LpDiagnostics,
    LpExecutionDiagnostics, LpSettings, Model, SessionSetup, SolveOptions, SolveRecord,
    Termination, ValidationError,
};
use optimizer_lp::{
    Engine, LinearProgram, certify,
    certify::assess_gap,
    control::Fp64Controller,
    research::{Mode, Operator, power_exponent},
};
use optimizer_lp_cuda::research::{ResearchExecutor, ResearchSession, code_object_path};
use serde::Serialize;
use std::{
    collections::BTreeMap,
    path::Path,
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
    pub vector_splits: u64,
    pub fp32_cross_products: u64,
    pub vector_tail_units: u32,
    pub packing_ns: Option<u64>,
    pub diagnostics: LpDiagnostics,
    pub execution: Option<LpExecutionDiagnostics>,
    pub operator_bounds: Option<[f64; 2]>,
    pub step: Option<f64>,
    pub matrix_tail_max: Option<f64>,
    pub scaling_sha256: Option<String>,
}
deserialize_required_object!(Witness {request:Request,executed_device:Option<String>,variable_ids:Vec<u32>,row_ids:Vec<u32>,primal:Option<Vec<f64>>,dual:Option<Vec<f64>>,status:String,failure:Option<String>,proposed_steps:u64,committed_steps:u64,physical_steps:Option<u64>,witness_iteration:u64,vector_splits:u64,fp32_cross_products:u64,vector_tail_units:u32,packing_ns:Option<u64>,diagnostics:LpDiagnostics,execution:Option<LpExecutionDiagnostics>,operator_bounds:Option<[f64;2]>,step:Option<f64>,matrix_tail_max:Option<f64>,scaling_sha256:Option<String>});
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
        if !(self.schema_version == 1 || self.schema_version == 2)
            || (self.schema_version == 1 && self.mode.v2())
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
            || self.options.time_limit_ms.is_none()
        {
            return Err(invalid("research request identity/limits"));
        }
        Ok(())
    }
}
fn assessment(bytes: &[u8], w: &Witness) -> Result<Assessment, ValidationError> {
    let model = Model::from_json(bytes)?;
    let program = LinearProgram::new(&model)?;
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
        .and_then(|v| certify(&program, v).ok())
        .map(|c| c.bound);
    let gap = report
        .as_ref()
        .filter(|v| v.feasible)
        .and(w.primal.as_ref())
        .and_then(|p| bound.and_then(|b| assess_gap(&program, p, b, w.request.options.tolerances)))
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
        backend: "isolated-research-witness".into(),
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
    };
    let mut d = LpDiagnostics::new(true, false);
    d.dual = w.dual.clone();
    crate::lp::assess(&model, &record, &d)
}
// Only matrix-derived verification metadata is reusable. This cache is private,
// rebuilt from the original host model (never session/device observations), and
// checked against each record's complete method, mode and canonical program.
// Candidate evaluation, bound certification and gap assessment remain per solve.
struct OperatorVerification {
    bounds: [f64; 2],
    step: f64,
    matrix_tail_max: f64,
    scaling_sha256: String,
}

impl OperatorVerification {
    fn new(
        program: &LinearProgram,
        method: LpSettings,
        mode: Mode,
    ) -> Result<Self, ValidationError> {
        let mut engine = Engine::new(program, method);
        if mode.power2() {
            let row = engine
                .preconditioner()
                .row()
                .iter()
                .map(|&x| power_exponent(x))
                .collect::<Result<Vec<_>, _>>()
                .map_err(invalid)?;
            let col = engine
                .preconditioner()
                .column()
                .iter()
                .map(|&x| power_exponent(x))
                .collect::<Result<Vec<_>, _>>()
                .map_err(invalid)?;
            engine = Engine::with_power2_scaling(program, method, &row, &col).map_err(invalid)?;
        }
        let op = Operator::new(&engine, mode).map_err(invalid)?;
        let scales = crate::sha256::hex(
            &serde_json::to_vec(&(
                engine.preconditioner().row(),
                engine.preconditioner().column(),
            ))
            .map_err(invalid)?,
        );
        Ok(Self {
            bounds: op.bounds,
            step: op.step,
            matrix_tail_max: op.matrix_tail_max,
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
        let result = Self {
            schema_version: witness.request.schema_version,
            assessment: assessment(bytes, &witness)?,
            payload_sha256: crate::sha256::hex(&serde_json::to_vec(&witness).map_err(invalid)?),
            witness,
        };
        result.verify_with_cache(bytes, &result.witness.request, operator_cache)?;
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
        let w = &self.witness;
        w.request.validate()?;
        let model = Model::from_json(bytes)?;
        let p = LinearProgram::new(&model)?;
        if self.schema_version != w.request.schema_version
            || &w.request != expected
            || w.request.model_sha256 != crate::sha256::hex(bytes)
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
            || self.assessment != assessment(bytes, w)?
        {
            return Err(invalid(
                "research evidence identity, work or assessment differs",
            ));
        }
        let products = w
            .proposed_steps
            .checked_mul(2)
            .and_then(|n| n.checked_mul(p.nonzeros() as u64))
            .ok_or_else(|| invalid("work overflow"))?;
        let k = w.request.mode.components() as u64;
        if w.vector_tail_units > 16 || (k != 2 && w.vector_tail_units != 0) {
            return Err(invalid("vector tail diagnostic differs"));
        }
        let cross_products = if w.request.mode.cross() {
            products
                .checked_mul(k)
                .and_then(|n| n.checked_mul(k))
                .ok_or_else(|| invalid("work overflow"))?
        } else {
            0
        };
        let launches = w
            .proposed_steps
            .checked_mul(w.request.mode.launches_per_step())
            .ok_or_else(|| invalid("work overflow"))?;
        let fusion = if w.request.mode.fused() {
            optimizer_core::Fp64Fusion::PrimalDual
        } else {
            optimizer_core::Fp64Fusion::Separate
        };
        if w.vector_splits != if k > 0 { products } else { 0 }
            || w.fp32_cross_products != cross_products
        {
            return Err(invalid("component work differs"));
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
            return Err(invalid("research execution differs"));
        }
        if w.operator_bounds.is_some() || w.executed_device.is_some() {
            let uncached;
            let op = if let Some(cache) = operator_cache {
                cache.get(&p, &w.request)?
            } else {
                uncached = OperatorVerification::new(&p, w.request.method, w.request.mode)?;
                &uncached
            };
            if w.operator_bounds != Some(op.bounds)
                || w.step != Some(op.step)
                || w.matrix_tail_max != Some(op.matrix_tail_max)
                || w.scaling_sha256.as_ref() != Some(&op.scaling_sha256)
            {
                return Err(invalid("operator/scaling provenance differs"));
            }
            if let Some(peak) = w.diagnostics.device_buffer_peak_bytes {
                let expected = optimizer_lp_cuda::research::peak_buffer_bytes(&p, w.request.mode)
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
                || w.packing_ns.is_none()
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
/// The shared iteration/assessment loop of [`solve`] and the batch path
/// (SPEC-0014 requirement 15): one controller from the cold iterate,
/// chunk-bounded executor advances, host certification at every check
/// boundary, and identical witness finalization. Both callers prepare the
/// controller (with its deadline), executor, engine, model and program; the
/// loop's behavior is byte-identical either way.
#[allow(clippy::too_many_arguments)]
fn run_research_loop(
    controller: &mut Fp64Controller<'_, '_>,
    executor: &mut ResearchExecutor,
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
        w.vector_tail_units = executor.vector_tail_units;
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
    let products = w.proposed_steps * 2 * program.nonzeros() as u64;
    let k = w.request.mode.components() as u64;
    w.vector_splits = if k > 0 { products } else { 0 };
    w.fp32_cross_products = if w.request.mode.cross() {
        products * k * k
    } else {
        0
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
        vector_splits: 0,
        fp32_cross_products: 0,
        vector_tail_units: 0,
        packing_ns: None,
        diagnostics: LpDiagnostics::new(true, false),
        execution: None,
        operator_bounds: None,
        step: None,
        matrix_tail_max: None,
        scaling_sha256: None,
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
        let mut engine = Engine::new(&p, w.request.method);
        if w.request.mode.power2() {
            let row = engine
                .preconditioner()
                .row()
                .iter()
                .map(|&v| power_exponent(v))
                .collect::<Result<Vec<_>, _>>()?;
            let col = engine
                .preconditioner()
                .column()
                .iter()
                .map(|&v| power_exponent(v))
                .collect::<Result<Vec<_>, _>>()?;
            engine = Engine::with_power2_scaling(&p, w.request.method, &row, &col)?;
        }
        w.diagnostics.finish("preconditioning", phase);
        let phase = w.diagnostics.start();
        let op = Operator::new(&engine, w.request.mode)?;
        engine.restrict_step(op.step)?;
        w.operator_bounds = Some(op.bounds);
        w.step = Some(op.step);
        w.matrix_tail_max = Some(op.matrix_tail_max);
        w.scaling_sha256 = Some(crate::sha256::hex(
            &serde_json::to_vec(&(
                engine.preconditioner().row(),
                engine.preconditioner().column(),
            ))
            .unwrap(),
        ));
        w.diagnostics.finish("research_preparation", phase);
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
        e.settings.fusion = if w.request.mode.fused() {
            optimizer_core::Fp64Fusion::PrimalDual
        } else {
            optimizer_core::Fp64Fusion::Separate
        };
        e.code_object_sha256 = Some(w.request.code_object_sha256.clone());
        w.diagnostics.execution = Some(e);
        let phase = w.diagnostics.start();
        let mut executor = ResearchExecutor::new(context, &engine, &op, &image, &mut w.diagnostics)
            .map_err(|e| e.to_string())?;
        w.packing_ns = Some(executor.packing_ns);
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

/// One solve's entry in a research batch record.
#[derive(Clone, Debug, PartialEq, Serialize)]
pub struct ResearchBatchSolve {
    pub index: u32,
    /// SHA-256 of the materialized model bytes actually solved.
    pub model_sha256: String,
    /// SHA-256 of the per-solve research-v2 evidence file bytes, or the
    /// crate::lp_batch no-record marker when the solve has no record.
    pub evidence_sha256: String,
    /// The per-solve witness status, or `not_attempted`/`failed` when no
    /// record exists (SPEC-0014 requirement 27).
    pub status: String,
    /// This solve's session phases (`variant_rebind`, `engine_rebind`,
    /// `bound_upload`); the research evidence vocabulary excludes them
    /// (requirement 24).
    pub session_phases_ns: BTreeMap<String, u64>,
    /// Why the solve has no record; present exactly for the no-record
    /// statuses.
    pub reason: Option<String>,
}
deserialize_required_object!(ResearchBatchSolve {
    index: u32,
    model_sha256: String,
    evidence_sha256: String,
    status: String,
    session_phases_ns: BTreeMap<String, u64>,
    reason: Option<String>
});

/// A research batch request, version 1: the research-v2 identity fields plus
/// an embedded lp-batch-request-v1. Modes are limited to intguard-fp64 and
/// fused-fp64 — the two modes bitwise-identical to the FP64 control — and the
/// tolerance tier is the per-solve options' tolerances, exactly as a
/// research-v2 Request records it.
#[derive(Clone, Debug, PartialEq, Serialize)]
pub struct ResearchBatchRequest {
    pub schema_version: u32,
    pub mode: Mode,
    /// SHA-256 of the exact base model input bytes.
    pub model_sha256: String,
    pub source_tree_sha256: String,
    pub executable_sha256: String,
    pub code_object_sha256: String,
    pub device: String,
    /// Per-solve options; time_limit_ms is required and bounds each solve.
    pub options: SolveOptions,
    pub method: LpSettings,
    pub profile: bool,
    pub device_buffer_bytes: u64,
    /// The batch description verbatim: kind, solves, variants, generator and
    /// the batch time limit.
    pub batch: crate::lp_batch::BatchRequest,
}
deserialize_required_object!(ResearchBatchRequest {
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
    device_buffer_bytes: u64,
    batch: crate::lp_batch::BatchRequest
});
impl ResearchBatchRequest {
    pub fn from_json(bytes: &[u8]) -> Result<Self, ValidationError> {
        crate::lp::unique_json(bytes)?;
        let r: Self = serde_json::from_slice(bytes).map_err(invalid)?;
        r.validate()?;
        Ok(r)
    }
    pub fn validate(&self) -> Result<(), ValidationError> {
        self.options.validate()?;
        self.method.validate()?;
        self.batch.validate()?;
        if self.schema_version != 1
            || !matches!(self.mode, Mode::IntguardFp64 | Mode::FusedFp64)
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
            || self.options.time_limit_ms.is_none()
        {
            return Err(invalid("research batch request identity/limits"));
        }
        Ok(())
    }
    /// SHA-256 of the canonical request serialization; the batch payload
    /// binds this value, so it is recomputed from the record's own fields.
    fn request_sha256(&self) -> Result<String, ValidationError> {
        Ok(crate::sha256::hex(
            &serde_json::to_vec(self).map_err(invalid)?,
        ))
    }
    /// The per-solve research-v2 request for one materialized model hash:
    /// the batch identity with the per-solve model and the v2 schema the
    /// admitted modes require.
    fn solve_request(&self, model_sha256: String) -> Request {
        Request {
            schema_version: 2,
            mode: self.mode,
            model_sha256,
            source_tree_sha256: self.source_tree_sha256.clone(),
            executable_sha256: self.executable_sha256.clone(),
            code_object_sha256: self.code_object_sha256.clone(),
            device: self.device.clone(),
            options: self.options.clone(),
            method: self.method,
            profile: self.profile,
            device_buffer_bytes: self.device_buffer_bytes,
        }
    }
}

/// A research batch record, version 1: the request, the one-time session
/// setup phases (device context, module load, preconditioning, research
/// preparation, invariant allocation/upload), one entry per solve and the
/// binding payload hash (requirement 26, crate::lp_batch's layout).
#[derive(Clone, Debug, PartialEq, Serialize)]
pub struct ResearchBatchEvidence {
    pub schema_version: u32,
    pub request: ResearchBatchRequest,
    pub setup: SessionSetup,
    pub solves: Vec<ResearchBatchSolve>,
    pub payload_sha256: String,
}
deserialize_required_object!(ResearchBatchEvidence {
    schema_version: u32,
    request: ResearchBatchRequest,
    setup: SessionSetup,
    solves: Vec<ResearchBatchSolve>,
    payload_sha256: String
});

fn not_attempted(index: u32, model_sha256: &str, reason: &str) -> ResearchBatchSolve {
    ResearchBatchSolve {
        index,
        model_sha256: model_sha256.to_owned(),
        evidence_sha256: crate::lp_batch::NO_RECORD.to_owned(),
        status: "not_attempted".into(),
        session_phases_ns: BTreeMap::new(),
        reason: Some(reason.to_owned()),
    }
}

impl ResearchBatchEvidence {
    pub fn from_json(bytes: &[u8]) -> Result<Self, ValidationError> {
        crate::lp::unique_json(bytes)?;
        serde_json::from_slice(bytes).map_err(invalid)
    }
    /// Build the record and immediately re-verify it against the evidence
    /// directory, exactly as [`Evidence::new`] self-verifies.
    pub fn new(
        base_bytes: &[u8],
        request: ResearchBatchRequest,
        setup: SessionSetup,
        solves: Vec<ResearchBatchSolve>,
        dir: &Path,
    ) -> Result<Self, ValidationError> {
        Self::new_with_cache(
            base_bytes,
            request,
            setup,
            solves,
            dir,
            &mut OperatorCache::default(),
        )
    }
    fn new_with_cache(
        base_bytes: &[u8],
        request: ResearchBatchRequest,
        setup: SessionSetup,
        solves: Vec<ResearchBatchSolve>,
        dir: &Path,
        operator_cache: &mut OperatorCache,
    ) -> Result<Self, ValidationError> {
        let mut result = Self {
            schema_version: 1,
            request,
            setup,
            solves,
            payload_sha256: String::new(),
        };
        result.payload_sha256 = result.compute_payload()?;
        result.verify_with_cache(base_bytes, dir, operator_cache)?;
        Ok(result)
    }
    fn compute_payload(&self) -> Result<String, ValidationError> {
        Ok(crate::lp_batch::payload_hash(
            &self.request.request_sha256()?,
            &self.request.model_sha256,
            self.solves
                .iter()
                .map(|solve| (solve.evidence_sha256.as_str(), solve.status.as_str())),
        ))
    }
    /// Re-verify the batch from the retained evidence alone: re-materialize
    /// every variant, re-verify every per-solve research-v2 evidence against
    /// its materialized bytes with the unchanged verifier, and recompute
    /// every hash (requirement 17).
    pub fn verify(&self, base_bytes: &[u8], dir: &Path) -> Result<(), ValidationError> {
        self.verify_with_cache(base_bytes, dir, &mut OperatorCache::default())
    }
    fn verify_with_cache(
        &self,
        base_bytes: &[u8],
        dir: &Path,
        operator_cache: &mut OperatorCache,
    ) -> Result<(), ValidationError> {
        self.request.validate()?;
        if self.schema_version != 1 || self.request.model_sha256 != crate::sha256::hex(base_bytes) {
            return Err(invalid("research batch version/model differs"));
        }
        let base = Model::from_json(base_bytes)?;
        crate::lp_batch::check_phases(&self.setup.phases_ns, &crate::lp_batch::SETUP_PHASES)?;
        if self.solves.len() != self.request.batch.solves as usize
            || self
                .solves
                .iter()
                .enumerate()
                .any(|(position, solve)| solve.index != position as u32)
        {
            return Err(invalid("research batch summary count/order"));
        }
        for solve in &self.solves {
            let no_record = ["not_attempted", "failed"].contains(&solve.status.as_str());
            if no_record != (solve.evidence_sha256 == crate::lp_batch::NO_RECORD)
                || no_record != solve.reason.is_some()
                || (!no_record && !hash_ok(&solve.evidence_sha256))
            {
                return Err(invalid("research batch record/reason mismatch"));
            }
            crate::lp_batch::check_phases(
                &solve.session_phases_ns,
                &crate::lp_batch::SOLVE_PHASES,
            )?;
            let (_, bytes, materialized_sha256) =
                crate::lp_batch::materialize(&base, &self.request.batch, solve.index)?;
            if solve.model_sha256 != materialized_sha256 {
                return Err(invalid("research batch solve model differs"));
            }
            let path = dir.join(crate::lp_batch::solve_file_name(solve.index));
            match std::fs::read(&path) {
                Ok(file_bytes) => {
                    if solve.evidence_sha256 == crate::lp_batch::NO_RECORD
                        || solve.evidence_sha256 != crate::sha256::hex(&file_bytes)
                    {
                        return Err(invalid("research solve evidence hash differs"));
                    }
                    let evidence = Evidence::from_json(&file_bytes)?;
                    evidence.verify_with_cache(
                        &bytes,
                        &self.request.solve_request(solve.model_sha256.clone()),
                        Some(operator_cache),
                    )?;
                    if solve.status != evidence.witness.status {
                        return Err(invalid("research solve status differs"));
                    }
                }
                Err(error) if error.kind() == std::io::ErrorKind::NotFound => {
                    if !no_record {
                        return Err(invalid("missing research solve record without a reason"));
                    }
                }
                Err(error) => return Err(invalid(format!("evidence read: {error}"))),
            }
        }
        if self.payload_sha256 != self.compute_payload()? {
            return Err(invalid("research batch payload differs"));
        }
        Ok(())
    }
}

/// Open the batch's one research session: cancellation, the shared lease and
/// the code/executable identities are checked once (mirroring solve()'s
/// gates), the context is created once, and ResearchSession::open performs
/// admission and the invariant upload once. The measured phases land in
/// `setup` under the requirement-24 vocabulary. Any failure is returned as a
/// reason string so every solve is recorded not_attempted, mirroring solve()'s
/// evidence-not-error rule.
fn open_research_session(
    base: &Model,
    request: &ResearchBatchRequest,
    cancel: &CancellationToken,
    setup: &mut SessionSetup,
) -> Result<(ResearchSession, LpExecutionDiagnostics, u64), String> {
    if cancel.is_cancelled() {
        return Err("cancelled".into());
    }
    if std::env::var("AI_OPTIMIZER_GPU_LEASE").ok().as_deref() != Some("inherited") {
        return Err("shared host lease required".into());
    }
    // The code object is read and hashed once for the batch (requirement 6);
    // the module itself loads inside ResearchSession::open.
    let phase = setup.start();
    let image = std::fs::read(code_object_path()).map_err(|e| e.to_string())?;
    if crate::sha256::hex(&image) != request.code_object_sha256 {
        return Err("code object mismatch".into());
    }
    setup.finish("module_load", phase);
    let binary = std::fs::read(std::env::current_exe().map_err(|e| e.to_string())?)
        .map_err(|e| e.to_string())?;
    if crate::sha256::hex(&binary) != request.executable_sha256 {
        return Err("executable mismatch".into());
    }
    let phase = setup.start();
    let context =
        Rc::new(optimizer_cuda_sys::Context::create(&request.device).map_err(|e| e.to_string())?);
    setup.finish("device_context", phase);
    let mut open_diagnostics = LpDiagnostics::new(true, request.profile);
    open_diagnostics.device_buffer_limit_bytes = Some(request.device_buffer_bytes);
    let session = ResearchSession::open(
        context,
        base.clone(),
        request.method,
        request.mode,
        image,
        &mut open_diagnostics,
    )
    .map_err(|e| e.to_string())?;
    // The session's open counters are the residency every solve runs on: the
    // unchanged per-solve verifier's allocation accounting pins them.
    let resident = open_diagnostics
        .execution
        .clone()
        .ok_or("missing session open counters")?;
    let peak = open_diagnostics
        .device_buffer_peak_bytes
        .ok_or("missing session open peak")?;
    for (name, ns) in &session.setup().phases_ns {
        setup.phases_ns.insert(name.clone(), *ns);
    }
    Ok((session, resident, peak))
}

/// Run one SPEC-0014 batch over one research session. The lease and the code
/// and executable identities are checked once at open; each solve
/// re-materializes its variant (requirement 16), rebinds only variable
/// bounds, runs the shared `run_research_loop` from a fresh controller with
/// fresh per-solve counters (requirements 8-10) and writes an individually
/// verifiable research-v2 record whose request hash names the materialized
/// bytes (requirement 23). Cancellation, the batch time limit and a poisoned
/// session are observed between solves; completed records are retained and
/// later solves are recorded not_attempted with the reason
/// (requirements 13-14, 27).
pub fn solve_batch(
    bytes: &[u8],
    request: &ResearchBatchRequest,
    dir: &Path,
    cancel: &CancellationToken,
) -> Result<ResearchBatchEvidence, ValidationError> {
    request.validate()?;
    if request.model_sha256 != crate::sha256::hex(bytes) {
        return Err(invalid("model hash differs"));
    }
    let base = Model::from_json(bytes)?;
    let program = LinearProgram::new(&base)?;
    // Every variant is materialized before any device open, so a malformed
    // change list refuses the batch before allocation or upload (requirement
    // 11); the hashes are the per-solve identities.
    let mut materialized = Vec::with_capacity(request.batch.solves as usize);
    for index in 0..request.batch.solves {
        materialized.push(crate::lp_batch::materialize(&base, &request.batch, index)?.2);
    }
    let batch_deadline = Instant::now() + Duration::from_millis(request.batch.batch_time_limit_ms);
    let mut setup = SessionSetup::default();
    let mut solves: Vec<ResearchBatchSolve> = Vec::with_capacity(request.batch.solves as usize);
    let (mut session, resident, peak) =
        match open_research_session(&base, request, cancel, &mut setup) {
            Ok(opened) => opened,
            Err(reason) => {
                for (index, model_sha256) in materialized.iter().enumerate() {
                    solves.push(not_attempted(index as u32, model_sha256, &reason));
                }
                return ResearchBatchEvidence::new(bytes, request.clone(), setup, solves, dir);
            }
        };
    let mut operator_cache = OperatorCache::default();
    let (operator_bounds, step, matrix_tail_max) = {
        let operator = session.operator();
        (operator.bounds, operator.step, operator.matrix_tail_max)
    };
    for index in 0..request.batch.solves {
        let blocked = if cancel.is_cancelled() {
            Some("cancelled".to_owned())
        } else if Instant::now() >= batch_deadline {
            Some("batch_time_limit".to_owned())
        } else {
            session.poisoned().map(str::to_owned)
        };
        if let Some(reason) = blocked {
            for (remaining, model_sha256) in materialized.iter().enumerate().skip(index as usize) {
                solves.push(not_attempted(remaining as u32, model_sha256, &reason));
            }
            break;
        }
        let (variant, variant_bytes, model_sha256) =
            crate::lp_batch::materialize(&base, &request.batch, index)?;
        let mut w = Witness {
            request: request.solve_request(model_sha256.clone()),
            executed_device: Some(session.device().uuid.clone()),
            variable_ids: session.program().variable_ids().to_vec(),
            row_ids: variant
                .document()
                .constraints
                .iter()
                .map(|r| r.id)
                .collect(),
            primal: None,
            dual: None,
            status: "iteration_limit".into(),
            failure: None,
            proposed_steps: 0,
            committed_steps: 0,
            physical_steps: Some(0),
            witness_iteration: 0,
            vector_splits: 0,
            fp32_cross_products: 0,
            vector_tail_units: 0,
            packing_ns: Some(session.packing_ns()),
            diagnostics: LpDiagnostics::new(true, request.profile),
            execution: None,
            operator_bounds: None,
            step: None,
            matrix_tail_max: None,
            scaling_sha256: None,
        };
        w.diagnostics.device_buffer_limit_bytes = Some(request.device_buffer_bytes);
        let started = Instant::now();
        let deadline = started + Duration::from_millis(request.options.time_limit_ms.unwrap());
        // Fresh per-solve counters (requirement 9): the upload, readback,
        // synchronization and launch counts are this solve's own. In a
        // session the allocation fields name the residency opened once and
        // reused — the unchanged per-solve verifier pins them — and the
        // batch record's setup phases carry that cost once (requirement 24).
        let mut counters = session.fresh_counters();
        counters.allocations = resident.allocations;
        counters.allocated_bytes = resident.allocated_bytes;
        let admitted = match request.batch.kind {
            crate::lp_batch::BatchKind::Repeat => None,
            crate::lp_batch::BatchKind::Variant => Some(&variant),
        };
        let solve = match session.prepare_solve(admitted, &mut counters) {
            Ok(solve) => solve,
            Err(error) => {
                // Per-solve preparation failed before the solve started. A
                // device fault here poisons the session (the next loop-top
                // check records every remaining solve not_attempted); a
                // refusal does not.
                solves.push(ResearchBatchSolve {
                    index,
                    model_sha256,
                    evidence_sha256: crate::lp_batch::NO_RECORD.to_owned(),
                    status: "failed".into(),
                    session_phases_ns: session.solve_phases().phases_ns.clone(),
                    reason: Some(error.to_string()),
                });
                continue;
            }
        };
        w.diagnostics.execution = Some(counters);
        w.diagnostics.device_buffer_peak_bytes = Some(peak);
        w.operator_bounds = Some(operator_bounds);
        w.step = Some(step);
        w.matrix_tail_max = Some(matrix_tail_max);
        w.scaling_sha256 = Some(crate::sha256::hex(
            &serde_json::to_vec(&(
                solve.engine.preconditioner().row(),
                solve.engine.preconditioner().column(),
            ))
            .map_err(invalid)?,
        ));
        let outcome = {
            let mut c = Fp64Controller::new(&solve.engine);
            c.set_deadline(Some(deadline));
            run_research_loop(
                &mut c,
                solve.executor,
                &solve.engine,
                &variant,
                solve.program,
                cancel,
                &mut w,
            )
        };
        let session_phases_ns = session.solve_phases().phases_ns.clone();
        if let Err(reason) = outcome {
            w.status = "unsupported".into();
            w.failure = Some(reason);
        }
        if w.status == "device_failure" {
            // The loop observed the fault; the session poisons so later
            // solves are recorded not_attempted (requirement 13).
            session.poison(w.failure.clone().unwrap_or_else(|| "device fault".into()));
        }
        finish_witness(&program, &mut w);
        match Evidence::new_with_cache(&variant_bytes, w, Some(&mut operator_cache)) {
            Ok(evidence) => {
                let status = evidence.witness.status.clone();
                let file = serde_json::to_vec_pretty(&evidence).map_err(invalid)?;
                let evidence_sha256 = crate::sha256::hex(&file);
                crate::lp_batch::write_evidence_file(
                    &dir.join(crate::lp_batch::solve_file_name(index)),
                    &file,
                )?;
                solves.push(ResearchBatchSolve {
                    index,
                    model_sha256,
                    evidence_sha256,
                    status,
                    session_phases_ns,
                    reason: None,
                });
            }
            Err(reason) => {
                // A solve whose evidence cannot be constructed is a failed
                // solve, recorded explicitly; the session is unaffected.
                solves.push(ResearchBatchSolve {
                    index,
                    model_sha256,
                    evidence_sha256: crate::lp_batch::NO_RECORD.to_owned(),
                    status: "failed".into(),
                    session_phases_ns,
                    reason: Some(reason.to_string()),
                });
            }
        }
    }
    ResearchBatchEvidence::new_with_cache(
        bytes,
        request.clone(),
        setup,
        solves,
        dir,
        &mut operator_cache,
    )
}

#[cfg(test)]
mod tests {
    use super::*;
    const MODEL: &[u8] = include_bytes!("../../../examples/lp-model-v1.json");
    fn request() -> Request {
        let mut options: SolveOptions =
            serde_json::from_slice(include_bytes!("../../../examples/solve-config-v1.json"))
                .unwrap();
        options.iteration_limit = Some(8);
        options.time_limit_ms = Some(1000);
        Request {
            schema_version: 1,
            mode: Mode::Components3Fp32,
            model_sha256: crate::sha256::hex(MODEL),
            source_tree_sha256: "1".repeat(64),
            executable_sha256: "2".repeat(64),
            code_object_sha256: "3".repeat(64),
            device: "GPU-test".into(),
            options,
            method: LpSettings::published(8, 4),
            profile: false,
            device_buffer_bytes: 1024,
        }
    }
    // A zero-work host witness exercises operator provenance and certification
    // without opening a device or claiming any device computation took place.
    fn host_witness(bytes: &[u8], mode: Mode, method: LpSettings) -> Witness {
        let mut r = request();
        r.schema_version = 2;
        r.mode = mode;
        r.method = method;
        r.options.iteration_limit = Some(method.iteration_limit);
        r.model_sha256 = crate::sha256::hex(bytes);
        let token = CancellationToken::new();
        token.cancel();
        let mut w = solve(bytes, r, &token).unwrap().witness;
        let model = Model::from_json(bytes).unwrap();
        let p = LinearProgram::new(&model).unwrap();
        let metadata = OperatorVerification::new(&p, method, mode).unwrap();
        w.operator_bounds = Some(metadata.bounds);
        w.step = Some(metadata.step);
        w.matrix_tail_max = Some(metadata.matrix_tail_max);
        w.scaling_sha256 = Some(metadata.scaling_sha256);
        w.primal = Some(vec![0.5, 1.0]);
        w.dual = Some(vec![-1.0]);
        w
    }

    #[test]
    fn batch_verification_reuses_only_matrix_metadata_and_rechecks_bounds() {
        let method = LpSettings::published(8, 4);
        let mut cache = OperatorCache::default();
        let w = host_witness(MODEL, Mode::FusedFp64, method);
        let original = Evidence::new_with_cache(MODEL, w.clone(), Some(&mut cache)).unwrap();
        assert_eq!(original, Evidence::new(MODEL, w).unwrap());
        let base = Model::from_json(MODEL).unwrap();
        let mut variables = base.document().variables.clone();
        variables[1].upper = optimizer_core::Bound::Finite { value: 0.75 };
        let bytes = base
            .rebound(variables)
            .unwrap()
            .to_json()
            .unwrap()
            .into_bytes();
        let w = host_witness(&bytes, Mode::FusedFp64, method);
        let variant = Evidence::new_with_cache(&bytes, w.clone(), Some(&mut cache)).unwrap();
        assert_eq!(
            serde_json::to_vec(&variant).unwrap(),
            serde_json::to_vec(&Evidence::new(&bytes, w).unwrap()).unwrap()
        );
        assert_eq!(cache.preparations, 1);
        assert_ne!(variant.assessment, original.assessment);
        // Even with correct hashes and a warm metadata cache, an assessment
        // copied from the old bounds must fail original-model certification.
        let mut stale = variant.clone();
        stale.assessment = original.assessment;
        assert!(
            stale
                .verify_with_cache(&bytes, &stale.witness.request, Some(&mut cache))
                .is_err()
        );
        for field in 0..4 {
            let mut altered = variant.clone();
            match field {
                0 => altered.witness.step = Some(0.0),
                1 => altered.witness.operator_bounds = Some([0.0, 0.0]),
                2 => altered.witness.matrix_tail_max = Some(1.0),
                _ => altered.witness.scaling_sha256 = Some("0".repeat(64)),
            }
            altered.payload_sha256 =
                crate::sha256::hex(&serde_json::to_vec(&altered.witness).unwrap());
            assert!(
                altered
                    .verify_with_cache(&bytes, &altered.witness.request, Some(&mut cache))
                    .is_err()
            );
        }
        assert_eq!(cache.preparations, 1);
    }

    #[test]
    fn batch_verification_reprepares_on_matrix_method_or_mode_change() {
        let mut cache = OperatorCache::default();
        let method = LpSettings::published(8, 4);
        let mut changed = Model::from_json(MODEL).unwrap().document().clone();
        changed.constraints[0].terms[0].coefficient = 2.0;
        let changed = Model::new(changed).unwrap().to_json().unwrap().into_bytes();
        let mut other_method = method;
        other_method.power_iterations += 1;
        for (index, (bytes, mode, method)) in [
            (MODEL, Mode::FusedFp64, method),
            (changed.as_slice(), Mode::FusedFp64, method),
            (changed.as_slice(), Mode::FusedFp64, other_method),
            (changed.as_slice(), Mode::IntguardFp64, other_method),
        ]
        .into_iter()
        .enumerate()
        {
            let witness = host_witness(bytes, mode, method);
            let cached =
                Evidence::new_with_cache(bytes, witness.clone(), Some(&mut cache)).unwrap();
            assert_eq!(cached, Evidence::new(bytes, witness).unwrap());
            assert_eq!(cache.preparations, index + 1);
        }
    }

    #[test]
    fn batch_directory_and_producer_share_one_independent_host_preparation() {
        let request = batch_request(Mode::IntguardFp64);
        let base = Model::from_json(MODEL).unwrap();
        let dir = batch_sandbox();
        let mut cache = OperatorCache::default();
        let mut solves = Vec::new();
        for index in 0..request.batch.solves {
            let (_, bytes, model_sha256) =
                crate::lp_batch::materialize(&base, &request.batch, index).unwrap();
            let mut witness = host_witness(&bytes, request.mode, request.method);
            witness.request = request.solve_request(model_sha256.clone());
            let expected = Evidence::new(&bytes, witness.clone()).unwrap();
            let evidence = Evidence::new_with_cache(&bytes, witness, Some(&mut cache)).unwrap();
            assert_eq!(evidence, expected);
            let file = serde_json::to_vec_pretty(&evidence).unwrap();
            crate::lp_batch::write_evidence_file(
                &dir.join(crate::lp_batch::solve_file_name(index)),
                &file,
            )
            .unwrap();
            solves.push(ResearchBatchSolve {
                index,
                model_sha256,
                evidence_sha256: crate::sha256::hex(&file),
                status: evidence.witness.status,
                session_phases_ns: BTreeMap::new(),
                reason: None,
            });
        }
        let batch = ResearchBatchEvidence::new_with_cache(
            MODEL,
            request,
            SessionSetup::default(),
            solves,
            &dir,
            &mut cache,
        )
        .unwrap();
        assert_eq!(
            cache.preparations, 1,
            "producer and final directory recheck share metadata"
        );
        let mut independent = OperatorCache::default();
        batch
            .verify_with_cache(MODEL, &dir, &mut independent)
            .unwrap();
        assert_eq!(
            independent.preparations, 1,
            "a new verifier independently prepares once"
        );
        std::fs::remove_dir_all(dir).unwrap();
    }

    #[test]
    fn review_session_outcome_cancelled_endpoint_verifies() {
        if std::env::var("AI_OPTIMIZER_GPU").ok().as_deref() != Some("1") {
            eprintln!("SKIP review_session_outcome: device tests are opt-in");
            return;
        }
        assert_eq!(
            std::env::var("AI_OPTIMIZER_GPU_LEASE").unwrap(),
            "inherited"
        );
        let device = std::env::var("CUDA_VISIBLE_DEVICES").unwrap();
        let context = Rc::new(optimizer_cuda_sys::Context::create(&device).unwrap());
        let model = Model::from_json(MODEL).unwrap();
        let execution = Fp64ExecutionSettings::from_json(include_bytes!(
            "../../../examples/lp-execution-v1.json"
        ))
        .unwrap();
        let method = LpSettings::published(8, 4);
        let mut session = optimizer_lp_cuda::TunedSession::open(
            context,
            method,
            execution,
            model,
            &mut LpDiagnostics::new(true, false),
        )
        .unwrap();
        let token = CancellationToken::new();
        token.cancel();
        let mut diagnostics = LpDiagnostics::new(true, false);
        let record = session
            .solve(None, &request().options, &token, &mut diagnostics)
            .unwrap();
        assert_eq!(record.termination, Termination::Interrupted);
        assert_eq!(record.backend, "cuda-lp-tuned");
        assert!(session.poisoned().is_none());
        let endpoint =
            crate::lp::LpEndpoint::new(MODEL, "cuda-lp-tuned".into(), record, diagnostics, None)
                .unwrap();
        endpoint.verify(MODEL).unwrap();
    }

    #[test]
    fn strict_research_request_and_cancelled_witness_are_device_free() {
        let r = request();
        let bytes = serde_json::to_vec(&r).unwrap();
        assert_eq!(Request::from_json(&bytes).unwrap(), r);
        let mut extra = serde_json::to_value(&r).unwrap();
        extra["unknown"] = true.into();
        assert!(Request::from_json(&serde_json::to_vec(&extra).unwrap()).is_err());
        extra = serde_json::to_value(&r).unwrap();
        extra["schema_version"] = 3.into();
        assert!(Request::from_json(&serde_json::to_vec(&extra).unwrap()).is_err());
        // ADR-0022 modes require research-v2; version 2 still admits the nine v1 modes.
        extra = serde_json::to_value(&r).unwrap();
        extra["mode"] = "doublefloat-fp32".into();
        assert!(Request::from_json(&serde_json::to_vec(&extra).unwrap()).is_err());
        extra["schema_version"] = 2.into();
        let v2 = Request::from_json(&serde_json::to_vec(&extra).unwrap()).unwrap();
        assert_eq!(v2.mode, Mode::DoublefloatFp32);
        extra["mode"] = "components3-fp32".into();
        assert!(Request::from_json(&serde_json::to_vec(&extra).unwrap()).is_ok());
        extra = serde_json::to_value(&r).unwrap();
        extra["mode"] = serde_json::json!({"components3-fp32":null});
        assert!(Request::from_json(&serde_json::to_vec(&extra).unwrap()).is_err());
        let duplicate =
            String::from_utf8(bytes)
                .unwrap()
                .replacen('{', "{\"schema_version\":1,", 1);
        assert!(Request::from_json(duplicate.as_bytes()).is_err());
        let token = CancellationToken::new();
        token.cancel();
        let e = solve(MODEL, r.clone(), &token).unwrap();
        let mut malformed = serde_json::to_value(&e).unwrap();
        malformed["unknown"] = true.into();
        assert!(Evidence::from_json(&serde_json::to_vec(&malformed).unwrap()).is_err());
        malformed = serde_json::to_value(&e).unwrap();
        malformed["witness"]
            .as_object_mut()
            .unwrap()
            .remove("packing_ns");
        assert!(Evidence::from_json(&serde_json::to_vec(&malformed).unwrap()).is_err());
        assert_eq!(e.assessment.classification, "interrupted");
        assert_eq!(e.witness.proposed_steps, 0);
        assert!(e.witness.executed_device.is_none());
        let mut altered = e.clone();
        altered.witness.request.code_object_sha256 = "4".repeat(64);
        altered.payload_sha256 = crate::sha256::hex(&serde_json::to_vec(&altered.witness).unwrap());
        assert!(altered.verify(MODEL, &r).is_err());
        let mut altered = e;
        altered.witness.physical_steps = Some(1);
        assert!(Evidence::new(MODEL, altered.witness).is_err());
    }
    #[test]
    fn corrupted_witness_and_mislabeled_execution_are_rejected() {
        let r = request();
        let token = CancellationToken::new();
        token.cancel();
        let e = solve(MODEL, r, &token).unwrap();
        let mut w = e.witness.clone();
        w.executed_device = Some("GPU-wrong".into());
        assert!(Evidence::new(MODEL, w).is_err());
        let mut w = e.witness.clone();
        w.primal = Some(vec![0.0]);
        w.dual = Some(vec![0.0]);
        assert!(Evidence::new(MODEL, w).is_err());
        let mut w = e.witness;
        w.status = "accepted".into();
        assert!(Evidence::new(MODEL, w).is_err());
    }
    #[test]
    fn fused_modes_bind_two_launches_and_the_fused_execution_setting() {
        let mut r = request();
        r.schema_version = 2;
        r.mode = Mode::FusedFp64;
        let token = CancellationToken::new();
        token.cancel();
        let e = solve(MODEL, r.clone(), &token).unwrap();
        assert_eq!(e.schema_version, 2);
        assert_eq!(e.witness.request.mode.launches_per_step(), 2);
        let separate = |fusion| {
            let mut w = e.witness.clone();
            let mut execution = LpExecutionDiagnostics::new(Fp64ExecutionSettings {
                schema_version: 1,
                allocation: optimizer_core::WorkingAllocation::Resident,
                uploads: optimizer_core::StateUploads::Necessary,
                reduction: optimizer_core::Fp64Reduction::Warp32V1,
                fusion,
            });
            execution.code_object_sha256 = Some(w.request.code_object_sha256.clone());
            w.execution = Some(execution);
            Evidence::new(MODEL, w)
        };
        assert!(separate(optimizer_core::Fp64Fusion::Separate).is_err());
        assert!(separate(optimizer_core::Fp64Fusion::PrimalDual).is_ok());
        let mut altered = e.clone();
        altered.schema_version = 1;
        assert!(altered.verify(MODEL, &r).is_err());
        assert_eq!(
            Mode::DoublefloatFp32.fused_kernels(),
            Some(("research_fused_primal_df", "research_fused_dual_df"))
        );
        assert_eq!(Mode::IntguardFp64.launches_per_step(), 6);
    }
    #[test]
    fn altered_execution_policy_and_overflowing_work_are_rejected() {
        let r = request();
        let token = CancellationToken::new();
        token.cancel();
        let e = solve(MODEL, r, &token).unwrap();
        let mut w = e.witness.clone();
        let mut execution = LpExecutionDiagnostics::new(Fp64ExecutionSettings {
            schema_version: 1,
            allocation: optimizer_core::WorkingAllocation::Resident,
            uploads: optimizer_core::StateUploads::Necessary,
            reduction: optimizer_core::Fp64Reduction::Warp32V1,
            fusion: optimizer_core::Fp64Fusion::PrimalDual,
        });
        execution.code_object_sha256 = Some(w.request.code_object_sha256.clone());
        w.execution = Some(execution);
        assert!(Evidence::new(MODEL, w).is_err());
        let mut w = e.witness;
        w.proposed_steps = 1 << 60;
        w.request.method.iteration_limit = w.proposed_steps;
        w.request.options.iteration_limit = Some(w.proposed_steps);
        w.physical_steps = Some(w.proposed_steps);
        w.executed_device = Some(w.request.device.clone());
        w.vector_splits = w.proposed_steps * 4;
        assert!(Evidence::new(MODEL, w).is_err());
    }

    fn batch_request(mode: Mode) -> ResearchBatchRequest {
        use crate::lp_batch::{BatchKind, BatchRequest, BoundChange, Generator, Variant};
        let mut options: SolveOptions =
            serde_json::from_slice(include_bytes!("../../../examples/solve-config-v1.json"))
                .unwrap();
        options.iteration_limit = Some(8);
        options.time_limit_ms = Some(1000);
        ResearchBatchRequest {
            schema_version: 1,
            mode,
            model_sha256: crate::sha256::hex(MODEL),
            source_tree_sha256: "1".repeat(64),
            executable_sha256: "2".repeat(64),
            code_object_sha256: "3".repeat(64),
            device: "GPU-test".into(),
            options,
            method: LpSettings::published(8, 4),
            profile: false,
            device_buffer_bytes: 1024,
            batch: BatchRequest {
                schema_version: 1,
                kind: BatchKind::Variant,
                solves: 2,
                variants: vec![
                    Variant {
                        index: 0,
                        changes: vec![BoundChange {
                            variable_id: 0,
                            lower: 0.25,
                            upper: 1.0,
                        }],
                    },
                    Variant {
                        index: 1,
                        changes: vec![BoundChange {
                            variable_id: 0,
                            lower: 0.0,
                            upper: 0.75,
                        }],
                    },
                ],
                generator: Some(Generator {
                    seed: 3,
                    changes: 1,
                }),
                batch_time_limit_ms: 60_000,
            },
        }
    }

    fn batch_sandbox() -> std::path::PathBuf {
        use std::sync::atomic::{AtomicUsize, Ordering};
        static COUNTER: AtomicUsize = AtomicUsize::new(0);
        let path = std::env::temp_dir().join(format!(
            "optimizer-lp-research-batch-{}-{}",
            std::process::id(),
            COUNTER.fetch_add(1, Ordering::SeqCst)
        ));
        std::fs::create_dir_all(&path).expect("sandbox");
        path
    }

    #[test]
    fn research_batch_request_is_strict_and_mode_gated() {
        let request = batch_request(Mode::IntguardFp64);
        let bytes = serde_json::to_vec(&request).unwrap();
        assert_eq!(ResearchBatchRequest::from_json(&bytes).unwrap(), request);
        let mut extra = serde_json::to_value(&request).unwrap();
        extra["unknown"] = true.into();
        assert!(ResearchBatchRequest::from_json(&serde_json::to_vec(&extra).unwrap()).is_err());
        extra = serde_json::to_value(&request).unwrap();
        extra["schema_version"] = 2.into();
        assert!(ResearchBatchRequest::from_json(&serde_json::to_vec(&extra).unwrap()).is_err());
        // An array where an object belongs is refused at every level.
        assert!(ResearchBatchRequest::from_json(b"[]").is_err());
        let mut nested = serde_json::to_value(&request).unwrap();
        nested["batch"] = serde_json::json!([]);
        assert!(ResearchBatchRequest::from_json(&serde_json::to_vec(&nested).unwrap()).is_err());
        nested = serde_json::to_value(&request).unwrap();
        nested["batch"]["variants"][0] = serde_json::json!([0, []]);
        assert!(ResearchBatchRequest::from_json(&serde_json::to_vec(&nested).unwrap()).is_err());
        // Every field is required-present, the embedded batch's included.
        for field in [
            "schema_version",
            "mode",
            "model_sha256",
            "source_tree_sha256",
            "executable_sha256",
            "code_object_sha256",
            "device",
            "options",
            "method",
            "profile",
            "device_buffer_bytes",
            "batch",
        ] {
            let mut missing = serde_json::to_value(&request).unwrap();
            missing.as_object_mut().unwrap().remove(field);
            assert!(
                ResearchBatchRequest::from_json(&serde_json::to_vec(&missing).unwrap()).is_err(),
                "missing {field}"
            );
        }
        let duplicate =
            String::from_utf8(bytes)
                .unwrap()
                .replacen('{', "{\"schema_version\":1,", 1);
        assert!(ResearchBatchRequest::from_json(duplicate.as_bytes()).is_err());
        // Only the two modes bitwise-identical to the FP64 control batch.
        for refused in [
            "default-fp64",
            "power2-fp64",
            "components3-fp32",
            "doublefloat-fp32",
        ] {
            let mut wrong = serde_json::to_value(&request).unwrap();
            wrong["mode"] = refused.into();
            assert!(
                ResearchBatchRequest::from_json(&serde_json::to_vec(&wrong).unwrap()).is_err(),
                "mode {refused} must be refused"
            );
        }
        for (admitted, expected) in [
            ("intguard-fp64", Mode::IntguardFp64),
            ("fused-fp64", Mode::FusedFp64),
        ] {
            let mut ok = serde_json::to_value(&request).unwrap();
            ok["mode"] = admitted.into();
            let parsed =
                ResearchBatchRequest::from_json(&serde_json::to_vec(&ok).unwrap()).unwrap();
            assert_eq!(parsed.mode, expected);
        }
        // The per-solve request is research-v2 with the materialized hash.
        let per_solve = request.solve_request("0".repeat(64));
        assert_eq!(per_solve.schema_version, 2);
        assert_eq!(per_solve.model_sha256, "0".repeat(64));
        per_solve.validate().unwrap();
    }

    #[test]
    fn cancelled_research_batch_records_every_solve_not_attempted() {
        let request = batch_request(Mode::FusedFp64);
        let token = CancellationToken::new();
        token.cancel();
        let dir = batch_sandbox();
        let evidence = solve_batch(MODEL, &request, &dir, &token).unwrap();
        assert_eq!(evidence.schema_version, 1);
        assert_eq!(evidence.request, request);
        assert_eq!(evidence.solves.len(), 2);
        let base = Model::from_json(MODEL).unwrap();
        for (index, solve) in evidence.solves.iter().enumerate() {
            assert_eq!(solve.index, index as u32);
            assert_eq!(solve.status, "not_attempted");
            assert_eq!(solve.reason.as_deref(), Some("cancelled"));
            assert_eq!(solve.evidence_sha256, crate::lp_batch::NO_RECORD);
            assert!(solve.session_phases_ns.is_empty());
            let (_, _, materialized) =
                crate::lp_batch::materialize(&base, &request.batch, index as u32).unwrap();
            assert_eq!(solve.model_sha256, materialized);
        }
        // No session opened, so the directory holds no per-solve record.
        assert!(std::fs::read_dir(&dir).unwrap().next().is_none());
        // The constructor self-verified; an independent verifier agrees.
        evidence.verify(MODEL, &dir).unwrap();
        let bytes = serde_json::to_vec(&evidence).unwrap();
        let parsed = ResearchBatchEvidence::from_json(&bytes).unwrap();
        assert_eq!(parsed, evidence);
        parsed.verify(MODEL, &dir).unwrap();
        // Strict parsing: unknown field, array shape, missing nullable.
        let mut malformed = serde_json::to_value(&evidence).unwrap();
        malformed["unknown"] = true.into();
        assert!(
            ResearchBatchEvidence::from_json(&serde_json::to_vec(&malformed).unwrap()).is_err()
        );
        assert!(ResearchBatchEvidence::from_json(b"[]").is_err());
        malformed = serde_json::to_value(&evidence).unwrap();
        malformed["solves"][0]
            .as_object_mut()
            .unwrap()
            .remove("reason");
        assert!(
            ResearchBatchEvidence::from_json(&serde_json::to_vec(&malformed).unwrap()).is_err()
        );
        // Tampering: payload, a dropped reason, a relabeled status.
        let mut wrong = evidence.clone();
        wrong.payload_sha256 = "0".repeat(64);
        assert!(wrong.verify(MODEL, &dir).is_err());
        let mut wrong = evidence.clone();
        wrong.solves[0].reason = None;
        assert!(wrong.verify(MODEL, &dir).is_err());
        let mut wrong = evidence.clone();
        wrong.solves[0].status = "accepted".into();
        assert!(wrong.verify(MODEL, &dir).is_err());
        let mut wrong = evidence.clone();
        wrong.solves[0].model_sha256 = "0".repeat(64);
        assert!(wrong.verify(MODEL, &dir).is_err());
        // A batch over different base bytes is a different batch.
        assert!(evidence.verify(b"{}", &dir).is_err());
        std::fs::remove_dir_all(&dir).ok();
    }

    #[test]
    fn research_batch_verifies_a_recorded_directory() {
        // One real device-free research-v2 record per solve, produced by the
        // unchanged fresh path (a cancelled solve) against the materialized
        // variant bytes, so the batch verification exercises its file loop.
        let request = batch_request(Mode::IntguardFp64);
        let base = Model::from_json(MODEL).unwrap();
        let dir = batch_sandbox();
        let token = CancellationToken::new();
        token.cancel();
        let mut solves = Vec::new();
        for index in 0..request.batch.solves {
            let (_, bytes, model_sha256) =
                crate::lp_batch::materialize(&base, &request.batch, index).unwrap();
            let evidence =
                solve(&bytes, request.solve_request(model_sha256.clone()), &token).unwrap();
            assert_eq!(evidence.witness.status, "interrupted");
            let file = serde_json::to_vec_pretty(&evidence).unwrap();
            let evidence_sha256 = crate::sha256::hex(&file);
            crate::lp_batch::write_evidence_file(
                &dir.join(crate::lp_batch::solve_file_name(index)),
                &file,
            )
            .unwrap();
            solves.push(ResearchBatchSolve {
                index,
                model_sha256,
                evidence_sha256,
                status: evidence.witness.status.clone(),
                session_phases_ns: BTreeMap::from([("variant_rebind".to_owned(), 1)]),
                reason: None,
            });
        }
        let mut setup = SessionSetup::default();
        setup.phases_ns.insert("research_preparation".into(), 3);
        let batch =
            ResearchBatchEvidence::new(MODEL, request.clone(), setup, solves, &dir).unwrap();
        batch.verify(MODEL, &dir).unwrap();
        let parsed =
            ResearchBatchEvidence::from_json(&serde_json::to_vec(&batch).unwrap()).unwrap();
        assert_eq!(parsed, batch);
        parsed.verify(MODEL, &dir).unwrap();
        // The per-solve record file is named solve-NNN.json and hash-bound.
        assert!(dir.join("solve-000.json").is_file());
        let mut file = std::fs::read(dir.join("solve-000.json")).unwrap();
        file[0] = b' ';
        std::fs::write(dir.join("solve-000.json"), file).unwrap();
        assert!(batch.verify(MODEL, &dir).is_err());
        std::fs::remove_dir_all(&dir).ok();
    }

    #[test]
    fn research_batch_refuses_a_malformed_variant_before_any_open() {
        // An unknown variable in one change list refuses the whole batch at
        // materialization, before the lease or any device work (the cancelled
        // token is never even observed: refusal comes first).
        let mut request = batch_request(Mode::IntguardFp64);
        request.batch.variants[1].changes[0].variable_id = 99;
        let token = CancellationToken::new();
        token.cancel();
        let dir = batch_sandbox();
        let error = solve_batch(MODEL, &request, &dir, &token).unwrap_err();
        assert!(error.message.contains("unknown variable 99"), "{error}");
        assert!(std::fs::read_dir(&dir).unwrap().next().is_none());
        // A model hash mismatch is refused before anything else.
        let mut wrong = batch_request(Mode::IntguardFp64);
        wrong.model_sha256 = "0".repeat(64);
        assert!(solve_batch(MODEL, &wrong, &dir, &token).is_err());
        std::fs::remove_dir_all(&dir).ok();
    }
}
