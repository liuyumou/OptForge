//! Independent numerical admission and bounded-controller contracts.
#![cfg(feature = "precision-research")]
use optimizer_core::Model;
use optimizer_lp::{
    LinearProgram,
    refine::{EqualityBox, Interval, contracts_progress},
};
fn contains(got: Interval, want: &serde_json::Value) {
    let lo = want["lower"].as_f64().unwrap();
    let hi = want["upper"].as_f64().unwrap();
    assert!(
        got.lower <= lo && got.upper >= hi,
        "{got:?} does not contain {want}"
    );
    assert!(got.rounded >= got.lower && got.rounded <= got.upper);
}
#[test]
fn independent_rational_maps_and_merit() {
    let fixture: serde_json::Value = serde_json::from_str(include_str!(
        "../../../tests/regression/lp-refine-oracle.json"
    ))
    .unwrap();
    for case in fixture["cases"].as_array().unwrap() {
        let model = Model::from_json(&serde_json::to_vec(&case["model"]).unwrap()).unwrap();
        let lp = LinearProgram::new(&model).unwrap();
        let eq = EqualityBox::new(&lp).unwrap();
        let vec = |name: &str| {
            case[name]
                .as_array()
                .unwrap()
                .iter()
                .map(|x| x.as_f64().unwrap())
                .collect::<Vec<_>>()
        };
        let (v, y) = (vec("v"), vec("y"));
        let r = eq.residuals(&v, &y).unwrap();
        for (name, values) in [("primal", r.primal), ("dual", r.dual)] {
            for (got, want) in values
                .into_iter()
                .zip(case["expected"][name].as_array().unwrap())
            {
                contains(got, want);
            }
        }
        contains(eq.merit(&v, &y).unwrap(), &case["expected"]["merit"]);
        let c = eq.correction(&v, &y).unwrap();
        assert_eq!(c.rhs.len(), lp.row_count());
        assert_eq!(c.objective.len(), v.len());
        assert_eq!(c.lower.len(), v.len());
        assert_eq!(c.upper.len(), v.len());
    }
}
#[test]
fn interval_extremes_preserve_uncertainty() {
    let p = Interval::point;
    let sub = f64::from_bits(1);
    let x = p(sub).unwrap().times(p(0.5).unwrap()).unwrap();
    assert!(x.lower <= 0.0 && x.upper >= sub);
    let x = p(1.0)
        .unwrap()
        .plus(p(f64::EPSILON / 2.0).unwrap())
        .unwrap();
    assert_eq!(x.rounded, 1.0);
    assert!(x.upper > 1.0);
    assert!(p(f64::MAX).unwrap().times(p(2.0).unwrap()).is_err());
    assert!(p(1.0).unwrap().divide_positive(p(0.0).unwrap()).is_err());
    assert!(!contracts_progress(p(0.0).unwrap(), p(0.0).unwrap()));
    assert!(!contracts_progress(
        Interval {
            lower: 0.0,
            upper: 1.0,
            rounded: 0.5
        },
        p(0.0).unwrap()
    ));
    assert!(contracts_progress(p(1.0).unwrap(), p(0.5).unwrap()));
}
fn tiny() -> Model {
    Model::from_json(br#"{"schema_version":1,"model_id":"refine-min-minus-x","variables":[{"id":0,"domain":"continuous","lower":{"kind":"finite","value":0.0},"upper":{"kind":"finite","value":1.0}}],"constraints":[{"id":0,"lower":{"kind":"finite","value":0.0},"upper":{"kind":"finite","value":1.0},"terms":[{"variable_id":0,"coefficient":1.0}]}],"objective":{"sense":"minimize","offset":7.0,"terms":[{"variable_id":0,"coefficient":-1.0}]}}"#).unwrap()
}
fn method() -> optimizer_core::LpSettings {
    optimizer_core::LpSettings::from_json(include_bytes!("../../../examples/lp-settings-v1.json"))
        .unwrap()
}
#[test]
fn bounded_controller_native_low_and_anchored() {
    use optimizer_lp::refine::{HostOracle, ProductWidth, run};
    let model = tiny();
    let p = LinearProgram::new(&model).unwrap();
    let eq = EqualityBox::new(&p).unwrap();
    for (width, anchored) in [
        (ProductWidth::F64, false),
        (ProductWidth::F32, false),
        (ProductWidth::F32, true),
    ] {
        let mut settings = method();
        settings.iteration_limit = 50000;
        let result = run(
            &eq,
            settings,
            width,
            anchored,
            1e-9,
            std::time::Instant::now() + std::time::Duration::from_secs(10),
            &optimizer_core::CancellationToken::new(),
            &mut HostOracle,
            |v, y| {
                let Some(bound) = optimizer_lp::certify(&p, y).ok().map(|x| x.bound) else {
                    return false;
                };
                let feasible = v[0] >= 0.0 && v[0] <= 1.0;
                feasible
                    && optimizer_lp::certify::assess_gap(
                        &p,
                        &v[..1],
                        bound,
                        optimizer_core::Tolerances {
                            absolute: 1e-9,
                            relative: 1e-9,
                            integrality: 1e-9,
                        },
                    )
                    .is_some_and(|g| g.closed)
            },
        );
        assert_eq!(result.status, "accepted", "{result:?}");
        assert!(result.work.physical_updates <= 50000);
        assert!(result.work.committed_updates <= result.work.physical_updates);
        assert!(result.work.promotions <= 1);
        for e in &result.trace {
            if e.decision == "contracted" {
                assert!(optimizer_lp::refine::contracts_progress(
                    e.anchor_merit,
                    e.candidate_merit.unwrap()
                ));
            }
        }
    }
}
#[test]
fn cancellation_and_bad_oracle_cannot_publish_success() {
    use optimizer_lp::refine::{HostOracle, InnerOperator, ProductOracle, ProductWidth, run};
    let model = tiny();
    let p = LinearProgram::new(&model).unwrap();
    let eq = EqualityBox::new(&p).unwrap();
    let cancel = optimizer_core::CancellationToken::new();
    cancel.cancel();
    let r = run(
        &eq,
        method(),
        ProductWidth::F32,
        true,
        1e-9,
        std::time::Instant::now() + std::time::Duration::from_secs(1),
        &cancel,
        &mut HostOracle,
        |_, _| false,
    );
    assert_eq!(r.status, "interrupted");
    assert_eq!(r.work.physical_updates, 0);
    struct Bad;
    impl ProductOracle for Bad {
        fn bind(&mut self, _: &InnerOperator) -> Result<(), String> {
            Ok(())
        }
        fn apply(
            &mut self,
            op: &InnerOperator,
            t: bool,
            _: &[f64],
            _: ProductWidth,
        ) -> Result<Vec<f64>, String> {
            Ok(vec![1e10; if t { op.columns() } else { op.rows() }])
        }
    }
    let r = run(
        &eq,
        method(),
        ProductWidth::F32,
        true,
        1e-9,
        std::time::Instant::now() + std::time::Duration::from_secs(1),
        &optimizer_core::CancellationToken::new(),
        &mut Bad,
        |_, _| false,
    );
    assert_eq!(r.status, "unsupported");
    assert_eq!(r.work.promotions, 1);
    assert_eq!(r.failure.as_deref(), Some("operator_error_budget"));
    assert_eq!(r.work.committed_updates, 0);
    assert_eq!(r.work.refreshes, 16);
    assert_eq!(r.work.anchor_products, 32);
    assert_eq!(r.work.physical_updates, 18);
}

#[test]
fn range_memory_and_matrix_rebind_fail_before_use() {
    use optimizer_lp::refine::{InnerOperator, correction_program, preparation_bytes};
    assert!(preparation_bytes(usize::MAX, 1, 1).is_err());
    assert!(preparation_bytes(65536, 65536, 1 << 23).is_err());
    let model = tiny();
    let p = LinearProgram::new(&model).unwrap();
    let eq = EqualityBox::new(&p).unwrap();
    assert!(eq.residuals(&[0.0], &[0.0]).is_err());
    assert!(eq.merit(&[f64::NAN, 0.0], &[0.0]).is_err());
    let (v, y) = eq.initial();
    let c = eq.correction(&v, &y).unwrap();
    let base = correction_program(&eq, &c).unwrap();
    let prepared = optimizer_lp::refine::PreparedCorrection::new(&base, method());
    assert!(prepared.bind(&p).is_err());
    assert!(InnerOperator::new(&optimizer_lp::Engine::new(&base, method()), usize::MAX).is_err());
    let mut malformed = c;
    malformed.rhs.clear();
    assert!(correction_program(&eq, &malformed).is_err());
}
#[test]
fn checkpoint_roundtrip_keeps_physical_work_deadline_and_sticky_promotion() {
    use optimizer_lp::{control::Fp64Controller, refine::*};
    let model = tiny();
    let p = LinearProgram::new(&model).unwrap();
    let eq = EqualityBox::new(&p).unwrap();
    let (v, y) = eq.initial();
    let c = eq.correction(&v, &y).unwrap();
    let cp = correction_program(&eq, &c).unwrap();
    let engine = optimizer_lp::Engine::new(&cp, method());
    let op = InnerOperator::new(&engine, 1).unwrap();
    let mut controller = Fp64Controller::new(&engine);
    let deadline = std::time::Instant::now();
    controller.set_deadline(Some(deadline));
    let mut a = AnchorState {
        generation: op.generation(),
        base_x: vec![0.0; 2],
        base_y: vec![0.0],
        delta_x: vec![0.0; 2],
        delta_y: vec![0.0],
        restart_x: vec![0.0; 2],
        restart_y: vec![0.0],
        primal_products: vec![Interval::point(0.0).unwrap()],
        dual_products: vec![Interval::point(0.0).unwrap(); 2],
        inner: controller.state().clone(),
        correction: c,
        assessment_position: 0,
        errors: ErrorBudget::default(),
        rebase_error: 0.0,
    };
    let mut out = Outcome {
        v,
        y,
        work: Work::default(),
        trace: vec![],
        status: "iteration_limit".into(),
        failure: None,
        width: ProductWidth::F32,
    };
    let snapshot = checkpoint(&controller, &a, &out);
    let original = a.clone();
    controller.charge_extra(4).unwrap();
    out.work.physical_updates = 4;
    out.work.promotions = 1;
    out.width = ProductWidth::F64;
    a.delta_x[0] = 99.0;
    restore(&mut controller, &mut a, &mut out, &snapshot, &op).unwrap();
    assert_eq!(a, original);
    assert_eq!(controller.physical_iterations(), 4);
    assert!(controller.expired_at(deadline));
    assert_eq!(out.work.physical_updates, 4);
    assert_eq!(out.width, ProductWidth::F64);
    a.generation.push('x');
    assert!(a.validate_generation(&op).is_err());
    let another = optimizer_lp::Engine::new(&cp, method());
    let mut other = Fp64Controller::new(&another);
    assert!(restore(&mut other, &mut a, &mut out, &snapshot, &op).is_err());
}

#[test]
fn subnormal_steps_cannot_inherit_the_nominal_point_nine_margin() {
    use optimizer_lp::{refine::safe_steps, research::scale_pow2};
    let step = 0.875 * scale_pow2(1.0, -500);
    let weight = 1.5 * scale_pow2(1.0, 574);
    let norm = scale_pow2(1.0, 500);
    assert!(step < 0.9 / norm);
    assert_eq!((step / weight).to_bits(), 1);
    // Exactly: RN(tau)=2^-1074, sigma=(21/16)*2^74, norm=2^500.
    // Their exact tau*sigma*norm^2 is 21/16, which is greater than one.
    assert_eq!(step * weight, 1.3125 * scale_pow2(1.0, 74));
    assert_eq!(
        safe_steps(step, weight, norm),
        Err("rounded_step_product_guard")
    );
    assert!(safe_steps(0.8, 1.0, 1.0).is_ok());
    assert!(safe_steps(1.0, 0.0, 1.0).is_err());
}
