//! ADR-0040 exact same-device arithmetic differentials; CPU acceptance skips devices.
#![cfg(feature = "precision-research")]
use optimizer_core::{CancellationToken, LpSettings, Model};
use optimizer_lp::{
    Engine, LinearProgram,
    quant::{Format, HostOracle, Operator, Oracle, Policy, Promotion, Settings, run},
};
use std::rc::Rc;
fn context() -> Option<Rc<optimizer_cuda_sys::Context>> {
    if std::env::var("AI_OPTIMIZER_GPU").ok().as_deref() != Some("1") {
        eprintln!("SKIP quant device acceptance: opt-in required");
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
fn compare(samples: usize) {
    let Some(context) = context() else {
        return;
    };
    let bound = |x| serde_json::json!({"kind":"finite","value":x});
    let variables=(0..96).map(|i|serde_json::json!({"id":i,"domain":"continuous","lower":bound(-2.),"upper":bound(2.)})).collect::<Vec<_>>();
    let rows=(0..65).map(|i|serde_json::json!({"id":i,"lower":bound(-10.),"upper":bound(10.),"terms":(0..7).map(|k|serde_json::json!({"variable_id":(i*7+k*11)%96,"coefficient":((i+k)%17+1)as f64/13.})).collect::<Vec<_>>()})).collect::<Vec<_>>();
    let model=Model::from_json(&serde_json::to_vec(&serde_json::json!({"schema_version":1,"model_id":"quant-sparse-tiles","variables":variables,"constraints":rows,"objective":{"sense":"minimize","offset":0.,"terms":[]}})).unwrap()).unwrap();
    let p = LinearProgram::new(&model).unwrap();
    let e = Engine::new(&p, LpSettings::published(200, 200));
    let image = std::fs::read(optimizer_lp_cuda::quant::code_object_path()).unwrap();
    let mut checked = 0;
    for f in [Format::Fp16, Format::E4m3, Format::E5m2] {
        for policy in [Policy::Uniform, Policy::Selective] {
            let op = Operator::new(&e, Settings::new(f, policy)).unwrap();
            let mut oracle =
                optimizer_lp_cuda::quant::Oracle::new(Rc::clone(&context), &op, &image, 1 << 30)
                    .unwrap();
            let mut promotion = Promotion::new(&op);
            for stage in 0..2 {
                if stage == 1 {
                    let ids = (0..op.tiles.len()).collect::<Vec<_>>();
                    promotion.promote(&op, &ids);
                }
                for t in [false, true] {
                    for sample in 0..samples {
                        let vector = (0..if t { op.rows } else { op.columns })
                            .map(|i| {
                                let n = ((i * 37 + sample * 19) % 127) as f64 - 63.;
                                n * 2f64.powi(-20 + (sample % 10) as i32)
                            })
                            .collect::<Vec<_>>();
                        let expected = op.product(&promotion, t, &vector).unwrap();
                        let actual = oracle.product(&op, &promotion, t, &vector).unwrap();
                        assert_eq!(
                            expected.iter().map(|x| x.to_bits()).collect::<Vec<_>>(),
                            actual.iter().map(|x| x.to_bits()).collect::<Vec<_>>(),
                            "{f:?} {policy:?} {t} {stage} {sample}"
                        );
                        checked += 1;
                    }
                }
            }
        }
    }
    println!("quant bitwise product comparisons: {checked}");
}
#[test]
fn quant_product_differentials() {
    compare(16);
}
#[test]
fn quant_sanitizer_smoke() {
    compare(1);
}
#[test]
fn quant_controller_matches_host() {
    let Some(context) = context() else {
        return;
    };
    let model = Model::from_json(include_bytes!("../../../examples/lp-model-v1.json")).unwrap();
    let p = LinearProgram::new(&model).unwrap();
    let image = std::fs::read(optimizer_lp_cuda::quant::code_object_path()).unwrap();
    for f in [Format::Fp16, Format::E4m3, Format::E5m2] {
        for policy in [Policy::Uniform, Policy::Selective] {
            let mut e = Engine::new(&p, LpSettings::published(400, 200));
            let op = Operator::new(&e, Settings::new(f, policy)).unwrap();
            e.restrict_step(op.step).unwrap();
            let mut oracle =
                optimizer_lp_cuda::quant::Oracle::new(Rc::clone(&context), &op, &image, 1 << 30)
                    .unwrap();
            let cpu = run(
                &e,
                &op,
                &mut HostOracle,
                true,
                &CancellationToken::new(),
                None,
                |_, _| false,
            );
            let gpu = run(
                &e,
                &op,
                &mut oracle,
                true,
                &CancellationToken::new(),
                None,
                |_, _| false,
            );
            assert_eq!(cpu, gpu);
        }
    }
}
