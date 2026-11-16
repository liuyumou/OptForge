//! Safe driver client; all ownership and unsafe CUDA calls remain in cuda-sys.
use crate::control::Fp64State;
use crate::{
    Result,
    operator::{Format, Operator, Orientation, Product},
};
use optimizer_cuda_sys::{
    Argument as A, Context, DeviceBuffer, LaunchConfig, Module, Stream, launch,
};
use optimizer_lp::Engine;
use std::{path::Path, rc::Rc};

pub const DEVICE: &str = "GPU-6721b13a-30f9-83ec-dace-ba2d9738556f";
pub(crate) fn upload<T: Copy + Default>(
    ctx: &Rc<Context>,
    stream: &Stream,
    values: &[T],
) -> Result<DeviceBuffer<T>> {
    let mut out = ctx.allocate(values.len().max(1))?;
    if values.is_empty() {
        out.copy_from(&[T::default()], stream)?;
    } else {
        out.copy_from(values, stream)?;
    }
    Ok(out)
}
pub(crate) fn read<T: Copy + Default>(
    b: &DeviceBuffer<T>,
    stream: &Stream,
    n: usize,
) -> Result<Vec<T>> {
    let mut v = vec![T::default(); b.len()];
    b.copy_to(&mut v, stream)?;
    v.truncate(n);
    Ok(v)
}
pub(crate) fn write<T: Copy + Default>(b: &mut DeviceBuffer<T>, s: &Stream, v: &[T]) -> Result<()> {
    if v.is_empty() {
        b.copy_from(&[T::default()], s)?;
    } else {
        b.copy_from(v, s)?;
    }
    Ok(())
}
pub(crate) fn pointer<T: Copy>(b: &DeviceBuffer<T>) -> A {
    A::DevicePtr(b.as_device_ptr())
}
pub(crate) fn mode(f: Format) -> u32 {
    match f {
        Format::Native => 0,
        Format::Fp32 => 1,
        Format::Fp4x1 => 2,
        Format::Fp4x2 => 3,
        Format::Fp4x3 => 4,
        Format::Fp4x4 => 5,
    }
}
struct Matrix {
    offsets: DeviceBuffer<u32>,
    indices: DeviceBuffer<u32>,
    ids: DeviceBuffer<u32>,
    original: DeviceBuffer<f64>,
    metadata: DeviceBuffer<f64>,
    reference: DeviceBuffer<f64>,
    reference_error: DeviceBuffer<f64>,
    product: DeviceBuffer<f64>,
    bound: DeviceBuffer<f64>,
    flags: DeviceBuffer<u32>,
    rows: usize,
}
impl Matrix {
    fn new(ctx: &Rc<Context>, stream: &Stream, m: &Orientation, metadata: &[f64]) -> Result<Self> {
        let rows = m.offsets.len() - 1;
        Ok(Self {
            offsets: upload(ctx, stream, &m.offsets)?,
            indices: upload(ctx, stream, &m.indices)?,
            ids: upload(ctx, stream, &m.ids)?,
            original: upload(ctx, stream, &m.original)?,
            metadata: upload(ctx, stream, metadata)?,
            reference: upload(ctx, stream, &vec![0.; rows])?,
            reference_error: upload(ctx, stream, &vec![0.; rows])?,
            product: upload(ctx, stream, &vec![0.; rows])?,
            bound: upload(ctx, stream, &vec![0.; rows])?,
            flags: upload(ctx, stream, &vec![0; rows])?,
            rows,
        })
    }
}
struct Vector {
    state: DeviceBuffer<f64>,
    anchor: DeviceBuffer<f64>,
    controller: DeviceBuffer<f64>,
    delta: DeviceBuffer<f32>,
    stats: DeviceBuffer<f64>,
    summary: DeviceBuffer<f64>,
    n: usize,
}
impl Vector {
    fn new(ctx: &Rc<Context>, s: &Stream, n: usize) -> Result<Self> {
        Ok(Self {
            state: upload(ctx, s, &vec![0.; n])?,
            anchor: upload(ctx, s, &vec![0.; n])?,
            controller: upload(ctx, s, &vec![0.; n])?,
            delta: upload(ctx, s, &vec![0.; n])?,
            stats: upload(ctx, s, &vec![0.; n.div_ceil(8) * 4])?,
            summary: upload(ctx, s, &[0.; 4])?,
            n,
        })
    }
}
pub struct Device {
    _ctx: Rc<Context>,
    module: Module,
    stream: Stream,
    rows: Matrix,
    columns: Matrix,
    x: Vector,
    y: Vector,
    extra: DeviceBuffer<f64>,
    codes: DeviceBuffer<u8>,
    exponents: DeviceBuffer<i32>,
    fp32: DeviceBuffer<f32>,
    xl: DeviceBuffer<f64>,
    xu: DeviceBuffer<f64>,
    yl: DeviceBuffer<f64>,
    yu: DeviceBuffer<f64>,
    objective: DeviceBuffer<f64>,
    pub format: Format,
    prepared: Format,
    pub allocated_bytes: usize,
}
impl Device {
    pub fn new(engine: &Engine<'_>, op: &Operator, image: &Path, format: Format) -> Result<Self> {
        if !op.supports(format) {
            return Err("unprepared device format".into());
        }
        if std::env::var("AI_OPTIMIZER_GPU_LEASE").as_deref() != Ok("inherited")
            || std::env::var("CUDA_VISIBLE_DEVICES").as_deref() != Ok(DEVICE)
        {
            return Err("pinned shared lease required".into());
        }
        let (n, m) = (
            engine.program().column_count(),
            engine.program().row_count(),
        );
        let allocated_bytes = op
            .storage_bytes()
            .checked_add(256 * (n + m + 1))
            .ok_or("memory accounting overflow")?;
        if allocated_bytes > 12usize << 30 {
            return Err("owned device allocation limit".into());
        }
        let ctx = Rc::new(Context::create(DEVICE)?);
        let module = ctx.load_module_file(image)?;
        let stream = ctx.stream()?;
        let (xl, xu) = engine.scaled_column_bounds();
        let (yl, yu) = engine.scaled_row_bounds();
        let out = Self {
            rows: Matrix::new(&ctx, &stream, &op.rows, &op.metadata(false, format))?,
            columns: Matrix::new(&ctx, &stream, &op.columns, &op.metadata(true, format))?,
            x: Vector::new(&ctx, &stream, n)?,
            y: Vector::new(&ctx, &stream, m)?,
            extra: upload(&ctx, &stream, &vec![0.; n])?,
            codes: upload(&ctx, &stream, &op.codes)?,
            exponents: upload(
                &ctx,
                &stream,
                &op.exponents.iter().flatten().copied().collect::<Vec<_>>(),
            )?,
            fp32: upload(&ctx, &stream, &op.fp32)?,
            xl: upload(&ctx, &stream, xl)?,
            xu: upload(&ctx, &stream, xu)?,
            yl: upload(&ctx, &stream, yl)?,
            yu: upload(&ctx, &stream, yu)?,
            objective: upload(&ctx, &stream, engine.scaled_objective())?,
            _ctx: ctx,
            module,
            stream,
            format,
            prepared: op.prepared,
            allocated_bytes,
        };
        out.stream.synchronize()?;
        Ok(out)
    }
    fn launch(&self, name: &str, grid: usize, block: u32, args: &[A]) -> Result<()> {
        if grid == 0 {
            return Ok(());
        }
        launch(
            &self.module.function(name)?,
            LaunchConfig {
                grid: grid as u32,
                block,
                shared_memory: 0,
            },
            args,
            &self.stream,
        )?;
        Ok(())
    }
    fn encode(&self, v: &Vector, input: &DeviceBuffer<f64>) -> Result<()> {
        self.launch(
            "general_encode",
            v.n.div_ceil(8),
            256,
            &[
                pointer(input),
                pointer(&v.anchor),
                pointer(&v.delta),
                pointer(&v.stats),
                A::U32(v.n as u32),
            ],
        )?;
        self.summarize(v)
    }
    fn summarize(&self, v: &Vector) -> Result<()> {
        self.launch(
            "general_summary",
            1,
            256,
            &[
                pointer(&v.stats),
                pointer(&v.summary),
                A::U32(v.n.div_ceil(8) as u32),
            ],
        )
    }
    fn reference(&self, m: &Matrix, x: &DeviceBuffer<f64>) -> Result<()> {
        self.launch(
            "general_reference",
            m.rows.div_ceil(8),
            256,
            &[
                pointer(&m.offsets),
                pointer(&m.indices),
                pointer(&m.original),
                pointer(x),
                pointer(&m.reference),
                pointer(&m.reference_error),
                A::U32(m.rows as u32),
            ],
        )
    }
    pub fn reset(&mut self, state: &Fp64State) -> Result<()> {
        if state.primal.len() != self.x.n
            || state.dual.len() != self.y.n
            || state.anchor_primal.len() != self.x.n
            || state.anchor_dual.len() != self.y.n
            || state
                .primal
                .iter()
                .chain(&state.dual)
                .chain(&state.anchor_primal)
                .chain(&state.anchor_dual)
                .any(|v| {
                    !v.is_finite() || (self.format != Format::Native && v.abs() > 2f64.powi(40))
                })
        {
            return Err("device state domain".into());
        }
        write(&mut self.x.state, &self.stream, &state.primal)?;
        write(&mut self.y.state, &self.stream, &state.dual)?;
        write(&mut self.x.controller, &self.stream, &state.anchor_primal)?;
        write(&mut self.y.controller, &self.stream, &state.anchor_dual)?;
        self.rows
            .flags
            .copy_from(&vec![0; self.rows.rows.max(1)], &self.stream)?;
        self.columns
            .flags
            .copy_from(&vec![0; self.columns.rows.max(1)], &self.stream)?;
        self.stream.synchronize()?;
        Ok(())
    }
    pub fn set_format(&mut self, op: &Operator, format: Format) -> Result<()> {
        let resident = match format {
            Format::Native => true,
            Format::Fp32 => self.prepared != Format::Native,
            Format::Fp4x2 => matches!(self.prepared, Format::Fp4x1 | Format::Fp4x2),
            Format::Fp4x1 => self.prepared == Format::Fp4x1,
            Format::Fp4x3 | Format::Fp4x4 => false,
        };
        if !resident || !op.supports(format) {
            return Err("unprepared device format".into());
        }
        write(
            &mut self.rows.metadata,
            &self.stream,
            &op.metadata(false, format),
        )?;
        write(
            &mut self.columns.metadata,
            &self.stream,
            &op.metadata(true, format),
        )?;
        self.format = format;
        Ok(())
    }
    pub fn refresh(&self) -> Result<()> {
        if self.format == Format::Native {
            return Ok(());
        }
        for v in [&self.x, &self.y] {
            self.launch(
                "general_copy",
                v.n.div_ceil(256),
                256,
                &[pointer(&v.state), pointer(&v.anchor), A::U32(v.n as u32)],
            )?;
        }
        self.reference(&self.rows, &self.x.anchor)?;
        self.reference(&self.columns, &self.y.anchor)?;
        self.encode(&self.y, &self.y.state)
    }
    fn step(&self, direction: u32, step: f64, since: u64, limit: f64, probe: bool) -> Result<()> {
        let (m, input, output, lower, upper) = if direction == 0 {
            (&self.columns, &self.y, &self.x, &self.xl, &self.xu)
        } else {
            (&self.rows, &self.x, &self.y, &self.yl, &self.yu)
        };
        let input_values = if direction == 1 && !probe {
            &self.extra
        } else {
            &input.state
        };
        let toward = (since + 1) as f64 / (since + 2) as f64;
        let back = 1. / (since + 2) as f64;
        self.launch(
            "general_step",
            m.rows.div_ceil(8),
            256,
            &[
                pointer(&m.offsets),
                pointer(&m.indices),
                pointer(&m.ids),
                pointer(&m.original),
                pointer(&self.codes),
                pointer(&self.exponents),
                pointer(&self.fp32),
                pointer(&input.delta),
                pointer(&input.summary),
                pointer(&m.metadata),
                pointer(&m.reference),
                pointer(&m.reference_error),
                pointer(input_values),
                pointer(&output.state),
                pointer(&self.extra),
                pointer(&output.anchor),
                pointer(&output.controller),
                pointer(lower),
                pointer(upper),
                pointer(&self.objective),
                pointer(&output.delta),
                pointer(&output.stats),
                pointer(&m.flags),
                pointer(&m.product),
                pointer(&m.bound),
                A::U32(m.rows as u32),
                A::U32(mode(self.format)),
                A::U32(if probe { 2 } else { direction }),
                A::F64(step),
                A::F64(toward),
                A::F64(back),
                A::F64(limit),
            ],
        )?;
        if !probe && self.format != Format::Native {
            self.summarize(output)?;
        }
        Ok(())
    }
    pub fn advance(
        &self,
        count: u64,
        step: f64,
        weight: f64,
        since: u64,
        limit: f64,
    ) -> Result<bool> {
        self.refresh()?;
        for t in 0..count {
            self.step(0, step / weight, since + t, limit, false)?;
            self.step(1, step * weight, since + t, limit, false)?;
        }
        let a = read(&self.rows.flags, &self.stream, self.rows.rows)?;
        let b = read(&self.columns.flags, &self.stream, self.columns.rows)?;
        Ok(a.iter().chain(&b).all(|v| *v == 0))
    }
    pub fn endpoint(&self) -> Result<(Vec<f64>, Vec<f64>)> {
        Ok((
            read(&self.x.state, &self.stream, self.x.n)?,
            read(&self.y.state, &self.stream, self.y.n)?,
        ))
    }
    pub fn probe(&mut self, transpose: bool, x: &[f64], anchor: &[f64]) -> Result<Product> {
        let v = if transpose { &mut self.y } else { &mut self.x };
        if x.len() != v.n
            || anchor.len() != v.n
            || x.iter()
                .chain(anchor)
                .any(|v| !v.is_finite() || v.abs() > 2f64.powi(40))
        {
            return Err("probe vector domain".into());
        }
        write(&mut v.state, &self.stream, x)?;
        write(&mut v.anchor, &self.stream, anchor)?;
        let (v, m) = if transpose {
            (&self.y, &self.columns)
        } else {
            (&self.x, &self.rows)
        };
        if self.format == Format::Native {
            self.reference(m, &v.state)?;
            return Ok(Product {
                values: read(&m.reference, &self.stream, m.rows)?,
                bounds: read(&m.reference_error, &self.stream, m.rows)?,
            });
        }
        self.reference(m, &v.anchor)?;
        self.encode(v, &v.state)?;
        self.step(if transpose { 0 } else { 1 }, 1., 0, f64::MAX, true)?;
        Ok(Product {
            values: read(&m.product, &self.stream, m.rows)?,
            bounds: read(&m.bound, &self.stream, m.rows)?,
        })
    }
}
