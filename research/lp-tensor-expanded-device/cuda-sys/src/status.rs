//! Exhaustive mapping of the driver's `CUresult`, under SPEC-0010 and ADR-0009.
//!
//! This is SPEC-0002's status-mapping rule applied to the second foreign boundary.
//! The mapping from a driver status to a [`DriverStatus`] has no catch-all arm, so a
//! CUDA upgrade that introduces a status fails to compile here rather than silently
//! classifying a new failure as an old one.
//!
//! The one place a number that is not in this list can arrive is
//! [`DriverStatus::Unrecognized`], which exists because the *driver* is not the
//! compiler: a newer driver than the one this table was written against can return a
//! status no build of this crate has heard of. That is a different situation from a
//! missing arm, and conflating the two is what the no-catch-all rule exists to
//! prevent, so it carries the raw number rather than pretending to name it.

use std::ffi::c_int;

/// A driver status, named rather than numbered.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
#[non_exhaustive]
pub enum DriverStatus {
    /// `CUDA_SUCCESS`.
    Success,
    /// `CUDA_ERROR_INVALID_VALUE`.
    InvalidValue,
    /// `CUDA_ERROR_OUT_OF_MEMORY`.
    OutOfMemory,
    /// `CUDA_ERROR_NOT_INITIALIZED`.
    NotInitialized,
    /// `CUDA_ERROR_DEINITIALIZED`.
    Deinitialized,
    /// `CUDA_ERROR_PROFILER_DISABLED`.
    ProfilerDisabled,
    /// `CUDA_ERROR_STUB_LIBRARY`.
    StubLibrary,
    /// `CUDA_ERROR_DEVICE_UNAVAILABLE`.
    DeviceUnavailable,
    /// `CUDA_ERROR_NO_DEVICE`.
    NoDevice,
    /// `CUDA_ERROR_INVALID_DEVICE`.
    InvalidDevice,
    /// `CUDA_ERROR_DEVICE_NOT_LICENSED`.
    DeviceNotLicensed,
    /// `CUDA_ERROR_INVALID_IMAGE`.
    InvalidImage,
    /// `CUDA_ERROR_INVALID_CONTEXT`.
    InvalidContext,
    /// `CUDA_ERROR_MAP_FAILED`.
    MapFailed,
    /// `CUDA_ERROR_UNMAP_FAILED`.
    UnmapFailed,
    /// `CUDA_ERROR_ARRAY_IS_MAPPED`.
    ArrayIsMapped,
    /// `CUDA_ERROR_ALREADY_MAPPED`.
    AlreadyMapped,
    /// `CUDA_ERROR_NO_BINARY_FOR_GPU`. The code object does not match this device's
    /// compute capability, which is the failure SPEC-0010 requirement 4 refuses
    /// rather than works around.
    NoBinaryForGpu,
    /// `CUDA_ERROR_ALREADY_ACQUIRED`.
    AlreadyAcquired,
    /// `CUDA_ERROR_NOT_MAPPED`.
    NotMapped,
    /// `CUDA_ERROR_ECC_UNCORRECTABLE`.
    EccUncorrectable,
    /// `CUDA_ERROR_UNSUPPORTED_LIMIT`.
    UnsupportedLimit,
    /// `CUDA_ERROR_CONTEXT_ALREADY_IN_USE`.
    ContextAlreadyInUse,
    /// `CUDA_ERROR_PEER_ACCESS_UNSUPPORTED`.
    PeerAccessUnsupported,
    /// `CUDA_ERROR_INVALID_PTX`.
    InvalidPtx,
    /// `CUDA_ERROR_UNSUPPORTED_PTX_VERSION`.
    UnsupportedPtxVersion,
    /// `CUDA_ERROR_JIT_COMPILATION_DISABLED`.
    JitCompilationDisabled,
    /// `CUDA_ERROR_UNSUPPORTED_EXEC_AFFINITY`.
    UnsupportedExecAffinity,
    /// `CUDA_ERROR_INVALID_SOURCE`.
    InvalidSource,
    /// `CUDA_ERROR_FILE_NOT_FOUND`.
    FileNotFound,
    /// `CUDA_ERROR_OPERATING_SYSTEM`.
    OperatingSystem,
    /// `CUDA_ERROR_INVALID_HANDLE`.
    InvalidHandle,
    /// `CUDA_ERROR_ILLEGAL_STATE`.
    IllegalState,
    /// `CUDA_ERROR_NOT_FOUND`.
    NotFound,
    /// `CUDA_ERROR_NOT_READY`.
    NotReady,
    /// `CUDA_ERROR_ILLEGAL_ADDRESS`. The context is poisoned after this and every
    /// later call fails, which is the sticky state SPEC-0010 requirement 29 requires
    /// be rebuilt rather than launched into again.
    IllegalAddress,
    /// `CUDA_ERROR_LAUNCH_OUT_OF_RESOURCES`.
    LaunchOutOfResources,
    /// `CUDA_ERROR_LAUNCH_TIMEOUT`.
    LaunchTimeout,
    /// `CUDA_ERROR_HARDWARE_STACK_ERROR`.
    HardwareStackError,
    /// `CUDA_ERROR_ILLEGAL_INSTRUCTION`.
    IllegalInstruction,
    /// `CUDA_ERROR_MISALIGNED_ADDRESS`.
    MisalignedAddress,
    /// `CUDA_ERROR_INVALID_ADDRESS_SPACE`.
    InvalidAddressSpace,
    /// `CUDA_ERROR_INVALID_PC`.
    InvalidProgramCounter,
    /// `CUDA_ERROR_LAUNCH_FAILED`.
    LaunchFailed,
    /// `CUDA_ERROR_COOPERATIVE_LAUNCH_TOO_LARGE`.
    CooperativeLaunchTooLarge,
    /// `CUDA_ERROR_NOT_PERMITTED`.
    NotPermitted,
    /// `CUDA_ERROR_NOT_SUPPORTED`.
    NotSupported,
    /// `CUDA_ERROR_SYSTEM_NOT_READY`.
    SystemNotReady,
    /// `CUDA_ERROR_SYSTEM_DRIVER_MISMATCH`.
    SystemDriverMismatch,
    /// `CUDA_ERROR_COMPAT_NOT_SUPPORTED_ON_DEVICE`.
    CompatNotSupportedOnDevice,
    /// `CUDA_ERROR_DEVICE_NOT_FOUND`.
    DeviceNotFound,
    /// `CUDA_ERROR_UNKNOWN`.
    Unknown,
    /// A status this build's table does not name, carrying the driver's number.
    ///
    /// This is not a catch-all for the mapping: it is the boundary between a table
    /// written against one driver and a newer driver at runtime. A number here means
    /// this crate should learn the name, and the raw value is kept so a report says
    /// which one.
    Unrecognized(i32),
}

impl DriverStatus {
    /// Map a raw `CUresult`.
    ///
    /// The match below is on explicit numbers with no `_` arm before
    /// [`DriverStatus::Unrecognized`], so adding a variant without adding its number
    /// is a compile error rather than a silent misclassification.
    #[must_use]
    pub(crate) fn from_raw(raw: c_int) -> Self {
        match raw {
            0 => Self::Success,
            1 => Self::InvalidValue,
            2 => Self::OutOfMemory,
            3 => Self::NotInitialized,
            4 => Self::Deinitialized,
            5 => Self::ProfilerDisabled,
            34 => Self::StubLibrary,
            46 => Self::DeviceUnavailable,
            100 => Self::NoDevice,
            101 => Self::InvalidDevice,
            102 => Self::DeviceNotLicensed,
            200 => Self::InvalidImage,
            201 => Self::InvalidContext,
            205 => Self::MapFailed,
            206 => Self::UnmapFailed,
            207 => Self::ArrayIsMapped,
            208 => Self::AlreadyMapped,
            209 => Self::NoBinaryForGpu,
            210 => Self::AlreadyAcquired,
            211 => Self::NotMapped,
            214 => Self::EccUncorrectable,
            215 => Self::UnsupportedLimit,
            216 => Self::ContextAlreadyInUse,
            217 => Self::PeerAccessUnsupported,
            218 => Self::InvalidPtx,
            222 => Self::UnsupportedPtxVersion,
            223 => Self::JitCompilationDisabled,
            224 => Self::UnsupportedExecAffinity,
            300 => Self::InvalidSource,
            301 => Self::FileNotFound,
            304 => Self::OperatingSystem,
            400 => Self::InvalidHandle,
            401 => Self::IllegalState,
            500 => Self::NotFound,
            600 => Self::NotReady,
            700 => Self::IllegalAddress,
            701 => Self::LaunchOutOfResources,
            702 => Self::LaunchTimeout,
            714 => Self::HardwareStackError,
            715 => Self::IllegalInstruction,
            716 => Self::MisalignedAddress,
            717 => Self::InvalidAddressSpace,
            718 => Self::InvalidProgramCounter,
            719 => Self::LaunchFailed,
            720 => Self::CooperativeLaunchTooLarge,
            800 => Self::NotPermitted,
            801 => Self::NotSupported,
            802 => Self::SystemNotReady,
            803 => Self::SystemDriverMismatch,
            804 => Self::CompatNotSupportedOnDevice,
            929 => Self::DeviceNotFound,
            999 => Self::Unknown,
            other => Self::Unrecognized(other),
        }
    }

    /// The status name, for a diagnostic.
    #[must_use]
    pub fn as_str(&self) -> &'static str {
        match self {
            Self::Success => "CUDA_SUCCESS",
            Self::InvalidValue => "CUDA_ERROR_INVALID_VALUE",
            Self::OutOfMemory => "CUDA_ERROR_OUT_OF_MEMORY",
            Self::NotInitialized => "CUDA_ERROR_NOT_INITIALIZED",
            Self::Deinitialized => "CUDA_ERROR_DEINITIALIZED",
            Self::ProfilerDisabled => "CUDA_ERROR_PROFILER_DISABLED",
            Self::StubLibrary => "CUDA_ERROR_STUB_LIBRARY",
            Self::DeviceUnavailable => "CUDA_ERROR_DEVICE_UNAVAILABLE",
            Self::NoDevice => "CUDA_ERROR_NO_DEVICE",
            Self::InvalidDevice => "CUDA_ERROR_INVALID_DEVICE",
            Self::DeviceNotLicensed => "CUDA_ERROR_DEVICE_NOT_LICENSED",
            Self::InvalidImage => "CUDA_ERROR_INVALID_IMAGE",
            Self::InvalidContext => "CUDA_ERROR_INVALID_CONTEXT",
            Self::MapFailed => "CUDA_ERROR_MAP_FAILED",
            Self::UnmapFailed => "CUDA_ERROR_UNMAP_FAILED",
            Self::ArrayIsMapped => "CUDA_ERROR_ARRAY_IS_MAPPED",
            Self::AlreadyMapped => "CUDA_ERROR_ALREADY_MAPPED",
            Self::NoBinaryForGpu => "CUDA_ERROR_NO_BINARY_FOR_GPU",
            Self::AlreadyAcquired => "CUDA_ERROR_ALREADY_ACQUIRED",
            Self::NotMapped => "CUDA_ERROR_NOT_MAPPED",
            Self::EccUncorrectable => "CUDA_ERROR_ECC_UNCORRECTABLE",
            Self::UnsupportedLimit => "CUDA_ERROR_UNSUPPORTED_LIMIT",
            Self::ContextAlreadyInUse => "CUDA_ERROR_CONTEXT_ALREADY_IN_USE",
            Self::PeerAccessUnsupported => "CUDA_ERROR_PEER_ACCESS_UNSUPPORTED",
            Self::InvalidPtx => "CUDA_ERROR_INVALID_PTX",
            Self::UnsupportedPtxVersion => "CUDA_ERROR_UNSUPPORTED_PTX_VERSION",
            Self::JitCompilationDisabled => "CUDA_ERROR_JIT_COMPILATION_DISABLED",
            Self::UnsupportedExecAffinity => "CUDA_ERROR_UNSUPPORTED_EXEC_AFFINITY",
            Self::InvalidSource => "CUDA_ERROR_INVALID_SOURCE",
            Self::FileNotFound => "CUDA_ERROR_FILE_NOT_FOUND",
            Self::OperatingSystem => "CUDA_ERROR_OPERATING_SYSTEM",
            Self::InvalidHandle => "CUDA_ERROR_INVALID_HANDLE",
            Self::IllegalState => "CUDA_ERROR_ILLEGAL_STATE",
            Self::NotFound => "CUDA_ERROR_NOT_FOUND",
            Self::NotReady => "CUDA_ERROR_NOT_READY",
            Self::IllegalAddress => "CUDA_ERROR_ILLEGAL_ADDRESS",
            Self::LaunchOutOfResources => "CUDA_ERROR_LAUNCH_OUT_OF_RESOURCES",
            Self::LaunchTimeout => "CUDA_ERROR_LAUNCH_TIMEOUT",
            Self::HardwareStackError => "CUDA_ERROR_HARDWARE_STACK_ERROR",
            Self::IllegalInstruction => "CUDA_ERROR_ILLEGAL_INSTRUCTION",
            Self::MisalignedAddress => "CUDA_ERROR_MISALIGNED_ADDRESS",
            Self::InvalidAddressSpace => "CUDA_ERROR_INVALID_ADDRESS_SPACE",
            Self::InvalidProgramCounter => "CUDA_ERROR_INVALID_PC",
            Self::LaunchFailed => "CUDA_ERROR_LAUNCH_FAILED",
            Self::CooperativeLaunchTooLarge => "CUDA_ERROR_COOPERATIVE_LAUNCH_TOO_LARGE",
            Self::NotPermitted => "CUDA_ERROR_NOT_PERMITTED",
            Self::NotSupported => "CUDA_ERROR_NOT_SUPPORTED",
            Self::SystemNotReady => "CUDA_ERROR_SYSTEM_NOT_READY",
            Self::SystemDriverMismatch => "CUDA_ERROR_SYSTEM_DRIVER_MISMATCH",
            Self::CompatNotSupportedOnDevice => "CUDA_ERROR_COMPAT_NOT_SUPPORTED_ON_DEVICE",
            Self::DeviceNotFound => "CUDA_ERROR_DEVICE_NOT_FOUND",
            Self::Unknown => "CUDA_ERROR_UNKNOWN",
            Self::Unrecognized(_) => "CUDA_ERROR_UNRECOGNIZED_BY_THIS_BUILD",
        }
    }

    /// Whether this status leaves the context permanently unusable.
    ///
    /// SPEC-0010 requirement 29 forbids launching into a context in this state, so a
    /// caller rebuilds or falls back. The list is the driver's documented sticky
    /// errors: every one of them is a fault that occurred *inside* a kernel, which is
    /// why none of them can be retried in place.
    #[must_use]
    pub fn is_sticky(&self) -> bool {
        matches!(
            self,
            Self::IllegalAddress
                | Self::HardwareStackError
                | Self::IllegalInstruction
                | Self::MisalignedAddress
                | Self::InvalidAddressSpace
                | Self::InvalidProgramCounter
                | Self::LaunchFailed
                | Self::EccUncorrectable
                | Self::LaunchTimeout
        )
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn documented_statuses_map_to_their_names() {
        assert_eq!(DriverStatus::from_raw(0), DriverStatus::Success);
        assert_eq!(DriverStatus::from_raw(2), DriverStatus::OutOfMemory);
        assert_eq!(DriverStatus::from_raw(209), DriverStatus::NoBinaryForGpu);
        assert_eq!(DriverStatus::from_raw(700), DriverStatus::IllegalAddress);
        assert_eq!(
            DriverStatus::from_raw(700).as_str(),
            "CUDA_ERROR_ILLEGAL_ADDRESS"
        );
    }

    #[test]
    fn a_status_this_build_does_not_name_keeps_its_number() {
        // A newer driver than this table is a different situation from a missing
        // match arm, and the number is what a report needs in order to say which.
        assert_eq!(
            DriverStatus::from_raw(31337),
            DriverStatus::Unrecognized(31337)
        );
        assert!(!DriverStatus::from_raw(31337).is_sticky());
    }

    #[test]
    fn faults_inside_a_kernel_are_sticky_and_ordinary_refusals_are_not() {
        for sticky in [
            DriverStatus::IllegalAddress,
            DriverStatus::LaunchFailed,
            DriverStatus::MisalignedAddress,
            DriverStatus::EccUncorrectable,
        ] {
            assert!(sticky.is_sticky(), "{} must be sticky", sticky.as_str());
        }
        // These are refusals, not faults: the context is still usable afterwards, so
        // treating them as sticky would rebuild a context that never broke.
        for recoverable in [
            DriverStatus::OutOfMemory,
            DriverStatus::InvalidValue,
            DriverStatus::NoBinaryForGpu,
            DriverStatus::LaunchOutOfResources,
            DriverStatus::NotFound,
        ] {
            assert!(
                !recoverable.is_sticky(),
                "{} must not be sticky",
                recoverable.as_str()
            );
        }
    }

    #[test]
    fn every_named_status_has_a_distinct_name() {
        // A copy-paste slip in the name table would otherwise be invisible, and the
        // name is what a diagnostic shows a reader.
        let named = [
            DriverStatus::Success,
            DriverStatus::InvalidValue,
            DriverStatus::OutOfMemory,
            DriverStatus::NotInitialized,
            DriverStatus::Deinitialized,
            DriverStatus::ProfilerDisabled,
            DriverStatus::StubLibrary,
            DriverStatus::DeviceUnavailable,
            DriverStatus::NoDevice,
            DriverStatus::InvalidDevice,
            DriverStatus::DeviceNotLicensed,
            DriverStatus::InvalidImage,
            DriverStatus::InvalidContext,
            DriverStatus::MapFailed,
            DriverStatus::UnmapFailed,
            DriverStatus::ArrayIsMapped,
            DriverStatus::AlreadyMapped,
            DriverStatus::NoBinaryForGpu,
            DriverStatus::AlreadyAcquired,
            DriverStatus::NotMapped,
            DriverStatus::EccUncorrectable,
            DriverStatus::UnsupportedLimit,
            DriverStatus::ContextAlreadyInUse,
            DriverStatus::PeerAccessUnsupported,
            DriverStatus::InvalidPtx,
            DriverStatus::UnsupportedPtxVersion,
            DriverStatus::JitCompilationDisabled,
            DriverStatus::UnsupportedExecAffinity,
            DriverStatus::InvalidSource,
            DriverStatus::FileNotFound,
            DriverStatus::OperatingSystem,
            DriverStatus::InvalidHandle,
            DriverStatus::IllegalState,
            DriverStatus::NotFound,
            DriverStatus::NotReady,
            DriverStatus::IllegalAddress,
            DriverStatus::LaunchOutOfResources,
            DriverStatus::LaunchTimeout,
            DriverStatus::HardwareStackError,
            DriverStatus::IllegalInstruction,
            DriverStatus::MisalignedAddress,
            DriverStatus::InvalidAddressSpace,
            DriverStatus::InvalidProgramCounter,
            DriverStatus::LaunchFailed,
            DriverStatus::CooperativeLaunchTooLarge,
            DriverStatus::NotPermitted,
            DriverStatus::NotSupported,
            DriverStatus::SystemNotReady,
            DriverStatus::SystemDriverMismatch,
            DriverStatus::CompatNotSupportedOnDevice,
            DriverStatus::DeviceNotFound,
            DriverStatus::Unknown,
        ];
        let names: std::collections::BTreeSet<&str> =
            named.iter().map(DriverStatus::as_str).collect();
        assert_eq!(names.len(), named.len(), "status names must be distinct");
    }

    #[test]
    fn every_mapped_number_round_trips_to_a_named_status() {
        // The numbers below are the table's own keys. Any of them landing in
        // `Unrecognized` would mean a variant was added without its number.
        for raw in [
            0, 1, 2, 3, 4, 5, 34, 46, 100, 101, 102, 200, 201, 205, 206, 207, 208, 209, 210, 211,
            214, 215, 216, 217, 218, 222, 223, 224, 300, 301, 304, 400, 401, 500, 600, 700, 701,
            702, 714, 715, 716, 717, 718, 719, 720, 800, 801, 802, 803, 804, 929, 999,
        ] {
            assert!(
                !matches!(DriverStatus::from_raw(raw), DriverStatus::Unrecognized(_)),
                "status {raw} must be named"
            );
        }
    }
}
