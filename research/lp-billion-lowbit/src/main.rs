use lp_billion_lowbit::engine::Engine;
use lp_billion_lowbit::merit::EngineMerit;
use lp_billion_lowbit::{
    Result,
    operator::{Format, Operator},
    solve::{Settings, cpu},
};
use optimizer_lp::LinearProgram;
use serde_json::{Value, json};
use std::{
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
            "gpu-fast",
            "gpu-fast-probe",
            "assess",
            "assess-proven",
            "assess-fast",
            "tighten",
            "host-probe",
        ]
        .contains(&args[1].as_str())
        || args.len() != if args[1].starts_with("gpu") { 4 } else { 3 }
    {
        return Err(
            "usage: lp-billion-lowbit cpu|operator|gpu|gpu-probe MODEL [CUBIN] < requests.jsonl"
                .into(),
        );
    }
    let (model, hash) = lp_billion_lowbit::input::load(Path::new(&args[2]))?;
    // Reuse immutable original geometry for a batch of independent assessments.
    // No endpoint answer or certificate is cached.
    let check_program = if matches!(args[1].as_str(), "assess" | "assess-proven" | "assess-fast") {
        Some(LinearProgram::new(&model)?)
    } else {
        None
    };
    let check_context = if matches!(args[1].as_str(), "assess-proven" | "assess-fast") {
        Some(lp_billion_lowbit::implied::Context::new(
            &model,
            check_program.as_ref().ok_or("check program")?,
        )?)
    } else {
        None
    };
    let mut input = io::stdin().lock();
    let mut cached: Option<(bool, lp_billion_lowbit::device::Device)> = None;
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
            "tensor-operator" | "gpu-tensor" | "gpu-tensor-probe" | "gpu-fast" | "gpu-fast-probe"
        ) {
            use lp_billion_lowbit::{
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
            let fast: lp_billion_lowbit::fast_device::Config =
                serde_json::from_value(request.get("fast").cloned().unwrap_or(json!({})))?;
            fast.validate()?;
            if args[1] == "gpu-fast" {
                lp_billion_lowbit::gpu_tensor::solve_with_fast(
                    &model,
                    &settings,
                    Path::new(&args[3]),
                    &config,
                    Some(&fast),
                )?
            } else if args[1] == "gpu-tensor" {
                lp_billion_lowbit::gpu_tensor::solve(
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
                } else if args[1] == "gpu-fast-probe" {
                    let tr = request["transpose"].as_bool().ok_or("transpose boolean")?;
                    let vector: Vec<f64> = serde_json::from_value(request["vector"].clone())?;
                    let anchor: Vec<f64> = serde_json::from_value(
                        request
                            .get("anchor")
                            .cloned()
                            .unwrap_or(json!(vec![0.; vector.len()])),
                    )?;
                    let mut d = lp_billion_lowbit::fast_device::Device::new(
                        &e,
                        &op,
                        if settings.format.components() > 0 {
                            Some(&packed)
                        } else {
                            None
                        },
                        Path::new(&args[3]),
                        settings.format,
                        &config,
                        &fast,
                    )?;
                    let values = d.probe(tr, &vector, &anchor)?;
                    json!({"operator":op,"packed":packed,"proposal_values":values,"enclosed":false,"tensor_config":config,"fast_config":fast,"lanes":d.shapes()})
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
        } else if args[1] == "host-probe" {
            let p = LinearProgram::new(&model)?;
            let e = Engine::new(&p, settings.lp());
            let indexed = LinearProgram::new_indexed(&model)?;
            if p.matrix_sha256() != indexed.matrix_sha256() {
                return Err("indexed preparation differs from original bits".into());
            }
            let prepared = lp_billion_lowbit::host::engine(&indexed, settings.lp());
            let x: Vec<f64> = serde_json::from_value(request["primal"].clone())?;
            let y: Vec<f64> = serde_json::from_value(request["dual"].clone())?;
            let w = request["weight"].as_f64().ok_or("weight")?;
            if x.len() != p.column_count()
                || y.len() != p.row_count()
                || x.iter().chain(&y).any(|v| !v.is_finite())
                || !w.is_finite()
                || w <= 0.
            {
                return Err("host probe domain".into());
            }
            let original = e.step_once(&x, &y, w);
            let optimized = lp_billion_lowbit::host::step_once(&prepared, &x, &y, w);
            lp_billion_lowbit::host::with_products(&prepared, true, |products| {
                let mut workspace = lp_billion_lowbit::host::ResidualWorkspace::default();
                // Repeated, changed weights exercise reused buffers and worker inputs.
                for weight in [w, 1., w] {
                    assert_eq!(
                        workspace
                            .evaluate(products, &prepared, &x, &y, weight)
                            .to_bits(),
                        e.projected_residual(&x, &y, weight).to_bits()
                    );
                }
            });
            let bits = |v: &[f64]| v.iter().map(|x| x.to_bits()).collect::<Vec<_>>();
            if e.step().to_bits() != prepared.step().to_bits()
                || bits(e.scaled_matrix().0) != bits(prepared.scaled_matrix().0)
                || bits(e.scaled_matrix().1) != bits(prepared.scaled_matrix().1)
                || bits(e.scaled_objective()) != bits(prepared.scaled_objective())
                || bits(e.preconditioner().row()) != bits(prepared.preconditioner().row())
                || bits(e.preconditioner().column()) != bits(prepared.preconditioner().column())
            {
                return Err("host preparation differs from original bits".into());
            }
            json!({"original":original,"optimized":optimized,
                "original_merit":e.projected_residual(&x,&y,w),
                "optimized_merit":lp_billion_lowbit::host::projected_residual(&prepared,&x,&y,w),"preparation_exact":true})
        } else if args[1] == "cpu" {
            cpu(&model, &settings)?
        } else if args[1] == "tighten" {
            let (tightened, proof) = lp_billion_lowbit::implied::derive(&model)?;
            json!({"model":tightened.as_ref().unwrap_or(&model).document(),"bound_proof":proof})
        } else if args[1] == "assess" || args[1] == "assess-proven" || args[1] == "assess-fast" {
            let p = check_program.as_ref().ok_or("check program")?;
            let x: Vec<f64> = serde_json::from_value(request["primal"].clone())?;
            let y: Vec<f64> = serde_json::from_value(request["dual"].clone())?;
            if x.len() != p.column_count() || y.len() != p.row_count() {
                return Err("witness dimensions".into());
            }
            if args[1] == "assess-fast" {
                let context = check_context.as_ref().ok_or("check context")?;
                let mut assessor =
                    lp_billion_lowbit::assessment::Assessor::new(&model, context.program(p), true);
                assessor.prepare();
                let mut result = assessor.evaluate(&x, &y, settings.tolerance, false)?;
                drop(assessor);
                result["bound_proof"] = json!(context.proof);
                result
            } else if args[1] == "assess-proven" {
                let context = check_context.as_ref().ok_or("check context")?;
                let mut r = lp_billion_lowbit::solve::assess_repaired(
                    &model,
                    context.program(p),
                    &x,
                    &y,
                    settings.tolerance,
                )?;
                r["bound_proof"] = json!(context.proof);
                r
            } else {
                lp_billion_lowbit::solve::assess(&model, p, &x, &y, settings.tolerance)?
            }
        } else if args[1] == "gpu" {
            lp_billion_lowbit::gpu::solve(&model, &settings, Path::new(&args[3]))?
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
                    lp_billion_lowbit::control::Fp64Controller::new_with_merit(&e, |x, y, w| {
                        e.projected_residual(x, y, w)
                    })
                    .state()
                    .clone();
                let mut device = lp_billion_lowbit::device::Device::new(
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
                        lp_billion_lowbit::device::Device::new(
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
