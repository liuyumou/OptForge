//! Explicit opt-in sparse Tensor Core driver; no changes to the retained backend.
use crate::engine::Engine;
use crate::{
    Result,
    control::Fp64State,
    device::{DEVICE, mode, pointer, read, upload, write},
    operator::{Format, Operator, Orientation, Product},
    tensor::{Config, Packed, Tiles},
};
use optimizer_cuda_sys::{
    Argument as A, Context, DeviceBuffer, Function, LaunchConfig, Module, Stream, launch,
};
use std::{path::Path, rc::Rc};
struct Matrix {
    offsets: DeviceBuffer<u32>,
    indices: DeviceBuffer<u32>,
    original: DeviceBuffer<f64>,
    reference: DeviceBuffer<f64>,
    reference_error: DeviceBuffer<f64>,
    fpmeta: DeviceBuffer<f64>,
    fpvalues: DeviceBuffer<f32>,
    ro: DeviceBuffer<u32>,
    ri: DeviceBuffer<u32>,
    rv: DeviceBuffer<f64>,
    covered: DeviceBuffer<u32>,
    to: DeviceBuffer<u32>,
    tc: DeviceBuffer<u32>,
    fr: DeviceBuffer<u32>,
    ex: DeviceBuffer<i32>,
    meta: DeviceBuffer<f64>,
    tiles: DeviceBuffer<f64>,
    tilebounds: DeviceBuffer<f64>,
    product: DeviceBuffer<f64>,
    bound: DeviceBuffer<f64>,
    flags: DeviceBuffer<u32>,
    work: DeviceBuffer<u64>,
    totals: DeviceBuffer<u64>,
    n: usize,
}
impl Matrix {
    fn new(
        ctx: &Rc<Context>,
        s: &Stream,
        m: &Orientation,
        t: Option<&Tiles>,
        fp32: bool,
    ) -> Result<Self> {
        let n = m.offsets.len() - 1;
        let mut fm = vec![0.; 2 * n];
        if fp32 {
            for r in 0..n {
                for j in m.offsets[r] as usize..m.offsets[r + 1] as usize {
                    let f = f64::from(m.original[j] as f32);
                    fm[2 * r] = (fm[2 * r] + (m.original[j] - f).abs().next_up()).next_up();
                    fm[2 * r + 1] = (fm[2 * r + 1] + f.abs()).next_up();
                }
            }
        }
        Ok(Self {
            fpvalues: upload(
                ctx,
                s,
                &if fp32 {
                    m.original.iter().map(|v| *v as f32).collect()
                } else {
                    Vec::new()
                },
            )?,
            offsets: upload(ctx, s, &m.offsets)?,
            indices: upload(ctx, s, &m.indices)?,
            original: upload(ctx, s, &m.original)?,
            reference: upload(ctx, s, &vec![0.; n])?,
            reference_error: upload(ctx, s, &vec![0.; n])?,
            fpmeta: upload(ctx, s, &fm)?,
            ro: upload(ctx, s, t.map_or(&[][..], |v| &v.residual.offsets))?,
            ri: upload(ctx, s, t.map_or(&[][..], |v| &v.residual.indices))?,
            rv: upload(ctx, s, t.map_or(&[][..], |v| &v.residual.original))?,
            covered: upload(ctx, s, t.map_or(&vec![0; n], |v| &v.covered))?,
            to: upload(ctx, s, t.map_or(&[][..], |v| &v.offsets))?,
            tc: upload(ctx, s, t.map_or(&[][..], |v| &v.columns))?,
            fr: upload(ctx, s, t.map_or(&[][..], |v| &v.fragments))?,
            ex: upload(ctx, s, t.map_or(&[][..], |v| &v.exponents))?,
            meta: upload(ctx, s, t.map_or(&[][..], |v| &v.metadata))?,
            tiles: upload(ctx, s, &vec![0.; n])?,
            tilebounds: upload(ctx, s, &vec![0.; n])?,
            product: upload(ctx, s, &vec![0.; n])?,
            bound: upload(ctx, s, &vec![0.; n])?,
            flags: upload(ctx, s, &vec![0; n])?,
            work: upload(ctx, s, &vec![0; 4 * n])?,
            totals: upload(ctx, s, &[0; 4])?,
            n,
        })
    }
}
struct Vector {
    anchor: DeviceBuffer<f64>,
    state: DeviceBuffer<f64>,
    controller: DeviceBuffer<f64>,
    codes: DeviceBuffer<u32>,
    ex: DeviceBuffer<i32>,
    norms: DeviceBuffer<f64>,
    n: usize,
}
impl Vector {
    fn new(ctx: &Rc<Context>, s: &Stream, n: usize, k: usize) -> Result<Self> {
        Ok(Self {
            anchor: upload(ctx, s, &vec![0.; n])?,
            state: upload(ctx, s, &vec![0.; n])?,
            controller: upload(ctx, s, &vec![0.; n])?,
            codes: upload(ctx, s, &vec![0; 4 * k * n.div_ceil(32)])?,
            ex: upload(ctx, s, &vec![0; k * n.div_ceil(32)])?,
            norms: upload(ctx, s, &vec![0.; 3 * n.div_ceil(32)])?,
            n,
        })
    }
}
struct Kernels<'a> {
    encode: Function<'a>,
    product: Function<'a>,
    step: Function<'a>,
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
    xl: DeviceBuffer<f64>,
    xu: DeviceBuffer<f64>,
    yl: DeviceBuffer<f64>,
    yu: DeviceBuffer<f64>,
    objective: DeviceBuffer<f64>,
    pub format: Format,
    pub allocated_bytes: usize,
    pub reference_work: u64,
    incremental: bool,
    compact: bool,
    tensor_warps: usize,
    nonzeros: u64,
    k: usize,
    prepared: Format,
}
impl Device {
    pub fn new(
        engine: &Engine<'_>,
        op: &Operator,
        p: Option<&Packed>,
        image: &Path,
        format: Format,
        c: &Config,
    ) -> Result<Self> {
        c.validate()?;
        if p.is_some_and(|p| {
            p.components != c.components || p.compact_fragments != c.compact_fragments
        }) || (format.components() > 0 && format.components() != c.components)
        {
            return Err("tensor format/packing mismatch".into());
        }
        if std::env::var("AI_OPTIMIZER_GPU_LEASE").as_deref() != Ok("inherited")
            || std::env::var("CUDA_VISIBLE_DEVICES").as_deref() != Ok(DEVICE)
        {
            return Err("pinned shared lease required".into());
        }
        if format.components() > 0 && p.is_none() {
            return Err("tensor representation missing".into());
        }
        let (n, m) = (
            engine.program().column_count(),
            engine.program().row_count(),
        );
        let allocated_bytes = op
            .storage_bytes()
            .checked_add(p.map_or(0, Packed::storage_bytes))
            .and_then(|b| {
                b.checked_add(if format == Format::Fp32 {
                    8 * op.rows.original.len()
                } else {
                    0
                })
            })
            .and_then(|b| b.checked_add(384 * (n + m + 1)))
            .ok_or("allocation overflow")?;
        if allocated_bytes > 12usize << 30 {
            return Err("owned device allocation limit".into());
        }
        let ctx = Rc::new(Context::create(DEVICE)?);
        let module = ctx.load_module_file(image)?;
        let stream = ctx.stream()?;
        let (xl, xu) = engine.scaled_column_bounds();
        let (yl, yu) = engine.scaled_row_bounds();
        let out = Self {
            rows: Matrix::new(
                &ctx,
                &stream,
                &op.rows,
                p.map(|v| &v.rows),
                format == Format::Fp32,
            )?,
            columns: Matrix::new(
                &ctx,
                &stream,
                &op.columns,
                p.map(|v| &v.columns),
                format == Format::Fp32,
            )?,
            x: Vector::new(&ctx, &stream, n, c.components)?,
            y: Vector::new(&ctx, &stream, m, c.components)?,
            extra: upload(&ctx, &stream, &vec![0.; n])?,
            xl: upload(&ctx, &stream, xl)?,
            xu: upload(&ctx, &stream, xu)?,
            yl: upload(&ctx, &stream, yl)?,
            yu: upload(&ctx, &stream, yu)?,
            objective: upload(&ctx, &stream, engine.scaled_objective())?,
            _ctx: ctx,
            module,
            stream,
            format,
            allocated_bytes,
            reference_work: 0,
            incremental: c.incremental,
            compact: c.compact_fragments,
            tensor_warps: c.tensor_warps,
            nonzeros: op.rows.original.len() as u64,
            k: c.components,
            prepared: format,
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
    fn kernels(&self) -> Result<Kernels<'_>> {
        Ok(Kernels {
            encode: self.module.function("tensor_encode")?,
            product: self.module.function("tensor_product")?,
            step: self.module.function("tensor_step")?,
        })
    }
    fn enqueue(&self, function: &Function<'_>, grid: usize, block: u32, args: &[A]) -> Result<()> {
        if grid == 0 {
            return Ok(());
        }
        launch(
            function,
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
    pub fn reset(&mut self, s: &Fp64State) -> Result<()> {
        write(&mut self.x.state, &self.stream, &s.primal)?;
        write(&mut self.y.state, &self.stream, &s.dual)?;
        write(&mut self.extra, &self.stream, &s.primal)?;
        write(&mut self.x.controller, &self.stream, &s.anchor_primal)?;
        write(&mut self.y.controller, &self.stream, &s.anchor_dual)?;
        write(&mut self.rows.flags, &self.stream, &vec![0; self.rows.n])?;
        write(
            &mut self.columns.flags,
            &self.stream,
            &vec![0; self.columns.n],
        )?;
        if self.incremental && self.format != Format::Native {
            write(&mut self.x.anchor, &self.stream, &s.primal)?;
            write(&mut self.y.anchor, &self.stream, &s.dual)?;
            self.reference(&self.rows, &self.x.anchor)?;
            self.reference(&self.columns, &self.y.anchor)?;
            self.reference_work += 2 * self.nonzeros;
        }
        Ok(())
    }
    pub fn set_format(&mut self, f: Format) -> Result<()> {
        if f != self.prepared && f != Format::Native {
            return Err("unprepared tensor promotion".into());
        }
        self.format = f;
        Ok(())
    }
    fn reference(&self, m: &Matrix, x: &DeviceBuffer<f64>) -> Result<()> {
        self.launch(
            "tensor_reference",
            m.n.div_ceil(8),
            256,
            &[
                pointer(&m.offsets),
                pointer(&m.indices),
                pointer(&m.original),
                pointer(x),
                pointer(&m.reference),
                pointer(&m.reference_error),
                A::U32(m.n as u32),
            ],
        )
    }
    fn product(
        &self,
        m: &Matrix,
        v: &Vector,
        input: &DeviceBuffer<f64>,
        kernels: &Kernels<'_>,
    ) -> Result<()> {
        if self.format.components() == 0 {
            return Ok(());
        }
        self.enqueue(
            &kernels.encode,
            v.n.div_ceil(256),
            256,
            &[
                pointer(input),
                pointer(&v.anchor),
                A::U32(u32::from(self.incremental)),
                pointer(&v.codes),
                pointer(&v.ex),
                pointer(&v.norms),
                A::U32(v.n as u32),
                A::U32(self.k as u32),
            ],
        )?;
        self.enqueue(
            &kernels.product,
            m.n.div_ceil(16 * self.tensor_warps),
            (32 * self.tensor_warps) as u32,
            &[
                pointer(&m.to),
                pointer(&m.tc),
                pointer(&m.fr),
                pointer(&m.ex),
                pointer(&m.meta),
                pointer(&v.codes),
                pointer(&v.ex),
                pointer(&v.norms),
                pointer(&m.tiles),
                pointer(&m.tilebounds),
                A::U32(m.n as u32),
                A::U32(self.k as u32),
                A::U32(u32::from(self.compact)),
            ],
        )
    }
    fn step(
        &self,
        direction: u32,
        step: f64,
        since: u64,
        limit: f64,
        probe: bool,
        kernels: &Kernels<'_>,
    ) -> Result<()> {
        let (m, v, out, lo, hi) = if direction == 0 {
            (&self.columns, &self.y, &self.x, &self.xl, &self.xu)
        } else {
            (&self.rows, &self.x, &self.y, &self.yl, &self.yu)
        };
        let input = if direction == 1 && !probe {
            &self.extra
        } else {
            &v.state
        };
        self.product(m, v, input, kernels)?;
        self.enqueue(
            &kernels.step,
            m.n.div_ceil(8),
            256,
            &[
                pointer(&m.offsets),
                pointer(&m.indices),
                pointer(&m.original),
                pointer(&m.ro),
                pointer(&m.ri),
                pointer(&m.rv),
                pointer(&m.fpvalues),
                pointer(&m.fpmeta),
                pointer(&m.covered),
                pointer(&m.tiles),
                pointer(&m.tilebounds),
                pointer(input),
                pointer(&m.reference),
                pointer(&m.reference_error),
                pointer(&v.anchor),
                pointer(&out.state),
                pointer(&self.extra),
                pointer(&out.controller),
                pointer(lo),
                pointer(hi),
                pointer(&self.objective),
                pointer(&m.flags),
                pointer(&m.work),
                pointer(&m.product),
                pointer(&m.bound),
                A::U32(m.n as u32),
                A::U32(mode(self.format)),
                A::U32(if probe { 2 } else { direction }),
                A::F64(step),
                A::F64((since + 1) as f64 / (since + 2) as f64),
                A::F64(1. / (since + 2) as f64),
                A::F64(limit),
                A::U32(u32::from(self.incremental)),
            ],
        )
    }
    pub fn advance(
        &self,
        count: u64,
        step: f64,
        weight: f64,
        since: u64,
        limit: f64,
    ) -> Result<bool> {
        let kernels = self.kernels()?;
        for t in 0..count {
            self.step(0, step / weight, since + t, limit, false, &kernels)?;
            self.step(1, step * weight, since + t, limit, false, &kernels)?;
        }
        let a = read(&self.rows.flags, &self.stream, self.rows.n)?;
        let b = read(&self.columns.flags, &self.stream, self.columns.n)?;
        Ok(a.iter().chain(&b).all(|v| *v == 0))
    }
    pub fn endpoint(&self) -> Result<(Vec<f64>, Vec<f64>)> {
        Ok((
            read(&self.x.state, &self.stream, self.x.n)?,
            read(&self.y.state, &self.stream, self.y.n)?,
        ))
    }
    pub fn work(&self) -> Result<[u64; 4]> {
        let mut out = [0; 4];
        for m in [&self.rows, &self.columns] {
            self.launch(
                "tensor_totals",
                1,
                256,
                &[pointer(&m.work), pointer(&m.totals), A::U32(m.n as u32)],
            )?;
            let v = read(&m.totals, &self.stream, 4)?;
            for j in 0..4 {
                out[j] += v[j];
            }
        }
        Ok(out)
    }
    pub fn probe(
        &mut self,
        transpose: bool,
        input: &[f64],
        anchor: &[f64],
        limit: f64,
    ) -> Result<Product> {
        let v = if transpose { &mut self.y } else { &mut self.x };
        if input.len() != v.n
            || anchor.len() != v.n
            || input
                .iter()
                .chain(anchor)
                .any(|x| !x.is_finite() || x.abs() > 2f64.powi(40))
        {
            return Err("tensor probe vector domain".into());
        }
        write(&mut v.state, &self.stream, input)?;
        write(&mut v.anchor, &self.stream, anchor)?;
        if self.incremental && self.format != Format::Native {
            let (m, v) = if transpose {
                (&self.columns, &self.y)
            } else {
                (&self.rows, &self.x)
            };
            self.reference(m, &v.anchor)?;
        }
        self.step(
            if transpose { 0 } else { 1 },
            1.,
            0,
            limit,
            true,
            &self.kernels()?,
        )?;
        let m = if transpose { &self.columns } else { &self.rows };
        Ok(Product {
            values: read(&m.product, &self.stream, m.n)?,
            bounds: read(&m.bound, &self.stream, m.n)?,
        })
    }
}
