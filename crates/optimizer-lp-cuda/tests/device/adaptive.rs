use super::*;
use optimizer_core::{
    Fp64ExecutionSettings, LpAdaptiveRung as R, LpAdaptiveSettings, LpDiagnostics,
    LpExecutionDiagnostics,
};
use optimizer_lp::{
    adaptive::{PreparedAdaptive, proposal, run},
    control::Fp64State,
};
fn execution() -> Fp64ExecutionSettings {
    Fp64ExecutionSettings::from_json(include_bytes!(
        "../../../../examples/lp-precision-execution-v1.json"
    ))
    .unwrap()
}
fn policy(ladder: Vec<R>, interval: u64, demote: bool) -> LpAdaptiveSettings {
    let mut s = LpAdaptiveSettings::from_json(include_bytes!(
        "../../../../examples/lp-adaptive-demotion-v1.json"
    ))
    .unwrap();
    s.ladder = ladder;
    s.audit_interval = interval;
    if !demote {
        s.demotion = None;
    }
    s
}
fn bits(v: &[f64]) -> Vec<u64> {
    v.iter().map(|v| v.to_bits()).collect()
}
fn host_proposals(
    e: &Engine<'_>,
    p: &PreparedAdaptive,
    s: &LpAdaptiveSettings,
    index: usize,
    state: &Fp64State,
    count: u64,
) -> Result<Fp64State, &'static str> {
    let mut state = state.clone();
    for _ in 0..count {
        let (x, y) = proposal(
            e,
            &state,
            p.operators[index].as_ref().unwrap(),
            s.ladder[index],
        )?;
        state.primal = x;
        state.dual = y;
        state.iterations += 1;
        state.since_restart += 1;
    }
    Ok(state)
}
#[test]
fn adaptive_device_trajectories_match_host_windows_and_accounting() {
    let Some(context) = device("adaptive_device_trajectories_match_host_windows_and_accounting")
    else {
        return;
    };
    for sense in [ObjectiveSense::Minimize, ObjectiveSense::Maximize] {
        let mut document = model().document().clone();
        document.objective.sense = sense;
        let model = Model::from_json(&serde_json::to_vec(&document).unwrap()).unwrap();
        for (ladder, interval, demote) in [
            (vec![R::Fp64], 1, false),
            (vec![R::WorkingFp32, R::Fp64], 3, false),
            (
                vec![
                    R::WorkingFp32,
                    R::AccumulationFp32,
                    R::ProductsFp32,
                    R::StorageFp32,
                    R::Fp64,
                ],
                8,
                true,
            ),
            (vec![R::AccumulationFp32, R::Fp64], 32, false),
            (vec![R::ProductsFp32, R::Fp64], 128, true),
            (vec![R::StorageFp32, R::Fp64], 8, false),
        ] {
            let mut s = policy(ladder, interval, demote);
            let force_recovery = s.ladder[0] == R::WorkingFp32 && interval == 3;
            if force_recovery {
                s.primal_absolute = 0.0;
                s.dual_absolute = 0.0;
                s.relative = 0.0;
            }
            let method = LpSettings::published(41, 10);
            let mut options = options();
            options.iteration_limit = Some(41);
            options.tolerances = Tolerances {
                absolute: 0.0,
                relative: 0.0,
                integrality: 0.0,
            };
            let backend =
                CudaLpBackend::open_adaptive(Rc::clone(&context), method, execution(), s.clone())
                    .unwrap();
            let mut observed = LpDiagnostics::new(true, true);
            let record = backend
                .solve_with_diagnostics(
                    &model,
                    &options,
                    &CancellationToken::new(),
                    None,
                    &mut observed,
                )
                .unwrap();
            assert_eq!(record.schema_version, 5);
            record.to_json().unwrap();
            assert!(observed.iterations.unwrap() <= 41);
            observed.adaptive.as_ref().unwrap().validate().unwrap();
            if force_recovery && sense == ObjectiveSense::Minimize {
                assert!(observed.adaptive.as_ref().unwrap().rejected_windows > 0);
            }
            let p = LinearProgram::new(&model).unwrap();
            let mut engine = Engine::new(&p, method);
            let prepared = PreparedAdaptive::new(&mut engine, &s);
            let mut d = LpDiagnostics::new(true, false);
            d.execution = Some(LpExecutionDiagnostics::new(execution()));
            let (x, y, _) = run::<()>(
                &engine,
                &prepared,
                s.clone(),
                &CancellationToken::new(),
                &mut d,
                None,
                |i, c, n, d| {
                    // Mirror completed GPU work, including deterministic range guards.
                    let trial = host_proposals(&engine, &prepared, &s, i, c.state(), n);
                    d.execution.as_mut().unwrap().kernel_launches += 6 * n;
                    match trial {
                        Ok(next) => {
                            c.replace_endpoint(next.primal, next.dual).unwrap();
                            Ok(None)
                        }
                        Err(_) => Ok(Some("mirror range guard".into())),
                    }
                },
                |x, y, _| {
                    let candidate = optimizer_core::Candidate {
                        schema_version: 1,
                        model_id: model.document().model_id.clone(),
                        values: model
                            .document()
                            .variables
                            .iter()
                            .zip(x)
                            .map(|(v, &value)| optimizer_core::Assignment {
                                variable_id: v.id,
                                value,
                            })
                            .collect(),
                    };
                    model
                        .evaluate(&candidate, options.tolerances)
                        .unwrap()
                        .feasible
                        && optimizer_lp::certify(&p, y)
                            .ok()
                            .and_then(|bound| {
                                optimizer_lp::certify::assess_gap(
                                    &p,
                                    x,
                                    bound.bound,
                                    options.tolerances,
                                )
                            })
                            .is_some_and(|gap| gap.closed)
                },
            )
            .unwrap();
            assert_eq!(observed.adaptive, d.adaptive);
            assert_eq!(
                observed.control.as_ref().unwrap().logical_iterations,
                d.control.as_ref().unwrap().logical_iterations
            );
            let actual = record.candidate.as_ref().unwrap();
            let actual_values = actual.values.iter().map(|v| v.value).collect::<Vec<_>>();
            assert_eq!(bits(&actual_values), bits(&x));
            assert_eq!(bits(observed.dual.as_ref().unwrap()), bits(&y));
        }
    }
}
#[test]
fn adaptive_device_recovery_limits_cancellation_and_memory_are_explicit() {
    let Some(context) =
        device("adaptive_device_recovery_limits_cancellation_and_memory_are_explicit")
    else {
        return;
    };
    for limit in [1, 2, 7, 33] {
        let s = policy(vec![R::WorkingFp32, R::Fp64], 8, true);
        let backend =
            CudaLpBackend::open_adaptive(Rc::clone(&context), settings(64), execution(), s)
                .unwrap();
        let mut options = options();
        options.iteration_limit = Some(limit);
        let mut d = LpDiagnostics::new(true, false);
        backend
            .solve_with_diagnostics(&model(), &options, &CancellationToken::new(), None, &mut d)
            .unwrap();
        assert!(d.iterations.unwrap() <= limit);
        d.adaptive.as_ref().unwrap().validate().unwrap();
        let cancel = CancellationToken::new();
        cancel.cancel();
        let mut d = LpDiagnostics::new(true, false);
        let record = backend
            .solve_with_diagnostics(&model(), &options, &cancel, None, &mut d)
            .unwrap();
        assert_eq!(record.termination, Termination::Interrupted);
        assert_eq!(d.iterations, Some(0));
    }
    let backend = CudaLpBackend::open_adaptive(
        Rc::clone(&context),
        settings(20),
        execution(),
        policy(vec![R::StorageFp32, R::Fp64], 8, false),
    )
    .unwrap();
    let mut d = LpDiagnostics::new(true, false);
    d.device_buffer_limit_bytes = Some(1);
    let record = backend
        .solve_with_diagnostics(
            &model(),
            &options(),
            &CancellationToken::new(),
            None,
            &mut d,
        )
        .unwrap();
    assert_eq!(record.termination, Termination::BackendFailure);
    assert_eq!(d.execution.as_ref().unwrap().kernel_launches, 0);
}
