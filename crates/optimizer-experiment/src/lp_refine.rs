//! Strict ADR-0037 research requests, original-model evidence and replay.
#![allow(missing_docs)]
use crate::{lp::Assessment, serde_strict::deserialize_required_object};
use optimizer_core::{
    Assignment, CancellationToken, Candidate, ErrorKind, LpSettings, Model, SolveOptions,
    ValidationError,
};
use optimizer_lp::{
    LinearProgram, certify,
    certify::assess_gap,
    refine::{EqualityBox, Outcome, ProductWidth},
};
use serde::Serialize;
use std::{
    collections::BTreeMap,
    rc::Rc,
    time::{Duration, Instant},
};
#[derive(Clone, Debug, PartialEq, Serialize)]
pub struct Request {
    pub schema_version: u32,
    pub identity: String,
    pub width: ProductWidth,
    pub anchored: bool,
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
    identity: String,
    width: ProductWidth,
    anchored: bool,
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
fn invalid(x: impl ToString) -> ValidationError {
    ValidationError::new(ErrorKind::Document, x.to_string())
}
impl Request {
    pub fn from_json(bytes: &[u8]) -> Result<Self, ValidationError> {
        crate::lp::unique_json(bytes)?;
        let x: Self = serde_json::from_slice(bytes).map_err(invalid)?;
        x.validate()?;
        Ok(x)
    }
    pub fn validate(&self) -> Result<(), ValidationError> {
        self.options.validate()?;
        self.method.validate()?;
        let hash = |s: &str| {
            s.len() == 64
                && s.bytes()
                    .all(|c| c.is_ascii_digit() || (b'a'..=b'f').contains(&c))
        };
        if self.schema_version != 1
            || self.identity != "lp-refine-v1"
            || !self.device.starts_with("GPU-")
            || ![
                &self.model_sha256,
                &self.source_tree_sha256,
                &self.executable_sha256,
                &self.code_object_sha256,
            ]
            .iter()
            .all(|h| hash(h))
            || self.options.iteration_limit != Some(self.method.iteration_limit)
            || self.method.iteration_limit > 50000
            || self.method.check_interval != 200
            || self.device_buffer_bytes == 0
            || self.device_buffer_bytes > 1 << 30
            || self
                .options
                .time_limit_ms
                .is_none_or(|x| x == 0 || x > 30000)
            || self.anchored && self.width != ProductWidth::F32
        {
            return Err(invalid("refine identity/settings/limits"));
        }
        Ok(())
    }
}
#[derive(Clone, Debug, PartialEq, Serialize)]
pub struct Observations {
    pub phases_ns: BTreeMap<String, u64>,
    pub kernel_launches: u64,
    pub upload_bytes: u64,
    pub readback_bytes: u64,
    pub allocations: u64,
    pub device_peak_bytes: u64,
    pub synchronizations: u64,
}
deserialize_required_object!(Observations{phases_ns:BTreeMap<String,u64>,kernel_launches:u64,upload_bytes:u64,readback_bytes:u64,allocations:u64,device_peak_bytes:u64,synchronizations:u64});
#[derive(Clone, Debug, PartialEq, Serialize)]
pub struct Witness {
    pub request: Request,
    pub executed_device: Option<String>,
    pub outcome: Outcome,
    pub observations: Observations,
}
deserialize_required_object!(Witness {
    request: Request,
    executed_device: Option<String>,
    outcome: Outcome,
    observations: Observations
});
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
fn assessment(
    model: &Model,
    p: &LinearProgram,
    v: &[f64],
    y: &[f64],
    options: &SolveOptions,
) -> Result<Assessment, ValidationError> {
    if v.len() != p.column_count() + p.row_count()
        || y.len() != p.row_count()
        || !v.iter().chain(y).all(|x| x.is_finite())
    {
        return Err(invalid("refine endpoint dimensions/nonfinite"));
    }
    let candidate = Candidate {
        schema_version: 1,
        model_id: model.document().model_id.clone(),
        values: p
            .variable_ids()
            .iter()
            .zip(v)
            .map(|(&variable_id, &value)| Assignment { variable_id, value })
            .collect(),
    };
    let report = model.evaluate(&candidate, options.tolerances)?;
    let certificate = certify(p, y);
    let reason = certificate.as_ref().err().map(ToString::to_string);
    let certificate = certificate.ok();
    let bound = certificate.as_ref().map(|c| c.bound);
    let gap = if report.feasible {
        bound.and_then(|b| assess_gap(p, &v[..p.column_count()], b, options.tolerances))
    } else {
        None
    };
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
        allowance: certificate.as_ref().map(|c| c.allowance),
        repaired: certificate.as_ref().map(|c| c.repaired),
        reason,
    })
}
impl Evidence {
    pub fn from_json(bytes: &[u8]) -> Result<Self, ValidationError> {
        crate::lp::unique_json(bytes)?;
        serde_json::from_slice(bytes).map_err(invalid)
    }
    pub fn verify(&self, bytes: &[u8], expected: &Request) -> Result<(), ValidationError> {
        expected.validate()?;
        let w = &self.witness;
        let o = &w.outcome;
        let model = Model::from_json(bytes)?;
        let p = LinearProgram::new(&model)?;
        let eq = EqualityBox::new(&p).map_err(invalid)?;
        if self.schema_version != 1
            || &w.request != expected
            || expected.model_sha256 != crate::sha256::hex(bytes)
            || w.executed_device
                .as_ref()
                .is_some_and(|d| d != &expected.device)
            || o.work.physical_updates > 0 && w.executed_device.is_none()
            || o.width
                != if expected.width == ProductWidth::F32 && o.work.promotions == 0 {
                    ProductWidth::F32
                } else {
                    ProductWidth::F64
                }
            || o.status == "accepted"
                && o.work.physical_updates > 0
                && o.trace.last().is_none_or(|x| x.decision != "certified")
            || self.payload_sha256 != crate::sha256::hex(&serde_json::to_vec(w).map_err(invalid)?)
            || o.work.physical_updates > expected.method.iteration_limit
            || o.work.committed_updates > o.work.physical_updates
            || o.work.promotions > u64::from(expected.width == ProductWidth::F32)
            || o.work.corrections > 33
            || o.work.failed_corrections > 2
            || o.work.refreshes > 8 * o.work.corrections
            || o.work.sparse_products > 2 * o.work.physical_updates
            || o.work.guard_products > 2 * o.work.sparse_products
            || o.work.anchor_products != 2 * o.work.refreshes
            || w.observations.kernel_launches > o.work.sparse_products
            || w.observations.device_peak_bytes > expected.device_buffer_bytes
            || self.assessment != assessment(&model, &p, &o.v, &o.y, &expected.options)?
            || o.status == "accepted" && !self.assessment.gap_closed
        {
            return Err(invalid("refine evidence identity/work/certification"));
        }
        if ![
            "accepted",
            "unsupported",
            "iteration_limit",
            "time_limit",
            "interrupted",
            "device_failure",
        ]
        .contains(&o.status.as_str())
        {
            return Err(invalid("refine status"));
        }
        let initial = eq.initial();
        let initial_c = eq.correction(&initial.0, &initial.1).map_err(invalid)?;
        let base = optimizer_lp::refine::correction_program(&eq, &initial_c).map_err(invalid)?;
        let prepared = optimizer_lp::refine::PreparedCorrection::new(&base, expected.method);
        let engine = prepared.bind(&base).map_err(invalid)?;
        let generation = optimizer_lp::refine::InnerOperator::new(&engine, p.column_count())
            .map_err(invalid)?
            .generation();
        let mut current_v = initial.0;
        let mut current_y = initial.1;
        let mut previous = 0;
        let mut previous_correction = 0;
        let mut saw_native = expected.width == ProductWidth::F64;
        for event in &o.trace {
            if event.anchor_v != current_v
                || event.anchor_y != current_y
                || event.generation != generation
                || event.physical_updates < previous
                || event.physical_updates > o.work.physical_updates
                || event.correction < previous_correction
                || event.correction > o.work.corrections
                || saw_native && event.width != ProductWidth::F64
                || event.anchor_merit
                    != eq
                        .merit(&event.anchor_v, &event.anchor_y)
                        .map_err(invalid)?
            {
                return Err(invalid("refine trace ordering/anchor"));
            }
            saw_native |= event.width == ProductWidth::F64;
            previous = event.physical_updates;
            previous_correction = event.correction;
            let c = eq
                .correction(&event.anchor_v, &event.anchor_y)
                .map_err(invalid)?;
            if event.primal_exponent != c.primal_exponent || event.dual_exponent != c.dual_exponent
            {
                return Err(invalid("refine correction scales"));
            }
            if let (Some(v), Some(y), Some(merit)) = (
                &event.candidate_v,
                &event.candidate_y,
                event.candidate_merit,
            ) {
                if merit != eq.merit(v, y).map_err(invalid)?
                    || ["contracted", "certified"].contains(&event.decision.as_str())
                        && !event.errors.admits(event.anchor_merit)
                {
                    return Err(invalid("refine progress/error enclosure"));
                }
                if event.decision == "contracted"
                    && !optimizer_lp::refine::contracts_progress(event.anchor_merit, merit)
                {
                    return Err(invalid("refine contraction"));
                }
                if ["contracted", "certified"].contains(&event.decision.as_str()) {
                    current_v = v.clone();
                    current_y = y.clone();
                }
                if event.decision == "certified"
                    && !assessment(&model, &p, v, y, &expected.options)?.gap_closed
                {
                    return Err(invalid("refine false trace certificate"));
                }
            } else if event.candidate_v.is_some()
                || event.candidate_y.is_some()
                || event.candidate_merit.is_some()
            {
                return Err(invalid("partial trace witness"));
            }
        }
        if current_v != o.v || current_y != o.y {
            return Err(invalid("refine final witness/trace chain"));
        }
        Ok(())
    }
}
pub fn solve(
    bytes: &[u8],
    request: Request,
    cancel: &CancellationToken,
) -> Result<Evidence, ValidationError> {
    request.validate()?;
    if request.model_sha256 != crate::sha256::hex(bytes) {
        return Err(invalid("refine model hash"));
    }
    if std::env::var("AI_OPTIMIZER_GPU_LEASE").ok().as_deref() != Some("inherited") {
        return Err(invalid("shared host lease required"));
    }
    let start = Instant::now();
    let deadline = start + Duration::from_millis(request.options.time_limit_ms.unwrap());
    let model = Model::from_json(bytes)?;
    let p = LinearProgram::new(&model)?;
    let eq = EqualityBox::new(&p).map_err(invalid)?;
    let image = std::fs::read(optimizer_lp_cuda::refine::code_object_path()).map_err(invalid)?;
    if crate::sha256::hex(&image) != request.code_object_sha256
        || crate::sha256::hex(
            &std::fs::read(std::env::current_exe().map_err(invalid)?).map_err(invalid)?,
        ) != request.executable_sha256
    {
        return Err(invalid("refine executable/image identity"));
    }
    let mut oracle = DeferredOracle {
        device: request.device.clone(),
        image,
        cap: request.device_buffer_bytes,
        inner: None,
        executed_device: None,
        phases: BTreeMap::new(),
    };
    let floor = [
        request.options.tolerances.absolute,
        request.options.tolerances.relative,
    ]
    .into_iter()
    .filter(|x| *x > 0.0)
    .reduce(f64::min)
    .unwrap_or(0.0);
    let solve_start = Instant::now();
    let outcome = optimizer_lp::refine::run(
        &eq,
        request.method,
        request.width,
        request.anchored,
        floor,
        deadline,
        cancel,
        &mut oracle,
        |v, y| assessment(&model, &p, v, y, &request.options).is_ok_and(|a| a.gap_closed),
    );
    let solve_ns = solve_start.elapsed().as_nanos() as u64;
    let mut phases = oracle.phases.clone();
    let mut observations = Observations {
        phases_ns: BTreeMap::new(),
        kernel_launches: 0,
        upload_bytes: 0,
        readback_bytes: 0,
        allocations: 0,
        device_peak_bytes: 0,
        synchronizations: 0,
    };
    if let Some(gpu) = &oracle.inner {
        let c = &gpu.counters;
        for (name, &ns) in &c.phases_ns {
            *phases.entry(name.clone()).or_default() += ns;
        }
        observations.kernel_launches = c.launches;
        observations.upload_bytes = c.upload_bytes;
        observations.readback_bytes = c.readback_bytes;
        observations.allocations = c.allocations;
        observations.device_peak_bytes = c.peak_bytes;
        observations.synchronizations = c.synchronizations;
    }
    let executed_device = oracle.executed_device.clone();
    drop(oracle);
    phases.insert(
        "refinement_including_guards_and_assessments".into(),
        solve_ns,
    );
    phases.insert(
        "through_device_teardown".into(),
        start.elapsed().as_nanos() as u64,
    );
    observations.phases_ns = phases;
    let assessed = assessment(&model, &p, &outcome.v, &outcome.y, &request.options)?;
    let witness = Witness {
        request,
        executed_device,
        outcome,
        observations,
    };
    let hash = crate::sha256::hex(&serde_json::to_vec(&witness).map_err(invalid)?);
    let evidence = Evidence {
        schema_version: 1,
        witness,
        assessment: assessed,
        payload_sha256: hash,
    };
    evidence.verify(bytes, &evidence.witness.request)?;
    Ok(evidence)
}

/// Defer all context work until the host transform, operator and norm are admitted.
struct DeferredOracle {
    device: String,
    image: Vec<u8>,
    cap: u64,
    inner: Option<optimizer_lp_cuda::refine::Oracle>,
    executed_device: Option<String>,
    phases: BTreeMap<String, u64>,
}
impl optimizer_lp::refine::ProductOracle for DeferredOracle {
    fn observe(&mut self, name: &str, ns: u64) {
        *self.phases.entry(name.into()).or_default() += ns;
    }
    fn bind(&mut self, op: &optimizer_lp::refine::InnerOperator) -> Result<(), String> {
        if self.inner.is_none() {
            let start = Instant::now();
            let context = Rc::new(
                optimizer_cuda_sys::Context::create(&self.device)
                    .map_err(|e| format!("device:{e}"))?,
            );
            self.executed_device = Some(context.device().uuid.clone());
            self.inner = Some(optimizer_lp_cuda::refine::Oracle::new(
                context,
                self.image.clone(),
                self.cap,
            )?);
            self.observe("context", start.elapsed().as_nanos() as u64);
        }
        self.inner.as_mut().unwrap().bind(op)
    }
    fn apply(
        &mut self,
        op: &optimizer_lp::refine::InnerOperator,
        t: bool,
        x: &[f64],
        w: ProductWidth,
    ) -> Result<Vec<f64>, String> {
        self.inner
            .as_mut()
            .ok_or("unbound_operator")?
            .apply(op, t, x, w)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    fn request() -> Request {
        Request {
            schema_version: 1,
            identity: "lp-refine-v1".into(),
            width: ProductWidth::F32,
            anchored: true,
            model_sha256: "a".repeat(64),
            source_tree_sha256: "b".repeat(64),
            executable_sha256: "c".repeat(64),
            code_object_sha256: "d".repeat(64),
            device: "GPU-test".into(),
            options: serde_json::from_slice(include_bytes!(
                "../../../examples/solve-config-v1.json"
            ))
            .unwrap(),
            method: LpSettings::published(50000, 200),
            profile: false,
            device_buffer_bytes: 1 << 30,
        }
    }
    #[test]
    fn strict_requests_bind_limits_and_reject_duplicate_or_unknown_fields() {
        let mut r = request();
        r.options.iteration_limit = Some(50000);
        r.options.time_limit_ms = Some(10000);
        r.validate().unwrap();
        let raw = serde_json::to_vec(&r).unwrap();
        assert_eq!(Request::from_json(&raw).unwrap(), r);
        let mut value = serde_json::to_value(&r).unwrap();
        value["unknown"] = true.into();
        assert!(Request::from_json(&serde_json::to_vec(&value).unwrap()).is_err());
        let s = String::from_utf8(raw)
            .unwrap()
            .replacen('{', "{\"schema_version\":1,", 1);
        assert!(Request::from_json(s.as_bytes()).is_err());
        r.method.check_interval = 100;
        assert!(r.validate().is_err());
    }
    #[test]
    fn forged_optimality_and_changed_model_fail_independent_assessment() {
        let bytes = include_bytes!("../../../examples/lp-model-v1.json");
        let model = Model::from_json(bytes).unwrap();
        let p = LinearProgram::new(&model).unwrap();
        let eq = EqualityBox::new(&p).unwrap();
        let (v, y) = eq.initial();
        let mut r = request();
        r.options.iteration_limit = Some(50000);
        r.options.time_limit_ms = Some(10000);
        r.model_sha256 = crate::sha256::hex(bytes);
        let assessed = assessment(&model, &p, &v, &y, &r.options).unwrap();
        assert!(!assessed.gap_closed);
        let w = Witness {
            executed_device: Some(r.device.clone()),
            request: r,
            outcome: Outcome {
                v,
                y,
                work: optimizer_lp::refine::Work::default(),
                trace: vec![],
                status: "unsupported".into(),
                failure: Some("admission_fixture".into()),
                width: ProductWidth::F32,
            },
            observations: Observations {
                phases_ns: BTreeMap::new(),
                kernel_launches: 0,
                upload_bytes: 0,
                readback_bytes: 0,
                allocations: 0,
                device_peak_bytes: 0,
                synchronizations: 0,
            },
        };
        let mut e = Evidence {
            schema_version: 1,
            payload_sha256: crate::sha256::hex(&serde_json::to_vec(&w).unwrap()),
            witness: w,
            assessment: assessed,
        };
        e.verify(bytes, &e.witness.request).unwrap();
        e.witness.outcome.status = "accepted".into();
        e.payload_sha256 = crate::sha256::hex(&serde_json::to_vec(&e.witness).unwrap());
        assert!(e.verify(bytes, &e.witness.request).is_err());
        e.witness.outcome.status = "unsupported".into();
        e.witness.outcome.work.physical_updates = 50001;
        e.payload_sha256 = crate::sha256::hex(&serde_json::to_vec(&e.witness).unwrap());
        assert!(e.verify(bytes, &e.witness.request).is_err());
        assert!(e.verify(b"{}", &e.witness.request).is_err());
    }
}
