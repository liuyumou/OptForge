//! Independently replayable LP endpoints under SPEC-0013. No device dependency.
use crate::serde_strict::deserialize_object;
use optimizer_core::{
    ErrorKind, LpControlDiagnostics, LpDiagnostics, Model, SolveRecord, Termination,
    ValidationError,
};
use optimizer_lp::{LinearProgram, certify, certify::assess_gap};
use serde::Serialize;

/// Fresh original-model and conservative-gap assessment.
#[derive(Clone, Debug, PartialEq, Serialize)]
pub struct Assessment {
    /// Certified success or an explicit unsuccessful endpoint class.
    pub classification: String,
    /// Original model candidate feasibility, if a candidate exists.
    pub feasible: Option<bool>,
    /// Objective recomputed from the original model.
    pub objective: Option<f64>,
    /// Independently certified original-sense bound.
    pub bound: Option<f64>,
    /// Conservative absolute gap upper bound.
    pub gap_upper: Option<f64>,
    /// Whether the recorded tolerances close the conservative gap.
    pub gap_closed: bool,
    /// Outward certification adjustment diagnostic.
    pub allowance: Option<f64>,
    /// Number of repaired multipliers.
    pub repaired: Option<usize>,
    /// Why certification/validation was unavailable.
    pub reason: Option<String>,
}
deserialize_object!(Assessment { classification: String, feasible: Option<bool>,
    objective: Option<f64>, bound: Option<f64>, gap_upper: Option<f64>, gap_closed: bool,
    allowance: Option<f64>, repaired: Option<usize>, reason: Option<String> });

/// Versioned sidecar; the existing solve record retains its original meaning.
#[derive(Clone, Debug, PartialEq, Serialize)]
pub struct LpEndpoint {
    /// One for legacy evidence, two for the opt-in matched path.
    pub schema_version: u32,
    /// SHA-256 of exact input model bytes.
    pub model_sha256: String,
    /// Requested implementation, distinguished from record.backend.
    pub requested_backend: String,
    /// Ordinary solve output, unchanged.
    pub record: SolveRecord,
    /// Canonical row IDs indexing diagnostics.dual.
    pub row_ids: Vec<u32>,
    /// Untrusted witness and optional phase/work observations.
    pub diagnostics: LpDiagnostics,
    /// Independently recomputed endpoint.
    pub assessment: Assessment,
    /// Explicit reason for executing another backend.
    pub fallback_reason: Option<String>,
    /// Integrity of the record, row IDs, observations and fallback identity.
    pub payload_sha256: String,
    /// Matched FP64 state/work observations; absent when unavailable or in v1.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub control: Option<LpControlDiagnostics>,
    /// Requested tuned execution and actual work, including fallback.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub execution: Option<optimizer_core::LpExecutionDiagnostics>,
}
deserialize_object!(LpEndpoint { schema_version: u32, model_sha256: String,
    requested_backend: String, record: SolveRecord, row_ids: Vec<u32>,
    diagnostics: LpDiagnostics, assessment: Assessment, fallback_reason: Option<String>,
    payload_sha256: String, control: Option<LpControlDiagnostics>, execution: Option<optimizer_core::LpExecutionDiagnostics> });

fn invalid(message: impl Into<String>) -> ValidationError {
    ValidationError::new(ErrorKind::Document, message)
}

/// Recompute the endpoint without trusting device/native status, objective or bound.
///
/// # Errors
/// Rejects inconsistent model identity, malformed witnesses and altered objectives.
pub fn assess(
    model: &Model,
    record: &SolveRecord,
    diagnostics: &LpDiagnostics,
) -> Result<Assessment, ValidationError> {
    record.options.validate()?;
    record.to_json()?;
    if record.model_id != model.document().model_id {
        return Err(invalid("record model identity differs"));
    }
    let program = LinearProgram::new(model)?;
    if let Some(dual) = &diagnostics.dual
        && (dual.len() != program.row_count() || dual.iter().any(|v| !v.is_finite()))
    {
        return Err(invalid("invalid canonical dual witness"));
    }
    let mut result = Assessment {
        classification: "missing_candidate".into(),
        feasible: None,
        objective: None,
        bound: None,
        gap_upper: None,
        gap_closed: false,
        allowance: None,
        repaired: None,
        reason: None,
    };
    let certificate = diagnostics
        .dual
        .as_ref()
        .map(|dual| certify(&program, dual));
    match certificate {
        Some(Ok(c)) => {
            result.bound = Some(c.bound);
            result.allowance = Some(c.allowance);
            result.repaired = Some(c.repaired);
        }
        Some(Err(reason)) => result.reason = Some(reason.to_string()),
        None => result.reason = Some("no dual witness supplied".into()),
    }
    if let Some(candidate) = &record.candidate {
        let report = model.evaluate(candidate, record.options.tolerances)?;
        if record
            .objective
            .is_some_and(|value| value != report.objective)
            || record.validation.as_ref().is_some_and(|v| *v != report)
        {
            return Err(invalid(
                "record objective/validation differs from original-model check",
            ));
        }
        result.feasible = Some(report.feasible);
        result.objective = Some(report.objective);
        if record.backend != "highs" && record.best_bound != result.bound {
            return Err(invalid(
                "first-order bound differs from witness certification",
            ));
        }
        let primal: Vec<f64> = candidate.values.iter().map(|a| a.value).collect();
        // Candidate documents need not arrive in canonical order.
        let primal: Vec<f64> = if candidate
            .values
            .iter()
            .map(|a| a.variable_id)
            .eq(program.variable_ids().iter().copied())
        {
            primal
        } else {
            program
                .variable_ids()
                .iter()
                .map(|id| {
                    candidate
                        .values
                        .iter()
                        .find(|a| a.variable_id == *id)
                        .expect("evaluate checked coverage")
                        .value
                })
                .collect()
        };
        if report.feasible
            && let Some(gap) = result
                .bound
                .and_then(|b| assess_gap(&program, &primal, b, record.options.tolerances))
        {
            result.gap_upper = Some(gap.upper);
            result.gap_closed = gap.closed;
        }
        if record.backend != "highs" && record.gap != result.gap_upper {
            return Err(invalid(
                "first-order gap differs from independent assessment",
            ));
        }
        result.classification = if !report.feasible {
            "numerical_rejection"
        } else if result.bound.is_none() {
            "missing_certificate"
        } else if result.gap_closed {
            "certified_success"
        } else {
            "feasible_unclosed"
        }
        .into();
    }
    // An interruption or limit is never retrospectively promoted to successful completion.
    let override_class = match record.termination {
        Termination::Interrupted => Some("interrupted"),
        Termination::TimeLimit => Some("timeout"),
        Termination::IterationLimit | Termination::NodeLimit => Some("work_limit"),
        Termination::Unsupported => Some("unsupported"),
        Termination::BackendFailure => Some("backend_failure"),
        Termination::NumericalFailure => Some("numerical_rejection"),
        Termination::Infeasible | Termination::Unbounded | Termination::UnboundedOrInfeasible => {
            Some("reference_only")
        }
        _ => None,
    };
    if let Some(class) = override_class {
        result.classification = class.into();
    }
    Ok(result)
}

impl LpEndpoint {
    fn payload_hash(&self) -> Result<String, ValidationError> {
        let payload = (
            &self.requested_backend,
            &self.record,
            &self.row_ids,
            &self.diagnostics,
            &self.fallback_reason,
        );
        let bytes = if self.schema_version == 1 {
            serde_json::to_vec(&payload)
        } else if self.schema_version == 3 {
            serde_json::to_vec(&(payload, &self.control, &self.execution))
        } else {
            serde_json::to_vec(&(payload, &self.control))
        }
        .map_err(|e| invalid(e.to_string()))?;
        Ok(crate::sha256::hex(&bytes))
    }

    /// Build a sidecar with a fresh independent endpoint assessment.
    ///
    /// # Errors
    /// Rejects malformed numerical evidence or model data.
    pub fn new(
        model_bytes: &[u8],
        requested_backend: String,
        record: SolveRecord,
        mut diagnostics: LpDiagnostics,
        fallback_reason: Option<String>,
    ) -> Result<Self, ValidationError> {
        let model = Model::from_json(model_bytes)?;
        let check = diagnostics.start();
        let assessment = assess(&model, &record, &diagnostics)?;
        diagnostics.finish("independent_endpoint", check);
        let tuned = requested_backend == "cuda-lp-tuned";
        let matched = requested_backend == "cuda-lp-matched" || tuned;
        let control = if matched {
            diagnostics.control.take()
        } else {
            None
        };
        if matched && control.is_none() {
            diagnostics
                .unavailable
                .push("matched controller state unavailable before completion".into());
        }
        let mut endpoint = Self {
            schema_version: if tuned {
                3
            } else if matched {
                2
            } else {
                1
            },
            execution: if tuned {
                diagnostics.execution.take()
            } else {
                None
            },
            control,
            model_sha256: crate::sha256::hex(model_bytes),
            requested_backend,
            record,
            row_ids: model.document().constraints.iter().map(|r| r.id).collect(),
            diagnostics,
            assessment,
            fallback_reason,
            payload_sha256: String::new(),
        };
        endpoint.verify_control()?;
        endpoint.payload_sha256 = endpoint.payload_hash()?;
        Ok(endpoint)
    }

    /// Check original input identity, payload integrity and the recomputed endpoint.
    ///
    /// # Errors
    /// Rejects altered or inconsistent evidence, without trusting its status label.
    pub fn verify(&self, model_bytes: &[u8]) -> Result<(), ValidationError> {
        if ![1, 2, 3].contains(&self.schema_version)
            || self.model_sha256 != crate::sha256::hex(model_bytes)
            || self.payload_sha256 != self.payload_hash()?
        {
            return Err(invalid("endpoint version/hash differs"));
        }
        let backends = [
            "highs",
            "host-lp",
            "cuda-lp",
            "cuda-lp-matched",
            "cuda-lp-tuned",
        ];
        if !backends.contains(&self.requested_backend.as_str())
            || !backends.contains(&self.record.backend.as_str())
            || (self.schema_version == 1
                && (self.control.is_some()
                    || self.requested_backend == "cuda-lp-matched"
                    || self.record.backend == "cuda-lp-matched"))
            || (self.schema_version == 2 && self.requested_backend != "cuda-lp-matched")
            || (self.schema_version == 3 && self.requested_backend != "cuda-lp-tuned")
            || (self.schema_version < 3
                && (self.execution.is_some()
                    || self.requested_backend == "cuda-lp-tuned"
                    || self.record.backend == "cuda-lp-tuned"))
            || !self.diagnostics.enabled
        {
            return Err(invalid("invalid observation/backend identity"));
        }
        self.verify_control()?;
        let fallback = self.requested_backend != self.record.backend;
        if fallback != self.fallback_reason.is_some()
            || (fallback
                && (!["cuda-lp", "cuda-lp-matched", "cuda-lp-tuned"]
                    .contains(&self.requested_backend.as_str())
                    || self.record.backend != "highs"))
        {
            return Err(invalid("inconsistent fallback identity"));
        }
        let model = Model::from_json(model_bytes)?;
        if self.row_ids
            != model
                .document()
                .constraints
                .iter()
                .map(|r| r.id)
                .collect::<Vec<_>>()
            || self.assessment != assess(&model, &self.record, &self.diagnostics)?
        {
            return Err(invalid("endpoint assessment differs"));
        }
        Ok(())
    }

    fn verify_control(&self) -> Result<(), ValidationError> {
        self.record.check_execution()?;
        if self.schema_version == 3 {
            let e = self
                .execution
                .as_ref()
                .ok_or_else(|| invalid("missing tuned execution"))?;
            e.settings.validate()?;
            if let Some(hash) = &e.code_object_sha256
                && (hash.len() != 64
                    || !hash
                        .bytes()
                        .all(|b| b.is_ascii_digit() || (b'a'..=b'f').contains(&b)))
            {
                return Err(invalid("invalid tuned code identity"));
            }
            if let Some(actual) = &self.record.lp_execution
                && (actual.settings != e.settings
                    || Some(&actual.code_object_sha256) != e.code_object_sha256.as_ref())
            {
                return Err(invalid("tuned requested/executed settings differ"));
            }
            if let Some(c) = &self.control
                && let Some(steps) = c.physical_iterations
            {
                let per_step = if e.settings.fusion == optimizer_core::Fp64Fusion::PrimalDual {
                    2
                } else {
                    6
                };
                if steps.checked_mul(per_step) != Some(e.kernel_launches) {
                    return Err(invalid("tuned completed work/launch count differs"));
                }
            }
            if let Some(c) = &self.control
                && c.device_kernel_launches != e.kernel_launches
            {
                return Err(invalid("tuned launch accounting differs"));
            }
        } else if self.execution.is_some() {
            return Err(invalid("legacy endpoint contains tuned execution"));
        }

        let Some(control) = &self.control else {
            if self.schema_version >= 2
                && ["cuda-lp-matched", "cuda-lp-tuned"].contains(&self.record.backend.as_str())
                && !matches!(
                    self.record.termination,
                    Termination::Unsupported | Termination::BackendFailure
                )
            {
                return Err(invalid("missing matched control evidence"));
            }
            return Ok(());
        };
        if control.controller != "host-restart-weight-v1"
            || !control.weight.is_finite()
            || !(1e-6..=1e6).contains(&control.weight)
            || control
                .physical_iterations
                .is_some_and(|n| n < control.logical_iterations)
            || control.restarts > control.logical_iterations
            || ![
                "accepted",
                "iteration_limit",
                "interrupted",
                "time_limit",
                "device_failure",
            ]
            .contains(&control.stop.as_str())
        {
            return Err(invalid("invalid matched controller observations"));
        }
        if ["cuda-lp-matched", "cuda-lp-tuned"].contains(&self.record.backend.as_str()) {
            let settings = self
                .record
                .lp_settings
                .ok_or_else(|| invalid("missing matched LP settings"))?;
            let expected = match self.record.termination {
                Termination::Optimal => "accepted",
                Termination::Interrupted => "interrupted",
                Termination::TimeLimit => "time_limit",
                Termination::IterationLimit => "iteration_limit",
                Termination::BackendFailure => "device_failure",
                _ => return Err(invalid("inconsistent matched termination")),
            };
            if expected != control.stop
                || control.physical_iterations.is_some_and(|n| {
                    n > settings.iteration_limit
                        || self
                            .record
                            .options
                            .iteration_limit
                            .is_some_and(|limit| n > limit)
                })
                || self.diagnostics.iterations != control.physical_iterations
                || (control.stop != "device_failure"
                    && self.diagnostics.restarts != Some(control.restarts))
                || self
                    .diagnostics
                    .assessment_iteration
                    .is_some_and(|i| i > control.logical_iterations)
                || control.kkt_evaluations == 0
            {
                return Err(invalid("matched work/assessment alignment differs"));
            }
        }
        Ok(())
    }

    /// Parse an object-form versioned sidecar. Verification is a separate required step.
    ///
    /// # Errors
    /// Returns malformed JSON, unknown field or unsupported version errors.
    pub fn from_json(bytes: &[u8]) -> Result<Self, ValidationError> {
        unique_json(bytes)?;
        let shape: serde_json::Value =
            serde_json::from_slice(bytes).map_err(|e| invalid(e.to_string()))?;
        let mut base_shape = shape.clone();
        if matches!(shape["schema_version"].as_u64(), Some(2 | 3))
            && let Some(control) = base_shape
                .as_object_mut()
                .and_then(|map| map.remove("control"))
        {
            let fields = [
                "controller",
                "logical_iterations",
                "physical_iterations",
                "device_kernel_launches",
                "assessments",
                "kkt_evaluations",
                "restarts",
                "weight",
                "stop",
            ];
            let map = control
                .as_object()
                .ok_or_else(|| invalid("control requires an object"))?;
            if map.len() != fields.len() || fields.iter().any(|key| !map.contains_key(*key)) {
                return Err(invalid("missing or unknown control field"));
            }
        }
        if shape["schema_version"] == 3 {
            let execution = base_shape
                .as_object_mut()
                .and_then(|m| m.remove("execution"))
                .ok_or_else(|| invalid("missing tuned execution"))?;
            let fields = [
                "settings",
                "code_object_sha256",
                "allocations",
                "allocated_bytes",
                "upload_calls",
                "upload_bytes",
                "readback_calls",
                "readback_bytes",
                "synchronizations",
                "kernel_launches",
            ];
            let map = execution
                .as_object()
                .ok_or_else(|| invalid("execution requires an object"))?;
            if map.len() != fields.len() || fields.iter().any(|k| !map.contains_key(*k)) {
                return Err(invalid("missing or unknown execution field"));
            }
        }
        for (object, fields) in [
            (
                &base_shape,
                &[
                    "schema_version",
                    "model_sha256",
                    "requested_backend",
                    "record",
                    "row_ids",
                    "diagnostics",
                    "assessment",
                    "fallback_reason",
                    "payload_sha256",
                ][..],
            ),
            (
                &shape["diagnostics"],
                &[
                    "enabled",
                    "profile",
                    "device_buffer_limit_bytes",
                    "dual",
                    "iterations",
                    "assessment_iteration",
                    "restarts",
                    "kernel_launches",
                    "device_buffer_peak_bytes",
                    "phases_ns",
                    "unavailable",
                ][..],
            ),
            (
                &shape["assessment"],
                &[
                    "classification",
                    "feasible",
                    "objective",
                    "bound",
                    "gap_upper",
                    "gap_closed",
                    "allowance",
                    "repaired",
                    "reason",
                ][..],
            ),
        ] {
            let Some(map) = object.as_object() else {
                return Err(invalid("LP evidence requires objects"));
            };
            if map.len() != fields.len() || fields.iter().any(|key| !map.contains_key(*key)) {
                return Err(invalid("missing or unknown LP evidence field"));
            }
        }
        let allowed = [
            "input_preparation",
            "device_context",
            "preparation",
            "preconditioning",
            "invariant_allocation_upload",
            "working_allocation",
            "working_upload",
            "kernels_and_synchronization",
            "readback",
            "iteration",
            "host_checks",
            "solve_record_serialization",
            "native_preparation",
            "native_solve",
            "native_extraction",
            "independent_endpoint",
        ];
        let phases = shape["diagnostics"]["phases_ns"]
            .as_object()
            .ok_or_else(|| invalid("phase measurements require an object"))?;
        if phases.keys().any(|name| {
            !(allowed.contains(&name.as_str())
                || (matches!(shape["schema_version"].as_u64(), Some(2 | 3))
                    && name == "controller"))
        }) {
            return Err(invalid("unknown LP measurement phase"));
        }
        let result: Self = serde_json::from_slice(bytes).map_err(|e| invalid(e.to_string()))?;
        if ![1, 2, 3].contains(&result.schema_version) {
            return Err(invalid("unsupported endpoint version"));
        }
        Ok(result)
    }
}

fn unique_json(bytes: &[u8]) -> Result<(), ValidationError> {
    struct Unique;
    impl<'de> serde::Deserialize<'de> for Unique {
        fn deserialize<D: serde::Deserializer<'de>>(deserializer: D) -> Result<Self, D::Error> {
            struct Visitor;
            impl<'de> serde::de::Visitor<'de> for Visitor {
                type Value = Unique;
                fn expecting(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
                    f.write_str("finite JSON with unique keys")
                }
                fn visit_bool<E: serde::de::Error>(self, _: bool) -> Result<Unique, E> {
                    Ok(Unique)
                }
                fn visit_i64<E: serde::de::Error>(self, _: i64) -> Result<Unique, E> {
                    Ok(Unique)
                }
                fn visit_u64<E: serde::de::Error>(self, _: u64) -> Result<Unique, E> {
                    Ok(Unique)
                }
                fn visit_f64<E: serde::de::Error>(self, v: f64) -> Result<Unique, E> {
                    if v.is_finite() {
                        Ok(Unique)
                    } else {
                        Err(E::custom("nonfinite JSON"))
                    }
                }
                fn visit_str<E: serde::de::Error>(self, _: &str) -> Result<Unique, E> {
                    Ok(Unique)
                }
                fn visit_unit<E: serde::de::Error>(self) -> Result<Unique, E> {
                    Ok(Unique)
                }
                fn visit_seq<A: serde::de::SeqAccess<'de>>(
                    self,
                    mut seq: A,
                ) -> Result<Unique, A::Error> {
                    while seq.next_element::<Unique>()?.is_some() {}
                    Ok(Unique)
                }
                fn visit_map<A: serde::de::MapAccess<'de>>(
                    self,
                    mut map: A,
                ) -> Result<Unique, A::Error> {
                    let mut seen = std::collections::BTreeSet::new();
                    while let Some(key) = map.next_key::<String>()? {
                        if !seen.insert(key) {
                            return Err(serde::de::Error::custom("duplicate JSON key"));
                        }
                        map.next_value::<Unique>()?;
                    }
                    Ok(Unique)
                }
            }
            deserializer.deserialize_any(Visitor)
        }
    }
    let _: Unique = serde_json::from_slice(bytes).map_err(|e| invalid(e.to_string()))?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use optimizer_core::{CancellationToken, LpSettings, SolveOptions};
    use optimizer_lp::HostLpBackend;

    const MODEL: &[u8] = include_bytes!("../../../examples/lp-model-v1.json");
    fn observed() -> LpEndpoint {
        let model = Model::from_json(MODEL).unwrap();
        let options: SolveOptions =
            serde_json::from_slice(include_bytes!("../../../examples/solve-config-v1.json"))
                .unwrap();
        let backend = HostLpBackend::new(LpSettings::published(3, 2)).unwrap();
        let mut diagnostics = LpDiagnostics::new(true, true);
        let record = backend
            .solve_with_diagnostics(
                &model,
                &options,
                &CancellationToken::new(),
                None,
                &mut diagnostics,
            )
            .unwrap();
        LpEndpoint::new(MODEL, "host-lp".into(), record, diagnostics, None).unwrap()
    }

    fn matched_observed() -> LpEndpoint {
        let mut endpoint = observed();
        endpoint.schema_version = 2;
        endpoint.requested_backend = "cuda-lp-matched".into();
        endpoint.record.backend = "cuda-lp-matched".into();
        endpoint
            .diagnostics
            .phases_ns
            .insert("controller".into(), 7);
        endpoint.control = Some(LpControlDiagnostics {
            controller: "host-restart-weight-v1".into(),
            logical_iterations: 3,
            physical_iterations: Some(3),
            device_kernel_launches: 18,
            assessments: 2,
            kkt_evaluations: 3,
            restarts: endpoint.diagnostics.restarts.unwrap(),
            weight: 1.0,
            stop: "iteration_limit".into(),
        });
        endpoint.payload_sha256 = endpoint.payload_hash().unwrap();
        endpoint
    }

    fn tuned_observed() -> LpEndpoint {
        let mut e = matched_observed();
        let settings = optimizer_core::Fp64ExecutionSettings::from_json(include_bytes!(
            "../../../examples/lp-execution-v1.json"
        ))
        .unwrap();
        let mut execution = optimizer_core::LpExecutionDiagnostics::new(settings);
        execution.code_object_sha256 = Some("a".repeat(64));
        execution.kernel_launches = 6;
        e.control.as_mut().unwrap().device_kernel_launches = 6;
        e.schema_version = 3;
        e.requested_backend = "cuda-lp-tuned".into();
        e.record.backend = "cuda-lp-tuned".into();
        e.record.schema_version = 3;
        e.record.lp_execution = Some(optimizer_core::LpExecutionRecord {
            settings,
            code_object_sha256: "a".repeat(64),
        });
        e.execution = Some(execution);
        e.payload_sha256 = e.payload_hash().unwrap();
        e
    }

    #[test]
    fn tuned_records_and_endpoints_are_versioned_and_strict() {
        let e = tuned_observed();
        e.verify(MODEL).unwrap();
        let json = serde_json::to_vec(&e).unwrap();
        let copy = LpEndpoint::from_json(&json).unwrap();
        copy.verify(MODEL).unwrap();
        assert_eq!(e, copy);
        let record = SolveRecord::from_json(e.record.to_json().unwrap().as_bytes()).unwrap();
        assert_eq!(record, e.record);
        for key in ["execution", "control"] {
            let mut value = serde_json::to_value(&e).unwrap();
            value.as_object_mut().unwrap().remove(key);
            assert!(
                LpEndpoint::from_json(&serde_json::to_vec(&value).unwrap())
                    .and_then(|e| e.verify(MODEL))
                    .is_err()
            );
        }
        for mutation in 0..8 {
            let mut wrong = e.clone();
            match mutation {
                0 => wrong.schema_version = 2,
                1 => wrong.record.schema_version = 2,
                2 => {
                    wrong.execution.as_mut().unwrap().settings.reduction =
                        optimizer_core::Fp64Reduction::Legacy1024
                }
                3 => wrong.execution.as_mut().unwrap().code_object_sha256 = Some("b".repeat(64)),
                4 => wrong.execution.as_mut().unwrap().kernel_launches += 1,
                5 => wrong.record.lp_execution = None,
                6 => {
                    wrong
                        .record
                        .lp_execution
                        .as_mut()
                        .unwrap()
                        .settings
                        .schema_version = 2
                }
                _ => wrong.record.backend = "host-lp".into(),
            }
            wrong.payload_sha256 = wrong.payload_hash().unwrap();
            assert!(wrong.verify(MODEL).is_err(), "mutation {mutation}");
        }
        let legacy = observed();
        let mut bad_record = serde_json::to_value(&legacy.record).unwrap();
        bad_record["lp_execution"] = serde_json::Value::Null;
        assert!(SolveRecord::from_json(&serde_json::to_vec(&bad_record).unwrap()).is_err());
        let value = serde_json::to_value(&legacy).unwrap();
        assert!(value.get("execution").is_none());
        assert!(value["record"].get("lp_execution").is_none());
    }

    #[test]
    fn tuned_fault_fallback_retains_requested_execution_and_unknown_work() {
        let mut endpoint = tuned_observed();
        endpoint.record.schema_version = 2;
        endpoint.record.backend = "highs".into();
        endpoint.record.lp_execution = None;
        endpoint.fallback_reason = Some("injected sticky device failure after submission".into());
        endpoint.control.as_mut().unwrap().physical_iterations = None;
        endpoint.control.as_mut().unwrap().stop = "device_failure".into();
        endpoint.diagnostics.iterations = None;
        endpoint.assessment = assess(
            &Model::from_json(MODEL).unwrap(),
            &endpoint.record,
            &endpoint.diagnostics,
        )
        .unwrap();
        endpoint.payload_sha256 = endpoint.payload_hash().unwrap();
        endpoint.verify(MODEL).unwrap();
        let copy = LpEndpoint::from_json(&serde_json::to_vec(&endpoint).unwrap()).unwrap();
        copy.verify(MODEL).unwrap();
        assert_eq!(copy.execution, endpoint.execution);
        assert_eq!(copy.control.as_ref().unwrap().physical_iterations, None);
        assert!(copy.execution.as_ref().unwrap().kernel_launches > 0);
        let mut erased = copy;
        erased.execution.as_mut().unwrap().kernel_launches = 0;
        erased.payload_sha256 = erased.payload_hash().unwrap();
        assert!(erased.verify(MODEL).is_err());
    }

    #[test]
    fn matched_evidence_roundtrips_without_changing_legacy_shape() {
        let legacy = observed();
        assert!(
            !serde_json::to_value(&legacy)
                .unwrap()
                .as_object()
                .unwrap()
                .contains_key("control")
        );
        let endpoint = matched_observed();
        endpoint.verify(MODEL).unwrap();
        let bytes = serde_json::to_vec(&endpoint).unwrap();
        let restored = LpEndpoint::from_json(&bytes).unwrap();
        assert_eq!(restored, endpoint);
        restored.verify(MODEL).unwrap();
    }

    #[test]
    fn matched_corruption_fails_even_with_a_recomputed_payload_hash() {
        for change in 0..10 {
            let mut endpoint = matched_observed();
            match change {
                0 => endpoint.control.as_mut().unwrap().physical_iterations = Some(2),
                1 => endpoint.control.as_mut().unwrap().stop = "accepted".into(),
                2 => endpoint.control = None,
                3 => endpoint.diagnostics.assessment_iteration = Some(4),
                4 => endpoint.record.objective = Some(100.0),
                5 => endpoint.diagnostics.dual = Some(vec![]),
                6 => endpoint.record.termination = Termination::Optimal,
                7 => endpoint.record.candidate.as_mut().unwrap().values[0].value = 100.0,
                8 => endpoint.record.best_bound = Some(1e30),
                _ => endpoint.control.as_mut().unwrap().weight = 0.0,
            }
            endpoint.payload_sha256 = endpoint.payload_hash().unwrap();
            assert!(endpoint.verify(MODEL).is_err(), "change {change}");
        }
        let mut value = serde_json::to_value(matched_observed()).unwrap();
        value["control"]["unknown"] = true.into();
        assert!(LpEndpoint::from_json(&serde_json::to_vec(&value).unwrap()).is_err());
        value["control"] = serde_json::json!([]);
        assert!(LpEndpoint::from_json(&serde_json::to_vec(&value).unwrap()).is_err());
    }

    #[test]
    fn a_limit_between_checks_retains_the_assessed_witness() {
        let endpoint = observed();
        assert_eq!(endpoint.diagnostics.iterations, Some(3));
        assert_eq!(endpoint.diagnostics.assessment_iteration, Some(2));
        endpoint.verify(MODEL).unwrap();
        let roundtrip = LpEndpoint::from_json(&serde_json::to_vec(&endpoint).unwrap()).unwrap();
        roundtrip.verify(MODEL).unwrap();
    }

    #[test]
    fn changed_claims_and_witnesses_are_rejected() {
        let original = observed();
        for change in 0..7 {
            let mut endpoint = original.clone();
            match change {
                0 => endpoint.assessment.bound = Some(1e30),
                1 => endpoint.assessment.classification = "certified_success".into(),
                2 => endpoint.record.objective = Some(100.0),
                3 => endpoint.record.candidate.as_mut().unwrap().values[0].value = 100.0,
                4 => endpoint.diagnostics.dual = Some(vec![]),
                5 => endpoint.record.termination = Termination::Optimal,
                _ => endpoint.row_ids[0] += 1,
            }
            assert!(endpoint.verify(MODEL).is_err(), "change {change}");
        }
    }

    #[test]
    fn malformed_duals_are_refused_before_the_certifier_assertion() {
        let endpoint = observed();
        let model = Model::from_json(MODEL).unwrap();
        let mut diagnostics = endpoint.diagnostics;
        diagnostics.dual = Some(vec![f64::NAN]);
        assert!(assess(&model, &endpoint.record, &diagnostics).is_err());
        diagnostics.dual = Some(vec![]);
        assert!(assess(&model, &endpoint.record, &diagnostics).is_err());
    }

    #[test]
    fn observation_does_not_change_the_numerical_solve() {
        use optimizer_core::Backend;
        let model = Model::from_json(MODEL).unwrap();
        let options = observed().record.options;
        let backend = HostLpBackend::new(LpSettings::published(3, 2)).unwrap();
        let mut ordinary = backend
            .solve(&model, &options, &CancellationToken::new(), None)
            .unwrap();
        let mut observed = observed().record;
        ordinary.elapsed_ms = 0;
        observed.elapsed_ms = 0;
        assert_eq!(ordinary, observed);
    }
}
