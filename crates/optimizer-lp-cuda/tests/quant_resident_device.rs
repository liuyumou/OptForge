//! ADR-0041 opt-in products, directed bounds, residency, and controller checks.
#![cfg(feature = "precision-research")]
use optimizer_core::{CancellationToken, LpSettings, Model};
use optimizer_lp::{Engine, LinearProgram, quant_resident::*};
use std::rc::Rc;
fn context() -> Option<Rc<optimizer_cuda_sys::Context>> {
    if std::env::var("AI_OPTIMIZER_GPU").ok().as_deref() != Some("1") {
        eprintln!("SKIP resident device acceptance: opt-in required");
        return None;
    }
    assert_eq!(
        std::env::var("AI_OPTIMIZER_GPU_LEASE").unwrap(),
        "inherited"
    );
    Some(Rc::new(
        optimizer_cuda_sys::Context::create(&std::env::var("CUDA_VISIBLE_DEVICES").unwrap())
            .unwrap(),
    ))
}
fn sparse() -> Model {
    let b = |x| serde_json::json!({"kind":"finite","value":x});
    let vars = (0..96)
        .map(|i| serde_json::json!({"id":i,"domain":"continuous","lower":b(-2.),"upper":b(2.)}))
        .collect::<Vec<_>>();
    let rows=(0..65).map(|i|serde_json::json!({"id":i,"lower":b(-10.),"upper":b(10.),"terms":(0..7).map(|k|serde_json::json!({"variable_id":(i*7+k*11)%96,"coefficient":((i+k)%17+1)as f64/13.})).collect::<Vec<_>>()})).collect::<Vec<_>>();
    Model::from_json(&serde_json::to_vec(&serde_json::json!({"schema_version":1,"model_id":"resident-sparse","variables":vars,"constraints":rows,"objective":{"sense":"minimize","offset":0.,"terms":[]}})).unwrap()).unwrap()
}
fn products(samples: usize) {
    let Some(context) = context() else {
        return;
    };
    let model = sparse();
    let p = LinearProgram::new(&model).unwrap();
    let e = Engine::new(&p, LpSettings::published(400, 200));
    let image = std::fs::read(optimizer_lp_cuda::quant_resident::code_object_path()).unwrap();
    let module = context.load_module(&image).unwrap();
    let mut checked = 0;
    for f in [Format::Fp16, Format::E4m3, Format::E5m2, Format::Fp64] {
        for policy in [Policy::Uniform, Policy::Selective] {
            let op = Operator::new(&e, Settings::new(f, policy), Layout::Segmented).unwrap();
            let mut oracle = optimizer_lp_cuda::quant_resident::Oracle::new(
                Rc::clone(&context),
                &op,
                &module,
                1 << 30,
                &e,
            )
            .unwrap();
            for stage in 0..4 {
                let mut promotion = Promotion::new(&op);
                if stage == 1 {
                    promotion.promote(&op, &[0]);
                }
                if stage == 2 {
                    promotion.promote(&op, &[1]);
                }
                if stage == 3 {
                    promotion.promote(&op, &(0..op.tiles.len()).collect::<Vec<_>>());
                }
                let g = op.generation(promotion).unwrap();
                for t in [false, true] {
                    for sample in 0..samples {
                        let v = (0..if t { op.rows } else { op.columns })
                            .map(|i| {
                                let n = ((i * 37 + sample * 19) % 127) as f64 - 63.;
                                n * 2f64.powi([-200, -140, -30, -10, 0, 30, 60][sample % 7])
                            })
                            .collect::<Vec<_>>();
                        let cpu = op.product(&g, t, &v).unwrap();
                        let gpu = oracle.probe(&g, t, &v).unwrap();
                        assert_eq!(
                            cpu.output.iter().map(|x| x.to_bits()).collect::<Vec<_>>(),
                            gpu.output.iter().map(|x| x.to_bits()).collect::<Vec<_>>(),
                            "product {f:?} {policy:?} {stage} {t} {sample}"
                        );
                        assert_eq!(
                            cpu.bounds.iter().map(|x| x.to_bits()).collect::<Vec<_>>(),
                            gpu.bounds.iter().map(|x| x.to_bits()).collect::<Vec<_>>(),
                            "bound {f:?} {policy:?} {stage} {t} {sample}"
                        );
                        assert_eq!(cpu.flags, gpu.flags);
                        assert_eq!(cpu.counts, gpu.counts);
                        checked += 1;
                    }
                }
            }
        }
    }
    checked += coefficient_extremes(&context, &module);
    println!("resident product and directed-bound vectors: {checked}");
}
fn coefficient_extremes(
    context: &Rc<optimizer_cuda_sys::Context>,
    module: &optimizer_cuda_sys::Module,
) -> usize {
    let finite = |x| serde_json::json!({"kind":"finite","value":x});
    let model=Model::from_json(&serde_json::to_vec(&serde_json::json!({"schema_version":1,"model_id":"resident-coefficient-extremes","variables":[{"id":0,"domain":"continuous","lower":finite(-2.),"upper":finite(2.)}],"constraints":[{"id":0,"lower":finite(-1.),"upper":finite(1.),"terms":[{"variable_id":0,"coefficient":1.}]}],"objective":{"sense":"minimize","offset":0.,"terms":[]}})).unwrap()).unwrap();
    let p = LinearProgram::new(&model).unwrap();
    let mut checked = 0;
    for exponent in [-149, -140, 100] {
        let method =
            LpSettings::from_json(include_bytes!("../../../examples/lp-settings-v1.json")).unwrap();
        let e = Engine::with_power2_scaling(&p, method, &[exponent], &[0]).unwrap();
        for format in [Format::Fp16, Format::E4m3, Format::E5m2] {
            let op = Operator::new(
                &e,
                Settings::new(format, Policy::Uniform),
                Layout::Segmented,
            )
            .unwrap();
            assert!(!Promotion::new(&op).native);
            let mut oracle = optimizer_lp_cuda::quant_resident::Oracle::new(
                Rc::clone(context),
                &op,
                module,
                1 << 30,
                &e,
            )
            .unwrap();
            for native in [false, true] {
                let mut promotion = Promotion::new(&op);
                if native {
                    promotion.promote(&op, &[0]);
                }
                let g = op.generation(promotion).unwrap();
                for t in [false, true] {
                    for value in [-0., 1., 2f64.powi(-140), 2f64.powi(-200), 2f64.powi(30)] {
                        let cpu = op.product(&g, t, &[value]).unwrap();
                        let gpu = oracle.probe(&g, t, &[value]).unwrap();
                        assert_eq!(
                            cpu.output.iter().map(|x| x.to_bits()).collect::<Vec<_>>(),
                            gpu.output.iter().map(|x| x.to_bits()).collect::<Vec<_>>()
                        );
                        assert_eq!(
                            cpu.bounds.iter().map(|x| x.to_bits()).collect::<Vec<_>>(),
                            gpu.bounds.iter().map(|x| x.to_bits()).collect::<Vec<_>>()
                        );
                        assert_eq!(cpu.flags, gpu.flags);
                        assert_eq!(cpu.counts, gpu.counts);
                        checked += 1;
                    }
                }
            }
        }
    }
    checked
}
#[test]
fn resident_product_guard_differentials() {
    products(7);
}
#[test]
fn resident_sanitizer_smoke() {
    products(1);
}
#[test]
fn resident_controller_and_fp64_bridges_match_cpu() {
    let Some(context) = context() else {
        return;
    };
    let b = |v| serde_json::json!({"kind":"finite","value":v});
    let model=Model::from_json(&serde_json::to_vec(&serde_json::json!({"schema_version":1,"model_id":"resident-controller","variables":[{"id":0,"domain":"continuous","lower":b(0.),"upper":b(2.)}],"constraints":[{"id":0,"lower":b(0.125),"upper":b(0.125),"terms":[{"variable_id":0,"coefficient":1.}]}],"objective":{"sense":"minimize","offset":0.,"terms":[]}})).unwrap()).unwrap();
    let p = LinearProgram::new(&model).unwrap();
    let image = std::fs::read(optimizer_lp_cuda::quant_resident::code_object_path()).unwrap();
    let module = context.load_module(&image).unwrap();
    let mut checked = 0;
    for (f, layout) in [
        (Format::Fp16, Layout::Segmented),
        (Format::E4m3, Layout::Segmented),
        (Format::E5m2, Layout::Segmented),
        (Format::Fp64, Layout::Segmented),
        (Format::Fp64, Layout::Tuned),
        (Format::Fp64, Layout::OriginalTuned),
    ] {
        let mut method =
            LpSettings::from_json(include_bytes!("../../../examples/lp-settings-v1.json")).unwrap();
        method.iteration_limit = 480;
        let mut e = Engine::new(&p, method);
        let op = Operator::new(&e, Settings::new(f, Policy::Selective), layout).unwrap();
        if layout.audits() {
            e.restrict_step(op.step).unwrap();
        }
        let cpu = run(
            &e,
            &op,
            &mut HostOracle,
            64,
            &CancellationToken::new(),
            None,
            |_, _| false,
        );
        let mut oracle = optimizer_lp_cuda::quant_resident::Oracle::new(
            Rc::clone(&context),
            &op,
            &module,
            1 << 30,
            &e,
        )
        .unwrap();
        let gpu = run(
            &e,
            &op,
            &mut oracle,
            64,
            &CancellationToken::new(),
            None,
            |_, _| false,
        );
        assert_eq!(cpu, gpu, "controller {f:?} {layout:?}");
        assert_eq!(oracle.counters.product_vector_transfers, 0);
        assert_eq!(oracle.counters.host_product_scans, 0);
        assert_eq!(oracle.counters.state_uploads, oracle.counters.windows);
        checked += 1;
    }
    println!("resident CPU/device controller comparisons: {checked}");
}
