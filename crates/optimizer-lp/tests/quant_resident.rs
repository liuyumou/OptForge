//! Independent lifecycle counterexamples for ADR-0041 resident windows.
#![cfg(feature = "precision-research")]
use optimizer_core::{CancellationToken, LpSettings, Model};
use optimizer_lp::{Engine, LinearProgram, quant_resident::*};
fn model() -> Model {
    Model::from_json(&serde_json::to_vec(&serde_json::json!({"schema_version":1,"model_id":"resident-equality","variables":[{"id":0,"domain":"continuous","lower":{"kind":"finite","value":0.0},"upper":{"kind":"finite","value":2.0}}],"constraints":[{"id":0,"lower":{"kind":"finite","value":0.125},"upper":{"kind":"finite","value":0.125},"terms":[{"variable_id":0,"coefficient":1.0}]}],"objective":{"sense":"minimize","offset":0.0,"terms":[]}})).unwrap()).unwrap()
}
fn method() -> LpSettings {
    let mut m =
        LpSettings::from_json(include_bytes!("../../../examples/lp-settings-v1.json")).unwrap();
    m.iteration_limit = 480;
    m
}
#[test]
fn useful_windows_force_the_horizon_after_early_certification() {
    let m = model();
    let p = LinearProgram::new(&m).unwrap();
    for f in [Format::Fp16, Format::E4m3, Format::E5m2] {
        let mut e = Engine::new(&p, method());
        let op = Operator::new(&e, Settings::new(f, Policy::Selective), Layout::Segmented).unwrap();
        e.restrict_step(op.step).unwrap();
        let o = run(
            &e,
            &op,
            &mut HostOracle,
            64,
            &CancellationToken::new(),
            None,
            |_, _| true,
        );
        assert_eq!(o.core.stop, "work_horizon");
        assert_eq!(o.core.iterations, 64);
        assert_eq!(o.core.physical, 66);
        assert!(o.counts.useful_windows > 0);
        assert_eq!(o.core.work.proposals + o.core.work.audits, o.core.physical);
    }
}
#[test]
fn failure_at_each_window_position_restores_and_charges_all_prefix_work() {
    struct Fault {
        position: u64,
        first: bool,
    }
    impl Oracle for Fault {
        fn window(
            &mut self,
            e: &Engine<'_>,
            op: &Operator,
            g: &Generation,
            s: &optimizer_lp::control::Fp64State,
            len: u64,
        ) -> Result<Window, String> {
            if self.first {
                self.first = false;
                let mut a = HostOracle.window(e, op, g, s, self.position)?;
                a.failure = Some("injected_guard".into());
                a.bad = (0..op.tiles.len()).collect();
                a.counts.predicated = len - self.position;
                Ok(a)
            } else {
                HostOracle.window(e, op, g, s, len)
            }
        }
    }
    let m = model();
    let p = LinearProgram::new(&m).unwrap();
    let mut e = Engine::new(&p, method());
    let native = Operator::new(
        &e,
        Settings::new(Format::Fp64, Policy::Uniform),
        Layout::Segmented,
    )
    .unwrap();
    e.restrict_step(native.step).unwrap();
    let reference = run(
        &e,
        &native,
        &mut HostOracle,
        64,
        &CancellationToken::new(),
        None,
        |_, _| false,
    );
    for position in 1..=32 {
        let op = Operator::new(
            &e,
            Settings::new(Format::Fp16, Policy::Uniform),
            Layout::Segmented,
        )
        .unwrap();
        let o = run(
            &e,
            &op,
            &mut Fault {
                position,
                first: true,
            },
            64,
            &CancellationToken::new(),
            None,
            |_, _| false,
        );
        assert_eq!(o.core.scaled_primal, reference.core.scaled_primal);
        assert_eq!(o.core.scaled_dual, reference.core.scaled_dual);
        assert_eq!(o.core.physical, 66 + position);
        assert_eq!(o.core.work.rejected, position);
        assert_eq!(o.core.work.replays, 32);
        assert!(o.core.promotion.native);
        assert_eq!(o.core.transitions.len(), 1);
    }
}
#[test]
fn generation_and_origin_must_match_and_resource_counters_never_restore() {
    let m = model();
    let p = LinearProgram::new(&m).unwrap();
    let e = Engine::new(&p, method());
    let op = Operator::new(
        &e,
        Settings::new(Format::Fp16, Policy::Selective),
        Layout::Segmented,
    )
    .unwrap();
    let other = Operator::new(
        &e,
        Settings::new(Format::Fp16, Policy::Selective),
        Layout::Segmented,
    )
    .unwrap();
    let g = op.generation(Promotion::new(&op)).unwrap();
    assert!(other.product(&g, false, &[0.1]).is_err());
    let mut wrong = Promotion::new(&op);
    wrong.generation = 1;
    assert!(op.generation(wrong).is_err());
    let mut a = Session::new(&e, &op, None).unwrap();
    let cp = a.checkpoint();
    a.controller.charge_extra(7).unwrap();
    a.restore(&cp).unwrap();
    assert_eq!(a.controller.physical_iterations(), 7);
    let mut b = Session::new(&e, &op, None).unwrap();
    assert!(b.restore(&cp).is_err());
}
#[test]
fn cancellation_deadline_and_unknown_device_work_keep_their_status() {
    struct Broken;
    impl Oracle for Broken {
        fn window(
            &mut self,
            _: &Engine<'_>,
            _: &Operator,
            _: &Generation,
            _: &optimizer_lp::control::Fp64State,
            _: u64,
        ) -> Result<Window, String> {
            Err("device:injected_poison".into())
        }
    }
    let m = model();
    let p = LinearProgram::new(&m).unwrap();
    let mut e = Engine::new(&p, method());
    let op = Operator::new(
        &e,
        Settings::new(Format::Fp64, Policy::Uniform),
        Layout::Segmented,
    )
    .unwrap();
    e.restrict_step(op.step).unwrap();
    let token = CancellationToken::new();
    token.cancel();
    let a = run(&e, &op, &mut HostOracle, 64, &token, None, |_, _| false);
    assert_eq!(a.core.stop, "interrupted");
    assert_eq!(a.core.physical, 0);
    let b = run(
        &e,
        &op,
        &mut HostOracle,
        64,
        &CancellationToken::new(),
        Some(std::time::Instant::now()),
        |_, _| false,
    );
    assert_eq!(b.core.stop, "time_limit");
    let c = run(
        &e,
        &op,
        &mut Broken,
        64,
        &CancellationToken::new(),
        None,
        |_, _| false,
    );
    assert_eq!(c.core.stop, "device_failure");
    assert_eq!(c.core.physical, 32);
    assert_eq!(c.counts.uncertain, 32);
    assert_eq!(c.core.iterations, 0);
}
#[test]
fn zero_subnormal_operand_range_and_native_operands_are_explicit() {
    let m = model();
    let p = LinearProgram::new(&m).unwrap();
    let e = Engine::new(&p, method());
    let op = Operator::new(
        &e,
        Settings::new(Format::E4m3, Policy::Uniform),
        Layout::Segmented,
    )
    .unwrap();
    let low = op.generation(Promotion::new(&op)).unwrap();
    let a = op.product(&low, false, &[-0.]).unwrap();
    assert_eq!(a.flags, [0]);
    let b = op.product(&low, false, &[f64::from_bits(1)]).unwrap();
    assert_eq!(b.flags[0] & 4, 4);
    let mut promotion = Promotion::new(&op);
    promotion.promote(&op, &[0]);
    let high = op.generation(promotion).unwrap();
    let c = op.product(&high, false, &[2f64.powi(-140)]).unwrap();
    assert_eq!(c.flags, [0]);
    assert_eq!(c.output[0], 2f64.powi(-140));
    assert_eq!(c.counts.low, 0);
    assert!(op.product(&high, false, &[f64::INFINITY]).is_err());
    assert!(optimizer_lp::quant::preparation_bytes(65537, 1, 0).is_err());
}

#[test]
fn invalid_device_windows_are_named_and_conservatively_charged() {
    struct Corrupt(u8);
    impl Oracle for Corrupt {
        fn window(
            &mut self,
            e: &Engine<'_>,
            op: &Operator,
            g: &Generation,
            s: &optimizer_lp::control::Fp64State,
            len: u64,
        ) -> Result<Window, String> {
            let mut a = HostOracle.window(e, op, g, s, len)?;
            match self.0 {
                0 => a.started = 0,
                1 => a.primal[0] = f64::NAN,
                2 => a.pre = None,
                3 => a.counts.nonzero_t = u64::MAX,
                4 => a.counts.coarse_pass = u64::MAX,
                5 => a.counts.guard_products = u64::MAX,
                6 => a.counts.uncertain = u64::MAX,
                7 => a.counts.accepted_nonzero_f = 1,
                _ => a.counts.useful_windows = 1,
            };
            Ok(a)
        }
    }
    let m = model();
    let p = LinearProgram::new(&m).unwrap();
    let mut e = Engine::new(&p, method());
    let op = Operator::new(
        &e,
        Settings::new(Format::Fp64, Policy::Uniform),
        Layout::Segmented,
    )
    .unwrap();
    e.restrict_step(op.step).unwrap();
    for kind in 0..9 {
        let o = run(
            &e,
            &op,
            &mut Corrupt(kind),
            64,
            &CancellationToken::new(),
            None,
            |_, _| false,
        );
        assert_eq!(o.core.stop, "device_failure");
        assert_eq!(o.core.failure.as_deref(), Some("resident_invalid_window"));
        assert_eq!(o.core.physical, 32);
        assert_eq!(o.counts.uncertain, 32);
        assert_eq!(o.core.iterations, 0);
        assert!(o.core.primal.iter().all(|v| v.is_finite()));
    }
}

#[test]
fn audit_adoption_and_cancellation_restore_the_whole_window() {
    struct Perturb(f64);
    impl Oracle for Perturb {
        fn window(
            &mut self,
            e: &Engine<'_>,
            op: &Operator,
            g: &Generation,
            s: &optimizer_lp::control::Fp64State,
            len: u64,
        ) -> Result<Window, String> {
            let mut a = HostOracle.window(e, op, g, s, len)?;
            a.primal[0] += self.0;
            self.0 = 0.;
            Ok(a)
        }
    }
    let m = model();
    let p = LinearProgram::new(&m).unwrap();
    let mut e = Engine::new(&p, method());
    let op = Operator::new(
        &e,
        Settings::new(Format::Fp16, Policy::Uniform),
        Layout::Segmented,
    )
    .unwrap();
    e.restrict_step(op.step).unwrap();
    let reference = run(
        &e,
        &op,
        &mut HostOracle,
        64,
        &CancellationToken::new(),
        None,
        |_, _| false,
    );
    let adopted = run(
        &e,
        &op,
        &mut Perturb(1e-10),
        64,
        &CancellationToken::new(),
        None,
        |_, _| false,
    );
    assert_eq!(reference, adopted);
    let promoted = run(
        &e,
        &op,
        &mut Perturb(1.),
        64,
        &CancellationToken::new(),
        None,
        |_, _| false,
    );
    assert_eq!(promoted.core.physical, 99);
    assert!(promoted.core.promotion.native);
    assert_eq!(promoted.core.work.replays, 32);
    struct Cancel<'a>(&'a CancellationToken);
    impl Oracle for Cancel<'_> {
        fn window(
            &mut self,
            e: &Engine<'_>,
            op: &Operator,
            g: &Generation,
            s: &optimizer_lp::control::Fp64State,
            len: u64,
        ) -> Result<Window, String> {
            let a = HostOracle.window(e, op, g, s, len)?;
            self.0.cancel();
            Ok(a)
        }
    }
    let token = CancellationToken::new();
    let cancelled = run(&e, &op, &mut Cancel(&token), 64, &token, None, |_, _| false);
    assert_eq!(cancelled.core.stop, "interrupted");
    assert_eq!(cancelled.core.iterations, 0);
    assert_eq!(cancelled.core.physical, 32);
    assert_eq!(cancelled.core.work.rejected, 32);
    let forced = run(
        &e,
        &op,
        &mut HostOracle,
        64,
        &CancellationToken::new(),
        None,
        |_, _| true,
    );
    assert_eq!(forced.first_certified_iteration, Some(0));
    assert_eq!(forced.core.iterations, 64);
}
