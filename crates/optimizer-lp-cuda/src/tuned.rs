//! Experimental FP64 residency and deterministic execution (ADR-0017).
use crate::residency::{AdvanceResult, LpResidency};
use optimizer_core::{
    Fp64ExecutionSettings, Fp64Fusion, Fp64Reduction, LpDiagnostics, LpExecutionDiagnostics,
    StateUploads, WorkingAllocation,
};
use optimizer_cuda_sys::{
    Argument as A, DeviceBuffer, DeviceError, Function, LaunchConfig, launch,
};
use optimizer_lp::LinearProgram;

/// Separate tuned code object, provisioned outside ordinary builds.
#[must_use]
pub fn code_object_path() -> std::path::PathBuf {
    crate::code_object_path().with_file_name("lp_pdhg_tuned.cubin")
}

/// Exact simultaneous LP-buffer allocation including empty-array padding.
pub fn peak_buffer_bytes(
    p: &LinearProgram,
    settings: Fp64ExecutionSettings,
) -> Result<u64, DeviceError> {
    let c = p.column_count().max(1) as u128;
    let r = p.row_count().max(1) as u128;
    let invariant = 24 * p.nonzeros().max(1) as u128
        + 4 * (p.row_count() as u128 + p.column_count() as u128 + 2)
        + 8 * (3 * c + 2 * r);
    let working = if settings.fusion == Fp64Fusion::PrimalDual {
        8 * (3 * c + 2 * r)
    } else {
        8 * (5 * c + 4 * r)
    };
    u64::try_from(invariant + working)
        .map_err(|_| DeviceError::Unsupported("tuned buffer byte count overflowed".into()))
}

/// Borrowed invariant residency with cached functions and owned working state.
/// A restoration generation, not an iteration index, invalidates cached state.
pub struct TunedExecutor<'r> {
    r: &'r LpResidency,
    settings: Fp64ExecutionSettings,
    column: Function<'r>,
    row: Function<'r>,
    primal: Function<'r>,
    dual: Function<'r>,
    halpern: Function<'r>,
    column_launch: LaunchConfig,
    row_launch: LaunchConfig,
    primal_launch: LaunchConfig,
    dual_launch: LaunchConfig,
    invariant_bytes: u64,
    working: Option<Vec<DeviceBuffer<f64>>>,
    loaded: Option<(u64, u64)>,
}
impl<'r> TunedExecutor<'r> {
    /// Resolve functions once per solve; all remain bound to their loaded module.
    pub fn new(r: &'r LpResidency, settings: Fp64ExecutionSettings) -> Result<Self, DeviceError> {
        settings
            .validate()
            .map_err(|e| DeviceError::Unsupported(e.to_string()))?;
        if r.execution != Some(settings) {
            return Err(DeviceError::Unsupported(
                "tuned executor settings differ from residency".into(),
            ));
        }
        let warp = settings.reduction == Fp64Reduction::Warp32V1;
        let fused = settings.fusion == Fp64Fusion::PrimalDual;
        let (col, row) = if fused {
            if warp {
                ("fused_primal_warp32", "fused_dual_warp32")
            } else {
                ("fused_primal_legacy", "fused_dual_legacy")
            }
        } else if warp {
            ("spmv_warp32", "spmv_warp32")
        } else {
            ("spmv_column", "spmv_row")
        };
        let column = r.module.function(col)?;
        let row = r.module.function(row)?;
        if r.requirement.shared_bytes > 48 * 1024 {
            column.set_max_dynamic_shared_memory(r.requirement.shared_bytes)?;
            row.set_max_dynamic_shared_memory(r.requirement.shared_bytes)?;
        }
        let sparse = |n: usize| LaunchConfig {
            grid: if warp {
                (n.max(1) as u32).div_ceil(8)
            } else {
                n.max(1) as u32
            },
            block: 256,
            shared_memory: r.requirement.shared_bytes,
        };
        let vector = |n: usize| LaunchConfig {
            grid: (n.max(1) as u32).div_ceil(256),
            block: 256,
            shared_memory: 0,
        };
        Ok(Self {
            r,
            settings,
            column,
            row,
            primal: r.module.function("primal_step")?,
            dual: r.module.function("dual_step")?,
            halpern: r.module.function("halpern")?,
            column_launch: sparse(r.columns),
            row_launch: sparse(r.rows),
            primal_launch: vector(r.columns),
            dual_launch: vector(r.rows),
            invariant_bytes: r.buffer_bytes(),
            working: None,
            loaded: None,
        })
    }

    /// Advance a bounded window, preserving observations on every failure path.
    #[allow(clippy::too_many_arguments)]
    pub fn advance(
        &mut self,
        x: &mut [f64],
        y: &mut [f64],
        ax: &[f64],
        ay: &[f64],
        generation: u64,
        restarts: u64,
        since_restart: u64,
        iterations: u64,
        step: f64,
        weight: f64,
        mut stop: impl FnMut(u64) -> bool,
        diagnostics: &mut LpDiagnostics,
    ) -> Result<AdvanceResult, DeviceError> {
        let mut counters = diagnostics
            .execution
            .take()
            .ok_or_else(|| DeviceError::Unsupported("missing tuned observations".into()))?;
        let result = self.advance_inner(
            x,
            y,
            ax,
            ay,
            generation,
            restarts,
            since_restart,
            iterations,
            step,
            weight,
            &mut stop,
            diagnostics,
            &mut counters,
        );
        diagnostics.execution = Some(counters);
        if self.settings.allocation == WorkingAllocation::PerCheck {
            self.working = None;
            self.loaded = None;
        }
        result
    }

    #[allow(clippy::too_many_arguments)]
    fn advance_inner(
        &mut self,
        x: &mut [f64],
        y: &mut [f64],
        ax: &[f64],
        ay: &[f64],
        generation: u64,
        restarts: u64,
        since_restart: u64,
        iterations: u64,
        step: f64,
        weight: f64,
        stop: &mut impl FnMut(u64) -> bool,
        diagnostics: &mut LpDiagnostics,
        counters: &mut LpExecutionDiagnostics,
    ) -> Result<AdvanceResult, DeviceError> {
        let r = self.r;
        r.usable()?;
        if x.len() != r.columns || ax.len() != r.columns || y.len() != r.rows || ay.len() != r.rows
        {
            return Err(DeviceError::Unsupported(
                "tuned state dimensions differ".into(),
            ));
        }
        let phase = diagnostics.start();
        let component_phase = optimizer_core::lp_cost::scope("working_allocation");
        if self.working.is_none() {
            let sizes = [
                r.columns, r.rows, r.columns, r.rows, r.columns, r.columns, r.rows, r.columns,
                r.rows,
            ];
            let count = if self.settings.fusion == Fp64Fusion::PrimalDual {
                5
            } else {
                9
            };
            let mut buffers = Vec::with_capacity(count);
            let mut live_bytes = self.invariant_bytes;
            for n in &sizes[..count] {
                let buffer = r
                    .context
                    .allocate::<f64>((*n).max(1))
                    .map_err(|e| r.observe(e))?;
                counters.allocations += 1;
                counters.allocated_bytes += buffer.len() as u64 * 8;
                live_bytes += buffer.len() as u64 * 8;
                if diagnostics.enabled {
                    diagnostics.device_buffer_peak_bytes = Some(
                        diagnostics
                            .device_buffer_peak_bytes
                            .unwrap_or(0)
                            .max(live_bytes),
                    );
                }
                buffers.push(buffer);
            }
            self.working = Some(buffers);
        }
        drop(component_phase);
        diagnostics.finish("working_allocation", phase);
        let w = self.working.as_mut().expect("allocated working buffers");
        let phase = diagnostics.start();
        let component_phase = optimizer_core::lp_cost::scope("working_upload");
        let full = self.settings.uploads == StateUploads::EveryCheck
            || self.loaded.is_none_or(|(g, _)| g != generation);
        let anchors = full || self.loaded.is_none_or(|(_, a)| a != restarts);
        for (index, values, needed) in [
            (0, &*x, full),
            (1, &*y, full),
            (2, ax, anchors),
            (3, ay, anchors),
        ] {
            if needed && !values.is_empty() {
                w[index]
                    .copy_from(values, &r.stream)
                    .map_err(|e| r.observe(e))?;
                counters.upload_calls += 1;
                counters.upload_bytes += values.len() as u64 * 8;
                counters.synchronizations += 1;
            }
        }
        self.loaded = Some((generation, restarts));
        drop(component_phase);
        diagnostics.finish("working_upload", phase);
        let phase = diagnostics.start();
        let component_phase = optimizer_core::lp_cost::scope("kernels_and_synchronization");
        let ptr = |i: usize| A::DevicePtr(w[i].as_device_ptr());
        let n = A::U32(r.columns as u32);
        let m = A::U32(r.rows as u32);
        let widest = A::U32(r.requirement.widest_line as u32);
        let mut done = 0;
        let mut interrupted = false;
        while done < iterations {
            if stop(done) {
                interrupted = true;
                break;
            }
            let chunk = (iterations - done).min(64);
            for k in 0..chunk {
                let i = since_restart + done + k;
                let toward = (i + 1) as f64 / (i + 2) as f64;
                let back = 1.0 / (i + 2) as f64;
                if self.settings.fusion == Fp64Fusion::PrimalDual {
                    submit(
                        r,
                        &self.column,
                        self.column_launch,
                        &[
                            A::DevicePtr(r.column_values.as_device_ptr()),
                            A::DevicePtr(r.column_indices.as_device_ptr()),
                            A::DevicePtr(r.column_offsets.as_device_ptr()),
                            ptr(1),
                            ptr(0),
                            A::DevicePtr(r.objective.as_device_ptr()),
                            A::DevicePtr(r.column_lower.as_device_ptr()),
                            A::DevicePtr(r.column_upper.as_device_ptr()),
                            ptr(2),
                            ptr(4),
                            A::F64(step / weight),
                            A::F64(toward),
                            A::F64(back),
                            n,
                            widest,
                        ],
                        counters,
                    )?;
                    submit(
                        r,
                        &self.row,
                        self.row_launch,
                        &[
                            A::DevicePtr(r.row_values.as_device_ptr()),
                            A::DevicePtr(r.row_indices.as_device_ptr()),
                            A::DevicePtr(r.row_offsets.as_device_ptr()),
                            ptr(4),
                            ptr(1),
                            A::DevicePtr(r.row_lower.as_device_ptr()),
                            A::DevicePtr(r.row_upper.as_device_ptr()),
                            ptr(3),
                            A::F64(step * weight),
                            A::F64(toward),
                            A::F64(back),
                            m,
                            widest,
                        ],
                        counters,
                    )?;
                } else {
                    submit(
                        r,
                        &self.column,
                        self.column_launch,
                        &[
                            A::DevicePtr(r.column_values.as_device_ptr()),
                            A::DevicePtr(r.column_indices.as_device_ptr()),
                            A::DevicePtr(r.column_offsets.as_device_ptr()),
                            ptr(1),
                            ptr(7),
                            n,
                            widest,
                        ],
                        counters,
                    )?;
                    submit(
                        r,
                        &self.primal,
                        self.primal_launch,
                        &[
                            ptr(0),
                            ptr(7),
                            A::DevicePtr(r.objective.as_device_ptr()),
                            A::DevicePtr(r.column_lower.as_device_ptr()),
                            A::DevicePtr(r.column_upper.as_device_ptr()),
                            ptr(5),
                            ptr(4),
                            A::F64(step / weight),
                            n,
                        ],
                        counters,
                    )?;
                    submit(
                        r,
                        &self.row,
                        self.row_launch,
                        &[
                            A::DevicePtr(r.row_values.as_device_ptr()),
                            A::DevicePtr(r.row_indices.as_device_ptr()),
                            A::DevicePtr(r.row_offsets.as_device_ptr()),
                            ptr(4),
                            ptr(8),
                            m,
                            widest,
                        ],
                        counters,
                    )?;
                    submit(
                        r,
                        &self.dual,
                        self.dual_launch,
                        &[
                            ptr(1),
                            ptr(8),
                            A::DevicePtr(r.row_lower.as_device_ptr()),
                            A::DevicePtr(r.row_upper.as_device_ptr()),
                            ptr(6),
                            A::F64(step * weight),
                            m,
                        ],
                        counters,
                    )?;
                    submit(
                        r,
                        &self.halpern,
                        self.primal_launch,
                        &[ptr(5), ptr(2), ptr(0), A::F64(toward), A::F64(back), n],
                        counters,
                    )?;
                    submit(
                        r,
                        &self.halpern,
                        self.dual_launch,
                        &[ptr(6), ptr(3), ptr(1), A::F64(toward), A::F64(back), m],
                        counters,
                    )?;
                }
            }
            r.stream.synchronize().map_err(|e| r.observe(e))?;
            counters.synchronizations += 1;
            done += chunk;
        }
        drop(component_phase);
        diagnostics.finish("kernels_and_synchronization", phase);
        let phase = diagnostics.start();
        let component_phase = optimizer_core::lp_cost::scope("readback");
        for (index, values) in [(0, x), (1, y)] {
            if !values.is_empty() {
                w[index]
                    .copy_to(values, &r.stream)
                    .map_err(|e| r.observe(e))?;
                counters.readback_calls += 1;
                counters.readback_bytes += values.len() as u64 * 8;
                counters.synchronizations += 1;
            }
        }
        drop(component_phase);
        diagnostics.finish("readback", phase);
        Ok(AdvanceResult {
            completed: done,
            interrupted,
        })
    }
}

fn submit(
    r: &LpResidency,
    f: &Function<'_>,
    config: LaunchConfig,
    args: &[A],
    c: &mut LpExecutionDiagnostics,
) -> Result<(), DeviceError> {
    launch(f, config, args, &r.stream).map_err(|e| r.observe(e))?;
    r.launches.set(r.launches.get() + 1);
    c.kernel_launches += 1;
    Ok(())
}
