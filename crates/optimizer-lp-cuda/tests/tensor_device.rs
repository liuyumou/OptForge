//! Opt-in ADR-0042 same-device arithmetic/controller and sanitizer acceptance.
#![cfg(feature = "precision-research")]
use optimizer_core::{CancellationToken, LpSettings, Model};
use optimizer_lp::{Engine, LinearProgram, tensor::*};
fn model() -> Model {
    let b = |x| serde_json::json!({"kind":"finite","value":x});
    let variables = (0..32)
        .map(|i| serde_json::json!({"id":i,"domain":"continuous","lower":b(-2.),"upper":b(2.)}))
        .collect::<Vec<_>>();
    let rows=(0..32).map(|r|serde_json::json!({"id":r,"lower":b(-1.),"upper":b(1.),"terms":(0..32).map(|c|serde_json::json!({"variable_id":c,"coefficient":if r==c{4.}else{((r+c)%3+1) as f64/32.}})).collect::<Vec<_>>()})).collect::<Vec<_>>();
    Model::from_json(&serde_json::to_vec(&serde_json::json!({"schema_version":1,"model_id":"tensor-dense","variables":variables,"constraints":rows,"objective":{"sense":"minimize","offset":0.,"terms":(0..32).map(|i|serde_json::json!({"variable_id":i,"coefficient":1.})).collect::<Vec<_>>()}})).unwrap()).unwrap()
}

fn context() -> Option<std::rc::Rc<optimizer_cuda_sys::Context>> {
    if std::env::var("AI_OPTIMIZER_GPU").ok().as_deref() != Some("1") {
        eprintln!("SKIP tensor device: explicit opt-in required");
        return None;
    }
    assert_eq!(
        std::env::var("AI_OPTIMIZER_GPU_LEASE").unwrap(),
        "inherited"
    );
    Some(std::rc::Rc::new(
        optimizer_cuda_sys::Context::create(&std::env::var("CUDA_VISIBLE_DEVICES").unwrap())
            .unwrap(),
    ))
}
#[test]
fn tensor_products_match_exact_cpu_in_both_orientations() {
    let Some(context) = context() else {
        return;
    };
    let m = model();
    let p = LinearProgram::new(&m).unwrap();
    let e = Engine::new(&p, LpSettings::published(480, 200));
    let module = context
        .load_module(&std::fs::read(optimizer_lp_cuda::tensor::code_object_path()).unwrap())
        .unwrap();
    let mut total = 0;
    for layout in [
        Layout::Int8,
        Layout::Fp16,
        Layout::Bf16,
        Layout::Simt,
        Layout::Segmented,
    ] {
        let op = Operator::new(&e, Settings::new(Format::Fp64, Policy::Uniform), layout).unwrap();
        let trajectory = run(
            &e,
            &op,
            &mut HostOracle,
            64,
            &CancellationToken::new(),
            None,
            |_, _| false,
        );
        let mut gpu = optimizer_lp_cuda::tensor::Oracle::new(
            std::rc::Rc::clone(&context),
            &op,
            &module,
            1 << 30,
            &e,
        )
        .unwrap();
        for native in [false, true] {
            let mut promotion = op.initial();
            if native && !promotion.native {
                assert!(promotion.promote(&op, &[0]));
            }
            let g = op.generation(promotion).unwrap();
            for t in [false, true] {
                for sample in 0..13 {
                    let v = if sample == 12 {
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
                    let cpu = op.product(&g, t, &v).unwrap();
                    let device = gpu.probe(&g, t, &v).unwrap();
                    assert_eq!(cpu.flags, device.flags, "{layout:?} {native} {t} {sample}");
                    assert_eq!(
                        cpu.output.iter().map(|x| x.to_bits()).collect::<Vec<_>>(),
                        device
                            .output
                            .iter()
                            .map(|x| x.to_bits())
                            .collect::<Vec<_>>(),
                        "{layout:?} {native} {t} {sample}"
                    );
                    assert_eq!(
                        cpu.bounds.iter().map(|x| x.to_bits()).collect::<Vec<_>>(),
                        device
                            .bounds
                            .iter()
                            .map(|x| x.to_bits())
                            .collect::<Vec<_>>()
                    );
                    assert_eq!(cpu.counts, device.counts, "physical component work");
                    total += 1;
                }
            }
        }
    }
    println!(
        "tensor products: {total} independent CPU/device pairs, both orientations, synthetic and recorded trajectory vectors"
    );
}
#[test]
fn tensor_controller_windows_match_cpu_and_charge_physical_work() {
    let Some(context) = context() else {
        return;
    };
    let m = model();
    let p = LinearProgram::new(&m).unwrap();
    let module = context
        .load_module(&std::fs::read(optimizer_lp_cuda::tensor::code_object_path()).unwrap())
        .unwrap();
    for layout in [
        Layout::Int8,
        Layout::Fp16,
        Layout::Bf16,
        Layout::Simt,
        Layout::Segmented,
    ] {
        let mut e = Engine::new(&p, LpSettings::published(480, 200));
        let op = Operator::new(&e, Settings::new(Format::Fp64, Policy::Uniform), layout).unwrap();
        e.restrict_step(op.step).unwrap();
        let cpu = run(
            &e,
            &op,
            &mut HostOracle,
            64,
            &CancellationToken::new(),
            None,
            |_, _| false,
        );
        let mut gpu = optimizer_lp_cuda::tensor::Oracle::new(
            std::rc::Rc::clone(&context),
            &op,
            &module,
            1 << 30,
            &e,
        )
        .unwrap();
        let out = run(
            &e,
            &op,
            &mut gpu,
            64,
            &CancellationToken::new(),
            None,
            |_, _| false,
        );
        assert_eq!(out, cpu, "{layout:?}");
        assert_eq!(out.core.stop, "work_horizon");
        assert_eq!(gpu.counters.host_product_scans, 0);
        assert_eq!(gpu.counters.product_vector_transfers, 0);
        if layout.tensor() {
            assert!(out.counts.useful_windows > 0);
        }
    }
}
#[test]
fn tensor_range_refuses_before_accepting_a_product() {
    let Some(context) = context() else {
        return;
    };
    let m = model();
    let p = LinearProgram::new(&m).unwrap();
    let e = Engine::new(&p, LpSettings::published(480, 200));
    let module = context
        .load_module(&std::fs::read(optimizer_lp_cuda::tensor::code_object_path()).unwrap())
        .unwrap();
    for layout in [Layout::Int8, Layout::Fp16, Layout::Bf16] {
        let op = Operator::new(&e, Settings::new(Format::Fp64, Policy::Uniform), layout).unwrap();
        let g = op.generation(op.initial()).unwrap();
        let mut gpu = optimizer_lp_cuda::tensor::Oracle::new(
            std::rc::Rc::clone(&context),
            &op,
            &module,
            1 << 30,
            &e,
        )
        .unwrap();
        let mut v = vec![1.; 32];
        v[0] = 1e100;
        v[1] = 1e-100;
        let out = gpu.probe(&g, false, &v).unwrap();
        assert!(out.flags.iter().all(|f| *f != 0));
        assert_eq!(out.counts.mma_instructions, 0);
    }
}
