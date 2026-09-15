//! Opt-in LP observations. Diagnostics never grant mathematical authority.

use serde::{Deserialize, Serialize};
use std::collections::BTreeMap;
use std::time::Instant;

/// Data collected by an explicitly observed solve, separately from SolveRecord.
#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct LpDiagnostics {
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
