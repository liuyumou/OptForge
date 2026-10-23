//! ADR-0041 strict, isolated requests and independently certified endpoints.
#![allow(missing_docs)]
use crate::{lp::Assessment, lp_assess::assessment, serde_strict::deserialize_required_object};
use optimizer_core::{
    CancellationToken, ErrorKind, LpSettings, Model, SolveOptions, ValidationError,
};
use optimizer_lp::{
    Engine, LinearProgram,
    assess::Point,
    quant_resident::{HostOracle, Layout, Operator, Outcome, Settings},
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
    pub layout: Layout,
    pub horizon: u64,
    pub guard: String,
    pub reduction: String,
    pub norm_policy: String,
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
    layout: Layout,
    horizon: u64,
    guard: String,
    reduction: String,
    norm_policy: String,
    device_buffer_bytes: u64
});
impl Request {
    pub fn from_json(b: &[u8]) -> Result<Self, ValidationError> {
        crate::lp::unique_json(b)?;
        let raw: serde_json::Value = serde_json::from_slice(b).map_err(invalid)?;
        let r: Self = serde_json::from_value(raw.clone()).map_err(invalid)?;
        if !crate::lp_quant::same_shape(&raw, &serde_json::to_value(&r).map_err(invalid)?) {
            return Err(invalid("resident request JSON shape"));
        }
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
            || self.identity != "lp-quant-resident-v1"
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
            || self.horizon > 2000
            || self.diagnostic != (self.horizon != 0)
            || self.guard != self.layout.guard()
            || self.reduction != self.layout.tree()
            || self.norm_policy
                != if self.layout == Layout::OriginalTuned {
                    "original-tuned-v1"
                } else {
                    "twice-absolute-original-v1"
                }
            || self.layout != Layout::Segmented
                && self.settings.format != optimizer_lp::quant::Format::Fp64
            || self.layout == Layout::OriginalTuned && !self.diagnostic
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
    pub state_uploads: u64,
    pub device_windows: u64,
    pub host_product_scans: u64,
    pub product_vector_transfers: u64,
    pub payload_sha256: String,
}
deserialize_required_object!(Evidence{schema_version:u32,request:Request,executor:String,executed_device:Option<String>,outcome:Outcome,assessment:Assessment,phases_ns:BTreeMap<String,u64>,launches:u64,upload_bytes:u64,readback_bytes:u64,device_peak_bytes:u64,state_uploads:u64,device_windows:u64,host_product_scans:u64,product_vector_transfers:u64,payload_sha256:String});
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
            e.state_uploads,
            e.device_windows,
            e.host_product_scans,
            e.product_vector_transfers,
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
                _ => crate::lp_quant::same_shape(a, b),
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
                    || self.upload_bytes != 0
                    || self.readback_bytes != 0
                    || self.device_peak_bytes != 0)
        {
            return Err(invalid("quant executor identity"));
        }
        let model = Model::from_json(bytes)?;
        let p = LinearProgram::new(&model)?;
        optimizer_lp::quant::admit_shape(&p).map_err(invalid)?;
        let mut engine = Engine::new(&p, expected.method);
        let op =
            Operator::new(&engine, expected.settings.clone(), expected.layout).map_err(invalid)?;
        if op.layout != Layout::OriginalTuned {
            engine.restrict_step(op.step).map_err(invalid)?;
        }
        let o = &self.outcome.core;
        let c = &self.outcome.counts;
        if self.outcome.layout != expected.layout
            || self.outcome.horizon != expected.horizon
            || self.outcome.guard != expected.guard
            || self.outcome.reduction != expected.reduction
            || self
                .outcome
                .first_certified_iteration
                .is_some_and(|n| n > o.iterations)
            || o.stop == "certified" && self.outcome.first_certified_iteration.is_none()
            || c.low != o.work.low_products
            || c.high != o.work.high_products
            || c.nonzero_t
                .checked_add(c.nonzero_f)
                .is_none_or(|v| v > c.low)
            || c.accepted_nonzero_t > c.nonzero_t
            || c.accepted_nonzero_f > c.nonzero_f
            || c.useful_windows > o.work.audits
            || c.windows > o.work.proposals
            || c.guard_products > c.high
            || expected.layout != Layout::Tuned && c.guard_products != 0
            || expected.layout == Layout::Tuned && c.guard_products.checked_mul(2) != Some(c.high)
            || c.uncertain > o.work.proposals
            || c.uncertain != 0 && o.stop != "device_failure"
            || c.coarse_pass
                .checked_add(c.detailed_pass)
                .and_then(|n| n.checked_add(c.detailed_fail))
                .is_none_or(|n| n > (op.rows + op.columns) as u64 * o.work.proposals.min(50000))
            || expected.horizon != 0 && o.iterations > expected.horizon
            || self.host_product_scans != 0
            || self.product_vector_transfers != 0
            || self.executor == "gpu"
                && (self.device_windows != c.windows || self.state_uploads > self.device_windows)
            || self.executor == "cpu" && (self.state_uploads != 0 || self.device_windows != 0)
        {
            return Err(invalid("resident metadata/counters"));
        }
        op.generation(o.promotion.clone()).map_err(invalid)?;
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
                .is_none_or(|n| {
                    n > (if expected.layout == Layout::Tuned {
                        4
                    } else {
                        2
                    }) * p.nonzeros() as u64
                        * o.work.proposals
                })
            || o.work.replays > o.work.proposals
            || o.work.audits > o.work.proposals
            || o.work.assessments > o.work.proposals + 2
            || self.device_peak_bytes > expected.device_buffer_bytes
            || o.transitions.len() > 9
        {
            return Err(invalid("quant outcome dimensions/counters"));
        }
        if self.executor == "gpu" {
            // Dimensions and physical work have already been bounded above.
            // Use wider arithmetic while checking untrusted serialized counters.
            let windows = u128::from(c.windows);
            let slots = u128::from(o.work.proposals) + u128::from(c.predicated);
            let original = expected.layout == Layout::OriginalTuned;
            let per = if original {
                6
            } else if expected.layout == Layout::Tuned {
                9
            } else {
                7
            };
            let exact_launches = per * slots + if original { 0 } else { 2 * windows };
            let size = (op.rows + op.columns).max(1) as u128;
            let peak = optimizer_lp_cuda::quant_resident::buffer_bytes(&op).map_err(invalid)?;
            let upload_limit = u128::from(peak)
                + 10 * (4 * op.tiles.len().max(1) as u128 + 24 * size)
                + 64 * size * windows;
            let readback_limit = (88 + 32 * size) * windows;
            if c.predicated as u128 > if original { 199 } else { 31 } * windows
                || original && o.failure.is_none() && c.uncertain == 0 && c.predicated != 0
                || self.device_peak_bytes != peak
                || self.launches as u128 > 10 * slots + 2 * windows
                || c.uncertain == 0
                    && o.failure.is_none()
                    && self.launches as u128 != exact_launches
                || self.upload_bytes as u128 > upload_limit
                || self.readback_bytes as u128 > readback_limit
            {
                return Err(invalid("resident physical resource counters"));
            }
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
            "work_horizon",
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
            || o.stop == "work_horizon"
                && (expected.horizon == 0 || o.iterations != expected.horizon)
        {
            return Err(invalid("quant failure metadata"));
        }
        crate::lp_quant::promotion_history(&op, o)?;
        if c.useful_windows > o.iterations / 32
            || c.useful_windows != 0 && (c.accepted_nonzero_t == 0 || c.accepted_nonzero_f == 0)
        {
            return Err(invalid("resident useful-window metadata"));
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
        && a.outcome.core.work == b.outcome.core.work
        && a.outcome.core.transitions == b.outcome.core.transitions
        && a.outcome.core.promotion == b.outcome.core.promotion
        && a.outcome.core.stop == b.outcome.core.stop
        && a.outcome.core.failure == b.outcome.core.failure
        && a.outcome.core.iterations == b.outcome.core.iterations
        && a.outcome.core.physical == b.outcome.core.physical
        && bits(&a.outcome.core.scaled_primal, &b.outcome.core.scaled_primal)
        && bits(&a.outcome.core.scaled_dual, &b.outcome.core.scaled_dual)
        && a.outcome.counts == b.outcome.counts
        && a.outcome.first_certified_iteration == b.outcome.first_certified_iteration
        && a.assessment == b.assessment
}
pub fn execute(
    bytes: &[u8],
    request: Request,
    cpu: bool,
    cancel: &CancellationToken,
) -> Result<Evidence, ValidationError> {
    let begin = Instant::now();
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
    let op = Operator::new(&engine, request.settings.clone(), request.layout).map_err(invalid)?;
    if op.layout != Layout::OriginalTuned {
        engine.restrict_step(op.step).map_err(invalid)?;
    }
    let initial_x = engine.start_primal();
    let initial_y = engine.start_dual();
    if initial_x
        .iter()
        .chain(&initial_y)
        .chain(&engine.unscale_primal(&initial_x))
        .chain(&engine.unscale_dual(&initial_y))
        .any(|v| !v.is_finite())
    {
        return Err(invalid("resident_initial_state_mapping_range"));
    }
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
    let (mut state_uploads, mut device_windows) = (0, 0);
    let mut outcome = if cpu {
        optimizer_lp::quant_resident::run(
            &engine,
            &op,
            &mut HostOracle,
            request.horizon,
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
        let image = std::fs::read(optimizer_lp_cuda::quant_resident::code_object_path())
            .map_err(invalid)?;
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
        let module = context.load_module(&image).map_err(invalid)?;
        let mut oracle = optimizer_lp_cuda::quant_resident::Oracle::new(
            context,
            &op,
            &module,
            request.device_buffer_bytes,
            &engine,
        )
        .map_err(invalid)?;
        let outcome = optimizer_lp::quant_resident::run(
            &engine,
            &op,
            &mut oracle,
            request.horizon,
            cancel,
            deadline,
            &mut check,
        );
        state_uploads = oracle.counters.state_uploads;
        device_windows = oracle.counters.windows;
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
            iteration: outcome.core.iterations,
            primal: outcome.core.primal.clone(),
            dual: outcome.core.dual.clone(),
        }),
        &request.options,
    )?;
    if outcome.core.failure.is_none() {
        if cancel.is_cancelled() {
            outcome.core.stop = "interrupted".into();
        } else if deadline.is_some_and(|d| Instant::now() >= d) {
            outcome.core.stop = "time_limit".into();
        }
    }
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
        state_uploads,
        device_windows,
        host_product_scans: 0,
        product_vector_transfers: 0,
        payload_sha256: String::new(),
    };
    e.payload_sha256 = payload(&e)?;
    // Independent self-verification prepares a new operator. Release the solve's
    // preparation first so the admitted peak cannot contain two live operators.
    drop(op);
    drop(engine);
    drop(p);
    drop(model);
    // The independent verifier runs after the lease, on CPU. Fresh host
    // certification above remains part of this producer and its solve deadline.
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
            identity: "lp-quant-resident-v1".into(),
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
            layout: Layout::Segmented,
            horizon: 64,
            guard: optimizer_lp::quant_resident::GUARD.into(),
            reduction: Layout::Segmented.tree().into(),
            norm_policy: "twice-absolute-original-v1".into(),
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
        missing["outcome"]["core"]
            .as_object_mut()
            .unwrap()
            .remove("failure");
        assert!(Evidence::from_json(&serde_json::to_vec(&missing).unwrap()).is_err());
        Evidence::from_json(&raw).unwrap().verify(&b, &r).unwrap();
        assert_eq!(
            e.outcome.core.physical,
            e.outcome.core.work.proposals + e.outcome.core.work.audits
        );
    }
    #[test]
    fn resigned_counter_failure_and_assessment_corruptions_are_rejected() {
        let (b, r) = fixture();
        let e = execute(&b, r.clone(), true, &CancellationToken::new()).unwrap();
        for kind in 0..3 {
            let mut bad = e.clone();
            match kind {
                0 => bad.outcome.core.work.proposals = u64::MAX,
                1 => bad.outcome.core.failure = Some("invented".into()),
                _ => bad.assessment.gap_closed = !bad.assessment.gap_closed,
            };
            bad.payload_sha256 = payload(&bad).unwrap();
            assert!(bad.verify(&b, &r).is_err());
        }
    }
    #[test]
    fn resigned_transfer_launch_and_predication_counters_are_bounded() {
        let (b, r) = fixture();
        let cpu = execute(&b, r.clone(), true, &CancellationToken::new()).unwrap();
        for upload in [true, false] {
            let mut bad = cpu.clone();
            if upload {
                bad.upload_bytes = 1;
            } else {
                bad.readback_bytes = 1;
            }
            bad.payload_sha256 = payload(&bad).unwrap();
            assert!(bad.verify(&b, &r).is_err(), "CPU transfer accepted");
        }
        // A CPU-generated trajectory supplies an independently verified numerical
        // endpoint; only its executor accounting is synthesized, without a device.
        let mut gpu = cpu;
        gpu.executor = "gpu".into();
        gpu.executed_device = Some(r.device.clone());
        gpu.device_windows = gpu.outcome.counts.windows;
        gpu.state_uploads = gpu.device_windows;
        gpu.launches = 7 * (gpu.outcome.core.work.proposals + gpu.outcome.counts.predicated)
            + 2 * gpu.device_windows;
        let model = Model::from_json(&b).unwrap();
        let p = LinearProgram::new(&model).unwrap();
        let engine = Engine::new(&p, r.method);
        let op = Operator::new(&engine, r.settings.clone(), r.layout).unwrap();
        gpu.device_peak_bytes = optimizer_lp_cuda::quant_resident::buffer_bytes(&op).unwrap();
        gpu.upload_bytes = gpu.device_peak_bytes;
        gpu.payload_sha256 = payload(&gpu).unwrap();
        gpu.verify(&b, &r).unwrap();
        for kind in 0..6 {
            let mut bad = gpu.clone();
            match kind {
                0 => bad.launches = u64::MAX,
                1 => bad.launches += 1,
                2 => bad.upload_bytes = u64::MAX,
                3 => bad.readback_bytes = u64::MAX,
                4 => bad.outcome.counts.predicated = u64::MAX,
                _ => bad.device_peak_bytes -= 1,
            }
            bad.payload_sha256 = payload(&bad).unwrap();
            assert!(bad.verify(&b, &r).is_err(), "counter {kind} accepted");
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
        a.outcome.core.scaled_primal[0] = 0.;
        c.outcome.core.scaled_primal[0] = -0.;
        assert!(!replay_matches(&a, &c));
    }
    #[test]
    fn enum_objects_and_positional_controller_records_are_rejected() {
        let (b, r) = fixture();
        for field in ["layout", "settings"] {
            let mut raw = serde_json::to_value(&r).unwrap();
            if field == "layout" {
                raw[field] = serde_json::json!({"segmented":null});
            } else {
                raw[field]["format"] = serde_json::json!({"fp16":null});
            }
            assert!(Request::from_json(&serde_json::to_vec(&raw).unwrap()).is_err());
        }
        let e = execute(&b, r, true, &CancellationToken::new()).unwrap();
        let mut raw = serde_json::to_value(&e).unwrap();
        raw["request"]["layout"] = serde_json::json!({"segmented":null});
        assert!(Evidence::from_json(&serde_json::to_vec(&raw).unwrap()).is_err());
    }
}
