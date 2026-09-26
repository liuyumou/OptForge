//! Fault injection against the host-owned window state machine; no CUDA dependency.
use optimizer_core::{
    CancellationToken, LpAdaptiveRung as R, LpAdaptiveSettings, LpDemotionSettings, LpDiagnostics,
    LpSettings, Model,
};
use optimizer_lp::{
    Engine, LinearProgram,
    adaptive::{PreparedAdaptive, proposal, run},
    control::Fp64State,
};
use std::time::{Duration, Instant};
fn policy(ladder: Vec<R>) -> LpAdaptiveSettings {
    LpAdaptiveSettings {
        schema_version: 1,
        ladder,
        audit_interval: 2,
        primal_absolute: 1e-7,
        dual_absolute: 1e-7,
        relative: 1e-7,
        demotion: None,
    }
}
fn model() -> Model {
    Model::from_json(include_bytes!("../../../examples/lp-model-v1.json")).unwrap()
}
fn proposals(
    e: &Engine<'_>,
    p: &PreparedAdaptive,
    s: &LpAdaptiveSettings,
    index: usize,
    state: &Fp64State,
    count: u64,
) -> Fp64State {
    let mut next = state.clone();
    for _ in 0..count {
        let (x, y) = proposal(
            e,
            &next,
            p.operators[index].as_ref().unwrap(),
            s.ladder[index],
        )
        .unwrap();
        next.primal = x;
        next.dual = y;
        next.iterations += 1;
        next.since_restart += 1;
    }
    next
}
#[test]
fn adaptive_failed_audit_restores_all_state_and_charges_reference_and_replay() {
    let p = LinearProgram::new(&model()).unwrap();
    let s = policy(vec![R::AccumulationFp32, R::StorageFp32, R::Fp64]);
    let mut e = Engine::new(&p, LpSettings::published(32, 4));
    let prepared = PreparedAdaptive::new(&mut e, &s);
    let mut d = LpDiagnostics::new(true, false);
    let mut original = None;
    let mut checked_restore = false;
    run::<()>(
        &e,
        &prepared,
        s.clone(),
        &CancellationToken::new(),
        &mut d,
        None,
        |i, c, n, _| {
            if original.is_none() {
                original = Some(c.state().clone());
            }
            if i == 1 && c.state().iterations == 0 {
                assert_eq!(Some(c.state()), original.as_ref());
                checked_restore = true;
            }
            let mut next = proposals(&e, &prepared, &s, i, c.state(), n);
            if i == 0 {
                next.primal[0] += 1000.0;
            }
            c.replace_endpoint(next.primal, next.dual).unwrap();
            Ok(None)
        },
        |_, _, _| false,
    )
    .unwrap();
    assert!(checked_restore);
    let a = d.adaptive.unwrap();
    a.validate().unwrap();
    assert_eq!(a.transitions[0].reason, "audit_failed");
    assert_eq!(a.transitions[0].physical_work, 3);
    assert!(a.replay_steps >= 2);
    assert_eq!(
        a.proposed_steps - a.rejected_steps,
        d.control.as_ref().unwrap().logical_iterations
    );
    assert_eq!(
        a.proposed_steps + a.audit_steps + a.probe_steps,
        d.iterations.unwrap()
    );
    assert!(d.iterations.unwrap() <= 32);
}
#[test]
fn adaptive_midwindow_guard_discards_complete_chunk_and_prior_updates() {
    let p = LinearProgram::new(&model()).unwrap();
    let mut s = policy(vec![R::StorageFp32, R::Fp64]);
    s.audit_interval = 128;
    let mut e = Engine::new(&p, LpSettings::published(400, 200));
    let prepared = PreparedAdaptive::new(&mut e, &s);
    let mut d = LpDiagnostics::new(true, false);
    let mut initial = None;
    let mut restored = false;
    run::<()>(
        &e,
        &prepared,
        s.clone(),
        &CancellationToken::new(),
        &mut d,
        None,
        |i, c, n, _| {
            if initial.is_none() {
                initial = Some(c.state().clone());
            }
            if i == 0 && c.state().iterations > 0 {
                assert_eq!(n, 63);
                return Ok(Some("injected guard".into()));
            }
            if i == 1 && c.state().iterations == 0 {
                assert_eq!(Some(c.state()), initial.as_ref());
                restored = true;
            }
            let next = proposals(&e, &prepared, &s, i, c.state(), n);
            c.replace_endpoint(next.primal, next.dual).unwrap();
            Ok(None)
        },
        |_, _, _| false,
    )
    .unwrap();
    assert!(restored);
    let a = d.adaptive.unwrap();
    a.validate().unwrap();
    assert_eq!(a.transitions[0].physical_work, 127);
    assert!(a.rejected_steps >= 127);
    assert_eq!(a.transitions[0].reason, "range_guard");
}
#[test]
fn adaptive_demotion_probes_are_charged_and_sticky_policies_do_not_demote() {
    for demotion in [false, true] {
        let p = LinearProgram::new(&model()).unwrap();
        let mut s = policy(vec![R::StorageFp32, R::Fp64]);
        if demotion {
            s.demotion = Some(LpDemotionSettings {
                clean_windows: 4,
                margin_fraction: 0.25,
            });
        }
        let mut e = Engine::new(&p, LpSettings::published(80, 8));
        let prepared = PreparedAdaptive::new(&mut e, &s);
        let mut d = LpDiagnostics::new(true, false);
        let mut injected = false;
        run::<()>(
            &e,
            &prepared,
            s.clone(),
            &CancellationToken::new(),
            &mut d,
            None,
            |i, c, n, _| {
                if !injected {
                    injected = true;
                    return Ok(Some("injected".into()));
                }
                let next = proposals(&e, &prepared, &s, i, c.state(), n);
                c.replace_endpoint(next.primal, next.dual).unwrap();
                Ok(None)
            },
            |_, _, _| false,
        )
        .unwrap();
        let a = d.adaptive.unwrap();
        a.validate().unwrap();
        assert_eq!(a.probe_steps > 0, demotion);
        assert_eq!(
            a.transitions.iter().any(|t| t.reason == "demotion"),
            demotion
        );
        assert_eq!(
            a.proposed_steps + a.audit_steps + a.probe_steps,
            d.iterations.unwrap()
        );
    }
}
#[test]
fn adaptive_interrupted_window_and_unknown_device_work_never_commit() {
    for device_fault in [false, true] {
        let p = LinearProgram::new(&model()).unwrap();
        let s = policy(vec![R::Fp64]);
        let mut e = Engine::new(&p, LpSettings::published(20, 4));
        let prepared = PreparedAdaptive::new(&mut e, &s);
        let cancel = CancellationToken::new();
        let mut d = LpDiagnostics::new(true, false);
        let result = run(
            &e,
            &prepared,
            s.clone(),
            &cancel,
            &mut d,
            None,
            |i, c, n, _| {
                let next = proposals(&e, &prepared, &s, i, c.state(), n);
                c.replace_endpoint(next.primal, next.dual).unwrap();
                cancel.cancel();
                if device_fault {
                    Err("injected device fault")
                } else {
                    Ok(None)
                }
            },
            |_, _, _| panic!("uncommitted state assessed"),
        );
        assert_eq!(result.is_err(), device_fault);
        assert_eq!(d.control.as_ref().unwrap().logical_iterations, 0);
        assert_eq!(d.iterations, if device_fault { None } else { Some(1) });
        let a = d.adaptive.unwrap();
        a.validate().unwrap();
        assert_eq!(a.proposed_steps, a.rejected_steps);
    }
}
#[test]
fn adaptive_exhausted_ladder_budget_deadline_and_preparation_are_explicit() {
    for limit in [0, 1, 2, 3, 16] {
        let p = LinearProgram::new(&model()).unwrap();
        let s = policy(vec![R::Fp64]);
        // Published settings require a positive limit; clamp only this test engine.
        let mut ls = LpSettings::published(limit.max(1), 4);
        ls.iteration_limit = limit;
        let mut e = Engine::new(&p, ls);
        let prepared = PreparedAdaptive::new(&mut e, &s);
        let mut d = LpDiagnostics::new(true, false);
        run::<()>(
            &e,
            &prepared,
            s.clone(),
            &CancellationToken::new(),
            &mut d,
            None,
            |i, c, n, _| {
                let mut next = proposals(&e, &prepared, &s, i, c.state(), n);
                next.primal[0] += 1e9;
                c.replace_endpoint(next.primal, next.dual).unwrap();
                Ok(None)
            },
            |_, _, _| false,
        )
        .unwrap();
        let a = d.adaptive.unwrap();
        a.validate().unwrap();
        assert!(d.iterations.unwrap() <= limit);
        if limit >= 2 {
            assert_eq!(d.control.unwrap().stop, "numerical_failure");
            assert_eq!(a.transitions.last().unwrap().to, None);
        }
    }
    let p = LinearProgram::new(&model()).unwrap();
    let s = policy(vec![R::StorageFp32, R::Fp64]);
    let mut e = Engine::new(&p, LpSettings::published(8, 4));
    let mut prepared = PreparedAdaptive::new(&mut e, &s);
    prepared.operators[0] = Err("injected conversion guard");
    let mut d = LpDiagnostics::new(true, false);
    run::<()>(
        &e,
        &prepared,
        s.clone(),
        &CancellationToken::new(),
        &mut d,
        None,
        |i, c, n, _| {
            assert_eq!(i, 1);
            let next = proposals(&e, &prepared, &s, i, c.state(), n);
            c.replace_endpoint(next.primal, next.dual).unwrap();
            Ok(None)
        },
        |_, _, _| false,
    )
    .unwrap();
    assert_eq!(
        d.adaptive.as_ref().unwrap().transitions[0].reason,
        "preparation_guard"
    );
    let mut d = LpDiagnostics::new(true, false);
    run::<()>(
        &e,
        &prepared,
        s,
        &CancellationToken::new(),
        &mut d,
        Some(Instant::now() - Duration::from_secs(1)),
        |_, _, _, _| panic!("expired"),
        |_, _, _| false,
    )
    .unwrap();
    assert_eq!(d.control.unwrap().stop, "time_limit");
    assert_eq!(d.iterations, Some(0));
}
#[test]
fn adaptive_policy_is_strict_and_has_no_hidden_defaults() {
    let value = serde_json::to_value(policy(vec![
        R::WorkingFp32,
        R::AccumulationFp32,
        R::ProductsFp32,
        R::StorageFp32,
        R::Fp64,
    ]))
    .unwrap();
    let encode = |v: &serde_json::Value| serde_json::to_vec(v).unwrap();
    assert!(LpAdaptiveSettings::from_json(&encode(&value)).is_ok());
    for key in value.as_object().unwrap().keys() {
        let mut v = value.clone();
        v.as_object_mut().unwrap().remove(key);
        assert!(LpAdaptiveSettings::from_json(&encode(&v)).is_err(), "{key}");
    }
    for (key, bad) in [
        ("ladder", serde_json::json!([])),
        ("ladder", serde_json::json!(["fp64", "fp64"])),
        ("ladder", serde_json::json!(["storage_fp32"])),
        ("audit_interval", serde_json::json!(0)),
        (
            "demotion",
            serde_json::json!({"clean_windows":0,"margin_fraction":0.25}),
        ),
        ("relative", serde_json::json!(-1)),
        ("schema_version", serde_json::json!(2)),
        ("unknown", serde_json::json!(null)),
    ] {
        let mut v = value.clone();
        v[key] = bad;
        assert!(LpAdaptiveSettings::from_json(&encode(&v)).is_err(), "{key}");
    }
}

#[test]
fn adaptive_rollback_preserves_restart_and_weight_history_after_a_check() {
    let p = LinearProgram::new(&model()).unwrap();
    let mut s = policy(vec![R::StorageFp32, R::Fp64]);
    s.primal_absolute = 1e-2;
    s.dual_absolute = 1e-2;
    let mut e = Engine::new(&p, LpSettings::published(30, 4));
    let prepared = PreparedAdaptive::new(&mut e, &s);
    let mut d = LpDiagnostics::new(true, false);
    let mut checkpoint = None;
    let mut restored = false;
    run::<()>(
        &e,
        &prepared,
        s.clone(),
        &CancellationToken::new(),
        &mut d,
        None,
        |i, c, n, _| {
            if i == 0 && c.state().iterations == 4 {
                checkpoint = Some(c.state().clone());
            }
            if i == 1 && c.state().iterations == 4 {
                assert_eq!(Some(c.state()), checkpoint.as_ref());
                restored = true;
            }
            let mut next = proposals(&e, &prepared, &s, i, c.state(), n);
            if i == 0 && c.state().iterations >= 4 {
                next.primal[0] += 1e8;
            }
            c.replace_endpoint(next.primal, next.dual).unwrap();
            Ok(None)
        },
        |_, _, _| false,
    )
    .unwrap();
    assert!(restored);
    assert_eq!(checkpoint.unwrap().checked_iteration, 4);
    assert_eq!(d.adaptive.unwrap().transitions[0].iteration, 4);
}

#[test]
fn adaptive_clean_fp64_windows_cannot_substitute_for_a_lower_precision_probe() {
    let p = LinearProgram::new(&model()).unwrap();
    let mut s = policy(vec![R::WorkingFp32, R::Fp64]);
    s.primal_absolute = 0.0;
    s.dual_absolute = 0.0;
    s.relative = 0.0;
    s.demotion = Some(LpDemotionSettings {
        clean_windows: 1,
        margin_fraction: 0.25,
    });
    let mut e = Engine::new(&p, LpSettings::published(40, 8));
    let prepared = PreparedAdaptive::new(&mut e, &s);
    let mut d = LpDiagnostics::new(true, false);
    let mut injected = false;
    run::<()>(
        &e,
        &prepared,
        s.clone(),
        &CancellationToken::new(),
        &mut d,
        None,
        |i, c, n, _| {
            if !injected {
                injected = true;
                return Ok(Some("initial guard".into()));
            }
            let next = proposals(&e, &prepared, &s, i, c.state(), n);
            c.replace_endpoint(next.primal, next.dual).unwrap();
            Ok(None)
        },
        |_, _, _| false,
    )
    .unwrap();
    let a = d.adaptive.unwrap();
    assert!(a.accepted_windows >= 4);
    assert!(a.probe_steps >= 4);
    assert!(!a.transitions.iter().any(|t| t.reason == "demotion"));
}

#[test]
fn adaptive_audits_check_both_original_unit_vectors_and_nonfinite_intermediates() {
    use optimizer_lp::{adaptive::audit, control::Fp64Controller};
    let p = LinearProgram::new(&model()).unwrap();
    let e = Engine::new(&p, LpSettings::published(10, 4));
    let c = Fp64Controller::new(&e);
    let mut s = policy(vec![R::Fp64]);
    s.primal_absolute = 1e100;
    s.dual_absolute = 0.0;
    s.relative = 0.0;
    let pre = c.state();
    let mut x = pre.primal.clone();
    let mut y = pre.dual.clone();
    x[0] += 1.0;
    assert!(audit(&e, &s, pre, (&x, &y), (&pre.primal, &pre.dual), 1.0).0);
    y[0] += 1.0;
    assert!(!audit(&e, &s, pre, (&x, &y), (&pre.primal, &pre.dual), 1.0).0);
    y = pre.dual.clone();
    x[0] = f64::INFINITY;
    assert!(!audit(&e, &s, pre, (&x, &y), (&pre.primal, &pre.dual), 1.0).0);
}
