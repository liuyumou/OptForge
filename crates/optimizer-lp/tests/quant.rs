//! Quantization boundary, canonical operator and recovery contracts.
#![cfg(feature = "precision-research")]
use optimizer_core::{CancellationToken, LpSettings, Model};
use optimizer_lp::{Engine, LinearProgram, quant::*};
fn model(n: usize) -> Model {
    let b = |x| serde_json::json!({"kind":"finite","value":x});
    let vars = (0..n)
        .map(|i| serde_json::json!({"id":i,"domain":"continuous","lower":b(0.),"upper":b(2.)}))
        .collect::<Vec<_>>();
    let rows=(0..n).map(|i|serde_json::json!({"id":i,"lower":b(0.),"upper":b(1.),"terms":[{"variable_id":i,"coefficient":1.1}]})).collect::<Vec<_>>();
    Model::from_json(&serde_json::to_vec(&serde_json::json!({"schema_version":1,"model_id":"quant-contract","variables":vars,"constraints":rows,"objective":{"sense":"minimize","offset":0.,"terms":[{"variable_id":0,"coefficient":-1.}]}})).unwrap()).unwrap()
}
fn method() -> LpSettings {
    let mut s =
        LpSettings::from_json(include_bytes!("../../../examples/lp-settings-v1.json")).unwrap();
    s.iteration_limit = 480;
    s
}
#[test]
fn format_ties_range_signed_zero_and_no_double_rounding() {
    for f in [Format::Fp16, Format::E4m3, Format::E5m2] {
        assert!(f.encode(f64::INFINITY).is_err());
        assert!(f.encode(f64::NAN).is_err());
        assert!(f.encode(f64::from_bits(1)).is_err());
        let z = f.encode(-0.).unwrap();
        assert_eq!(f.decode(z).unwrap().to_bits(), (-0f64).to_bits());
        for i in 1..f.max_code() {
            let a = f.decode(i).unwrap();
            let b = f.decode(i + 1).unwrap();
            let mid = (a + b) * 0.5;
            assert_eq!(f.encode(mid).unwrap(), if i & 1 == 0 { i } else { i + 1 });
            assert_eq!(f.encode(mid.next_down()).unwrap(), i);
            assert_eq!(f.encode(mid.next_up()).unwrap(), i + 1);
        }
    }
}
#[test]
fn canonical_tiles_transpose_norm_and_generation() {
    let m = model(160);
    let p = LinearProgram::new(&m).unwrap();
    let e = Engine::new(&p, method());
    let mut norms = vec![];
    for f in [Format::Fp16, Format::E4m3, Format::E5m2, Format::Fp64] {
        let op = Operator::new(&e, Settings::new(f, Policy::Selective)).unwrap();
        norms.push(op.norm.to_bits());
        let mut s = Promotion::new(&op);
        let v = vec![0.25; 160];
        let a = op.product(&s, false, &v).unwrap();
        assert_eq!(a, op.product(&s, true, &v).unwrap());
        let mut copied = s.clone();
        copied.generation += 1;
        assert!(op.product(&copied, false, &v).is_err());
        if f != Format::Fp64 {
            assert!(s.promote(&op, &[0]));
            assert!(!s.native);
            assert!(s.promote(&op, &[1]));
            assert!(s.native);
        }
    }
    assert!(norms.iter().all(|n| *n == norms[0]));
    assert!(preparation_bytes(65537, 1, 0).is_err());
    assert!(preparation_bytes(1, 1, (1 << 23) + 1).is_err());
}
#[test]
fn checkpoint_binds_origin_and_preserves_physical_work() {
    let m = model(2);
    let p = LinearProgram::new(&m).unwrap();
    let e = Engine::new(&p, method());
    let op = Operator::new(&e, Settings::new(Format::Fp16, Policy::Uniform)).unwrap();
    let mut a = Session::new(&e, &op, None);
    let cp = a.checkpoint();
    a.controller.charge_extra(3).unwrap();
    a.promotion.promote(&op, &[0]);
    a.restore(&cp).unwrap();
    assert_eq!(a.controller.physical_iterations(), 3);
    assert_eq!(a.promotion, Promotion::new(&op));
    let mut b = Session::new(&e, &op, None);
    assert!(b.restore(&cp).is_err());
}
#[test]
fn charged_replay_and_native_failure_remain_explicit() {
    struct Fault {
        calls: u64,
    }
    impl Oracle for Fault {
        fn product(
            &mut self,
            o: &Operator,
            p: &Promotion,
            t: bool,
            v: &[f64],
        ) -> Result<Vec<f64>, String> {
            self.calls += 1;
            if self.calls == 1 {
                return Err("injected_guard".into());
            }
            o.product(p, t, v).map_err(str::to_string)
        }
    }
    let m = model(2);
    let p = LinearProgram::new(&m).unwrap();
    let mut e = Engine::new(&p, method());
    let op = Operator::new(&e, Settings::new(Format::Fp16, Policy::Selective)).unwrap();
    e.restrict_step(op.step).unwrap();
    let o = run(
        &e,
        &op,
        &mut Fault { calls: 0 },
        true,
        &CancellationToken::new(),
        None,
        |_, _| false,
    );
    assert_eq!(o.physical, o.work.proposals + o.work.audits);
    assert!(o.work.replays > 0);
    assert!(o.work.rejected <= o.work.proposals);
    assert!(o.promotion.native, "{o:?}");
    assert!(o.transitions.iter().any(|t| t.reason == "injected_guard"));
}
#[test]
fn cancellation_and_deadline_cannot_become_success() {
    let m = model(1);
    let p = LinearProgram::new(&m).unwrap();
    let e = Engine::new(&p, method());
    let op = Operator::new(&e, Settings::new(Format::Fp16, Policy::Uniform)).unwrap();
    let c = CancellationToken::new();
    c.cancel();
    let o = run(&e, &op, &mut HostOracle, false, &c, None, |_, _| true);
    assert_eq!(o.stop, "interrupted");
    let o = run(
        &e,
        &op,
        &mut HostOracle,
        false,
        &CancellationToken::new(),
        Some(std::time::Instant::now()),
        |_, _| true,
    );
    assert_eq!(o.stop, "time_limit");
}

#[test]
fn late_cancellation_preserves_terminal_device_failure_metadata() {
    struct Fault<'a>(&'a CancellationToken);
    impl Oracle for Fault<'_> {
        fn product(
            &mut self,
            _: &Operator,
            _: &Promotion,
            _: bool,
            _: &[f64],
        ) -> Result<Vec<f64>, String> {
            self.0.cancel();
            Err("device:injected".into())
        }
    }
    let m = model(1);
    let p = LinearProgram::new(&m).unwrap();
    let e = Engine::new(&p, method());
    let op = Operator::new(&e, Settings::new(Format::Fp64, Policy::Uniform)).unwrap();
    let c = CancellationToken::new();
    let out = run(&e, &op, &mut Fault(&c), true, &c, None, |_, _| true);
    assert_eq!(out.stop, "device_failure");
    assert_eq!(out.failure.as_deref(), Some("device:injected"));
    assert_eq!(out.work.proposals - out.work.rejected, out.iterations);
}

#[test]
fn native_weighted_updates_refuse_nonzero_underflow() {
    let mut doc = serde_json::to_value(model(1).document()).unwrap();
    let sub = f64::from_bits(1);
    doc["variables"][0]["lower"]["value"] = serde_json::json!(sub);
    doc["variables"][0]["upper"]["value"] = serde_json::json!(sub);
    doc["constraints"] = serde_json::json!([]);
    doc["objective"]["terms"] = serde_json::json!([]);
    let model = Model::from_json(&serde_json::to_vec(&doc).unwrap()).unwrap();
    let p = LinearProgram::new(&model).unwrap();
    let e = Engine::new(&p, method());
    let op = Operator::new(&e, Settings::new(Format::Fp64, Policy::Uniform)).unwrap();
    let out = run(
        &e,
        &op,
        &mut HostOracle,
        true,
        &CancellationToken::new(),
        None,
        |_, _| true,
    );
    assert_eq!(out.stop, "numerical_failure");
    assert_eq!(out.failure.as_deref(), Some("product_lost_nonzero"));
    assert_eq!(out.iterations, 0);
}

#[test]
fn zero_tiles_and_symbolic_scale_boundaries_are_explicit() {
    let mut doc = serde_json::to_value(model(1).document()).unwrap();
    doc["constraints"][0]["terms"] = serde_json::json!([]);
    let m = Model::from_json(&serde_json::to_vec(&doc).unwrap()).unwrap();
    let p = LinearProgram::new(&m).unwrap();
    let e = Engine::new(&p, method());
    for f in [Format::Fp16, Format::E4m3, Format::E5m2] {
        let op = Operator::new(&e, Settings::new(f, Policy::Uniform)).unwrap();
        assert!(op.tiles.is_empty());
        assert_eq!(op.norm, 0.);
        assert_eq!(
            op.product(&Promotion::new(&op), false, &[1.]).unwrap(),
            vec![0.]
        );
        assert!(f.encode(f.decode(f.max_code()).unwrap().next_up()).is_err());
        for code in [1, f.max_code()] {
            for exponent in [-1000, -200, 0, 200, 900] {
                let x = f.decode(code).unwrap();
                let scaled = optimizer_lp::research::scale_pow2(x, exponent);
                if scaled.is_finite() && scaled != 0. {
                    let restored = optimizer_lp::research::scale_pow2(scaled, -exponent);
                    if restored.to_bits() == x.to_bits() {
                        assert_eq!(f.encode(restored).unwrap(), code);
                    }
                }
            }
        }
    }
}
