//! External LP study witnesses; no external solver is a runtime backend.
use crate::serde_strict::deserialize_required_object;
use optimizer_core::{
    Assignment, Candidate, ErrorKind, LpDiagnostics, Model, SolveOptions, SolveRecord, Termination,
    ValidationError,
};
use optimizer_lp::{LinearProgram, certify, certify::assess_gap};
use serde::Serialize;
use std::collections::BTreeMap;
/// Untrusted external solver output bound to original model bytes.
#[derive(Clone, Debug, PartialEq, Serialize)]
pub struct ExternalWitness {
    /// One.
    pub schema_version: u32,
    /// Original model byte hash.
    pub model_sha256: String,
    /// Requested COPT CPU or GPU PDLP.
    pub requested_backend: String,
    /// Observed implementation, or unavailable.
    pub executed_backend: Option<String>,
    /// Requested solve contract; limitations explicitly report unsupported native controls.
    pub options: SolveOptions,
    /// Pinned solver version.
    pub copt_version: String,
    /// Effective explicit parameters.
    pub parameters: BTreeMap<String, f64>,
    /// Exact external library bytes.
    pub library_sha256: String,
    /// Exact Python extension bytes.
    pub binding_sha256: String,
    /// Affirmative PDLP GPU-start log, not merely device discovery.
    pub gpu_confirmed: bool,
    /// Canonical original row IDs.
    pub row_ids: Vec<u32>,
    /// Canonical original variable IDs.
    pub variable_ids: Vec<u32>,
    /// Untrusted original-unit primal.
    pub primal: Option<Vec<f64>>,
    /// Untrusted original-unit dual normalized to minimization.
    pub dual: Option<Vec<f64>>,
    /// Native outcome, without mathematical authority.
    pub status: String,
    /// Native PDLP iterations, when available.
    pub iterations: Option<u64>,
    /// Explicit unsupported controls and execution limitations.
    pub limitations: Vec<String>,
}
deserialize_required_object!(ExternalWitness {schema_version:u32,model_sha256:String,requested_backend:String,executed_backend:Option<String>,options:SolveOptions,
 copt_version:String,parameters:BTreeMap<String,f64>,library_sha256:String,binding_sha256:String,gpu_confirmed:bool,row_ids:Vec<u32>,variable_ids:Vec<u32>,
 primal:Option<Vec<f64>>,dual:Option<Vec<f64>>,status:String,iterations:Option<u64>,limitations:Vec<String>});
/// Independent original-model assessment of external evidence.
#[derive(Clone, Debug, PartialEq, Serialize)]
pub struct ExternalEndpoint {
    /// One; distinct from runtime LP endpoint versions.
    pub schema_version: u32,
    /// Complete untrusted witness and provenance.
    pub witness: ExternalWitness,
    /// Recomputed host assessment.
    pub assessment: crate::lp::Assessment,
    /// Exact serialized witness hash.
    pub payload_sha256: String,
}
deserialize_required_object!(ExternalEndpoint {
    schema_version: u32,
    witness: ExternalWitness,
    assessment: crate::lp::Assessment,
    payload_sha256: String
});
fn invalid(s: &str) -> ValidationError {
    ValidationError::new(ErrorKind::Document, s)
}
impl ExternalWitness {
    /// Parse strict evidence, including duplicate keys inside parameter maps.
    pub fn from_json(bytes: &[u8]) -> Result<Self, ValidationError> {
        crate::lp::unique_json(bytes)?;
        serde_json::from_slice(bytes).map_err(|_| invalid("malformed external witness"))
    }

    /// Validate shape, identity and precision policy, then independently assess.
    pub fn assess(&self, bytes: &[u8]) -> Result<crate::lp::Assessment, ValidationError> {
        self.options.validate()?;
        let model = Model::from_json(bytes)?;
        let program = LinearProgram::new(&model)?;
        let valid_hash = |s: &str| {
            s.len() == 64
                && s.bytes()
                    .all(|b| b.is_ascii_digit() || (b'a'..=b'f').contains(&b))
        };
        if self.schema_version != 1
            || self.model_sha256 != crate::sha256::hex(bytes)
            || self.copt_version != "8.0.6"
            || !valid_hash(&self.library_sha256)
            || !valid_hash(&self.binding_sha256)
            || self.row_ids
                != model
                    .document()
                    .constraints
                    .iter()
                    .map(|r| r.id)
                    .collect::<Vec<_>>()
            || self.variable_ids != program.variable_ids()
            || !["copt-cpu-pdlp", "copt-gpu-pdlp"].contains(&self.requested_backend.as_str())
            || self
                .executed_backend
                .as_ref()
                .is_some_and(|b| !["copt-cpu-pdlp", "copt-gpu-pdlp"].contains(&b.as_str()))
            || (self.executed_backend.as_deref() == Some("copt-gpu-pdlp")) != self.gpu_confirmed
            || (self.requested_backend == "copt-cpu-pdlp" && self.gpu_confirmed)
            || (self.executed_backend.is_none()
                && (self.primal.is_some() || self.dual.is_some() || self.status == "optimal"))
            || self.parameters.values().any(|v| !v.is_finite())
        {
            return Err(invalid("external witness identity differs"));
        }
        let expected = BTreeMap::from([
            ("LpMethod".into(), 6.0),
            (
                "GPUMode".into(),
                if self.requested_backend == "copt-gpu-pdlp" {
                    1.0
                } else {
                    0.0
                },
            ),
            ("GPUDevice".into(), 0.0),
            ("Threads".into(), 1.0),
            ("Crossover".into(), 0.0),
            (
                "TimeLimit".into(),
                self.options
                    .time_limit_ms
                    .ok_or_else(|| invalid("external wall limit required"))? as f64
                    / 1000.0,
            ),
            ("PDLPTol".into(), self.options.tolerances.absolute),
            ("FeasTol".into(), self.options.tolerances.absolute),
            ("DualTol".into(), self.options.tolerances.absolute),
        ]);
        if self.parameters != expected {
            return Err(invalid("external parameters differ"));
        }
        let termination = match self.status.as_str() {
            "optimal" => Termination::Feasible,
            "time_limit" => Termination::TimeLimit,
            "iteration_limit" => Termination::IterationLimit,
            "interrupted" => Termination::Interrupted,
            "unsupported" => Termination::Unsupported,
            "numerical_failure" => Termination::NumericalFailure,
            "backend_failure" => Termination::BackendFailure,
            _ => return Err(invalid("unknown external outcome")),
        };
        if self
            .dual
            .as_ref()
            .is_some_and(|d| d.len() != program.row_count() || d.iter().any(|v| !v.is_finite()))
            || self.primal.as_ref().is_some_and(|v| {
                v.len() != program.column_count() || v.iter().any(|v| !v.is_finite())
            })
        {
            return Err(invalid("external witness dimensions or range"));
        }
        let candidate = self.primal.as_ref().map(|v| Candidate {
            schema_version: 1,
            model_id: model.document().model_id.clone(),
            values: program
                .variable_ids()
                .iter()
                .zip(v)
                .map(|(&variable_id, &value)| Assignment { variable_id, value })
                .collect(),
        });
        let report = candidate
            .as_ref()
            .map(|c| model.evaluate(c, self.options.tolerances))
            .transpose()?;
        let bound = self
            .dual
            .as_ref()
            .and_then(|d| certify(&program, d).ok())
            .map(|c| c.bound);
        let gap = report
            .as_ref()
            .filter(|v| v.feasible)
            .and(self.primal.as_ref())
            .and_then(|p| bound.and_then(|b| assess_gap(&program, p, b, self.options.tolerances)))
            .map(|g| g.upper);
        // Private transient neutral record only reuses the existing assessment policy;
        // it is never emitted or registered as a runtime backend.
        let record = SolveRecord {
            schema_version: 2,
            model_id: model.document().model_id.clone(),
            backend: "external-study-witness".into(),
            backend_version: self.copt_version.clone(),
            termination,
            native_status: None,
            objective: report.as_ref().filter(|v| v.feasible).map(|v| v.objective),
            best_bound: bound,
            gap,
            candidate,
            validation: report,
            warnings: vec![],
            elapsed_ms: 0,
            options: self.options.clone(),
            lp_settings: None,
            lp_execution: None,
            lp_precision: None,
            lp_adaptive: None,
        };
        let mut d = LpDiagnostics::new(true, false);
        d.dual = self.dual.clone();
        let mut result = crate::lp::assess(&model, &record, &d)?;
        if self.requested_backend == "copt-gpu-pdlp" && !self.gpu_confirmed {
            result.classification = "unsupported".into();
            result.reason = Some("requested GPU PDLP execution was not confirmed".into());
        }
        if self
            .iterations
            .zip(self.options.iteration_limit)
            .is_some_and(|(n, limit)| n > limit)
        {
            result.classification = "work_limit".into();
            result.reason =
                Some("external native PDLP iteration count exceeds requested allowance".into());
        }
        Ok(result)
    }
}
impl ExternalEndpoint {
    /// Parse strict evidence before independent verification.
    pub fn from_json(bytes: &[u8]) -> Result<Self, ValidationError> {
        crate::lp::unique_json(bytes)?;
        serde_json::from_slice(bytes).map_err(|_| invalid("malformed external endpoint"))
    }

    /// Construct only after original-model assessment.
    pub fn new(witness: ExternalWitness, bytes: &[u8]) -> Result<Self, ValidationError> {
        let assessment = witness.assess(bytes)?;
        let payload_sha256 = crate::sha256::hex(
            &serde_json::to_vec(&witness).map_err(|_| invalid("external serialization"))?,
        );
        Ok(Self {
            schema_version: 1,
            witness,
            assessment,
            payload_sha256,
        })
    }
    /// Recompute all mathematical conclusions and witness integrity.
    pub fn verify(&self, bytes: &[u8]) -> Result<(), ValidationError> {
        if *self != Self::new(self.witness.clone(), bytes)? {
            return Err(invalid("external endpoint assessment/hash differs"));
        }
        Ok(())
    }
}
