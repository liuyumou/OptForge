//! Device probing under SPEC-0010 requirements 3, 4 and 9.
//!
//! A probe is the smallest thing that can honestly answer "can this build use this
//! device". It creates a real context, which is what distinguishes it from
//! discovery: discovery asks management tooling what hardware exists and never
//! touches the driver, while a probe asks the driver itself and therefore needs the
//! host lease.
//!
//! Its output is deliberately a record rather than free text. The three facts a
//! caller needs before dispatching work — the driver-read UUID, the compute
//! capability, and whether a code object for it exists — are each a field, so a
//! refusal names which one failed instead of leaving a reader to infer it.

use std::path::Path;
use std::sync::atomic::AtomicBool;
use std::time::Duration;

use serde::Serialize;

use crate::schedule::{KERNEL_NAMES, code_object_path, provisioned, target_capability};
use crate::{Ownership, discover};

/// What a caller asked for regarding the host lease.
///
/// Separate from [`LeaseMode`], which records what actually happened. A caller can
/// ask for [`LeaseRequest::Auto`] and get either, and a report that conflated the
/// two could not say whether an inherited lease was asserted or discovered.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum LeaseRequest {
    /// Consult the wrapper's marker: inherit when it is set, acquire otherwise.
    Auto,
    /// Take the host lock in this process.
    Acquire,
    /// Assert that an ancestor already holds it.
    Inherited,
}

/// How this process came to hold the host lease, as recorded in a probe.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum LeaseMode {
    /// This process took the host lock.
    Acquired,
    /// An ancestor holds it; `tools/gpu_job.sh` is the one that does.
    Inherited,
}

/// What a probe found on one device.
#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct ProbeReport {
    /// The UUID the caller asked for.
    pub requested: String,
    /// The UUID read back from the driver through the context that was created.
    ///
    /// Separate from `requested` on purpose. Equality of the two is the check
    /// requirement 3 makes, and a single field would record the answer without
    /// recording that anything was compared.
    pub observed: String,
    /// Driver-reported model name.
    pub name: String,
    /// Kernel-mode driver version, from management tooling.
    pub driver_version: String,
    /// Compute capability major version.
    pub capability_major: u32,
    /// Compute capability minor version.
    pub capability_minor: u32,
    /// Streaming multiprocessor count.
    pub multiprocessors: u32,
    /// Largest shared memory allocation a single block may opt into, in bytes.
    pub max_shared_memory_per_block: u32,
    /// Free device memory in bytes at the moment of the probe.
    pub free_memory: u64,
    /// Total device memory in bytes.
    pub total_memory: u64,
    /// Whether this build was provisioned with device code objects at all.
    pub provisioned: bool,
    /// Where the code object was looked for.
    pub code_object: String,
    /// Kernels the loaded code object provides, empty when none was loaded.
    pub kernels: Vec<String>,
    /// Compute capability this build's code object targets.
    pub target_capability: String,
    /// How the host lease was obtained.
    pub lease: LeaseMode,
}

/// Everything a probe can refuse for, each distinguishable from the others.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum ProbeError {
    /// The host lease could not be taken, so no context may be created.
    Lease(String),
    /// Management tooling reported no usable inventory.
    Discovery(String),
    /// No visible device carries the requested UUID.
    NotFound(String),
    /// The driver reported a different device than the one requested.
    Mismatch {
        /// What the caller asked for.
        requested: String,
        /// What the driver reported.
        observed: String,
    },
    /// The driver or a driver call failed.
    Device(String),
    /// A code object exists but does not provide a kernel this build expects.
    KernelMissing(String),
}

impl std::fmt::Display for ProbeError {
    fn fmt(&self, formatter: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::Lease(detail) => write!(formatter, "host lease unavailable: {detail}"),
            Self::Discovery(detail) => write!(formatter, "device discovery failed: {detail}"),
            Self::NotFound(uuid) => write!(formatter, "no device with UUID {uuid}"),
            Self::Mismatch {
                requested,
                observed,
            } => write!(
                formatter,
                "requested device {requested} but the driver reported {observed}"
            ),
            Self::Device(detail) => write!(formatter, "{detail}"),
            Self::KernelMissing(name) => {
                write!(formatter, "code object does not provide kernel {name}")
            }
        }
    }
}

impl std::error::Error for ProbeError {}

/// Probe `uuid`, holding the host lease for the whole of it.
///
/// The lease is taken before the context and released after it, which is
/// requirements 7 and 10, and is inherited rather than re-acquired when an ancestor
/// holds it, which is requirement 8. Nothing here launches a kernel: loading the
/// module and resolving its entry points is how requirement 4 reports what this
/// build holds without running any of it.
///
/// # Errors
///
/// Returns the [`ProbeError`] that applies. A UUID no device carries and a UUID the
/// driver disagrees with are separate variants, because the first is a caller
/// mistake and the second would be a record claiming hardware the run did not use.
pub fn probe(
    uuid: &str,
    lease_path: &Path,
    timeout: Duration,
    request: LeaseRequest,
) -> Result<ProbeReport, ProbeError> {
    let cancelled = AtomicBool::new(false);
    let ownership = match request {
        LeaseRequest::Auto => Ownership::acquire_or_inherit(lease_path, timeout, &cancelled),
        LeaseRequest::Acquire => {
            crate::GpuLease::acquire(lease_path, timeout, &cancelled).map(Ownership::Acquired)
        }
        LeaseRequest::Inherited => Ok(Ownership::Inherited),
    }
    .map_err(|error| ProbeError::Lease(error.to_string()))?;
    let lease = if ownership.is_inherited() {
        LeaseMode::Inherited
    } else {
        LeaseMode::Acquired
    };

    // Management tooling supplies the driver version, which the driver API does not
    // expose in the same form. Discovery is also what makes a UUID no device carries
    // distinguishable from a driver that refused, since it answers without a context.
    let inventory = match discover() {
        crate::Discovery::Available { devices } => devices,
        crate::Discovery::Unavailable { reason } => return Err(ProbeError::Discovery(reason)),
    };
    let listed = inventory
        .iter()
        .find(|device| device.uuid == uuid)
        .ok_or_else(|| ProbeError::NotFound(uuid.to_string()))?;

    let context = optimizer_cuda_sys::Context::create(uuid).map_err(map_device_error)?;
    let device = context.device();
    if device.uuid != uuid {
        return Err(ProbeError::Mismatch {
            requested: uuid.to_string(),
            observed: device.uuid.clone(),
        });
    }
    let (free_memory, total_memory) = context.memory_info().map_err(map_device_error)?;

    // Load the module and resolve every entry point this build expects. A code
    // object that loads but is missing a kernel is a build mismatch, and finding
    // that out here is the whole reason a probe exists rather than a first launch
    // discovering it.
    let path = code_object_path();
    let mut kernels = Vec::new();
    if path.is_file() {
        let module = context.load_module_file(&path).map_err(map_device_error)?;
        for name in KERNEL_NAMES {
            module
                .function(name)
                .map_err(|_| ProbeError::KernelMissing(name.to_string()))?;
            kernels.push(name.to_string());
        }
    }

    let (major, minor) = target_capability();
    let report = ProbeReport {
        requested: uuid.to_string(),
        observed: device.uuid.clone(),
        name: device.name.clone(),
        driver_version: listed.driver_version.clone(),
        capability_major: device.capability_major,
        capability_minor: device.capability_minor,
        multiprocessors: device.multiprocessors,
        max_shared_memory_per_block: device.max_shared_memory_per_block,
        free_memory,
        total_memory,
        provisioned: provisioned(),
        code_object: path.display().to_string(),
        kernels,
        target_capability: format!("{major}.{minor}"),
        lease,
    };

    // Requirement 10: the context is destroyed before the lease is released, so a
    // second holder cannot create one while this one still owns device memory.
    drop(context);
    drop(ownership);
    Ok(report)
}

fn map_device_error(error: optimizer_cuda_sys::DeviceError) -> ProbeError {
    match error {
        optimizer_cuda_sys::DeviceError::DeviceNotFound(uuid) => ProbeError::NotFound(uuid),
        optimizer_cuda_sys::DeviceError::DeviceMismatch { requested, found } => {
            ProbeError::Mismatch {
                requested,
                observed: found,
            }
        }
        other => ProbeError::Device(other.to_string()),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn every_refusal_reads_differently() {
        // A probe has six ways to fail and a caller acts differently on each, so a
        // shared message would be the same defect as a catch-all status arm.
        let messages = [
            ProbeError::Lease("timed out".into()).to_string(),
            ProbeError::Discovery("nvidia-smi absent".into()).to_string(),
            ProbeError::NotFound("GPU-a".into()).to_string(),
            ProbeError::Mismatch {
                requested: "GPU-a".into(),
                observed: "GPU-b".into(),
            }
            .to_string(),
            ProbeError::Device("driver error".into()).to_string(),
            ProbeError::KernelMissing("makespan_batch".into()).to_string(),
        ];
        let distinct: std::collections::BTreeSet<&String> = messages.iter().collect();
        assert_eq!(distinct.len(), messages.len(), "{messages:?}");
    }

    #[test]
    fn a_mismatch_names_both_devices() {
        // Requirement 3's refusal is only useful if it says what was asked for and
        // what answered; naming one would leave a reader unable to tell which.
        let message = ProbeError::Mismatch {
            requested: "GPU-aaa".into(),
            observed: "GPU-bbb".into(),
        }
        .to_string();
        assert!(message.contains("GPU-aaa"), "{message}");
        assert!(message.contains("GPU-bbb"), "{message}");
    }
}
