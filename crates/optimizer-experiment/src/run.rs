//! Provenance-bearing run records and verification under SPEC-0005.
//!
//! A [`SearchRecord`] already carries every budget needed to repeat the search
//! it describes. What it cannot say is what produced it: which revision, which
//! model bytes, which toolchain. [`RunRecord`] adds exactly that, and
//! [`RunRecord::verify_agreement`] is the single authority for comparing a
//! recorded search against a fresh one.
//!
//! Verification establishes determinism, not correctness. Two runs agreeing that
//! a search forfeited its proof claim is exactly as much of a proof as one run
//! saying so, and nothing here upgrades a claim the executive declined to make.

use serde::{Deserialize, Serialize};

use optimizer_core::{ErrorKind, ValidationError, nested_version};
use optimizer_extension::ExtensionSummary;
use optimizer_solver::{SEARCH_SCHEMA_VERSION, SearchRecord};

use crate::serde_strict::deserialize_object;

/// Current run record wire version.
pub const RUN_SCHEMA_VERSION: u32 = 2;

/// Revision recorded by an example that is deliberately not a measurement.
///
/// SPEC-0007 already fixed this convention for experiment results. Reusing the
/// same sentinel keeps one rule for "this document is a shape, not evidence".
pub const EXAMPLE_REVISION: &str = "0000000000000000000000000000000000000000";

/// Role one input document played in a run.
#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum InputRole {
    /// The original model that was searched.
    Model,
    /// The search configuration that was applied.
    Config,
}

impl<'de> Deserialize<'de> for InputRole {
    fn deserialize<D: serde::Deserializer<'de>>(deserializer: D) -> Result<Self, D::Error> {
        const NAMES: &[&str] = &["model", "config"];
        match String::deserialize(deserializer)?.as_str() {
            "model" => Ok(Self::Model),
            "config" => Ok(Self::Config),
            other => Err(serde::de::Error::unknown_variant(other, NAMES)),
        }
    }
}

/// One input document identified by its bytes rather than only its location.
#[derive(Clone, Debug, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct InputDocument {
    /// What this document was used for.
    pub role: InputRole,
    /// Path as the caller supplied it, for diagnosis rather than resolution.
    pub path: String,
    /// SHA-256 of the exact bytes that were read, as 64 lowercase hex digits.
    pub sha256: String,
}

deserialize_object!(InputDocument {
    role: InputRole,
    path: String,
    sha256: String,
});

/// Host facts describing where a run executed.
///
/// Field names are taken from SPEC-0007's experiment result rather than chosen
/// fresh, so the repository's two provenance shapes cannot drift apart.
#[derive(Clone, Debug, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct Hardware {
    /// Operating system description.
    pub os: String,
    /// CPU model name.
    pub cpu: String,
    /// Logical CPU count visible to the process.
    pub logical_cpus: u32,
    /// Selected GPU UUID; null for a CPU run.
    pub gpu_uuid: Option<String>,
    /// Selected GPU name; null for a CPU run.
    pub gpu_name: Option<String>,
    /// GPU driver version; null for a CPU run.
    pub driver: Option<String>,
}

deserialize_object!(Hardware {
    os: String,
    cpu: String,
    logical_cpus: u32,
    gpu_uuid: Option<String>,
    gpu_name: Option<String>,
    driver: Option<String>,
});

/// Build tooling that produced the binary performing a run.
#[derive(Clone, Debug, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct Toolchain {
    /// Rust compiler version string.
    pub rustc: String,
    /// Cargo version string.
    pub cargo: String,
}

deserialize_object!(Toolchain {
    rustc: String,
    cargo: String,
});

/// Immutable record of one run: a search plus what produced it.
///
/// The search record is embedded verbatim rather than summarized, so a reader
/// can see whether extensions influenced the run without consulting another
/// document.
#[derive(Clone, Debug, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct RunRecord {
    /// Must equal [`RUN_SCHEMA_VERSION`].
    pub schema_version: u32,
    /// Identifier for this record, unique within its collection.
    pub record_id: String,
    /// Source revision as 40 lowercase hex digits.
    pub revision: String,
    /// Whether the working tree differed from that revision.
    ///
    /// A dirty record identifies a source state no revision can reconstruct, so
    /// it must not be presented as reproducible evidence.
    pub dirty: bool,
    /// Host the run executed on.
    pub hardware: Hardware,
    /// Build tooling of the binary that performed the run.
    pub toolchain: Toolchain,
    /// Fingerprint of the canonical original model document.
    ///
    /// This identifies model bytes, not model identity: a record whose model was
    /// edited under an unchanged `model_id` is refused before any search runs.
    pub model_fingerprint: String,
    /// Input documents with the hashes of the bytes actually read.
    pub inputs: Vec<InputDocument>,
    /// The complete search record, embedded verbatim.
    pub search: SearchRecord,
    /// Run-level warnings, retained even on success.
    pub warnings: Vec<String>,
}

deserialize_object!(RunRecord {
    schema_version: u32,
    record_id: String,
    revision: String,
    dirty: bool,
    hardware: Hardware,
    toolchain: Toolchain,
    model_fingerprint: String,
    inputs: Vec<InputDocument>,
    search: SearchRecord,
    warnings: Vec<String>,
});

/// One field verification compares, named so a divergence can be reported.
///
/// Elapsed time is deliberately absent: it measures the host, not the search,
/// and a check that fails on every machine under every load would be obeyed by
/// deleting it.
const COMPARED_FIELDS: &[&str] = &[
    "outcome",
    "objective",
    "dual_bound",
    "gap",
    "forfeited",
    "nodes_explored",
    "nodes_pruned_infeasible",
    "nodes_pruned_bound",
    "open_nodes_remaining",
    "relaxations_solved",
];

/// What the environment performing a verification differs from, if anything.
///
/// This is diagnostic only. It never decides whether a run agreed: the fields
/// listed by [`RunRecord::compared_fields`] do that, and adding a field to
/// agreement would change what agreement means. Reporting an environment change
/// alongside a divergence explains a likely cause without excusing it.
#[derive(Clone, Debug, PartialEq, Eq, Default)]
pub struct EnvironmentDifference {
    /// The backend version the record names, when it differs from the current one.
    ///
    /// This is the only difference that speaks to numerical behavior directly: a
    /// rebuilt or upgraded library can legitimately change a node count.
    pub backend_version: Option<(String, String)>,
    /// The source revision the record names, when it differs.
    pub revision: Option<(String, String)>,
    /// The compiler the record names, when it differs.
    pub rustc: Option<(String, String)>,
}

impl EnvironmentDifference {
    /// Whether anything differs.
    pub fn is_empty(&self) -> bool {
        self.backend_version.is_none() && self.revision.is_none() && self.rustc.is_none()
    }

    /// One line per difference, each naming what changed and both values.
    ///
    /// The backend is reported first and labeled distinctly, because a changed
    /// library can alter a search's numbers while a changed revision or compiler
    /// only indicates that the source moved.
    pub fn describe(&self) -> Vec<String> {
        let mut lines = Vec::new();
        if let Some((recorded, current)) = &self.backend_version {
            lines.push(format!(
                "backend library differs: record {recorded}, current {current}; \
                 a rebuilt or upgraded library can change a search's counters"
            ));
        }
        if let Some((recorded, current)) = &self.revision {
            lines.push(format!(
                "source revision differs: record {recorded}, current {current}"
            ));
        }
        if let Some((recorded, current)) = &self.rustc {
            lines.push(format!(
                "compiler differs: record {recorded}, current {current}"
            ));
        }
        lines
    }
}

/// How a re-executed search's extensions behaved differently, if at all.
///
/// Diagnostic only, and deliberately built the same way as
/// [`EnvironmentDifference`]: it is computed after the search has run and is never
/// consulted when deciding agreement. Adding it to agreement would change what
/// agreement means for every record produced before that change, which SPEC-0005's
/// compatibility section reserves for a new record version and an ADR.
///
/// It is worth having anyway, because an extension that behaved differently
/// already shows up in the compared node counters. This says which extension, so a
/// reader is not left inferring it from a node count.
#[derive(Clone, Debug, PartialEq, Eq, Default)]
pub struct ExtensionDifference {
    /// One entry per extension whose summary differs, with both descriptions.
    pub changed: Vec<(String, String, String)>,
    /// Extensions the record names that the re-execution did not register.
    pub absent: Vec<String>,
    /// Extensions the re-execution registered that the record does not name.
    pub unexpected: Vec<String>,
}

impl ExtensionDifference {
    /// Compare a record's extension summaries against a fresh search's.
    pub fn between(recorded: &[ExtensionSummary], fresh: &[ExtensionSummary]) -> Self {
        // Counters only. An extension's identity and version are checked before
        // re-execution and refused there, so a difference reaching this point is
        // about behavior rather than about identity.
        let describe = |summary: &ExtensionSummary| {
            format!(
                "invocations {}, proposals {}, accepted {}, rejected {}, disabled {}",
                summary.invocations,
                summary.proposals,
                summary.accepted,
                summary.rejected,
                summary.disabled
            )
        };
        let mut difference = Self::default();
        for recorded_summary in recorded {
            match fresh
                .iter()
                .find(|summary| summary.extension_id == recorded_summary.extension_id)
            {
                Some(fresh_summary) => {
                    let (before, after) = (describe(recorded_summary), describe(fresh_summary));
                    if before != after {
                        difference.changed.push((
                            recorded_summary.extension_id.clone(),
                            before,
                            after,
                        ));
                    }
                }
                None => difference
                    .absent
                    .push(recorded_summary.extension_id.clone()),
            }
        }
        for fresh_summary in fresh {
            if !recorded
                .iter()
                .any(|summary| summary.extension_id == fresh_summary.extension_id)
            {
                difference
                    .unexpected
                    .push(fresh_summary.extension_id.clone());
            }
        }
        difference
    }

    /// Whether anything differs.
    pub fn is_empty(&self) -> bool {
        self.changed.is_empty() && self.absent.is_empty() && self.unexpected.is_empty()
    }

    /// One line per difference, each naming the extension and both descriptions.
    pub fn describe(&self) -> Vec<String> {
        let mut lines = Vec::new();
        for (extension_id, recorded, fresh) in &self.changed {
            lines.push(format!(
                "extension {extension_id} behaved differently: record {recorded}; \
                 reproduced {fresh}"
            ));
        }
        for extension_id in &self.absent {
            lines.push(format!(
                "extension {extension_id} is named by the record but was not registered"
            ));
        }
        for extension_id in &self.unexpected {
            lines.push(format!(
                "extension {extension_id} was registered but is not named by the record"
            ));
        }
        lines
    }
}

impl RunRecord {
    /// Field names verification compares, in report order.
    ///
    /// Exposed so a test can assert the comparison covers what the
    /// specification says it covers, rather than trusting the prose.
    pub fn compared_fields() -> &'static [&'static str] {
        COMPARED_FIELDS
    }

    /// Compare this record's environment against the one verifying it.
    ///
    /// The result is never consulted when deciding agreement. It exists so a
    /// divergence can say that the engine also changed, which is the difference
    /// between "this result is wrong" and "this was produced by another build".
    /// Distinguishing those two as an *outcome* rather than as a diagnostic would
    /// change what agreement means and needs its own decision record.
    pub fn environment_difference(
        &self,
        backend_version: &str,
        revision: &str,
        rustc: &str,
    ) -> EnvironmentDifference {
        let changed = |recorded: &str, current: &str| {
            (recorded != current).then(|| (recorded.to_owned(), current.to_owned()))
        };
        EnvironmentDifference {
            backend_version: changed(&self.search.backend_version, backend_version),
            revision: changed(&self.revision, revision),
            rustc: changed(&self.toolchain.rustc, rustc),
        }
    }

    /// Serialize one run record.
    ///
    /// # Errors
    ///
    /// Returns a document failure when the embedded search record cannot be
    /// serialized, which includes its own rejection of a nonfinite measurement
    /// standing in for a real number.
    pub fn to_json(&self) -> Result<String, ValidationError> {
        // Delegate to the search record's own serializer first so a nonfinite
        // measurement is rejected by the type that owns that rule.
        self.search.to_json()?;
        serde_json::to_string_pretty(self)
            .map_err(|error| ValidationError::new(ErrorKind::Document, error.to_string()))
    }

    /// Parse one complete versioned run record.
    ///
    /// Nested documents are versioned too, and their versions are checked here
    /// rather than deferred, so this parser cannot be laxer than the artifact
    /// validation tooling about a document it accepts.
    ///
    /// # Errors
    ///
    /// Returns a document failure for malformed JSON, an unknown or duplicate
    /// field, a positional array in place of an object, an unsupported version
    /// at this or any nested level, or malformed provenance.
    pub fn from_json(bytes: &[u8]) -> Result<Self, ValidationError> {
        let record: Self = serde_json::from_slice(bytes)
            .map_err(|error| ValidationError::new(ErrorKind::Document, error.to_string()))?;
        if record.schema_version != RUN_SCHEMA_VERSION {
            return Err(ValidationError::new(
                ErrorKind::Document,
                format!("unsupported run schema_version {}", record.schema_version),
            ));
        }
        nested_version(
            "search",
            record.search.schema_version,
            SEARCH_SCHEMA_VERSION,
        )?;
        record.validate_provenance()?;
        Ok(record)
    }

    /// Check that provenance is present and well shaped.
    ///
    /// # Errors
    ///
    /// Returns a document failure naming the offending field.
    fn validate_provenance(&self) -> Result<(), ValidationError> {
        let document = |message: String| ValidationError::new(ErrorKind::Document, message);
        if self.record_id.is_empty() {
            return Err(document("record_id must not be empty".to_owned()));
        }
        if !is_hex(&self.revision, 40) {
            return Err(document(
                "revision must be 40 lowercase hexadecimal digits".to_owned(),
            ));
        }
        if self.model_fingerprint.is_empty() {
            return Err(document("model_fingerprint must not be empty".to_owned()));
        }
        for role in [InputRole::Model, InputRole::Config] {
            let count = self
                .inputs
                .iter()
                .filter(|input| input.role == role)
                .count();
            if count != 1 {
                return Err(document(format!(
                    "inputs must name exactly one {} document, found {count}",
                    match role {
                        InputRole::Model => "model",
                        InputRole::Config => "config",
                    }
                )));
            }
        }
        for input in &self.inputs {
            if !is_hex(&input.sha256, 64) {
                return Err(document(format!(
                    "inputs: {}: sha256 must be 64 lowercase hexadecimal digits",
                    input.path
                )));
            }
        }
        Ok(())
    }

    /// Whether this record may be presented as reproducible evidence.
    ///
    /// A dirty working tree and the example revision each mean the recorded
    /// source cannot be recovered, so neither is evidence however well the run
    /// verifies.
    pub fn is_evidence(&self) -> bool {
        !self.dirty && self.revision != EXAMPLE_REVISION
    }

    /// Compare this record's search against a freshly produced one.
    ///
    /// The comparison covers outcome, recomputed objective, dual bound, gap,
    /// forfeiture state and all five counters, and deliberately excludes
    /// measured elapsed time. Agreement is evidence of determinism; it is not a
    /// proof of optimality, and it cannot clear a forfeited proof claim.
    ///
    /// # Errors
    ///
    /// Returns a numerical failure naming the first diverging field.
    pub fn verify_agreement(&self, fresh: &SearchRecord) -> Result<(), ValidationError> {
        let recorded = &self.search;
        let diverged = |field: &str, recorded: String, fresh: String| {
            ValidationError::new(
                ErrorKind::Numerical,
                format!("{field}: recorded {recorded}, reproduced {fresh}"),
            )
        };

        if recorded.outcome != fresh.outcome {
            return Err(diverged(
                "outcome",
                format!("{:?}", recorded.outcome),
                format!("{:?}", fresh.outcome),
            ));
        }
        for (field, left, right) in [
            ("objective", recorded.objective, fresh.objective),
            ("dual_bound", recorded.dual_bound, fresh.dual_bound),
            ("gap", recorded.gap, fresh.gap),
        ] {
            // Bitwise equality is intended: a reproduced search that computed a
            // different number diverged, however small the difference.
            if left.map(f64::to_bits) != right.map(f64::to_bits) {
                return Err(diverged(field, describe(left), describe(right)));
            }
        }
        if recorded.forfeited != fresh.forfeited {
            return Err(diverged(
                "forfeited",
                recorded.forfeited.to_string(),
                fresh.forfeited.to_string(),
            ));
        }
        for (field, left, right) in [
            (
                "nodes_explored",
                recorded.nodes_explored,
                fresh.nodes_explored,
            ),
            (
                "nodes_pruned_infeasible",
                recorded.nodes_pruned_infeasible,
                fresh.nodes_pruned_infeasible,
            ),
            (
                "nodes_pruned_bound",
                recorded.nodes_pruned_bound,
                fresh.nodes_pruned_bound,
            ),
            (
                "open_nodes_remaining",
                recorded.open_nodes_remaining,
                fresh.open_nodes_remaining,
            ),
            (
                "relaxations_solved",
                recorded.relaxations_solved,
                fresh.relaxations_solved,
            ),
        ] {
            if left != right {
                return Err(diverged(field, left.to_string(), right.to_string()));
            }
        }
        Ok(())
    }
}

/// Describe an optional measurement for a divergence diagnostic.
fn describe(value: Option<f64>) -> String {
    value.map_or_else(|| "absent".to_owned(), |value| value.to_string())
}

/// Whether `value` is exactly `length` lowercase hexadecimal digits.
fn is_hex(value: &str, length: usize) -> bool {
    value.len() == length
        && value
            .bytes()
            .all(|byte| byte.is_ascii_digit() || (b'a'..=b'f').contains(&byte))
}
