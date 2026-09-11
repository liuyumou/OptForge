//! Flow-shop instance documents under SPEC-0008 requirements 1 to 5.
//!
//! An instance is immutable once constructed and is never rescaled, normalized or
//! transposed. Processing times are indexed by machine and then by job, matching
//! the reference generator's own ordering, so a transposed matrix is a different
//! document rather than an interpretation of this one.

use serde::Serialize;

use optimizer_core::{ErrorKind, ValidationError};

use crate::serde_strict::deserialize_object;

/// Current flow-shop instance wire version.
pub const SCHEDULE_SCHEMA_VERSION: u32 = 1;

/// Largest accepted job count.
///
/// The positional encoding is quadratic in this number, so an instance large
/// enough to exhaust memory during encoding is refused as unsupported input
/// rather than discovered as an allocation failure. Taillard's largest published
/// class is 500 jobs.
pub const MAX_JOBS: u32 = 500;

/// Largest accepted machine count.
pub const MAX_MACHINES: u32 = 20;

/// Largest accepted processing time.
///
/// Taillard's generator draws from 1..=99. The bound here is looser because the
/// document type describes a flow shop rather than that one generator, but it is
/// still bounded so that the makespan of a legal instance cannot overflow.
pub const MAX_PROCESSING_TIME: u32 = 1_000_000;

/// Unvalidated instance input. Use [`FlowShopInstance::new`] before evaluation.
#[derive(Clone, Debug, PartialEq, Eq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct FlowShopDocument {
    /// Must equal [`SCHEDULE_SCHEMA_VERSION`].
    pub schema_version: u32,
    /// Nonempty caller-assigned instance identity.
    pub instance_id: String,
    /// Number of jobs.
    pub jobs: u32,
    /// Number of machines.
    pub machines: u32,
    /// Processing times indexed by machine, then by job.
    pub processing_times: Vec<Vec<u32>>,
}

deserialize_object!(FlowShopDocument {
    schema_version: u32,
    instance_id: String,
    jobs: u32,
    machines: u32,
    processing_times: Vec<Vec<u32>>,
});

/// Immutable structurally valid flow-shop instance.
///
/// Construction validates the declared shape against the data, so no later stage
/// has to re-check it. This is not a claim that the instance is solvable.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct FlowShopInstance {
    document: FlowShopDocument,
}

impl FlowShopInstance {
    /// Validate instance data without modifying any processing time.
    ///
    /// # Errors
    ///
    /// Returns a document failure for an unsupported version, and a structural
    /// failure for an empty identifier, a zero or oversized job or machine count,
    /// a matrix disagreeing with the declared shape, or a processing time that is
    /// zero or above [`MAX_PROCESSING_TIME`].
    pub fn new(document: FlowShopDocument) -> Result<Self, ValidationError> {
        if document.schema_version != SCHEDULE_SCHEMA_VERSION {
            return Err(ValidationError::new(
                ErrorKind::Document,
                format!(
                    "unsupported instance schema_version {}, expected {SCHEDULE_SCHEMA_VERSION}",
                    document.schema_version
                ),
            ));
        }
        if document.instance_id.is_empty() {
            return Err(ValidationError::new(
                ErrorKind::Structural,
                "instance_id must not be empty",
            ));
        }
        if document.instance_id.chars().any(char::is_control) {
            return Err(ValidationError::new(
                ErrorKind::Structural,
                "instance_id must not contain control characters",
            ));
        }
        for (name, value, limit) in [
            ("jobs", document.jobs, MAX_JOBS),
            ("machines", document.machines, MAX_MACHINES),
        ] {
            if value == 0 {
                return Err(ValidationError::new(
                    ErrorKind::Structural,
                    format!("{name} must be positive"),
                ));
            }
            if value > limit {
                return Err(ValidationError::new(
                    ErrorKind::Unsupported,
                    format!("{name} is {value}, which exceeds the supported maximum {limit}"),
                ));
            }
        }
        // Requirement 3: the declared shape and the data must not disagree. A
        // ragged matrix is rejected per row, so the diagnostic names the row.
        if document.processing_times.len() != document.machines as usize {
            return Err(ValidationError::new(
                ErrorKind::Structural,
                format!(
                    "processing_times has {} machine rows, expected {}",
                    document.processing_times.len(),
                    document.machines
                ),
            ));
        }
        for (machine, row) in document.processing_times.iter().enumerate() {
            if row.len() != document.jobs as usize {
                return Err(ValidationError::new(
                    ErrorKind::Structural,
                    format!(
                        "processing_times row {machine} has {} entries, expected {}",
                        row.len(),
                        document.jobs
                    ),
                ));
            }
            for (job, &time) in row.iter().enumerate() {
                // Requirement 2: refuse rather than clamp. A zero time would make
                // an operation instantaneous, which is a different problem.
                if time == 0 {
                    return Err(ValidationError::new(
                        ErrorKind::Structural,
                        format!(
                            "processing time for job {job} on machine {machine} must be positive"
                        ),
                    ));
                }
                if time > MAX_PROCESSING_TIME {
                    return Err(ValidationError::new(
                        ErrorKind::Unsupported,
                        format!(
                            "processing time for job {job} on machine {machine} is {time}, which exceeds the supported maximum {MAX_PROCESSING_TIME}"
                        ),
                    ));
                }
            }
        }
        Ok(Self { document })
    }

    /// Read-only access to the validated document.
    pub fn document(&self) -> &FlowShopDocument {
        &self.document
    }

    /// Number of jobs.
    pub fn jobs(&self) -> usize {
        self.document.jobs as usize
    }

    /// Number of machines.
    pub fn machines(&self) -> usize {
        self.document.machines as usize
    }

    /// Instance identity.
    pub fn instance_id(&self) -> &str {
        &self.document.instance_id
    }

    /// Processing time of `job` on `machine`.
    ///
    /// # Panics
    ///
    /// Panics when either index is out of range. Construction fixed the shape, so
    /// an out-of-range index is a caller bug rather than invalid input.
    pub fn processing_time(&self, job: usize, machine: usize) -> u32 {
        self.document.processing_times[machine][job]
    }

    /// Total processing time of one job across every machine.
    ///
    /// Used by the NEH ordering. Returned as `u64` because the sum of bounded
    /// times can exceed a `u32` for the largest supported instances.
    pub fn job_total(&self, job: usize) -> u64 {
        (0..self.machines())
            .map(|machine| u64::from(self.processing_time(job, machine)))
            .sum()
    }

    /// Parse one complete versioned JSON document and validate its shape.
    ///
    /// # Errors
    ///
    /// Returns a document failure for malformed JSON, and whatever
    /// [`FlowShopInstance::new`] returns for a well-formed but invalid document.
    pub fn from_json(bytes: &[u8]) -> Result<Self, ValidationError> {
        let document: FlowShopDocument = serde_json::from_slice(bytes)
            .map_err(|error| ValidationError::new(ErrorKind::Document, error.to_string()))?;
        Self::new(document)
    }

    /// Serialize the validated instance.
    ///
    /// # Errors
    ///
    /// Returns a document failure when serialization fails.
    pub fn to_json(&self) -> Result<String, ValidationError> {
        serde_json::to_string_pretty(&self.document)
            .map_err(|error| ValidationError::new(ErrorKind::Document, error.to_string()))
    }
}
