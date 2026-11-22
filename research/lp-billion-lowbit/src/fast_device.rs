//! Specialized unenclosed proposals. Original residual/certificate authority is external.
use crate::engine::Engine;
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
    /// Preserve original host arithmetic while skipping padded-zero reductions.
    #[serde(skip_serializing_if = "disabled")]
    pub host_reductions: bool,
    #[serde(skip_serializing_if = "disabled")]
    pub host_preparation: bool,
    #[serde(skip_serializing_if = "disabled")]
    pub host_certificates: bool,
    /// Split heavily tiled output groups to expose independent product CTAs.
    #[serde(skip_serializing_if = "disabled")]
    pub auto_schedule: bool,
    /// Exact-order FP64 preparation through the separately admitted CUDA module.
    #[serde(skip_serializing_if = "disabled")]
    pub gpu_preparation: bool,
    #[serde(skip_serializing_if = "disabled")]
    pub gpu_packing: bool,
    /// Exact-tree progress residuals and restart movement norms.
    #[serde(skip_serializing_if = "disabled")]
    pub gpu_control: bool,
    /// Original-order feasibility; CPU feasibility still gates certificate acceptance.
    #[serde(skip_serializing_if = "disabled")]
    pub gpu_feasibility: bool,
}
fn disabled(value: &bool) -> bool {
    !*value
}
impl Default for Config {
    fn default() -> Self {
        Self {
            lanes: 0,
            fused_encode: true,
            combined: true,
            adaptive_rows: true,
            host_reductions: false,
            host_preparation: false,
            host_certificates: false,
            auto_schedule: false,
            gpu_preparation: false,
            gpu_packing: false,
            gpu_control: false,
            gpu_feasibility: false,
        }
    }
}
impl Config {
    pub fn resolved(&self, packed: Option<&Packed>) -> Self {
        let mut result = self.clone();
        if self.auto_schedule
            && self.combined
            && packed.is_some_and(|p| {
                [&p.rows, &p.columns]
                    .iter()
                    .any(|t| t.columns.len() > 4 * t.offsets.len().saturating_sub(1))
            })
        {
            result.combined = false;
        }
        result
    }
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
fn upload_proposal_values(
    ctx: &Rc<Context>,
    stream: &Stream,
    values: &[f64],
    format: Format,
) -> Result<DeviceBuffer<f32>> {
    if format == Format::Native || values.is_empty() {
        return upload(ctx, stream, &[]);
    }
    const CHUNK: usize = 8 << 20; // At most 32 MiB of host conversion scratch.
    let mut output = ctx.allocate(values.len())?;
    let mut converted = Vec::with_capacity(CHUNK.min(values.len()));
    for (index, chunk) in values.chunks(CHUNK).enumerate() {
        converted.clear();
        converted.extend(chunk.iter().map(|v| *v as f32));
        output.copy_from_at(index * CHUNK, &converted, stream)?;
    }
    Ok(output)
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
    fn view(&self) -> crate::gpu_control::Matrix<'_> {
        crate::gpu_control::Matrix {
            offsets: &self.offsets,
            indices: &self.indices,
            values: &self.original,
            n: self.n,
        }
    }
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
            values: upload_proposal_values(ctx, stream, &residual.original, format)?,
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
    support: Option<crate::gpu_control::Support>,
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
        let resolved = c.resolved(packed);
        let c = &resolved;
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
        let support_bytes = if c.gpu_control || c.gpu_feasibility {
            crate::gpu_control::required_bytes(m, n, op.rows.original.len(), c.gpu_feasibility)?
        } else {
            0
        };
        let allocated_bytes = allocation_bytes(op, packed, format, t.components, c.combined)?
            .checked_add(support_bytes)
            .ok_or("GPU control allocation overflow")?;
        if allocated_bytes > 80usize << 30 {
            return Err("combined GPU allocation limit".into());
        }
        for (matrix, tiles) in [
            (&op.rows, packed.map(|p| &p.rows)),
            (&op.columns, packed.map(|p| &p.columns)),
        ] {
            let rows = matrix.offsets.len() - 1;
            let residual = tiles.map_or(matrix, |v| &v.residual);
            let work = tiles
                .map_or(0, |v| v.columns.len())
                .checked_mul(16)
                .and_then(|v| v.checked_add(residual.original.len()))
                .ok_or("proposal scheduling overflow")?;
            check_thread_domain(rows, lanes(matrix.original.len(), rows, c.lanes))?;
            check_thread_domain(rows, lanes(work, rows, c.lanes))?;
        }
        let ctx = Rc::new(Context::create(DEVICE)?);
        let module = ctx.load_module_file(image)?;
        let stream = ctx.stream()?;
        let (xl, xu) = engine.scaled_column_bounds();
        let (yl, yu) = engine.scaled_row_bounds();
        let result = Self {
            support: if c.gpu_control || c.gpu_feasibility {
                Some(crate::gpu_control::Support::new(
                    &ctx,
                    &stream,
                    engine.program(),
                    &image.with_file_name("control.cubin"),
                    c.gpu_control,
                    c.gpu_feasibility,
                )?)
            } else {
                None
            },
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
    pub fn gpu_merit(
        &mut self,
        x: &[f64],
        y: &[f64],
        step: f64,
        weight: f64,
    ) -> Result<Option<f64>> {
        let Some(s) = self.support.as_mut().filter(|s| s.control && s.short_lines) else {
            return Ok(None);
        };
        if x.len() != self.x.n || y.len() != self.y.n {
            return Err("control dimensions".into());
        }
        write(&mut self.x.state, &self.stream, x)?;
        write(&mut self.y.state, &self.stream, y)?;
        Ok(Some(s.merit(
            &self.stream,
            self.rows.view(),
            self.columns.view(),
            &self.x.state,
            &self.y.state,
            &self.extra,
            &self.columns.product,
            &self.rows.product,
            &self.objective,
            &self.xl,
            &self.xu,
            &self.yl,
            &self.yu,
            step,
            weight,
        )?))
    }
    pub fn gpu_movements(&mut self, state: &Fp64State) -> Result<Option<(f64, f64)>> {
        let Some(s) = self.support.as_mut().filter(|s| s.control) else {
            return Ok(None);
        };
        if state.primal.len() != self.x.n
            || state.dual.len() != self.y.n
            || state.anchor_primal.len() != self.x.n
            || state.anchor_dual.len() != self.y.n
        {
            return Err("movement dimensions".into());
        }
        write(&mut self.x.state, &self.stream, &state.primal)?;
        write(&mut self.y.state, &self.stream, &state.dual)?;
        write(&mut self.x.controller, &self.stream, &state.anchor_primal)?;
        write(&mut self.y.controller, &self.stream, &state.anchor_dual)?;
        Ok(Some(s.movements(
            &self.stream,
            &self.x.state,
            &self.x.controller,
            &self.columns.product,
            self.x.n,
            &self.y.state,
            &self.y.controller,
            &self.rows.product,
            self.y.n,
        )?))
    }
    pub fn gpu_feasible(&mut self, x: &[f64], tolerance: f64) -> Result<Option<bool>> {
        let Some(s) = self.support.as_mut().filter(|s| s.has_feasibility()) else {
            return Ok(None);
        };
        if x.len() != self.x.n {
            return Err("candidate domain".into());
        }
        write(&mut self.extra, &self.stream, x)?;
        Ok(Some(s.feasible(
            &self.stream,
            self.rows.view(),
            &self.extra,
            tolerance,
        )?))
    }
    pub fn support_metrics(&self) -> Option<serde_json::Value> {
        self.support.as_ref().map(|s| serde_json::json!({
            "control_backend":if s.control && s.short_lines {"gpu"} else {"host"},
            "movement_backend":if s.control {"gpu"} else {"host"},
            "feasibility_backend":if s.has_feasibility() {"gpu"} else {"host"},
            "merit_calls":s.merit_calls,"movement_calls":s.movement_calls,"feasibility_calls":s.feasibility_calls,
            "control_product_nnz":2*self.nonzeros*s.merit_calls as u64,
            "certificate_acceptance":"original_cpu_dual_gap_and_feasibility"}))
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

/// Every allocation below mirrors an actual upload, including one-element empty
/// buffers. Check all 32-bit physical CUDA indexing before creating a context.
pub fn allocation_bytes(
    op: &Operator,
    packed: Option<&Packed>,
    format: Format,
    k: usize,
    combined: bool,
) -> Result<usize> {
    if !(1..=4).contains(&k) {
        return Err("component domain".into());
    }
    let mut bytes = 0usize;
    let mut add = |count: usize, width: usize| -> Result<()> {
        // CUDA element offsets are unsigned 32 bit in the unchanged image.
        if count > u32::MAX as usize {
            return Err("CUDA physical index limit".into());
        }
        bytes = bytes
            .checked_add(
                count
                    .max(1)
                    .checked_mul(width)
                    .ok_or("allocation product")?,
            )
            .ok_or("allocation sum")?;
        Ok(())
    };
    let (n, m) = (op.columns.offsets.len() - 1, op.rows.offsets.len() - 1);
    for (matrix, tiles) in [
        (&op.rows, packed.map(|p| &p.rows)),
        (&op.columns, packed.map(|p| &p.columns)),
    ] {
        let size = matrix.offsets.len() - 1;
        let residual = tiles.map_or(matrix, |t| &t.residual);
        add(matrix.offsets.len(), 4)?;
        add(matrix.indices.len(), 4)?;
        add(matrix.original.len(), 8)?;
        add(tiles.map_or(0, |t| t.residual.offsets.len()), 4)?;
        add(tiles.map_or(0, |t| t.residual.indices.len()), 4)?;
        add(
            if format == Format::Native {
                0
            } else {
                residual.original.len()
            },
            4,
        )?;
        add(tiles.map_or(0, |t| t.offsets.len()), 4)?;
        add(tiles.map_or(0, |t| t.columns.len()), 4)?;
        add(tiles.map_or(0, |t| t.fragments.len()), 4)?;
        add(tiles.map_or(0, |t| t.exponents.len()), 4)?;
        let count = tiles.map_or(0, |t| t.columns.len());
        // Kernel launch and tile arithmetic multiply before pointer conversion.
        let physical = count
            .checked_mul(k)
            .and_then(|v| v.checked_mul(128))
            .ok_or("tile physical index")?;
        if physical > u32::MAX as usize {
            return Err("tile physical index limit".into());
        }
        add(
            if combined {
                0
            } else {
                count.checked_mul(16).ok_or("partial index")?
            },
            4,
        )?;
        for _ in 0..3 {
            add(size, 8)?;
        }
    }
    for size in [n, m] {
        for _ in 0..3 {
            add(size, 8)?;
        }
        add(size, 4)?;
        let encoded = k.checked_mul(size.div_ceil(32)).ok_or("vector encoding")?;
        add(encoded.checked_mul(4).ok_or("vector codes")?, 4)?;
        add(encoded, 4)?;
    }
    for size in [n, n, n, m, m, n] {
        add(size, 8)?;
    }
    add(1, 4)?;
    if bytes > 80usize << 30 {
        return Err("owned device allocation limit".into());
    }
    Ok(bytes)
}

fn check_thread_domain(rows: usize, lanes: usize) -> Result<()> {
    let threads = rows
        .div_ceil(256 / lanes)
        .checked_mul(256)
        .ok_or("CUDA launch thread overflow")?;
    if threads > u32::MAX as usize + 1 {
        return Err("CUDA flat thread index limit".into());
    }
    Ok(())
}
#[cfg(test)]
mod capacity_tests {
    #[test]
    fn flat_thread_index_is_checked_before_any_device_allocation() {
        assert!(super::check_thread_domain(250_000_000, 4).is_ok());
        assert!(super::check_thread_domain(250_000_000, 8).is_ok());
        assert!(super::check_thread_domain(250_000_000, 32).is_err());
        assert!(super::check_thread_domain(1 << 27, 32).is_ok());
        assert!(super::check_thread_domain((1 << 27) + 1, 32).is_err());
    }
}
