//! Exact control diagnostics and GPU feasibility; CPU certification stays authoritative.
use crate::{Result, device::pointer};
use optimizer_cuda_sys::{
    Argument as A, Context, DeviceBuffer, LaunchConfig, Module, Stream, launch,
};
use optimizer_lp::{LinearProgram, Range};
use std::{path::Path, rc::Rc};

#[derive(Clone, Copy)]
pub(crate) struct Matrix<'a> {
    pub offsets: &'a DeviceBuffer<u32>,
    pub indices: &'a DeviceBuffer<u32>,
    pub values: &'a DeviceBuffer<f64>,
    pub n: usize,
}
struct Feasibility {
    values: DeviceBuffer<f64>,
    rl: DeviceBuffer<f64>,
    ru: DeviceBuffer<f64>,
    cl: DeviceBuffer<f64>,
    cu: DeviceBuffer<f64>,
    m: usize,
    n: usize,
}
pub fn required_bytes(m: usize, n: usize, z: usize, feasibility: bool) -> Result<usize> {
    let extra = if feasibility {
        8 * z.max(1) as u128 + 16 * m.max(1) as u128 + 16 * n.max(1) as u128
    } else {
        0
    };
    let bytes = extra + 16 * m.max(n).div_ceil(1024).max(1) as u128 + 24;
    if m.max(n) > 250_000_000 || z > 1_000_000_000 || bytes > 80u128 << 30 {
        return Err("GPU control allocation domain".into());
    }
    Ok(bytes as usize)
}
fn bounds(
    ctx: &Rc<Context>,
    stream: &Stream,
    ranges: &[Range],
    lower: bool,
) -> Result<DeviceBuffer<f64>> {
    let mut out = ctx.allocate(ranges.len().max(1))?;
    let mut values = Vec::with_capacity(ranges.len().min(1 << 20));
    for (i, chunk) in ranges.chunks(1 << 20).enumerate() {
        values.clear();
        values.extend(chunk.iter().map(|r| if lower { r.lower } else { r.upper }));
        out.copy_from_at(i * (1 << 20), &values, stream)?;
    }
    Ok(out)
}
pub(crate) struct Support {
    module: Module,
    a: DeviceBuffer<f64>,
    b: DeviceBuffer<f64>,
    scalars: DeviceBuffer<f64>,
    flags: DeviceBuffer<u32>,
    feasibility: Option<Feasibility>,
    pub control: bool,
    pub short_lines: bool,
    pub merit_calls: usize,
    pub movement_calls: usize,
    pub feasibility_calls: usize,
}
impl Support {
    pub fn new(
        ctx: &Rc<Context>,
        stream: &Stream,
        p: &LinearProgram,
        image: &Path,
        control: bool,
        feasibility: bool,
    ) -> Result<Self> {
        let (m, n) = (p.row_count(), p.column_count());
        required_bytes(m, n, p.nonzeros(), feasibility)?;
        let count = m.max(n).div_ceil(1024).max(1);
        let check = if feasibility {
            Some(Feasibility {
                values: crate::device::upload(ctx, stream, p.row_major().arrays().2)?,
                rl: bounds(ctx, stream, p.rows(), true)?,
                ru: bounds(ctx, stream, p.rows(), false)?,
                cl: bounds(ctx, stream, p.columns(), true)?,
                cu: bounds(ctx, stream, p.columns(), false)?,
                m,
                n,
            })
        } else {
            None
        };
        Ok(Self {
            module: ctx.load_module_file(image)?,
            a: ctx.allocate(count)?,
            b: ctx.allocate(count)?,
            scalars: ctx.allocate(2)?,
            flags: ctx.allocate(2)?,
            feasibility: check,
            control,
            short_lines: [p.row_major(), p.column_major()]
                .into_iter()
                .all(|a| a.arrays().0.windows(2).all(|v| v[1] - v[0] <= 1024)),
            merit_calls: 0,
            movement_calls: 0,
            feasibility_calls: 0,
        })
    }
    fn call(&self, stream: &Stream, name: &str, grid: usize, block: u32, args: &[A]) -> Result<()> {
        if grid != 0 {
            launch(
                &self.module.function(name)?,
                LaunchConfig {
                    grid: u32::try_from(grid)?,
                    block,
                    shared_memory: 0,
                },
                args,
                stream,
            )?;
        }
        Ok(())
    }
    fn product(
        &self,
        stream: &Stream,
        a: Matrix<'_>,
        input: &DeviceBuffer<f64>,
        output: &DeviceBuffer<f64>,
    ) -> Result<()> {
        self.call(
            stream,
            "prep_product",
            a.n.div_ceil(8),
            256,
            &[
                pointer(a.offsets),
                pointer(a.indices),
                pointer(a.values),
                pointer(input),
                pointer(input),
                pointer(input),
                pointer(output),
                A::U32(a.n as u32),
                A::U32(0),
                pointer(&self.flags),
            ],
        )
    }
    fn reduce(
        &self,
        stream: &Stream,
        input: &DeviceBuffer<f64>,
        n: usize,
        sum: bool,
        slot: u32,
    ) -> Result<()> {
        let mut count = n;
        let mut current = input;
        let mut other = &self.a;
        // Even a single live value traverses the original 1024-leaf sum tree.
        while count > 0 {
            if sum {
                self.call(
                    stream,
                    "prep_reduce",
                    count.div_ceil(1024),
                    256,
                    &[
                        pointer(current),
                        pointer(other),
                        A::U32(count as u32),
                        A::U32(0),
                        pointer(&self.flags),
                    ],
                )?;
            } else {
                self.call(
                    stream,
                    "control_max",
                    count.div_ceil(1024),
                    256,
                    &[pointer(current), pointer(other), A::U32(count as u32)],
                )?;
            }
            current = other;
            other = if std::ptr::eq(other, &self.a) {
                &self.b
            } else {
                &self.a
            };
            count = count.div_ceil(1024);
            if count == 1 {
                break;
            }
        }
        self.call(
            stream,
            "control_scalar",
            1,
            1,
            &[
                pointer(current),
                pointer(&self.scalars),
                A::U32(slot),
                A::U32(u32::from(n > 0)),
            ],
        )
    }
    #[allow(clippy::too_many_arguments)]
    pub fn merit(
        &mut self,
        stream: &Stream,
        rows: Matrix<'_>,
        columns: Matrix<'_>,
        x: &DeviceBuffer<f64>,
        y: &DeviceBuffer<f64>,
        extra: &DeviceBuffer<f64>,
        xp: &DeviceBuffer<f64>,
        yp: &DeviceBuffer<f64>,
        cost: &DeviceBuffer<f64>,
        xl: &DeviceBuffer<f64>,
        xu: &DeviceBuffer<f64>,
        yl: &DeviceBuffer<f64>,
        yu: &DeviceBuffer<f64>,
        step: f64,
        weight: f64,
    ) -> Result<f64> {
        self.merit_calls += 1;
        if !weight.is_finite() || weight <= 0. {
            return Ok(f64::INFINITY);
        }
        self.flags.copy_from(&[0, 1], stream)?;
        self.product(stream, columns, y, xp)?;
        self.call(
            stream,
            "control_primal",
            columns.n.div_ceil(256),
            256,
            &[
                pointer(x),
                pointer(xp),
                pointer(cost),
                pointer(xl),
                pointer(xu),
                pointer(extra),
                A::U32(columns.n as u32),
                A::F64(step / weight),
            ],
        )?;
        self.reduce(stream, xp, columns.n, false, 0)?;
        self.product(stream, rows, extra, yp)?;
        self.call(
            stream,
            "control_dual",
            rows.n.div_ceil(256),
            256,
            &[
                pointer(y),
                pointer(yp),
                pointer(yl),
                pointer(yu),
                A::U32(rows.n as u32),
                A::F64(step * weight),
            ],
        )?;
        self.reduce(stream, yp, rows.n, false, 1)?;
        let mut result = [0.; 2];
        self.scalars.copy_to(&mut result, stream)?;
        Ok(result[0].max(result[1]))
    }
    #[allow(clippy::too_many_arguments)]
    pub fn movements(
        &mut self,
        stream: &Stream,
        x: &DeviceBuffer<f64>,
        ax: &DeviceBuffer<f64>,
        xp: &DeviceBuffer<f64>,
        n: usize,
        y: &DeviceBuffer<f64>,
        ay: &DeviceBuffer<f64>,
        yp: &DeviceBuffer<f64>,
        m: usize,
    ) -> Result<(f64, f64)> {
        self.movement_calls += 1;
        self.flags.copy_from(&[0, 1], stream)?;
        for (slot, v, a, out, len) in [(0, x, ax, xp, n), (1, y, ay, yp, m)] {
            self.call(
                stream,
                "control_movement",
                len.div_ceil(256),
                256,
                &[pointer(v), pointer(a), pointer(out), A::U32(len as u32)],
            )?;
            self.reduce(stream, out, len, true, slot)?;
        }
        let mut result = [0.; 2];
        self.scalars.copy_to(&mut result, stream)?;
        // Keep scalar sqrt/log/exp and the primal-weight recurrence on the host.
        Ok((result[0].sqrt(), result[1].sqrt()))
    }
    pub fn has_feasibility(&self) -> bool {
        self.feasibility.is_some()
    }
    pub fn feasible(
        &mut self,
        stream: &Stream,
        rows: Matrix<'_>,
        x: &DeviceBuffer<f64>,
        tolerance: f64,
    ) -> Result<bool> {
        let f = self
            .feasibility
            .as_ref()
            .ok_or("GPU feasibility unavailable")?;
        if !tolerance.is_finite() || tolerance < 0. {
            return Err("candidate domain".into());
        }
        self.feasibility_calls += 1;
        self.flags.copy_from(&[0, 0], stream)?;
        self.call(
            stream,
            "control_feasible_columns",
            f.n.div_ceil(256),
            256,
            &[
                pointer(x),
                pointer(&f.cl),
                pointer(&f.cu),
                A::U32(f.n as u32),
                A::F64(tolerance),
                pointer(&self.flags),
            ],
        )?;
        self.call(
            stream,
            "control_feasible_rows",
            f.m.div_ceil(256),
            256,
            &[
                pointer(rows.offsets),
                pointer(rows.indices),
                pointer(&f.values),
                pointer(x),
                pointer(&f.rl),
                pointer(&f.ru),
                A::U32(f.m as u32),
                A::F64(tolerance),
                pointer(&self.flags),
            ],
        )?;
        let mut flags = [0; 2];
        self.flags.copy_to(&mut flags, stream)?;
        if flags[0] != 0 {
            return Err("nonfinite original feasibility arithmetic".into());
        }
        Ok(flags[1] == 0)
    }
}
