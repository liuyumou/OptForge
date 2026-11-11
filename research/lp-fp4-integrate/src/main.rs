//! Safe persistent research service. CPU checker mode never creates a CUDA context.
mod checker;
use optimizer_core::Model;
use optimizer_cuda_sys::events::Event;
use optimizer_cuda_sys::{
    Argument as A, Context, DeviceBuffer, LaunchConfig, Module, Stream, launch,
};
use optimizer_experiment::sha256::hex;
use optimizer_lp::LinearProgram;
use serde::{Deserialize, Serialize};
use serde_json::{Value, json};
use std::{
    fs,
    io::{self, BufRead, Read, Write},
    path::Path,
    rc::Rc,
    time::Instant,
};
type Result<T> = std::result::Result<T, Box<dyn std::error::Error>>;
const DEVICE: &str = "GPU-6721b13a-30f9-83ec-dace-ba2d9738556f";
#[derive(Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
struct Request {
    format: u32,
    components: u32,
    codes: Vec<u32>,
    exponents: Vec<i32>,
    initial: Vec<f64>,
    shift: u32,
    max_updates: u32,
    initial_iteration: u32,
}
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Command {
    #[serde(default)]
    solve_id: u32,
    op: String,
    generation: u32,
    #[serde(default)]
    count: u32,
    #[serde(default)]
    limit: f64,
    #[serde(default)]
    request: Option<Request>,
}
fn valid(r: &Request, p: &LinearProgram) -> Result<()> {
    let b = p.row_count().max(p.column_count()).div_ceil(32);
    let k = r.components as usize;
    let f = r.format as usize;
    if !(1..=4).contains(&b)
        || ![(64, 1), (4, 2), (4, 4), (4, 8), (8, 4), (16, 2)].contains(&(f, k))
        || !(1..=24).contains(&r.shift)
        || !(1..=10000).contains(&r.max_updates)
        || r.initial_iteration > r.max_updates
        || r.initial.len() != 5 * b * 32
        || r.initial.iter().any(|v| !v.is_finite())
        || r.codes.len() != if f == 64 { 1 } else { b * b * k * 32 * f }
        || r.exponents.len() != if f == 64 { 1 } else { b * b * k }
        || r.exponents.iter().any(|e| !(-48..=48).contains(e))
    {
        return Err("request shape/range".into());
    }
    for v in 0..5 {
        let size = if v == 1 || v == 4 {
            p.row_count()
        } else {
            p.column_count()
        };
        if r.initial[v * b * 32 + size..(v + 1) * b * 32]
            .iter()
            .any(|x| *x != 0.)
        {
            return Err("state padding".into());
        }
    }
    Ok(())
}
fn upload<T: Copy>(ctx: &Rc<Context>, stream: &Stream, data: &[T]) -> Result<DeviceBuffer<T>> {
    let mut b = ctx.allocate(data.len())?;
    b.copy_from(data, stream)?;
    Ok(b)
}
fn download<T: Copy + Default>(b: &DeviceBuffer<T>, stream: &Stream) -> Result<Vec<T>> {
    let mut out = vec![T::default(); b.len()];
    b.copy_to(&mut out, stream)?;
    Ok(out)
}
fn decoded(code: u32, f: u32) -> f64 {
    let (sign, mag) = if f == 4 {
        (code & 8, code & 7)
    } else if f == 8 {
        (code & 128, code & 127)
    } else {
        (code & 32768, code & 32767)
    };
    let v = if f == 4 {
        [0., 0.5, 1., 1.5, 2., 3., 4., 6.][mag as usize]
    } else if f == 8 {
        let e = mag >> 3;
        let m = mag & 7;
        if e == 0 {
            f64::from(m) * 2_f64.powi(-9)
        } else {
            (1. + f64::from(m) / 8.) * 2_f64.powi(e as i32 - 7)
        }
    } else {
        let e = mag >> 10;
        let m = mag & 1023;
        if e == 0 {
            f64::from(m) * 2_f64.powi(-24)
        } else {
            (1. + f64::from(m) / 1024.) * 2_f64.powi(e as i32 - 15)
        }
    };
    if sign == 0 { v } else { -v }
}
fn prepared(r: &Request, p: &LinearProgram) -> Result<(Vec<f64>, Vec<f64>)> {
    let b = p.row_count().max(p.column_count()).div_ceil(32);
    let n = b * 32;
    let k = r.components as usize;
    let f = r.format as usize;
    let mut a = vec![0.; n * n];
    for (i, j, v) in p.row_major().entries() {
        a[i * n + j as usize] = v;
    }
    let mut cb = vec![0.; 5 * n + 5];
    cb[..p.column_count()].copy_from_slice(p.objective());
    for (i, v) in p.columns().iter().enumerate() {
        cb[n + i] = v.lower;
        cb[2 * n + i] = v.upper;
    }
    for (i, v) in p.rows().iter().enumerate() {
        cb[3 * n + i] = v.lower;
        cb[4 * n + i] = v.upper;
    }
    let mut er = vec![0.; n];
    let mut ec = vec![0.; n];
    if f != 64 {
        for i in 0..n {
            for j in 0..n {
                let tile = i / 32 * b + j / 32;
                let index = i % 32 * 32 + j % 32;
                let mut h = 0.;
                for plane in 0..k {
                    let word = r.codes[(tile * k + plane) * 32 * f + index / (32 / f)];
                    let code = (word >> ((index % (32 / f)) * f)) & ((1 << f) - 1);
                    if (f == 4 && code == 8)
                        || (f == 8 && (code == 128 || code & 127 == 127))
                        || (f == 16 && (code == 32768 || code & 0x7c00 == 0x7c00))
                    {
                        return Err("noncanonical packed coefficient".into());
                    }
                    h += decoded(code, f as u32) * 2_f64.powi(r.exponents[tile * k + plane]);
                }
                if (i >= p.row_count() || j >= p.column_count()) && h != 0. {
                    return Err("matrix padding".into());
                }
                let error = (a[i * n + j] - h).abs();
                er[i] += error;
                ec[j] += error;
            }
        }
    }
    cb[5 * n] = (0..n)
        .map(|i| a[i * n..(i + 1) * n].iter().map(|v| v.abs()).sum::<f64>())
        .fold(0., f64::max);
    cb[5 * n + 1] = (0..n)
        .map(|j| (0..n).map(|i| a[i * n + j].abs()).sum::<f64>())
        .fold(0., f64::max);
    cb[5 * n + 2] = er.into_iter().fold(0., f64::max);
    cb[5 * n + 3] = ec.into_iter().fold(0., f64::max);
    cb[5 * n + 4] = cb[..5 * n]
        .iter()
        .filter(|v| v.is_finite())
        .map(|&v| {
            let h = f64::from(v as f32);
            (v - h - f64::from((v - h) as f32)).abs()
        })
        .fold(0., f64::max);
    // Exact CSR/CSC controls skip structural zeros, retaining original term order.
    let nnz = a.iter().filter(|v| **v != 0.).count();
    cb.push(nnz as f64);
    for transpose in [false, true] {
        let mut offsets = vec![0.];
        let mut indices = Vec::with_capacity(nnz);
        let mut values = Vec::with_capacity(nnz);
        for i in 0..n {
            for j in 0..n {
                let value = a[if transpose { j * n + i } else { i * n + j }];
                if value != 0. {
                    indices.push(j as f64);
                    values.push(value);
                }
            }
            offsets.push(indices.len() as f64);
        }
        a.extend(offsets);
        a.extend(indices);
        a.extend(values);
    }
    Ok((a, cb))
}
struct Engine {
    format: u32,
    k: u32,
    b: u32,
    n: u32,
    m: u32,
    shift: u32,
    generation: u32,
    logical: u32,
    saved_logical: u32,
    since_audit: u32,
    faulted: bool,
    restored: bool,
    a: DeviceBuffer<u32>,
    ae: DeviceBuffer<i32>,
    fr: DeviceBuffer<u32>,
    masks: DeviceBuffer<u32>,
    original: DeviceBuffer<f64>,
    cb: DeviceBuffer<f64>,
    s: DeviceBuffer<u32>,
    se: DeviceBuffer<i32>,
    raw: DeviceBuffer<f64>,
    flags: DeviceBuffer<u32>,
    metrics: DeviceBuffer<f32>,
    cs: DeviceBuffer<u32>,
    ce: DeviceBuffer<i32>,
    cr: DeviceBuffer<f64>,
    start: Event,
    end: Event,
}
impl Engine {
    fn new(
        r: &Request,
        p: &LinearProgram,
        ctx: &Rc<Context>,
        module: &Module,
        stream: &Stream,
        generation: u32,
    ) -> Result<Self> {
        valid(r, p)?;
        let b = p.row_count().max(p.column_count()).div_ceil(32);
        let k = r.components as usize;
        let f = r.format as usize;
        let (a, cb) = prepared(r, p)?;
        let ns = if f == 64 { 1 } else { 5 * b * k * f };
        let ne = if f == 64 { 1 } else { 5 * b * k };
        let mut e = Self {
            format: r.format,
            k: r.components,
            b: b as u32,
            n: p.column_count() as u32,
            m: p.row_count() as u32,
            shift: r.shift,
            generation,
            logical: r.initial_iteration,
            saved_logical: r.initial_iteration,
            since_audit: 0,
            faulted: false,
            restored: false,
            a: upload(ctx, stream, &r.codes)?,
            ae: upload(ctx, stream, &r.exponents)?,
            fr: upload(
                ctx,
                stream,
                &vec![0; b * b * k * 512 * if f == 16 { 2 } else { 1 }],
            )?,
            masks: upload(ctx, stream, &vec![0; b * b])?,
            original: upload(ctx, stream, &a)?,
            cb: upload(ctx, stream, &cb)?,
            s: upload(ctx, stream, &vec![0; ns])?,
            se: upload(ctx, stream, &vec![0; ne])?,
            raw: upload(ctx, stream, &r.initial)?,
            flags: upload(ctx, stream, &[0; 5])?,
            metrics: upload(ctx, stream, &vec![0.; b * 7])?,
            cs: upload(ctx, stream, &vec![0; ns])?,
            ce: upload(ctx, stream, &vec![0; ne])?,
            cr: upload(ctx, stream, &vec![0.; r.initial.len()])?,
            start: Event::new(ctx)?,
            end: Event::new(ctx)?,
        };
        if f != 64 {
            launch(
                &module.function(&format!("iprepare_{f}_{k}"))?,
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
        e.run(module, stream, 0, 0, 1.)?;
        e.checkpoint(module, stream, false)?;
        Ok(e)
    }
    fn run(
        &mut self,
        module: &Module,
        stream: &Stream,
        op: u32,
        count: u32,
        limit: f64,
    ) -> Result<Value> {
        if op == 1
            && (self.faulted
                || count == 0
                || count > 32
                || self.since_audit + count > 200
                || !limit.is_finite()
                || limit <= 0.)
        {
            return Err("submission crosses boundary".into());
        }
        let args = [
            A::DevicePtr(self.a.as_device_ptr()),
            A::DevicePtr(self.ae.as_device_ptr()),
            A::DevicePtr(self.fr.as_device_ptr()),
            A::DevicePtr(self.masks.as_device_ptr()),
            A::DevicePtr(self.original.as_device_ptr()),
            A::DevicePtr(self.cb.as_device_ptr()),
            A::DevicePtr(self.s.as_device_ptr()),
            A::DevicePtr(self.se.as_device_ptr()),
            A::DevicePtr(self.raw.as_device_ptr()),
            A::DevicePtr(self.flags.as_device_ptr()),
            A::DevicePtr(self.metrics.as_device_ptr()),
            A::U32(self.n),
            A::U32(self.m),
            A::U32(self.b),
            A::U32(op),
            A::U32(count),
            A::U32(self.shift),
            A::F64(limit),
        ];
        self.flags.copy_from(&[0; 5], stream)?;
        self.start.record(stream)?;
        launch(
            &module.function(&format!("integrate_{}_{}", self.format, self.k))?,
            LaunchConfig {
                grid: 1,
                block: self.b * 32,
                shared_memory: 0,
            },
            &args,
            stream,
        )?;
        self.end.record(stream)?;
        // copy_to synchronizes this stream; no extra host fence is needed.
        let flags = download(&self.flags, stream)?;
        let gpu_us = f64::from(self.start.elapsed_to(&self.end)?) * 1000.;
        let terms = download(&self.metrics, stream)?;
        if op != 2 {
            self.faulted |= flags[..4].iter().any(|v| *v != 0);
        }
        if op == 1 {
            self.restored = false;
        }
        self.logical += flags[4];
        self.since_audit += flags[4];
        Ok(
            json!({"flags":flags,"local_terms":terms,"gpu_us":gpu_us,"generation":self.generation,"logical":self.logical}),
        )
    }
    fn checkpoint(&mut self, module: &Module, stream: &Stream, restore: bool) -> Result<()> {
        if !restore && self.faulted {
            return Err("unsafe checkpoint adoption".into());
        }
        let (src, ex, raw, dst, de, dr) = if restore {
            (
                self.cs.as_device_ptr(),
                self.ce.as_device_ptr(),
                self.cr.as_device_ptr(),
                self.s.as_device_ptr(),
                self.se.as_device_ptr(),
                self.raw.as_device_ptr(),
            )
        } else {
            (
                self.s.as_device_ptr(),
                self.se.as_device_ptr(),
                self.raw.as_device_ptr(),
                self.cs.as_device_ptr(),
                self.ce.as_device_ptr(),
                self.cr.as_device_ptr(),
            )
        };
        let size = self.s.len().max(self.se.len()).max(self.raw.len());
        launch(
            &module.function("checkpoint")?,
            LaunchConfig {
                grid: size.div_ceil(128) as u32,
                block: 128,
                shared_memory: 0,
            },
            &[
                A::DevicePtr(src),
                A::DevicePtr(ex),
                A::DevicePtr(raw),
                A::DevicePtr(dst),
                A::DevicePtr(de),
                A::DevicePtr(dr),
                A::U32(self.s.len() as u32),
                A::U32(self.se.len() as u32),
                A::U32(self.raw.len() as u32),
            ],
            stream,
        )?;
        stream.synchronize()?;
        if restore {
            self.logical = self.saved_logical;
            self.faulted = false;
            self.restored = true;
            self.generation = self
                .generation
                .checked_add(1)
                .ok_or("generation overflow")?;
        } else {
            self.saved_logical = self.logical;
        }
        self.since_audit = 0;
        Ok(())
    }
    fn export(&mut self, module: &Module, stream: &Stream, model: &[u8]) -> Result<Value> {
        self.run(module, stream, 2, 0, 1.)?;
        let raw = download(&self.raw, stream)?;
        let endpoint = checker::Endpoint {
            model_sha256: hex(model),
            primal: raw[..self.n as usize].to_vec(),
            dual: raw[(self.b * 32) as usize..(self.b * 32 + self.m) as usize].to_vec(),
            transport: "completed".into(),
        };
        Ok(
            json!({"raw":raw,"codes":download(&self.s,stream)?,"exponents":download(&self.se,stream)?,"endpoint":endpoint,"generation":self.generation,"logical":self.logical}),
        )
    }
}
fn emit(v: &Value) -> Result<()> {
    let mut out = io::stdout().lock();
    serde_json::to_writer(&mut out, v)?;
    out.write_all(b"\n")?;
    out.flush()?;
    Ok(())
}
fn serve(image: &Path, model_bytes: &[u8]) -> Result<()> {
    if std::env::var("AI_OPTIMIZER_GPU_LEASE").as_deref() != Ok("inherited")
        || std::env::var("CUDA_VISIBLE_DEVICES").as_deref() != Ok(DEVICE)
    {
        return Err("pinned lease required".into());
    }
    let model = Model::from_json(model_bytes)?;
    let p = LinearProgram::new(&model)?;
    let start = Instant::now();
    let ctx = Rc::new(Context::create(DEVICE)?);
    let module = ctx.load_module_file(image)?;
    let stream = ctx.stream()?;
    emit(
        &json!({"ready":true,"context_ns":start.elapsed().as_nanos(),"model_sha256":hex(model_bytes)}),
    )?;
    let mut engine: Option<Engine> = None;
    let mut physical = 0_u32;
    let mut physical_total = 0_u64;
    let mut solve_id = 0_u32;
    let mut ceiling = None;
    let mut loads = 0;
    let mut cancelled = false;
    let stdin = io::stdin();
    let mut input = stdin.lock();
    loop {
        let mut line = String::new();
        let got = (&mut input).take((8 << 20) + 1).read_line(&mut line)?;
        if got == 0 {
            break;
        }
        if got > 8 << 20 {
            return Err("command too large".into());
        }
        let c: Command = serde_json::from_str(&line)?;
        if c.solve_id != solve_id {
            return Err("stale solve identity".into());
        }
        if c.op == "finish" {
            if cancelled
                || engine.as_ref().is_none_or(|e| e.generation != c.generation)
                || solve_id >= 999
            {
                return Err("invalid solve finish".into());
            }
            stream.synchronize()?;
            engine = None;
            ceiling = None;
            loads = 0;
            physical = 0;
            solve_id += 1;
            emit(&json!({"finished":true,"solve_id":solve_id,"physical_total":physical_total}))?;
            continue;
        }
        if cancelled && c.op != "export" {
            return Err("cancelled service is terminal".into());
        }
        let started = Instant::now();
        let mut result = if c.op == "load" {
            let r = c.request.ok_or("missing request")?;
            loads += 1;
            if loads > 5 || ceiling.is_some_and(|v| v != r.max_updates) {
                return Err("load/budget bound".into());
            }
            ceiling = Some(r.max_updates);
            if let Some(old) = engine.as_mut() {
                if c.generation != old.generation
                    || !old.restored
                    || r.initial_iteration != old.logical
                    || !(r.format == 64
                        || (old.format == 4 && r.format == 4 && r.components > old.k))
                    || old.format == 64
                {
                    return Err("invalid precision transition".into());
                }
                old.run(&module, &stream, 2, 0, 1.)?;
                if download(&old.raw, &stream)? != r.initial {
                    return Err("conversion input differs from checkpoint".into());
                }
            }
            let candidate = Engine::new(&r, &p, &ctx, &module, &stream, c.generation);
            match candidate {
                Ok(mut next) => {
                    next.run(&module, &stream, 2, 0, 1.)?;
                    if engine.is_some() && download(&next.raw, &stream)? != r.initial {
                        json!({"loaded":false,"conversion_failure":true,"generation":c.generation})
                    } else {
                        engine = Some(next);
                        json!({"loaded":true,"generation":c.generation})
                    }
                }
                Err(error) if engine.is_some() => {
                    json!({"loaded":false,"conversion_failure":true,"generation":c.generation,"reason":error.to_string()})
                }
                Err(error) => return Err(error),
            }
        } else {
            let e = engine.as_mut().ok_or("model not loaded")?;
            if e.generation != c.generation {
                return Err("stale generation".into());
            }
            match c.op.as_str() {
                "step" => {
                    if physical
                        .checked_add(c.count)
                        .is_none_or(|v| v > ceiling.unwrap_or(0))
                    {
                        return Err("physical budget exhausted".into());
                    }
                    let v = e.run(&module, &stream, 1, c.count, c.limit)?;
                    let actual = v["flags"][4].as_u64().ok_or("physical count")?;
                    physical += actual as u32;
                    physical_total += actual;
                    v
                }
                "forward" | "transpose" => {
                    e.run(
                        &module,
                        &stream,
                        if c.op == "transpose" { 3 } else { 4 },
                        0,
                        1.,
                    )?;
                    json!({"product":download(&e.raw,&stream)?[..(e.b*32)as usize].to_vec()})
                }
                "export" => e.export(&module, &stream, model_bytes)?,
                "cancel" => {
                    e.checkpoint(&module, &stream, true)?;
                    cancelled = true;
                    json!({"cancelled":true,"generation":e.generation,"logical":e.logical})
                }
                "save" | "restore" => {
                    e.checkpoint(&module, &stream, c.op == "restore")?;
                    json!({"generation":e.generation,"logical":e.logical})
                }
                _ => return Err("unknown operation".into()),
            }
        };
        result["wall_ns"] = json!(started.elapsed().as_nanos());
        result["physical_updates"] = json!(physical);
        result["physical_total"] = json!(physical_total);
        result["solve_id"] = json!(solve_id);
        emit(&result)?;
    }
    Ok(())
}
fn check_service(bytes: &[u8], tier: &str) -> Result<()> {
    let binary_hash = hex(&fs::read(std::env::current_exe()?)?);
    emit(&json!({"ready":true,"checker_binary_sha256":binary_hash}))?;
    let stdin = io::stdin();
    let mut input = stdin.lock();
    loop {
        let mut line = String::new();
        let got = (&mut input).take((8 << 20) + 1).read_line(&mut line)?;
        if got == 0 {
            break;
        }
        if got > 8 << 20 {
            return Err("endpoint too large".into());
        }
        let endpoint: checker::Endpoint = serde_json::from_str(&line)?;
        let mut result = checker::assess(bytes, &endpoint, tier)?;
        result["checker_binary_sha256"] = json!(binary_hash);
        emit(&result)?;
    }
    Ok(())
}
fn main() -> Result<()> {
    let a: Vec<_> = std::env::args().collect();
    if a.len() == 4 && a[1] == "serve" {
        return serve(Path::new(&a[2]), &fs::read(&a[3])?);
    }
    if a.len() == 4 && a[1] == "check-service" {
        return check_service(&fs::read(&a[2])?, &a[3]);
    }
    if a.len() == 6 && a[1] == "check" {
        let bytes = fs::read(&a[2])?;
        let e: checker::Endpoint = serde_json::from_slice(&fs::read(&a[3])?)?;
        let mut result = checker::assess(&bytes, &e, &a[4])?;
        result["checker_binary_sha256"] = json!(hex(&fs::read(std::env::current_exe()?)?));
        let mut out = fs::OpenOptions::new()
            .write(true)
            .create_new(true)
            .open(&a[5])?;
        serde_json::to_writer_pretty(&mut out, &result)?;
        out.write_all(b"\n")?;
        return Ok(());
    }
    Err(
        "usage: serve IMAGE MODEL | check-service MODEL TIER | check MODEL ENDPOINT TIER OUTPUT"
            .into(),
    )
}
#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn codes() {
        assert_eq!(decoded(7, 4), 6.);
        assert_eq!(decoded(15, 4), -6.);
        assert_eq!(decoded(0x38, 8), 1.);
        assert_eq!(decoded(0x3c00, 16), 1.);
        assert_eq!(decoded(1, 16), 2_f64.powi(-24));
    }
    #[test]
    fn command_unknown_field() {
        assert!(
            serde_json::from_str::<Command>(r#"{"op":"save","generation":0,"unexpected":1}"#)
                .is_err()
        );
    }
    #[test]
    fn tier_is_explicit() {
        let e = checker::Endpoint {
            model_sha256: String::new(),
            primal: vec![],
            dual: vec![],
            transport: "completed".into(),
        };
        assert!(checker::assess(b"{}", &e, "default").is_err());
    }
}
