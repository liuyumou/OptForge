//! Device residency for the first-order method, under SPEC-0011 requirements 5
//! to 8 and SPEC-0010's residency and cancellation rules.
//!
//! The matrix, the bounds and the objective are uploaded once and reused for every
//! iteration, which is SPEC-0010 requirement 16 expressed in the type: the upload
//! happens in [`LpResidency::open`] and no later call re-sends it. Only the
//! iterates move after that, and only at a termination check.
//!
//! Everything this module launches is `f64` and every reduction the kernels perform
//! uses the partition and tree defined once in `optimizer_lp::reduce`. The kernels
//! restate neither: a device test asserts the segment size is one number on both
//! sides rather than two that happen to agree today.

use std::cell::Cell;
use std::path::{Path, PathBuf};
use std::rc::Rc;

use optimizer_core::CancellationToken;
use optimizer_cuda_sys::{
    Argument, Context, DeviceBuffer, DeviceError, LaunchConfig, Module, Stream, launch,
};
use optimizer_lp::problem::LinearProgram;
use optimizer_lp::reduce::SEGMENT;

/// Threads per block, matching `BLOCK` in the code object.
const BLOCK: u32 = 256;

/// Iterations launched between host-side cancellation checks.
///
/// Bounded rather than unbounded for the same reason SPEC-0010 requirement 27
/// bounds a batch: the host synchronizes at the end of each chunk, so cancellation
/// latency is one chunk rather than the whole iteration limit. The caller's
/// termination check interval is a separate, larger bound; this one exists so a
/// long interval cannot make cancellation unresponsive.
const ITERATION_CHUNK: u64 = 64;

/// The kernels a code object must export for this residency to run.
pub const KERNEL_NAMES: [&str; 4] = ["spmv_row", "spmv_column", "primal_step", "dual_step"];

/// Why a program cannot run on this device.
///
/// Decided from the program before any allocation, never from a failed one, which
/// is the same shape `InstanceShape::admissible` already uses for the integer
/// evaluator.
#[derive(Clone, Debug, PartialEq, Eq)]
pub enum Decline {
    /// A row or column has more entries than one block's shared memory can stage.
    LineTooWide {
        /// Entries in the widest line.
        widest: usize,
        /// Entries one block can stage.
        capacity: usize,
    },
    /// A line exceeds what two levels of the fixed reduction can cover.
    LineExceedsReduction {
        /// Entries in the widest line.
        widest: usize,
        /// The two-level bound.
        capacity: usize,
    },
    /// The device's compute capability is below the one the code object targets.
    Capability {
        /// What the driver reported.
        found: (u32, u32),
        /// What the code object was built for.
        target: (u32, u32),
    },
    /// The program's device memory requirement exceeds what is free.
    Memory {
        /// Bytes the program needs.
        needed: u64,
        /// Bytes the device reports free.
        available: u64,
    },
}

impl std::fmt::Display for Decline {
    fn fmt(&self, formatter: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::LineTooWide { widest, capacity } => write!(
                formatter,
                "the widest line has {widest} entries and one block can stage {capacity}"
            ),
            Self::LineExceedsReduction { widest, capacity } => write!(
                formatter,
                "the widest line has {widest} entries, above the {capacity} two levels of the \
                 fixed reduction cover"
            ),
            Self::Capability { found, target } => write!(
                formatter,
                "compute capability {}.{} is below the {}.{} this code object targets",
                found.0, found.1, target.0, target.1
            ),
            Self::Memory { needed, available } => write!(
                formatter,
                "the program needs {needed} bytes of device memory and {available} are free"
            ),
        }
    }
}

/// The compute capability the committed code object targets.
pub const TARGET_CAPABILITY: (u32, u32) = (12, 0);

/// What one program requires of a device, known before any allocation.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct Requirement {
    /// Entries in the widest row or column.
    pub widest_line: usize,
    /// Dynamic shared memory one block needs, in bytes.
    pub shared_bytes: u32,
    /// Total device memory the buffers need, in bytes.
    pub memory_bytes: u64,
}

impl Requirement {
    /// What `program` requires.
    ///
    /// Computed from the program's own counts rather than discovered by a failed
    /// allocation, which is what SPEC-0011's Security and Resource Limits section
    /// requires: the requirement is known from the model before the solve begins.
    #[must_use]
    pub fn of(program: &LinearProgram) -> Self {
        let widest_line = (0..program.row_major().lines())
            .map(|line| program.row_major().line(line).0.len())
            .chain(
                (0..program.column_major().lines())
                    .map(|line| program.column_major().line(line).0.len()),
            )
            .max()
            .unwrap_or(0);

        // products + reduction buffer + per-segment partials.
        let doubles = widest_line + SEGMENT + SEGMENT;
        let shared_bytes = u32::try_from(doubles * size_of::<f64>()).unwrap_or(u32::MAX);

        let nonzeros = program.nonzeros() as u64;
        let rows = program.row_count() as u64;
        let columns = program.column_count() as u64;
        let eight = size_of::<f64>() as u64;
        let four = size_of::<u32>() as u64;
        // Two copies of the matrix, plus a constant number of vectors: five of
        // length `columns` and four of length `rows`.
        let memory_bytes = 2 * nonzeros * (eight + four)
            + (rows + columns + 2) * four
            + (5 * columns + 4 * rows) * eight;

        Self {
            widest_line,
            shared_bytes,
            memory_bytes,
        }
    }

    /// Whether a device can run this program.
    ///
    /// # Errors
    ///
    /// Returns the first [`Decline`] that applies, checked in a fixed order with
    /// capability first so a device that cannot load the code object at all is
    /// refused for that reason rather than for a consequence of it.
    pub fn admissible(
        &self,
        capability: (u32, u32),
        max_shared_memory: u32,
        free_memory: u64,
    ) -> Result<(), Decline> {
        if capability < TARGET_CAPABILITY {
            return Err(Decline::Capability {
                found: capability,
                target: TARGET_CAPABILITY,
            });
        }
        if self.widest_line > SEGMENT * SEGMENT {
            return Err(Decline::LineExceedsReduction {
                widest: self.widest_line,
                capacity: SEGMENT * SEGMENT,
            });
        }
        if self.shared_bytes > max_shared_memory {
            let capacity =
                (max_shared_memory as usize / size_of::<f64>()).saturating_sub(2 * SEGMENT);
            return Err(Decline::LineTooWide {
                widest: self.widest_line,
                capacity,
            });
        }
        if self.memory_bytes > free_memory {
            return Err(Decline::Memory {
                needed: self.memory_bytes,
                available: free_memory,
            });
        }
        Ok(())
    }
}

/// Instance-invariant data resident on one device, plus the iterate buffers.
pub struct LpResidency {
    context: Rc<Context>,
    module: Module,
    stream: Stream,
    row_values: DeviceBuffer<f64>,
    row_indices: DeviceBuffer<u32>,
    row_offsets: DeviceBuffer<u32>,
    column_values: DeviceBuffer<f64>,
    column_indices: DeviceBuffer<u32>,
    column_offsets: DeviceBuffer<u32>,
    objective: DeviceBuffer<f64>,
    column_lower: DeviceBuffer<f64>,
    column_upper: DeviceBuffer<f64>,
    row_lower: DeviceBuffer<f64>,
    row_upper: DeviceBuffer<f64>,
    rows: usize,
    columns: usize,
    requirement: Requirement,
    uploads: usize,
    launches: Cell<u64>,
    poisoned: Cell<bool>,
}

/// Where the committed LP code object lives.
#[must_use]
pub fn code_object_path() -> PathBuf {
    let directory = std::env::var("AI_OPTIMIZER_CUDA_DIR")
        .ok()
        .map(PathBuf::from)
        .unwrap_or_else(|| {
            PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../../target/native/cuda")
        });
    directory.join("lp_pdhg.cubin")
}

/// Whether a driver and a code object are both present.
#[must_use]
pub fn device_path_available() -> bool {
    optimizer_cuda_sys::driver_available() && code_object_path().is_file()
}

impl LpResidency {
    /// Upload one program's invariant data and allocate its iterate buffers.
    ///
    /// # Errors
    ///
    /// Returns [`DeviceError::Unsupported`] naming a [`Decline`] when the device
    /// cannot run this program, and an availability failure when the device refuses.
    #[allow(clippy::too_many_arguments)]
    pub fn open(
        context: Rc<Context>,
        program: &LinearProgram,
        scaled_row_values: &[f64],
        scaled_column_values: &[f64],
        scaled_objective: &[f64],
        scaled_row_bounds: (&[f64], &[f64]),
        scaled_column_bounds: (&[f64], &[f64]),
        code_object: &Path,
    ) -> Result<Self, DeviceError> {
        let device = context.device();
        let requirement = Requirement::of(program);
        let (free, _total) = context.memory_info()?;
        requirement
            .admissible(
                (device.capability_major, device.capability_minor),
                device.max_shared_memory_per_block,
                free,
            )
            .map_err(|decline| DeviceError::Unsupported(decline.to_string()))?;

        let module = context.load_module_file(code_object)?;
        let stream = context.stream()?;

        let row_indices_host: Vec<u32> = program.row_major().entries().map(|(_, m, _)| m).collect();
        let column_indices_host: Vec<u32> = program
            .column_major()
            .entries()
            .map(|(_, m, _)| m)
            .collect();
        let row_offsets_host: Vec<u32> = (0..=program.row_count())
            .map(|line| u32::try_from(program.row_major().offset(line)).unwrap_or(u32::MAX))
            .collect();
        let column_offsets_host: Vec<u32> = (0..=program.column_count())
            .map(|line| u32::try_from(program.column_major().offset(line)).unwrap_or(u32::MAX))
            .collect();

        let upload_f64 = |values: &[f64]| -> Result<DeviceBuffer<f64>, DeviceError> {
            let mut buffer = context.allocate::<f64>(values.len().max(1))?;
            if !values.is_empty() {
                buffer.copy_from(values, &stream)?;
            }
            Ok(buffer)
        };
        let upload_u32 = |values: &[u32]| -> Result<DeviceBuffer<u32>, DeviceError> {
            let mut buffer = context.allocate::<u32>(values.len().max(1))?;
            if !values.is_empty() {
                buffer.copy_from(values, &stream)?;
            }
            Ok(buffer)
        };

        Ok(Self {
            row_values: upload_f64(scaled_row_values)?,
            row_indices: upload_u32(&row_indices_host)?,
            row_offsets: upload_u32(&row_offsets_host)?,
            column_values: upload_f64(scaled_column_values)?,
            column_indices: upload_u32(&column_indices_host)?,
            column_offsets: upload_u32(&column_offsets_host)?,
            objective: upload_f64(scaled_objective)?,
            column_lower: upload_f64(scaled_column_bounds.0)?,
            column_upper: upload_f64(scaled_column_bounds.1)?,
            row_lower: upload_f64(scaled_row_bounds.0)?,
            row_upper: upload_f64(scaled_row_bounds.1)?,
            rows: program.row_count(),
            columns: program.column_count(),
            requirement,
            // One upload per residency, counted so requirement 16 is asserted
            // against a counter rather than against elapsed time.
            uploads: 1,
            launches: Cell::new(0),
            poisoned: Cell::new(false),
            module,
            stream,
            context,
        })
    }

    /// How many times invariant data has been uploaded. One, for the life of this.
    #[must_use]
    pub fn uploads(&self) -> usize {
        self.uploads
    }

    /// How many kernel launches this residency has issued.
    #[must_use]
    pub fn launches(&self) -> u64 {
        self.launches.get()
    }

    /// Whether a sticky fault has disabled this residency.
    #[must_use]
    pub fn poisoned(&self) -> bool {
        self.poisoned.get()
    }

    /// What this program required of the device.
    #[must_use]
    pub fn requirement(&self) -> Requirement {
        self.requirement
    }

    /// The device this residency is bound to, for a record that must name it.
    #[must_use]
    pub fn device(&self) -> &optimizer_cuda_sys::DeviceInfo {
        self.context.device()
    }

    fn usable(&self) -> Result<(), DeviceError> {
        if self.poisoned.get() {
            return Err(DeviceError::ContextPoisoned(
                optimizer_cuda_sys::DriverStatus::LaunchFailed,
            ));
        }
        Ok(())
    }

    fn observe(&self, error: DeviceError) -> DeviceError {
        if error.poisons_context() {
            self.poisoned.set(true);
        }
        error
    }

    /// Run `iterations` steps from `(x, y)`, returning the scaled iterate.
    ///
    /// The vectors are in the scaled space; unscaling is the caller's, because the
    /// caller is also what certifies, and the certification must read the original
    /// model rather than anything this module touched.
    ///
    /// # Errors
    ///
    /// Returns [`DeviceError::Cancelled`] at a chunk boundary, and an availability
    /// failure when the device refuses or a launch faults.
    #[allow(clippy::too_many_arguments)]
    pub fn advance(
        &self,
        x: &mut [f64],
        y: &mut [f64],
        anchor_x: &[f64],
        anchor_y: &[f64],
        since_restart: u64,
        iterations: u64,
        step: f64,
        weight: f64,
        cancel: &CancellationToken,
    ) -> Result<u64, DeviceError> {
        self.usable()?;
        let spmv_row = self.module.function("spmv_row")?;
        let spmv_column = self.module.function("spmv_column")?;
        let primal = self.module.function("primal_step")?;
        let dual = self.module.function("dual_step")?;
        let halpern = self.module.function("halpern")?;

        let shared = self.requirement.shared_bytes;
        if shared > 48 * 1024 {
            spmv_row.set_max_dynamic_shared_memory(shared)?;
            spmv_column.set_max_dynamic_shared_memory(shared)?;
        }

        let mut device_x = self.context.allocate::<f64>(self.columns.max(1))?;
        let mut device_y = self.context.allocate::<f64>(self.rows.max(1))?;
        let mut device_anchor_x = self.context.allocate::<f64>(self.columns.max(1))?;
        let mut device_anchor_y = self.context.allocate::<f64>(self.rows.max(1))?;
        let next_x = self.context.allocate::<f64>(self.columns.max(1))?;
        let next_y = self.context.allocate::<f64>(self.rows.max(1))?;
        let extrapolated = self.context.allocate::<f64>(self.columns.max(1))?;
        let transposed = self.context.allocate::<f64>(self.columns.max(1))?;
        let activity = self.context.allocate::<f64>(self.rows.max(1))?;

        device_x.copy_from(x, &self.stream)?;
        device_y.copy_from(y, &self.stream)?;
        device_anchor_x.copy_from(anchor_x, &self.stream)?;
        device_anchor_y.copy_from(anchor_y, &self.stream)?;

        let primal_step = step / weight;
        let dual_step = step * weight;
        let grid_columns = (self.columns.max(1) as u32).div_ceil(BLOCK);
        let grid_rows = (self.rows.max(1) as u32).div_ceil(BLOCK);
        let line_grid = |lines: usize| u32::try_from(lines.max(1)).unwrap_or(u32::MAX);

        let mut done = 0u64;
        for chunk_start in (0..iterations).step_by(ITERATION_CHUNK as usize) {
            // Cancellation is checked before each chunk rather than after, so a run
            // cancelled before any work starts does none.
            if cancel.is_cancelled() {
                return Err(DeviceError::Cancelled);
            }
            let chunk = ITERATION_CHUNK.min(iterations - chunk_start);
            for step_index in 0..chunk {
                let iteration = since_restart + done + step_index;
                let toward = (iteration + 1) as f64 / (iteration + 2) as f64;
                let back = 1.0 / (iteration + 2) as f64;

                launch(
                    &spmv_column,
                    LaunchConfig {
                        grid: line_grid(self.columns),
                        block: BLOCK,
                        shared_memory: shared,
                    },
                    &[
                        Argument::DevicePtr(self.column_values.as_device_ptr()),
                        Argument::DevicePtr(self.column_indices.as_device_ptr()),
                        Argument::DevicePtr(self.column_offsets.as_device_ptr()),
                        Argument::DevicePtr(device_y.as_device_ptr()),
                        Argument::DevicePtr(transposed.as_device_ptr()),
                        Argument::U32(u32::try_from(self.columns).unwrap_or(u32::MAX)),
                        Argument::U32(
                            u32::try_from(self.requirement.widest_line).unwrap_or(u32::MAX),
                        ),
                    ],
                    &self.stream,
                )
                .map_err(|error| self.observe(error))?;

                launch(
                    &primal,
                    LaunchConfig {
                        grid: grid_columns,
                        block: BLOCK,
                        shared_memory: 0,
                    },
                    &[
                        Argument::DevicePtr(device_x.as_device_ptr()),
                        Argument::DevicePtr(transposed.as_device_ptr()),
                        Argument::DevicePtr(self.objective.as_device_ptr()),
                        Argument::DevicePtr(self.column_lower.as_device_ptr()),
                        Argument::DevicePtr(self.column_upper.as_device_ptr()),
                        Argument::DevicePtr(next_x.as_device_ptr()),
                        Argument::DevicePtr(extrapolated.as_device_ptr()),
                        Argument::F64(primal_step),
                        Argument::U32(u32::try_from(self.columns).unwrap_or(u32::MAX)),
                    ],
                    &self.stream,
                )
                .map_err(|error| self.observe(error))?;

                launch(
                    &spmv_row,
                    LaunchConfig {
                        grid: line_grid(self.rows),
                        block: BLOCK,
                        shared_memory: shared,
                    },
                    &[
                        Argument::DevicePtr(self.row_values.as_device_ptr()),
                        Argument::DevicePtr(self.row_indices.as_device_ptr()),
                        Argument::DevicePtr(self.row_offsets.as_device_ptr()),
                        Argument::DevicePtr(extrapolated.as_device_ptr()),
                        Argument::DevicePtr(activity.as_device_ptr()),
                        Argument::U32(u32::try_from(self.rows).unwrap_or(u32::MAX)),
                        Argument::U32(
                            u32::try_from(self.requirement.widest_line).unwrap_or(u32::MAX),
                        ),
                    ],
                    &self.stream,
                )
                .map_err(|error| self.observe(error))?;

                launch(
                    &dual,
                    LaunchConfig {
                        grid: grid_rows,
                        block: BLOCK,
                        shared_memory: 0,
                    },
                    &[
                        Argument::DevicePtr(device_y.as_device_ptr()),
                        Argument::DevicePtr(activity.as_device_ptr()),
                        Argument::DevicePtr(self.row_lower.as_device_ptr()),
                        Argument::DevicePtr(self.row_upper.as_device_ptr()),
                        Argument::DevicePtr(next_y.as_device_ptr()),
                        Argument::F64(dual_step),
                        Argument::U32(u32::try_from(self.rows).unwrap_or(u32::MAX)),
                    ],
                    &self.stream,
                )
                .map_err(|error| self.observe(error))?;

                // The Halpern coefficients are pure functions of an integer and are
                // computed here rather than on the device, so both engines derive
                // the same numbers instead of one sending them to the other.
                for (stepped, anchor, out, count, grid) in [
                    (
                        &next_x,
                        &device_anchor_x,
                        &device_x,
                        self.columns,
                        grid_columns,
                    ),
                    (&next_y, &device_anchor_y, &device_y, self.rows, grid_rows),
                ] {
                    launch(
                        &halpern,
                        LaunchConfig {
                            grid,
                            block: BLOCK,
                            shared_memory: 0,
                        },
                        &[
                            Argument::DevicePtr(stepped.as_device_ptr()),
                            Argument::DevicePtr(anchor.as_device_ptr()),
                            Argument::DevicePtr(out.as_device_ptr()),
                            Argument::F64(toward),
                            Argument::F64(back),
                            Argument::U32(u32::try_from(count).unwrap_or(u32::MAX)),
                        ],
                        &self.stream,
                    )
                    .map_err(|error| self.observe(error))?;
                }
                self.launches.set(self.launches.get() + 5);
            }

            // Synchronizing per chunk is what makes the cancellation check above
            // mean anything: without it the launches queue and the loop finishes
            // before any has run. It is also where a kernel fault surfaces.
            self.stream
                .synchronize()
                .map_err(|error| self.observe(error))?;
            done += chunk;
        }

        device_x.copy_to(x, &self.stream)?;
        device_y.copy_to(y, &self.stream)?;
        Ok(done)
    }
}
