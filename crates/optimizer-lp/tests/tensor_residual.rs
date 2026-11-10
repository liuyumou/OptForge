//! Independent lifecycle and exact-dot counterexamples for ADR-0043.
#![cfg(feature = "precision-research")]
use optimizer_core::{CancellationToken, LpSettings, Model};
use optimizer_lp::{Engine, LinearProgram, tensor_residual::*};
fn model() -> Model {
    let b = |x| serde_json::json!({"kind":"finite","value":x});
    let variables = (0..32)
        .map(|i| serde_json::json!({"id":i,"domain":"continuous","lower":b(-2.),"upper":b(2.)}))
        .collect::<Vec<_>>();
    let rows=(0..32).map(|r|serde_json::json!({"id":r,"lower":b(-1.),"upper":b(1.),"terms":(0..32).map(|c|serde_json::json!({"variable_id":c,"coefficient":if r==c{4.}else{((r+c)%3+1) as f64/32.}})).collect::<Vec<_>>()})).collect::<Vec<_>>();
    Model::from_json(&serde_json::to_vec(&serde_json::json!({"schema_version":1,"model_id":"tensor-dense","variables":variables,"constraints":rows,"objective":{"sense":"minimize","offset":0.,"terms":(0..32).map(|i|serde_json::json!({"variable_id":i,"coefficient":1.})).collect::<Vec<_>>()}})).unwrap()).unwrap()
}
#[test]
fn exact_encoding_and_rounding_boundaries() {
    assert_eq!(encode(1., 1), Ok(1i64 << 55));
    assert_eq!(encode(-1., 1), Ok(-(1i64 << 55)));
    assert!(encode(f64::NAN, 1).is_err());
    assert_eq!(encode(f64::from_bits(1), 1), Ok(0));
    assert_eq!(block_exponent([f64::from_bits(1)]), Ok(-1073));
    assert_eq!(round_dot(1, -1074).unwrap().0.to_bits(), 1);
    assert!(round_dot(1, -1075).is_err());
    assert_eq!(round_dot(3, -1075).unwrap().0.to_bits(), 2);
    assert_eq!(round_dot((1i128 << 53) + 1, -53).unwrap().0, 1.);
    assert_eq!(
        round_dot((1i128 << 53) + 3, -53).unwrap().0.to_bits(),
        1f64.to_bits() + 2
    );
    assert_eq!(round_dot(-((1i128 << 53) + 1), -53).unwrap().0, -1.);
    assert!(round_dot(1, 1024).is_err());
}
#[test]
fn both_orientations_and_all_families_share_represented_dot() {
    let m = model();
    let p = LinearProgram::new(&m).unwrap();
    let e = Engine::new(&p, LpSettings::published(480, 200));
    let mut reference = None;
    for layout in [Layout::Int8, Layout::Fp16, Layout::Bf16, Layout::Simt] {
        let op = Operator::new(&e, Settings::new(Format::Fp64, Policy::Uniform), layout).unwrap();
        assert_eq!(op.dense_exponents.len(), 1);
        let g = op.generation(op.initial()).unwrap();
        assert!(!g.promotion().native);
        let mut outputs = vec![];
        for t in [false, true] {
            for sample in 0..9 {
                let v = (0..32)
                    .map(|i| ((i * 37 + sample * 13) % 127) as f64 / 17. - 3.)
                    .collect::<Vec<_>>();
                let a = op.product(&g, t, &v).unwrap();
                assert!(a.flags.iter().all(|x| *x == 0));
                outputs.push(a.output.iter().map(|x| x.to_bits()).collect::<Vec<_>>());
            }
        }
        if let Some(ref r) = reference {
            assert_eq!(&outputs, r);
        } else {
            reference = Some(outputs);
        }
    }
}
#[test]
fn session_binding_counter_refusal_and_whole_window_rollback() {
    let m = model();
    let p = LinearProgram::new(&m).unwrap();
    let mut e = Engine::new(&p, LpSettings::published(480, 200));
    let op = Operator::new(
        &e,
        Settings::new(Format::Fp64, Policy::Uniform),
        Layout::Int8,
    )
    .unwrap();
    e.restrict_step(op.step).unwrap();
    let other = Operator::new(
        &e,
        Settings::new(Format::Fp64, Policy::Uniform),
        Layout::Int8,
    )
    .unwrap();
    let g = op.generation(op.initial()).unwrap();
    assert!(other.product(&g, false, &[1.; 32]).is_err());
    let s = Session::new(&e, &op, None).unwrap();
    let c = s.checkpoint();
    let mut fresh = Session::new(&e, &op, None).unwrap();
    assert!(fresh.restore(&c).is_err());
    struct Invalid;
    impl Oracle for Invalid {
        fn window(
            &mut self,
            e: &Engine<'_>,
            o: &Operator,
            g: &Generation,
            s: &optimizer_lp::control::Fp64State,
            n: u64,
        ) -> Result<Window, String> {
            let mut w = HostOracle.window(e, o, g, s, n)?;
            w.counts.mma_instructions = u64::MAX;
            Ok(w)
        }
    }
    let bad = run(
        &e,
        &op,
        &mut Invalid,
        64,
        &CancellationToken::new(),
        None,
        |_, _| false,
    );
    assert_eq!(bad.core.stop, "device_failure");
    assert_eq!(bad.counts.mma_instructions, 0);
    assert_eq!(bad.core.iterations, 0);
    struct Fault(bool);
    impl Oracle for Fault {
        fn window(
            &mut self,
            e: &Engine<'_>,
            o: &Operator,
            g: &Generation,
            s: &optimizer_lp::control::Fp64State,
            n: u64,
        ) -> Result<Window, String> {
            if self.0 {
                self.0 = false;
                let mut w = HostOracle.window(e, o, g, s, 7)?;
                w.failure = Some("injected_guard".into());
                w.bad = vec![0];
                w.counts.predicated = n - 7;
                Ok(w)
            } else {
                HostOracle.window(e, o, g, s, n)
            }
        }
    }
    let recovered = run(
        &e,
        &op,
        &mut Fault(true),
        64,
        &CancellationToken::new(),
        None,
        |_, _| false,
    );
    assert_eq!(recovered.core.iterations, 64, "{recovered:?}");
    assert_eq!(recovered.core.work.replays, 32);
    assert_eq!(recovered.core.transitions.len(), 1);
    assert!(recovered.core.promotion.native);
    let normal = run(
        &e,
        &op,
        &mut HostOracle,
        64,
        &CancellationToken::new(),
        None,
        |_, _| true,
    );
    assert_eq!(normal.core.stop, "work_horizon");
    assert_eq!(normal.core.physical, 66);
    assert!(normal.counts.useful_windows > 0);
}

#[test]
fn tiny_values_are_corrected_and_residual_counters_refuse_before_aggregation() {
    let m = model();
    let p = LinearProgram::new(&m).unwrap();
    let e = Engine::new(&p, LpSettings::published(480, 200));
    let op = Operator::new(
        &e,
        Settings::new(Format::Fp64, Policy::Uniform),
        Layout::Int8,
    )
    .unwrap();
    let g = op.generation(op.initial()).unwrap();
    let v = (0..32)
        .map(|i| {
            if i % 3 == 0 {
                2.0816681711721685e-17
            } else {
                1.
            }
        })
        .collect::<Vec<_>>();
    for t in [false, true] {
        let product = op.product(&g, t, &v).unwrap();
        assert!(product.flags.iter().all(|f| *f == 0));
        assert!(product.counts.residual_products > 0);
        assert!(product.counts.nonzero_t + product.counts.nonzero_f < product.counts.low);
    }
    let invalid = Counts {
        low: 3,
        residual_products: 4,
        ..Counts::default()
    };
    assert!(!physical_counts_valid(&invalid, &op, 1));
}
