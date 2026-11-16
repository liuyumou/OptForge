use lp_general_lowbit::merit::EngineMerit;
use lp_general_lowbit::{
    Result,
    operator::{Format, Operator},
    solve::{Settings, cpu},
};
use optimizer_core::Model;
use optimizer_lp::{Engine, LinearProgram};
use serde_json::{Value, json};
use sha2::{Digest, Sha256};
use std::{
    fs::File,
    io::{self, BufRead, Read, Write},
    path::Path,
};

fn run() -> Result<()> {
    let args: Vec<_> = std::env::args().collect();
    if args.len() < 3
        || ![
            "cpu",
            "operator",
            "gpu",
            "gpu-probe",
            "gpu-fixed",
            "tensor-operator",
            "gpu-tensor",
            "gpu-tensor-probe",
            "assess",
            "assess-proven",
            "tighten",
        ]
        .contains(&args[1].as_str())
        || args.len() != if args[1].starts_with("gpu") { 4 } else { 3 }
    {
        return Err(
            "usage: lp-general-lowbit cpu|operator|gpu|gpu-probe MODEL [CUBIN] < requests.jsonl"
                .into(),
        );
    }
    let mut bytes = Vec::new();
    File::open(&args[2])?
        .take((384 << 20) + 1)
        .read_to_end(&mut bytes)?;
    if bytes.len() > 384 << 20 {
        return Err("model byte limit".into());
    }
    let hash = format!("{:x}", Sha256::digest(&bytes));
    let model = Model::from_json(&bytes)?;
    drop(bytes);
    let mut input = io::stdin().lock();
    let mut cached: Option<(bool, lp_general_lowbit::device::Device)> = None;
    loop {
        let mut line = Vec::new();
        let n = (&mut input)
            .take((128 << 20) + 1)
            .read_until(b'\n', &mut line)?;
        if n == 0 {
            break;
        }
        if n > 128 << 20 {
            return Err("request byte limit".into());
        }
        let request: Value = serde_json::from_slice(&line)?;
        let settings: Settings = serde_json::from_value(request["settings"].clone())?;
        settings.validate()?;
        let mut result = if matches!(
            args[1].as_str(),
            "tensor-operator" | "gpu-tensor" | "gpu-tensor-probe"
        ) {
            use lp_general_lowbit::{
                tensor::{Config, Packed},
                tensor_device,
            };
            let mut config: Config =
                serde_json::from_value(request.get("tensor").cloned().unwrap_or(json!({})))?;
            config.validate()?;
            if settings.format.components() > 0 {
                if request
                    .get("tensor")
                    .and_then(|t| t.get("components"))
                    .is_some()
                    && config.components != settings.format.components()
                {
                    return Err("format/component mismatch".into());
                }
                config.components = settings.format.components();
            }
            config.validate()?;
            if args[1] == "gpu-tensor" {
                lp_general_lowbit::gpu_tensor::solve(
                    &model,
                    &settings,
                    Path::new(&args[3]),
                    &config,
                )?
            } else {
                let p = LinearProgram::new(&model)?;
                let e = Engine::new(&p, settings.lp());
                let op = Operator::new_for(&e, Format::Native)?;
                let packed = Packed::new(&op, &config)?;
                if args[1] == "tensor-operator" {
                    json!({"operator":op,"packed":packed,"tensor_config":config})
                } else {
                    let tr = request["transpose"].as_bool().ok_or("transpose boolean")?;
                    let vector: Vec<f64> = serde_json::from_value(request["vector"].clone())?;
                    let limit = request
                        .get("local_limit")
                        .and_then(Value::as_f64)
                        .unwrap_or(f64::MAX);
                    if !limit.is_finite() || limit < 0. {
                        return Err("local limit domain".into());
                    }
                    let mut d = tensor_device::Device::new(
                        &e,
                        &op,
                        Some(&packed),
                        Path::new(&args[3]),
                        settings.format,
                        &config,
                    )?;
                    let anchor: Vec<f64> = serde_json::from_value(
                        request
                            .get("anchor")
                            .cloned()
                            .unwrap_or(json!(vec![0.; vector.len()])),
                    )?;
                    let product = d.probe(tr, &vector, &anchor, limit)?;
                    json!({"operator":op,"packed":packed,"product":product,"tensor_config":config})
                }
            }
        } else if args[1] == "cpu" {
            cpu(&model, &settings)?
        } else if args[1] == "tighten" {
            let (tightened, proof) = lp_general_lowbit::implied::derive(&model)?;
            json!({"model":tightened.as_ref().unwrap_or(&model).document(),"bound_proof":proof})
        } else if args[1] == "assess" || args[1] == "assess-proven" {
            let p = LinearProgram::new(&model)?;
            let x: Vec<f64> = serde_json::from_value(request["primal"].clone())?;
            let y: Vec<f64> = serde_json::from_value(request["dual"].clone())?;
            if x.len() != p.column_count() || y.len() != p.row_count() {
                return Err("witness dimensions".into());
            }
            if args[1] == "assess-proven" {
                let context = lp_general_lowbit::implied::Context::new(&model, &p)?;
                let mut r = lp_general_lowbit::solve::assess_repaired(
                    &model,
                    context.program(&p),
                    &x,
                    &y,
                    settings.tolerance,
                )?;
                r["bound_proof"] = json!(context.proof);
                r
            } else {
                lp_general_lowbit::solve::assess(&model, &p, &x, &y, settings.tolerance)?
            }
        } else if args[1] == "gpu" {
            lp_general_lowbit::gpu::solve(&model, &settings, Path::new(&args[3]))?
        } else {
            let p = LinearProgram::new(&model)?;
            let e = Engine::new(&p, settings.lp());
            let op = if args[1] == "gpu-fixed" {
                Operator::new_for(&e, settings.format)?
            } else {
                Operator::new(&e)?
            };
            if args[1] == "gpu-fixed" {
                let count = request["count"]
                    .as_u64()
                    .filter(|c| *c > 0 && *c <= 64)
                    .ok_or("fixed count")?;
                let state =
                    lp_general_lowbit::control::Fp64Controller::new_with_merit(&e, |x, y, w| {
                        e.projected_residual(x, y, w)
                    })
                    .state()
                    .clone();
                let mut device = lp_general_lowbit::device::Device::new(
                    &e,
                    &op,
                    Path::new(&args[3]),
                    settings.format,
                )?;
                device.reset(&state)?;
                let valid = device.advance(count, e.step(), state.weight, 0, f64::MAX)?;
                let (x, y) = device.endpoint()?;
                device.reset(&state)?;
                let (restored_x, restored_y) = device.endpoint()?;
                let result = json!({"kind":"fixed-admission","operator":op,"components":(0..op.rows.original.len()).map(|j|op.parts(j,settings.format)).collect::<Vec<_>>(),
                    "step":e.step(),"weight":state.weight,"initial_x":state.primal,"initial_y":state.dual,
                    "column_bounds":e.scaled_column_bounds(),"row_bounds":e.scaled_row_bounds(),"objective":e.scaled_objective(),
                    "primal":x,"dual":y,"restored_x":restored_x,"restored_y":restored_y,"valid":valid,"count":count,"model_sha256":hash});
                serde_json::to_writer(io::stdout().lock(), &result)?;
                println!();
                io::stdout().flush()?;
                continue;
            }
            let transpose = request["transpose"].as_bool().ok_or("transpose boolean")?;
            let x: Vec<f64> = serde_json::from_value(request["vector"].clone())?;
            let anchor: Vec<f64> = serde_json::from_value(request["anchor"].clone())?;
            let product = if args[1] == "gpu-probe" {
                if cached
                    .as_ref()
                    .is_none_or(|(s, _)| *s != settings.equilibrate)
                {
                    drop(cached.take());
                    cached = Some((
                        settings.equilibrate,
                        lp_general_lowbit::device::Device::new(
                            &e,
                            &op,
                            Path::new(&args[3]),
                            settings.format,
                        )?,
                    ));
                }
                let (_, device) = cached.as_mut().ok_or("device cache missing")?;
                device.set_format(&op, settings.format)?;
                device.probe(transpose, &x, &anchor)?
            } else {
                op.product(transpose, &x, &anchor, settings.format)?
            };
            let canonical: Vec<_> = (0..op.codes.len())
                .map(|i| op.parts(i, settings.format))
                .collect();
            json!({"operator":op,"canonical_components":canonical,"product":product,
                "native":op.product(transpose,&x,&anchor,Format::Native)?,
                "row_scale":e.preconditioner().row(),"column_scale":e.preconditioner().column()})
        };
        result["model_sha256"] = json!(hash);
        serde_json::to_writer(io::stdout().lock(), &result)?;
        println!();
        io::stdout().flush()?;
    }
    Ok(())
}
fn main() {
    if let Err(error) = run() {
        eprintln!("{error}");
        std::process::exit(2);
    }
}
