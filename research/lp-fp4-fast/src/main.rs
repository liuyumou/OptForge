//! Bounded SPEC-0028 research executor. No certificate or solver authority.
use optimizer_cuda_sys::events::Event;
use optimizer_cuda_sys::{
    Argument as A, Context, DeviceBuffer, Function, LaunchConfig, Stream, launch,
};
use serde::{Deserialize, Serialize};
use serde_json::json;
use std::{fs, io::Write, path::Path, rc::Rc, time::Instant};

type Result<T> = std::result::Result<T, Box<dyn std::error::Error>>;
const DEVICE: &str = "GPU-6721b13a-30f9-83ec-dace-ba2d9738556f";
#[derive(Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
struct Request {
    backend: String,
    repetitions: u32,
    format: u32,
    components: u32,
    blocks: u32,
    n: u32,
    matrix: Vec<f64>,
    matrix_codes: Vec<u32>,
    matrix_exponents: Vec<i32>,
    cb: Vec<f64>,
    initial: Vec<f64>,
    variant: String,
    updates: u32,
    mode: String,
    cancel_after: Option<u32>,
    inject_fault: bool,
}
impl Request {
    fn validate(&self) -> Result<()> {
        let b = self.blocks as usize;
        let k = self.components as usize;
        let f = self.format as usize;
        if ![(64, 1), (4, 2), (4, 4), (4, 8), (8, 4), (16, 2)].contains(&(f, k))
            || !(1..=4096).contains(&b)
            || !(1..=21).contains(&self.repetitions)
            || ![
                "legacy",
                "encode",
                "prune",
                "prepack",
                "columns",
                "shared",
                "registers",
                "quick",
                "timers",
                "hardware",
                "native_cached",
            ]
            .contains(&self.backend.as_str())
            || (f == 64 && !["legacy", "native_cached"].contains(&self.backend.as_str()))
            || (self.backend == "native_cached" && f != 64)
            || (self.backend == "timers" && f != 4)
            || !(1..=32).contains(&self.n)
            || self.updates > 32
            || !["split", "fused", "persistent", "roundtrip"].contains(&self.variant.as_str())
            || !["trajectory", "transpose", "forward"].contains(&self.mode.as_str())
            || self.matrix.len() != b * 1024
            || self.cb.len() != b * 64
            || self.initial.len() != b * 96
            || self.matrix_codes.len() != if f == 64 { 1 } else { b * k * 32 * f }
            || self.matrix_exponents.len() != if f == 64 { 1 } else { b * k }
            || self
                .matrix_exponents
                .iter()
                .any(|e| !(-48..=48).contains(e))
            || self
                .matrix
                .iter()
                .chain(&self.cb)
                .chain(&self.initial)
                .any(|x| !x.is_finite())
        {
            return Err("invalid bounded pilot request".into());
        }
        for block in 0..b {
            for i in 0..32 {
                for j in 0..32 {
                    if (i >= self.n as usize || j >= self.n as usize)
                        && self.matrix[block * 1024 + i * 32 + j] != 0.
                    {
                        return Err("nonzero matrix padding".into());
                    }
                }
            }
            for v in 0..3 {
                if self.initial[block * 96 + v * 32 + self.n as usize..block * 96 + (v + 1) * 32]
                    .iter()
                    .any(|x| *x != 0.)
                {
                    return Err("nonzero state padding".into());
                }
            }
        }
        Ok(())
    }
}
#[derive(Default)]
struct Counts {
    launches: u64,
    copies: u64,
    bytes: u64,
}
fn upload<T: Copy>(
    ctx: &Rc<Context>,
    stream: &Stream,
    data: &[T],
    stats: &mut Counts,
) -> Result<DeviceBuffer<T>> {
    let mut buffer = ctx.allocate(data.len())?;
    buffer.copy_from(data, stream)?;
    stats.copies += 1;
    stats.bytes += std::mem::size_of_val(data) as u64;
    Ok(buffer)
}
fn download<T: Copy + Default>(
    buffer: &DeviceBuffer<T>,
    stream: &Stream,
    stats: &mut Counts,
) -> Result<Vec<T>> {
    let mut v = vec![T::default(); buffer.len()];
    buffer.copy_to(&mut v, stream)?;
    stats.copies += 1;
    stats.bytes += std::mem::size_of_val(v.as_slice()) as u64;
    Ok(v)
}
fn copy<T: Copy>(
    buffer: &mut DeviceBuffer<T>,
    v: &[T],
    stream: &Stream,
    stats: &mut Counts,
) -> Result<()> {
    buffer.copy_from(v, stream)?;
    stats.copies += 1;
    stats.bytes += std::mem::size_of_val(v) as u64;
    Ok(())
}
fn submit(
    function: &Function<'_>,
    stream: &Stream,
    base: &[A],
    blocks: u32,
    op: u32,
    count: u32,
    stats: &mut Counts,
) -> Result<()> {
    let mut args = base.to_vec();
    args.extend([A::U32(op), A::U32(count)]);
    launch(
        function,
        LaunchConfig {
            grid: blocks,
            block: 32,
            shared_memory: 0,
        },
        &args,
        stream,
    )?;
    stats.launches += 1;
    Ok(())
}
fn audit(r: &Request, state: &[f64]) -> f64 {
    let mut error = 0_f64;
    for b in 0..r.blocks as usize {
        for i in 0..r.n as usize {
            let sum = (0..r.n as usize)
                .map(|j| r.matrix[b * 1024 + i * 32 + j] * state[b * 96 + j])
                .sum::<f64>();
            error = error.max((sum - r.cb[b * 64 + 32 + i]).abs());
        }
    }
    error
}
fn execute(r: Request, image: &Path) -> Result<serde_json::Value> {
    r.validate()?;
    if std::env::var("AI_OPTIMIZER_GPU_LEASE").as_deref() != Ok("inherited")
        || std::env::var("CUDA_VISIBLE_DEVICES").as_deref() != Ok(DEVICE)
    {
        return Err("pinned shared lease required".into());
    }
    let entered = Instant::now();
    if r.cancel_after == Some(0) {
        return Ok(
            json!({"status":"cancelled","physical_updates":0,"launches":0,"state":r.initial}),
        );
    }
    let ctx = Rc::new(Context::create(DEVICE)?);
    if (ctx.device().capability_major, ctx.device().capability_minor) != (12, 0) {
        return Err("SM120 required".into());
    }
    let module = ctx.load_module_file(image)?;
    let stream = ctx.stream()?;
    let fast_mode = match r.backend.as_str() {
        "legacy" | "native_cached" => None,
        "encode" => Some(0),
        "prune" => Some(1),
        "prepack" => Some(2),
        "columns" => Some(3),
        "shared" => Some(4),
        "registers" => Some(5),
        "quick" => Some(6),
        "timers" => Some(7),
        "hardware" => Some(8),
        _ => unreachable!(),
    };
    let function = module.function(&match fast_mode {
        None => {
            if r.backend == "native_cached" {
                "native_cached_64_1".into()
            } else {
                format!("pilot_{}_{}", r.format, r.components)
            }
        }
        Some(m) => format!("fast_{}_{}_{}", r.format, r.components, m),
    })?;
    let context_ns = entered.elapsed().as_nanos();
    let start = Instant::now();
    let mut stats = Counts::default();
    let blocks = r.blocks as usize;
    let low = r.format != 64;
    let words = if low {
        blocks * 3 * r.components as usize * r.format as usize
    } else {
        1
    };
    let exponents = if low {
        blocks * 3 * r.components as usize
    } else {
        1
    };
    let fragment_words = if fast_mode.is_some() {
        blocks * r.components as usize * 512 * if r.format == 16 { 2 } else { 1 }
    } else {
        1
    };
    let checkpoint_bytes = if r.repetitions > 1 {
        (words + exponents + blocks * 2) * 4 + r.initial.len() * 8
    } else {
        0
    };
    let allocated = checkpoint_bytes
        + fragment_words * 4
        + blocks * 4
        + (r.matrix_codes.len() + words + exponents + r.matrix_exponents.len() + blocks * 2) * 4
        + (r.matrix.len() + r.cb.len() + r.initial.len() + blocks * 32) * 8;
    if allocated > 12usize << 30 {
        return Err("device buffer cap".into());
    }
    let a = upload(&ctx, &stream, &r.matrix_codes, &mut stats)?;
    let ae = upload(&ctx, &stream, &r.matrix_exponents, &mut stats)?;
    let original = upload(&ctx, &stream, &r.matrix, &mut stats)?;
    let cb = upload(&ctx, &stream, &r.cb, &mut stats)?;
    let mut state = upload(&ctx, &stream, &vec![0u32; words], &mut stats)?;
    let mut scales = upload(&ctx, &stream, &vec![0i32; exponents], &mut stats)?;
    let mut raw = upload(&ctx, &stream, &r.initial, &mut stats)?;
    let tmp = upload(&ctx, &stream, &vec![0u32; blocks * 64], &mut stats)?;
    let mut flags = upload(&ctx, &stream, &vec![0u32; blocks * 2], &mut stats)?;
    let fragments = upload(&ctx, &stream, &vec![0u32; fragment_words], &mut stats)?;
    let masks = upload(&ctx, &stream, &vec![0u32; blocks], &mut stats)?;
    if fast_mode.is_some() {
        let prepare = module.function(&format!("prepare_{}_{}", r.format, r.components))?;
        launch(
            &prepare,
            LaunchConfig {
                grid: r.blocks,
                block: 32,
                shared_memory: 0,
            },
            &[
                A::DevicePtr(a.as_device_ptr()),
                A::DevicePtr(fragments.as_device_ptr()),
                A::DevicePtr(masks.as_device_ptr()),
            ],
            &stream,
        )?;
        stats.launches += 1;
    }
    let mut base = vec![
        A::DevicePtr(a.as_device_ptr()),
        A::DevicePtr(ae.as_device_ptr()),
        A::DevicePtr(original.as_device_ptr()),
        A::DevicePtr(cb.as_device_ptr()),
        A::DevicePtr(state.as_device_ptr()),
        A::DevicePtr(scales.as_device_ptr()),
        A::DevicePtr(raw.as_device_ptr()),
        A::DevicePtr(tmp.as_device_ptr()),
        A::DevicePtr(flags.as_device_ptr()),
        A::U32(r.n),
    ];
    if fast_mode.is_some() {
        base.splice(
            0..0,
            [
                A::DevicePtr(fragments.as_device_ptr()),
                A::DevicePtr(masks.as_device_ptr()),
            ],
        );
    }
    submit(&function, &stream, &base, r.blocks, 0, 0, &mut stats)?;
    stream.synchronize()?;
    submit(&function, &stream, &base, r.blocks, 6, 0, &mut stats)?;
    let checkpoint_raw = download(&raw, &stream, &mut stats)?;
    let checkpoint_state = download(&state, &stream, &mut stats)?;
    let checkpoint_scales = download(&scales, &stream, &mut stats)?;
    let checkpoint_flags = download(&flags, &stream, &mut stats)?;
    if checkpoint_flags.chunks(2).any(|f| f[0] != 0) {
        return Err("initial encoding refused".into());
    }
    let device_checkpoint = if r.repetitions > 1 {
        Some((
            upload(&ctx, &stream, &checkpoint_state, &mut stats)?,
            upload(&ctx, &stream, &checkpoint_scales, &mut stats)?,
            upload(&ctx, &stream, &checkpoint_raw, &mut stats)?,
            upload(&ctx, &stream, &checkpoint_flags, &mut stats)?,
        ))
    } else {
        None
    };
    let reset = if r.repetitions > 1 {
        Some(module.function("reset_checkpoint")?)
    } else {
        None
    };
    let begin = Event::new(&ctx)?;
    let end = Event::new(&ctx)?;
    let upload_ns = start.elapsed().as_nanos();
    let mut samples = Vec::new();
    let mut first_endpoint: Option<(Vec<u32>, Vec<i32>, Vec<f64>)> = None;
    let mut final_result = serde_json::Value::Null;
    for repetition in 0..r.repetitions {
        let prepared = Instant::now();
        if repetition > 0 {
            let (cs, ce, cr, cf) = device_checkpoint
                .as_ref()
                .ok_or("missing prepared checkpoint")?;
            let width = words.max(exponents).max(r.initial.len()).max(blocks * 2) as u32;
            launch(
                reset.as_ref().ok_or("missing reset kernel")?,
                LaunchConfig {
                    grid: width.div_ceil(256),
                    block: 256,
                    shared_memory: 0,
                },
                &[
                    A::DevicePtr(cs.as_device_ptr()),
                    A::DevicePtr(ce.as_device_ptr()),
                    A::DevicePtr(cr.as_device_ptr()),
                    A::DevicePtr(cf.as_device_ptr()),
                    A::DevicePtr(state.as_device_ptr()),
                    A::DevicePtr(scales.as_device_ptr()),
                    A::DevicePtr(raw.as_device_ptr()),
                    A::DevicePtr(flags.as_device_ptr()),
                    A::U32(words as u32),
                    A::U32(exponents as u32),
                    A::U32(r.initial.len() as u32),
                    A::U32((blocks * 2) as u32),
                ],
                &stream,
            )?;
            stats.launches += 1;
            stream.synchronize()?;
        }
        let reset_ns = prepared.elapsed().as_nanos();
        let iteration = Instant::now();
        begin.record(&stream)?;
        let mut physical = 0;
        let mut status = "completed";
        let launches_before = stats.launches;
        let copies_before = stats.copies;
        let bytes_before = stats.bytes;
        if r.mode != "trajectory" {
            submit(
                &function,
                &stream,
                &base,
                r.blocks,
                if r.mode == "transpose" { 1 } else { 3 },
                0,
                &mut stats,
            )?;
        } else {
            while physical < r.updates {
                if entered.elapsed().as_secs() >= 120 {
                    return Err("bounded execution deadline".into());
                }
                if r.cancel_after.is_some_and(|c| physical >= c) {
                    status = "cancelled";
                    break;
                }
                let count = if r.variant == "persistent" {
                    (r.updates - physical).min(if r.cancel_after.is_some() { 8 } else { 32 })
                } else {
                    1
                };
                if r.variant == "split" {
                    for op in 1..=4 {
                        submit(&function, &stream, &base, r.blocks, op, 1, &mut stats)?;
                    }
                } else {
                    submit(&function, &stream, &base, r.blocks, 5, count, &mut stats)?;
                }
                physical += count;
                if r.variant == "roundtrip" {
                    submit(&function, &stream, &base, r.blocks, 6, 0, &mut stats)?;
                    let host = download(&raw, &stream, &mut stats)?;
                    copy(&mut raw, &host, &stream, &mut stats)?;
                    submit(&function, &stream, &base, r.blocks, 0, 0, &mut stats)?;
                }
                if r.inject_fault {
                    submit(&function, &stream, &base, r.blocks, 7, 0, &mut stats)?;
                    break;
                }
            }
        }
        end.record(&stream)?;
        stream.synchronize()?;
        let stream_span_ms = begin.elapsed_to(&end)?;
        let iteration_ns = iteration.elapsed().as_nanos();
        let iteration_launches = stats.launches - launches_before;
        let iteration_copies = stats.copies - copies_before;
        let iteration_bytes = stats.bytes - bytes_before;
        let export = Instant::now();
        let observed_flags = download(&flags, &stream, &mut stats)?;
        if observed_flags.chunks(2).any(|f| f[0] != 0) {
            status = "refused";
        }
        if status != "completed" {
            copy(&mut state, &checkpoint_state, &stream, &mut stats)?;
            copy(&mut scales, &checkpoint_scales, &stream, &mut stats)?;
            copy(&mut flags, &checkpoint_flags, &stream, &mut stats)?;
            copy(&mut raw, &checkpoint_raw, &stream, &mut stats)?;
        }
        submit(&function, &stream, &base, r.blocks, 6, 0, &mut stats)?;
        let values = download(&raw, &stream, &mut stats)?;
        let codes = download(&state, &stream, &mut stats)?;
        let exponents = download(&scales, &stream, &mut stats)?;
        let scratch = download(&tmp, &stream, &mut stats)?;
        if values.iter().any(|x| !x.is_finite()) {
            return Err("nonfinite exported candidate".into());
        }
        let rollback_exact = status == "completed"
            || (codes == checkpoint_state
                && exponents == checkpoint_scales
                && values == checkpoint_raw);
        if !rollback_exact {
            return Err("rollback differs".into());
        }
        let export_ns = export.elapsed().as_nanos();
        let start = Instant::now();
        let residual = audit(&r, &values);
        let audit_ns = start.elapsed().as_nanos();
        let phase_cycles: Vec<Vec<u64>> = if r.backend == "timers" {
            scratch
                .chunks(64)
                .map(|block| {
                    block[..8]
                        .chunks(2)
                        .map(|p| u64::from(p[0]) | (u64::from(p[1]) << 32))
                        .collect()
                })
                .collect()
        } else {
            Vec::new()
        };
        let product: Vec<f64> = scratch
            .chunks(2)
            .map(|p| {
                if low {
                    f32::from_bits(p[0]) as f64 + f32::from_bits(p[1]) as f64
                } else {
                    f64::from_bits(u64::from(p[0]) | (u64::from(p[1]) << 32))
                }
            })
            .collect();
        if let Some((old_codes, old_exponents, old_values)) = &first_endpoint {
            if *old_codes != codes || *old_exponents != exponents || *old_values != values {
                return Err("fresh-state repetition changed endpoint".into());
            }
        } else {
            first_endpoint = Some((codes.clone(), exponents.clone(), values.clone()));
        }
        samples.push(json!({"repetition":repetition,"cuda_ms":stream_span_ms,
        "iteration_ns":iteration_ns,"reset_ns":reset_ns,"export_ns":export_ns,
        "audit_ns":audit_ns,"prepared_ns":prepared.elapsed().as_nanos()}));
        final_result = json!({"phase_cycles":phase_cycles,"status":status,"physical_updates":physical,"logical_updates":if status=="completed"{physical}else{0},"rollback_exact":rollback_exact,"generation":if status=="completed"{0}else{1},"state":values,"codes":codes,"exponents":exponents,"observed_flags":observed_flags,"product":product,"original_a_primal_residual":residual,"certified":false,"counts":{"launches":stats.launches,"copies":stats.copies,"copy_bytes":stats.bytes,"iteration_launches":iteration_launches,"iteration_copies":iteration_copies,"iteration_copy_bytes":iteration_bytes,"device_bytes":allocated,"checkpoint_bytes":checkpoint_bytes,"prepared_reset_launches":r.repetitions-1,"prepared_reset_host_copy_bytes":0},"phases_ns":{"context":context_ns,"upload_checkpoint":upload_ns,"iteration":iteration_ns,"export":export_ns,"audit":audit_ns},"cuda_stream_span_ms":stream_span_ms,"executor_ns":entered.elapsed().as_nanos()});
    }
    final_result["samples"] = json!(samples);
    final_result["backend"] = json!(r.backend);
    final_result["repetitions"] = json!(r.repetitions);
    Ok(final_result)
}
fn read_word<const N: usize>(data: &[u8], offset: &mut usize) -> Result<[u8; N]> {
    let word = data
        .get(*offset..*offset + N)
        .ok_or("truncated binary array")?;
    *offset += N;
    Ok(word.try_into()?)
}
fn parse_request(data: &[u8]) -> Result<Request> {
    if !data.starts_with(b"FP4FAST1") {
        return Ok(serde_json::from_slice(data)?);
    }
    let mut offset = 8;
    let length = u32::from_le_bytes(read_word(data, &mut offset)?) as usize;
    if length > 16384 {
        return Err("binary header cap".into());
    }
    let mut r: Request = serde_json::from_slice(
        data.get(offset..offset + length)
            .ok_or("truncated header")?,
    )?;
    offset += length;
    let b = r.blocks as usize;
    let f = r.format as usize;
    let k = r.components as usize;
    if !(1..=4096).contains(&b)
        || ![(64, 1), (4, 2), (4, 4), (4, 8), (8, 4), (16, 2)].contains(&(f, k))
        || !r.matrix.is_empty()
        || !r.matrix_codes.is_empty()
        || !r.matrix_exponents.is_empty()
        || !r.cb.is_empty()
        || !r.initial.is_empty()
    {
        return Err("invalid binary metadata".into());
    }
    r.matrix = (0..b * 1024)
        .map(|_| Ok(f64::from_le_bytes(read_word(data, &mut offset)?)))
        .collect::<Result<_>>()?;
    r.matrix_codes = (0..if f == 64 { 1 } else { b * k * 32 * f })
        .map(|_| Ok(u32::from_le_bytes(read_word(data, &mut offset)?)))
        .collect::<Result<_>>()?;
    r.matrix_exponents = (0..if f == 64 { 1 } else { b * k })
        .map(|_| Ok(i32::from_le_bytes(read_word(data, &mut offset)?)))
        .collect::<Result<_>>()?;
    r.cb = (0..b * 64)
        .map(|_| Ok(f64::from_le_bytes(read_word(data, &mut offset)?)))
        .collect::<Result<_>>()?;
    r.initial = (0..b * 96)
        .map(|_| Ok(f64::from_le_bytes(read_word(data, &mut offset)?)))
        .collect::<Result<_>>()?;
    if offset != data.len() {
        return Err("trailing binary data".into());
    }
    Ok(r)
}
fn main() -> Result<()> {
    let args: Vec<_> = std::env::args_os().collect();
    if args.len() != 4 {
        return Err("usage: lp-fp4-fast INPUT IMAGE OUTPUT".into());
    }
    let path = Path::new(&args[1]);
    if fs::metadata(path)?.len() > 128 << 20 {
        return Err("input exceeds 128 MiB".into());
    }
    let r = parse_request(&fs::read(path)?)?;
    let out = execute(r, Path::new(&args[2]))?;
    let mut f = fs::OpenOptions::new()
        .create_new(true)
        .write(true)
        .open(&args[3])?;
    serde_json::to_writer(&mut f, &out)?;
    f.write_all(b"\n")?;
    f.sync_all()?;
    Ok(())
}
#[cfg(test)]
mod tests {
    use super::*;
    fn request() -> Request {
        Request {
            backend: "legacy".into(),
            repetitions: 1,
            format: 64,
            components: 1,
            blocks: 1,
            n: 29,
            matrix: vec![0.; 1024],
            matrix_codes: vec![0],
            matrix_exponents: vec![0],
            cb: vec![0.; 64],
            initial: vec![0.; 96],
            variant: "persistent".into(),
            updates: 32,
            mode: "trajectory".into(),
            cancel_after: None,
            inject_fault: false,
        }
    }
    #[test]
    fn bounded_shapes() {
        let mut r = request();
        assert!(r.validate().is_ok());
        r.blocks = 4097;
        assert!(r.validate().is_err());
        r = request();
        r.updates = 33;
        assert!(r.validate().is_err());
        r = request();
        r.matrix.pop();
        assert!(r.validate().is_err());
    }
    #[test]
    fn padding_and_finiteness() {
        let mut r = request();
        r.matrix[31] = 1.;
        assert!(r.validate().is_err());
        r = request();
        r.cb[0] = f64::NAN;
        assert!(r.validate().is_err());
        r = request();
        r.initial[31] = 1.;
        assert!(r.validate().is_err());
    }
    #[test]
    fn unsupported_lane() {
        let mut r = request();
        r.format = 4;
        r.components = 3;
        assert!(r.validate().is_err());
    }
    #[test]
    fn binary_transport_bounds_and_coefficients() {
        let mut r = request();
        r.matrix.clear();
        r.matrix_codes.clear();
        r.matrix_exponents.clear();
        r.cb.clear();
        r.initial.clear();
        let header = serde_json::to_vec(&r).unwrap();
        let mut data = b"FP4FAST1".to_vec();
        data.extend((header.len() as u32).to_le_bytes());
        data.extend(header);
        let header_end = data.len();
        data.extend(vec![0; 1024 * 8 + 8 + 64 * 8 + 96 * 8]);
        data[header_end..header_end + 8].copy_from_slice(&0.123456789012345_f64.to_le_bytes());
        let parsed = parse_request(&data).unwrap();
        assert_eq!(parsed.matrix[0], 0.123456789012345);
        assert!(parsed.validate().is_ok());
        data.pop();
        assert!(parse_request(&data).is_err());
        data.push(0);
        data.push(0);
        assert!(parse_request(&data).is_err());
        assert!(parse_request(b"FP4FAST1").is_err());
    }
}
