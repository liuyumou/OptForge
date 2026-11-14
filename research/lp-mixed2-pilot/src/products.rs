//! Fixed-operand products and guard costs; no solver/certificate authority.
use crate::{
    Result,
    device::{download, upload},
};
use optimizer_cuda_sys::{Argument as A, Context, LaunchConfig, events::Event, launch};
use serde::Deserialize;
use serde_json::json;
use std::{fs, io::Write, rc::Rc, time::Instant};

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Input {
    rows: usize,
    cols: usize,
    a: Vec<f64>,
    x: Vec<f64>,
    transpose: bool,
    mode: String,
    count: u32,
}
struct Host {
    p: usize,
    a64: Vec<f64>,
    a32: Vec<f32>,
    error: Vec<f64>,
    x: Vec<f64>,
}
fn prepare(input: &Input) -> Result<Host> {
    if input.rows == 0
        || input.cols == 0
        || input.rows.max(input.cols) > 512
        || input.a.len() != input.rows * input.cols
        || input.x.len()
            != if input.transpose {
                input.rows
            } else {
                input.cols
            }
        || input.a.iter().chain(&input.x).any(|v| !v.is_finite())
        || !["fp64", "fp32", "guard"].contains(&input.mode.as_str())
        || input.count == 0
        || input.count > 256
    {
        return Err("invalid product probe".into());
    }
    let p = input.rows.max(input.cols).div_ceil(32) * 32;
    let mut a64 = vec![0.; 2 * p * p];
    let mut a32 = vec![0.; 2 * p * p];
    let mut error = vec![0.; 2 * p * p];
    let mut x = vec![0.; p];
    x[..input.x.len()].copy_from_slice(&input.x);
    for r in 0..input.rows {
        for c in 0..input.cols {
            let a = input.a[r * input.cols + c];
            let b = a as f32;
            if !b.is_finite() || (a != 0. && b == 0.) {
                return Err("FP32 coefficient range refusal".into());
            }
            let e = (a - f64::from(b)).abs();
            let e = if e == 0. { 0. } else { e.next_up() };
            for at in [c * p + r, p * p + r * p + c] {
                a64[at] = a;
                a32[at] = b;
                error[at] = e;
            }
        }
    }
    Ok(Host {
        p,
        a64,
        a32,
        error,
        x,
    })
}
fn expected(h: &Host, tr: bool, fp32: bool) -> Vec<f64> {
    (0..h.p)
        .map(|i| {
            let mut partial = [0.; 8];
            for (w, acc) in partial.iter_mut().enumerate() {
                for j in (w..h.p).step_by(8) {
                    let at = usize::from(tr) * h.p * h.p + j * h.p + i;
                    let a = if fp32 {
                        f64::from(h.a32[at])
                    } else {
                        h.a64[at]
                    };
                    *acc = a.mul_add(h.x[j], *acc);
                }
            }
            partial.into_iter().fold(0., |a, b| a + b)
        })
        .collect()
}
pub fn run(args: &[String]) -> Result<()> {
    if args.len() != 5 {
        return Err("product-pilot IMAGE INPUT OUTPUT".into());
    }
    let started = Instant::now();
    let bytes = fs::read(&args[3])?;
    let input: Input = serde_json::from_slice(&bytes)?;
    let read_ns = started.elapsed().as_nanos();
    let begin = Instant::now();
    let host = prepare(&input)?;
    let representation_ns = begin.elapsed().as_nanos();
    let begin = Instant::now();
    let expected = expected(&host, input.transpose, input.mode != "fp64");
    if expected.iter().any(|v| !v.is_finite()) {
        return Err("nonfinite product refusal".into());
    }
    let oracle_ns = begin.elapsed().as_nanos();
    if std::env::var("AI_OPTIMIZER_GPU_LEASE").as_deref() != Ok("inherited")
        || std::env::var("CUDA_VISIBLE_DEVICES").as_deref() != Ok(crate::DEVICE)
    {
        return Err("pinned shared lease required".into());
    }
    let begin = Instant::now();
    let ctx = Rc::new(Context::create(crate::DEVICE)?);
    let module = ctx.load_module_file(std::path::Path::new(&args[2]))?;
    let stream = ctx.stream()?;
    let context_ns = begin.elapsed().as_nanos();
    let begin = Instant::now();
    let a64 = upload(&ctx, &stream, &host.a64)?;
    let h2d_fp64_ns = begin.elapsed().as_nanos();
    let begin = Instant::now();
    let a32 = upload(&ctx, &stream, &host.a32)?;
    let h2d_fp32_ns = begin.elapsed().as_nanos();
    let begin = Instant::now();
    let error = upload(&ctx, &stream, &host.error)?;
    let h2d_error_ns = begin.elapsed().as_nanos();
    let x = upload(&ctx, &stream, &host.x)?;
    let out = upload(&ctx, &stream, &vec![0_f64; host.p])?;
    let stamps = upload(&ctx, &stream, &[0u64; 64])?;
    launch(
        &module.function("mixed2_timer_probe")?,
        LaunchConfig {
            grid: 1,
            block: 32,
            shared_memory: 0,
        },
        &[A::DevicePtr(stamps.as_device_ptr())],
        &stream,
    )?;
    let timer = download(&stamps, &stream)?;
    let function = module.function(match input.mode.as_str() {
        "fp64" => "mixed2_product64",
        "fp32" => "mixed2_product32",
        _ => "mixed2_product_guard",
    })?;
    let arguments = [
        A::DevicePtr(a64.as_device_ptr()),
        A::DevicePtr(a32.as_device_ptr()),
        A::DevicePtr(error.as_device_ptr()),
        A::DevicePtr(x.as_device_ptr()),
        A::DevicePtr(out.as_device_ptr()),
        A::U32(host.p as u32),
        A::U32(u32::from(input.transpose)),
    ];
    let start = Event::new(&ctx)?;
    let end = Event::new(&ctx)?;
    let begin = Instant::now();
    start.record(&stream)?;
    for _ in 0..input.count {
        launch(
            &function,
            LaunchConfig {
                grid: (host.p / 32) as u32,
                block: 256,
                shared_memory: 0,
            },
            &arguments,
            &stream,
        )?;
    }
    end.record(&stream)?;
    stream.synchronize()?;
    let launch_sync_ns = begin.elapsed().as_nanos();
    let gpu_ns = f64::from(start.elapsed_to(&end)?) * 1e6;
    let begin = Instant::now();
    let output = download(&out, &stream)?;
    let d2h_ns = begin.elapsed().as_nanos();
    if output.iter().any(|v| !v.is_finite()) {
        return Err("nonfinite device output".into());
    }
    if input.mode != "guard"
        && output
            .iter()
            .zip(&expected)
            .any(|(a, b)| a.to_bits() != b.to_bits())
    {
        return Err("CPU schedule oracle mismatch".into());
    }
    let value = json!({"mode":input.mode,"transpose":input.transpose,"count":input.count,"p":host.p,"rows":input.rows,"cols":input.cols,"values":output,"expected":expected,"gpu_ns":gpu_ns,"launch_sync_ns":launch_sync_ns,"read_ns":read_ns,"representation_ns":representation_ns,"oracle_ns":oracle_ns,"context_ns":context_ns,"h2d_fp64_ns":h2d_fp64_ns,"h2d_fp32_ns":h2d_fp32_ns,"h2d_error_ns":h2d_error_ns,"d2h_ns":d2h_ns,"matrix_bytes":{"fp64":host.a64.len()*8,"fp32":host.a32.len()*4,"error":host.error.len()*8},"timer":timer,"input_sha256":crate::identity::hex(&bytes)});
    let mut out = fs::OpenOptions::new()
        .write(true)
        .create_new(true)
        .open(&args[4])?;
    serde_json::to_writer(&mut out, &value)?;
    out.write_all(b"\n")?;
    out.sync_all()?;
    Ok(())
}
#[cfg(test)]
mod tests {
    use super::*;
    fn input() -> Input {
        Input {
            rows: 1,
            cols: 2,
            a: vec![-0., 0.1],
            x: vec![1., -2.],
            transpose: false,
            mode: "fp32".into(),
            count: 1,
        }
    }
    #[test]
    fn bounded_shapes_ranges_and_modes() {
        let mut i = input();
        i.rows = usize::MAX;
        assert!(prepare(&i).is_err());
        let mut i = input();
        i.a[0] = f64::MAX;
        assert!(prepare(&i).is_err());
        let mut i = input();
        i.a[0] = f64::from_bits(1);
        assert!(prepare(&i).is_err());
        let mut i = input();
        i.mode = "automatic".into();
        assert!(prepare(&i).is_err());
    }
    #[test]
    fn transpose_bits_and_subnormals() {
        let mut i = input();
        i.a[1] = f64::from(f32::from_bits(1));
        let h = prepare(&i).unwrap();
        assert_eq!(h.a32[0].to_bits(), (-0_f32).to_bits());
        assert_eq!(h.a32[32].to_bits(), h.a32[1025].to_bits());
        assert!(h.error.iter().all(|v| *v == 0.));
    }
    #[test]
    fn schedule_oracle_keeps_padding_and_widening() {
        let i = input();
        let h = prepare(&i).unwrap();
        let values = expected(&h, false, true);
        assert_eq!(values[0], -2. * f64::from(0.1_f32));
        assert!(values[1..].iter().all(|v| *v == 0.));
    }
}
