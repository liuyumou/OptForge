//! Independently replayable LP endpoints under SPEC-0013. No device dependency.
use crate::serde_strict::deserialize_object;
use optimizer_core::{ErrorKind, LpDiagnostics, Model, SolveRecord, Termination, ValidationError};
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
    /// Must be one.
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
}
deserialize_object!(LpEndpoint { schema_version: u32, model_sha256: String,
    requested_backend: String, record: SolveRecord, row_ids: Vec<u32>,
    diagnostics: LpDiagnostics, assessment: Assessment, fallback_reason: Option<String>,
    payload_sha256: String });

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
        let bytes = serde_json::to_vec(&(
            &self.requested_backend,
            &self.record,
            &self.row_ids,
            &self.diagnostics,
            &self.fallback_reason,
        ))
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
        let mut endpoint = Self {
            schema_version: 1,
            model_sha256: crate::sha256::hex(model_bytes),
            requested_backend,
            record,
            row_ids: model.document().constraints.iter().map(|r| r.id).collect(),
            diagnostics,
            assessment,
            fallback_reason,
            payload_sha256: String::new(),
        };
        endpoint.payload_sha256 = endpoint.payload_hash()?;
        Ok(endpoint)
    }

    /// Check original input identity, payload integrity and the recomputed endpoint.
    ///
    /// # Errors
    /// Rejects altered or inconsistent evidence, without trusting its status label.
    pub fn verify(&self, model_bytes: &[u8]) -> Result<(), ValidationError> {
        if self.schema_version != 1
            || self.model_sha256 != crate::sha256::hex(model_bytes)
            || self.payload_sha256 != self.payload_hash()?
        {
            return Err(invalid("endpoint version/hash differs"));
        }
        if !["highs", "host-lp", "cuda-lp"].contains(&self.requested_backend.as_str())
            || !["highs", "host-lp", "cuda-lp"].contains(&self.record.backend.as_str())
            || !self.diagnostics.enabled
        {
            return Err(invalid("invalid observation/backend identity"));
        }
        let fallback = self.requested_backend != self.record.backend;
        if fallback != self.fallback_reason.is_some()
            || (fallback && (self.requested_backend != "cuda-lp" || self.record.backend != "highs"))
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

    /// Parse an object-form versioned sidecar. Verification is a separate required step.
    ///
    /// # Errors
    /// Returns malformed JSON, unknown field or unsupported version errors.
    pub fn from_json(bytes: &[u8]) -> Result<Self, ValidationError> {
        unique_json(bytes)?;
        let shape: serde_json::Value =
            serde_json::from_slice(bytes).map_err(|e| invalid(e.to_string()))?;
        for (object, fields) in [
            (
                &shape,
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
        let result: Self = serde_json::from_slice(bytes).map_err(|e| invalid(e.to_string()))?;
        if result.schema_version != 1 {
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
