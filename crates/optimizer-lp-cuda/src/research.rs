//! ADR-0021 isolated executor. Mirrors the guarded six-kernel schedule for comparison.
use optimizer_core::{
    ErrorKind, Fp64ExecutionSettings, Fp64Fusion, Fp64Reduction, LpDiagnostics,
    LpExecutionDiagnostics, LpSettings, LpWidth, Model, SessionSetup, StateUploads,
    ValidationError, WorkingAllocation,
};
use optimizer_cuda_sys::{
    Argument as A, Context, DeviceBuffer, DeviceError, LaunchConfig, Module, Stream, launch,
};
use optimizer_lp::{
    LinearProgram, PreparedMatrix,
    control::Fp64Controller,
    pdhg::Engine,
    research::{Mode, Operator, Pair, Parts2, Parts3, split},
};
use std::{path::PathBuf, rc::Rc};

/// Provisioned independently of ordinary Cargo builds.
#[must_use]
pub fn code_object_path() -> PathBuf {
    crate::tuned::code_object_path().with_file_name("lp_pdhg_research.cubin")
}
enum Buffer {
    F64(DeviceBuffer<f64>),
    F32(DeviceBuffer<f32>),
    C2(DeviceBuffer<Parts2>),
    C3(DeviceBuffer<Parts3>),
    /// ADR-0022 unevaluated FP32 pairs; split on upload, never read back.
    Df(DeviceBuffer<Pair>),
}
impl Buffer {
    fn ptr(&self) -> A {
        A::DevicePtr(match self {
            Self::F64(b) => b.as_device_ptr(),
            Self::F32(b) => b.as_device_ptr(),
            Self::C2(b) => b.as_device_ptr(),
            Self::C3(b) => b.as_device_ptr(),
            Self::Df(b) => b.as_device_ptr(),
        })
    }
    fn upload(
        &mut self,
        v: &[f64],
        s: &Stream,
        c: &mut LpExecutionDiagnostics,
    ) -> Result<(), DeviceError> {
        if v.is_empty() {
            return Ok(());
        }
        let bytes = match self {
            Self::F64(b) => {
                b.copy_from(v, s)?;
                8
            }
            Self::C2(_) | Self::C3(_) => {
                return Err(DeviceError::Unsupported(
                    "components require canonical packing".into(),
                ));
            }
            Self::F32(b) => {
                let data = v.iter().map(|&x| x as f32).collect::<Vec<_>>();
                b.copy_from(&data, s)?;
                4
            }
            Self::Df(b) => {
                let data = v.iter().map(|&x| Pair::split(x)).collect::<Vec<_>>();
                b.copy_from(&data, s)?;
                8
            }
        };
        c.upload_calls += 1;
        c.upload_bytes += v.len() as u64 * bytes;
        c.synchronizations += 1;
        Ok(())
    }
    fn read(
        &self,
        n: usize,
        s: &Stream,
        c: &mut LpExecutionDiagnostics,
    ) -> Result<Vec<f64>, DeviceError> {
        if n == 0 {
            return Ok(vec![]);
        }
        let (out, bytes) = match self {
            Self::F64(b) => {
                let mut v = vec![0.0; n];
                b.copy_to(&mut v, s)?;
                (v, 8)
            }
            Self::C2(_) | Self::C3(_) | Self::Df(_) => {
                return Err(DeviceError::Unsupported("component state read".into()));
            }
            Self::F32(b) => {
                let mut v = vec![0.0_f32; n];
                b.copy_to(&mut v, s)?;
                (v.into_iter().map(f64::from).collect(), 4)
            }
        };
        c.readback_calls += 1;
        c.readback_bytes += n as u64 * bytes;
        c.synchronizations += 1;
        Ok(out)
    }
}
const X: usize = 7;
const Y: usize = 8;
const AX: usize = 9;
const AY: usize = 10;
/// One-solve owned precision residency. All driver interaction uses the existing safe boundary.
pub struct ResearchExecutor {
    module: Module,
    stream: Stream,
    b: Vec<Buffer>,
    i: Vec<DeviceBuffer<u32>>,
    n: usize,
    m: usize,
    mode: Mode,
    scales: Vec<DeviceBuffer<f64>>,
    loaded: Option<(u64, u64)>,
    /// Largest discarded normalized vector residual in exact units of 2^-53.
    pub vector_tail_units: u32,
    /// CPU splitting/packing/permutation time, a subset of invariant preparation.
    pub packing_ns: u64,
}
const YDF: usize = 16;
const BARDF: usize = 17;
fn shape(p: &LinearProgram, mode: Mode) -> Vec<(usize, LpWidth)> {
    use LpWidth::F64;
    let n = p.column_count();
    let m = p.row_count();
    let z = p.nonzeros();
    let mut v = vec![
        (z, F64),
        (z, F64),
        (n, F64),
        (n, F64),
        (n, F64),
        (m, F64),
        (m, F64),
        (n, F64),
        (m, F64),
        (n, F64),
        (m, F64),
        (n, F64),
        (n, F64),
        (n, F64),
        (m, F64),
        (m, F64),
    ];
    if mode.doublefloat() {
        v.push((m, F64));
        v.push((n, F64));
    }
    v
}
/// Byte width of buffer `index` for `mode`; only matrices and pair shadows differ from 8.
fn width(mode: Mode, index: usize) -> u64 {
    if index < 2 { matrix_bytes(mode) } else { 8 }
}
/// Exact allocated device bytes, including empty padding, guards and scratch.
pub fn peak_buffer_bytes(p: &LinearProgram, mode: Mode) -> Result<u64, DeviceError> {
    let mut total = 0_u64;
    let mut add = |n: usize, w: u64| -> Result<(), DeviceError> {
        total = total
            .checked_add(
                (n.max(1) as u64)
                    .checked_mul(w)
                    .ok_or_else(|| DeviceError::Unsupported("precision memory overflow".into()))?,
            )
            .ok_or_else(|| DeviceError::Unsupported("precision memory overflow".into()))?;
        Ok(())
    };
    for (index, (n, _)) in shape(p, mode).into_iter().enumerate() {
        add(n, width(mode, index))?;
    }
    let guards = p
        .column_count()
        .checked_add(p.row_count())
        .and_then(|v| v.checked_mul(3))
        .ok_or_else(|| DeviceError::Unsupported("guard memory overflow".into()))?;
    for n in [
        p.nonzeros(),
        p.nonzeros(),
        p.row_count() + 1,
        p.column_count() + 1,
        guards,
    ] {
        add(n, 4)?;
    }
    add(if mode.factored() { p.row_count() } else { 1 }, 8)?;
    add(if mode.factored() { p.column_count() } else { 1 }, 8)?;
    Ok(total)
}
fn matrix_bytes(mode: Mode) -> u64 {
    match mode.components() {
        2 => 12,
        3 => 16,
        _ => {
            if mode.storage32() {
                4
            } else {
                8
            }
        }
    }
}

impl ResearchExecutor {
    /// Admit every buffer before allocation; the code image was identified before opening.
    pub fn new(
        context: Rc<Context>,
        engine: &Engine<'_>,
        op: &Operator,
        image: &[u8],
        d: &mut LpDiagnostics,
    ) -> Result<Self, DeviceError> {
        let p = engine.program();
        let mode = op.mode;
        let peak = peak_buffer_bytes(p, mode)?;
        let device = context.device();
        if (device.capability_major, device.capability_minor) < crate::residency::TARGET_CAPABILITY
        {
            return Err(DeviceError::Unsupported(
                "precision code object capability".into(),
            ));
        }
        if p.column_count() > u32::MAX as usize
            || p.row_count() > u32::MAX as usize
            || p.nonzeros() > u32::MAX as usize
        {
            return Err(DeviceError::Unsupported("precision index range".into()));
        }
        let (free, _) = context.memory_info()?;
        if peak > free || d.device_buffer_limit_bytes.is_some_and(|v| peak > v) {
            return Err(DeviceError::Unsupported(format!(
                "precision device memory: {peak} bytes"
            )));
        }
        let module = context.load_module(image)?;
        let stream = context.stream()?;
        let packing_start = std::time::Instant::now();
        let row3 = if mode.components() > 0 {
            op.rows
                .iter()
                .map(|&v| split(v))
                .collect::<Result<Vec<_>, _>>()
                .map_err(|e| DeviceError::Unsupported(e.into()))?
        } else {
            vec![]
        };
        let row2 = if mode.components() == 2 {
            row3.iter()
                .map(|v| Parts2 {
                    parts: [v.parts[0], v.parts[1]],
                    exponent: v.exponent,
                })
                .collect::<Vec<_>>()
        } else {
            vec![]
        };
        let col3 = if mode.components() == 3 {
            optimizer_lp::research::transpose(p, &row3)
        } else {
            vec![]
        };
        let col2 = if mode.components() == 2 {
            optimizer_lp::research::transpose(p, &row2)
        } else {
            vec![]
        };
        let packing_ns = if mode.components() > 0 {
            packing_start.elapsed().as_nanos() as u64
        } else {
            0
        };
        let c = d
            .execution
            .as_mut()
            .expect("explicit execution observations");
        let mut b = Vec::new();
        let (xl, xu) = engine.scaled_column_bounds();
        let (yl, yu) = engine.scaled_row_bounds();
        let data = [
            op.rows.as_slice(),
            op.columns.as_slice(),
            engine.scaled_objective(),
            xl,
            xu,
            yl,
            yu,
        ];
        let padding2 = [Parts2::default()];
        let padding3 = [Parts3::default()];
        for (idx, (n, _)) in shape(p, mode).into_iter().enumerate() {
            let width = width(mode, idx);
            let mut buffer = if idx < 2 && mode.components() == 2 {
                Buffer::C2(context.allocate(n.max(1))?)
            } else if idx < 2 && mode.components() == 3 {
                Buffer::C3(context.allocate(n.max(1))?)
            } else if mode.doublefloat() && !(2..YDF).contains(&idx) {
                Buffer::Df(context.allocate(n.max(1))?)
            } else if width == 4 {
                Buffer::F32(context.allocate(n.max(1))?)
            } else {
                Buffer::F64(context.allocate(n.max(1))?)
            };
            c.allocations += 1;
            c.allocated_bytes += n.max(1) as u64 * width;
            // Initialized padding and working buffers make whole-buffer sanitizer reads defined.
            let zero = vec![0.0; n.max(1)];
            match &mut buffer {
                Buffer::C2(buf) => {
                    let v = if idx == 0 { &row2 } else { &col2 };
                    buf.copy_from(if v.is_empty() { &padding2 } else { v }, &stream)?;
                    c.upload_calls += 1;
                    c.upload_bytes += n.max(1) as u64 * 12;
                    c.synchronizations += 1;
                }
                Buffer::C3(buf) => {
                    let v = if idx == 0 { &row3 } else { &col3 };
                    buf.copy_from(if v.is_empty() { &padding3 } else { v }, &stream)?;
                    c.upload_calls += 1;
                    c.upload_bytes += n.max(1) as u64 * 16;
                    c.synchronizations += 1;
                }
                _ => {
                    buffer.upload(
                        if idx < data.len() && !data[idx].is_empty() {
                            data[idx]
                        } else {
                            &zero
                        },
                        &stream,
                        c,
                    )?;
                }
            }
            b.push(buffer);
        }
        let n = p.column_count();
        let m = p.row_count();
        let ints = [
            p.row_major()
                .entries()
                .map(|(_, v, _)| v)
                .collect::<Vec<_>>(),
            p.column_major().entries().map(|(_, v, _)| v).collect(),
            (0..=m).map(|j| p.row_major().offset(j) as u32).collect(),
            (0..=n).map(|j| p.column_major().offset(j) as u32).collect(),
            vec![0; 3 * (n + m)],
        ];
        let mut i = Vec::new();
        for mut v in ints {
            if v.is_empty() {
                v.push(0)
            }
            let mut buf = context.allocate::<u32>(v.len())?;
            c.allocations += 1;
            c.allocated_bytes += v.len() as u64 * 4;
            buf.copy_from(&v, &stream)?;
            c.upload_calls += 1;
            c.upload_bytes += v.len() as u64 * 4;
            c.synchronizations += 1;
            i.push(buf);
        }
        let mut scales = Vec::new();
        for source in [
            engine.preconditioner().row(),
            engine.preconditioner().column(),
        ] {
            let data = if mode.factored() && !source.is_empty() {
                source
            } else {
                &[1.0]
            };
            let mut b = context.allocate::<f64>(data.len())?;
            b.copy_from(data, &stream)?;
            c.allocations += 1;
            c.allocated_bytes += data.len() as u64 * 8;
            c.upload_calls += 1;
            c.upload_bytes += data.len() as u64 * 8;
            c.synchronizations += 1;
            scales.push(b);
        }
        d.device_buffer_peak_bytes = Some(peak);
        Ok(Self {
            module,
            stream,
            b,
            i,
            n,
            m,
            mode,
            scales,
            loaded: None,
            vector_tail_units: 0,
            packing_ns,
        })
    }
    /// Reset per-solve state for a session (SPEC-0014 requirement 10).
    ///
    /// Clears the upload-gating key and the tail diagnostic, and re-uploads
    /// the zeroed guard slots as a counted upload, so a reused executor can
    /// never silently keep a previous solve's terminal iterate gating or
    /// guard state. The zero image and its padding are the constructor's.
    ///
    /// # Errors
    /// Returns an availability failure when the device refuses the upload.
    pub fn begin_solve(
        &mut self,
        counters: &mut LpExecutionDiagnostics,
    ) -> Result<(), DeviceError> {
        self.loaded = None;
        self.vector_tail_units = 0;
        let mut zeroes = vec![0_u32; 3 * (self.n + self.m)];
        if zeroes.is_empty() {
            zeroes.push(0);
        }
        self.i[4].copy_from(&zeroes, &self.stream)?;
        counters.upload_calls += 1;
        counters.upload_bytes += zeroes.len() as u64 * 4;
        counters.synchronizations += 1;
        Ok(())
    }

    /// Re-upload the scaled column bounds (buffers 3 and 4) for a bounds-only
    /// variant, counted in the caller's per-solve counters.
    ///
    /// These two buffers are `F64` in every mode — components and
    /// double-float packing apply only to the matrix and shadow buffers — and
    /// the row-bound buffers are the session's and never move (SPEC-0014
    /// requirement 12). The length check runs before any device call.
    ///
    /// # Errors
    /// Returns an unsupported failure on a dimension mismatch and an
    /// availability failure when the device refuses an upload.
    pub fn rebind_column_bounds(
        &mut self,
        xl: &[f64],
        xu: &[f64],
        counters: &mut LpExecutionDiagnostics,
    ) -> Result<(), DeviceError> {
        if xl.len() != self.n || xu.len() != self.n {
            return Err(DeviceError::Unsupported(
                "column bounds differ from the program's column count".into(),
            ));
        }
        self.b[3].upload(xl, &self.stream, counters)?;
        self.b[4].upload(xu, &self.stream, counters)?;
        Ok(())
    }

    /// Execute at most 64 steps; only synchronized, range-clean endpoints are committed.
    pub fn advance(
        &mut self,
        control: &mut Fp64Controller<'_, '_>,
        steps: u64,
        step: f64,
        c: &mut LpExecutionDiagnostics,
    ) -> Result<Option<String>, DeviceError> {
        if steps == 0 || steps > control.next_chunk(64) {
            return Err(DeviceError::Unsupported(
                "research work not admitted".into(),
            ));
        }
        let state = control.state();
        let key = (control.generation(), state.restarts);
        let full = self.loaded.is_none_or(|v| v.0 != key.0);
        let anchors = full || self.loaded.is_none_or(|v| v.1 != key.1);
        for (idx, v, needed) in [
            (X, &state.primal, full),
            (Y, &state.dual, full),
            (AX, &state.anchor_primal, anchors),
            (AY, &state.anchor_dual, anchors),
        ] {
            if needed {
                self.b[idx].upload(v, &self.stream, c)?;
            }
        }
        if self.mode.doublefloat() && full {
            // The dual pair shadow is split on the host once; fused kernels keep it current.
            self.b[YDF].upload(&state.dual, &self.stream, c)?;
        }
        self.loaded = Some(key);
        let sparse_launch = |n: usize| LaunchConfig {
            grid: (n.max(1) as u32).div_ceil(8),
            block: 256,
            shared_memory: 0,
        };
        let vector_launch = |n: usize| LaunchConfig {
            grid: (n.max(1) as u32).div_ceil(256),
            block: 256,
            shared_memory: 0,
        };
        let ip = |j: usize| A::DevicePtr(self.i[j].as_device_ptr());
        let gp = |offset: usize| A::DevicePtr(self.i[4].as_device_ptr() + offset as u64 * 4);
        let n = A::U32(self.n as u32);
        let m = A::U32(self.m as u32);
        let primal_step = step / state.weight;
        let dual_step = step * state.weight;
        if !primal_step.is_finite()
            || !dual_step.is_finite()
            || primal_step == 0.0
            || dual_step == 0.0
        {
            return Ok(Some("update_step_range".into()));
        }
        if let Some((primal_name, dual_name)) = self.mode.fused_kernels() {
            let primal = self.module.function(primal_name)?;
            let dual = self.module.function(dual_name)?;
            let df = self.mode.doublefloat();
            for t in 0..steps {
                let since = state.since_restart + t;
                let toward = A::F64((since + 1) as f64 / (since + 2) as f64);
                let back = A::F64(1.0 / (since + 2) as f64);
                let mut args = vec![self.b[1].ptr(), ip(1), ip(3)];
                if df {
                    args.push(self.b[YDF].ptr());
                } else {
                    args.push(self.b[Y].ptr());
                }
                args.extend([
                    self.b[X].ptr(),
                    self.b[2].ptr(),
                    self.b[3].ptr(),
                    self.b[4].ptr(),
                    self.b[AX].ptr(),
                    self.b[13].ptr(),
                ]);
                if df {
                    args.push(self.b[BARDF].ptr());
                }
                args.extend([
                    self.b[12].ptr(),
                    gp(0),
                    gp(self.n),
                    gp(2 * (self.n + self.m)),
                    A::F64(primal_step),
                    toward,
                    back,
                    n,
                ]);
                launch(&primal, sparse_launch(self.n), &args, &self.stream)?;
                c.kernel_launches += 1;
                let mut args = vec![self.b[0].ptr(), ip(0), ip(2)];
                if df {
                    args.push(self.b[BARDF].ptr());
                } else {
                    args.push(self.b[13].ptr());
                }
                args.push(self.b[Y].ptr());
                if df {
                    args.push(self.b[YDF].ptr());
                }
                args.extend([
                    self.b[5].ptr(),
                    self.b[6].ptr(),
                    self.b[AY].ptr(),
                    self.b[15].ptr(),
                    gp(2 * self.n),
                    gp(2 * self.n + self.m),
                    gp(3 * self.n + 2 * self.m),
                    A::F64(dual_step),
                    toward,
                    back,
                    m,
                ]);
                launch(&dual, sparse_launch(self.m), &args, &self.stream)?;
                c.kernel_launches += 1;
            }
        } else {
            let sparse = self.module.function(self.mode.kernel())?;
            let primal = self.module.function("precision_primal")?;
            let dual = self.module.function("precision_dual")?;
            let store = self.module.function("precision_store")?;
            for t in 0..steps {
                let since = state.since_restart + t;
                let toward = A::F64((since + 1) as f64 / (since + 2) as f64);
                let back = A::F64(1.0 / (since + 2) as f64);
                launch(
                    &sparse,
                    sparse_launch(self.n),
                    &[
                        self.b[1].ptr(),
                        ip(1),
                        ip(3),
                        self.b[Y].ptr(),
                        self.b[11].ptr(),
                        gp(0),
                        n,
                        A::U32(0),
                        A::U32(0),
                        A::U32(0),
                        A::U32(0),
                        A::DevicePtr(self.scales[1].as_device_ptr()),
                        A::DevicePtr(self.scales[0].as_device_ptr()),
                    ],
                    &self.stream,
                )?;
                c.kernel_launches += 1;
                launch(
                    &primal,
                    vector_launch(self.n),
                    &[
                        self.b[X].ptr(),
                        self.b[11].ptr(),
                        self.b[2].ptr(),
                        self.b[3].ptr(),
                        self.b[4].ptr(),
                        self.b[12].ptr(),
                        self.b[13].ptr(),
                        gp(self.n),
                        A::F64(primal_step),
                        n,
                        A::U32(0),
                    ],
                    &self.stream,
                )?;
                c.kernel_launches += 1;
                launch(
                    &sparse,
                    sparse_launch(self.m),
                    &[
                        self.b[0].ptr(),
                        ip(0),
                        ip(2),
                        self.b[13].ptr(),
                        self.b[14].ptr(),
                        gp(2 * self.n),
                        m,
                        A::U32(0),
                        A::U32(0),
                        A::U32(0),
                        A::U32(0),
                        A::DevicePtr(self.scales[0].as_device_ptr()),
                        A::DevicePtr(self.scales[1].as_device_ptr()),
                    ],
                    &self.stream,
                )?;
                c.kernel_launches += 1;
                launch(
                    &dual,
                    vector_launch(self.m),
                    &[
                        self.b[Y].ptr(),
                        self.b[14].ptr(),
                        self.b[5].ptr(),
                        self.b[6].ptr(),
                        self.b[15].ptr(),
                        gp(2 * self.n + self.m),
                        A::F64(dual_step),
                        m,
                        A::U32(0),
                    ],
                    &self.stream,
                )?;
                c.kernel_launches += 1;
                launch(
                    &store,
                    vector_launch(self.n),
                    &[
                        self.b[X].ptr(),
                        self.b[12].ptr(),
                        self.b[AX].ptr(),
                        gp(2 * (self.n + self.m)),
                        toward,
                        back,
                        n,
                        A::U32(0),
                    ],
                    &self.stream,
                )?;
                c.kernel_launches += 1;
                launch(
                    &store,
                    vector_launch(self.m),
                    &[
                        self.b[Y].ptr(),
                        self.b[15].ptr(),
                        self.b[AY].ptr(),
                        gp(3 * self.n + 2 * self.m),
                        toward,
                        back,
                        m,
                        A::U32(0),
                    ],
                    &self.stream,
                )?;
                c.kernel_launches += 1;
            }
        }
        let mut guards = vec![0_u32; (3 * (self.n + self.m)).max(1)];
        self.i[4].copy_to(&mut guards, &self.stream)?;
        c.readback_calls += 1;
        c.readback_bytes += guards.len() as u64 * 4;
        c.synchronizations += 1;
        self.vector_tail_units = guards.iter().map(|g| g >> 8).max().unwrap_or(0);
        if let Some((index, bits)) = guards.iter().enumerate().find(|(_, g)| **g & 255 != 0) {
            return Ok(Some(format!(
                "range_guard_slot_{index}_bits_{}",
                bits & 255
            )));
        }
        let x = self.b[X].read(self.n, &self.stream, c)?;
        let y = self.b[Y].read(self.m, &self.stream, c)?;
        let (cx, cy, _, _) = control.buffers();
        cx.copy_from_slice(&x);
        cy.copy_from_slice(&y);
        Ok(None)
    }
}

/// One admitted solve of a [`ResearchSession`]: a fresh engine over the
/// solve's program plus the session's resident executor, reset for this
/// solve.
///
/// The engine borrows the session's program and prepared matrix while the
/// executor is mutably borrowed — disjoint fields, so the batch loop in
/// optimizer-experiment can build a fresh [`Fp64Controller`] from `engine`,
/// drive `executor.advance` with the per-solve counters
/// [`ResearchSession::fresh_counters`] minted, and certify against `program`,
/// all through this value. The controller cannot be part of the struct: it
/// would borrow the engine the struct owns, which no struct may do.
pub struct ResearchSolve<'s> {
    /// The solve's engine, step-restricted to the session operator's step.
    pub engine: Engine<'s>,
    /// The resident executor after `begin_solve` and any bound rebind.
    pub executor: &'s mut ResearchExecutor,
    /// The program actually solved: the materialized variant or the base.
    pub program: &'s LinearProgram,
}

/// A repeated-solve session for the isolated research executor (SPEC-0014).
///
/// Mirrors [`crate::session::TunedSession`] on the research path: one
/// context, one code image (read and hashed once), one matrix, one operator
/// and one [`ResearchExecutor`] for the session's life, with per-solve
/// gating/guard resets and bounds-only variant rebinds. The per-solve
/// assess/certify/record loop stays in optimizer-experiment — it is the
/// witness contract's code, shared with the fresh path in a later slice —
/// so this type exposes [`ResearchSession::prepare_solve`] rather than a
/// whole-solve entry point.
///
/// The session is `!Send` through its `Rc<Context>`. A device fault reported
/// by the batch loop must be passed to [`ResearchSession::poison`]; a
/// poisoned session refuses later solves, and the driver records them
/// `not_attempted` (requirement 13).
pub struct ResearchSession {
    context: Rc<Context>,
    execution: Fp64ExecutionSettings,
    image: Vec<u8>,
    image_sha256: String,
    model: Model,
    program: LinearProgram,
    prepared: PreparedMatrix,
    operator: Operator,
    executor: ResearchExecutor,
    solve_program: Option<LinearProgram>,
    loaded_bounds: Vec<(f64, f64)>,
    poisoned: Option<String>,
    setup: SessionSetup,
    solve_phases: SessionSetup,
}

impl ResearchSession {
    /// Open a research session: precondition once, admit the operator and
    /// memory once, upload the invariant data once.
    ///
    /// The operator and the restricted step are admitted before any device
    /// allocation, exactly as the fresh research flow admits them, and the
    /// executor constructor performs the same admission and upload as a
    /// fresh solve. The execution identity is the one the research verifier
    /// pins (resident allocation, necessary uploads, warp32 reduction), with
    /// fusion following the mode. The phases this open measures —
    /// `preconditioning`, `research_preparation` and
    /// `invariant_allocation_upload` — land in [`ResearchSession::setup`].
    ///
    /// Power-of-two scaling modes are refused: the fresh flow rebuilds the
    /// engine with explicit exponents for them, which a prepared matrix does
    /// not express, so a session could not reproduce a fresh power-of-two
    /// solve bitwise (requirement 15). The batch contract's modes —
    /// intguard-fp64 and fused-fp64 — do not rescale and are admitted.
    ///
    /// # Errors
    ///
    /// Returns the settings' and model's validation failures, an unsupported
    /// failure when the mode or the operator cannot be admitted, and a
    /// backend failure when the device or the image is refused. Nothing
    /// falls back.
    pub fn open(
        context: Rc<Context>,
        model: Model,
        settings: LpSettings,
        mode: Mode,
        image: Vec<u8>,
        diagnostics: &mut LpDiagnostics,
    ) -> Result<Self, ValidationError> {
        settings.validate()?;
        if mode.power2() {
            return Err(ValidationError::new(
                ErrorKind::Unsupported,
                "research sessions do not support power-of-two scaling modes",
            ));
        }
        let mut setup = SessionSetup::default();
        let program = LinearProgram::new(&model)?;
        let phase = setup.start();
        let prepared = PreparedMatrix::new(&program, &settings);
        setup.finish("preconditioning", phase);
        let phase = setup.start();
        let mut engine = Engine::from_prepared(&program, &prepared);
        let operator = Operator::new(&engine, mode)
            .map_err(|e| ValidationError::new(ErrorKind::Unsupported, e))?;
        engine
            .restrict_step(operator.step)
            .map_err(|e| ValidationError::new(ErrorKind::Unsupported, e))?;
        setup.finish("research_preparation", phase);
        let execution = Fp64ExecutionSettings {
            schema_version: 1,
            allocation: WorkingAllocation::Resident,
            uploads: StateUploads::Necessary,
            reduction: Fp64Reduction::Warp32V1,
            fusion: if mode.fused() {
                Fp64Fusion::PrimalDual
            } else {
                Fp64Fusion::Separate
            },
        };
        execution.validate()?;
        let image_sha256 = optimizer_core::sha256::hex(&image);
        let mut counters = LpExecutionDiagnostics::new(execution);
        counters.code_object_sha256 = Some(image_sha256.clone());
        diagnostics.execution = Some(counters);
        let phase = setup.start();
        let executor =
            ResearchExecutor::new(Rc::clone(&context), &engine, &operator, &image, diagnostics)
                .map_err(|e| ValidationError::new(ErrorKind::Backend, e.to_string()))?;
        setup.finish("invariant_allocation_upload", phase);
        let (lower, upper) = engine.scaled_column_bounds();
        let loaded_bounds = lower.iter().copied().zip(upper.iter().copied()).collect();
        Ok(Self {
            context,
            execution,
            image,
            image_sha256,
            model,
            program,
            prepared,
            operator,
            executor,
            solve_program: None,
            loaded_bounds,
            poisoned: None,
            setup,
            solve_phases: SessionSetup::default(),
        })
    }

    /// Admit one solve and return its engine plus the reset resident
    /// executor.
    ///
    /// The variant, when present, is checked against the session's matrix,
    /// objective, row bounds, variable IDs and domains before any upload for
    /// the solve (requirement 11). The executor is then reset
    /// ([`ResearchExecutor::begin_solve`]) and its column-bound buffers are
    /// re-uploaded only when the solve's scaled bounds differ from the
    /// resident ones (requirement 12). The caller drives the shared
    /// iteration/assessment loop on the returned [`ResearchSolve`]; the
    /// deadline, cancellation and witness recording are the loop's, as they
    /// are for a fresh solve.
    ///
    /// A device fault here poisons the session. A fault inside the loop is
    /// reported by the loop, and the caller passes it to
    /// [`ResearchSession::poison`] — the loop's outcome is not this method's
    /// to observe.
    ///
    /// # Errors
    ///
    /// Returns a backend failure naming the original fault when the session
    /// is poisoned, an unsupported failure for an inadmissible variant, and
    /// a backend failure when the reset or rebind upload is refused.
    pub fn prepare_solve(
        &mut self,
        variant: Option<&Model>,
        counters: &mut LpExecutionDiagnostics,
    ) -> Result<ResearchSolve<'_>, ValidationError> {
        if let Some(reason) = &self.poisoned {
            return Err(ValidationError::new(
                ErrorKind::Backend,
                format!("the session is poisoned by an earlier device fault: {reason}"),
            ));
        }
        let mut phases = SessionSetup::default();
        self.solve_phases = SessionSetup::default();
        let phase = phases.start();
        let mut variant_program = None;
        if let Some(variant) = variant {
            // Admission compares the variant's own canonical program against
            // the session's: the bounds-only rebind inherits this program's
            // matrix, objective and row bounds, so comparing against it alone
            // could never see a changed coefficient (requirement 11).
            let canonical = LinearProgram::new(variant)?;
            let rebound = self.program.with_variable_bounds(variant)?;
            let same_domains = variant
                .document()
                .variables
                .iter()
                .zip(&self.model.document().variables)
                .all(|(v, b)| v.domain == b.domain);
            if !same_domains || !self.program.same_matrix_objective_rows(&canonical) {
                return Err(ValidationError::new(
                    ErrorKind::Unsupported,
                    "a session variant must differ from the session model only in variable bounds",
                ));
            }
            variant_program = Some(rebound);
        }
        phases.finish("variant_rebind", phase);
        self.solve_program = variant_program;
        let program = self.solve_program.as_ref().unwrap_or(&self.program);

        let phase = phases.start();
        let mut engine = Engine::from_prepared(program, &self.prepared);
        engine
            .restrict_step(self.operator.step)
            .map_err(|e| ValidationError::new(ErrorKind::Unsupported, e))?;
        phases.finish("engine_rebind", phase);

        if let Err(error) = self.executor.begin_solve(counters) {
            self.poisoned = Some(error.to_string());
            return Err(ValidationError::new(ErrorKind::Backend, error.to_string()));
        }
        let (lower, upper) = engine.scaled_column_bounds();
        if !crate::session::bounds_match(&self.loaded_bounds, lower, upper) {
            let phase = phases.start();
            if let Err(error) = self.executor.rebind_column_bounds(lower, upper, counters) {
                self.poisoned = Some(error.to_string());
                self.solve_phases = phases;
                return Err(ValidationError::new(ErrorKind::Backend, error.to_string()));
            }
            phases.finish("bound_upload", phase);
            self.loaded_bounds = lower.iter().copied().zip(upper.iter().copied()).collect();
        }
        self.solve_phases = phases;
        let executor = &mut self.executor;
        Ok(ResearchSolve {
            engine,
            executor,
            program,
        })
    }

    /// Mark the session poisoned after a device fault the batch loop
    /// reported; later solves are refused (requirement 13).
    pub fn poison(&mut self, reason: impl Into<String>) {
        self.poisoned = Some(reason.into());
    }

    /// Fresh per-solve execution counters carrying the session's recorded
    /// execution identity and code-image hash (requirement 9).
    #[must_use]
    pub fn fresh_counters(&self) -> LpExecutionDiagnostics {
        let mut counters = LpExecutionDiagnostics::new(self.execution);
        counters.code_object_sha256 = Some(self.image_sha256.clone());
        counters
    }

    /// The model this session was opened with.
    #[must_use]
    pub fn model(&self) -> &Model {
        &self.model
    }

    /// The session's canonical program, with the base model's column bounds.
    #[must_use]
    pub fn program(&self) -> &LinearProgram {
        &self.program
    }

    /// The admitted operator; its bounds, step and matrix tail are recorded
    /// in every solve's witness, identical to a fresh solve's.
    #[must_use]
    pub fn operator(&self) -> &Operator {
        &self.operator
    }

    /// The mode this session runs.
    #[must_use]
    pub fn mode(&self) -> Mode {
        self.operator.mode
    }

    /// The code image the executor was loaded from, read once at open.
    #[must_use]
    pub fn image(&self) -> &[u8] {
        &self.image
    }

    /// The code image's SHA-256, recorded once at open.
    #[must_use]
    pub fn image_sha256(&self) -> &str {
        &self.image_sha256
    }

    /// The executor's one-time host packing/packing-permutation time.
    #[must_use]
    pub fn packing_ns(&self) -> u64 {
        self.executor.packing_ns
    }

    /// The one-time setup phases measured at open.
    #[must_use]
    pub fn setup(&self) -> &SessionSetup {
        &self.setup
    }

    /// The session phases of the most recent prepared solve.
    #[must_use]
    pub fn solve_phases(&self) -> &SessionSetup {
        &self.solve_phases
    }

    /// The fault that poisoned this session, if one did.
    #[must_use]
    pub fn poisoned(&self) -> Option<&str> {
        self.poisoned.as_deref()
    }

    /// The device this session is bound to, for a record that must name it.
    #[must_use]
    pub fn device(&self) -> &optimizer_cuda_sys::DeviceInfo {
        self.context.device()
    }
}
