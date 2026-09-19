//! Independent research representation, range and operator admission checks.
#![cfg(feature = "precision-research")]
use optimizer_lp::research::*;
#[test]
fn exact_components_cover_extreme_exponents_and_signed_zero() {
    let values = [
        0.0,
        -0.0,
        f64::from_bits(1),
        -f64::from_bits(1),
        f64::MIN_POSITIVE,
        f64::MAX,
        -f64::MAX,
        1.0 / 3.0,
        1.0_f64.next_up(),
        2.0_f64.next_down(),
    ];
    for x in values {
        let p = split(x).unwrap();
        assert_eq!(reconstruct(p, 3), x);
        if x != 0.0 {
            assert_eq!(reconstruct(p, 3).to_bits(), x.to_bits());
        }
    }
    let mut bits = 17002_u64;
    for _ in 0..10000 {
        bits ^= bits << 13;
        bits ^= bits >> 7;
        bits ^= bits << 17;
        let x = f64::from_bits(bits);
        if x.is_finite() {
            assert_eq!(reconstruct(split(x).unwrap(), 3), x);
        }
    }
    assert!(split(f64::INFINITY).is_err());
}
#[test]
fn powers_are_chosen_without_logarithms_and_refuse_loss() {
    assert_eq!(power_exponent(1.0), Ok(0));
    assert_eq!(power_exponent(1.4), Ok(0));
    assert_eq!(power_exponent(1.5), Ok(1));
    for e in -1074..1024 {
        let x = scale_pow2(1.0, e);
        assert_eq!(power_exponent(x), Ok(e));
    }
    assert_eq!(exact_scale(f64::from_bits(1), 1), Ok(f64::from_bits(2)));
    assert!(exact_scale(f64::from_bits(1), -1).is_err());
    assert!(exact_scale(f64::MAX, 1).is_err());
    assert_eq!(scale_pow2(0.75, -1074), f64::from_bits(1));
    assert_eq!(scale_pow2(0.5, -1074), 0.0);
}
#[test]
fn cross_products_retain_subnormals_and_refuse_concealed_range_loss() {
    assert_eq!(
        component_product(f64::from_bits(1), 1.0, 3, true),
        Ok(f64::from_bits(1))
    );
    assert!(component_product(f64::from_bits(1), 0.25, 3, true).is_err());
    assert!(component_product(f64::MAX, 2.0, 3, true).is_err());
    for a in [1.0 / 3.0, -1.23456789012345, 1e-100, 1e100] {
        for b in [0.375, 1.0 / 7.0, -1e-100, 1e100] {
            let p = component_product(a, b, 3, true).unwrap();
            assert!((p - a * b).abs() <= 2.0 * f64::EPSILON * (a * b).abs());
        }
    }
    assert_ne!(reconstruct(split(1.0 / 3.0).unwrap(), 2), 1.0 / 3.0);
}
#[test]
fn exact_scaling_canonical_transpose_and_conservative_bounds() {
    use optimizer_core::{LpSettings, Model};
    use optimizer_lp::{Engine, LinearProgram};
    let m = Model::from_json(include_bytes!("../../../examples/lp-model-v1.json")).unwrap();
    let p = LinearProgram::new(&m).unwrap();
    let e = Engine::new(&p, LpSettings::published(20, 4));
    let r = e
        .preconditioner()
        .row()
        .iter()
        .map(|&v| power_exponent(v).unwrap())
        .collect::<Vec<_>>();
    let c = e
        .preconditioner()
        .column()
        .iter()
        .map(|&v| power_exponent(v).unwrap())
        .collect::<Vec<_>>();
    let scaled = Engine::with_power2_scaling(&p, e.settings(), &r, &c).unwrap();
    assert!(Engine::with_power2_scaling(&p, e.settings(), &[], &c).is_err());
    for mode in [
        Mode::DefaultFp64,
        Mode::Power2Fp32,
        Mode::FactoredFp32,
        Mode::Components2Fp32,
        Mode::Components3Fp32,
    ] {
        let engine = if mode.power2() { &scaled } else { &e };
        let op = Operator::new(engine, mode).unwrap();
        assert_eq!(transpose(&p, &op.rows), op.columns);
        assert!(op.step <= engine.step());
        for bound in op.bounds {
            assert!(op.step * bound <= 0.9);
        }
        if mode.components() == 3 {
            assert_eq!(op.matrix_tail_max, 0.0);
        }
    }
}
#[test]
fn component_products_agree_with_independent_exact_rational_fixtures() {
    let data: serde_json::Value =
        serde_json::from_str(include_str!("fixtures/research-products.json")).unwrap();
    let value = |s: &serde_json::Value| {
        f64::from_bits(u64::from_str_radix(s.as_str().unwrap(), 16).unwrap())
    };
    let mut worst_ulp = 0.0_f64;
    let mut differing = 0;
    for row in data["products"].as_array().unwrap() {
        let a = value(&row["a"]);
        let b = value(&row["b"]);
        let expected = value(&row["nearest"]);
        let result = component_product(a, b, 3, true);
        if expected == 0.0 && a != 0.0 && b != 0.0 {
            assert!(result.is_err());
        } else {
            let found = result.unwrap();
            let ulp = (expected.next_up() - expected)
                .abs()
                .max((expected - expected.next_down()).abs());
            worst_ulp = worst_ulp.max((found - expected).abs() / ulp);
            differing += usize::from(found.to_bits() != expected.to_bits());
            assert!((found - expected).abs() <= 2.0 * ulp, "{row}");
        }
    }
    println!(
        "independent scalar fixture maximum ulps: {worst_ulp}; differing finite products: {differing}"
    );
}

#[test]
fn sparse_products_and_transpose_obey_independent_rational_error_bounds() {
    use optimizer_core::{LpSettings, Model};
    use optimizer_lp::{Engine, LinearProgram};
    let data: serde_json::Value =
        serde_json::from_str(include_str!("fixtures/research-sparse.json")).unwrap();
    let number = |s: &serde_json::Value| {
        f64::from_bits(u64::from_str_radix(s.as_str().unwrap(), 16).unwrap())
    };
    let mut worst = 0.0_f64;
    for case in data["cases"].as_array().unwrap() {
        let a: Vec<f64> = case["a"].as_array().unwrap().iter().map(number).collect();
        let x: Vec<f64> = case["x"].as_array().unwrap().iter().map(number).collect();
        let variables: Vec<_> = (0..a.len())
            .map(|i| {
                serde_json::json!({
                    "id":i,"domain":"continuous","lower":{"kind":"finite","value":-1.0},
                    "upper":{"kind":"finite","value":1.0}
                })
            })
            .collect();
        let terms: Vec<_> = a
            .iter()
            .enumerate()
            .map(|(i, a)| {
                serde_json::json!({
                    "variable_id":i,"coefficient":a
                })
            })
            .collect();
        let model = Model::from_json(
            &serde_json::to_vec(&serde_json::json!({
                "schema_version":1,"model_id":"independent-sparse-rational","variables":variables,
                "constraints":[{"id":0,"lower":{"kind":"finite","value":-1.0},
                    "upper":{"kind":"finite","value":1.0},"terms":terms}],
                "objective":{"sense":"minimize","offset":0.0,"terms":[]}
            }))
            .unwrap(),
        )
        .unwrap();
        let p = LinearProgram::new(&model).unwrap();
        let e =
            Engine::with_power2_scaling(&p, LpSettings::published(8, 4), &[0], &vec![0; a.len()])
                .unwrap();
        for mode in [
            Mode::DefaultFp64,
            Mode::Components2Fp64,
            Mode::Components2Fp32,
            Mode::Components3Fp64,
            Mode::Components3Fp32,
        ] {
            let op = Operator::new(&e, mode).unwrap();
            let expected = &case["expected"][usize::from(mode.components() != 2)];
            let actual = op.apply(&e, false, &x).unwrap()[0];
            let error = (actual - number(&expected["nearest"])).abs();
            let allowance = expected["absolute_allowance"].as_f64().unwrap();
            assert!(error <= allowance, "{mode:?}: {error} > {allowance}");
            worst = worst.max(error / allowance);
            let transposed = op.apply(&e, true, &[0.75]).unwrap();
            for (actual, expected) in transposed
                .iter()
                .zip(expected["transpose_nearest"].as_array().unwrap())
            {
                let target = number(expected);
                let ulp = (target.next_up() - target)
                    .abs()
                    .max((target - target.next_down()).abs());
                assert!((actual - target).abs() <= 2.0 * ulp);
            }
        }
    }
    println!("independent rational sparse error / allowance maximum: {worst}");
}

#[test]
fn adr0022_modes_round_trip_and_declare_their_schedules() {
    let strings = [
        ("intguard-fp64", Mode::IntguardFp64, 6, false, false),
        ("fused-fp64", Mode::FusedFp64, 2, true, false),
        ("doublefloat-fp32", Mode::DoublefloatFp32, 2, true, true),
        ("default-fp64", Mode::DefaultFp64, 6, false, false),
        ("components3-fp32", Mode::Components3Fp32, 6, false, false),
    ];
    for (text, mode, launches, fused, df) in strings {
        let json = serde_json::to_string(&mode).unwrap();
        assert_eq!(json, format!("\"{text}\""));
        assert_eq!(serde_json::from_str::<Mode>(&json).unwrap(), mode);
        assert_eq!(mode.launches_per_step(), launches);
        assert_eq!(mode.fused(), fused);
        assert_eq!(mode.doublefloat(), df);
        assert_eq!(mode.fused_kernels().is_some(), fused);
        assert_eq!(
            mode.v2(),
            matches!(
                mode,
                Mode::IntguardFp64 | Mode::FusedFp64 | Mode::DoublefloatFp32
            )
        );
        assert_eq!(
            mode.components(),
            if text.starts_with("components3") {
                3
            } else {
                0
            }
        );
    }
    assert!(serde_json::from_str::<Mode>("\"fused-fp32\"").is_err());
    assert_eq!(Mode::IntguardFp64.kernel(), "research_intguard64");
}

#[test]
fn fp32_pairs_split_exactly_and_refuse_lost_or_subnormal_coefficients() {
    use optimizer_core::{LpSettings, Model};
    use optimizer_lp::{Engine, LinearProgram};
    for x in [
        0.0,
        1.0 / 3.0,
        -1.23456789012345,
        1e30,
        1e-30,
        2.0_f64.next_down(),
    ] {
        let pair = Pair::split(x);
        assert_eq!(f64::from(pair.hi), f64::from(x as f32));
        // 48 significant bits: the pair error is below 2^-47 relative.
        assert!(
            (pair.value() - x).abs() <= x.abs() * 2.0_f64.powi(-47),
            "{x}"
        );
        assert!(pair.lo.abs() <= (pair.hi.abs() * f32::EPSILON) / 2.0 + f32::MIN_POSITIVE);
    }
    let a = Pair::split(1.0 / 3.0);
    let b = Pair::split(1.0 / 7.0);
    let p = a.times(b);
    assert!((p.value() - 1.0 / 21.0).abs() <= 2.0_f64.powi(-44) / 21.0);
    let s = p.plus(Pair::split(-1.0 / 21.0));
    assert!(s.value().abs() <= 2.0_f64.powi(-44) / 21.0);
    let m = Model::from_json(include_bytes!("../../../examples/lp-model-v1.json")).unwrap();
    let p = LinearProgram::new(&m).unwrap();
    let e = Engine::new(&p, LpSettings::published(20, 4));
    let op = Operator::new(&e, Mode::DoublefloatFp32).unwrap();
    assert_eq!(transpose(&p, &op.rows), op.columns);
    assert!(
        op.matrix_tail_max <= 2.0_f64.powi(-47) * op.rows.iter().fold(0.0, |m, v| v.abs().max(m))
    );
    for bound in op.bounds {
        assert!(op.step * bound <= 0.9);
    }
    let control = Operator::new(&e, Mode::DefaultFp64).unwrap();
    assert_eq!(op.bounds[0], control.bounds[0]);
    // The CPU pair oracle agrees with FP64 to the representation error on this model.
    let x: Vec<f64> = (0..p.column_count())
        .map(|j| 0.25 + j as f64 * 0.125)
        .collect();
    let fp64 = control.apply(&e, false, &x).unwrap();
    let df = op.apply(&e, false, &x).unwrap();
    for (a, b) in fp64.iter().zip(&df) {
        assert!((a - b).abs() <= 1e-12 * (1.0 + a.abs()), "{a} {b}");
    }
}

#[test]
fn doublefloat_sparse_products_obey_independent_rational_error_bounds() {
    use optimizer_core::{LpSettings, Model};
    use optimizer_lp::{Engine, LinearProgram};
    let data: serde_json::Value =
        serde_json::from_str(include_str!("fixtures/research-doublefloat.json")).unwrap();
    let number = |s: &serde_json::Value| {
        f64::from_bits(u64::from_str_radix(s.as_str().unwrap(), 16).unwrap())
    };
    let mut worst = 0.0_f64;
    for case in data["cases"].as_array().unwrap() {
        let a: Vec<f64> = case["a"].as_array().unwrap().iter().map(number).collect();
        let x: Vec<f64> = case["x"].as_array().unwrap().iter().map(number).collect();
        let variables: Vec<_> = (0..a.len())
            .map(|i| {
                serde_json::json!({
                    "id":i,"domain":"continuous","lower":{"kind":"finite","value":-1.0},
                    "upper":{"kind":"finite","value":1.0}
                })
            })
            .collect();
        let terms: Vec<_> = a
            .iter()
            .enumerate()
            .map(|(i, a)| serde_json::json!({"variable_id":i,"coefficient":a}))
            .collect();
        let model = Model::from_json(
            &serde_json::to_vec(&serde_json::json!({
                "schema_version":1,"model_id":"independent-doublefloat-rational","variables":variables,
                "constraints":[{"id":0,"lower":{"kind":"finite","value":-1.0},
                    "upper":{"kind":"finite","value":1.0},"terms":terms}],
                "objective":{"sense":"minimize","offset":0.0,"terms":[]}
            }))
            .unwrap(),
        )
        .unwrap();
        let p = LinearProgram::new(&model).unwrap();
        let e =
            Engine::with_power2_scaling(&p, LpSettings::published(8, 4), &[0], &vec![0; a.len()])
                .unwrap();
        let op = Operator::new(&e, Mode::DoublefloatFp32).unwrap();
        let expected = &case["expected"];
        let actual = op.apply(&e, false, &x).unwrap()[0];
        let error = (actual - number(&expected["nearest"])).abs();
        let allowance = expected["absolute_allowance"].as_f64().unwrap();
        assert!(error <= allowance, "{error} > {allowance}");
        worst = worst.max(error / allowance);
        let transposed = op.apply(&e, true, &[0.75]).unwrap();
        for ((actual, target), allowance) in transposed
            .iter()
            .zip(expected["transpose_nearest"].as_array().unwrap())
            .zip(expected["transpose_allowance"].as_array().unwrap())
        {
            assert!((actual - number(target)).abs() <= allowance.as_f64().unwrap());
        }
    }
    println!("independent rational double-float error / allowance maximum: {worst}");
}
