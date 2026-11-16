//! Specialized unenclosed proposals. Original residual/certificate authority is external.
use crate::{
    Result,
    control::Fp64State,
    device::{DEVICE, pointer, read, upload, write},
    operator::{Format, Operator, Orientation},
    tensor::{Config as TensorConfig, Packed, Tiles},
};
use optimizer_cuda_sys::{
    Argument as A, Context, DeviceBuffer, Function, LaunchConfig, Module, Stream, launch,
};
use optimizer_lp::Engine;
use serde::{Deserialize, Serialize};
use std::{path::Path, rc::Rc};

#[derive(Clone, Debug, Serialize, Deserialize)]
#[serde(default, deny_unknown_fields)]
pub struct Config {
    /// Zero selects a shape from sparse work per output, never from model identity.
    pub lanes: usize,
    pub fused_encode: bool,
    /// Fuse tensor products, full-warp sparse rows, projection and encoding.
    pub combined: bool,
    /// Eight lanes for short rows; a full warp for groups containing >64 entries.
    pub adaptive_rows: bool,
}
impl Default for Config {
    fn default() -> Self {
        Self {
            lanes: 0,
            fused_encode: true,
            combined: true,
            adaptive_rows: true,
        }
    }
}
impl Config {
    pub fn validate(&self) -> Result<()> {
        if ![0, 1, 4, 8, 32].contains(&self.lanes) {
            return Err("fast lane domain".into());
        }
        Ok(())
    }
}
fn lanes(work: usize, rows: usize, override_lanes: usize) -> usize {
    if override_lanes != 0 {
        return override_lanes;
    }
    let average = work.div_ceil(rows.max(1));
    if average >= 64 {
        32
    } else if average >= 8 {
        8
    } else if average >= 4 {
        4
    } else {
        1
    }
}
struct Matrix {
    offsets: DeviceBuffer<u32>,
    indices: DeviceBuffer<u32>,
    original: DeviceBuffer<f64>,
    ro: DeviceBuffer<u32>,
    ri: DeviceBuffer<u32>,
    values: DeviceBuffer<f32>,
    to: DeviceBuffer<u32>,
    tc: DeviceBuffer<u32>,
    fragments: DeviceBuffer<u32>,
    ex: DeviceBuffer<i32>,
    partial: DeviceBuffer<f32>,
    reference: DeviceBuffer<f64>,
    reference_error: DeviceBuffer<f64>,
    product: DeviceBuffer<f64>,
    n: usize,
    tiles: usize,
    covered: u64,
    native_lanes: usize,
    proposal_lanes: usize,
}
impl Matrix {
    fn new(
        ctx: &Rc<Context>,
        stream: &Stream,
        m: &Orientation,
        t: Option<&Tiles>,
        c: &Config,
        format: Format,
    ) -> Result<Self> {
        let n = m.offsets.len() - 1;
        let residual = t.map_or(m, |v| &v.residual);
        let tile_count = t.map_or(0, |v| v.columns.len());
        Ok(Self {
            offsets: upload(ctx, stream, &m.offsets)?,
            indices: upload(ctx, stream, &m.indices)?,
            original: upload(ctx, stream, &m.original)?,
            ro: upload(ctx, stream, t.map_or(&[][..], |v| &v.residual.offsets))?,
            ri: upload(ctx, stream, t.map_or(&[][..], |v| &v.residual.indices))?,
            values: upload(
                ctx,
                stream,
                &if format == Format::Native {
                    Vec::new()
                } else {
                    residual.original.iter().map(|v| *v as f32).collect()
                },
            )?,
            to: upload(ctx, stream, t.map_or(&[][..], |v| &v.offsets))?,
            tc: upload(ctx, stream, t.map_or(&[][..], |v| &v.columns))?,
            fragments: upload(ctx, stream, t.map_or(&[][..], |v| &v.fragments))?,
            ex: upload(ctx, stream, t.map_or(&[][..], |v| &v.exponents))?,
            partial: upload(
                ctx,
                stream,
                &vec![0.; if c.combined { 0 } else { 16 * tile_count }],
            )?,
            reference: upload(ctx, stream, &vec![0.; n])?,
            reference_error: upload(ctx, stream, &vec![0.; n])?,
            product: upload(ctx, stream, &vec![0.; n])?,
            n,
            tiles: tile_count,
            covered: t.map_or(0, |v| v.covered.iter().map(|v| u64::from(*v)).sum()),
            native_lanes: lanes(m.original.len(), n, c.lanes),
            proposal_lanes: lanes(residual.original.len() + 16 * tile_count, n, c.lanes),
        })
    }
}
struct Vector {
    state: DeviceBuffer<f64>,
    delta: DeviceBuffer<f32>,
    anchor: DeviceBuffer<f64>,
    controller: DeviceBuffer<f64>,
    codes: DeviceBuffer<u32>,
    ex: DeviceBuffer<i32>,
    n: usize,
}
impl Vector {
    fn new(ctx: &Rc<Context>, s: &Stream, n: usize, k: usize) -> Result<Self> {
        Ok(Self {
            state: upload(ctx, s, &vec![0.; n])?,
            delta: upload(ctx, s, &vec![0.; n])?,
            anchor: upload(ctx, s, &vec![0.; n])?,
            controller: upload(ctx, s, &vec![0.; n])?,
            codes: upload(ctx, s, &vec![0; 4 * k * n.div_ceil(32)])?,
            ex: upload(ctx, s, &vec![0; k * n.div_ceil(32)])?,
            n,
        })
    }
}
struct Kernels<'a> {
    encode: Function<'a>,
    product: Function<'a>,
    primal: Function<'a>,
    dual: Function<'a>,
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
    flags: DeviceBuffer<u32>,
    pub format: Format,
    prepared: Format,
    k: usize,
    incremental: bool,
    compact: bool,
    fused: bool,
    combined: bool,
    adaptive_rows: bool,
    pub allocated_bytes: usize,
    pub reference_work: u64,
    nonzeros: u64,
    work: [u64; 4],
}
impl Device {
    pub fn new(
        engine: &Engine<'_>,
        op: &Operator,
        packed: Option<&Packed>,
        image: &Path,
        format: Format,
        t: &TensorConfig,
        c: &Config,
    ) -> Result<Self> {
        c.validate()?;
        t.validate()?;
        if std::env::var("AI_OPTIMIZER_GPU_LEASE").as_deref() != Ok("inherited")
            || std::env::var("CUDA_VISIBLE_DEVICES").as_deref() != Ok(DEVICE)
        {
            return Err("pinned shared lease required".into());
        }
        if format.components() > 0 && packed.is_none() {
            return Err("fast tensor representation missing".into());
        }
        if packed.is_some_and(|p| {
            p.components != t.components || p.compact_fragments != t.compact_fragments
        }) {
            return Err("fast packing mismatch".into());
        }
        let (n, m) = (
            engine.program().column_count(),
            engine.program().row_count(),
        );
        let tiles = packed.map_or(0, |p| p.rows.columns.len() + p.columns.columns.len());
        let allocated_bytes = op
            .storage_bytes()
            .checked_add(packed.map_or(0, Packed::storage_bytes))
            .and_then(|v| {
                v.checked_add(8 * op.rows.original.len() + 64 * tiles + 320 * (n + m + 1))
            })
            .ok_or("fast allocation overflow")?;
        if allocated_bytes > 12usize << 30 {
            return Err("owned device allocation limit".into());
        }
        let ctx = Rc::new(Context::create(DEVICE)?);
        let module = ctx.load_module_file(image)?;
        let stream = ctx.stream()?;
        let (xl, xu) = engine.scaled_column_bounds();
        let (yl, yu) = engine.scaled_row_bounds();
        let result = Self {
            rows: Matrix::new(&ctx, &stream, &op.rows, packed.map(|p| &p.rows), c, format)?,
            columns: Matrix::new(
                &ctx,
                &stream,
                &op.columns,
                packed.map(|p| &p.columns),
                c,
                format,
            )?,
            x: Vector::new(&ctx, &stream, n, t.components)?,
            y: Vector::new(&ctx, &stream, m, t.components)?,
            extra: upload(&ctx, &stream, &vec![0.; n])?,
            xl: upload(&ctx, &stream, xl)?,
            xu: upload(&ctx, &stream, xu)?,
            yl: upload(&ctx, &stream, yl)?,
            yu: upload(&ctx, &stream, yu)?,
            objective: upload(&ctx, &stream, engine.scaled_objective())?,
            flags: upload(&ctx, &stream, &[0])?,
            _ctx: ctx,
            module,
            stream,
            format,
            prepared: format,
            k: t.components,
            incremental: t.incremental,
            compact: t.compact_fragments,
            fused: c.fused_encode,
            combined: c.combined,
            adaptive_rows: c.adaptive_rows,
            allocated_bytes,
            reference_work: 0,
            nonzeros: op.rows.original.len() as u64,
            work: [0; 4],
        };
        result.stream.synchronize()?;
        Ok(result)
    }
    fn mode(&self) -> u32 {
        match self.format {
            Format::Native => 0,
            Format::Fp32 => 1,
            _ => 2,
        }
    }
    fn shape(&self, m: &Matrix) -> usize {
        if self.combined && self.mode() == 2 {
            if self.adaptive_rows { 8 } else { 32 }
        } else if self.format == Format::Native {
            m.native_lanes
        } else {
            m.proposal_lanes
        }
    }
    fn fused(&self, m: &Matrix) -> bool {
        self.fused && self.mode() == 2 && (self.combined || self.shape(m) <= 8)
    }
    fn enqueue(&self, f: &Function<'_>, grid: usize, block: u32, args: &[A]) -> Result<()> {
        if grid > 0 {
            launch(
                f,
                LaunchConfig {
                    grid: grid as u32,
                    block,
                    shared_memory: 0,
                },
                args,
                &self.stream,
            )?;
        }
        Ok(())
    }
    fn kernels(&self) -> Result<Kernels<'_>> {
        Ok(Kernels {
            encode: self.module.function("fast_encode")?,
            product: self.module.function(&format!("fast_product_{}", self.k))?,
            primal: self
                .module
                .function(&if self.combined && self.mode() == 2 {
                    format!("fast_combined_{}", self.k)
                } else {
                    format!("fast_step_{}_{}", self.mode(), self.shape(&self.columns))
                })?,
            dual: self
                .module
                .function(&if self.combined && self.mode() == 2 {
                    format!("fast_combined_{}", self.k)
                } else {
                    format!("fast_step_{}_{}", self.mode(), self.shape(&self.rows))
                })?,
        })
    }
    fn encode(&self, v: &Vector, input: &DeviceBuffer<f64>, kernel: &Function<'_>) -> Result<()> {
        self.enqueue(
            kernel,
            v.n.div_ceil(256),
            256,
            &[
                pointer(input),
                pointer(&v.anchor),
                A::U32(u32::from(self.incremental)),
                pointer(&v.codes),
                pointer(&v.ex),
                pointer(&self.flags),
                A::U32(v.n as u32),
                A::U32(self.k as u32),
            ],
        )
    }
    fn reference(&self, m: &Matrix, x: &Vector) -> Result<()> {
        self.enqueue(
            &self.module.function("tensor_reference")?,
            m.n.div_ceil(8),
            256,
            &[
                pointer(&m.offsets),
                pointer(&m.indices),
                pointer(&m.original),
                pointer(&x.anchor),
                pointer(&m.reference),
                pointer(&m.reference_error),
                A::U32(m.n as u32),
            ],
        )
    }
    pub fn reset(&mut self, s: &Fp64State) -> Result<()> {
        write(&mut self.x.state, &self.stream, &s.primal)?;
        write(&mut self.y.state, &self.stream, &s.dual)?;
        write(&mut self.extra, &self.stream, &s.primal)?;
        write(&mut self.x.controller, &self.stream, &s.anchor_primal)?;
        write(&mut self.y.controller, &self.stream, &s.anchor_dual)?;
        write(&mut self.flags, &self.stream, &[0])?;
        if self.format != Format::Native {
            for (vector, state) in [(&mut self.x, &s.primal), (&mut self.y, &s.dual)] {
                let delta: Vec<f32> = state
                    .iter()
                    .map(|v| if self.incremental { 0. } else { *v as f32 })
                    .collect();
                write(&mut vector.delta, &self.stream, &delta)?;
            }
        }
        if self.incremental && self.format != Format::Native {
            write(&mut self.x.anchor, &self.stream, &s.primal)?;
            write(&mut self.y.anchor, &self.stream, &s.dual)?;
            self.reference(&self.rows, &self.x)?;
            self.reference(&self.columns, &self.y)?;
            self.reference_work += 2 * self.nonzeros;
        }
        if self.mode() == 2 {
            self.encode(
                &self.y,
                &self.y.state,
                &self.module.function("fast_encode")?,
            )?;
        }
        Ok(())
    }
    pub fn set_format(&mut self, f: Format) -> Result<()> {
        if f != self.prepared && f != Format::Native {
            return Err("unprepared fast promotion".into());
        }
        self.format = f;
        Ok(())
    }
    fn step(
        &self,
        direction: u32,
        step: f64,
        since: u64,
        probe: bool,
        kernels: &Kernels<'_>,
    ) -> Result<()> {
        let (m, v, out, lo, hi, kernel, previous) = if direction == 0 {
            (
                &self.columns,
                &self.y,
                &self.x,
                &self.xl,
                &self.xu,
                &kernels.primal,
                &self.rows,
            )
        } else {
            (
                &self.rows,
                &self.x,
                &self.y,
                &self.yl,
                &self.yu,
                &kernels.dual,
                &self.columns,
            )
        };
        let input = if direction == 1 && !probe {
            &self.extra
        } else {
            &v.state
        };
        if self.mode() == 2 {
            if probe || !self.fused(previous) {
                self.encode(v, input, &kernels.encode)?;
            }
            if !self.combined {
                self.enqueue(
                    &kernels.product,
                    m.tiles.div_ceil(4),
                    128,
                    &[
                        pointer(&m.tc),
                        pointer(&m.fragments),
                        pointer(&m.ex),
                        pointer(&v.codes),
                        pointer(&v.ex),
                        pointer(&m.partial),
                        A::U32(m.tiles as u32),
                        A::U32(u32::from(self.compact)),
                    ],
                )?;
            }
        }
        let (offsets, indices) = if self.mode() == 2 {
            (&m.ro, &m.ri)
        } else {
            (&m.offsets, &m.indices)
        };
        let mut arguments = vec![
            pointer(offsets),
            pointer(indices),
            pointer(&m.original),
            pointer(&m.values),
            pointer(&m.to),
            pointer(&m.partial),
            pointer(input),
            pointer(&v.anchor),
            pointer(&m.reference),
            pointer(&out.state),
            pointer(&self.extra),
            pointer(&out.controller),
            pointer(lo),
            pointer(hi),
            pointer(&self.objective),
            pointer(&m.product),
            pointer(&self.flags),
            A::U32(m.n as u32),
            A::U32(if probe { 2 } else { direction }),
            A::F64(step),
            A::F64((since + 1) as f64 / (since + 2) as f64),
            A::F64(1. / (since + 2) as f64),
            A::U32(u32::from(self.incremental)),
            A::U32(u32::from(self.fused(m))),
            A::U32(self.k as u32),
            pointer(&out.anchor),
            pointer(&out.codes),
            pointer(&out.ex),
            pointer(&v.delta),
            pointer(&out.delta),
        ];
        if self.combined && self.mode() == 2 {
            arguments.extend([
                pointer(&m.tc),
                pointer(&m.fragments),
                pointer(&m.ex),
                pointer(&v.codes),
                pointer(&v.ex),
                A::U32(u32::from(self.compact)),
                A::U32(u32::from(self.adaptive_rows)),
            ]);
        }
        self.enqueue(
            kernel,
            m.n.div_ceil(if self.combined && self.mode() == 2 {
                32
            } else {
                256 / self.shape(m)
            }),
            256,
            &arguments,
        )
    }
    pub fn advance(
        &mut self,
        count: u64,
        step: f64,
        weight: f64,
        since: u64,
        _limit: f64,
    ) -> Result<bool> {
        let kernels = self.kernels()?;
        for i in 0..count {
            self.step(0, step / weight, since + i, false, &kernels)?;
            self.step(1, step * weight, since + i, false, &kernels)?;
        }
        let covered = if self.mode() == 2 {
            self.rows.covered + self.columns.covered
        } else {
            0
        };
        self.work[0] += covered * count;
        self.work[1] += covered * count;
        self.work[3] += 2 * self.nonzeros * count;
        Ok(read(&self.flags, &self.stream, 1)?[0] == 0)
    }
    pub fn endpoint(&self) -> Result<(Vec<f64>, Vec<f64>)> {
        Ok((
            read(&self.x.state, &self.stream, self.x.n)?,
            read(&self.y.state, &self.stream, self.y.n)?,
        ))
    }
    pub fn work(&self) -> Result<[u64; 4]> {
        Ok(self.work)
    }
    pub fn probe(&mut self, transpose: bool, input: &[f64], anchor: &[f64]) -> Result<Vec<f64>> {
        let v = if transpose { &mut self.y } else { &mut self.x };
        if input.len() != v.n
            || anchor.len() != v.n
            || input
                .iter()
                .chain(anchor)
                .any(|x| !x.is_finite() || x.abs() > 2f64.powi(40))
        {
            return Err("fast probe domain".into());
        }
        write(&mut v.state, &self.stream, input)?;
        write(&mut v.anchor, &self.stream, anchor)?;
        let delta: Vec<f32> = input
            .iter()
            .zip(anchor)
            .map(|(x, a)| {
                if self.incremental {
                    (x - a) as f32
                } else {
                    *x as f32
                }
            })
            .collect();
        write(&mut v.delta, &self.stream, &delta)?;
        if self.incremental && self.mode() != 0 {
            if transpose {
                self.reference(&self.columns, &self.y)?;
            } else {
                self.reference(&self.rows, &self.x)?;
            }
        }
        self.step(if transpose { 0 } else { 1 }, 1., 0, true, &self.kernels()?)?;
        if read(&self.flags, &self.stream, 1)?[0] != 0 {
            return Err("invalid fast product".into());
        }
        let m = if transpose { &self.columns } else { &self.rows };
        read(&m.product, &self.stream, m.n)
    }
    pub fn shapes(&self) -> [usize; 2] {
        [self.shape(&self.rows), self.shape(&self.columns)]
    }
}
