//! Bounded ADR-0036 diagnostic; safe Rust, no solver integration or device fallback.
use optimizer_cuda_sys::{
    Argument as A, Context, DeviceBuffer, LaunchConfig, Module, Stream, launch,
};
use serde_json::{Value as Json, json};
use std::{error::Error, path::Path, rc::Rc, time::Instant};

type Result<T> = std::result::Result<T, Box<dyn Error>>;
const DEVICE: &str = "GPU-6721b13a-30f9-83ec-dace-ba2d9738556f";
const CAP: usize = 64 * 1024 * 1024;
const GUARD: u32 = 0xa5a5_a5a5;
const SENTINEL: Value = Value {
    m: 0xa5a5_a5a5_a5a5_a5a5,
    e: -777,
    sign: 13,
};

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
#[repr(C)]
struct Value {
    m: u64,
    e: i32,
    sign: u32,
}

fn ns(start: Instant) -> u64 {
    u64::try_from(start.elapsed().as_nanos()).unwrap_or(u64::MAX)
}
fn u32_field(j: &Json, key: &str) -> Result<u32> {
    Ok(u32::try_from(
        j[key].as_u64().ok_or("unsigned integer required")?,
    )?)
}
fn read(path: &Path) -> Result<Json> {
    if std::fs::metadata(path)?.len() > 8 * 1024 * 1024 {
        return Err("input byte limit".into());
    }
    Ok(serde_json::from_slice(&std::fs::read(path)?)?)
}
fn value(j: &Json, precision: u32) -> Result<Value> {
    let a = j.as_array().ok_or("value array required")?;
    if a.len() != 3 {
        return Err("value width".into());
    }
    let v = Value {
        m: a[0].as_u64().ok_or("magnitude")?,
        e: i32::try_from(a[1].as_i64().ok_or("exponent")?)?,
        sign: u32::try_from(a[2].as_u64().ok_or("sign")?)?,
    };
    let p = i32::try_from(precision)?;
    if !matches!(precision, 48 | 64)
        || v.sign > 1
        || (v.m == 0 && v.e != 0)
        || (v.m != 0
            && (!((-1022 - (p - 1))..=(1023 - (p - 1))).contains(&v.e)
                || (precision == 48 && v.m >= 1_u64 << 48)
                || (v.e != -1022 - (p - 1) && v.m < 1_u64 << (precision - 1))))
    {
        return Err("noncanonical operand".into());
    }
    Ok(v)
}
fn row(v: Value, guard: u32) -> Json {
    json!([v.m, v.e, v.sign, guard])
}
fn ptr<T: Copy>(b: &DeviceBuffer<T>) -> A {
    A::DevicePtr(b.as_device_ptr())
}

struct Buffers {
    input: DeviceBuffer<Value>,
    output: DeviceBuffer<Value>,
    guards: DeviceBuffer<u32>,
    cycles: DeviceBuffer<u64>,
    len: usize,
    bytes: usize,
}
impl Buffers {
    fn new(context: &Rc<Context>, count: usize) -> Result<Self> {
        let len = count.checked_add(1).ok_or("shape overflow")?;
        let bytes = len
            .checked_mul(3 * 16 + 16 + 4 + 8)
            .ok_or("allocation overflow")?;
        if count > 65536 || bytes > CAP {
            return Err("device allocation limit".into());
        }
        Ok(Self {
            input: context.allocate(3 * len)?,
            output: context.allocate(len)?,
            guards: context.allocate(len)?,
            cycles: context.allocate(len)?,
            len,
            bytes,
        })
    }
    fn run(
        &mut self,
        module: &Module,
        stream: &Stream,
        input: &[Value],
        shape: (u32, u32, u32, Option<u32>),
    ) -> Result<Json> {
        let (precision, count, block, iterations) = shape;
        if input.len() != count as usize * 3
            || count as usize >= self.len
            || !matches!(block, 1 | 64 | 128 | 256)
        {
            return Err("launch shape".into());
        }
        let preparation = Instant::now();
        let mut padded = vec![SENTINEL; self.len * 3];
        padded[..input.len()].copy_from_slice(input);
        let mut output = vec![SENTINEL; self.len];
        let mut guards = vec![GUARD; self.len];
        let mut cycles = vec![0_u64; self.len];
        let host_prepare_ns = ns(preparation);
        let transfer = Instant::now();
        self.input.copy_from(&padded, stream)?;
        self.output.copy_from(&output, stream)?;
        self.guards.copy_from(&guards, stream)?;
        self.cycles.copy_from(&cycles, stream)?;
        let upload_ns = ns(transfer);
        let name = match iterations {
            Some(_) => format!("state_bench_p{precision}"),
            None => format!("state_compact_fma_p{precision}"),
        };
        let function = module.function(&name)?;
        let mut arguments = vec![ptr(&self.input), ptr(&self.output), ptr(&self.guards)];
        if iterations.is_some() {
            arguments.push(ptr(&self.cycles));
        }
        arguments.push(A::U32(count));
        if let Some(n) = iterations {
            arguments.push(A::U32(n));
        }
        let started = Instant::now();
        launch(
            &function,
            LaunchConfig {
                grid: count.div_ceil(block).max(1),
                block,
                shared_memory: 0,
            },
            &arguments,
            stream,
        )?;
        stream.synchronize()?;
        let launch_sync_ns = ns(started);
        let download = Instant::now();
        self.output.copy_to(&mut output, stream)?;
        self.guards.copy_to(&mut guards, stream)?;
        self.cycles.copy_to(&mut cycles, stream)?;
        let download_ns = ns(download);
        // All unwritten elements, including the canary, remain byte-for-byte.
        for index in count as usize..self.len {
            if output[index] != SENTINEL || guards[index] != GUARD || cycles[index] != 0 {
                return Err("output canary changed".into());
            }
        }
        let values: Vec<Json> = output[..=count as usize]
            .iter()
            .zip(&guards)
            .map(|(&v, &g)| row(v, g))
            .collect();
        Ok(
            json!({"precision":precision,"count":count,"block":block,"iterations":iterations,
            "values":values,"cycles":&cycles[..=count as usize],"host_prepare_ns":host_prepare_ns,
            "upload_ns":upload_ns,"launch_sync_ns":launch_sync_ns,"download_ns":download_ns,
            "allocated_bytes":self.bytes,"kernel":name}),
        )
    }
}

fn benchmark_input(p: u32, count: u32, pattern: &str) -> Result<Vec<Value>> {
    let one = 1_u64 << (p - 1);
    let e = -(i32::try_from(p)? - 1);
    let mut input = Vec::with_capacity(count as usize * 3);
    for index in 0..count {
        input.push(Value {
            m: one + u64::from(index % 17),
            e,
            sign: 0,
        });
        input.push(Value {
            m: one,
            e,
            sign: u32::from(pattern != "increment"),
        });
        input.push(match pattern {
            "increment" => Value {
                m: one,
                e: 2 * e,
                sign: 0,
            },
            "far_tail" => Value {
                m: 1,
                e: -1022 + e,
                sign: 0,
            },
            "cancellation" => Value { m: one, e, sign: 0 },
            _ => return Err("benchmark pattern".into()),
        });
    }
    Ok(input)
}

fn execute(request: &Json) -> Result<Json> {
    if !optimizer_cuda::inherited()
        || std::env::var("CUDA_VISIBLE_DEVICES")? != DEVICE
        || request["device"] != DEVICE
    {
        return Err("selected inherited lease required".into());
    }
    let mode = request["mode"].as_str().ok_or("mode")?;
    if !matches!(mode, "check" | "timing") {
        return Err("mode".into());
    }
    let context_time = Instant::now();
    let context = Rc::new(Context::create(DEVICE)?);
    let context_ns = ns(context_time);
    let module_time = Instant::now();
    let module = context.load_module_file(Path::new(request["image"].as_str().ok_or("image")?))?;
    let stream = context.stream()?;
    let module_stream_ns = ns(module_time);
    let device = json!({"uuid":context.device().uuid,"name":context.device().name,
        "capability":[context.device().capability_major,context.device().capability_minor],
        "multiprocessors":context.device().multiprocessors});
    let mut launches = Vec::new();
    let mut allocation_ns = 0_u64;
    if mode == "check" {
        let corpus = read(Path::new(request["corpus"].as_str().ok_or("corpus")?))?;
        let cases = corpus["cases"].as_array().ok_or("cases")?;
        if cases.len() != 6170 {
            return Err("corpus size".into());
        }
        for precision in [48, 64] {
            let mut input = Vec::new();
            let mut expected = Vec::new();
            for case in cases.iter().filter(|c| c["precision"] == precision) {
                let triple = case["input"].as_array().ok_or("triple")?;
                if triple.len() != 3 {
                    return Err("triple size".into());
                }
                for v in triple {
                    input.push(value(v, precision)?);
                }
                expected.push(case["expected"].clone());
            }
            if expected.len() != 3085 {
                return Err("format corpus size".into());
            }
            let start = Instant::now();
            let mut buffers = Buffers::new(&context, expected.len())?;
            allocation_ns += ns(start);
            for block in [64, 128, 256] {
                for repeat in 0..2 {
                    let mut result =
                        buffers.run(&module, &stream, &input, (precision, 3085, block, None))?;
                    if result["values"].as_array().ok_or("values")?[..3085] != expected {
                        return Err("device/oracle disagreement".into());
                    }
                    result["repeat"] = json!(repeat);
                    launches.push(result);
                }
            }
            for count in [0, 1, 31, 32, 33, 127, 128, 129] {
                let result = buffers.run(
                    &module,
                    &stream,
                    &input[..count * 3],
                    (precision, count as u32, 128, None),
                )?;
                if result["values"].as_array().ok_or("values")?[..count] != expected[..count] {
                    return Err("partial launch disagreement".into());
                }
                launches.push(result);
            }
            for pattern in ["increment", "far_tail", "cancellation"] {
                for (count, block, iterations) in [(1, 1, 7), (129, 128, 8)] {
                    let input = benchmark_input(precision, count, pattern)?;
                    let mut result = buffers.run(
                        &module,
                        &stream,
                        &input,
                        (precision, count, block, Some(iterations)),
                    )?;
                    result["pattern"] = json!(pattern);
                    launches.push(result);
                }
            }
        }
    } else {
        let p = u32_field(request, "precision")?;
        let count = u32_field(request, "count")?;
        let iterations = u32_field(request, "iterations")?;
        let block = u32_field(request, "block")?;
        if !matches!(p, 48 | 64)
            || !matches!(
                (count, iterations, block),
                (1, 16385, 1) | (65536, 129, 128)
            )
        {
            return Err("timing shape".into());
        }
        let pattern = request["pattern"].as_str().ok_or("pattern")?;
        let input = benchmark_input(p, count, pattern)?;
        let start = Instant::now();
        let mut buffers = Buffers::new(&context, count as usize)?;
        allocation_ns = ns(start);
        for phase in ["warmup", "measured"] {
            let mut result = buffers.run(
                &module,
                &stream,
                &input,
                (p, count, block, Some(iterations)),
            )?;
            result["phase"] = json!(phase);
            result["pattern"] = json!(pattern);
            launches.push(result);
        }
    }
    let teardown = Instant::now();
    drop(stream);
    drop(module);
    drop(context);
    Ok(
        json!({"schema_version":1,"request":request,"device":device,"context_ns":context_ns,
        "module_stream_ns":module_stream_ns,"allocation_ns":allocation_ns,
        "teardown_ns":ns(teardown),"launches":launches}),
    )
}
fn run() -> Result<()> {
    let args: Vec<_> = std::env::args_os().collect();
    if args.len() != 3 {
        return Err("usage: lp_state_probe request.json endpoint.json".into());
    }
    let started = Instant::now();
    let request = read(Path::new(&args[1]))?;
    let mut endpoint = execute(&request)?;
    endpoint["process_work_ns"] = json!(ns(started));
    std::fs::write(&args[2], serde_json::to_vec(&endpoint)?)?;
    println!("state primitive endpoint complete");
    Ok(())
}
fn main() {
    if let Err(error) = run() {
        eprintln!("state primitive diagnostic: {error}");
        std::process::exit(2);
    }
}
