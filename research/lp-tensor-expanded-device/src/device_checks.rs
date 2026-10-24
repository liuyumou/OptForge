//! New device acceptance, using retained independent scalar expected results.
use crate::{Image, Request, device, tensor_cost, value::Value};
use optimizer_core::{CancellationToken, LpSettings, Model, sha256};
use optimizer_cuda_sys::{
    Argument as A, Context, DeviceBuffer, LaunchConfig, Module, Stream, launch,
};
use optimizer_lp::{Engine, LinearProgram, control::Fp64Controller};
use std::{error::Error, rc::Rc};
use tensor_cost::{Format, HostOracle, Layout, Oracle, Policy, Settings};
type Result<T> = std::result::Result<T, Box<dyn Error>>;
fn upload<T: Copy>(c: &Rc<Context>, s: &Stream, v: &[T]) -> Result<DeviceBuffer<T>> {
    let mut b = c.allocate(v.len())?;
    b.copy_from(v, s)?;
    Ok(b)
}
struct Soa {
    words: DeviceBuffer<u32>,
    n: usize,
}
impl Soa {
    fn new(c: &Rc<Context>, s: &Stream, values: &[Value]) -> Result<Self> {
        let n = values.len();
        let mut words = vec![0u32; 4 * n];
        for (i, v) in values.iter().enumerate() {
            words[i] = ((v.magnitude >> 40) as f32).to_bits();
            words[n + i] = (((v.magnitude >> 16) & 0xffffff) as f32).to_bits();
            words[2 * n + i] = ((v.magnitude & 65535) as f32).to_bits();
            words[3 * n + i] = (v.exponent as u32 & 65535) | (u32::from(v.negative) << 31);
        }
        Ok(Self {
            words: upload(c, s, &words)?,
            n,
        })
    }
    fn argument(&self) -> A {
        let p = self.words.as_device_ptr();
        A::Soa32([
            p,
            p + 4 * self.n as u64,
            p + 8 * self.n as u64,
            p + 12 * self.n as u64,
        ])
    }
    fn read(&self, s: &Stream) -> Result<Vec<Value>> {
        let mut w = vec![0u32; 4 * self.n];
        self.words.copy_to(&mut w, s)?;
        Ok((0..self.n)
            .map(|i| Value {
                magnitude: ((f32::from_bits(w[i]) as u64) << 40)
                    | ((f32::from_bits(w[self.n + i]) as u64) << 16)
                    | f32::from_bits(w[2 * self.n + i]) as u64,
                exponent: (w[3 * self.n + i] as u16 as i16) as i32,
                negative: w[3 * self.n + i] >> 31 != 0,
            })
            .collect())
    }
}
fn write(path: &str, value: &serde_json::Value) -> Result<()> {
    let f = std::fs::OpenOptions::new()
        .write(true)
        .create_new(true)
        .open(path)?;
    serde_json::to_writer_pretty(f, value)?;
    Ok(())
}
fn fail(
    path: &str,
    kind: &str,
    index: usize,
    expected: impl std::fmt::Debug,
    actual: impl std::fmt::Debug,
) -> Result<()> {
    write(
        path,
        &serde_json::json!({"status":"refused","kind":kind,"index":index,"expected":format!("{expected:?}"),"actual":format!("{actual:?}")}),
    )?;
    Err(format!("{kind} mismatch at {index}: expected {expected:?}; actual {actual:?}").into())
}
fn model() -> Model {
    let b = |v| serde_json::json!({"kind":"finite","value":v});
    let variables = (0..32)
        .map(|i| serde_json::json!({"id":i,"domain":"continuous","lower":b(-2.),"upper":b(2.)}))
        .collect::<Vec<_>>();
    let rows=(0..32).map(|r|serde_json::json!({"id":r,"lower":b(-1.),"upper":b(1.),"terms":(0..32).map(|c|serde_json::json!({"variable_id":c,"coefficient":if r==c{4.}else{((r+c)%3+1) as f64/32.}})).collect::<Vec<_>>()})).collect::<Vec<_>>();
    Model::from_json(&serde_json::to_vec(&serde_json::json!({"schema_version":1,"model_id":"tensor-dense","variables":variables,"constraints":rows,"objective":{"sense":"minimize","offset":0.,"terms":(0..32).map(|i|serde_json::json!({"variable_id":i,"coefficient":1.})).collect::<Vec<_>>()}})).unwrap()).unwrap()
}
fn primitive(c: &Rc<Context>, module: &Module, fixture: &str, out: &str) -> Result<()> {
    let s = c.stream()?;
    let f: serde_json::Value = serde_json::from_slice(&std::fs::read(fixture)?)?;
    let input_path = f["input"]["path"].as_str().ok_or("scalar input path")?;
    let expected_path = f["output"]["path"].as_str().ok_or("scalar expected path")?;
    let input = std::fs::read(input_path)?;
    let expected = std::fs::read(expected_path)?;
    if sha256::hex(&input) != f["input"]["sha256"].as_str().unwrap()
        || sha256::hex(&expected) != f["output"]["sha256"].as_str().unwrap()
    {
        return Err("retained scalar binding".into());
    }
    let mut operands: [Vec<Value>; 3] = std::array::from_fn(|_| Vec::new());
    for line in std::str::from_utf8(&input)?.lines() {
        let v = line.split_whitespace().collect::<Vec<_>>();
        if v.len() != 9 {
            return Err("scalar fixture width".into());
        }
        for k in 0..3 {
            operands[k].push(Value {
                magnitude: v[k * 3].parse()?,
                exponent: v[k * 3 + 1].parse()?,
                negative: v[k * 3 + 2].parse::<u32>()? != 0,
            });
        }
    }
    let expected = std::str::from_utf8(&expected)?
        .lines()
        .map(|line| {
            let v = line.split_whitespace().collect::<Vec<_>>();
            Ok((
                Value {
                    magnitude: v[0].parse()?,
                    exponent: v[1].parse()?,
                    negative: v[2].parse::<u32>()? != 0,
                },
                v[3].parse::<u32>()?,
            ))
        })
        .collect::<Result<Vec<_>>>()?;
    let n = operands[0].len();
    if n != 7376 || expected.len() != n {
        return Err("scalar corpus count".into());
    }
    let a = Soa::new(c, &s, &operands[0])?;
    let b = Soa::new(c, &s, &operands[1])?;
    let d = Soa::new(c, &s, &operands[2])?;
    let output = Soa::new(c, &s, &vec![Value::default(); n])?;
    let guards = upload(c, &s, &vec![0u32; n])?;
    let fast = upload(c, &s, &vec![0u32; n])?;
    for name in ["xe_scalar", "xe_integer_fma"] {
        let function = module.function(name)?;
        let mut args = vec![
            a.argument(),
            b.argument(),
            d.argument(),
            output.argument(),
            A::DevicePtr(guards.as_device_ptr()),
        ];
        if name == "xe_scalar" {
            args.extend([
                A::DevicePtr(fast.as_device_ptr()),
                A::U32(n as u32),
                A::U32(3),
            ]);
        } else {
            args.push(A::U32(n as u32));
        }
        launch(
            &function,
            LaunchConfig {
                grid: (n as u32).div_ceil(128),
                block: 128,
                shared_memory: 0,
            },
            &args,
            &s,
        )?;
        let mut g = vec![0u32; n];
        guards.copy_to(&mut g, &s)?;
        let values = output.read(&s)?;
        for (i, ((value, guard), (want, wg))) in values.iter().zip(g).zip(&expected).enumerate() {
            if guard != *wg || guard == 0 && value != want {
                return fail(out, name, i, (want, wg), (value, guard));
            }
        }
    }
    let mut f = vec![0u32; n];
    fast.copy_to(&mut f, &s)?;
    let fast_count = f.iter().filter(|&&x| x == 1).count();
    if fast_count < 2000 || fast_count == n {
        return Err("fast/fallback coverage".into());
    }
    let bits = [
        0u64,
        1,
        (1 << 52) - 1,
        1 << 52,
        0x3ff0000000000000,
        0x8000000000000000,
        0x8000000000000001,
        0x7fefffffffffffff,
        0x7ff0000000000000,
        0xfff0000000000000,
        0x7ff8000000000000,
    ];
    let input = upload(c, &s, &bits)?;
    let output = Soa::new(c, &s, &vec![Value::default(); bits.len()])?;
    let guards = upload(c, &s, &vec![0u32; bits.len()])?;
    launch(
        &module.function("xe_encode64")?,
        LaunchConfig {
            grid: 1,
            block: 128,
            shared_memory: 0,
        },
        &[
            A::DevicePtr(input.as_device_ptr()),
            output.argument(),
            A::DevicePtr(guards.as_device_ptr()),
            A::U32(bits.len() as u32),
        ],
        &s,
    )?;
    let values = output.read(&s)?;
    let mut g = vec![0u32; bits.len()];
    guards.copy_to(&mut g, &s)?;
    for (i, ((&bits, value), guard)) in bits.iter().zip(&values).zip(g).enumerate() {
        let want = Value::from_f64(f64::from_bits(bits));
        if want.is_err() != (guard != 0) || want.is_ok_and(|v| v != *value) {
            return fail(out, "encode", i, want, (value, guard));
        }
    }
    write(
        out,
        &serde_json::json!({"status":"passed","scalar_cases":n,"integer_fallback_cases":n,"fast_cases":fast_count,"codec_cases":bits.len(),"retained_expected_values_reused":true}),
    )
}
fn project(
    c: &Rc<Context>,
    reference: &Module,
    modules: &[Module; 4],
    out: &str,
    smoke: bool,
) -> Result<()> {
    let m = model();
    let p = LinearProgram::new(&m)?;
    let mut pairs = 0;
    let mut refusals = 0;
    let mut windows = 0;
    let mut controllers = 0;
    let layouts = if smoke {
        vec![Layout::Int8, Layout::Fp16, Layout::Bf16]
    } else {
        vec![Layout::Int8, Layout::Fp16, Layout::Bf16, Layout::Simt]
    };
    for layout in layouts {
        let mut e = Engine::new(&p, LpSettings::published(480, 200));
        let op =
            tensor_cost::Operator::new(&e, Settings::new(Format::Fp64, Policy::Uniform), layout)?;
        e.restrict_step(op.step)?;
        let g = op.generation(op.initial())?;
        let trajectory = tensor_cost::run(
            &e,
            &op,
            &mut HostOracle,
            64,
            &CancellationToken::new(),
            None,
            |_, _| false,
        );
        let mut gpu = device::Oracle::new(Rc::clone(c), &op, reference, modules, &e, false)?;
        for t in [false, true] {
            for sample in 0..if smoke { 2 } else { 14 } {
                let v = if sample == 13 {
                    (0..32)
                        .map(|i| {
                            if i % 3 == 0 {
                                2.0816681711721685e-17
                            } else {
                                1.
                            }
                        })
                        .collect::<Vec<_>>()
                } else if sample == 12 {
                    if t {
                        trajectory.core.scaled_dual.clone()
                    } else {
                        trajectory.core.scaled_primal.clone()
                    }
                } else {
                    (0..32)
                        .map(|i| {
                            if sample == 0 {
                                0.
                            } else {
                                (((i * 37 + sample * 17) % 127) as f64 - 63.)
                                    * 2f64.powi([-200, -30, -10, 0, 30, 60][sample % 6])
                            }
                        })
                        .collect::<Vec<_>>()
                };
                let values = v
                    .into_iter()
                    .map(Value::from_f64)
                    .collect::<std::result::Result<Vec<_>, _>>()?;
                let cpu = tensor_cost::expanded_probe(&op, &g, t, &values);
                let device = gpu.probe(&g, t, &values);
                match (cpu, device) {
                    (Ok(cpu), Ok(device)) => {
                        if cpu.0 != device.0
                            || cpu.1.iter().map(|v| v.to_bits()).collect::<Vec<_>>()
                                != device.1.iter().map(|v| v.to_bits()).collect::<Vec<_>>()
                            || cpu.2 != device.2
                        {
                            return fail(out, "expanded_product", pairs, cpu, device);
                        }
                    }
                    (Err(_), Err(_)) => refusals += 1,
                    (cpu, device) => {
                        return fail(out, "expanded_product_refusal", pairs, cpu, device);
                    }
                }
                pairs += 1;
            }
        }
        let state = Fp64Controller::new(&e).state().clone();
        for length in if smoke {
            vec![2]
        } else {
            vec![1, 2, 8, 31, 32]
        } {
            let cpu = HostOracle.window(&e, &op, &g, &state, length)?;
            let actual = gpu.window(&e, &op, &g, &state, length)?;
            let bits = |v: &[f64]| v.iter().map(|v| v.to_bits()).collect::<Vec<_>>();
            if cpu.failure != actual.failure
                || cpu.counts != actual.counts
                || bits(&cpu.primal) != bits(&actual.primal)
                || bits(&cpu.dual) != bits(&actual.dual)
                || !device::same_state(
                    cpu.pre.as_ref().ok_or("CPU penultimate")?,
                    actual.pre.as_ref().ok_or("GPU penultimate")?,
                )
            {
                return fail(
                    out,
                    "expanded_window",
                    windows,
                    (&cpu.counts, cpu.failure, bits(&cpu.primal), bits(&cpu.dual)),
                    (
                        &actual.counts,
                        actual.failure,
                        bits(&actual.primal),
                        bits(&actual.dual),
                    ),
                );
            }
            let reference_input = actual.pre.as_ref().unwrap();
            let expected = HostOracle.reference(&e, reference_input)?;
            let result = gpu.reference(&e, reference_input)?;
            if bits(&expected.0) != bits(&result.0) || bits(&expected.1) != bits(&result.1) {
                return fail(out, "reference_binding", windows, expected, result);
            }
            windows += 1;
        }
        if !smoke {
            let actual = tensor_cost::run(
                &e,
                &op,
                &mut gpu,
                64,
                &CancellationToken::new(),
                None,
                |_, _| false,
            );
            if serde_json::to_vec(&actual)? != serde_json::to_vec(&trajectory)? {
                return fail(out, "expanded_controller", controllers, trajectory, actual);
            }
            controllers += 1;
        }
    }
    write(
        out,
        &serde_json::json!({"status":"passed","new_product_pairs":pairs,"expected_refusals":refusals,"new_window_reference_pairs":windows,"new_controller_pairs":controllers,"sanitizer_scope":smoke}),
    )
}
pub fn run(args: &[String]) -> Result<()> {
    if args.len() != 4 {
        return Err("device-checks primitive|project|sanitizer FIXTURE REQUEST REPORT".into());
    }
    let request: Request = serde_json::from_slice(&std::fs::read(&args[2])?)?;
    if request.source_tree_sha256 != env!("EXPANDED_SOURCE_SHA256")
        || request.executable_sha256 != sha256::hex(&std::fs::read(std::env::current_exe()?)?)
        || std::env::var("AI_OPTIMIZER_GPU_LEASE").ok().as_deref() != Some("inherited")
        || std::env::var("CUDA_VISIBLE_DEVICES").ok().as_deref() != Some(request.device.as_str())
    {
        return Err("device acceptance lease/source binding".into());
    }
    let blobs = request
        .images
        .iter()
        .map(Image::bytes)
        .collect::<Result<Vec<_>>>()?;
    let c = Rc::new(Context::create(&request.device)?);
    let reference = c.load_module(&blobs[0])?;
    let modules: [Module; 4] = blobs[1..]
        .iter()
        .map(|b| c.load_module(b))
        .collect::<std::result::Result<Vec<_>, _>>()?
        .try_into()
        .map_err(|_| "images")?;
    match args[0].as_str() {
        "primitive" => primitive(&c, &modules[0], &args[1], &args[3]),
        "project" => project(&c, &reference, &modules, &args[3], false),
        "sanitizer" => project(&c, &reference, &modules, &args[3], true),
        _ => Err("unknown device scope".into()),
    }
}
