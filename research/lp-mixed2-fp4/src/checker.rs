//! Cached original-model checker. This process never creates a CUDA context.
use crate::Result;
use crate::identity::hex;
use optimizer_core::{Model, Tolerances};
use optimizer_lp::{LinearProgram, certify, certify::assess_gap};
use serde::{Deserialize, Serialize};
use serde_json::{Value, json};
#[derive(Deserialize, Serialize, Clone, PartialEq, Debug)]
#[serde(deny_unknown_fields)]
pub struct Endpoint {
    pub model_sha256: String,
    pub primal: Vec<f64>,
    pub dual: Vec<f64>,
    pub transport: String,
}
pub struct Checker {
    feasibility: crate::prepared_feasibility::Prepared,
    p: LinearProgram,
    hash: String,
    parallel: bool,
    plan: crate::cached_certificate::Plan,
}
impl Checker {
    pub fn new(bytes: &[u8]) -> Result<Self> {
        let model = Model::from_json(bytes)?;
        let p = LinearProgram::new(&model)?;
        let parallel = p.row_major().entries().count() >= 4096;
        Ok(Self {
            parallel,
            plan: crate::cached_certificate::Plan::new(&p),
            feasibility: crate::prepared_feasibility::Prepared::new(model),
            p,
            hash: hex(bytes),
        })
    }
    pub fn assess(&self, e: &Endpoint, tier: &str) -> Result<Value> {
        self.assess_mode(e, tier, false)
    }
    pub fn assess_mode(&self, e: &Endpoint, tier: &str, baseline: bool) -> Result<Value> {
        self.assess_impl(e, tier, baseline, false)
    }
    pub fn assess_serial(&self, e: &Endpoint, tier: &str) -> Result<Value> {
        self.assess_impl(e, tier, true, true)
    }
    fn assess_impl(&self, e: &Endpoint, tier: &str, baseline: bool, serial: bool) -> Result<Value> {
        let tol = match tier {
            "certified-1e-7" => 1e-7,
            "certified-1e-9" => 1e-9,
            _ => return Err("unknown tier".into()),
        };
        if e.model_sha256 != self.hash
            || e.primal.len() != self.p.column_count()
            || e.dual.len() != self.p.row_count()
            || e.primal.iter().chain(&e.dual).any(|v| !v.is_finite())
            || !["completed", "cancelled", "limit", "error", "refused"]
                .contains(&e.transport.as_str())
        {
            return Err("endpoint identity/domain".into());
        }
        let tolerances = Tolerances {
            absolute: tol,
            relative: tol,
            integrality: tol,
        };
        let validation = if baseline {
            self.feasibility.original(&e.primal, tolerances)?
        } else {
            self.feasibility.evaluate(&e.primal, tolerances)?
        };
        let bound = if serial || !self.parallel {
            certify(&self.p, &e.dual)
        } else if baseline {
            crate::parallel_certificate::parallel(&self.p, &e.dual)
        } else {
            self.plan.certify(&self.p, &e.dual)
        };
        let certificate = bound.as_ref().ok();
        let gap = certificate.and_then(|c| assess_gap(&self.p, &e.primal, c.bound, tolerances));
        let eligible = e.transport == "completed";
        let accepted = eligible && validation.feasible && gap.as_ref().is_some_and(|g| g.closed);
        Ok(
            json!({"schema_version":1,"kind":"lp-fp4-accel-certificate","model_sha256":self.hash,
            "endpoint_sha256":hex(&serde_json::to_vec(e)?),"tier":tier,"tolerances":tolerances,"eligible":eligible,
            "feasible":validation.feasible,"objective":validation.objective,"bound":certificate.map(|c|c.bound),
            "gap_upper":gap.as_ref().map(|g|g.upper),"gap_closed":gap.as_ref().is_some_and(|g|g.closed),
            "accepted":accepted,"refusal":bound.err().map(|e|e.to_string())}),
        )
    }
}
