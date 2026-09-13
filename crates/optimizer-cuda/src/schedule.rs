//! Batched schedule evaluation on a device, under SPEC-0010.
//!
//! This module is safe Rust. It reaches the device only through
//! `optimizer-cuda-sys`, so the crate every GPU consumer already depends on keeps
//! `unsafe_code = "forbid"`; ADR-0009 confines the boundary to the other crate.
//!
//! A [`ScheduleResidency`] uploads an instance once and reuses it, which is
//! requirement 16 expressed in the type rather than only in prose: there is no way
//! to evaluate a batch without first opening a residency, and no method re-sends the
//! processing times.
//!
//! Nothing here holds mathematical authority. The makespans it returns are checked
//! against the host recurrence by the caller's contracts, and a candidate built from
//! them is validated against the original model like any other.

use std::path::{Path, PathBuf};

use optimizer_cuda_sys::{
    Argument, Context, DeviceBuffer, DeviceError, LaunchConfig, Module, Stream, launch,
};

/// Threads per block for the batch kernel. Chosen so a block's staged processing
/// times and its 31 registers a thread both stay inside what compute capability
/// 12.0 allows, rather than tuned against a measurement that does not exist yet.
const BATCH_BLOCK: u32 = 256;

/// Threads per block for the neighborhood kernel. This is fixed in the kernel too,
/// because its reduction arrays are sized by it, and a mismatch between the two
/// would show up as a wrong answer rather than a crash.
const NEIGHBORHOOD_BLOCK: u32 = 256;

/// Compute capability this build's cubin targets.
const TARGET_CAPABILITY: (u32, u32) = (12, 0);

/// Where `tools/setup_cuda.sh` wrote its output when this crate was built.
///
/// Absolute, and baked in by the build script rather than resolved at runtime: a
/// relative default would resolve against whatever directory the process was started
/// in, which for `cargo test` is the crate and not the workspace.
const CODE_OBJECT_DIRECTORY: &str = env!("AI_OPTIMIZER_CUDA_DEFAULT_DIR");

/// Locate the device code object this build was provisioned with.
///
/// `AI_OPTIMIZER_CUDA_DIR` overrides the default at runtime as well as at build
/// time, matching how the pinned native library is located. Returning a path rather
/// than reading it keeps the "no code object" case a named refusal under
/// requirement 4.
#[must_use]
pub fn code_object_path() -> PathBuf {
    let directory = std::env::var_os("AI_OPTIMIZER_CUDA_DIR")
        .map_or_else(|| PathBuf::from(CODE_OBJECT_DIRECTORY), PathBuf::from);
    directory.join("schedule_eval.cubin")
}

/// Whether this build was provisioned with device code objects.
///
/// This is the build-time half of availability, decided by the build script. It is
/// deliberately separate from whether a driver is present, because the two are
/// absent for different reasons and a diagnostic that conflated them would send a
/// reader to the wrong place.
#[must_use]
pub const fn provisioned() -> bool {
    cfg!(cuda_native)
}

/// Whether this build can reach a device at all.
///
/// Both halves must hold: a driver must be present and a code object must have been
/// provisioned. Either being absent is an availability failure that requirement 24
/// turns into a fallback, so a caller asks this before taking a lease rather than
/// discovering it afterwards.
#[must_use]
pub fn device_path_available() -> bool {
    optimizer_cuda_sys::driver_available() && code_object_path().is_file()
}

/// An instance resident in device memory, with its kernels loaded.
///
/// The lifetime ties every device allocation to the context that owns it, so a
/// program that dropped the context while a buffer was live would not compile.
pub struct ScheduleResidency<'context> {
    context: &'context Context,
    module: Module<'context>,
    stream: Stream<'context>,
    times: DeviceBuffer<'context, u32>,
    jobs: usize,
    machines: usize,
    /// Counts uploads of instance-invariant data. Requirement 16 says this must be
    /// one per residency, and a counter is how a test asserts that without timing.
    uploads: usize,
}

/// Why a device path declined, separately from why it failed.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Decline {
    /// The instance's own makespan bound does not fit the kernel's arithmetic.
    /// Requirement 13: decided from the instance, never from a result.
    ArithmeticRange {
        /// Sum of every processing time, which bounds every makespan.
        bound: u64,
    },
    /// The instance needs more shared memory per block than the device allows.
    SharedMemory {
        /// Bytes the kernel would need.
        needed: u32,
        /// Bytes the device permits.
        available: u32,
    },
    /// The device's compute capability is older than this build's code object.
    Capability {
        /// What the device reports.
        found: (u32, u32),
        /// What this build targets.
        target: (u32, u32),
    },
    /// The job count exceeds what the sequence encoding can address.
    JobCount {
        /// Jobs in the instance.
        jobs: usize,
    },
}

impl std::fmt::Display for Decline {
    fn fmt(&self, formatter: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::ArithmeticRange { bound } => write!(
                formatter,
                "instance makespan bound {bound} exceeds the kernel's 32-bit range"
            ),
            Self::SharedMemory { needed, available } => write!(
                formatter,
                "kernel needs {needed} bytes of shared memory per block, device allows {available}"
            ),
            Self::Capability { found, target } => write!(
                formatter,
                "device compute capability {}.{} is older than this build's {}.{} code object",
                found.0, found.1, target.0, target.1
            ),
            Self::JobCount { jobs } => {
                write!(
                    formatter,
                    "{jobs} jobs exceeds the sequence encoding's range"
                )
            }
        }
    }
}

/// The shape an instance must have for the device path to be attempted.
///
/// Deliberately a plain struct rather than a borrow of `FlowShopInstance`: this
/// crate does not depend on the scheduling crate, so the device layer stays
/// independent of the application that first uses it.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct InstanceShape {
    /// Job count.
    pub jobs: usize,
    /// Machine count.
    pub machines: usize,
    /// Sum of every processing time, which bounds every makespan.
    pub total_processing_time: u64,
}

impl InstanceShape {
    /// Whether a device may be used for this instance, and why not if it may not.
    ///
    /// Every check here is decided from the instance and the device, before any
    /// allocation and before any launch, which is what requirement 13 means by
    /// refusing dispatch rather than detecting a bad result.
    ///
    /// # Errors
    ///
    /// Returns the [`Decline`] that applies, in a fixed order so a caller's
    /// diagnostic does not depend on which check happens to be written first.
    pub fn admissible(
        &self,
        capability: (u32, u32),
        max_shared_memory: u32,
    ) -> Result<(), Decline> {
        if capability < TARGET_CAPABILITY {
            return Err(Decline::Capability {
                found: capability,
                target: TARGET_CAPABILITY,
            });
        }
        if self.jobs > usize::from(u16::MAX) {
            return Err(Decline::JobCount { jobs: self.jobs });
        }
        if self.total_processing_time > u64::from(u32::MAX) {
            return Err(Decline::ArithmeticRange {
                bound: self.total_processing_time,
            });
        }
        let needed = self.neighborhood_shared_bytes();
        if needed > max_shared_memory {
            return Err(Decline::SharedMemory {
                needed,
                available: max_shared_memory,
            });
        }
        Ok(())
    }

    /// Dynamic shared memory the neighborhood kernel needs: a head table and a tail
    /// table, each `jobs * machines` 32-bit entries.
    ///
    /// This is the number that forces 32-bit arithmetic. At 500 jobs and 20 machines
    /// it is 80,000 bytes, inside the 99 KB a block may address at compute
    /// capability 12.0; the same tables in 64-bit would be 160,000 and would not fit
    /// on any block of this hardware.
    #[must_use]
    pub fn neighborhood_shared_bytes(&self) -> u32 {
        u32::try_from(2 * self.jobs * self.machines * size_of::<u32>()).unwrap_or(u32::MAX)
    }

    /// Dynamic shared memory the batch kernel needs to stage the processing times.
    #[must_use]
    pub fn batch_shared_bytes(&self) -> u32 {
        u32::try_from(self.jobs * self.machines * size_of::<u32>()).unwrap_or(u32::MAX)
    }
}

impl<'context> ScheduleResidency<'context> {
    /// Upload an instance and load the kernels.
    ///
    /// `times` is machine-major, `times[machine * jobs + job]`, matching the
    /// instance document so no transpose happens on either side.
    ///
    /// # Errors
    ///
    /// Returns [`DeviceError::Unsupported`] when the shape is inadmissible, naming
    /// the [`Decline`], and an availability failure when the device refuses.
    pub fn open(
        context: &'context Context,
        shape: InstanceShape,
        times: &[u32],
        code_object: &Path,
    ) -> Result<Self, DeviceError> {
        let device = context.device();
        shape
            .admissible(
                (device.capability_major, device.capability_minor),
                device.max_shared_memory_per_block,
            )
            .map_err(|decline| DeviceError::Unsupported(decline.to_string()))?;
        if times.len() != shape.jobs * shape.machines {
            return Err(DeviceError::Unsupported(format!(
                "processing times have {} entries, expected {}",
                times.len(),
                shape.jobs * shape.machines
            )));
        }

        let module = context.load_module_file(code_object)?;
        let stream = context.stream()?;
        let mut resident = context.allocate::<u32>(times.len())?;
        resident.copy_from(times, &stream)?;

        Ok(Self {
            context,
            module,
            stream,
            times: resident,
            jobs: shape.jobs,
            machines: shape.machines,
            uploads: 1,
        })
    }

    /// How many times instance-invariant data has been uploaded.
    ///
    /// One, for the life of the residency. Exposed so requirement 16 is asserted
    /// against a counter rather than against elapsed time, which would make the test
    /// a measurement.
    #[must_use]
    pub fn uploads(&self) -> usize {
        self.uploads
    }

    /// Makespan of every permutation in `sequences`, which holds `batch * jobs`
    /// entries in permutation order.
    ///
    /// # Errors
    ///
    /// Returns [`DeviceError::Unsupported`] for a malformed batch and an
    /// availability failure when the device refuses or a launch faults.
    pub fn makespans(&self, sequences: &[u16]) -> Result<Vec<u32>, DeviceError> {
        if self.jobs == 0 || !sequences.len().is_multiple_of(self.jobs) {
            return Err(DeviceError::Unsupported(format!(
                "{} sequence entries is not a whole number of {}-job permutations",
                sequences.len(),
                self.jobs
            )));
        }
        let batch = sequences.len() / self.jobs;
        if batch == 0 {
            return Ok(Vec::new());
        }

        let function = self.module.function("makespan_batch")?;
        let shape = self.shape();
        let shared = shape.batch_shared_bytes();
        if shared > 48 * 1024 {
            function.set_max_dynamic_shared_memory(shared)?;
        }

        let mut device_sequences = self.allocate_u16(sequences.len())?;
        device_sequences.copy_from(sequences, &self.stream)?;
        let device_makespans = self.allocate_u32(batch)?;

        let grid = batch.div_ceil(BATCH_BLOCK as usize);
        launch(
            &function,
            LaunchConfig {
                grid: u32::try_from(grid).map_err(|_| {
                    DeviceError::Unsupported("batch exceeds the grid dimension".into())
                })?,
                block: BATCH_BLOCK,
                shared_memory: shared,
            },
            &[
                Argument::DevicePtr(self.times.as_device_ptr()),
                Argument::DevicePtr(device_sequences.as_device_ptr()),
                Argument::DevicePtr(device_makespans.as_device_ptr()),
                Argument::U32(u32::try_from(self.jobs).unwrap_or(u32::MAX)),
                Argument::U32(u32::try_from(self.machines).unwrap_or(u32::MAX)),
                Argument::U32(u32::try_from(batch).unwrap_or(u32::MAX)),
            ],
            &self.stream,
        )?;

        let mut makespans = vec![0u32; batch];
        device_makespans.copy_to(&mut makespans, &self.stream)?;
        Ok(makespans)
    }

    /// For every job, the cost and position of its best reinsertion into
    /// `sequence`, with that job removed first.
    ///
    /// Returns one pair per job, indexed by job. Choosing among them is the caller's
    /// decision and stays on the host, which keeps the tie-break in one place.
    ///
    /// # Errors
    ///
    /// Returns [`DeviceError::Unsupported`] when `sequence` is not a permutation of
    /// the resident instance's jobs, and an availability failure otherwise.
    pub fn insertion_neighborhood(&self, sequence: &[u16]) -> Result<Vec<(u32, u32)>, DeviceError> {
        if sequence.len() != self.jobs {
            return Err(DeviceError::Unsupported(format!(
                "sequence has {} entries, expected {}",
                sequence.len(),
                self.jobs
            )));
        }

        let function = self.module.function("insertion_neighborhood")?;
        let shared = self.shape().neighborhood_shared_bytes();
        if shared > 48 * 1024 {
            function.set_max_dynamic_shared_memory(shared)?;
        }

        let mut device_sequence = self.allocate_u16(sequence.len())?;
        device_sequence.copy_from(sequence, &self.stream)?;
        let device_cost = self.allocate_u32(self.jobs)?;
        let device_position = self.allocate_u32(self.jobs)?;

        launch(
            &function,
            LaunchConfig {
                grid: u32::try_from(self.jobs).unwrap_or(u32::MAX),
                block: NEIGHBORHOOD_BLOCK,
                shared_memory: shared,
            },
            &[
                Argument::DevicePtr(self.times.as_device_ptr()),
                Argument::DevicePtr(device_sequence.as_device_ptr()),
                Argument::DevicePtr(device_cost.as_device_ptr()),
                Argument::DevicePtr(device_position.as_device_ptr()),
                Argument::U32(u32::try_from(self.jobs).unwrap_or(u32::MAX)),
                Argument::U32(u32::try_from(self.machines).unwrap_or(u32::MAX)),
            ],
            &self.stream,
        )?;

        let mut costs = vec![0u32; self.jobs];
        let mut positions = vec![0u32; self.jobs];
        device_cost.copy_to(&mut costs, &self.stream)?;
        device_position.copy_to(&mut positions, &self.stream)?;
        Ok(costs.into_iter().zip(positions).collect())
    }

    fn shape(&self) -> InstanceShape {
        InstanceShape {
            jobs: self.jobs,
            machines: self.machines,
            // Not consulted by the byte-size helpers, and the residency only exists
            // because `open` already found the real bound admissible.
            total_processing_time: 0,
        }
    }

    fn allocate_u32(&self, count: usize) -> Result<DeviceBuffer<'context, u32>, DeviceError> {
        self.context.allocate::<u32>(count)
    }

    fn allocate_u16(&self, count: usize) -> Result<DeviceBuffer<'context, u16>, DeviceError> {
        self.context.allocate::<u16>(count)
    }
}

/// Kernel and function names this build expects a code object to export.
///
/// Exposed so a probe can report what it looked for when a module fails to provide
/// one, which is requirement 4's "report the code objects it holds".
pub const KERNEL_NAMES: [&str; 2] = ["makespan_batch", "insertion_neighborhood"];

/// The compute capability this build's cubin targets.
#[must_use]
pub fn target_capability() -> (u32, u32) {
    TARGET_CAPABILITY
}

#[cfg(test)]
mod tests {
    use super::*;

    fn shape(jobs: usize, machines: usize, total: u64) -> InstanceShape {
        InstanceShape {
            jobs,
            machines,
            total_processing_time: total,
        }
    }

    #[test]
    fn the_largest_supported_instance_fits_the_capability_shared_memory_limit() {
        // 500 jobs by 20 machines is the document limit, and this is the arithmetic
        // that forces 32-bit tables: the same tables in 64 bits would not fit on any
        // block of this hardware.
        let largest = shape(500, 20, 500 * 20 * 99);
        assert_eq!(largest.neighborhood_shared_bytes(), 80_000);
        assert!(largest.neighborhood_shared_bytes() < 99 * 1024);
        assert!(largest.neighborhood_shared_bytes() * 2 > 99 * 1024);
        largest
            .admissible((12, 0), 99 * 1024)
            .expect("the largest supported instance must be admissible");
    }

    #[test]
    fn an_instance_whose_bound_exceeds_the_kernel_range_is_declined() {
        let overflowing = shape(500, 20, u64::from(u32::MAX) + 1);
        assert_eq!(
            overflowing.admissible((12, 0), 99 * 1024),
            Err(Decline::ArithmeticRange {
                bound: u64::from(u32::MAX) + 1
            })
        );
        // And the boundary itself is admissible, so the refusal is a range check
        // rather than a margin someone chose.
        shape(500, 20, u64::from(u32::MAX))
            .admissible((12, 0), 99 * 1024)
            .expect("a bound of exactly u32::MAX still fits");
    }

    #[test]
    fn an_older_capability_is_declined_rather_than_attempted() {
        assert_eq!(
            shape(20, 5, 20 * 5 * 99).admissible((8, 9), 99 * 1024),
            Err(Decline::Capability {
                found: (8, 9),
                target: (12, 0)
            })
        );
        // A newer capability loads the PTX instead, so it is not declined.
        shape(20, 5, 20 * 5 * 99)
            .admissible((13, 0), 99 * 1024)
            .expect("a newer capability must not be declined");
    }

    #[test]
    fn a_device_with_less_shared_memory_is_declined_with_both_numbers() {
        assert_eq!(
            shape(500, 20, 500 * 20 * 99).admissible((12, 0), 48 * 1024),
            Err(Decline::SharedMemory {
                needed: 80_000,
                available: 48 * 1024
            })
        );
    }

    #[test]
    fn checks_are_ordered_so_a_diagnostic_does_not_depend_on_check_order() {
        // An instance failing several checks reports the capability first, because a
        // device that cannot run the code object at all makes the other numbers
        // meaningless.
        let bad = shape(500, 20, u64::from(u32::MAX) + 1);
        assert!(matches!(
            bad.admissible((8, 9), 1024),
            Err(Decline::Capability { .. })
        ));
    }
}
