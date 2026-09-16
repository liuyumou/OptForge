//! Strict study-only ADR-0021 requests and independently assessed witnesses.
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
    research::{Mode, Operator, power_exponent},
};
use optimizer_lp_cuda::research::{ResearchExecutor, code_object_path};
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
impl Evidence {
    pub fn from_json(bytes: &[u8]) -> Result<Self, ValidationError> {
        crate::lp::unique_json(bytes)?;
        serde_json::from_slice(bytes).map_err(invalid)
    }
    pub fn new(bytes: &[u8], witness: Witness) -> Result<Self, ValidationError> {
        let result = Self {
            schema_version: 1,
            assessment: assessment(bytes, &witness)?,
            payload_sha256: crate::sha256::hex(&serde_json::to_vec(&witness).map_err(invalid)?),
            witness,
        };
        result.verify(bytes, &result.witness.request)?;
        Ok(result)
    }
    pub fn verify(&self, bytes: &[u8], expected: &Request) -> Result<(), ValidationError> {
        let w = &self.witness;
        w.request.validate()?;
        let model = Model::from_json(bytes)?;
        let p = LinearProgram::new(&model)?;
        if self.schema_version != 1
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
            .checked_mul(6)
            .ok_or_else(|| invalid("work overflow"))?;
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
                    fusion: optimizer_core::Fp64Fusion::Separate,
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
            let mut engine = Engine::new(&p, w.request.method);
            if w.request.mode.power2() {
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
                engine = Engine::with_power2_scaling(&p, w.request.method, &row, &col)
                    .map_err(invalid)?;
            }
            let op = Operator::new(&engine, w.request.mode).map_err(invalid)?;
            let scales = crate::sha256::hex(
                &serde_json::to_vec(&(
                    engine.preconditioner().row(),
                    engine.preconditioner().column(),
                ))
                .map_err(invalid)?,
            );
            if w.operator_bounds != Some(op.bounds)
                || w.step != Some(op.step)
                || w.matrix_tail_max != Some(op.matrix_tail_max)
                || w.scaling_sha256.as_ref() != Some(&scales)
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
        e.settings.fusion = optimizer_core::Fp64Fusion::Separate;
        e.code_object_sha256 = Some(w.request.code_object_sha256.clone());
        w.diagnostics.execution = Some(e);
        let phase = w.diagnostics.start();
        let mut executor = ResearchExecutor::new(context, &engine, &op, &image, &mut w.diagnostics)
            .map_err(|e| e.to_string())?;
        w.packing_ns = Some(executor.packing_ns);
        w.diagnostics.finish("invariant_allocation_upload", phase);
        let mut c = Fp64Controller::new(&engine);
        c.set_deadline(Some(deadline));
        let mut saved = None;
        let mut valid = None;
        while c.remaining() > 0 {
            if cancel.is_cancelled() {
                w.status = "interrupted".into();
                break;
            }
            if c.expired() {
                w.status = "time_limit".into();
                break;
            }
            let primal_step = engine.step() / c.state().weight;
            let dual_step = engine.step() * c.state().weight;
            if !primal_step.is_finite()
                || !dual_step.is_finite()
                || primal_step == 0.0
                || dual_step == 0.0
            {
                w.status = "numerical_failure".into();
                w.failure = Some("update_step_range".into());
                break;
            }
            let chunk = c.next_chunk(64);
            let phase = w.diagnostics.start();
            let outcome = executor.advance(
                &mut c,
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
                    c.charge_extra(chunk)?;
                    w.status = "numerical_failure".into();
                    w.failure = Some(reason);
                    break;
                }
                Ok(None) => c.commit_steps(chunk)?,
            }
            if c.check_pending() {
                let point = c.iterate();
                let phase = w.diagnostics.start();
                let candidate = Candidate {
                    schema_version: 1,
                    model_id: model.document().model_id.clone(),
                    values: p
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
                let bound = certify(&p, &point.dual).ok().map(|v| v.bound);
                let closed = feasible
                    && bound
                        .and_then(|b| {
                            assess_gap(&p, &point.primal, b, w.request.options.tolerances)
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
                c.continue_after_check();
                w.diagnostics.finish("controller", phase);
            }
        }
        w.committed_steps = c.state().iterations;
        if w.physical_steps.is_some() {
            w.physical_steps = Some(c.physical_iterations());
        }
        let point = valid.or(saved).unwrap_or_else(|| c.iterate());
        w.witness_iteration = point.iterations;
        w.primal = Some(point.primal);
        w.dual = Some(point.dual);
        w.diagnostics.iterations = w.physical_steps;
        w.diagnostics.restarts = Some(c.state().restarts);
        w.diagnostics.kernel_launches =
            Some(w.diagnostics.execution.as_ref().unwrap().kernel_launches);
        Ok(())
    })();
    if let Err(reason) = outcome {
        w.status = "unsupported".into();
        w.failure = Some(reason);
    }
    let products = w.proposed_steps * 2 * p.nonzeros() as u64;
    let k = w.request.mode.components() as u64;
    w.vector_splits = if k > 0 { products } else { 0 };
    w.fp32_cross_products = if w.request.mode.cross() {
        products * k * k
    } else {
        0
    };
    w.execution = w.diagnostics.execution.clone();
    Evidence::new(bytes, w)
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
    #[test]
    fn strict_research_request_and_cancelled_witness_are_device_free() {
        let r = request();
        let bytes = serde_json::to_vec(&r).unwrap();
        assert_eq!(Request::from_json(&bytes).unwrap(), r);
        let mut extra = serde_json::to_value(&r).unwrap();
        extra["unknown"] = true.into();
        assert!(Request::from_json(&serde_json::to_vec(&extra).unwrap()).is_err());
        extra = serde_json::to_value(&r).unwrap();
        extra["schema_version"] = 2.into();
        assert!(Request::from_json(&serde_json::to_vec(&extra).unwrap()).is_err());
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
}
