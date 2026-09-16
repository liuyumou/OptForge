use super::*;
use optimizer_core::{
    Fp64ExecutionSettings, LpDiagnostics, LpExecutionDiagnostics, LpPrecisionSettings, LpWidth,
};
use optimizer_lp::{
    control::Fp64Controller,
    precision::{PrecisionOperator, step},
};
use optimizer_lp_cuda::precision::PrecisionExecutor;
fn execution() -> Fp64ExecutionSettings {
    {
        let mut s = Fp64ExecutionSettings::from_json(include_bytes!(
            "../../../../examples/lp-execution-v1.json"
        ))
        .unwrap();
        s.fusion = optimizer_core::Fp64Fusion::Separate;
        s
    }
}
fn modes() -> Vec<LpPrecisionSettings> {
    [
        include_bytes!("../../../../examples/lp-precision-fp64-v1.json").as_slice(),
        include_bytes!("../../../../examples/lp-storage-fp32-v1.json"),
        include_bytes!("../../../../examples/lp-products-fp32-v1.json"),
        include_bytes!("../../../../examples/lp-accumulation-fp32-v1.json"),
        include_bytes!("../../../../examples/lp-working-fp32-correction32-v1.json"),
    ]
    .into_iter()
    .map(|b| LpPrecisionSettings::from_json(b).unwrap())
    .collect()
}
#[test]
fn precision_modes_match_independent_steps_and_restore_residency() {
    let Some(context) = device("precision_modes_match_independent_steps_and_restore_residency")
    else {
        return;
    };
    let program = LinearProgram::new(&model()).unwrap();
    let image = std::fs::read(optimizer_lp_cuda::precision::code_object_path()).unwrap();
    for mode in modes() {
        let mut engine = Engine::new(&program, settings(16));
        let op = PrecisionOperator::new(&engine, &mode).unwrap();
        engine.restrict_step(op.step).unwrap();
        let mut d = LpDiagnostics::new(true, false);
        d.execution = Some(LpExecutionDiagnostics::new(execution()));
        let mut executor = PrecisionExecutor::new(
            Rc::clone(&context),
            &engine,
            &op,
            mode.clone(),
            &image,
            &mut d,
        )
        .unwrap();
        let mut control = Fp64Controller::new(&engine);
        let checkpoint = control.checkpoint();
        let mut first = None;
        for round in 0..2 {
            if round == 1 {
                control.restore(&checkpoint).unwrap();
            }
            for _ in 0..4 {
                if mode.working_state == LpWidth::F32 {
                    control.round_working().unwrap();
                }
                let (mut x, mut y) = step(
                    &engine,
                    control.state(),
                    &op.rows,
                    &op.columns,
                    mode.products,
                    mode.accumulation,
                )
                .unwrap();
                if mode.working_state == LpWidth::F32 {
                    for v in x.iter_mut().chain(&mut y) {
                        *v = f64::from(*v as f32);
                    }
                }
                let guard = executor
                    .advance(
                        &mut control,
                        1,
                        engine.step(),
                        d.execution.as_mut().unwrap(),
                    )
                    .unwrap();
                assert_eq!(guard, None);
                control.commit_steps(1).unwrap();
                assert_eq!(
                    control
                        .state()
                        .primal
                        .iter()
                        .map(|v| v.to_bits())
                        .collect::<Vec<_>>(),
                    x.iter().map(|v| v.to_bits()).collect::<Vec<_>>()
                );
                assert_eq!(
                    control
                        .state()
                        .dual
                        .iter()
                        .map(|v| v.to_bits())
                        .collect::<Vec<_>>(),
                    y.iter().map(|v| v.to_bits()).collect::<Vec<_>>()
                );
            }
            let state = (control.state().primal.clone(), control.state().dual.clone());
            if let Some(first) = &first {
                assert_eq!(&state, first)
            } else {
                first = Some(state)
            };
        }
        assert_eq!(
            d.execution.as_ref().unwrap().allocated_bytes,
            d.device_buffer_peak_bytes.unwrap()
        );
    }
}
#[test]
fn precision_correction_work_cancellation_and_memory_are_bounded() {
    let Some(context) = device("precision_correction_work_cancellation_and_memory_are_bounded")
    else {
        return;
    };
    for interval in [1, 3, 8, 32, 128] {
        let mut p = modes().pop().unwrap();
        p.correction_interval = Some(interval);
        let backend =
            CudaLpBackend::open_precision(Rc::clone(&context), settings(30), execution(), p)
                .unwrap();
        let mut options = options();
        options.iteration_limit = Some(9);
        let mut d = LpDiagnostics::new(true, false);
        let result = backend
            .solve_with_diagnostics(&model(), &options, &CancellationToken::new(), None, &mut d)
            .unwrap();
        assert_eq!(result.schema_version, 4);
        let p = d.precision.as_ref().unwrap();
        let c = d.control.as_ref().unwrap();
        assert_eq!(
            c.physical_iterations,
            Some(p.proposed_steps + p.correction_steps)
        );
        assert!(c.physical_iterations.unwrap() <= 9);
        assert!(p.correction_steps <= p.proposed_steps);
        if interval == 1 {
            assert_eq!(p.proposed_steps, 4);
            assert_eq!(p.correction_steps, 4);
        }
        let token = CancellationToken::new();
        token.cancel();
        let mut d = LpDiagnostics::new(true, false);
        let r = backend
            .solve_with_diagnostics(&model(), &options, &token, None, &mut d)
            .unwrap();
        assert_eq!(r.termination, Termination::Interrupted);
        assert_eq!(d.iterations, Some(0));
        let mut d = LpDiagnostics::new(true, false);
        d.device_buffer_limit_bytes = Some(1);
        let r = backend
            .solve_with_diagnostics(&model(), &options, &CancellationToken::new(), None, &mut d)
            .unwrap();
        assert_eq!(r.termination, Termination::BackendFailure);
        assert_eq!(d.execution.unwrap().allocations, 0);
    }
}
#[test]
fn precision_range_failure_is_not_availability_fallback() {
    let Some(context) = device("precision_range_failure_is_not_availability_fallback") else {
        return;
    };
    let mut document = model().document().clone();
    document.variables[0].lower = finite(1e50);
    document.variables[0].upper = finite(1e51);
    let extreme = Model::new(document).unwrap();
    let p = modes().pop().unwrap();
    let backend = CudaLpBackend::open_precision(context, settings(4), execution(), p).unwrap();
    let mut d = LpDiagnostics::new(true, false);
    let result = backend
        .solve_with_diagnostics(
            &extreme,
            &options(),
            &CancellationToken::new(),
            None,
            &mut d,
        )
        .unwrap();
    assert_eq!(result.termination, Termination::NumericalFailure);
    assert!(d.precision.unwrap().guard.is_some());
}

#[test]
fn precision_long_sparse_reductions_and_guarded_operands() {
    let Some(context) = device("precision_long_sparse_reductions_and_guarded_operands") else {
        return;
    };
    let mut doc = model().document().clone();
    doc.variables = (0..67)
        .map(|id| optimizer_core::Variable {
            id,
            domain: optimizer_core::Domain::Continuous,
            lower: finite(-2.0),
            upper: finite(3.0),
        })
        .collect();
    doc.constraints = (0..35)
        .map(|id| optimizer_core::Constraint {
            id,
            lower: finite(-4.0),
            upper: finite(4.0),
            terms: (0..67)
                .filter(|j| (j + id) % 5 != 0)
                .map(|variable_id| optimizer_core::LinearTerm {
                    variable_id,
                    coefficient: (f64::from((variable_id + id) % 17) - 8.0) / 9.0,
                })
                .filter(|t| t.coefficient != 0.0)
                .collect(),
        })
        .collect();
    doc.objective.terms = (0..67)
        .map(|variable_id| optimizer_core::LinearTerm {
            variable_id,
            coefficient: (f64::from(variable_id % 11) - 5.0) / 7.0,
        })
        .filter(|t| t.coefficient != 0.0)
        .collect();
    let program = LinearProgram::new(&Model::new(doc).unwrap()).unwrap();
    let image = std::fs::read(optimizer_lp_cuda::precision::code_object_path()).unwrap();
    for mode in modes() {
        let mut engine = Engine::new(&program, settings(8));
        let op = PrecisionOperator::new(&engine, &mode).unwrap();
        engine.restrict_step(op.step).unwrap();
        let mut d = LpDiagnostics::new(true, false);
        d.execution = Some(LpExecutionDiagnostics::new(execution()));
        let mut executor = PrecisionExecutor::new(
            Rc::clone(&context),
            &engine,
            &op,
            mode.clone(),
            &image,
            &mut d,
        )
        .unwrap();
        let mut c = Fp64Controller::new(&engine);
        for _ in 0..3 {
            if mode.working_state == LpWidth::F32 {
                c.round_working().unwrap();
            }
            let (mut x, mut y) = step(
                &engine,
                c.state(),
                &op.rows,
                &op.columns,
                mode.products,
                mode.accumulation,
            )
            .unwrap();
            if mode.working_state == LpWidth::F32 {
                for v in x.iter_mut().chain(&mut y) {
                    *v = f64::from(*v as f32);
                }
            }
            assert_eq!(
                executor
                    .advance(&mut c, 1, engine.step(), d.execution.as_mut().unwrap())
                    .unwrap(),
                None
            );
            c.commit_steps(1).unwrap();
            assert_eq!(c.state().primal, x);
            assert_eq!(c.state().dual, y);
        }
        if mode.products == LpWidth::F32 {
            let x = c.state().primal.clone();
            let y = vec![1e100; program.row_count()];
            c.replace_endpoint(x, y).unwrap();
            let guard = executor
                .advance(&mut c, 1, engine.step(), d.execution.as_mut().unwrap())
                .unwrap();
            assert!(guard.is_some());
        }
    }
}

#[test]
fn precision_interval_one_adopts_original_fp64_endpoint() {
    let Some(context) = device("precision_interval_one_adopts_original_fp64_endpoint") else {
        return;
    };
    let mut doc = model().document().clone();
    doc.variables.truncate(1);
    doc.objective.terms.truncate(1);
    doc.constraints[0].terms.truncate(1);
    doc.constraints[0].upper = finite(0.75);
    let model = Model::new(doc).unwrap();
    let mut p = modes().pop().unwrap();
    p.correction_interval = Some(1);
    let backend = CudaLpBackend::open_precision(context, settings(2), execution(), p).unwrap();
    let mut d = LpDiagnostics::new(true, false);
    let result = backend
        .solve_with_diagnostics(&model, &options(), &CancellationToken::new(), None, &mut d)
        .unwrap();
    let step = d.precision.as_ref().unwrap().step.unwrap();
    // A=[1], x=y=anchors=0, c=-1: literal original-model one-step arithmetic.
    let expected_x = 0.5 * step;
    let raw = -(step * (2.0 * step));
    let expected_y = 0.5 * (raw - step * (-0.75));
    assert_eq!(result.candidate.unwrap().values[0].value, expected_x);
    assert_eq!(d.dual.unwrap(), vec![expected_y]);
    assert_ne!(expected_x, f64::from(expected_x as f32));
    assert_eq!(d.precision.as_ref().unwrap().proposed_steps, 1);
    assert_eq!(d.precision.as_ref().unwrap().correction_steps, 1);
    assert_eq!(d.iterations, Some(2));
}

#[test]
fn precision_device_preserves_subnormals_and_checks_loss_before_projection() {
    let Some(context) =
        device("precision_device_preserves_subnormals_and_checks_loss_before_projection")
    else {
        return;
    };
    let mut doc = model().document().clone();
    doc.variables.truncate(1);
    doc.variables[0].lower = finite(-2.0);
    doc.variables[0].upper = finite(2.0);
    doc.constraints.truncate(1);
    doc.constraints[0].lower = finite(-2.0);
    doc.constraints[0].upper = finite(2.0);
    doc.constraints[0].terms = vec![optimizer_core::LinearTerm {
        variable_id: doc.variables[0].id,
        coefficient: 1.0,
    }];
    doc.objective.terms.clear();
    let program = LinearProgram::new(&Model::new(doc).unwrap()).unwrap();
    let image = std::fs::read(optimizer_lp_cuda::precision::code_object_path()).unwrap();
    // Directly supply exactly representable coefficients to isolate the kernel's
    // arithmetic from preconditioning. The host oracle uses these same inputs.
    for (coefficient, dual, primal, mode_index, fails) in [
        (2_f64.powi(-149), 1.0, 0.0, 1, false),
        (2_f64.powi(-149), 1.0, 1.0, 2, false),
        (1.0, 1.0 + 2_f64.powi(-24), 1.0, 2, false),
        (1.0, 1.0 + 3.0 * 2_f64.powi(-24), 1.0, 2, false),
        (1.0, 2_f64.powi(-150), 1.0, 2, true),
        (2_f64.powi(-126), 2_f64.powi(-24), 1.0, 2, true),
        (f64::from(f32::MAX), f64::from(f32::MAX), 1.0, 2, true),
    ] {
        let mode = modes().remove(mode_index);
        let mut engine = Engine::new(&program, settings(4));
        let mut op = PrecisionOperator::new(&engine, &mode).unwrap();
        engine.restrict_step(op.step).unwrap();
        op.rows.fill(coefficient);
        op.columns.fill(coefficient);
        let mut d = LpDiagnostics::new(true, false);
        d.execution = Some(LpExecutionDiagnostics::new(execution()));
        let mut executor = PrecisionExecutor::new(
            Rc::clone(&context),
            &engine,
            &op,
            mode.clone(),
            &image,
            &mut d,
        )
        .unwrap();
        let mut c = Fp64Controller::new(&engine);
        c.replace_endpoint(vec![primal], vec![dual]).unwrap();
        let before = c.state().clone();
        let expected = step(
            &engine,
            &before,
            &op.rows,
            &op.columns,
            mode.products,
            mode.accumulation,
        );
        let guard = executor
            .advance(&mut c, 1, engine.step(), d.execution.as_mut().unwrap())
            .unwrap();
        assert_eq!(
            guard.is_some(),
            fails,
            "coefficient={coefficient}, dual={dual}"
        );
        assert_eq!(expected.is_err(), fails);
        if let Ok((x, y)) = expected {
            assert_eq!(c.state().primal, x);
            assert_eq!(c.state().dual, y);
        } else {
            assert_eq!(c.state().primal, before.primal);
            assert_eq!(c.state().dual, before.dual);
        }
    }
}
