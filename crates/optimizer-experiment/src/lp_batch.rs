//! Repeated-solve batch documents under SPEC-0014. No device dependency.
//!
//! A batch request fixes one ordered sequence of solves over one fixed matrix:
//! either `solves` identical repeats of the base model, or one materialized
//! variable-bounds variant per solve. [`materialize`] is the single
//! deterministic pure function (requirement 16) that turns (base model,
//! request, solve index) into the complete variant model bytes that are
//! solved and hashed — it, not the change description, is the evidence
//! identity.
//!
//! [`BatchEndpoint`] is the lp-batch-endpoint-v1 record: the batch and base
//! model hashes, the one-time session setup phases, one [`SolveSummary`] per
//! solve carrying the per-solve session phases, and a payload hash binding
//! the request hash, the base model hash and every per-solve record hash and
//! status in solve order (requirement 26). Verification re-materializes every
//! variant and re-verifies every per-solve lp-endpoint record against it
//! (requirement 17), so the retained directory alone decides bitwise
//! identity.
use crate::serde_strict::deserialize_required_object;
use optimizer_core::{Bound, ErrorKind, Model, SessionSetup, ValidationError};
use serde::Serialize;
use std::collections::BTreeMap;
use std::path::Path;

fn invalid(message: impl Into<String>) -> ValidationError {
    ValidationError::new(ErrorKind::Document, message)
}

fn hash_ok(hex: &str) -> bool {
    hex.len() == 64
        && hex
            .bytes()
            .all(|b| b.is_ascii_digit() || (b'a'..=b'f').contains(&b))
}

/// The marker a per-solve hash field carries when the solve has no record:
/// the literal `-`, never a valid SHA-256 hex string. Used for solves whose
/// batch status is `not_attempted` or `failed` (requirement 27).
pub const NO_RECORD: &str = "-";

/// Batch-level statuses that never correspond to a per-solve record file.
const NO_RECORD_STATUSES: [&str; 2] = ["not_attempted", "failed"];

/// The one-time setup phase vocabulary of a batch record (requirement 24).
/// These names are deliberately absent from the lp-endpoint phase allow-list;
/// per-solve endpoint records keep their existing phase vocabulary.
pub(crate) const SETUP_PHASES: [&str; 5] = [
    "device_context",
    "module_load",
    "preconditioning",
    "research_preparation",
    "invariant_allocation_upload",
];

/// The per-solve session phase vocabulary of a batch record (requirement 24).
pub(crate) const SOLVE_PHASES: [&str; 3] = ["variant_rebind", "engine_rebind", "bound_upload"];

pub(crate) fn check_phases(
    phases: &BTreeMap<String, u64>,
    allowed: &[&str],
) -> Result<(), ValidationError> {
    if phases.keys().any(|name| !allowed.contains(&name.as_str())) {
        return Err(invalid("unknown batch session phase"));
    }
    Ok(())
}

/// The per-solve record file name: `solve-NNN.json` with the zero-padded
/// solve index (requirement 23).
pub(crate) fn solve_file_name(index: u32) -> String {
    format!("solve-{index:03}.json")
}

/// The batch payload hash (requirement 26): SHA-256 over the byte
/// concatenation of
///
/// ```text
/// <request hash>\n<base model hash>\n
/// ```
///
/// followed by one line per solve, in solve order:
///
/// ```text
/// <record hash> <status>\n
/// ```
///
/// where `<record hash>` is the 64-lowercase-hex SHA-256 of the per-solve
/// record file bytes, or the literal [`NO_RECORD`] marker for a solve without
/// a record. Hashes are lowercase hex and statuses contain no whitespace, so
/// the layout is unambiguous.
pub(crate) fn payload_hash<'a>(
    request_sha256: &str,
    model_sha256: &str,
    solves: impl Iterator<Item = (&'a str, &'a str)>,
) -> String {
    let mut payload = String::new();
    payload.push_str(request_sha256);
    payload.push('\n');
    payload.push_str(model_sha256);
    payload.push('\n');
    for (record_sha256, status) in solves {
        payload.push_str(record_sha256);
        payload.push(' ');
        payload.push_str(status);
        payload.push('\n');
    }
    crate::sha256::hex(payload.as_bytes())
}

/// Write one evidence file: `create_new` into a temporary sibling name, then
/// rename into place (requirement 25). An existing final record is never
/// replaced; a stale temporary from an interrupted write refuses the write
/// rather than being adopted.
///
/// # Errors
/// Returns a document failure when the destination exists or the filesystem
/// refuses the write or rename.
pub fn write_evidence_file(destination: &Path, bytes: &[u8]) -> Result<(), ValidationError> {
    use std::io::Write;
    let io = |e: std::io::Error| invalid(format!("evidence write: {e}"));
    if destination.symlink_metadata().is_ok() {
        return Err(invalid("evidence record already exists"));
    }
    let partial = destination.with_extension("partial");
    let mut file = std::fs::OpenOptions::new()
        .create_new(true)
        .write(true)
        .open(&partial)
        .map_err(io)?;
    file.write_all(bytes).map_err(io)?;
    file.sync_all().map_err(io)?;
    drop(file);
    std::fs::rename(&partial, destination).map_err(io)?;
    Ok(())
}

/// The kind of a batch: identical repeats of the base model, or one
/// bounds-only variant per solve.
#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, serde::Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum BatchKind {
    /// Every solve uses the base model unchanged.
    Repeat,
    /// Solve k uses the materialized variant with index k.
    Variant,
}

/// The recorded variant generator identity: the seed band and the number of
/// variables the generator was asked to change. The variant list, not this
/// record, is what a solve materializes; the generator identity exists so the
/// protocol's generator can be replayed independently (requirements 19-20).
#[derive(Clone, Copy, Debug, PartialEq, Serialize)]
pub struct Generator {
    /// The SHA-256 counter PRNG seed band for this batch.
    pub seed: u64,
    /// Variables changed per variant: min(n, 256) for the protocol generator.
    pub changes: u32,
}
deserialize_required_object!(Generator {
    seed: u64,
    changes: u32
});

/// One changed variable bound pair. Both bounds are finite by construction
/// (the strict parser rejects non-finite JSON numbers and
/// [`BatchRequest::validate`] rejects non-finite or inverted pairs).
#[derive(Clone, Copy, Debug, PartialEq, Serialize)]
pub struct BoundChange {
    /// The original variable identity the change names.
    pub variable_id: u32,
    /// Replacement finite lower bound.
    pub lower: f64,
    /// Replacement finite upper bound.
    pub upper: f64,
}
deserialize_required_object!(BoundChange {
    variable_id: u32,
    lower: f64,
    upper: f64
});

/// One solve's bound changes; `index` is the solve index within the batch.
#[derive(Clone, Debug, PartialEq, Serialize)]
pub struct Variant {
    /// Solve index; the variants of a valid request are ordered 0..solves-1.
    pub index: u32,
    /// Changed variable bounds; at least one, with no repeated variable.
    pub changes: Vec<BoundChange>,
}
deserialize_required_object!(Variant {
    index: u32,
    changes: Vec<BoundChange>
});

/// An lp-batch-request-v1 document: one ordered batch of solves over one
/// fixed matrix (requirement 22).
///
/// Every field is required-present, so `generator` is explicitly `null` for a
/// repeat batch and `variants` is explicitly empty; a variant batch requires
/// the generator record.
#[derive(Clone, Debug, PartialEq, Serialize)]
pub struct BatchRequest {
    /// Must be 1.
    pub schema_version: u32,
    /// Repeat or variant batch.
    pub kind: BatchKind,
    /// The number of solves in the batch; at least one.
    pub solves: u32,
    /// The variant list; empty for a repeat batch, exactly `solves` ordered
    /// entries for a variant batch.
    pub variants: Vec<Variant>,
    /// The generator identity; present exactly for a variant batch.
    pub generator: Option<Generator>,
    /// Whole-batch wall time limit in milliseconds, observed between solves.
    pub batch_time_limit_ms: u64,
}
deserialize_required_object!(BatchRequest {
    schema_version: u32,
    kind: BatchKind,
    solves: u32,
    variants: Vec<Variant>,
    generator: Option<Generator>,
    batch_time_limit_ms: u64
});

impl BatchRequest {
    /// Parse a strict lp-batch-request-v1 document and validate it.
    ///
    /// # Errors
    /// Returns malformed JSON, duplicate keys, unknown fields, a non-object
    /// shape or a validation failure.
    pub fn from_json(bytes: &[u8]) -> Result<Self, ValidationError> {
        crate::lp::unique_json(bytes)?;
        let request: Self = serde_json::from_slice(bytes).map_err(|e| invalid(e.to_string()))?;
        request.validate()?;
        Ok(request)
    }

    /// The structural invariants of a batch request: version, kind/variants
    /// consistency, ordered indices, nonempty finite non-inverted changes
    /// with no repeated variable, and a nonzero batch limit.
    ///
    /// # Errors
    /// Returns a document failure naming the violated invariant.
    pub fn validate(&self) -> Result<(), ValidationError> {
        if self.schema_version != 1 || self.solves == 0 || self.batch_time_limit_ms == 0 {
            return Err(invalid("batch request version/limits"));
        }
        match self.kind {
            BatchKind::Repeat => {
                if !self.variants.is_empty() || self.generator.is_some() {
                    return Err(invalid("a repeat batch carries no variants or generator"));
                }
            }
            BatchKind::Variant => {
                let generator = self
                    .generator
                    .ok_or_else(|| invalid("a variant batch requires its generator record"))?;
                if generator.changes == 0
                    || self.variants.len() != self.solves as usize
                    || self
                        .variants
                        .iter()
                        .enumerate()
                        .any(|(position, variant)| variant.index != position as u32)
                {
                    return Err(invalid("variant batch count/order"));
                }
                for variant in &self.variants {
                    let mut seen = std::collections::BTreeSet::new();
                    if variant.changes.is_empty()
                        || variant.changes.iter().any(|change| {
                            !change.lower.is_finite()
                                || !change.upper.is_finite()
                                || change.lower > change.upper
                                || !seen.insert(change.variable_id)
                        })
                    {
                        return Err(invalid("invalid variant bound change"));
                    }
                }
            }
        }
        Ok(())
    }

    /// Canonical request bytes: the struct's own serialization, pretty
    /// printed exactly as [`Model::to_json`] prints model documents.
    ///
    /// # Errors
    /// Returns a document failure if serialization fails.
    pub fn to_json(&self) -> Result<String, ValidationError> {
        serde_json::to_string_pretty(self).map_err(|e| invalid(e.to_string()))
    }
}

/// Materialize one solve's model (requirement 16): the deterministic pure
/// function of (base model, batch request, solve index) whose returned bytes
/// — not the change description — are what is solved and hashed.
///
/// A repeat batch returns the base model's canonical bytes unchanged. A
/// variant batch replaces exactly the named variables' bounds and rebinds the
/// model through [`Model::rebound`], so domains, the matrix, the objective
/// and row bounds are the base's by construction.
///
/// # Errors
/// Returns a document failure for an invalid request or out-of-range index,
/// and for a change naming a variable the base model does not have.
pub fn materialize(
    base: &Model,
    request: &BatchRequest,
    index: u32,
) -> Result<(Model, Vec<u8>, String), ValidationError> {
    request.validate()?;
    if index >= request.solves {
        return Err(invalid("solve index outside the batch"));
    }
    let model = match request.kind {
        BatchKind::Repeat => base.clone(),
        BatchKind::Variant => {
            let variant = request
                .variants
                .iter()
                .find(|variant| variant.index == index)
                .ok_or_else(|| invalid("missing variant for solve index"))?;
            let mut variables = base.document().variables.clone();
            for change in &variant.changes {
                let variable = variables
                    .iter_mut()
                    .find(|variable| variable.id == change.variable_id)
                    .ok_or_else(|| {
                        invalid(format!(
                            "variant change names unknown variable {}",
                            change.variable_id
                        ))
                    })?;
                variable.lower = Bound::Finite {
                    value: change.lower,
                };
                variable.upper = Bound::Finite {
                    value: change.upper,
                };
            }
            base.rebound(variables)?
        }
    };
    let bytes = model.to_json()?.into_bytes();
    let sha256 = crate::sha256::hex(&bytes);
    Ok((model, bytes, sha256))
}

/// One solve's entry in an lp-batch-endpoint-v1 record.
#[derive(Clone, Debug, PartialEq, Serialize)]
pub struct SolveSummary {
    /// Solve index; summaries are ordered 0..solves-1.
    pub index: u32,
    /// SHA-256 of the materialized model bytes actually solved.
    pub model_sha256: String,
    /// SHA-256 of the per-solve record file bytes, or [`NO_RECORD`] when the
    /// solve has no record.
    pub endpoint_sha256: String,
    /// The per-solve record's own outcome label — the endpoint's assessment
    /// classification — or `not_attempted`/`failed` when no record exists.
    pub status: String,
    /// Wall time of the solve itself, excluding session setup.
    pub solve_elapsed_ns: u64,
    /// This solve's session phases (`variant_rebind`, `engine_rebind`,
    /// `bound_upload`), recorded here because the endpoint phase allow-list
    /// deliberately excludes them (requirement 24).
    pub session_phases_ns: BTreeMap<String, u64>,
    /// Why the solve has no record; present exactly when the status is
    /// `not_attempted` or `failed` (requirement 27).
    pub reason: Option<String>,
}
deserialize_required_object!(SolveSummary {
    index: u32,
    model_sha256: String,
    endpoint_sha256: String,
    status: String,
    solve_elapsed_ns: u64,
    session_phases_ns: BTreeMap<String, u64>,
    reason: Option<String>
});

/// An lp-batch-endpoint-v1 record: one batch's identity, one-time setup
/// phases, per-solve summaries and the binding payload hash.
#[derive(Clone, Debug, PartialEq, Serialize)]
pub struct BatchEndpoint {
    /// Must be 1.
    pub schema_version: u32,
    /// SHA-256 of the exact base model input bytes.
    pub model_sha256: String,
    /// SHA-256 of the exact batch request input bytes.
    pub batch_sha256: String,
    /// The session backend every solve requested; SPEC-0014 sessions exist
    /// only for `cuda-lp-tuned`, so the record refuses any other identity.
    pub requested_backend: String,
    /// The one-time setup phases: device context, module load,
    /// preconditioning and invariant allocation/upload (requirement 24).
    pub setup: SessionSetup,
    /// One summary per solve, in solve order.
    pub solves: Vec<SolveSummary>,
    /// Binds the request hash, the base model hash and every per-solve record
    /// hash and status in solve order; the layout is this module's shared
    /// `payload_hash` definition (requirement 26).
    pub payload_sha256: String,
}
deserialize_required_object!(BatchEndpoint {
    schema_version: u32,
    model_sha256: String,
    batch_sha256: String,
    requested_backend: String,
    setup: SessionSetup,
    solves: Vec<SolveSummary>,
    payload_sha256: String
});

impl BatchEndpoint {
    /// Build a batch record from the documents and per-solve summaries,
    /// computing the identity and payload hashes.
    ///
    /// Every directory-independent invariant of [`BatchEndpoint::verify`] is
    /// checked here, so a producer's own inconsistency is refused at
    /// construction rather than left for a later verifier.
    ///
    /// # Errors
    /// Returns a document failure when the request, the summaries or the
    /// phase vocabularies violate the batch contract.
    pub fn new(
        batch_bytes: &[u8],
        model_bytes: &[u8],
        requested_backend: String,
        setup: SessionSetup,
        solves: Vec<SolveSummary>,
    ) -> Result<Self, ValidationError> {
        let mut endpoint = Self {
            schema_version: 1,
            model_sha256: crate::sha256::hex(model_bytes),
            batch_sha256: crate::sha256::hex(batch_bytes),
            requested_backend,
            setup,
            solves,
            payload_sha256: String::new(),
        };
        endpoint.payload_sha256 = endpoint.compute_payload();
        endpoint.check(
            &Model::from_json(model_bytes)?,
            &BatchRequest::from_json(batch_bytes)?,
        )?;
        Ok(endpoint)
    }

    /// Parse a strict lp-batch-endpoint-v1 document. Verification against the
    /// model, request and evidence directory is a separate required step.
    ///
    /// # Errors
    /// Returns malformed JSON, duplicate keys, unknown fields or a
    /// non-object shape.
    pub fn from_json(bytes: &[u8]) -> Result<Self, ValidationError> {
        crate::lp::unique_json(bytes)?;
        serde_json::from_slice(bytes).map_err(|e| invalid(e.to_string()))
    }

    fn compute_payload(&self) -> String {
        payload_hash(
            &self.batch_sha256,
            &self.model_sha256,
            self.solves
                .iter()
                .map(|solve| (solve.endpoint_sha256.as_str(), solve.status.as_str())),
        )
    }

    /// Every invariant that does not touch the evidence directory.
    fn check(&self, base: &Model, request: &BatchRequest) -> Result<(), ValidationError> {
        if self.schema_version != 1 {
            return Err(invalid("batch endpoint version"));
        }
        if self.requested_backend != "cuda-lp-tuned" {
            return Err(invalid("batch session backend"));
        }
        check_phases(&self.setup.phases_ns, &SETUP_PHASES)?;
        if self.solves.len() != request.solves as usize
            || self
                .solves
                .iter()
                .enumerate()
                .any(|(position, solve)| solve.index != position as u32)
        {
            return Err(invalid("batch summary count/order"));
        }
        for solve in &self.solves {
            let no_record = NO_RECORD_STATUSES.contains(&solve.status.as_str());
            if no_record != (solve.endpoint_sha256 == NO_RECORD)
                || no_record != solve.reason.is_some()
            {
                return Err(invalid("batch summary record/reason mismatch"));
            }
            if !no_record && !hash_ok(&solve.endpoint_sha256) {
                return Err(invalid("invalid per-solve record hash"));
            }
            check_phases(&solve.session_phases_ns, &SOLVE_PHASES)?;
            let (_, _, materialized_sha256) = materialize(base, request, solve.index)?;
            if solve.model_sha256 != materialized_sha256 {
                return Err(invalid("solve model identity differs"));
            }
        }
        Ok(())
    }

    /// Recompute the batch record from the retained evidence alone:
    /// re-materialize every variant, re-verify every per-solve lp-endpoint
    /// record against its materialized bytes, and recompute every hash
    /// (requirement 17).
    ///
    /// # Errors
    /// Returns a document failure on any identity, hash, status or
    /// verification mismatch; a missing per-solve record without an explicit
    /// reason fails (requirement 27).
    pub fn verify(
        &self,
        model_bytes: &[u8],
        batch_bytes: &[u8],
        dir: &Path,
    ) -> Result<(), ValidationError> {
        if self.model_sha256 != crate::sha256::hex(model_bytes)
            || self.batch_sha256 != crate::sha256::hex(batch_bytes)
        {
            return Err(invalid("batch model/request hash differs"));
        }
        let request = BatchRequest::from_json(batch_bytes)?;
        let base = Model::from_json(model_bytes)?;
        self.check(&base, &request)?;
        let mut session_identity = None;
        for solve in &self.solves {
            let (_, bytes, _) = materialize(&base, &request, solve.index)?;
            let path = dir.join(solve_file_name(solve.index));
            match std::fs::read(&path) {
                Ok(file_bytes) => {
                    if solve.endpoint_sha256 == NO_RECORD
                        || solve.endpoint_sha256 != crate::sha256::hex(&file_bytes)
                    {
                        return Err(invalid("solve record hash differs"));
                    }
                    let endpoint = crate::lp::LpEndpoint::from_json(&file_bytes)?;
                    endpoint.verify(&bytes)?;
                    if endpoint.requested_backend != self.requested_backend {
                        return Err(invalid("solve backend identity differs"));
                    }
                    if endpoint.record.backend != self.requested_backend
                        || endpoint.fallback_reason.is_some()
                    {
                        return Err(invalid("a batch session cannot fall back"));
                    }
                    let identity = (
                        endpoint
                            .record
                            .lp_settings
                            .ok_or_else(|| invalid("missing session method identity"))?,
                        endpoint
                            .record
                            .lp_execution
                            .clone()
                            .ok_or_else(|| invalid("missing session execution identity"))?,
                    );
                    if session_identity
                        .as_ref()
                        .is_some_and(|expected| expected != &identity)
                    {
                        return Err(invalid("batch session method/execution identity differs"));
                    }
                    session_identity = Some(identity);
                    if solve.status != endpoint.assessment.classification {
                        return Err(invalid("solve status differs"));
                    }
                }
                Err(error) if error.kind() == std::io::ErrorKind::NotFound => {
                    if !NO_RECORD_STATUSES.contains(&solve.status.as_str())
                        || solve.reason.is_none()
                    {
                        return Err(invalid("missing solve record without a reason"));
                    }
                }
                Err(error) => return Err(invalid(format!("evidence read: {error}"))),
            }
        }
        if self.payload_sha256 != self.compute_payload() {
            return Err(invalid("batch payload hash differs"));
        }
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use optimizer_core::{CancellationToken, LpDiagnostics, LpSettings, SolveOptions};
    use optimizer_lp::HostLpBackend;
    use std::sync::atomic::{AtomicUsize, Ordering};

    const MODEL: &[u8] = include_bytes!("../../../examples/lp-model-v1.json");

    fn base() -> Model {
        Model::from_json(MODEL).unwrap()
    }

    fn repeat_request(solves: u32) -> BatchRequest {
        BatchRequest {
            schema_version: 1,
            kind: BatchKind::Repeat,
            solves,
            variants: vec![],
            generator: None,
            batch_time_limit_ms: 60_000,
        }
    }

    fn variant_request(solves: u32) -> BatchRequest {
        BatchRequest {
            schema_version: 1,
            kind: BatchKind::Variant,
            solves,
            variants: (0..solves)
                .map(|index| Variant {
                    index,
                    changes: vec![BoundChange {
                        variable_id: index % 2,
                        lower: 0.0,
                        upper: 1.0 - f64::from(index) * 0.25,
                    }],
                })
                .collect(),
            generator: Some(Generator {
                seed: 7,
                changes: 1,
            }),
            batch_time_limit_ms: 60_000,
        }
    }

    fn sandbox() -> std::path::PathBuf {
        static COUNTER: AtomicUsize = AtomicUsize::new(0);
        let path = std::env::temp_dir().join(format!(
            "optimizer-lp-batch-{}-{}",
            std::process::id(),
            COUNTER.fetch_add(1, Ordering::SeqCst)
        ));
        std::fs::create_dir_all(&path).expect("sandbox");
        path
    }

    /// One schema-valid lp-endpoint-v3 tuned record over the base model's
    /// canonical bytes, built exactly as lp.rs's tuned tests build theirs: a
    /// host solve's record carrying the tuned execution identity and matched
    /// control observations, signed by the real constructor.
    fn observed_endpoint() -> (Vec<u8>, crate::lp::LpEndpoint) {
        use optimizer_core::{
            Fp64ExecutionSettings, LpControlDiagnostics, LpExecutionDiagnostics, LpExecutionRecord,
        };
        let model = base();
        let canonical = model.to_json().unwrap().into_bytes();
        let options: SolveOptions =
            serde_json::from_slice(include_bytes!("../../../examples/solve-config-v1.json"))
                .unwrap();
        let backend = HostLpBackend::new(LpSettings::published(3, 2)).unwrap();
        let mut diagnostics = LpDiagnostics::new(true, true);
        let mut record = backend
            .solve_with_diagnostics(
                &model,
                &options,
                &CancellationToken::new(),
                None,
                &mut diagnostics,
            )
            .unwrap();
        let settings = Fp64ExecutionSettings::from_json(include_bytes!(
            "../../../examples/lp-execution-v1.json"
        ))
        .unwrap();
        record.schema_version = 3;
        record.backend = "cuda-lp-tuned".into();
        record.lp_execution = Some(LpExecutionRecord {
            settings,
            code_object_sha256: "a".repeat(64),
        });
        let mut execution = LpExecutionDiagnostics::new(settings);
        execution.code_object_sha256 = Some("a".repeat(64));
        execution.kernel_launches = 6;
        diagnostics.execution = Some(execution);
        diagnostics.control = Some(LpControlDiagnostics {
            controller: "host-restart-weight-v1".into(),
            logical_iterations: 3,
            physical_iterations: Some(3),
            device_kernel_launches: 6,
            assessments: 2,
            kkt_evaluations: 3,
            restarts: diagnostics.restarts.unwrap(),
            weight: 1.0,
            stop: "iteration_limit".into(),
        });
        let endpoint = crate::lp::LpEndpoint::new(
            &canonical,
            "cuda-lp-tuned".into(),
            record,
            diagnostics,
            None,
        )
        .unwrap();
        endpoint.verify(&canonical).unwrap();
        (canonical, endpoint)
    }

    fn summary(
        index: u32,
        model_sha256: String,
        endpoint_bytes: &[u8],
        status: String,
    ) -> SolveSummary {
        SolveSummary {
            index,
            model_sha256,
            endpoint_sha256: crate::sha256::hex(endpoint_bytes),
            status,
            solve_elapsed_ns: 1,
            session_phases_ns: BTreeMap::from([("variant_rebind".to_owned(), 1)]),
            reason: None,
        }
    }

    #[test]
    fn batch_refuses_mixed_method_code_and_fallback_identities() {
        for change in ["code", "method", "fallback"] {
            let (canonical, first) = observed_endpoint();
            let mut record = first.record.clone();
            let mut diagnostics = first.diagnostics.clone();
            diagnostics.control = first.control.clone();
            diagnostics.execution = first.execution.clone();
            let fallback = match change {
                "code" => {
                    record.lp_execution.as_mut().unwrap().code_object_sha256 = "b".repeat(64);
                    diagnostics.execution.as_mut().unwrap().code_object_sha256 =
                        Some("b".repeat(64));
                    None
                }
                "method" => {
                    record.lp_settings.as_mut().unwrap().power_iterations += 1;
                    None
                }
                _ => {
                    record.backend = "highs".into();
                    record.schema_version = 2;
                    record.lp_settings = None;
                    record.lp_execution = None;
                    diagnostics.control = None;
                    Some("injected fallback".into())
                }
            };
            let second = crate::lp::LpEndpoint::new(
                &canonical,
                "cuda-lp-tuned".into(),
                record,
                diagnostics,
                fallback,
            )
            .unwrap();
            second.verify(&canonical).unwrap(); // Each file is individually valid.
            let dir = sandbox();
            let request = repeat_request(2).to_json().unwrap().into_bytes();
            let mut solves = Vec::new();
            for (index, endpoint) in [first, second].into_iter().enumerate() {
                let bytes = serde_json::to_vec_pretty(&endpoint).unwrap();
                write_evidence_file(&dir.join(solve_file_name(index as u32)), &bytes).unwrap();
                solves.push(summary(
                    index as u32,
                    crate::sha256::hex(&canonical),
                    &bytes,
                    endpoint.assessment.classification,
                ));
            }
            let batch = BatchEndpoint::new(
                &request,
                &canonical,
                "cuda-lp-tuned".into(),
                SessionSetup::default(),
                solves,
            )
            .unwrap();
            let error = batch.verify(&canonical, &request, &dir).unwrap_err();
            assert!(
                error.message.contains(if change == "fallback" {
                    "cannot fall back"
                } else {
                    "session method/execution"
                }),
                "{change}: {error}"
            );
            std::fs::remove_dir_all(dir).unwrap();
        }
    }

    #[test]
    fn batch_request_parsing_is_strict() {
        let request = variant_request(2);
        let bytes = serde_json::to_vec(&request).unwrap();
        assert_eq!(BatchRequest::from_json(&bytes).unwrap(), request);
        let mut extra = serde_json::to_value(&request).unwrap();
        extra["unknown"] = true.into();
        assert!(BatchRequest::from_json(&serde_json::to_vec(&extra).unwrap()).is_err());
        extra = serde_json::to_value(&request).unwrap();
        extra["schema_version"] = 2.into();
        assert!(BatchRequest::from_json(&serde_json::to_vec(&extra).unwrap()).is_err());
        // An array where the object belongs is refused at every level.
        assert!(BatchRequest::from_json(b"[]").is_err());
        let mut array = serde_json::to_value(&request).unwrap();
        array["variants"] = serde_json::json!([]);
        array["kind"] = "variant".into();
        assert!(BatchRequest::from_json(&serde_json::to_vec(&array).unwrap()).is_err());
        let mut nested = serde_json::to_value(&request).unwrap();
        nested["variants"][0] = serde_json::json!([0, []]);
        assert!(BatchRequest::from_json(&serde_json::to_vec(&nested).unwrap()).is_err());
        // A missing required field (nullables included) is refused.
        for field in [
            "schema_version",
            "kind",
            "solves",
            "variants",
            "generator",
            "batch_time_limit_ms",
        ] {
            let mut missing = serde_json::to_value(&request).unwrap();
            missing.as_object_mut().unwrap().remove(field);
            assert!(
                BatchRequest::from_json(&serde_json::to_vec(&missing).unwrap()).is_err(),
                "missing {field}"
            );
        }
        let duplicate =
            String::from_utf8(bytes)
                .unwrap()
                .replacen('{', "{\"schema_version\":1,", 1);
        assert!(BatchRequest::from_json(duplicate.as_bytes()).is_err());
        // Kind/generator consistency: a variant batch without its generator
        // and a repeat batch with one are both refused.
        let mut orphan = serde_json::to_value(&request).unwrap();
        orphan["generator"] = serde_json::Value::Null;
        assert!(BatchRequest::from_json(&serde_json::to_vec(&orphan).unwrap()).is_err());
        let mut surplus = serde_json::to_value(repeat_request(1)).unwrap();
        surplus["generator"] = serde_json::json!({"seed": 1, "changes": 1});
        assert!(BatchRequest::from_json(&serde_json::to_vec(&surplus).unwrap()).is_err());
        // Kind spelling is the snake_case contract.
        assert_eq!(
            serde_json::to_string(&BatchKind::Repeat).unwrap(),
            "\"repeat\""
        );
        assert!(serde_json::from_str::<BatchKind>("\"Repeat\"").is_err());
    }

    #[test]
    fn materialize_is_deterministic_and_refuses_bad_changes() {
        let base = base();
        let request = variant_request(3);
        let first = materialize(&base, &request, 1).unwrap();
        let second = materialize(&base, &request, 1).unwrap();
        assert_eq!(first.1, second.1, "materialized bytes are deterministic");
        assert_eq!(first.2, second.2);
        let repeat = materialize(&base, &repeat_request(2), 1).unwrap();
        let canonical = base.to_json().unwrap().into_bytes();
        assert_eq!(repeat.1, canonical);
        assert_eq!(repeat.2, crate::sha256::hex(&canonical));
        assert_ne!(first.2, repeat.2, "a changed bound changes the identity");
        assert!(
            materialize(&base, &request, 3).is_err(),
            "index outside the batch"
        );

        let mut unknown = variant_request(1);
        unknown.variants[0].changes[0].variable_id = 99;
        assert!(
            materialize(&base, &unknown, 0).is_err(),
            "unknown variable refused"
        );

        let mut inverted = variant_request(1);
        inverted.variants[0].changes[0].lower = 0.75;
        inverted.variants[0].changes[0].upper = 0.25;
        assert!(inverted.validate().is_err(), "inverted bounds refused");
        assert!(materialize(&base, &inverted, 0).is_err());

        let mut nonfinite = variant_request(1);
        nonfinite.variants[0].changes[0].upper = f64::NAN;
        assert!(nonfinite.validate().is_err(), "non-finite bounds refused");

        let mut repeated = variant_request(1);
        let repeated_id = repeated.variants[0].changes[0].variable_id;
        repeated.variants[0].changes.push(BoundChange {
            variable_id: repeated_id,
            lower: 0.0,
            upper: 0.5,
        });
        assert!(
            repeated.validate().is_err(),
            "a repeated variable is ambiguous"
        );
    }

    #[test]
    fn variant_materialization_changes_only_bounds() {
        let base = base();
        let request = variant_request(2);
        let (variant, bytes, sha256) = materialize(&base, &request, 1).unwrap();
        assert_eq!(sha256, crate::sha256::hex(&bytes));
        let document = variant.document();
        assert_eq!(document.variables[1].upper, Bound::Finite { value: 0.75 });
        assert_eq!(document.variables[0], base.document().variables[0]);
        assert_eq!(document.constraints, base.document().constraints);
        assert_eq!(document.objective, base.document().objective);
        // The change lands in the canonical program: the scaled bounds differ.
        let base_program = optimizer_lp::LinearProgram::new(&base).unwrap();
        let variant_program = optimizer_lp::LinearProgram::new(&variant).unwrap();
        assert!(base_program.same_matrix_objective_rows(&variant_program));
        assert_ne!(
            base_program.matrix_sha256(),
            variant_program.matrix_sha256()
        );
    }

    #[test]
    fn batch_endpoint_verifies_a_recorded_directory() {
        let dir = sandbox();
        let (canonical, endpoint) = observed_endpoint();
        let request = repeat_request(2);
        let batch_bytes = request.to_json().unwrap().into_bytes();
        let mut solves = Vec::new();
        for index in 0..2 {
            let (_, _, model_sha256) = materialize(&base(), &request, index).unwrap();
            let endpoint_bytes = serde_json::to_vec_pretty(&endpoint).unwrap();
            write_evidence_file(&dir.join(solve_file_name(index)), &endpoint_bytes).unwrap();
            solves.push(summary(
                index,
                model_sha256,
                &endpoint_bytes,
                endpoint.assessment.classification.clone(),
            ));
        }
        let mut setup = SessionSetup::default();
        setup.phases_ns.insert("device_context".into(), 1);
        setup.phases_ns.insert("preconditioning".into(), 2);
        let endpoint_record =
            BatchEndpoint::new(&batch_bytes, MODEL, "cuda-lp-tuned".into(), setup, solves).unwrap();
        endpoint_record.verify(MODEL, &batch_bytes, &dir).unwrap();
        let bytes = serde_json::to_vec(&endpoint_record).unwrap();
        let parsed = BatchEndpoint::from_json(&bytes).unwrap();
        assert_eq!(parsed, endpoint_record);
        parsed.verify(MODEL, &batch_bytes, &dir).unwrap();
        // The endpoint's model identity is the materialized canonical bytes,
        // which the per-solve record verification recomputes.
        assert_eq!(endpoint.model_sha256, crate::sha256::hex(&canonical));
        std::fs::remove_dir_all(&dir).ok();
    }

    #[test]
    fn batch_endpoint_verification_detects_tampering() {
        let dir = sandbox();
        let (.., endpoint) = observed_endpoint();
        let request = repeat_request(1);
        let batch_bytes = request.to_json().unwrap().into_bytes();
        let (_, _, model_sha256) = materialize(&base(), &request, 0).unwrap();
        let endpoint_bytes = serde_json::to_vec_pretty(&endpoint).unwrap();
        write_evidence_file(&dir.join(solve_file_name(0)), &endpoint_bytes).unwrap();
        let build = |solve: SolveSummary| {
            BatchEndpoint::new(
                &batch_bytes,
                MODEL,
                "cuda-lp-tuned".into(),
                SessionSetup::default(),
                vec![solve],
            )
            .unwrap()
        };
        let good = summary(
            0,
            model_sha256.clone(),
            &endpoint_bytes,
            endpoint.assessment.classification.clone(),
        );
        let record = build(good.clone());
        record.verify(MODEL, &batch_bytes, &dir).unwrap();
        // Hash, status, payload, model and request mutations all fail.
        let mut wrong = record.clone();
        wrong.solves[0].endpoint_sha256 = "0".repeat(64);
        assert!(wrong.verify(MODEL, &batch_bytes, &dir).is_err());
        let mut wrong = record.clone();
        wrong.solves[0].status = "interrupted".into();
        assert!(wrong.verify(MODEL, &batch_bytes, &dir).is_err());
        let mut wrong = record.clone();
        wrong.payload_sha256 = "0".repeat(64);
        assert!(wrong.verify(MODEL, &batch_bytes, &dir).is_err());
        assert!(record.verify(b"{}", &batch_bytes, &dir).is_err());
        let other_request = repeat_request(1);
        let other_bytes = serde_json::to_vec(&BatchRequest {
            batch_time_limit_ms: 30_000,
            ..other_request
        })
        .unwrap();
        assert!(record.verify(MODEL, &other_bytes, &dir).is_err());
        // A wrong phase name is outside the requirement-24 vocabulary.
        let mut wrong = record.clone();
        wrong
            .solves
            .get_mut(0)
            .unwrap()
            .session_phases_ns
            .insert("kernels_and_synchronization".into(), 1);
        assert!(wrong.verify(MODEL, &batch_bytes, &dir).is_err());
        let mut wrong = record.clone();
        wrong.setup.phases_ns.insert("controller".into(), 1);
        assert!(wrong.verify(MODEL, &batch_bytes, &dir).is_err());
        // Requirement 27: a missing record needs an explicit reason.
        let missing_dir = sandbox();
        let mut unrecorded = good.clone();
        unrecorded.status = "not_attempted".into();
        unrecorded.endpoint_sha256 = NO_RECORD.to_owned();
        unrecorded.reason = Some("cancelled".into());
        let partial = build(unrecorded.clone());
        partial.verify(MODEL, &batch_bytes, &missing_dir).unwrap();
        let mut no_reason = partial.clone();
        no_reason.solves[0].reason = None;
        assert!(no_reason.verify(MODEL, &batch_bytes, &missing_dir).is_err());
        // A reasoned not_attempted summary with a present record file fails.
        assert!(partial.verify(MODEL, &batch_bytes, &dir).is_err());
        std::fs::remove_dir_all(&dir).ok();
        std::fs::remove_dir_all(&missing_dir).ok();
    }

    #[test]
    fn batch_endpoint_parsing_is_strict() {
        let request = repeat_request(1);
        let batch_bytes = request.to_json().unwrap().into_bytes();
        let (_, _, model_sha256) = materialize(&base(), &request, 0).unwrap();
        let record = BatchEndpoint::new(
            &batch_bytes,
            MODEL,
            "cuda-lp-tuned".into(),
            SessionSetup::default(),
            vec![SolveSummary {
                index: 0,
                model_sha256,
                endpoint_sha256: NO_RECORD.to_owned(),
                status: "not_attempted".into(),
                solve_elapsed_ns: 0,
                session_phases_ns: BTreeMap::new(),
                reason: Some("cancelled".into()),
            }],
        )
        .unwrap();
        let bytes = serde_json::to_vec(&record).unwrap();
        assert_eq!(BatchEndpoint::from_json(&bytes).unwrap(), record);
        let mut extra = serde_json::to_value(&record).unwrap();
        extra["unknown"] = true.into();
        assert!(BatchEndpoint::from_json(&serde_json::to_vec(&extra).unwrap()).is_err());
        assert!(BatchEndpoint::from_json(b"[]").is_err());
        let mut array = serde_json::to_value(&record).unwrap();
        array["solves"] = serde_json::json!([]);
        assert!(BatchEndpoint::from_json(&serde_json::to_vec(&array).unwrap()).is_ok());
        array["solves"] = serde_json::json!([[0]]);
        assert!(BatchEndpoint::from_json(&serde_json::to_vec(&array).unwrap()).is_err());
        // A missing required field (the nullable reason included) is refused.
        for field in [
            "schema_version",
            "model_sha256",
            "batch_sha256",
            "requested_backend",
            "setup",
            "solves",
            "payload_sha256",
        ] {
            let mut missing = serde_json::to_value(&record).unwrap();
            missing.as_object_mut().unwrap().remove(field);
            assert!(
                BatchEndpoint::from_json(&serde_json::to_vec(&missing).unwrap()).is_err(),
                "missing {field}"
            );
        }
        let mut missing = serde_json::to_value(&record).unwrap();
        missing["solves"][0]
            .as_object_mut()
            .unwrap()
            .remove("reason");
        assert!(BatchEndpoint::from_json(&serde_json::to_vec(&missing).unwrap()).is_err());
        let duplicate =
            String::from_utf8(bytes)
                .unwrap()
                .replacen('{', "{\"schema_version\":1,", 1);
        assert!(BatchEndpoint::from_json(duplicate.as_bytes()).is_err());
        // The session backend is SPEC-0014's tuned identity only.
        let wrong_backend = BatchEndpoint::new(
            &batch_bytes,
            MODEL,
            "host-lp".into(),
            SessionSetup::default(),
            record.solves.clone(),
        );
        assert!(wrong_backend.is_err());
    }
}
