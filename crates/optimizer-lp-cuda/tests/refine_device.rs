//! ADR-0037 opt-in sparse-product differentials and bounded correction trajectories.
#![cfg(feature = "precision-research")]
use optimizer_core::{CancellationToken, LpSettings, Model};
use optimizer_cuda_sys::Context;
use optimizer_lp::{
    Engine, LinearProgram,
    refine::{
        EqualityBox, HostOracle, InnerOperator, ProductOracle, ProductWidth, correction_program,
        host_product, run,
    },
};
use optimizer_lp_cuda::refine::{Oracle, code_object_path};
use std::{
    rc::Rc,
    time::{Duration, Instant},
};
fn device() -> Option<Rc<Context>> {
    if std::env::var("AI_OPTIMIZER_GPU").ok().as_deref() != Some("1") {
        eprintln!("SKIP refine device gate: GPU opt-in unset");
        return None;
    }
    assert_eq!(
        std::env::var("AI_OPTIMIZER_GPU_LEASE").unwrap(),
        "inherited"
    );
    Some(Rc::new(
        Context::create(&std::env::var("CUDA_VISIBLE_DEVICES").unwrap()).unwrap(),
    ))
}
fn operator(model: &Model) -> InnerOperator {
    let p = LinearProgram::new(model).unwrap();
    let eq = EqualityBox::new(&p).unwrap();
    let (v, y) = eq.initial();
    let c = eq.correction(&v, &y).unwrap();
    let cp = correction_program(&eq, &c).unwrap();
    InnerOperator::new(
        &Engine::new(&cp, LpSettings::published(2000, 200)),
        p.column_count(),
    )
    .unwrap()
}
#[test]
fn refine_independent_fixture_and_both_orientations() {
    let Some(context) = device() else {
        return;
    };
    let image = std::fs::read(code_object_path()).unwrap();
    let mut gpu = Oracle::new(context, image, 1 << 30).unwrap();
    let fixture: serde_json::Value = serde_json::from_str(include_str!(
        "../../../tests/regression/lp-refine-oracle.json"
    ))
    .unwrap();
    let mut checked = 0;
    for case in fixture["cases"].as_array().unwrap() {
        let model = Model::from_json(&serde_json::to_vec(&case["model"]).unwrap()).unwrap();
        let op = operator(&model);
        gpu.bind(&op).unwrap();
        for width in [ProductWidth::F64, ProductWidth::F32] {
            for t in [false, true] {
                let length = if t { op.rows() } else { op.columns() };
                let input = (0..length)
                    .map(|i| ((i % 7) as f64 - 3.0) * 0.125)
                    .collect::<Vec<_>>();
                let expected = host_product(&op, t, &input, width).unwrap();
                for _ in 0..2 {
                    let actual = gpu.apply(&op, t, &input, width).unwrap();
                    assert_eq!(
                        actual.iter().map(|x| x.to_bits()).collect::<Vec<_>>(),
                        expected.iter().map(|x| x.to_bits()).collect::<Vec<_>>()
                    );
                    checked += 1;
                }
            }
        }
    }
    println!("refine independent fixture product checks={checked}");
    assert_eq!(checked, 1920);
}
#[test]
fn refine_partial_blocks_guards_and_generation() {
    let Some(context) = device() else {
        return;
    };
    let image = std::fs::read(code_object_path()).unwrap();
    let mut gpu = Oracle::new(context.clone(), image.clone(), 1 << 30).unwrap();
    let base: serde_json::Value =
        serde_json::from_str(include_str!("../../../examples/lp-model-v1.json")).unwrap();
    for count in [0, 1, 7, 8, 9, 31, 32, 33, 127, 128, 129] {
        let mut doc = base.clone();
        let row = doc["constraints"][0].clone();
        doc["constraints"] = serde_json::Value::Array(
            (0..count)
                .map(|i| {
                    let mut r = row.clone();
                    r["id"] = i.into();
                    r
                })
                .collect(),
        );
        let model = Model::from_json(&serde_json::to_vec(&doc).unwrap()).unwrap();
        let op = operator(&model);
        gpu.bind(&op).unwrap();
        for t in [false, true] {
            for w in [ProductWidth::F64, ProductWidth::F32] {
                let input = vec![0.25; if t { op.rows() } else { op.columns() }];
                let expected = host_product(&op, t, &input, w).unwrap();
                assert_eq!(gpu.apply(&op, t, &input, w).unwrap(), expected);
            }
        }
        let mut other = doc.clone();
        if count == 0 {
            other["variables"][0]["upper"]["value"] = 2.0.into();
        } else {
            other["constraints"][0]["terms"][0]["coefficient"] = 2.0.into();
        }
        let changed = Model::from_json(&serde_json::to_vec(&other).unwrap()).unwrap();
        let stale = operator(&changed);
        if count == 0 {
            continue;
        }
        let launches = gpu.counters.launches;
        assert!(
            gpu.apply(
                &stale,
                false,
                &vec![0.0; stale.columns()],
                ProductWidth::F64
            )
            .is_err()
        );
        assert_eq!(gpu.counters.launches, launches);
    }
    for count in [31, 32, 33, 127, 128, 129] {
        let mut doc = base.clone();
        let variable = doc["variables"][0].clone();
        doc["variables"] = serde_json::Value::Array(
            (0..count)
                .map(|i| {
                    let mut v = variable.clone();
                    v["id"] = i.into();
                    v
                })
                .collect(),
        );
        doc["constraints"][0]["terms"] = serde_json::Value::Array(
            (0..count)
                .map(
                    |i| serde_json::json!({"variable_id":i,"coefficient":if i%2==0{1.0}else{-0.5}}),
                )
                .collect(),
        );
        let model = Model::from_json(&serde_json::to_vec(&doc).unwrap()).unwrap();
        let op = operator(&model);
        gpu.bind(&op).unwrap();
        for width in [ProductWidth::F64, ProductWidth::F32] {
            for t in [false, true] {
                let input = (0..if t { op.rows() } else { op.columns() })
                    .map(|i| ((i % 5) as f64 - 2.0) / 8.0)
                    .collect::<Vec<_>>();
                let expected = host_product(&op, t, &input, width).unwrap();
                let actual = gpu.apply(&op, t, &input, width).unwrap();
                assert_eq!(
                    actual.iter().map(|x| x.to_bits()).collect::<Vec<_>>(),
                    expected.iter().map(|x| x.to_bits()).collect::<Vec<_>>()
                );
            }
        }
    }
    let model = Model::from_json(include_bytes!("../../../examples/lp-model-v1.json")).unwrap();
    let op = operator(&model);
    let mut limited = Oracle::new(context, image, 1).unwrap();
    assert!(limited.bind(&op).is_err());
    assert_eq!(limited.counters.allocations, 0);
    gpu.bind(&op).unwrap();
    assert!(
        gpu.apply(
            &op,
            false,
            &vec![f64::from_bits(1); op.columns()],
            ProductWidth::F32
        )
        .is_err()
    );
}
#[test]
fn refine_cpu_device_trajectory_and_repeatability() {
    let Some(context) = device() else {
        return;
    };
    let image = std::fs::read(code_object_path()).unwrap();
    let model = Model::from_json(include_bytes!("../../../examples/lp-model-v1.json")).unwrap();
    let p = LinearProgram::new(&model).unwrap();
    let eq = EqualityBox::new(&p).unwrap();
    for (width, anchor) in [
        (ProductWidth::F64, false),
        (ProductWidth::F32, false),
        (ProductWidth::F32, true),
    ] {
        let method = LpSettings::published(200, 200);
        let expected = run(
            &eq,
            method,
            width,
            anchor,
            1e-9,
            Instant::now() + Duration::from_secs(20),
            &CancellationToken::new(),
            &mut HostOracle,
            |_, _| false,
        );
        for _ in 0..2 {
            let mut gpu = Oracle::new(context.clone(), image.clone(), 1 << 30).unwrap();
            let actual = run(
                &eq,
                method,
                width,
                anchor,
                1e-9,
                Instant::now() + Duration::from_secs(20),
                &CancellationToken::new(),
                &mut gpu,
                |_, _| false,
            );
            assert_eq!(actual, expected);
        }
    }
}
