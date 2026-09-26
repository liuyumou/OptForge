//! Explicit COPT method/counter study evidence; legacy v1 stays unchanged.
use crate::serde_strict::deserialize_required_object;
use optimizer_core::{ErrorKind, SolveOptions, ValidationError};
use serde::Serialize;
use std::collections::BTreeMap;
fn invalid(s: &str) -> ValidationError {
    ValidationError::new(ErrorKind::Document, s)
}
/// Native reports, with no mathematical authority.
#[derive(Clone, Debug, PartialEq, Serialize)]
pub struct NativeObservations {
    /// Native simplex count.
    pub simplex_iterations: u64,
    /// Native barrier count.
    pub barrier_iterations: u64,
    /// Native PDLP count.
    pub pdlp_iterations: u64,
    /// Native SolvingTime, seconds.
    pub solving_seconds: f64,
    /// Native MemPeak, MB; not process-tree RSS.
    pub peak_memory_mb: f64,
}
deserialize_required_object!(NativeObservations {
    simplex_iterations: u64,
    barrier_iterations: u64,
    pdlp_iterations: u64,
    solving_seconds: f64,
    peak_memory_mb: f64
});
/// Untrusted external solver output bound to original model bytes.
#[derive(Clone, Debug, PartialEq, Serialize)]
pub struct ExternalWitnessV2 {
    /// Two; explicit method and native observations.
    pub schema_version: u32,
    /// Original model byte hash.
    pub model_sha256: String,
    /// Requested COPT default CPU LP, CPU PDLP, or GPU PDLP.
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
    /// Sum of native simplex, barrier, and PDLP iterations, when available.
    pub iterations: Option<u64>,
    /// Native observations, absent when execution did not return them.
    pub native: Option<NativeObservations>,
    /// Explicit unsupported controls and execution limitations.
    pub limitations: Vec<String>,
}
deserialize_required_object!(ExternalWitnessV2 {schema_version:u32,model_sha256:String,requested_backend:String,executed_backend:Option<String>,options:SolveOptions,
 copt_version:String,parameters:BTreeMap<String,f64>,library_sha256:String,binding_sha256:String,gpu_confirmed:bool,row_ids:Vec<u32>,variable_ids:Vec<u32>,
 primal:Option<Vec<f64>>,dual:Option<Vec<f64>>,status:String,iterations:Option<u64>,native:Option<NativeObservations>,limitations:Vec<String>});
impl ExternalWitnessV2 {
    /// Parse strict v2 fields and reject duplicate keys.
    pub fn from_json(bytes: &[u8]) -> Result<Self, ValidationError> {
        crate::lp::unique_json(bytes)?;
        serde_json::from_slice(bytes).map_err(|_| invalid("malformed external v2 witness"))
    }
    /// Check method/work identity and assess the original model independently.
    pub fn assess(&self, bytes: &[u8]) -> Result<crate::lp::Assessment, ValidationError> {
        let _cost = optimizer_core::lp_cost::scope("external_assessment");
        self.options.validate()?;
        let methods = ["copt-cpu-default", "copt-cpu-pdlp", "copt-gpu-pdlp"];
        if self.schema_version != 2
            || !methods.contains(&self.requested_backend.as_str())
            || self
                .executed_backend
                .as_ref()
                .is_some_and(|v| !methods.contains(&v.as_str()))
            || self.executed_backend.as_ref().is_some_and(|v| {
                v != &self.requested_backend
                    && !(self.requested_backend == "copt-gpu-pdlp" && v == "copt-cpu-pdlp")
            })
        {
            return Err(invalid("external v2 method identity differs"));
        }
        let default = self.requested_backend == "copt-cpu-default";
        let gpu = self.requested_backend == "copt-gpu-pdlp";
        let mut expected = BTreeMap::from([
            ("LpMethod".into(), if default { -1.0 } else { 6.0 }),
            ("GPUMode".into(), if gpu { 1.0 } else { 0.0 }),
            ("GPUDevice".into(), 0.0),
            ("Threads".into(), 1.0),
            ("Crossover".into(), if default { 1.0 } else { 0.0 }),
            (
                "TimeLimit".into(),
                self.options
                    .time_limit_ms
                    .ok_or_else(|| invalid("external wall limit required"))? as f64
                    / 1000.0,
            ),
            ("FeasTol".into(), self.options.tolerances.absolute),
            ("DualTol".into(), self.options.tolerances.absolute),
        ]);
        if !default {
            expected.insert("PDLPTol".into(), self.options.tolerances.absolute);
        }
        if self.parameters != expected {
            return Err(invalid("external v2 parameters differ"));
        }
        let total = self
            .native
            .as_ref()
            .map(|n| {
                if !n.solving_seconds.is_finite()
                    || n.solving_seconds < 0.0
                    || !n.peak_memory_mb.is_finite()
                    || n.peak_memory_mb < 0.0
                {
                    return Err(invalid("invalid native observations"));
                }
                n.simplex_iterations
                    .checked_add(n.barrier_iterations)
                    .and_then(|v| v.checked_add(n.pdlp_iterations))
                    .ok_or_else(|| invalid("native count overflow"))
            })
            .transpose()?;
        if total != self.iterations || (self.status == "optimal" && total.is_none()) {
            return Err(invalid("native count observations differ"));
        }
        // Reuse the legacy mathematical assessor through a private neutral
        // proxy, after validating the actual v2 method and parameters above.
        // The proxy is never emitted and changes no vector, outcome or identity hash.
        let normalize = |name: &str| {
            if name == "copt-cpu-default" {
                "copt-cpu-pdlp".into()
            } else {
                name.to_owned()
            }
        };
        expected.insert("LpMethod".into(), 6.0);
        expected.insert("Crossover".into(), 0.0);
        expected.insert("PDLPTol".into(), self.options.tolerances.absolute);
        let proxy = crate::lp_external::ExternalWitness {
            schema_version: 1,
            model_sha256: self.model_sha256.clone(),
            requested_backend: normalize(&self.requested_backend),
            executed_backend: self.executed_backend.as_deref().map(normalize),
            options: self.options.clone(),
            copt_version: self.copt_version.clone(),
            parameters: expected,
            library_sha256: self.library_sha256.clone(),
            binding_sha256: self.binding_sha256.clone(),
            gpu_confirmed: self.gpu_confirmed,
            row_ids: self.row_ids.clone(),
            variable_ids: self.variable_ids.clone(),
            primal: self.primal.clone(),
            dual: self.dual.clone(),
            status: self.status.clone(),
            iterations: self.iterations,
            limitations: self.limitations.clone(),
        };
        let mut result = proxy.assess(bytes)?;
        if total
            .zip(self.options.iteration_limit)
            .is_some_and(|(n, cap)| n > cap)
        {
            result.classification = "work_limit".into();
            result.reason = Some("aggregate native iterations exceed the study allowance; units differ from project updates".into());
        }
        Ok(result)
    }
}
/// Independently assessed external-v2 endpoint.
#[derive(Clone, Debug, PartialEq, Serialize)]
pub struct ExternalEndpointV2 {
    /// Two.
    pub schema_version: u32,
    /// Original-unit witness and provenance.
    pub witness: ExternalWitnessV2,
    /// Original-model host assessment.
    pub assessment: crate::lp::Assessment,
    /// Canonical witness hash.
    pub payload_sha256: String,
}
deserialize_required_object!(ExternalEndpointV2 {
    schema_version: u32,
    witness: ExternalWitnessV2,
    assessment: crate::lp::Assessment,
    payload_sha256: String
});
impl ExternalEndpointV2 {
    /// Parse strict endpoint data.
    pub fn from_json(bytes: &[u8]) -> Result<Self, ValidationError> {
        crate::lp::unique_json(bytes)?;
        serde_json::from_slice(bytes).map_err(|_| invalid("malformed external v2 endpoint"))
    }
    /// Construct a fresh original-model assessment and witness hash.
    pub fn new(witness: ExternalWitnessV2, bytes: &[u8]) -> Result<Self, ValidationError> {
        let assessment = witness.assess(bytes)?;
        let payload_sha256 = crate::sha256::hex(
            &serde_json::to_vec(&witness).map_err(|_| invalid("external serialization"))?,
        );
        Ok(Self {
            schema_version: 2,
            witness,
            assessment,
            payload_sha256,
        })
    }
    /// Recompute the entire assessment and payload identity.
    pub fn verify(&self, bytes: &[u8]) -> Result<(), ValidationError> {
        if *self != Self::new(self.witness.clone(), bytes)? {
            return Err(invalid("external v2 assessment/hash differs"));
        }
        Ok(())
    }
}
