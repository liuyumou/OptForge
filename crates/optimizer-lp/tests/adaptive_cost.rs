//! SPEC-0017: differential against the pre-repair host implementations.
use optimizer_core::LpAdaptiveRung;
use optimizer_core::{LpAdaptiveRung as R, LpAdaptiveSettings, LpSettings, Model};
use optimizer_lp::{
    Engine, LinearProgram,
    adaptive::{PreparedAdaptive, audit, proposal},
    control::{Fp64Controller, Fp64State},
    precision::{PrecisionOperator, narrow, step},
};
use std::sync::Arc;
fn policy() -> LpAdaptiveSettings {
    LpAdaptiveSettings::from_json(include_bytes!(
        "../../../examples/lp-adaptive-demotion-v1.json"
    ))
    .unwrap()
}
fn model(coefficient: f64) -> Model {
    let mut value: serde_json::Value =
        serde_json::from_slice(include_bytes!("../../../examples/lp-model-v1.json")).unwrap();
    value["constraints"][0]["terms"][0]["coefficient"] = coefficient.into();
    value["constraints"][0]["terms"][1]["coefficient"] = coefficient.into();
    Model::from_json(&serde_json::to_vec(&value).unwrap()).unwrap()
}
fn bits(v: &[f64]) -> Vec<u64> {
    v.iter().map(|v| v.to_bits()).collect()
}
fn same_operator(a: &PrecisionOperator, b: &PrecisionOperator) {
    assert_eq!(bits(&a.rows), bits(&b.rows));
    assert_eq!(bits(&a.columns), bits(&b.columns));
    assert_eq!(bits(&a.bounds), bits(&b.bounds));
    assert_eq!(a.step.to_bits(), b.step.to_bits());
    assert_eq!(a.max_error.to_bits(), b.max_error.to_bits());
    assert_eq!(a.subnormals, b.subnormals);
}
#[test]
fn every_ladder_matches_independent_preparation_and_common_step() {
    for coefficient in [0.0, 1.00000003, 2_f64.powi(-149), 2_f64.powi(-150), 1e40] {
        let p = LinearProgram::new(&model(coefficient)).unwrap();
        let mut method = LpSettings::published(200, 20);
        method.preconditioner.ruiz_passes = 0;
        method.preconditioner.pock_chambolle_alpha = 0.0;
        for mask in 0..16 {
            let mut s = policy();
            s.ladder = [
                R::WorkingFp32,
                R::AccumulationFp32,
                R::ProductsFp32,
                R::StorageFp32,
            ]
            .into_iter()
            .enumerate()
            .filter_map(|(i, r)| (mask & (1 << i) != 0).then_some(r))
            .chain([R::Fp64])
            .collect();
            s.validate().unwrap();
            let mut e = Engine::new(&p, method);
            let legacy: Vec<_> = s
                .ladder
                .iter()
                .map(|r| PrecisionOperator::new(&e, &r.precision()))
                .collect();
            let common = legacy
                .iter()
                .filter_map(|v| v.as_ref().ok().map(|v| v.step))
                .fold(e.step(), f64::min);
            let session = optimizer_core::lp_cost::Session::begin().unwrap();
            let prepared = PreparedAdaptive::new(&mut e, &s);
            let profile = session.finish();
            let calls: u64 = profile
                .scopes
                .iter()
                .filter(|v| v.path.last().unwrap() == "precision_operator_preparation")
                .map(|v| v.calls)
                .sum();
            assert_eq!(calls, if mask == 0 { 1 } else { 2 });
            assert_eq!(e.step().to_bits(), common.to_bits());
            for (a, b) in prepared.operators.iter().zip(&legacy) {
                match (a, b) {
                    (Ok(a), Ok(b)) => same_operator(a, b),
                    (Err(a), Err(b)) => assert_eq!(a, b),
                    _ => panic!("preparation changed"),
                }
            }
            for pair in prepared.operators[..prepared.operators.len() - 1].windows(2) {
                if let (Ok(a), Ok(b)) = (&pair[0], &pair[1]) {
                    assert!(Arc::ptr_eq(a, b));
                }
            }
            if mask != 0 {
                match coefficient {
                    v if v == 2_f64.powi(-149) => {
                        assert!(prepared.operators[0].as_ref().unwrap().subnormals > 0)
                    }
                    v if v == 2_f64.powi(-150) => assert_eq!(
                        prepared.operators[0].as_ref().err(),
                        Some(&"conversion_lost_nonzero")
                    ),
                    1e40 => assert_eq!(
                        prepared.operators[0].as_ref().err(),
                        Some(&"conversion_nonfinite")
                    ),
                    _ => {}
                }
            }
        }
    }
}
#[test]
fn streamed_audits_match_legacy_bits_boundaries_nonfinite_and_shapes() {
    let p = LinearProgram::new(&model(3.7)).unwrap();
    let e = Engine::new(&p, LpSettings::published(200, 20));
    let mut pre = Fp64Controller::new(&e).state().clone();
    let mut s = policy();
    for value in [
        -0.0,
        0.0,
        1.0,
        -1.0,
        1e-300,
        1e300,
        f64::INFINITY,
        f64::NEG_INFINITY,
        f64::NAN,
    ] {
        for margin in [0.25, 1.0] {
            for absolute in [0.0, 1e-7, 1.0] {
                s.primal_absolute = absolute;
                s.dual_absolute = absolute;
                pre.primal.fill(value);
                pre.dual.fill(value);
                let low_x = vec![value.next_up(), value];
                let low_y = vec![value];
                let ref_x = vec![value, value.next_down()];
                let ref_y = vec![value.next_up()];
                let a = audit(&e, &s, &pre, (&low_x, &low_y), (&ref_x, &ref_y), margin);
                let b = legacy_audit(&e, &s, &pre, (&low_x, &low_y), (&ref_x, &ref_y), margin);
                assert_eq!((a.0, a.1.to_bits()), (b.0, b.1.to_bits()));
            }
        }
    }
    // All length combinations preserve old zip truncation and partial maxima.
    for before in 0..=4 {
        for low in 0..=4 {
            for reference in 0..=4 {
                pre.primal = vec![1.0; before];
                pre.dual = vec![2.0; reference];
                let lx = vec![3.0; low];
                let ly = vec![4.0; before];
                let hx = vec![5.0; reference];
                let hy = vec![6.0; low];
                let a = audit(&e, &s, &pre, (&lx, &ly), (&hx, &hy), 1.0);
                let b = legacy_audit(&e, &s, &pre, (&lx, &ly), (&hx, &hy), 1.0);
                assert_eq!((a.0, a.1.to_bits()), (b.0, b.1.to_bits()));
            }
        }
    }
    // Exact allowance boundary in original units, and the adjacent binary64 value.
    let unit = LinearProgram::new(&model(1.0)).unwrap();
    let mut method = LpSettings::published(20, 4);
    method.preconditioner.ruiz_passes = 0;
    method.preconditioner.pock_chambolle_alpha = 0.0;
    let e = Engine::new(&unit, method);
    let pre = Fp64Controller::new(&e).state().clone();
    s.relative = 0.0;
    s.primal_absolute = 1.0;
    s.dual_absolute = 1.0;
    for (delta, expected) in [(1.0, true), (1_f64.next_up(), false)] {
        let actual = audit(
            &e,
            &s,
            &pre,
            (&[delta, 0.0], &[0.0]),
            (&[0.0, 0.0], &[0.0]),
            1.0,
        );
        assert_eq!(actual.0, expected);
    }
}
#[test]
fn borrowed_and_narrowed_probes_match_original_without_mutating_state() {
    let p = LinearProgram::new(&model(1.00000003)).unwrap();
    let e = Engine::new(&p, LpSettings::published(200, 20));
    for rung in policy().ladder {
        let op = PrecisionOperator::new(&e, &rung.precision()).unwrap();
        for value in [
            -0.0,
            0.25,
            1.00000003,
            2_f64.powi(-150),
            1e40,
            f64::INFINITY,
            f64::NAN,
        ] {
            let mut s = Fp64Controller::new(&e).state().clone();
            s.primal.fill(value);
            s.dual.fill(value);
            s.anchor_primal.fill(value);
            s.anchor_dual.fill(value);
            s.since_restart = 3;
            let before = [
                bits(&s.primal),
                bits(&s.dual),
                bits(&s.anchor_primal),
                bits(&s.anchor_dual),
            ];
            let session = optimizer_core::lp_cost::Session::begin().unwrap();
            let a = proposal(&e, &s, &op, rung);
            let profile = session.finish();
            let b = legacy_proposal(&e, &s, &op, rung);
            match (a, b) {
                (Ok((ax, ay)), Ok((bx, by))) => {
                    assert_eq!(bits(&ax), bits(&bx));
                    assert_eq!(bits(&ay), bits(&by));
                }
                (Err(a), Err(b)) => assert_eq!(a, b),
                _ => panic!("probe changed"),
            }
            assert_eq!(
                before,
                [
                    bits(&s.primal),
                    bits(&s.dual),
                    bits(&s.anchor_primal),
                    bits(&s.anchor_dual)
                ]
            );
            let copied = profile
                .counters
                .get("probe_state_copied_elements")
                .copied()
                .unwrap_or(0);
            assert_eq!(copied, if rung == R::WorkingFp32 { 6 } else { 0 });
        }
    }
}

// Frozen pre-repair implementations from 5b9a9d0, deliberately independent.
fn legacy_proposal(
    engine: &Engine<'_>,
    state: &Fp64State,
    op: &PrecisionOperator,
    rung: LpAdaptiveRung,
) -> Result<(Vec<f64>, Vec<f64>), &'static str> {
    let _component_scope = optimizer_core::lp_cost::scope("demotion_cpu_mirror");
    let mut saved = state.clone();
    if rung == LpAdaptiveRung::WorkingFp32 {
        for v in saved
            .primal
            .iter_mut()
            .chain(&mut saved.dual)
            .chain(&mut saved.anchor_primal)
            .chain(&mut saved.anchor_dual)
        {
            *v = narrow(*v)?;
        }
    }
    let p = rung.precision();
    let (mut x, mut y) = step(
        engine,
        &saved,
        &op.rows,
        &op.columns,
        p.products,
        p.accumulation,
    )?;
    if rung == LpAdaptiveRung::WorkingFp32 {
        for v in x.iter_mut().chain(&mut y) {
            *v = narrow(*v)?;
        }
    }
    Ok((x, y))
}
fn legacy_audit(
    engine: &Engine<'_>,
    settings: &LpAdaptiveSettings,
    pre: &Fp64State,
    low: (&[f64], &[f64]),
    reference: (&[f64], &[f64]),
    margin: f64,
) -> (bool, f64) {
    let _component_scope = optimizer_core::lp_cost::scope("audit_comparison");
    let pre_x = engine.unscale_primal(&pre.primal);
    let pre_y = engine.unscale_dual(&pre.dual);
    let low_x = engine.unscale_primal(low.0);
    let low_y = engine.unscale_dual(low.1);
    let ref_x = engine.unscale_primal(reference.0);
    let ref_y = engine.unscale_dual(reference.1);
    let mut pass = true;
    let mut maximum: f64 = 0.0;
    for (before, lo, hi, absolute) in [
        (&pre_x, &low_x, &ref_x, settings.primal_absolute),
        (&pre_y, &low_y, &ref_y, settings.dual_absolute),
    ] {
        if before.len() != lo.len() || lo.len() != hi.len() {
            return (false, maximum);
        }
        for ((&b, &l), &h) in before.iter().zip(lo).zip(hi) {
            let error = (l - h).abs();
            let allowance = margin * (absolute + settings.relative * b.abs().max(h.abs()));
            if error.is_finite() {
                maximum = maximum.max(error);
            }
            pass &= b.is_finite()
                && l.is_finite()
                && h.is_finite()
                && error.is_finite()
                && allowance.is_finite()
                && error <= allowance;
        }
    }
    (pass, maximum)
}
