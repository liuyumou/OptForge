use crate::{Result, model::Data};
use optimizer_cuda_sys::{
    Argument as A, Context, DeviceBuffer, LaunchConfig, Module, Stream, events::Event, launch,
};
use serde::Serialize;
use std::rc::Rc;
fn upload<T: Copy>(ctx: &Rc<Context>, stream: &Stream, data: &[T]) -> Result<DeviceBuffer<T>> {
    let mut b = ctx.allocate(data.len())?;
    b.copy_from(data, stream)?;
    Ok(b)
}
fn download<T: Copy + Default>(b: &DeviceBuffer<T>, stream: &Stream) -> Result<Vec<T>> {
    let mut v = vec![T::default(); b.len()];
    b.copy_to(&mut v, stream)?;
    Ok(v)
}
#[derive(Serialize, Clone, Debug)]
pub struct Snapshot {
    pub raw: Vec<f64>,
    pub logical: u32,
    pub generation: u32,
}
#[derive(Serialize, Clone, Debug)]
pub struct Step {
    pub done: u32,
    pub flags: Vec<u32>,
    pub terms: Vec<f64>,
    pub gpu_us: f64,
}
#[derive(Serialize)]
pub struct Product {
    pub product: Vec<f64>,
    pub bound: Vec<f64>,
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
    a: DeviceBuffer<u32>,
    ae: DeviceBuffer<i32>,
    fr: DeviceBuffer<u32>,
    masks: DeviceBuffer<u32>,
    native: DeviceBuffer<f64>,
    cb: DeviceBuffer<f64>,
    an: DeviceBuffer<f64>,
    codes: DeviceBuffer<u32>,
    ex: DeviceBuffer<i32>,
    raw: DeviceBuffer<f64>,
    saved: DeviceBuffer<f64>,
    flags: DeviceBuffer<u32>,
    refs: DeviceBuffer<f64>,
    norms: DeviceBuffer<f64>,
    pending: DeviceBuffer<u32>,
    errors: DeviceBuffer<f64>,
    products: DeviceBuffer<f64>,
    start: Event,
    end: Event,
}
impl Engine {
    pub fn replace_bounds(&mut self, data: &Data, stream: &Stream) -> Result<()> {
        if self.cb.len() != data.cb.len() {
            return Err("scenario bounds shape".into());
        }
        self.cb.copy_from(&data.cb, stream)?;
        stream.synchronize()?;
        Ok(())
    }

    pub fn new(
        data: &Data,
        key: usize,
        ctx: &Rc<Context>,
        module: &Module,
        stream: &Stream,
    ) -> Result<Self> {
        if ![32, 34, 36].contains(&key) {
            return Err("unsupported lane".into());
        }
        let k = key % 16;
        let p = data.p;
        let b = p / 32;
        let packed = data.pack(k)?;
        // Per-engine conservative bound; at most three engines per session (<12 GiB total).
        let bytes = 16 * p * p + 4 * b * b * k * 640 + 1024 * p;
        if bytes > 4usize << 30 {
            return Err("device allocation bound".into());
        }
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
            a: upload(ctx, stream, &packed.codes)?,
            ae: upload(ctx, stream, &packed.exponents)?,
            fr: upload(ctx, stream, &vec![0; (b * b * k * 512).max(1)])?,
            masks: upload(ctx, stream, &vec![0; (b * b).max(1)])?,
            native: upload(ctx, stream, &packed.native)?,
            cb: upload(ctx, stream, &data.cb)?,
            an: upload(ctx, stream, &packed.norms)?,
            codes: upload(ctx, stream, &vec![0; (2 * b * k * 4).max(1)])?,
            ex: upload(ctx, stream, &vec![0; (2 * b * k).max(1)])?,
            raw: upload(ctx, stream, &data.initial)?,
            saved: upload(ctx, stream, &vec![0.; 5 * p])?,
            flags: upload(ctx, stream, &vec![0; b + 1])?,
            refs: upload(ctx, stream, &vec![0.; 4 * p])?,
            norms: upload(ctx, stream, &vec![0.; 8 * b])?,
            pending: upload(ctx, stream, &vec![0; 2 * b])?,
            errors: upload(ctx, stream, &vec![0.; 2 * b])?,
            products: upload(ctx, stream, &vec![0.; 2 * p])?,
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
        if raw.len() != self.raw.len()
            || raw.iter().any(|v| {
                !v.is_finite() || (!self.k.is_multiple_of(16) && v.abs() > 6. * 2_f64.powi(47))
            })
        {
            return Err("invalid reset state".into());
        }
        self.raw.copy_from(raw, stream)?;
        self.logical = logical;
        self.generation = generation;
        self.since_audit = 0;
        self.faulted = false;
        self.flags
            .copy_from(&vec![0; self.b as usize + 1], stream)?;
        self.checkpoint(module, stream, false)
    }
    fn submit(&self, module: &Module, stream: &Stream, op: u32, limit: f64) -> Result<()> {
        let name = if self.k.is_multiple_of(16) {
            "mixed_native".into()
        } else {
            format!("mixed_{}", self.k % 16)
        };
        launch(
            &module.function(&name)?,
            LaunchConfig {
                grid: self.b,
                block: 256,
                shared_memory: 0,
            },
            &[
                A::DevicePtr(self.a.as_device_ptr()),
                A::DevicePtr(self.ae.as_device_ptr()),
                A::DevicePtr(self.fr.as_device_ptr()),
                A::DevicePtr(self.masks.as_device_ptr()),
                A::DevicePtr(self.native.as_device_ptr()),
                A::DevicePtr(self.cb.as_device_ptr()),
                A::DevicePtr(self.an.as_device_ptr()),
                A::DevicePtr(self.codes.as_device_ptr()),
                A::DevicePtr(self.ex.as_device_ptr()),
                A::DevicePtr(self.raw.as_device_ptr()),
                A::DevicePtr(self.flags.as_device_ptr()),
                A::DevicePtr(self.refs.as_device_ptr()),
                A::DevicePtr(self.norms.as_device_ptr()),
                A::DevicePtr(self.pending.as_device_ptr()),
                A::DevicePtr(self.errors.as_device_ptr()),
                A::DevicePtr(self.products.as_device_ptr()),
                A::U32(self.n),
                A::U32(self.m),
                A::U32(self.b),
                A::U32(self.shift),
                A::F64(limit),
                A::U32(op),
            ],
            stream,
        )?;
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
        if op != 1
            || self.faulted
            || count == 0
            || count > 32
            || self.since_audit + count > 200
            || !limit.is_finite()
            || limit <= 0.
        {
            return Err("unsafe submission".into());
        }
        self.flags
            .copy_from(&vec![0; self.b as usize + 1], stream)?;
        self.errors
            .copy_from(&vec![0.; 2 * self.b as usize], stream)?;
        self.start.record(stream)?;
        if !self.k.is_multiple_of(16) {
            self.submit(module, stream, 0, limit)?;
        }
        let guard = module.function("mixed_guard")?;
        for _ in 0..count {
            self.submit(module, stream, 1, limit)?;
            self.submit(module, stream, 2, limit)?;
            launch(
                &guard,
                LaunchConfig {
                    grid: 1,
                    block: 128,
                    shared_memory: 0,
                },
                &[
                    A::DevicePtr(self.flags.as_device_ptr()),
                    A::DevicePtr(self.pending.as_device_ptr()),
                    A::U32(self.b),
                ],
                stream,
            )?;
        }
        self.end.record(stream)?;
        let f = download(&self.flags, stream)?;
        let errs = download(&self.errors, stream)?;
        let gpu_us = f64::from(self.start.elapsed_to(&self.end)?) * 1000.;
        let done = f[self.b as usize];
        self.logical += done;
        self.since_audit += done;
        let flags = f[..self.b as usize].to_vec();
        self.faulted |= flags.iter().any(|v| *v != 0);
        let mut terms = vec![0.; 8];
        terms[0] = errs.into_iter().fold(0., f64::max);
        Ok(Step {
            done,
            flags,
            terms,
            gpu_us,
        })
    }
    pub fn raw(&self, _module: &Module, stream: &Stream) -> Result<Vec<f64>> {
        download(&self.raw, stream)
    }
    pub fn snapshot(&self, module: &Module, stream: &Stream) -> Result<Snapshot> {
        Ok(Snapshot {
            raw: self.raw(module, stream)?,
            logical: self.logical,
            generation: self.generation,
        })
    }
    pub fn saved_snapshot(&self, stream: &Stream) -> Result<Snapshot> {
        Ok(Snapshot {
            raw: download(&self.saved, stream)?,
            logical: self.saved_logical,
            generation: self.generation,
        })
    }
    pub fn checkpoint(&mut self, module: &Module, stream: &Stream, restore: bool) -> Result<()> {
        if !restore && self.faulted {
            return Err("unsafe checkpoint adoption".into());
        }
        let generation = if restore {
            self.generation
                .checked_add(1)
                .ok_or("generation overflow")?
        } else {
            self.generation
        };
        let (src, dst) = if restore {
            (self.saved.as_device_ptr(), self.raw.as_device_ptr())
        } else {
            (self.raw.as_device_ptr(), self.saved.as_device_ptr())
        };
        launch(
            &module.function("mixed_copy")?,
            LaunchConfig {
                grid: self.raw.len().div_ceil(128) as u32,
                block: 128,
                shared_memory: 0,
            },
            &[
                A::DevicePtr(src),
                A::DevicePtr(dst),
                A::U32(self.raw.len() as u32),
            ],
            stream,
        )?;
        stream.synchronize()?;
        if restore {
            self.logical = self.saved_logical;
            self.generation = generation;
            self.faulted = false;
        } else {
            self.saved_logical = self.logical;
        }
        self.since_audit = 0;
        Ok(())
    }
    pub fn product(
        &mut self,
        module: &Module,
        stream: &Stream,
        tr: bool,
        centered: bool,
    ) -> Result<Product> {
        if self.faulted || (centered && self.since_audit == 0) {
            return Err("unsafe product inspection".into());
        }
        self.flags
            .copy_from(&vec![0; self.b as usize + 1], stream)?;
        if !self.k.is_multiple_of(16) && !centered {
            self.submit(module, stream, 6, 1.)?;
        }
        self.submit(
            module,
            stream,
            if centered {
                if tr { 9 } else { 8 }
            } else if tr {
                5
            } else {
                4
            },
            1.,
        )?;
        if download(&self.flags, stream)?.iter().any(|v| *v != 0) {
            return Err("product conversion refused".into());
        }
        let v = download(&self.products, stream)?;
        let p = self.b as usize * 32;
        Ok(Product {
            product: v[..p].to_vec(),
            bound: v[p..].to_vec(),
        })
    }
    pub fn benchmark_product(
        &mut self,
        module: &Module,
        stream: &Stream,
        tr: bool,
        count: u32,
        guarded: bool,
    ) -> Result<serde_json::Value> {
        if self.faulted || count == 0 || count > 1024 {
            return Err("product benchmark limits".into());
        }
        let start = std::time::Instant::now();
        self.flags
            .copy_from(&vec![0; self.b as usize + 1], stream)?;
        if !self.k.is_multiple_of(16) {
            self.submit(module, stream, 6, 1.)?;
        }
        if download(&self.flags, stream)?.iter().any(|v| *v != 0) {
            return Err("product conversion refused".into());
        }
        let preparation_ns = start.elapsed().as_nanos();
        self.start.record(stream)?;
        let op = if guarded {
            if tr { 5 } else { 4 }
        } else if tr {
            13
        } else {
            12
        };
        for _ in 0..count {
            self.submit(module, stream, op, 1.)?;
        }
        self.end.record(stream)?;
        let result = download(&self.products, stream)?;
        let gpu_us = f64::from(self.start.elapsed_to(&self.end)?) * 1000.;
        let p = self.b as usize * 32;
        Ok(
            serde_json::json!({"count":count,"guarded":guarded,"gpu_us":gpu_us,"preparation_ns":preparation_ns,"complete_ns":start.elapsed().as_nanos(),"product":result[..p],"bound":result[p..]}),
        )
    }
}
