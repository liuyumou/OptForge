//! A leased, open device for the duration of one run, under SPEC-0010.
//!
//! This is the type that makes "the run holds a device" a thing a caller can pass
//! around rather than a convention. Holding one means, by construction, that the
//! host lease was taken and a context was created on the named device and its
//! identity was read back from the driver. Requirement 35's rule — a `gpu` entry
//! resolves only when a device is selected — is sound precisely because the only
//! way to obtain the UUID that unlocks it is to have done all of that.
//!
//! The lease is released after the context is destroyed, which is requirement 10,
//! and that ordering is a property of the field order below rather than of any
//! caller's discipline.

use std::path::Path;
use std::rc::Rc;
use std::time::Duration;

use optimizer_cuda_sys::{Context, DeviceError, DeviceInfo};

use crate::Ownership;
use crate::schedule::{InstanceShape, ScheduleResidency, code_object_path};

/// Why a device could not be opened for a run.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum SessionError {
    /// The host lease could not be taken.
    Lease(String),
    /// Management tooling reported no usable inventory.
    Discovery(String),
    /// No visible device carries the requested UUID.
    NotFound(String),
    /// Management tooling lists the device but the driver cannot see it.
    ///
    /// Distinct from [`SessionError::NotFound`] because it sends a reader
    /// somewhere else entirely. The UUID is right and the hardware is present;
    /// what is wrong is the process's device visibility, which `CUDA_VISIBLE_DEVICES`
    /// controls and which `tools/gpu_job.sh` sets. Reporting this as "no such
    /// device" would send someone to check a UUID that is already correct.
    HiddenFromDriver(String),
    /// This build has no device code object, so a device cannot be used for work.
    NotProvisioned(String),
    /// The driver or a driver call failed.
    Device(String),
}

impl std::fmt::Display for SessionError {
    fn fmt(&self, formatter: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::Lease(detail) => write!(formatter, "host lease unavailable: {detail}"),
            Self::Discovery(detail) => write!(formatter, "device discovery failed: {detail}"),
            Self::NotFound(uuid) => write!(formatter, "no device with UUID {uuid}"),
            Self::HiddenFromDriver(uuid) => write!(
                formatter,
                "management tooling lists {uuid} but the driver cannot see it; \
                 check CUDA_VISIBLE_DEVICES"
            ),
            Self::NotProvisioned(path) => write!(
                formatter,
                "no device code object at {path}; run bash tools/setup_cuda.sh"
            ),
            Self::Device(detail) => write!(formatter, "{detail}"),
        }
    }
}

impl std::error::Error for SessionError {}

/// UUIDs the driver can actually see from this process, in UUID order.
///
/// Deliberately different from [`crate::discover`], and the difference matters.
/// Discovery asks management tooling what hardware the host has; this asks the
/// driver what this process may use, which `CUDA_VISIBLE_DEVICES` restricts and
/// which `tools/gpu_job.sh` sets to exactly one. A consumer choosing a device must
/// choose from this list: picking from the inventory instead yields a UUID that is
/// real, correct, and unusable here, which is the mistake
/// [`SessionError::HiddenFromDriver`] exists to name.
///
/// This reports what is visible; it does not choose. SPEC-0010 requirement 5 says
/// there is no default device, so selecting one stays the caller's decision.
///
/// # Errors
///
/// Returns a device failure when the driver is absent or a query fails.
pub fn visible_uuids() -> Result<Vec<String>, SessionError> {
    optimizer_cuda_sys::devices()
        .map(|devices| devices.into_iter().map(|device| device.uuid).collect())
        .map_err(|error| SessionError::Device(error.to_string()))
}

/// One device, leased and open, for as long as this value lives.
pub struct DeviceSession {
    // Field order is the drop order, and it is the contract. The context is
    // destroyed before the lease is released, so a second holder cannot create one
    // while this run still owns device memory.
    context: Rc<Context>,
    _lease: Ownership,
    driver_version: String,
}

impl DeviceSession {
    /// Lease the host lock and open `uuid`, refusing rather than falling back.
    ///
    /// Falling back to the CPU here would be wrong even though requirement 24 makes
    /// an availability failure a fallback elsewhere: a caller naming a device has
    /// asked for one, and silently running without it would produce a record whose
    /// configuration names hardware the run never touched.
    ///
    /// # Errors
    ///
    /// Returns the [`SessionError`] that applies, each distinguishable so a
    /// diagnostic sends a reader to the right place.
    pub fn open(uuid: &str, lease_path: &Path, timeout: Duration) -> Result<Self, SessionError> {
        let cancelled = std::sync::atomic::AtomicBool::new(false);
        let lease = Ownership::acquire_or_inherit(lease_path, timeout, &cancelled)
            .map_err(|error| SessionError::Lease(error.to_string()))?;

        // Management tooling is what reports the driver version; the driver API does
        // not expose it in the same form, and SPEC-0007 requirement 9 requires a GPU
        // record to carry it.
        let driver_version = match crate::discover() {
            crate::Discovery::Available { devices } => devices
                .into_iter()
                .find(|device| device.uuid == uuid)
                .map(|device| device.driver_version)
                .ok_or_else(|| SessionError::NotFound(uuid.to_string()))?,
            crate::Discovery::Unavailable { reason } => {
                return Err(SessionError::Discovery(reason));
            }
        };

        let path = code_object_path();
        if !path.is_file() {
            return Err(SessionError::NotProvisioned(path.display().to_string()));
        }

        // Discovery already found this UUID above, so the driver refusing it means
        // the two disagree about visibility rather than that the device is absent.
        let context = Rc::new(Context::create(uuid).map_err(|error| match error {
            DeviceError::DeviceNotFound(uuid) => SessionError::HiddenFromDriver(uuid),
            other => SessionError::Device(other.to_string()),
        })?);
        Ok(Self {
            context,
            _lease: lease,
            driver_version,
        })
    }

    /// The driver-reported UUID of the device this session holds.
    #[must_use]
    pub fn uuid(&self) -> &str {
        &self.context.device().uuid
    }

    /// The driver-reported model name.
    #[must_use]
    pub fn name(&self) -> &str {
        &self.context.device().name
    }

    /// The kernel-mode driver version, from management tooling.
    #[must_use]
    pub fn driver_version(&self) -> &str {
        &self.driver_version
    }

    /// Everything the driver reports about this device.
    #[must_use]
    pub fn device(&self) -> &DeviceInfo {
        self.context.device()
    }

    /// Make an instance resident on this session's device.
    ///
    /// # Errors
    ///
    /// Returns whatever [`ScheduleResidency::open`] returns, which includes the
    /// admissibility refusals decided before any allocation.
    pub fn residency(
        &self,
        shape: InstanceShape,
        times: &[u32],
    ) -> Result<ScheduleResidency, DeviceError> {
        ScheduleResidency::open(Rc::clone(&self.context), shape, times, &code_object_path())
    }
}

impl std::fmt::Debug for DeviceSession {
    fn fmt(&self, formatter: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        formatter
            .debug_struct("DeviceSession")
            .field("uuid", &self.uuid())
            .field("driver_version", &self.driver_version)
            .finish()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn every_refusal_reads_differently() {
        let messages = [
            SessionError::Lease("timed out".into()).to_string(),
            SessionError::Discovery("nvidia-smi absent".into()).to_string(),
            SessionError::NotFound("GPU-a".into()).to_string(),
            SessionError::HiddenFromDriver("GPU-a".into()).to_string(),
            SessionError::NotProvisioned("/tmp/x.cubin".into()).to_string(),
            SessionError::Device("driver error".into()).to_string(),
        ];
        let distinct: std::collections::BTreeSet<&String> = messages.iter().collect();
        assert_eq!(distinct.len(), messages.len(), "{messages:?}");
    }

    /// A device the driver hides is a different problem from one that is absent.
    ///
    /// Both are "the UUID did not resolve" from the caller's side, and they send a
    /// reader to opposite places: one to check the UUID, one to check the
    /// process's device visibility. Collapsing them would make the common
    /// wrapper mistake read as a hardware fault.
    #[test]
    fn a_hidden_device_points_at_visibility_rather_than_at_the_uuid() {
        let hidden = SessionError::HiddenFromDriver("GPU-a".into()).to_string();
        assert!(hidden.contains("CUDA_VISIBLE_DEVICES"), "{hidden}");
        let absent = SessionError::NotFound("GPU-a".into()).to_string();
        assert!(!absent.contains("CUDA_VISIBLE_DEVICES"), "{absent}");
    }

    #[test]
    fn an_unprovisioned_build_names_the_script_that_fixes_it() {
        // A caller who sees this has a device and no code object, which is a
        // provisioning step rather than a hardware problem; the message says which.
        let message = SessionError::NotProvisioned("/x/schedule_eval.cubin".into()).to_string();
        assert!(message.contains("setup_cuda.sh"), "{message}");
    }
}
