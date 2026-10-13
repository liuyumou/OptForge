//! ADR-0035 device gates. Opt-in requires the supervising shared lease.
#![cfg(feature = "precision-research")]
use optimizer_core::{
    Fp64ExecutionSettings, LpDiagnostics, LpExecutionDiagnostics, LpSettings, Model,
};
use optimizer_cuda_sys::{Argument as A, Context, DeviceBuffer, LaunchConfig, launch};
use optimizer_lp::{
    Engine, LinearProgram,
    control::Fp64Controller,
    exec::{self, Decoded, Mode},
};
use optimizer_lp_cuda::exec::{Executor, code_object_path};
use std::rc::Rc;
fn device() -> Option<Rc<Context>> {
    if std::env::var("AI_OPTIMIZER_GPU").ok().as_deref() != Some("1") {
        eprintln!("SKIP exec device gate: GPU opt-in unset");
        return None;
    }
    assert_eq!(
        std::env::var("AI_OPTIMIZER_GPU_LEASE").unwrap(),
        "inherited"
    );
    let uuid = std::env::var("CUDA_VISIBLE_DEVICES").unwrap();
    Some(Rc::new(Context::create(&uuid).unwrap()))
}
fn diagnostics() -> LpDiagnostics {
    let mut d = LpDiagnostics::new(true, true);
    d.device_buffer_limit_bytes = Some(exec::RESIDENT_CAP);
    d.execution = Some(LpExecutionDiagnostics::new(
        Fp64ExecutionSettings::from_json(include_bytes!("../../../examples/lp-execution-v1.json"))
            .unwrap(),
    ));
    d
}
#[test]
fn exec_device_trajectories_restore_and_controller_boundaries() {
    let Some(context) = device() else {
        return;
    };
    let model = Model::from_json(include_bytes!("../../../examples/lp-model-v1.json")).unwrap();
    let p = LinearProgram::new(&model).unwrap();
    let image = std::fs::read(code_object_path()).unwrap();
    let mut e = Engine::new(&p, LpSettings::published(48, 8));
    let op = exec::prepare_operator(&e, exec::RESIDENT_CAP, exec::PEAK_CAP).unwrap();
    e.restrict_step(op.step()).unwrap();
    for mode in [Mode::Cached, Mode::Uncached] {
        let mut d = diagnostics();
        let mut gpu = Executor::new(context.clone(), &e, &op, mode, &image, &mut d).unwrap();
        let mut c = Fp64Controller::new(&e);
        let initial = c.checkpoint();
        for index in 0..40 {
            if index == 19 {
                c.restore(&initial).unwrap();
            }
            let (x, y) = exec::step(&e, c.state(), &op).unwrap();
            assert_eq!(
                gpu.advance(&mut c, 1, e.step(), d.execution.as_mut().unwrap())
                    .unwrap(),
                None
            );
            c.commit_steps(1).unwrap();
            let bits = |v: &[f64]| v.iter().map(|v| v.to_bits()).collect::<Vec<_>>();
            assert_eq!(
                bits(&c.state().primal),
                bits(&x),
                "primal {mode:?} step {index}"
            );
            assert_eq!(
                bits(&c.state().dual),
                bits(&y),
                "dual {mode:?} step {index}"
            );
            if c.check_pending() {
                c.continue_after_check();
            }
        }
        assert!(d.execution.as_ref().unwrap().allocated_bytes <= op.receipt().resident_bytes);
    }
}
fn pointer<T: Copy>(b: &DeviceBuffer<T>) -> A {
    A::DevicePtr(b.as_device_ptr())
}
#[test]
fn exec_device_fraction_fixture_both_cache_modes() {
    let Some(context) = device() else {
        return;
    };
    let image = std::fs::read(code_object_path()).unwrap();
    let module = context.load_module(&image).unwrap();
    let stream = context.stream().unwrap();
    let fixture: serde_json::Value = serde_json::from_str(include_str!(
        "../../../tests/regression/lp-exec-oracle.json"
    ))
    .unwrap();
    let mut batches: Vec<Vec<&serde_json::Value>> = vec![vec![]];
    let mut length = 0;
    for case in fixture["cases"].as_array().unwrap() {
        let n = case["left"].as_array().unwrap().len() * case["repeat"].as_u64().unwrap() as usize;
        if n > exec::MAX_DIM {
            continue;
        }
        if length + n > exec::MAX_DIM || batches.last().unwrap().len() >= 128 {
            batches.push(vec![]);
            length = 0;
        }
        batches.last_mut().unwrap().push(case);
        length += n;
    }
    for cases in batches {
        let mut av = vec![];
        let mut bv = vec![];
        let mut offsets = vec![0_u32];
        for case in &cases {
            let repeat = case["repeat"].as_u64().unwrap() as usize;
            av.extend(
                case["left"]
                    .as_array()
                    .unwrap()
                    .iter()
                    .map(|x| x.as_u64().unwrap())
                    .collect::<Vec<_>>()
                    .repeat(repeat),
            );
            bv.extend(
                case["right"]
                    .as_array()
                    .unwrap()
                    .iter()
                    .map(|x| x.as_u64().unwrap())
                    .collect::<Vec<_>>()
                    .repeat(repeat),
            );
            offsets.push(av.len() as u32);
        }
        let n = av.len();
        let rows = cases.len();
        if av.is_empty() {
            av.push(0);
            bv.push(0);
        }
        macro_rules! buffer {
            ($data:expr) => {{
                let v = $data;
                let mut b = context.allocate(v.len()).unwrap();
                b.copy_from(&v, &stream).unwrap();
                b
            }};
        }
        let a = buffer!(av);
        let x = buffer!(bv);
        let indices = buffer!((0..n.max(1) as u32).collect::<Vec<_>>());
        let off = buffer!(offsets.clone());
        let cached = buffer!(vec![Decoded::default(); n.max(1)]);
        for mode in [Mode::Cached, Mode::Uncached] {
            let out = buffer!(vec![0_u64; rows]);
            let guards = buffer!(vec![0_u32; rows]);
            let flags = buffer!(vec![0_u32; rows]);
            let errors = buffer!(vec![i32::MAX; rows]);
            let prep = buffer!(vec![0_u32; n.max(1)]);
            if mode == Mode::Cached {
                launch(
                    &module.function("exec_prepare").unwrap(),
                    LaunchConfig {
                        grid: (n.max(1) as u32).div_ceil(256),
                        block: 256,
                        shared_memory: 0,
                    },
                    &[
                        pointer(&x),
                        pointer(&cached),
                        pointer(&prep),
                        A::U32(n as u32),
                    ],
                    &stream,
                )
                .unwrap();
            }
            launch(
                &module
                    .function(if mode == Mode::Cached {
                        "exec_cached"
                    } else {
                        "exec_uncached"
                    })
                    .unwrap(),
                LaunchConfig {
                    grid: (rows as u32).div_ceil(8),
                    block: 256,
                    shared_memory: 0,
                },
                &[
                    pointer(&a),
                    pointer(&indices),
                    pointer(&off),
                    pointer(&indices),
                    pointer(&x),
                    pointer(&cached),
                    pointer(&out),
                    pointer(&guards),
                    pointer(&flags),
                    pointer(&errors),
                    A::U32(rows as u32),
                    A::U32(0),
                ],
                &stream,
            )
            .unwrap();
            let mut output = vec![0_u64; rows];
            out.copy_to(&mut output, &stream).unwrap();
            let mut gs = vec![0_u32; rows];
            guards.copy_to(&mut gs, &stream).unwrap();
            let mut fs = gs.clone();
            flags.copy_to(&mut fs, &stream).unwrap();
            let mut es = vec![0_i32; rows];
            errors.copy_to(&mut es, &stream).unwrap();
            let mut ps = vec![0_u32; n.max(1)];
            prep.copy_to(&mut ps, &stream).unwrap();
            for (row, case) in cases.iter().enumerate() {
                let e = &case["expected"];
                let g = ps[offsets[row] as usize..offsets[row + 1] as usize]
                    .iter()
                    .fold(gs[row], |a, b| a | b);
                if let Some(error) = e.get("error") {
                    let bit = match error.as_str().unwrap() {
                        "nonfinite_operand" => 1,
                        "product_exponent_window" => 2,
                        "output_overflow" => 4,
                        other => panic!("unhandled {other}"),
                    };
                    assert_ne!(g & bit, 0, "{mode:?} {case}");
                } else {
                    assert_eq!(g, 0, "{mode:?} {case}");
                    assert_eq!(output[row], e["bits"].as_u64().unwrap(), "{mode:?} {case}");
                    assert_eq!(
                        fs[row] as u64,
                        e["flags"].as_u64().unwrap(),
                        "{mode:?} {case}"
                    );
                    assert_eq!(
                        es[row],
                        e["error_exponent"].as_i64().map_or(i32::MAX, |e| e as i32),
                        "{mode:?} {case}"
                    );
                }
            }
        }
    }
}

#[test]
fn exec_device_range_refusal_preserves_host_and_poisons_executor() {
    let Some(context) = device() else {
        return;
    };
    let mut model: serde_json::Value =
        serde_json::from_slice(include_bytes!("../../../examples/lp-model-v1.json")).unwrap();
    let mut row = model["constraints"][0].clone();
    row["id"] = serde_json::json!(1);
    row["terms"][1]["coefficient"] = serde_json::json!(-1.0);
    model["constraints"].as_array_mut().unwrap().push(row);
    let model = Model::from_json(&serde_json::to_vec(&model).unwrap()).unwrap();
    let p = LinearProgram::new(&model).unwrap();
    let image = std::fs::read(code_object_path()).unwrap();
    let mut e = Engine::new(&p, LpSettings::published(8, 8));
    let op = exec::prepare_operator(&e, exec::RESIDENT_CAP, exec::PEAK_CAP).unwrap();
    e.restrict_step(op.step()).unwrap();
    for mode in [Mode::Cached, Mode::Uncached] {
        let mut d = diagnostics();
        let mut gpu = Executor::new(context.clone(), &e, &op, mode, &image, &mut d).unwrap();
        let mut c = Fp64Controller::new(&e);
        c.replace_endpoint(vec![0.0; 2], vec![1e300, 1e-300])
            .unwrap();
        let before = c.state().clone();
        assert!(
            gpu.advance(&mut c, 1, e.step(), d.execution.as_mut().unwrap())
                .unwrap()
                .is_some()
        );
        assert_eq!(c.state().primal, before.primal);
        assert_eq!(c.state().dual, before.dual);
        assert_eq!(c.state().iterations, 0);
        assert!(
            gpu.advance(&mut c, 1, e.step(), d.execution.as_mut().unwrap())
                .is_err()
        );
    }
}
