//! Exact-order FP64 preparation; original host certification remains authoritative.
use crate::{
    Result,
    device::{DEVICE, pointer, read, upload},
    engine::Engine,
};
use optimizer_cuda_sys::{
    Argument as A, Context, DeviceBuffer, LaunchConfig, Module, Stream, launch,
};
use optimizer_lp::{Compressed, LinearProgram, LpSettings};
use serde_json::{Value, json};
use std::{path::Path, rc::Rc, time::Instant};

pub fn required_bytes(m: usize, n: usize, z: usize) -> Result<usize> {
    let amount = (z as u128) * 24
        + (m as u128) * 28
        + (n as u128) * 36
        + (n.div_ceil(1024) as u128) * 16
        + 40;
    if m == 0
        || n == 0
        || z == 0
        || m > 250_000_000
        || n > 250_000_000
        || z > 1_000_000_000
        || amount > 80u128 << 30
    {
        return Err("GPU preparation allocation domain".into());
    }
    Ok(amount as usize)
}

struct Matrix {
    offsets: DeviceBuffer<u32>,
    indices: DeviceBuffer<u32>,
    values: DeviceBuffer<f64>,
    n: usize,
}
impl Matrix {
    fn new(p: &Compressed, ctx: &Rc<Context>, s: &Stream) -> Result<Self> {
        let (offsets, indices, values) = p.arrays();
        let offsets = offsets
            .iter()
            .map(|&v| u32::try_from(v))
            .collect::<std::result::Result<Vec<_>, _>>()?;
        Ok(Self {
            offsets: upload(ctx, s, &offsets)?,
            indices: upload(ctx, s, indices)?,
            values: upload(ctx, s, values)?,
            n: p.lines(),
        })
    }
}
struct Preparation {
    _ctx: Rc<Context>,
    module: Module,
    stream: Stream,
    rows: Matrix,
    columns: Matrix,
    r: DeviceBuffer<f64>,
    c: DeviceBuffer<f64>,
    rm: DeviceBuffer<f64>,
    cm: DeviceBuffer<f64>,
    x: DeviceBuffer<f64>,
    y: DeviceBuffer<f64>,
    z: DeviceBuffer<f64>,
    a: DeviceBuffer<f64>,
    b: DeviceBuffer<f64>,
    state: DeviceBuffer<f64>,
    flags: DeviceBuffer<u32>,
}
impl Preparation {
    fn new(p: &LinearProgram, image: &Path) -> Result<Self> {
        if std::env::var("AI_OPTIMIZER_GPU_LEASE").as_deref() != Ok("inherited")
            || std::env::var("CUDA_VISIBLE_DEVICES").as_deref() != Ok(DEVICE)
        {
            return Err("pinned shared lease required for GPU preparation".into());
        }
        let (m, n) = (p.row_count(), p.column_count());
        required_bytes(m, n, p.nonzeros())?;
        let ctx = Rc::new(Context::create(DEVICE)?);
        let stream = ctx.stream()?;
        let module = ctx.load_module_file(image)?;
        let out = Self {
            rows: Matrix::new(p.row_major(), &ctx, &stream)?,
            columns: Matrix::new(p.column_major(), &ctx, &stream)?,
            r: ctx.allocate(m)?,
            c: ctx.allocate(n)?,
            rm: ctx.allocate(m)?,
            cm: ctx.allocate(n)?,
            x: ctx.allocate(n)?,
            y: ctx.allocate(m)?,
            z: ctx.allocate(n)?,
            a: ctx.allocate(n.div_ceil(1024))?,
            b: ctx.allocate(n.div_ceil(1024))?,
            state: upload(&ctx, &stream, &[1., 0., 1.])?,
            flags: upload(&ctx, &stream, &[0u32, 1])?,
            _ctx: ctx,
            module,
            stream,
        };
        for (buffer, count) in [(&out.r, m), (&out.c, n), (&out.x, n)] {
            out.enqueue(
                "prep_fill",
                count.div_ceil(256),
                256,
                &[pointer(buffer), A::U32(count as u32), A::F64(1.)],
            )?;
        }
        out.stream.synchronize()?;
        Ok(out)
    }
    fn enqueue(&self, name: &str, grid: usize, block: u32, args: &[A]) -> Result<()> {
        if grid > 0 {
            let grid = u32::try_from(grid)?;
            launch(
                &self.module.function(name)?,
                LaunchConfig {
                    grid,
                    block,
                    shared_memory: 0,
                },
                args,
                &self.stream,
            )?;
        }
        Ok(())
    }
    fn lines(
        &self,
        name: &str,
        m: &Matrix,
        transpose: bool,
        input: &DeviceBuffer<f64>,
        output: &DeviceBuffer<f64>,
    ) -> Result<()> {
        self.enqueue(
            name,
            m.n.div_ceil(8),
            256,
            &[
                pointer(&m.offsets),
                pointer(&m.indices),
                pointer(&m.values),
                pointer(&self.r),
                pointer(&self.c),
                pointer(input),
                pointer(output),
                A::U32(m.n as u32),
                A::U32(u32::from(transpose)),
                pointer(&self.flags),
            ],
        )
    }
    fn scaling_pass(&self, name: &str) -> Result<()> {
        self.lines(name, &self.rows, false, &self.x, &self.rm)?;
        self.lines(name, &self.columns, true, &self.y, &self.cm)?;
        self.enqueue(
            "prep_update",
            self.rows.n.max(self.columns.n).div_ceil(256),
            256,
            &[
                pointer(&self.r),
                pointer(&self.c),
                pointer(&self.rm),
                pointer(&self.cm),
                A::U32(self.rows.n as u32),
                A::U32(self.columns.n as u32),
                pointer(&self.flags),
            ],
        )
    }
    fn scaling(&self, s: LpSettings) -> Result<()> {
        for _ in 0..s.preconditioner.ruiz_passes {
            self.scaling_pass("prep_max")?;
        }
        if s.preconditioner.pock_chambolle_alpha == 1. {
            self.scaling_pass("prep_sum")?;
        }
        for (matrix, transpose) in [(&self.rows, false), (&self.columns, true)] {
            self.enqueue(
                "prep_scale",
                matrix.n.div_ceil(8),
                256,
                &[
                    pointer(&matrix.offsets),
                    pointer(&matrix.indices),
                    pointer(&matrix.values),
                    pointer(&self.r),
                    pointer(&self.c),
                    A::U32(matrix.n as u32),
                    A::U32(u32::from(transpose)),
                    pointer(&self.flags),
                ],
            )?;
        }
        self.stream.synchronize()?;
        Ok(())
    }
    fn spectral(&self, s: LpSettings) -> Result<()> {
        let n = self.columns.n;
        for _ in 0..s.power_iterations {
            self.lines("prep_product", &self.rows, false, &self.x, &self.y)?;
            self.lines("prep_product", &self.columns, true, &self.y, &self.z)?;
            self.enqueue(
                "prep_reduce",
                n.div_ceil(1024),
                256,
                &[
                    pointer(&self.z),
                    pointer(&self.a),
                    A::U32(n as u32),
                    A::U32(1),
                    pointer(&self.flags),
                ],
            )?;
            let (mut current, mut other) = (&self.a, &self.b);
            let mut count = n.div_ceil(1024);
            while count > 1 {
                self.enqueue(
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
                std::mem::swap(&mut current, &mut other);
                count = count.div_ceil(1024);
            }
            self.enqueue(
                "prep_norm",
                1,
                1,
                &[pointer(current), pointer(&self.state), pointer(&self.flags)],
            )?;
            self.enqueue(
                "prep_normalize",
                n.div_ceil(256),
                256,
                &[
                    pointer(&self.z),
                    pointer(&self.x),
                    A::U32(n as u32),
                    pointer(&self.state),
                    pointer(&self.flags),
                ],
            )?;
        }
        self.stream.synchronize()?;
        Ok(())
    }
}

pub fn engine<'a>(
    p: &'a LinearProgram,
    s: LpSettings,
    image: &Path,
) -> Result<(Engine<'a>, Value)> {
    let started = Instant::now();
    let longest = [p.row_major(), p.column_major()]
        .into_iter()
        .flat_map(|a| a.arrays().0.windows(2).map(|v| v[1] - v[0]))
        .max()
        .unwrap_or(0);
    let fallback = if p.nonzeros() == 0 || p.column_count() == 0 || p.row_count() == 0 {
        Some("empty original geometry")
    } else if ![0., 1.].contains(&s.preconditioner.pock_chambolle_alpha) {
        Some("Pock exponent outside exact GPU domain")
    } else if longest > 1024 {
        Some("original line exceeds 1024-term GPU domain")
    } else {
        None
    };
    if let Some(reason) = fallback {
        let e = crate::host::engine(p, s);
        return Ok((
            e,
            json!({"backend":"host-fallback","reason":reason,"longest_line":longest,"allocated_bytes":0,"total_ns":started.elapsed().as_nanos()}),
        ));
    }
    let bytes = required_bytes(p.row_count(), p.column_count(), p.nonzeros())?;
    let device = Preparation::new(p, image)?;
    let setup = started.elapsed().as_nanos();
    let t = Instant::now();
    device.scaling(s)?;
    let scaling = t.elapsed().as_nanos();
    let t = Instant::now();
    device.spectral(s)?;
    let spectral = t.elapsed().as_nanos();
    let t = Instant::now();
    let flags = read(&device.flags, &device.stream, 2)?;
    if flags[0] != 0 {
        drop(device);
        let e = crate::host::engine(p, s);
        return Ok((
            e,
            json!({"backend":"host-fallback","reason":"nonfinite or nonpositive GPU preparation intermediate",
            "longest_line":longest,"allocated_bytes":bytes,"setup_ns":setup,"scaling_ns":scaling,"spectral_ns":spectral,"total_ns":started.elapsed().as_nanos()}),
        ));
    }
    let row = read(&device.r, &device.stream, p.row_count())?;
    let column = read(&device.c, &device.stream, p.column_count())?;
    let values = read(&device.rows.values, &device.stream, p.nonzeros())?;
    let transposed = read(&device.columns.values, &device.stream, p.nonzeros())?;
    let state = read(&device.state, &device.stream, 3)?;
    let download = t.elapsed().as_nanos();
    let t = Instant::now();
    drop(device);
    let teardown = t.elapsed().as_nanos();
    let base = optimizer_lp::Engine::from_device_preparation(
        p, s, row, column, values, transposed, state[2],
    )?;
    let e = Engine::from_device(base, s);
    let metrics = json!({"backend":"gpu-fp64","longest_line":longest,"allocated_bytes":bytes,
        "setup_ns":setup,"scaling_ns":scaling,"spectral_ns":spectral,"download_ns":download,"teardown_ns":teardown,
        "total_ns":started.elapsed().as_nanos(),"step_bits":state[2].to_bits(),"power_iterations":s.power_iterations});
    Ok((e, metrics))
}

pub fn check(p: &LinearProgram, s: LpSettings, image: &Path) -> Result<Value> {
    let reference = crate::host::engine(p, s);
    let (candidate, metrics) = engine(p, s, image)?;
    let equal = |a: &[f64], b: &[f64]| {
        a.len() == b.len() && a.iter().zip(b).all(|(a, b)| a.to_bits() == b.to_bits())
    };
    let pairs = [
        (
            "row scales",
            reference.preconditioner().row(),
            candidate.preconditioner().row(),
        ),
        (
            "column scales",
            reference.preconditioner().column(),
            candidate.preconditioner().column(),
        ),
        (
            "row coefficients",
            reference.scaled_matrix().0,
            candidate.scaled_matrix().0,
        ),
        (
            "column coefficients",
            reference.scaled_matrix().1,
            candidate.scaled_matrix().1,
        ),
        (
            "objective",
            reference.scaled_objective(),
            candidate.scaled_objective(),
        ),
        (
            "row lower",
            reference.scaled_row_bounds().0,
            candidate.scaled_row_bounds().0,
        ),
        (
            "row upper",
            reference.scaled_row_bounds().1,
            candidate.scaled_row_bounds().1,
        ),
        (
            "column lower",
            reference.scaled_column_bounds().0,
            candidate.scaled_column_bounds().0,
        ),
        (
            "column upper",
            reference.scaled_column_bounds().1,
            candidate.scaled_column_bounds().1,
        ),
    ];
    for (name, a, b) in pairs {
        if !equal(a, b) {
            return Err(format!("GPU preparation differs: {name}").into());
        }
    }
    if reference.step().to_bits() != candidate.step().to_bits() {
        return Err(format!(
            "GPU preparation step differs: {:x} vs {:x}",
            reference.step().to_bits(),
            candidate.step().to_bits()
        )
        .into());
    }
    Ok(
        json!({"exact":true,"preparation":metrics,"step_bits":candidate.step().to_bits(),"scale_digest":candidate.preconditioner().digest()}),
    )
}

#[cfg(test)]
mod tests {
    #[test]
    fn preparation_allocation_includes_both_orientations_and_all_scratch() {
        assert_eq!(
            super::required_bytes(1, 2, 3).unwrap(),
            72 + 28 + 72 + 16 + 40
        );
        assert!(
            super::required_bytes(62_500_000, 250_000_000, 1_000_000_000).unwrap() < 80usize << 30
        );
        assert!(super::required_bytes(usize::MAX, 1, 1).is_err());
        assert!(super::required_bytes(1, 1, 1_000_000_001).is_err());
    }
}
