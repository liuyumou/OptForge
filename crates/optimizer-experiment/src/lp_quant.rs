//! ADR-0040 strict, isolated requests and independently certified endpoints.
#![allow(missing_docs)]
use crate::{lp::Assessment, lp_assess::assessment, serde_strict::deserialize_required_object};
use optimizer_core::{
    CancellationToken, ErrorKind, LpSettings, Model, SolveOptions, ValidationError,
};
use optimizer_lp::{
    Engine, LinearProgram,
    assess::Point,
    quant::{HostOracle, Operator, Outcome, Settings},
};
use serde::Serialize;
use std::{
    collections::BTreeMap,
    time::{Duration, Instant},
};
fn invalid(e: impl ToString) -> ValidationError {
    ValidationError::new(ErrorKind::Document, e.to_string())
}
#[derive(Clone, Debug, PartialEq, Serialize)]
pub struct Request {
    pub schema_version: u32,
    pub identity: String,
    pub settings: Settings,
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
    settings: Settings,
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
    pub fn from_json(b: &[u8]) -> Result<Self, ValidationError> {
        crate::lp::unique_json(b)?;
        let r: Self = serde_json::from_slice(b).map_err(invalid)?;
        r.validate()?;
        Ok(r)
    }
    pub fn validate(&self) -> Result<(), ValidationError> {
        self.options.validate()?;
        self.method.validate()?;
        self.settings.validate().map_err(invalid)?;
        let expected =
            LpSettings::from_json(include_bytes!("../../../examples/lp-settings-v1.json"))?;
        let mut actual = self.method;
        actual.iteration_limit = expected.iteration_limit;
        let hashes = [
            &self.model_sha256,
            &self.source_tree_sha256,
            &self.executable_sha256,
            &self.code_object_sha256,
        ];
        if self.schema_version != 1
            || self.identity != "lp-quant-v1"
            || !self.device.starts_with("GPU-")
            || hashes.iter().any(|s| {
                s.len() != 64
                    || !s
                        .bytes()
                        .all(|c| c.is_ascii_digit() || (b'a'..=b'f').contains(&c))
            })
            || actual != expected
            || self.method.check_interval != 200
            || self.method.iteration_limit > 50000
            || self.options.iteration_limit != Some(self.method.iteration_limit)
            || self.options.seed != 17
            || self.options.threads != 1
            || self.options.tolerances.absolute != 1e-9
            || self.options.tolerances.relative != 1e-9
            || self.options.tolerances.integrality != 1e-9
            || self
                .options
                .time_limit_ms
                .is_none_or(|n| n == 0 || n > 30000)
            || self.device_buffer_bytes == 0
            || self.device_buffer_bytes > 1 << 30
            || self.diagnostic && self.method.iteration_limit > 2000
        {
            return Err(invalid("quant request identity/settings/limits"));
        }
        Ok(())
    }
}
#[derive(Clone, Debug, PartialEq, Serialize)]
pub struct Evidence {
    pub schema_version: u32,
    pub request: Request,
    pub executor: String,
    pub executed_device: Option<String>,
    pub outcome: Outcome,
    pub assessment: Assessment,
    pub phases_ns: BTreeMap<String, u64>,
    pub launches: u64,
    pub upload_bytes: u64,
    pub readback_bytes: u64,
    pub device_peak_bytes: u64,
    pub payload_sha256: String,
}
deserialize_required_object!(Evidence{schema_version:u32,request:Request,executor:String,executed_device:Option<String>,outcome:Outcome,assessment:Assessment,phases_ns:BTreeMap<String,u64>,launches:u64,upload_bytes:u64,readback_bytes:u64,device_peak_bytes:u64,payload_sha256:String});
fn payload(e: &Evidence) -> Result<String, ValidationError> {
    Ok(crate::sha256::hex(
        &serde_json::to_vec(&(
            &e.request,
            &e.executor,
            &e.executed_device,
            &e.outcome,
            &e.assessment,
            &e.phases_ns,
            e.launches,
            e.upload_bytes,
            e.readback_bytes,
            e.device_peak_bytes,
        ))
        .map_err(invalid)?,
    ))
}
impl Evidence {
    pub fn from_json(b: &[u8]) -> Result<Self, ValidationError> {
        crate::lp::unique_json(b)?;
        let raw: serde_json::Value = serde_json::from_slice(b).map_err(invalid)?;
        let parsed: Self = serde_json::from_value(raw.clone()).map_err(invalid)?;
        fn keys(a: &serde_json::Value, b: &serde_json::Value) -> bool {
            match (a, b) {
                (serde_json::Value::Object(a), serde_json::Value::Object(b)) => {
                    a.len() == b.len()
                        && b.iter().all(|(k, v)| a.get(k).is_some_and(|x| keys(x, v)))
                }
                (serde_json::Value::Array(a), serde_json::Value::Array(b)) => {
                    a.len() == b.len() && a.iter().zip(b).all(|(a, b)| keys(a, b))
                }
                _ => true,
            }
        }
        if !keys(&raw, &serde_json::to_value(&parsed).map_err(invalid)?) {
            return Err(invalid("quant missing required nested field"));
        }
        Ok(parsed)
    }
    pub fn verify(&self, bytes: &[u8], expected: &Request) -> Result<(), ValidationError> {
        expected.validate()?;
        if self.schema_version != 1
            || &self.request != expected
            || crate::sha256::hex(bytes) != expected.model_sha256
            || payload(self)? != self.payload_sha256
        {
            return Err(invalid("quant evidence identity/integrity"));
        }
        if !["cpu", "gpu"].contains(&self.executor.as_str())
            || self.executor == "gpu" && self.executed_device.as_ref() != Some(&expected.device)
            || self.executor == "cpu"
                && (!expected.diagnostic
                    || self.executed_device.is_some()
                    || self.launches != 0
                    || self.device_peak_bytes != 0)
        {
            return Err(invalid("quant executor identity"));
        }
        let model = Model::from_json(bytes)?;
        let p = LinearProgram::new(&model)?;
        optimizer_lp::quant::admit_shape(&p).map_err(invalid)?;
        let mut engine = Engine::new(&p, expected.method);
        let op = Operator::new(&engine, expected.settings.clone()).map_err(invalid)?;
        engine.restrict_step(op.step).map_err(invalid)?;
        let o = &self.outcome;
        o.promotion.validate(&op).map_err(invalid)?;
        let finite = o
            .primal
            .iter()
            .chain(&o.dual)
            .chain(&o.scaled_primal)
            .chain(&o.scaled_dual)
            .all(|v| v.is_finite());
        if !finite
            || o.primal.len() != p.column_count()
            || o.dual.len() != p.row_count()
            || o.scaled_primal.len() != p.column_count()
            || o.scaled_dual.len() != p.row_count()
            || o.norm.to_bits() != op.norm.to_bits()
            || o.step.to_bits() != engine.step().to_bits()
            || o.physical > expected.method.iteration_limit
            || o.iterations > o.physical
            || o.work.proposals.checked_add(o.work.audits) != Some(o.physical)
            || o.work.rejected > o.work.proposals
            || o.work.proposals.checked_sub(o.work.rejected) != Some(o.iterations)
            || o.work
                .low_products
                .checked_add(o.work.high_products)
                .is_none_or(|n| n > 2 * p.nonzeros() as u64 * o.work.proposals)
            || o.work.replays > o.work.proposals
            || o.work.audits > o.work.proposals
            || o.work.assessments > o.work.proposals + 2
            || self.device_peak_bytes > expected.device_buffer_bytes
            || o.transitions.len() > 9
        {
            return Err(invalid("quant outcome dimensions/counters"));
        }
        let bits = |a: &[f64], b: &[f64]| {
            a.len() == b.len() && a.iter().zip(b).all(|(a, b)| a.to_bits() == b.to_bits())
        };
        if !bits(&engine.unscale_primal(&o.scaled_primal), &o.primal)
            || !bits(&engine.unscale_dual(&o.scaled_dual), &o.dual)
        {
            return Err(invalid("quant scaling identity"));
        }
        let allowed = [
            "certified",
            "iteration_limit",
            "numerical_failure",
            "device_failure",
            "time_limit",
            "interrupted",
        ];
        if !allowed.contains(&o.stop.as_str())
            || matches!(o.stop.as_str(), "numerical_failure" | "device_failure")
                != o.failure.is_some()
            || expected.diagnostic && o.stop == "certified"
        {
            return Err(invalid("quant failure metadata"));
        }
        let mut last = 0;
        for t in &o.transitions {
            if t.generation <= last
                || t.generation > o.promotion.generation
                || t.iteration > o.iterations
                || t.promoted_coefficients > op.values.len() as u64
                || t.reason.is_empty()
            {
                return Err(invalid("quant transition metadata"));
            }
            last = t.generation;
        }
        let a = assessment(
            &model,
            &p,
            Some(&Point {
                iteration: o.iterations,
                primal: o.primal.clone(),
                dual: o.dual.clone(),
            }),
            &expected.options,
        )?;
        if a != self.assessment || o.stop == "certified" && !a.gap_closed {
            return Err(invalid("quant original-model assessment"));
        }
        Ok(())
    }
    pub fn write(&self, path: &std::path::Path) -> Result<(), ValidationError> {
        use std::io::Write;
        let mut f = std::fs::OpenOptions::new()
            .create_new(true)
            .write(true)
            .open(path)
            .map_err(invalid)?;
        f.write_all(&serde_json::to_vec(self).map_err(invalid)?)
            .map_err(invalid)?;
        f.sync_all().map_err(invalid)
    }
}
pub fn replay_matches(a: &Evidence, b: &Evidence) -> bool {
    let bits = |x: &[f64], y: &[f64]| {
        x.len() == y.len() && x.iter().zip(y).all(|(x, y)| x.to_bits() == y.to_bits())
    };
    a.request == b.request
        && a.executor == b.executor
        && a.executed_device == b.executed_device
        && a.outcome.work == b.outcome.work
        && a.outcome.transitions == b.outcome.transitions
        && a.outcome.promotion == b.outcome.promotion
        && a.outcome.stop == b.outcome.stop
        && a.outcome.failure == b.outcome.failure
        && a.outcome.iterations == b.outcome.iterations
        && a.outcome.physical == b.outcome.physical
        && bits(&a.outcome.scaled_primal, &b.outcome.scaled_primal)
        && bits(&a.outcome.scaled_dual, &b.outcome.scaled_dual)
        && a.assessment == b.assessment
}
pub fn execute(
    bytes: &[u8],
    request: Request,
    cpu: bool,
    cancel: &CancellationToken,
) -> Result<Evidence, ValidationError> {
    request.validate()?;
    if crate::sha256::hex(bytes) != request.model_sha256 {
        return Err(invalid("quant model identity"));
    }
    if cpu && !request.diagnostic {
        return Err(invalid("CPU requires diagnostic request"));
    }
    if crate::sha256::hex(
        &std::fs::read(std::env::current_exe().map_err(invalid)?).map_err(invalid)?,
    ) != request.executable_sha256
    {
        return Err(invalid("quant executable identity"));
    }
    let begin = Instant::now();
    let profile = if request.diagnostic {
        Some(optimizer_core::lp_cost::Session::begin().map_err(invalid)?)
    } else {
        None
    };
    let deadline =
        (!cpu).then(|| begin + Duration::from_millis(request.options.time_limit_ms.unwrap()));
    let model = Model::from_json(bytes)?;
    let p = LinearProgram::new(&model)?;
    optimizer_lp::quant::admit_shape(&p).map_err(invalid)?;
    let mut engine = Engine::new(&p, request.method);
    let op = Operator::new(&engine, request.settings.clone()).map_err(invalid)?;
    engine.restrict_step(op.step).map_err(invalid)?;
    let mut phases = BTreeMap::new();
    phases.insert("host_preparation".into(), begin.elapsed().as_nanos() as u64);
    let mut assessment_ns = 0;
    let mut check = |x: &[f64], y: &[f64]| {
        let _cost = optimizer_core::lp_cost::scope("quant_original_assessment");
        let t = Instant::now();
        let result = assessment(
            &model,
            &p,
            Some(&Point {
                iteration: 0,
                primal: x.to_vec(),
                dual: y.to_vec(),
            }),
            &request.options,
        )
        .is_ok_and(|a| a.gap_closed);
        assessment_ns += t.elapsed().as_nanos() as u64;
        result
    };
    let (mut launches, mut upload_bytes, mut readback_bytes, mut device_peak_bytes) = (0, 0, 0, 0);
    let mut executed_device = None;
    let loop_start = Instant::now();
    let outcome = if cpu {
        optimizer_lp::quant::run(
            &engine,
            &op,
            &mut HostOracle,
            request.diagnostic,
            cancel,
            None,
            &mut check,
        )
    } else {
        if std::env::var("AI_OPTIMIZER_GPU_LEASE").ok().as_deref() != Some("inherited")
            || std::env::var("CUDA_VISIBLE_DEVICES").ok().as_deref()
                != Some(request.device.as_str())
        {
            return Err(invalid("selected shared host lease required"));
        }
        let image = std::fs::read(optimizer_lp_cuda::quant::code_object_path()).map_err(invalid)?;
        if crate::sha256::hex(&image) != request.code_object_sha256 {
            return Err(invalid("quant image identity"));
        }
        let t = Instant::now();
        let context = std::rc::Rc::new(
            optimizer_cuda_sys::Context::create(&request.device).map_err(invalid)?,
        );
        if context.device().uuid != request.device {
            return Err(invalid("quant executed device"));
        }
        executed_device = Some(context.device().uuid.clone());
        phases.insert("context".into(), t.elapsed().as_nanos() as u64);
        let mut oracle = optimizer_lp_cuda::quant::Oracle::new(
            context,
            &op,
            &image,
            request.device_buffer_bytes,
        )
        .map_err(invalid)?;
        let outcome = optimizer_lp::quant::run(
            &engine,
            &op,
            &mut oracle,
            request.diagnostic,
            cancel,
            deadline,
            &mut check,
        );
        launches = oracle.counters.launches;
        upload_bytes = oracle.counters.upload_bytes;
        readback_bytes = oracle.counters.readback_bytes;
        device_peak_bytes = oracle.counters.peak_bytes;
        outcome
    };
    phases.insert("solve_loop".into(), loop_start.elapsed().as_nanos() as u64);
    phases.insert("original_model_assessments".into(), assessment_ns);
    let final_assessment = assessment(
        &model,
        &p,
        Some(&Point {
            iteration: outcome.iterations,
            primal: outcome.primal.clone(),
            dual: outcome.dual.clone(),
        }),
        &request.options,
    )?;
    phases.insert("execute_total".into(), begin.elapsed().as_nanos() as u64);
    if let Some(profile) = profile {
        let profile = profile.finish();
        if !profile.unavailable.is_empty() {
            return Err(invalid("quant incomplete cost profile"));
        }
        for row in profile.scopes {
            phases.insert(format!("cost/{}", row.path.join("/")), row.exclusive_ns);
        }
    }
    let mut e = Evidence {
        schema_version: 1,
        request,
        executor: if cpu { "cpu" } else { "gpu" }.into(),
        executed_device,
        outcome,
        assessment: final_assessment,
        phases_ns: phases,
        launches,
        upload_bytes,
        readback_bytes,
        device_peak_bytes,
        payload_sha256: String::new(),
    };
    e.payload_sha256 = payload(&e)?;
    // Independent self-verification prepares a new operator. Release the solve's
    // preparation first so the admitted peak cannot contain two live operators.
    drop(op);
    drop(engine);
    drop(p);
    drop(model);
    e.verify(bytes, &e.request)?;
    Ok(e)
}

#[cfg(test)]
mod tests {
    use super::*;
    fn fixture() -> (Vec<u8>, Request) {
        let bytes = include_bytes!("../../../examples/lp-model-v1.json").to_vec();
        let mut options = serde_json::from_slice::<SolveOptions>(include_bytes!(
            "../../../examples/solve-config-v1.json"
        ))
        .unwrap();
        options.seed = 17;
        options.time_limit_ms = Some(30000);
        options.iteration_limit = Some(80);
        let mut method =
            LpSettings::from_json(include_bytes!("../../../examples/lp-settings-v1.json")).unwrap();
        method.iteration_limit = 80;
        let r = Request {
            schema_version: 1,
            identity: "lp-quant-v1".into(),
            settings: Settings::new(
                optimizer_lp::quant::Format::Fp16,
                optimizer_lp::quant::Policy::Uniform,
            ),
            model_sha256: crate::sha256::hex(&bytes),
            source_tree_sha256: "a".repeat(64),
            executable_sha256: crate::sha256::hex(
                &std::fs::read(std::env::current_exe().unwrap()).unwrap(),
            ),
            code_object_sha256: "b".repeat(64),
            device: "GPU-contract".into(),
            options,
            method,
            diagnostic: true,
            device_buffer_bytes: 1 << 30,
        };
        (bytes, r)
    }
    #[test]
    fn cpu_evidence_roundtrip_reassesses_original_model() {
        let (b, r) = fixture();
        let e = execute(&b, r.clone(), true, &CancellationToken::new()).unwrap();
        let raw = serde_json::to_vec(&e).unwrap();
        let mut missing = serde_json::to_value(&e).unwrap();
        missing["outcome"]
            .as_object_mut()
            .unwrap()
            .remove("failure");
        assert!(Evidence::from_json(&serde_json::to_vec(&missing).unwrap()).is_err());
        Evidence::from_json(&raw).unwrap().verify(&b, &r).unwrap();
        assert_eq!(
            e.outcome.physical,
            e.outcome.work.proposals + e.outcome.work.audits
        );
    }
    #[test]
    fn resigned_counter_failure_and_assessment_corruptions_are_rejected() {
        let (b, r) = fixture();
        let e = execute(&b, r.clone(), true, &CancellationToken::new()).unwrap();
        for kind in 0..3 {
            let mut bad = e.clone();
            match kind {
                0 => bad.outcome.work.proposals = u64::MAX,
                1 => bad.outcome.failure = Some("invented".into()),
                _ => bad.assessment.gap_closed = !bad.assessment.gap_closed,
            };
            bad.payload_sha256 = payload(&bad).unwrap();
            assert!(bad.verify(&b, &r).is_err());
        }
    }
    #[test]
    fn duplicate_settings_and_opposite_zero_replay_are_rejected() {
        let (b, r) = fixture();
        let raw = serde_json::to_string(&r).unwrap().replace(
            "\"schema_version\":1",
            "\"schema_version\":1,\"schema_version\":1",
        );
        assert!(Request::from_json(raw.as_bytes()).is_err());
        let mut a = execute(&b, r, true, &CancellationToken::new()).unwrap();
        let mut c = a.clone();
        a.outcome.scaled_primal[0] = 0.;
        c.outcome.scaled_primal[0] = -0.;
        assert!(!replay_matches(&a, &c));
    }
}
