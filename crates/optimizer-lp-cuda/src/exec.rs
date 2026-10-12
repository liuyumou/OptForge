//! ADR-0035 isolated executor: exact sparse products, native FP64 vector updates.
#![allow(missing_docs)]
use optimizer_core::{LpDiagnostics, LpExecutionDiagnostics};
use optimizer_cuda_sys::{
    Argument as A, Context, DeviceBuffer, DeviceError, LaunchConfig, Module, Stream, launch,
};
use optimizer_lp::{
    Engine,
    control::Fp64Controller,
    exec::{Decoded, Mode, Operator},
};
use std::{path::PathBuf, rc::Rc};

pub fn code_object_path() -> PathBuf {
    crate::tuned::code_object_path().with_file_name("lp_pdhg_exec.cubin")
}
fn unsupported(s: impl Into<String>) -> DeviceError {
    DeviceError::Unsupported(s.into())
}
fn grid(n: usize, warp: bool) -> LaunchConfig {
    LaunchConfig {
        grid: (n.max(1) as u32).div_ceil(if warp { 8 } else { 256 }),
        block: 256,
        shared_memory: 0,
    }
}
fn upload<T: Copy>(
    context: &Rc<Context>,
    stream: &Stream,
    data: &[T],
    c: &mut LpExecutionDiagnostics,
) -> Result<DeviceBuffer<T>, DeviceError> {
    let mut b = context.allocate(data.len())?;
    b.copy_from(data, stream)?;
    c.allocations += 1;
    c.allocated_bytes += std::mem::size_of_val(data) as u64;
    c.upload_calls += 1;
    c.upload_bytes += std::mem::size_of_val(data) as u64;
    c.synchronizations += 1;
    Ok(b)
}
const X: usize = 7;
const Y: usize = 8;
const AX: usize = 9;
const AY: usize = 10;
pub struct Executor {
    module: Module,
    stream: Stream,
    b: Vec<DeviceBuffer<f64>>,
    i: Vec<DeviceBuffer<u32>>,
    cached: Vec<DeviceBuffer<Decoded>>,
    flags: DeviceBuffer<u32>,
    errors: DeviceBuffer<i32>,
    n: usize,
    m: usize,
    mode: Mode,
    loaded: Option<(u64, u64)>,
    poisoned: bool,
    pub rounding_flags: u32,
    pub allocation_upload_ns: u64,
}
impl Executor {
    pub fn new(
        context: Rc<Context>,
        engine: &Engine<'_>,
        op: &Operator,
        mode: Mode,
        image: &[u8],
        d: &mut LpDiagnostics,
    ) -> Result<Self, DeviceError> {
        if std::env::var("AI_OPTIMIZER_GPU_LEASE").ok().as_deref() != Some("inherited") {
            return Err(unsupported("shared host lease required"));
        }
        if (
            context.device().capability_major,
            context.device().capability_minor,
        ) != (12, 0)
        {
            return Err(unsupported("exec requires sm_120"));
        }
        op.validate_engine(engine).map_err(unsupported)?;
        let peak = optimizer_lp::exec::device_bytes(
            op.receipt().rows,
            op.receipt().columns,
            op.receipt().nonzeros,
            mode,
        )
        .map_err(unsupported)?;
        let (free, _) = context.memory_info()?;
        if peak > free || d.device_buffer_limit_bytes.is_some_and(|cap| peak > cap) {
            return Err(unsupported("exec device memory"));
        }
        let (n, m) = (op.receipt().columns, op.receipt().rows);
        let module = context.load_module(image)?;
        let stream = context.stream()?;
        let c = d
            .execution
            .as_mut()
            .ok_or_else(|| unsupported("execution diagnostics required"))?;
        let start = std::time::Instant::now();
        let rows = op
            .coefficients()
            .iter()
            .map(|&v| f64::from_bits(v))
            .collect::<Vec<_>>();
        let (xl, xu) = engine.scaled_column_bounds();
        let (yl, yu) = engine.scaled_row_bounds();
        let data = [
            rows.as_slice(),
            &[],
            engine.scaled_objective(),
            xl,
            xu,
            yl,
            yu,
        ];
        let lengths = [rows.len(), 0, n, n, n, m, m, n, m, n, m, n, n, n, m, m];
        let mut b = Vec::new();
        for (k, len) in lengths.into_iter().enumerate() {
            let zero = vec![0.0; len.max(1)];
            let v = if k < data.len() && !data[k].is_empty() {
                data[k]
            } else {
                &zero
            };
            b.push(upload(&context, &stream, v, c)?);
        }
        let mut i = Vec::new();
        for mut v in [
            op.row_indices().to_vec(),
            op.column_indices().to_vec(),
            op.row_offsets().to_vec(),
            op.column_offsets().to_vec(),
            vec![0; 4 * (m + n)],
            op.permutation().to_vec(),
        ] {
            if v.is_empty() {
                v.push(0);
            }
            i.push(upload(&context, &stream, &v, c)?);
        }
        let cached = [n, m]
            .into_iter()
            .map(|len| {
                upload(
                    &context,
                    &stream,
                    &vec![Decoded::default(); if mode == Mode::Cached { len.max(1) } else { 1 }],
                    c,
                )
            })
            .collect::<Result<Vec<_>, _>>()?;
        let flags = upload(&context, &stream, &vec![0_u32; (m + n).max(1)], c)?;
        let errors = upload(&context, &stream, &vec![i32::MAX; (m + n).max(1)], c)?;
        let allocation_upload_ns = start.elapsed().as_nanos() as u64;
        d.device_buffer_peak_bytes = Some(peak);
        Ok(Self {
            module,
            stream,
            b,
            i,
            cached,
            flags,
            errors,
            n,
            m,
            mode,
            loaded: None,
            poisoned: false,
            rounding_flags: 0,
            allocation_upload_ns,
        })
    }
    fn bp(&self, k: usize) -> A {
        A::DevicePtr(self.b[k].as_device_ptr())
    }
    fn ip(&self, k: usize) -> A {
        A::DevicePtr(self.i[k].as_device_ptr())
    }
    fn gp(&self, k: usize) -> A {
        A::DevicePtr(self.i[4].as_device_ptr() + 4 * k as u64)
    }
    fn launch_sparse(
        &self,
        transpose: bool,
        input: usize,
        output: usize,
        guard: usize,
        c: &mut LpExecutionDiagnostics,
    ) -> Result<(), DeviceError> {
        let (lines, len, orientation, flag_offset) = if transpose {
            (self.n, self.m, 1, 0)
        } else {
            (self.m, self.n, 0, self.n)
        };
        if self.mode == Mode::Cached {
            launch(
                &self.module.function("exec_prepare")?,
                grid(len, false),
                &[
                    self.bp(input),
                    A::DevicePtr(self.cached[orientation].as_device_ptr()),
                    self.gp(3 * (self.n + self.m) + if transpose { 0 } else { self.m }),
                    A::U32(len as u32),
                ],
                &self.stream,
            )?;
            c.kernel_launches += 1;
        }
        let name = if self.mode == Mode::Cached {
            "exec_cached"
        } else {
            "exec_uncached"
        };
        launch(
            &self.module.function(name)?,
            grid(lines, true),
            &[
                self.bp(0),
                self.ip(orientation),
                self.ip(orientation + 2),
                self.ip(5),
                self.bp(input),
                A::DevicePtr(self.cached[orientation].as_device_ptr()),
                self.bp(output),
                self.gp(guard),
                A::DevicePtr(self.flags.as_device_ptr() + 4 * flag_offset as u64),
                A::DevicePtr(self.errors.as_device_ptr() + 4 * flag_offset as u64),
                A::U32(lines as u32),
                A::U32(u32::from(transpose)),
            ],
            &self.stream,
        )?;
        c.kernel_launches += 1;
        Ok(())
    }
    pub fn advance(
        &mut self,
        control: &mut Fp64Controller<'_, '_>,
        steps: u64,
        step: f64,
        c: &mut LpExecutionDiagnostics,
    ) -> Result<Option<String>, DeviceError> {
        if self.poisoned {
            return Err(unsupported("exec executor is poisoned"));
        }
        let result = self.advance_inner(control, steps, step, c);
        if !matches!(result, Ok(None)) {
            self.poisoned = true;
        }
        result
    }
    fn advance_inner(
        &mut self,
        control: &mut Fp64Controller<'_, '_>,
        steps: u64,
        step: f64,
        c: &mut LpExecutionDiagnostics,
    ) -> Result<Option<String>, DeviceError> {
        if steps == 0 || steps > control.next_chunk(64) {
            return Err(unsupported("exec work not admitted"));
        }
        let state = control.state();
        let key = (control.generation(), state.restarts);
        let full = self.loaded.is_none_or(|v| v.0 != key.0);
        let anchors = full || self.loaded.is_none_or(|v| v.1 != key.1);
        for (k, v, needed) in [
            (X, &state.primal, full),
            (Y, &state.dual, full),
            (AX, &state.anchor_primal, anchors),
            (AY, &state.anchor_dual, anchors),
        ] {
            if needed && !v.is_empty() {
                self.b[k].copy_from(v, &self.stream)?;
                c.upload_calls += 1;
                c.upload_bytes += v.len() as u64 * 8;
                c.synchronizations += 1;
            }
        }
        self.loaded = Some(key);
        let primal_step = step / state.weight;
        let dual_step = step * state.weight;
        if !primal_step.is_finite()
            || !dual_step.is_finite()
            || primal_step == 0.0
            || dual_step == 0.0
        {
            return Ok(Some("update_step_range".into()));
        }
        let primal = self.module.function("precision_primal")?;
        let dual = self.module.function("precision_dual")?;
        let store = self.module.function("precision_store")?;
        for t in 0..steps {
            let since = state.since_restart + t;
            let toward = A::F64((since + 1) as f64 / (since + 2) as f64);
            let back = A::F64(1.0 / (since + 2) as f64);
            self.launch_sparse(true, Y, 11, 0, c)?;
            launch(
                &primal,
                grid(self.n, false),
                &[
                    self.bp(X),
                    self.bp(11),
                    self.bp(2),
                    self.bp(3),
                    self.bp(4),
                    self.bp(12),
                    self.bp(13),
                    self.gp(self.n),
                    A::F64(primal_step),
                    A::U32(self.n as u32),
                    A::U32(0),
                ],
                &self.stream,
            )?;
            c.kernel_launches += 1;
            self.launch_sparse(false, 13, 14, 2 * self.n, c)?;
            launch(
                &dual,
                grid(self.m, false),
                &[
                    self.bp(Y),
                    self.bp(14),
                    self.bp(5),
                    self.bp(6),
                    self.bp(15),
                    self.gp(2 * self.n + self.m),
                    A::F64(dual_step),
                    A::U32(self.m as u32),
                    A::U32(0),
                ],
                &self.stream,
            )?;
            c.kernel_launches += 1;
            launch(
                &store,
                grid(self.n, false),
                &[
                    self.bp(X),
                    self.bp(12),
                    self.bp(AX),
                    self.gp(2 * (self.n + self.m)),
                    toward,
                    back,
                    A::U32(self.n as u32),
                    A::U32(0),
                ],
                &self.stream,
            )?;
            c.kernel_launches += 1;
            launch(
                &store,
                grid(self.m, false),
                &[
                    self.bp(Y),
                    self.bp(15),
                    self.bp(AY),
                    self.gp(3 * self.n + 2 * self.m),
                    toward,
                    back,
                    A::U32(self.m as u32),
                    A::U32(0),
                ],
                &self.stream,
            )?;
            c.kernel_launches += 1;
        }
        let mut guards = vec![0_u32; (4 * (self.n + self.m)).max(1)];
        self.i[4].copy_to(&mut guards, &self.stream)?;
        c.readback_calls += 1;
        c.readback_bytes += guards.len() as u64 * 4;
        c.synchronizations += 1;
        let mut flags = vec![0_u32; (self.n + self.m).max(1)];
        self.flags.copy_to(&mut flags, &self.stream)?;
        c.readback_calls += 1;
        c.readback_bytes += flags.len() as u64 * 4;
        c.synchronizations += 1;
        self.rounding_flags = flags.into_iter().fold(0, |a, b| a | b);
        if let Some((slot, bits)) = guards.iter().enumerate().find(|(_, v)| **v != 0) {
            return Ok(Some(format!("exec_guard_slot_{slot}_bits_{bits}")));
        }
        let mut x = vec![0.0; self.n];
        let mut y = vec![0.0; self.m];
        for (k, v) in [(X, &mut x), (Y, &mut y)] {
            if !v.is_empty() {
                self.b[k].copy_to(v, &self.stream)?;
                c.readback_calls += 1;
                c.readback_bytes += v.len() as u64 * 8;
                c.synchronizations += 1;
            }
        }
        let (cx, cy, _, _) = control.buffers();
        cx.copy_from_slice(&x);
        cy.copy_from_slice(&y);
        Ok(None)
    }
}
