//! ADR-0021 isolated executor. Mirrors the guarded six-kernel schedule for comparison.
use optimizer_core::{LpDiagnostics, LpExecutionDiagnostics, LpWidth};
use optimizer_cuda_sys::{
    Argument as A, Context, DeviceBuffer, DeviceError, LaunchConfig, Module, Stream, launch,
};
use optimizer_lp::{
    LinearProgram,
    control::Fp64Controller,
    pdhg::Engine,
    research::{Mode, Operator, Parts2, Parts3, split},
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
}
impl Buffer {
    fn ptr(&self) -> A {
        A::DevicePtr(match self {
            Self::F64(b) => b.as_device_ptr(),
            Self::F32(b) => b.as_device_ptr(),
            Self::C2(b) => b.as_device_ptr(),
            Self::C3(b) => b.as_device_ptr(),
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
            Self::C2(_) | Self::C3(_) => {
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
fn shape(p: &LinearProgram, _mode: Mode) -> Vec<(usize, LpWidth)> {
    use LpWidth::F64;
    let n = p.column_count();
    let m = p.row_count();
    let z = p.nonzeros();
    vec![
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
    ]
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
        add(n, if index < 2 { matrix_bytes(mode) } else { 8 })?;
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
            let width = if idx < 2 { matrix_bytes(mode) } else { 8 };
            let mut buffer = if idx < 2 && mode.components() == 2 {
                Buffer::C2(context.allocate(n.max(1))?)
            } else if idx < 2 && mode.components() == 3 {
                Buffer::C3(context.allocate(n.max(1))?)
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
        self.loaded = Some(key);
        let sparse = self.module.function(self.mode.kernel())?;
        let primal = self.module.function("precision_primal")?;
        let dual = self.module.function("precision_dual")?;
        let store = self.module.function("precision_store")?;
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
