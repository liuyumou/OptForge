use crate::{Result, model::Data};
use optimizer_cuda_sys::{
    Argument as A, Context, DeviceBuffer, LaunchConfig, Module, Stream, events::Event, launch,
};
use serde::Serialize;
use std::rc::Rc;

pub fn upload<T: Copy>(ctx: &Rc<Context>, stream: &Stream, data: &[T]) -> Result<DeviceBuffer<T>> {
    let mut b = ctx.allocate(data.len())?;
    b.copy_from(data, stream)?;
    Ok(b)
}
pub fn download<T: Copy + Default>(b: &DeviceBuffer<T>, stream: &Stream) -> Result<Vec<T>> {
    let mut out = vec![T::default(); b.len()];
    b.copy_to(&mut out, stream)?;
    Ok(out)
}
#[derive(Serialize, Clone, PartialEq, Debug)]
pub struct Snapshot {
    pub raw: Vec<f64>,
    pub codes: Vec<u32>,
    pub exponents: Vec<i32>,
    pub pairs: Vec<[f32; 2]>,
    pub logical: u32,
    pub generation: u32,
}
#[derive(Serialize, Clone, Debug)]
pub struct Step {
    pub done: u32,
    pub flags: Vec<u32>,
    pub terms: Vec<f32>,
    pub gpu_us: f64,
}
pub struct Engine {
    pub k: usize,
    pub logical: u32,
    pub generation: u32,
    pub since_audit: u32,
    saved_logical: u32,
    faulted: bool,
    n: u32,
    m: u32,
    b: u32,
    shift: u32,
    extra: u32,
    a: DeviceBuffer<u32>,
    ae: DeviceBuffer<i32>,
    fr: DeviceBuffer<u32>,
    masks: DeviceBuffer<u32>,
    original: DeviceBuffer<[f32; 2]>,
    error: DeviceBuffer<[f32; 2]>,
    native: DeviceBuffer<f64>,
    cb: DeviceBuffer<f64>,
    s: DeviceBuffer<u32>,
    se: DeviceBuffer<i32>,
    v: DeviceBuffer<[f32; 2]>,
    raw: DeviceBuffer<f64>,
    cs: DeviceBuffer<u32>,
    ce: DeviceBuffer<i32>,
    cv: DeviceBuffer<[f32; 2]>,
    cr: DeviceBuffer<f64>,
    report: DeviceBuffer<u32>,
    zeros: Vec<u32>,
    refs: DeviceBuffer<[f32; 2]>,
    norms: DeviceBuffer<f32>,
    pending: DeviceBuffer<u32>,
    start: Event,
    end: Event,
}
impl Engine {
    pub fn new(
        data: &Data,
        key: usize,
        ctx: &Rc<Context>,
        module: &Module,
        stream: &Stream,
    ) -> Result<Self> {
        if ![0, 2, 4, 18, 20, 32, 34, 36].contains(&key) {
            return Err("unsupported arithmetic lane".into());
        }
        let k = key % 16;
        let packed = data.pack_mode(k, (16..32).contains(&key), key == 0 && !data.dense)?;
        let b = data.p / 32;
        let ns = if k == 0 { 1 } else { 3 * b * k * 4 };
        let ne = if k == 0 { 1 } else { 3 * b * k };
        let zeros = vec![0; b + 1 + 8 * b];
        let mut e = Self {
            k: key,
            logical: 0,
            generation: 0,
            since_audit: 0,
            saved_logical: 0,
            faulted: false,
            n: data.original.column_count() as u32,
            m: data.original.row_count() as u32,
            b: b as u32,
            shift: data.shift,
            extra: if k == 0 {
                u32::from(data.dense)
            } else {
                u32::from(packed.has_error)
            },
            a: upload(ctx, stream, &packed.codes)?,
            ae: upload(ctx, stream, &packed.exponents)?,
            fr: upload(
                ctx,
                stream,
                &vec![0; if k == 0 { 1 } else { b * b * k * 512 }],
            )?,
            masks: upload(ctx, stream, &vec![0; if k == 0 { 1 } else { b * b }])?,
            original: upload(
                ctx,
                stream,
                if (16..32).contains(&key) {
                    &packed.original
                } else {
                    &[[0.; 2]]
                },
            )?,
            error: upload(
                ctx,
                stream,
                if (16..32).contains(&key) {
                    &packed.error
                } else {
                    &[[0.; 2]]
                },
            )?,
            native: upload(
                ctx,
                stream,
                if key > 0 && key < 16 {
                    &packed.native[..2 * data.p * data.p]
                } else {
                    &packed.native
                },
            )?,
            cb: upload(ctx, stream, &packed.cb)?,
            s: upload(ctx, stream, &vec![0; ns])?,
            se: upload(ctx, stream, &vec![0; ne])?,
            v: upload(ctx, stream, &vec![[0.; 2]; 5 * data.p])?,
            raw: upload(ctx, stream, &data.initial)?,
            cs: upload(ctx, stream, &vec![0; ns])?,
            ce: upload(ctx, stream, &vec![0; ne])?,
            cv: upload(ctx, stream, &vec![[0.; 2]; 5 * data.p])?,
            cr: upload(ctx, stream, &vec![0.; 5 * data.p])?,
            report: upload(ctx, stream, &zeros)?,
            zeros,
            refs: upload(ctx, stream, &vec![[0.; 2]; 4 * data.p])?,
            norms: upload(ctx, stream, &vec![0.; 8 * b])?,
            pending: upload(ctx, stream, &vec![0; 2 * b])?,
            start: Event::new(ctx)?,
            end: Event::new(ctx)?,
        };
        if k != 0 {
            launch(
                &module.function(&format!("prepare_4_{k}"))?,
                LaunchConfig {
                    grid: (b * b) as u32,
                    block: 32,
                    shared_memory: 0,
                },
                &[
                    A::DevicePtr(e.a.as_device_ptr()),
                    A::DevicePtr(e.fr.as_device_ptr()),
                    A::DevicePtr(e.masks.as_device_ptr()),
                ],
                stream,
            )?;
        }
        e.reset(module, stream, &data.initial, 0, 0)?;
        Ok(e)
    }
    pub fn reset(
        &mut self,
        module: &Module,
        stream: &Stream,
        raw: &[f64],
        logical: u32,
        generation: u32,
    ) -> Result<()> {
        if raw.len() != self.raw.len() || raw.iter().any(|v| !v.is_finite()) {
            return Err("invalid reset state".into());
        }
        self.raw.copy_from(raw, stream)?;
        self.logical = logical;
        self.generation = generation;
        self.since_audit = 0;
        self.faulted = false;
        let result = self.run(module, stream, 0, 0, 1.)?;
        if result.flags.iter().any(|v| *v != 0) {
            return Err("unrepresentable reset state".into());
        }
        self.checkpoint(module, stream, false)?;
        Ok(())
    }
    pub fn run(
        &mut self,
        module: &Module,
        stream: &Stream,
        op: u32,
        count: u32,
        limit: f64,
    ) -> Result<Step> {
        if op == 1
            && (self.faulted
                || count == 0
                || count > 32
                || self.since_audit + count > 200
                || !limit.is_finite()
                || limit <= 0.)
        {
            return Err("unsafe submission".into());
        }
        self.report.copy_from(&self.zeros, stream)?;
        let args = [
            A::DevicePtr(self.a.as_device_ptr()),
            A::DevicePtr(self.ae.as_device_ptr()),
            A::DevicePtr(self.fr.as_device_ptr()),
            A::DevicePtr(self.masks.as_device_ptr()),
            A::DevicePtr(self.original.as_device_ptr()),
            A::DevicePtr(self.error.as_device_ptr()),
            A::DevicePtr(self.native.as_device_ptr()),
            A::DevicePtr(self.cb.as_device_ptr()),
            A::DevicePtr(self.s.as_device_ptr()),
            A::DevicePtr(self.se.as_device_ptr()),
            A::DevicePtr(self.v.as_device_ptr()),
            A::DevicePtr(self.raw.as_device_ptr()),
            A::DevicePtr(self.report.as_device_ptr()),
            A::DevicePtr(self.report.as_device_ptr() + 4 * u64::from(self.b + 1)),
            A::U32(self.n),
            A::U32(self.m),
            A::U32(self.b),
            A::U32(op),
            A::U32(count),
            A::U32(self.shift),
            A::F64(limit),
            A::U32(self.extra),
        ];
        self.start.record(stream)?;
        if self.k >= 32 && op == 1 {
            self.grid_run(module, stream, count, limit)?;
        } else {
            launch(
                &module.function(&if self.k.is_multiple_of(16) {
                    "accel_64_1".into()
                } else {
                    format!(
                        "accel_{}4_{}",
                        if (16..32).contains(&self.k) {
                            "scalar_"
                        } else {
                            ""
                        },
                        self.k % 16
                    )
                })?,
                LaunchConfig {
                    grid: 1,
                    block: self.b * 32,
                    shared_memory: 0,
                },
                &args,
                stream,
            )?;
        }
        self.end.record(stream)?;
        let report = download(&self.report, stream)?;
        let gpu_us = f64::from(self.start.elapsed_to(&self.end)?) * 1000.;
        let done = report[self.b as usize];
        self.logical += done;
        self.since_audit += done;
        let flags = report[..self.b as usize].to_vec();
        self.faulted |= flags.iter().any(|v| *v != 0);
        Ok(Step {
            done,
            flags,
            terms: report[self.b as usize + 1..]
                .iter()
                .map(|v| f32::from_bits(*v))
                .collect(),
            gpu_us,
        })
    }
    fn grid_run(&self, module: &Module, stream: &Stream, count: u32, limit: f64) -> Result<()> {
        let native = self.k.is_multiple_of(16);
        let function = module.function(&if native {
            "grid_native".into()
        } else {
            format!("grid_4_{}", self.k % 16)
        })?;
        let guard = module.function("grid_guard")?;
        let run = |op: u32, is_guard: bool| -> Result<()> {
            let args = [
                A::DevicePtr(self.a.as_device_ptr()),
                A::DevicePtr(self.ae.as_device_ptr()),
                A::DevicePtr(self.fr.as_device_ptr()),
                A::DevicePtr(self.masks.as_device_ptr()),
                A::DevicePtr(self.native.as_device_ptr()),
                A::DevicePtr(self.cb.as_device_ptr()),
                A::DevicePtr(self.s.as_device_ptr()),
                A::DevicePtr(self.se.as_device_ptr()),
                A::DevicePtr(self.v.as_device_ptr()),
                A::DevicePtr(self.raw.as_device_ptr()),
                A::DevicePtr(self.report.as_device_ptr()),
                A::DevicePtr(self.report.as_device_ptr() + 4 * u64::from(self.b + 1)),
                A::DevicePtr(self.refs.as_device_ptr()),
                A::DevicePtr(self.norms.as_device_ptr()),
                A::DevicePtr(self.pending.as_device_ptr()),
                A::U32(self.n),
                A::U32(self.m),
                A::U32(self.b),
                A::U32(self.shift),
                A::F64(limit),
                A::U32(op),
            ];
            launch(
                if is_guard { &guard } else { &function },
                LaunchConfig {
                    grid: if is_guard { 1 } else { self.b },
                    block: if is_guard { 32 } else { 256 },
                    shared_memory: 0,
                },
                &args,
                stream,
            )?;
            Ok(())
        };
        if !native {
            run(0, false)?;
        }
        for _ in 0..count {
            run(1, false)?;
            run(2, false)?;
            run(if native { 4 } else { 0 }, true)?;
        }
        if !native {
            run(3, false)?;
        }
        Ok(())
    }
    pub fn raw(&self, module: &Module, stream: &Stream) -> Result<Vec<f64>> {
        if !self.k.is_multiple_of(16) {
            launch(
                &module.function("export_pairs")?,
                LaunchConfig {
                    grid: self.raw.len().div_ceil(128) as u32,
                    block: 128,
                    shared_memory: 0,
                },
                &[
                    A::DevicePtr(self.v.as_device_ptr()),
                    A::DevicePtr(self.raw.as_device_ptr()),
                    A::U32(self.raw.len() as u32),
                ],
                stream,
            )?;
        }
        download(&self.raw, stream)
    }
    pub fn product(
        &mut self,
        module: &Module,
        stream: &Stream,
        transpose: bool,
    ) -> Result<Vec<f64>> {
        self.run(module, stream, if transpose { 3 } else { 4 }, 0, 1.)?;
        Ok(download(&self.raw, stream)?[..self.b as usize * 32].to_vec())
    }
    pub fn snapshot(&self, module: &Module, stream: &Stream) -> Result<Snapshot> {
        Ok(Snapshot {
            raw: self.raw(module, stream)?,
            codes: download(&self.s, stream)?,
            exponents: download(&self.se, stream)?,
            pairs: download(&self.v, stream)?,
            logical: self.logical,
            generation: self.generation,
        })
    }
    pub fn saved_snapshot(&self, stream: &Stream) -> Result<Snapshot> {
        Ok(Snapshot {
            raw: download(&self.cr, stream)?,
            codes: download(&self.cs, stream)?,
            exponents: download(&self.ce, stream)?,
            pairs: download(&self.cv, stream)?,
            logical: self.saved_logical,
            generation: self.generation,
        })
    }
    pub fn checkpoint(&mut self, module: &Module, stream: &Stream, restore: bool) -> Result<()> {
        if !restore && self.faulted {
            return Err("unsafe checkpoint adoption".into());
        }
        // A checkpoint must be self-consistent even without a preceding host export.
        if !restore && !self.k.is_multiple_of(16) {
            launch(
                &module.function("export_pairs")?,
                LaunchConfig {
                    grid: self.raw.len().div_ceil(128) as u32,
                    block: 128,
                    shared_memory: 0,
                },
                &[
                    A::DevicePtr(self.v.as_device_ptr()),
                    A::DevicePtr(self.raw.as_device_ptr()),
                    A::U32(self.raw.len() as u32),
                ],
                stream,
            )?;
        }
        let (a, e, v, r, oa, oe, ov, oraw) = if restore {
            (
                self.cs.as_device_ptr(),
                self.ce.as_device_ptr(),
                self.cv.as_device_ptr(),
                self.cr.as_device_ptr(),
                self.s.as_device_ptr(),
                self.se.as_device_ptr(),
                self.v.as_device_ptr(),
                self.raw.as_device_ptr(),
            )
        } else {
            (
                self.s.as_device_ptr(),
                self.se.as_device_ptr(),
                self.v.as_device_ptr(),
                self.raw.as_device_ptr(),
                self.cs.as_device_ptr(),
                self.ce.as_device_ptr(),
                self.cv.as_device_ptr(),
                self.cr.as_device_ptr(),
            )
        };
        launch(
            &module.function("checkpoint")?,
            LaunchConfig {
                grid: self
                    .s
                    .len()
                    .max(self.se.len())
                    .max(self.raw.len())
                    .div_ceil(128) as u32,
                block: 128,
                shared_memory: 0,
            },
            &[
                A::DevicePtr(a),
                A::DevicePtr(e),
                A::DevicePtr(v),
                A::DevicePtr(r),
                A::DevicePtr(oa),
                A::DevicePtr(oe),
                A::DevicePtr(ov),
                A::DevicePtr(oraw),
                A::U32(self.s.len() as u32),
                A::U32(self.se.len() as u32),
                A::U32(self.raw.len() as u32),
            ],
            stream,
        )?;
        stream.synchronize()?;
        if restore {
            self.logical = self.saved_logical;
            self.generation = self
                .generation
                .checked_add(1)
                .ok_or("generation overflow")?;
            self.faulted = false;
        } else {
            self.saved_logical = self.logical;
        }
        self.since_audit = 0;
        Ok(())
    }
}
