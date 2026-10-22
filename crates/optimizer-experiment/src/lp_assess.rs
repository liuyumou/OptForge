//! Strict study-only ADR-0039 requests, fresh host authority and trace attachments.
#![allow(missing_docs)]
use crate::{lp::Assessment, serde_strict::deserialize_required_object};
use optimizer_core::{
    Assignment, CancellationToken, Candidate, ErrorKind, LpSettings, Model, SolveOptions,
    ValidationError,
};
use optimizer_lp::{
    Engine, LinearProgram,
    assess::{Arithmetic, Frame, Outcome, Point, Policy, Scheduler},
    certify,
    certify::assess_gap,
};
use serde::Serialize;
use std::{
    collections::BTreeMap,
    path::{Component, Path},
    time::{Duration, Instant},
};
fn invalid(e: impl ToString) -> ValidationError {
    ValidationError::new(ErrorKind::Document, e.to_string())
}
fn hash_ok(s: &str) -> bool {
    s.len() == 64
        && s.bytes()
            .all(|c| c.is_ascii_digit() || (b'a'..=b'f').contains(&c))
}
#[derive(Clone, Debug, PartialEq, Serialize)]
pub struct Request {
    pub schema_version: u32,
    pub identity: String,
    pub arithmetic: Arithmetic,
    pub policy: Policy,
    pub model_sha256: String,
    pub source_tree_sha256: String,
    pub executable_sha256: String,
    pub code_object_sha256: String,
    pub device: String,
    pub options: SolveOptions,
    pub method: LpSettings,
    pub diagnostic: bool,
    pub device_buffer_bytes: u64,
}
deserialize_required_object!(Request {
    schema_version: u32,
    identity: String,
    arithmetic: Arithmetic,
    policy: Policy,
    model_sha256: String,
    source_tree_sha256: String,
    executable_sha256: String,
    code_object_sha256: String,
    device: String,
    options: SolveOptions,
    method: LpSettings,
    diagnostic: bool,
    device_buffer_bytes: u64
});
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
        let expected =
            LpSettings::from_json(include_bytes!("../../../examples/lp-settings-v1.json"))?;
        let mut actual = self.method;
        actual.iteration_limit = expected.iteration_limit;
        if self.schema_version != 1
            || self.identity != "lp-assess-v1"
            || !self.device.starts_with("GPU-")
            || [
                &self.model_sha256,
                &self.source_tree_sha256,
                &self.executable_sha256,
                &self.code_object_sha256,
            ]
            .into_iter()
            .any(|h| !hash_ok(h))
            || self.options.iteration_limit != Some(self.method.iteration_limit)
            || self.method.iteration_limit > 50000
            || self.method.check_interval != 200
            || actual != expected
            || self.options.threads != 1
            || self.options.seed != 17
            || self
                .options
                .time_limit_ms
                .is_none_or(|v| v == 0 || v > 30000)
            || self.device_buffer_bytes == 0
            || self.device_buffer_bytes > 1 << 30
            || self.diagnostic && self.method.iteration_limit > 4000
        {
            return Err(invalid("assessment request identity/settings/limits"));
        }
        Ok(())
    }
}
#[derive(Clone, Debug, PartialEq, Serialize)]
pub struct Attachment {
    pub name: String,
    pub sha256: String,
}
deserialize_required_object!(Attachment {
    name: String,
    sha256: String
});
#[derive(Clone, Debug, PartialEq, Serialize)]
pub struct Witness {
    pub request: Request,
    pub executor: String,
    pub executed_device: Option<String>,
    pub outcome: Outcome,
    pub initial: Frame,
    pub traces: Vec<Attachment>,
    pub phases_ns: BTreeMap<String, u64>,
    pub execution: Option<optimizer_core::LpExecutionDiagnostics>,
}
deserialize_required_object!(Witness {request:Request,executor:String,executed_device:Option<String>,outcome:Outcome,
 initial:Frame,traces:Vec<Attachment>,phases_ns:BTreeMap<String,u64>,execution:Option<optimizer_core::LpExecutionDiagnostics>});
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
pub struct Bundle {
    pub evidence: Evidence,
    pub frames: Vec<Frame>,
}
pub fn assessment(
    model: &Model,
    p: &LinearProgram,
    point: Option<&Point>,
    options: &SolveOptions,
) -> Result<Assessment, ValidationError> {
    let Some(point) = point else {
        return Ok(Assessment {
            classification: "missing_endpoint".into(),
            feasible: None,
            objective: None,
            bound: None,
            gap_upper: None,
            gap_closed: false,
            allowance: None,
            repaired: None,
            reason: Some("safe endpoint unavailable".into()),
        });
    };
    if point.primal.len() != p.column_count()
        || point.dual.len() != p.row_count()
        || !point
            .primal
            .iter()
            .chain(&point.dual)
            .all(|v| v.is_finite())
    {
        return Err(invalid("assessment witness shape/nonfinite"));
    }
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
    let report = model.evaluate(&candidate, options.tolerances)?;
    let c = certify(p, &point.dual);
    let reason = c.as_ref().err().map(ToString::to_string);
    let c = c.ok();
    let bound = c.as_ref().map(|c| c.bound);
    let gap = report
        .feasible
        .then(|| bound.and_then(|b| assess_gap(p, &point.primal, b, options.tolerances)))
        .flatten();
    let closed = gap.is_some_and(|g| g.closed);
    Ok(Assessment {
        classification: if !report.feasible {
            "numerical_rejection"
        } else if bound.is_none() {
            "missing_certificate"
        } else if closed {
            "certified_success"
        } else {
            "feasible_unclosed"
        }
        .into(),
        feasible: Some(report.feasible),
        objective: Some(report.objective),
        bound,
        gap_upper: gap.map(|g| g.upper),
        gap_closed: closed,
        allowance: c.as_ref().map(|c| c.allowance),
        repaired: c.as_ref().map(|c| c.repaired),
        reason,
    })
}
fn inputs(bytes: &[u8], request: &Request) -> Result<(Model, LinearProgram), ValidationError> {
    request.validate()?;
    if crate::sha256::hex(bytes) != request.model_sha256 {
        return Err(invalid("assessment model identity"));
    }
    let model = Model::from_json(bytes)?;
    let p = LinearProgram::new(&model)?;
    if p.row_count() > 65536 || p.column_count() > 65536 || p.nonzeros() > 1 << 23 {
        return Err(invalid("assessment shape admission"));
    }
    // Controller, scheduler, saved safe window and diagnostic frame peak, plus
    // original/scaled dual sparse views. Checked before trace/scheduler allocation.
    let vectors = (p.row_count() as u64 + p.column_count() as u64)
        .checked_mul(8)
        .and_then(|v| {
            v.checked_mul(
                24 + if request.diagnostic {
                    4 * (request.method.iteration_limit / 200)
                } else {
                    0
                },
            )
        });
    let bytes = vectors
        .and_then(|v| v.checked_add(p.nonzeros() as u64 * 96))
        .ok_or_else(|| invalid("assessment memory overflow"))?;
    if bytes > 6 << 30 {
        return Err(invalid("assessment host memory admission"));
    }
    Ok((model, p))
}
fn shape(raw: &serde_json::Value, canonical: &serde_json::Value) -> bool {
    match (raw, canonical) {
        (serde_json::Value::Object(a), serde_json::Value::Object(b)) => {
            a.len() == b.len() && b.iter().all(|(k, v)| a.get(k).is_some_and(|x| shape(x, v)))
        }
        (serde_json::Value::Array(a), serde_json::Value::Array(b)) => {
            a.len() == b.len() && a.iter().zip(b).all(|(x, y)| shape(x, y))
        }
        (serde_json::Value::Object(_) | serde_json::Value::Array(_), _)
        | (_, serde_json::Value::Object(_) | serde_json::Value::Array(_)) => false,
        _ => true,
    }
}
impl Evidence {
    pub fn from_json(bytes: &[u8]) -> Result<Self, ValidationError> {
        crate::lp::unique_json(bytes)?;
        let raw: serde_json::Value = serde_json::from_slice(bytes).map_err(invalid)?;
        let e: Self = serde_json::from_value(raw.clone()).map_err(invalid)?;
        if !shape(&raw, &serde_json::to_value(&e).map_err(invalid)?) {
            return Err(invalid(
                "assessment evidence requires complete object fields",
            ));
        }
        Ok(e)
    }
    pub fn verify(
        &self,
        bytes: &[u8],
        expected: &Request,
        directory: &Path,
    ) -> Result<(), ValidationError> {
        let (model, p) = inputs(bytes, expected)?;
        let w = &self.witness;
        let o = &w.outcome;
        if self.schema_version != 1
            || &w.request != expected
            || !o.frames.is_empty()
            || self.payload_sha256 != crate::sha256::hex(&serde_json::to_vec(w).map_err(invalid)?)
            || !["cpu", "gpu"].contains(&w.executor.as_str())
            || w.executor == "cpu"
                && (!expected.diagnostic || w.executed_device.is_some() || w.execution.is_some())
            || w.executor == "gpu"
                && w.executed_device
                    .as_ref()
                    .is_some_and(|d| d != &expected.device)
            || o.logical_steps > expected.method.iteration_limit
            || o.physical_steps
                .is_some_and(|n| n < o.logical_steps || n > expected.method.iteration_limit)
            || o.proposed_steps > expected.method.iteration_limit
            || o.proposed_steps < o.physical_steps.unwrap_or(0)
            || o.events.len() as u64 > o.logical_steps / 200
            || (o.events.len() as u64
                + u64::from(
                    [
                        "interrupted",
                        "time_limit",
                        "numerical_failure",
                        "device_failure",
                    ]
                    .contains(&o.status.as_str())
                        && o.logical_steps.is_multiple_of(200),
                ))
                < o.logical_steps / 200
            || !expected.diagnostic && !w.traces.is_empty()
            || expected.diagnostic && w.traces.len() != o.events.len()
            || ![
                "accepted",
                "iteration_limit",
                "time_limit",
                "interrupted",
                "numerical_failure",
                "device_failure",
            ]
            .contains(&o.status.as_str())
            || o.status == "accepted"
                && (expected.diagnostic || !self.assessment.gap_closed || o.point.is_none())
            || o.status == "device_failure" && (o.point.is_some() || o.physical_steps.is_some())
            || o.status != "device_failure"
                && (o
                    .point
                    .as_ref()
                    .is_none_or(|p| p.iteration != o.logical_steps)
                    || o.physical_steps.is_none())
            || self.assessment != assessment(&model, &p, o.point.as_ref(), &expected.options)?
        {
            return Err(invalid("assessment evidence identity/work/authority"));
        }
        let initial_engine = Engine::new(&p, expected.method);
        let initial = &w.initial;
        if initial.point.iteration != 0
            || initial.scaled_primal != initial_engine.start_primal()
            || initial.scaled_dual != initial_engine.start_dual()
            || initial.point.primal != initial_engine.unscale_primal(&initial.scaled_primal)
            || initial.point.dual != initial_engine.unscale_dual(&initial.scaled_dual)
            || initial.weight != 1.0
            || initial.restarts != 0
        {
            return Err(invalid("assessment initial state"));
        }
        if o.kkt_evaluations != 1 + o.controller_checks + o.restarts
            || o.restarts > o.controller_checks
            || o.status == "iteration_limit"
                && o.physical_steps != Some(expected.method.iteration_limit)
            || w.executor == "gpu"
                && (w.executed_device.as_deref() != Some(expected.device.as_str())
                    || w.execution.as_ref().is_none_or(|d| {
                        d.settings != optimizer_lp_cuda::assess::execution_settings()
                            || d.code_object_sha256.as_deref()
                                != Some(expected.code_object_sha256.as_str())
                    }))
        {
            return Err(invalid("assessment executed identity/controller counters"));
        }
        let mut last = 0;
        let mut reference = None;
        for (i, event) in o.events.iter().enumerate() {
            let d = &event.decision;
            let iteration = (i as u64 + 1) * 200;
            let reason = if expected.policy == Policy::Fixed200 {
                "fixed"
            } else if last == 0 {
                "first"
            } else if d.movement.is_none() {
                "invalid_indicator"
            } else if iteration - last >= 800 {
                "maximum_spacing"
            } else if reference.is_some_and(|r| r > 0.0 && d.movement.is_some_and(|q| q <= r / 2.0))
            {
                "movement"
            } else {
                "defer"
            };
            if d.iteration != iteration
                || d.reason != reason
                || d.assess != (reason != "defer")
                || d.movement
                    .is_some_and(|q| !q.is_finite() || !(0.0..=2.0).contains(&q))
                || expected.policy == Policy::Fixed200 && d.movement.is_some()
                || !event.weight.is_finite()
                || event.weight <= 0.0
                || event.closed && !d.assess
                || event.closed
                    && !expected.diagnostic
                    && (i + 1 != o.events.len()
                        || o.point.as_ref().is_none_or(|p| p.iteration != iteration))
            {
                return Err(invalid("assessment decision trace"));
            }
            if d.assess {
                last = iteration;
                reference = d.movement;
            }
        }
        let expected_checks = o.events.len() as u64
            - u64::from(o.events.last().is_some_and(|e| e.closed) && !expected.diagnostic);
        if o.assessments
            != o.events.iter().filter(|e| e.decision.assess).count() as u64
                + u64::from(o.point.is_some())
            || o.controller_checks != expected_checks
        {
            return Err(invalid("assessment check counters"));
        }
        if expected.diagnostic {
            let mut e = Engine::new(&p, expected.method);
            if expected.arithmetic == Arithmetic::AccumulationFp32
                && let Ok(op) = optimizer_lp::precision::PrecisionOperator::new(
                    &e,
                    &expected.arithmetic.precision(),
                )
            {
                e.restrict_step(op.step).map_err(invalid)?;
            }
            let mut scheduler = Scheduler::new(expected.policy, &e.start_primal(), &e.start_dual());
            for (i, frame) in self.read_frames(directory)?.iter().enumerate() {
                let event = &o.events[i];
                if frame.point.iteration != event.decision.iteration
                    || frame.scaled_primal.len() != p.column_count()
                    || frame.scaled_dual.len() != p.row_count()
                    || !frame
                        .scaled_primal
                        .iter()
                        .chain(&frame.scaled_dual)
                        .all(|v| v.is_finite())
                    || frame.point.primal != e.unscale_primal(&frame.scaled_primal)
                    || frame.point.dual != e.unscale_dual(&frame.scaled_dual)
                    || frame.weight != event.weight
                    || frame.restarts != event.restarts
                    || scheduler
                        .sample(
                            frame.point.iteration,
                            &frame.scaled_primal,
                            &frame.scaled_dual,
                        )
                        .map_err(invalid)?
                        != event.decision
                    || event.closed
                        != (event.decision.assess
                            && assessment(&model, &p, Some(&frame.point), &expected.options)?
                                .gap_closed)
                {
                    return Err(invalid("assessment diagnostic frame/authority"));
                }
            }
        }
        Ok(())
    }
    pub fn read_frames(&self, directory: &Path) -> Result<Vec<Frame>, ValidationError> {
        self.witness
            .traces
            .iter()
            .map(|r| {
                let path = Path::new(&r.name);
                if path.components().count() != 1
                    || !matches!(path.components().next(), Some(Component::Normal(_)))
                    || !hash_ok(&r.sha256)
                {
                    return Err(invalid("assessment trace path/hash"));
                }
                let path = directory.join(path);
                if std::fs::metadata(&path).map_err(invalid)?.len() > 32 << 20 {
                    return Err(invalid("assessment frame byte limit"));
                }
                let raw = std::fs::read(path).map_err(invalid)?;
                if crate::sha256::hex(&raw) != r.sha256 {
                    return Err(invalid("assessment frame hash"));
                }
                crate::lp::unique_json(&raw)?;
                let f: Frame = serde_json::from_slice(&raw).map_err(invalid)?;
                if !shape(
                    &serde_json::from_slice(&raw).map_err(invalid)?,
                    &serde_json::to_value(&f).map_err(invalid)?,
                ) {
                    return Err(invalid("assessment frame requires object fields"));
                }
                Ok(f)
            })
            .collect()
    }
}
/// Compare deterministic replay payloads including the bits of every finite
/// binary64 value. Phase durations are observations, not replay state. Callers
/// independently verify the original evidence and construct/verify the replay.
pub fn replay_matches(
    original: &Evidence,
    replayed: &Evidence,
    directory: &Path,
) -> Result<bool, ValidationError> {
    if original.witness.request != replayed.witness.request
        || original.witness.executor != replayed.witness.executor
        || original.witness.executed_device != replayed.witness.executed_device
    {
        return Ok(false);
    }
    let a = original.read_frames(directory)?;
    let b = replayed.read_frames(directory)?;
    Ok(
        serde_json::to_vec(&(&original.witness.outcome, &original.assessment, a))
            .map_err(invalid)?
            == serde_json::to_vec(&(&replayed.witness.outcome, &replayed.assessment, b))
                .map_err(invalid)?,
    )
}
impl Bundle {
    pub fn write(mut self, path: &Path) -> Result<Evidence, ValidationError> {
        let stem = path
            .file_name()
            .and_then(|s| s.to_str())
            .ok_or_else(|| invalid("assessment output filename"))?;
        for (i, frame) in self.frames.iter().enumerate() {
            let raw = serde_json::to_vec(frame).map_err(invalid)?;
            if raw.len() > 32 << 20 {
                return Err(invalid("assessment frame output limit"));
            }
            let name = format!("{stem}.frame-{i}.json");
            write_new(&path.with_file_name(&name), &raw)?;
            self.evidence.witness.traces.push(Attachment {
                name,
                sha256: crate::sha256::hex(&raw),
            });
        }
        self.evidence.payload_sha256 =
            crate::sha256::hex(&serde_json::to_vec(&self.evidence.witness).map_err(invalid)?);
        write_new(path, &serde_json::to_vec(&self.evidence).map_err(invalid)?)?;
        Ok(self.evidence)
    }
}
fn write_new(path: &Path, raw: &[u8]) -> Result<(), ValidationError> {
    use std::io::Write;
    let mut f = std::fs::OpenOptions::new()
        .create_new(true)
        .write(true)
        .open(path)
        .map_err(invalid)?;
    f.write_all(raw).map_err(invalid)?;
    f.sync_all().map_err(invalid)
}
pub fn execute(
    bytes: &[u8],
    request: Request,
    cpu: bool,
    cancel: &CancellationToken,
) -> Result<Bundle, ValidationError> {
    let start = Instant::now();
    let deadline =
        (!cpu).then(|| start + Duration::from_millis(request.options.time_limit_ms.unwrap_or(0)));
    let (model, p) = inputs(bytes, &request)?;
    if cpu && !request.diagnostic {
        return Err(invalid("CPU traces require diagnostic mode"));
    }
    if crate::sha256::hex(
        &std::fs::read(std::env::current_exe().map_err(invalid)?).map_err(invalid)?,
    ) != request.executable_sha256
    {
        return Err(invalid("assessment executable identity"));
    }
    let mut engine = Engine::new(&p, request.method);
    let precision_operator = if request.arithmetic == Arithmetic::AccumulationFp32 {
        Some(
            optimizer_lp::precision::PrecisionOperator::new(
                &engine,
                &request.arithmetic.precision(),
            )
            .map_err(invalid)?,
        )
    } else {
        None
    };
    if let Some(op) = &precision_operator {
        engine.restrict_step(op.step).map_err(invalid)?;
    }
    let initial = Frame {
        point: Point {
            iteration: 0,
            primal: engine.unscale_primal(&engine.start_primal()),
            dual: engine.unscale_dual(&engine.start_dual()),
        },
        scaled_primal: engine.start_primal(),
        scaled_dual: engine.start_dual(),
        weight: 1.0,
        restarts: 0,
    };
    let mut phases = BTreeMap::new();
    phases.insert("host_preparation".into(), start.elapsed().as_nanos() as u64);
    let mut check_ns = 0;
    let mut last_assessment = None;
    let check = |point: &Point| {
        let t = Instant::now();
        let a = assessment(&model, &p, Some(point), &request.options);
        let closed = a.as_ref().is_ok_and(|a| a.gap_closed);
        last_assessment = a.ok();
        check_ns += t.elapsed().as_nanos() as u64;
        closed
    };
    let (mut outcome, executed_device, execution) = if cpu {
        (
            optimizer_lp::assess::run_cpu(
                &engine,
                request.arithmetic,
                request.policy,
                true,
                cancel,
                None,
                check,
            ),
            None,
            None,
        )
    } else {
        if std::env::var("AI_OPTIMIZER_GPU_LEASE").ok().as_deref() != Some("inherited")
            || std::env::var("CUDA_VISIBLE_DEVICES").ok().as_deref()
                != Some(request.device.as_str())
        {
            return Err(invalid("selected shared host lease required"));
        }
        let image_path = if request.arithmetic == Arithmetic::TunedFp64 {
            optimizer_lp_cuda::tuned::code_object_path()
        } else {
            optimizer_lp_cuda::precision::code_object_path()
        };
        let image = std::fs::read(&image_path).map_err(invalid)?;
        if crate::sha256::hex(&image) != request.code_object_sha256 {
            return Err(invalid("assessment CUDA image identity"));
        }
        let t = Instant::now();
        let context = std::rc::Rc::new(
            optimizer_cuda_sys::Context::create(&request.device).map_err(invalid)?,
        );
        let executed = context.device().uuid.clone();
        if executed != request.device {
            return Err(invalid("assessment executed device identity"));
        }
        phases.insert("context".into(), t.elapsed().as_nanos() as u64);
        let t = Instant::now();
        let (o, mut d) = optimizer_lp_cuda::assess::execute(
            context,
            &engine,
            request.arithmetic,
            precision_operator.as_ref(),
            request.policy,
            request.diagnostic,
            &image,
            &image_path,
            request.device_buffer_bytes,
            cancel,
            deadline,
            check,
        )
        .map_err(invalid)?;
        phases.insert("solve_loop".into(), t.elapsed().as_nanos() as u64);
        if let Some(execution) = &mut d.execution {
            execution.code_object_sha256 = Some(request.code_object_sha256.clone());
        }
        (o, Some(executed), d.execution)
    };
    phases.insert("original_model_assessments".into(), check_ns);
    let final_assessment = if outcome.point.is_some() {
        last_assessment.ok_or_else(|| invalid("missing final assessment"))?
    } else {
        assessment(&model, &p, None, &request.options)?
    };
    let frames = std::mem::take(&mut outcome.frames);
    phases.insert("execute_total".into(), start.elapsed().as_nanos() as u64);
    let _ = deadline;
    let witness = Witness {
        request,
        executor: if cpu { "cpu" } else { "gpu" }.into(),
        executed_device,
        outcome,
        initial,
        traces: Vec::new(),
        phases_ns: phases,
        execution,
    };
    Ok(Bundle {
        evidence: Evidence {
            schema_version: 1,
            witness,
            assessment: final_assessment,
            payload_sha256: String::new(),
        },
        frames,
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    fn request() -> Request {
        let method =
            LpSettings::from_json(include_bytes!("../../../examples/lp-settings-v1.json")).unwrap();
        let options = SolveOptions {
            schema_version: 1,
            seed: 17,
            time_limit_ms: Some(30000),
            iteration_limit: Some(1801),
            node_limit: None,
            threads: 1,
            tolerances: optimizer_core::Tolerances {
                absolute: 1e-9,
                relative: 1e-9,
                integrality: 1e-9,
            },
        };
        Request {
            schema_version: 1,
            identity: "lp-assess-v1".into(),
            arithmetic: Arithmetic::TunedFp64,
            policy: Policy::Bounded800,
            model_sha256: crate::sha256::hex(include_bytes!("../../../examples/lp-model-v1.json")),
            source_tree_sha256: "a".repeat(64),
            executable_sha256: "b".repeat(64),
            code_object_sha256: "c".repeat(64),
            device: "GPU-test".into(),
            options,
            method: LpSettings {
                iteration_limit: 1801,
                ..method
            },
            diagnostic: false,
            device_buffer_bytes: 1 << 30,
        }
    }
    fn fixture() -> (Vec<u8>, Evidence) {
        let bytes = include_bytes!("../../../examples/lp-model-v1.json").to_vec();
        let r = request();
        let m = Model::from_json(&bytes).unwrap();
        let p = LinearProgram::new(&m).unwrap();
        let e = Engine::new(&p, r.method);
        // A deliberately stationary wrong endpoint has a zero indicator forever.
        let outcome = optimizer_lp::assess::run(
            &e,
            r.policy,
            false,
            &CancellationToken::new(),
            None,
            64,
            |c, n| c.commit_steps(n).map_err(str::to_string),
            |point| {
                assessment(&m, &p, Some(point), &r.options)
                    .unwrap()
                    .gap_closed
            },
        );
        let initial = Frame {
            point: Point {
                iteration: 0,
                primal: e.unscale_primal(&e.start_primal()),
                dual: e.unscale_dual(&e.start_dual()),
            },
            scaled_primal: e.start_primal(),
            scaled_dual: e.start_dual(),
            weight: 1.,
            restarts: 0,
        };
        let a = assessment(&m, &p, outcome.point.as_ref(), &r.options).unwrap();
        let mut execution = optimizer_core::LpExecutionDiagnostics::new(
            optimizer_lp_cuda::assess::execution_settings(),
        );
        execution.code_object_sha256 = Some(r.code_object_sha256.clone());
        let w = Witness {
            request: r,
            executor: "gpu".into(),
            executed_device: Some("GPU-test".into()),
            outcome,
            initial,
            traces: Vec::new(),
            phases_ns: BTreeMap::new(),
            execution: Some(execution),
        };
        let h = crate::sha256::hex(&serde_json::to_vec(&w).unwrap());
        (
            bytes,
            Evidence {
                schema_version: 1,
                witness: w,
                assessment: a,
                payload_sha256: h,
            },
        )
    }
    fn rehash(e: &mut Evidence) {
        e.payload_sha256 = crate::sha256::hex(&serde_json::to_vec(&e.witness).unwrap());
    }
    #[test]
    fn stationary_signal_never_certifies_or_hides_a_partial_final_point() {
        let (bytes, e) = fixture();
        assert!(!e.assessment.gap_closed);
        assert_eq!(e.witness.outcome.status, "iteration_limit");
        assert_eq!(e.witness.outcome.point.as_ref().unwrap().iteration, 1801);
        e.verify(&bytes, &e.witness.request, Path::new("/tmp"))
            .unwrap();
    }
    #[test]
    fn replay_distinguishes_signed_zero_with_identical_mathematical_assessment() {
        let (bytes, a) = fixture();
        let mut b = a.clone();
        b.witness.outcome.point.as_mut().unwrap().primal[0] = -0.0;
        rehash(&mut b);
        assert_eq!(
            a.witness.outcome, b.witness.outcome,
            "the old float-value comparison misses this"
        );
        a.verify(&bytes, &a.witness.request, Path::new("/tmp"))
            .unwrap();
        b.verify(&bytes, &b.witness.request, Path::new("/tmp"))
            .unwrap();
        assert!(replay_matches(&a, &a, Path::new("/tmp")).unwrap());
        assert!(!replay_matches(&a, &b, Path::new("/tmp")).unwrap());
    }
    #[test]
    fn strict_objects_and_required_nullable_fields() {
        let (_, e) = fixture();
        let raw = serde_json::to_value(e).unwrap();
        for key in ["failure", "point", "physical_steps"] {
            let mut bad = raw.clone();
            bad["witness"]["outcome"]
                .as_object_mut()
                .unwrap()
                .remove(key);
            assert!(Evidence::from_json(&serde_json::to_vec(&bad).unwrap()).is_err());
        }
        let mut bad = raw.clone();
        bad["witness"]["outcome"]["unexpected"] = true.into();
        assert!(Evidence::from_json(&serde_json::to_vec(&bad).unwrap()).is_err());
        let text = serde_json::to_string(&raw).unwrap().replacen(
            "\"schema_version\":1",
            "\"schema_version\":1,\"schema_version\":1",
            1,
        );
        assert!(Evidence::from_json(text.as_bytes()).is_err());
        let mut r = serde_json::to_value(request()).unwrap();
        r.as_object_mut().unwrap().remove("diagnostic");
        assert!(Request::from_json(&serde_json::to_vec(&r).unwrap()).is_err());
    }
    #[test]
    fn rehashed_missing_witness_and_forged_decisions_are_rejected() {
        let (bytes, e) = fixture();
        for k in 0..8 {
            let mut bad = e.clone();
            match k {
                0 => bad.witness.outcome.point = None,
                1 => bad.witness.outcome.status = "accepted".into(),
                2 => bad.witness.outcome.events[1].decision.assess = true,
                3 => bad.witness.outcome.events[0].closed = true,
                4 => bad.witness.outcome.physical_steps = Some(0),
                5 => bad.witness.outcome.point.as_mut().unwrap().iteration = 1800,
                6 => bad.witness.executed_device = Some("GPU-wrong".into()),
                _ => bad.witness.outcome.assessments = 0,
            };
            rehash(&mut bad);
            assert!(
                bad.verify(&bytes, &e.witness.request, Path::new("/tmp"))
                    .is_err(),
                "mutation {k}"
            );
        }
    }
    #[test]
    fn original_objective_senses_offsets_and_perturbations_remain_authoritative() {
        let (_, e) = fixture();
        let mut raw: serde_json::Value =
            serde_json::from_slice(include_bytes!("../../../examples/lp-model-v1.json")).unwrap();
        for sense in ["minimize", "maximize"] {
            raw["objective"]["sense"] = sense.into();
            raw["objective"]["offset"] = 7.into();
            let m = Model::from_json(&serde_json::to_vec(&raw).unwrap()).unwrap();
            let p = LinearProgram::new(&m).unwrap();
            let point = Point {
                iteration: 0,
                primal: vec![0., 0.],
                dual: vec![0.],
            };
            let a = assessment(&m, &p, Some(&point), &e.witness.request.options).unwrap();
            assert_eq!(a.objective, Some(7.));
            let wrong = Point {
                primal: vec![2., 0.],
                ..point
            };
            assert_eq!(
                assessment(&m, &p, Some(&wrong), &e.witness.request.options)
                    .unwrap()
                    .feasible,
                Some(false)
            );
        }
    }
}
