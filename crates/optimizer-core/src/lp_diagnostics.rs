//! Opt-in LP observations. Diagnostics never grant mathematical authority.

use serde::{Deserialize, Serialize};
use std::collections::BTreeMap;
use std::time::Instant;

/// Additional observations for the opt-in matched FP64 endpoint-v2 contract.
#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct LpControlDiagnostics {
    /// Versioned shared controller identity.
    pub controller: String,
    /// Logical iteration index at stop.
    pub logical_iterations: u64,
    /// Actual completed physical steps; restoration never reduces it.
    pub physical_iterations: Option<u64>,
    /// Successfully enqueued LP kernels, retained even when pinned fallback executes.
    pub device_kernel_launches: u64,
    /// Actual host endpoint assessments in the backend (excluding independent verification).
    pub assessments: u64,
    /// Actual KKT evaluations steering control, including initialization/restarts.
    pub kkt_evaluations: u64,
    /// Completed restart decisions.
    pub restarts: u64,
    /// Final controller weight.
    pub weight: f64,
    /// Explicit control stop: accepted, iteration_limit, interrupted or time_limit.
    pub stop: String,
}

/// Session phase timings for a repeated-solve batch (SPEC-0014 requirement 24).
///
/// A session's setup phases (device context, module load, preconditioning,
/// research preparation, invariant allocation and upload) and per-solve session
/// phases (variant rebind, engine rebind, bound upload) live here rather than
/// in [`LpDiagnostics::phases_ns`]: the lp-endpoint phase allow-list does not
/// admit them, and per-solve endpoint records keep their existing vocabulary.
/// Batch records serialize this document separately.
#[derive(Clone, Debug, Default, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct SessionSetup {
    /// Cumulative session phase timings in nanoseconds, keyed by phase name.
    pub phases_ns: BTreeMap<String, u64>,
}

impl SessionSetup {
    /// Start a session phase clock. Session phases are always measured: they
    /// are the quantity a batch exists to amortize, so they are not gated on
    /// the profiling flag the endpoint's own phases follow.
    #[must_use]
    pub fn start(&self) -> Instant {
        Instant::now()
    }

    /// Accumulate one completed session phase.
    pub fn finish(&mut self, name: &str, start: Instant) {
        let ns = u64::try_from(start.elapsed().as_nanos()).unwrap_or(u64::MAX);
        let entry = self.phases_ns.entry(name.to_owned()).or_default();
        *entry = entry.saturating_add(ns);
    }
}

/// Data collected by an explicitly observed solve, separately from SolveRecord.
#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct LpDiagnostics {
    /// Adaptive observations serialized only by endpoint v5.
    #[serde(skip)]
    pub adaptive: Option<crate::LpAdaptiveDiagnostics>,
    /// Precision observations belong only to endpoint v4.
    #[serde(skip)]
    pub precision: Option<crate::LpPrecisionDiagnostics>,
    /// Kept out of the legacy wire shape; endpoint v2 serializes this separately.
    #[serde(skip)]
    pub control: Option<LpControlDiagnostics>,
    /// Tuned execution observations serialized separately by endpoint v3.
    #[serde(skip)]
    pub execution: Option<crate::LpExecutionDiagnostics>,
    /// Whether witness collection was requested.
    pub enabled: bool,
    /// Detailed timing is a separate profiling execution.
    pub profile: bool,
    /// Optional explicit LP device-buffer ceiling.
    pub device_buffer_limit_bytes: Option<u64>,
    /// Untrusted multipliers in canonical row order, normalized to minimization.
    pub dual: Option<Vec<f64>>,
    /// Completed algorithm iterations, or unavailable for the native method.
    pub iterations: Option<u64>,
    /// Iteration whose candidate and dual were assessed.
    pub assessment_iteration: Option<u64>,
    /// Completed controller restarts, when applicable.
    pub restarts: Option<u64>,
    /// Successfully enqueued device kernels.
    pub kernel_launches: Option<u64>,
    /// Peak explicitly allocated LP buffers, excluding driver/context allocations.
    pub device_buffer_peak_bytes: Option<u64>,
    /// Cumulative non-overlapping diagnostic phases in nanoseconds.
    pub phases_ns: BTreeMap<String, u64>,
    /// Explicit limits of available observations.
    pub unavailable: Vec<String>,
}

impl LpDiagnostics {
    /// Create an observation sink. Disabled sinks do not retain witnesses/timings.
    #[must_use]
    pub fn new(enabled: bool, profile: bool) -> Self {
        Self {
            adaptive: None,
            precision: None,
            control: None,
            execution: None,
            enabled,
            profile,
            device_buffer_limit_bytes: None,
            dual: None,
            iterations: None,
            assessment_iteration: None,
            restarts: None,
            kernel_launches: None,
            device_buffer_peak_bytes: None,
            phases_ns: BTreeMap::new(),
            unavailable: Vec::new(),
        }
    }

    /// Start a clock only in an explicitly profiled execution.
    #[must_use]
    pub fn start(&self) -> Option<Instant> {
        (self.enabled && self.profile).then(Instant::now)
    }

    /// Accumulate one completed diagnostic phase.
    pub fn finish(&mut self, name: &str, start: Option<Instant>) {
        if let Some(start) = start {
            let ns = u64::try_from(start.elapsed().as_nanos()).unwrap_or(u64::MAX);
            let entry = self.phases_ns.entry(name.to_owned()).or_default();
            *entry = entry.saturating_add(ns);
        }
    }

    /// Retain the witness that corresponds to one candidate assessment.
    pub fn capture(&mut self, dual: &[f64], iteration: u64) {
        if self.enabled {
            self.dual = Some(dual.to_vec());
            self.assessment_iteration = Some(iteration);
        }
    }
}
