use super::*;
use optimizer_core::{Fp64ExecutionSettings, LpDiagnostics, LpExecutionDiagnostics};
use optimizer_lp::{
    control::Fp64Controller,
    research::{Mode, Operator, power_exponent, step},
};
use optimizer_lp_cuda::research::ResearchExecutor;
fn modes() -> [Mode; 12] {
    [
        Mode::DefaultFp64,
        Mode::Power2Fp64,
        Mode::Power2Fp32,
        Mode::FactoredFp64,
        Mode::FactoredFp32,
        Mode::Components2Fp64,
        Mode::Components3Fp64,
        Mode::Components2Fp32,
        Mode::Components3Fp32,
        Mode::IntguardFp64,
        Mode::FusedFp64,
        Mode::DoublefloatFp32,
    ]
}
fn diagnostics() -> LpDiagnostics {
    diagnostics_for(Mode::DefaultFp64)
}
fn diagnostics_for(mode: Mode) -> LpDiagnostics {
    let mut d = LpDiagnostics::new(true, true);
    let mut e = Fp64ExecutionSettings::from_json(include_bytes!(
        "../../../../examples/lp-execution-v1.json"
    ))
    .unwrap();
    e.fusion = if mode.fused() {
        optimizer_core::Fp64Fusion::PrimalDual
    } else {
        optimizer_core::Fp64Fusion::Separate
    };
    d.execution = Some(LpExecutionDiagnostics::new(e));
    d
}
fn engine(p: &LinearProgram, mode: Mode, iterations: u64) -> Engine<'_> {
    let e = Engine::new(p, LpSettings::published(iterations, 8));
    if mode.power2() {
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
        Engine::with_power2_scaling(p, e.settings(), &r, &c).unwrap()
    } else {
        e
    }
}
#[test]
fn research_all_modes_match_independent_steps_across_controller_boundaries() {
    let Some(context) =
        device("research_all_modes_match_independent_steps_across_controller_boundaries")
    else {
        return;
    };
    let m = model();
    let p = LinearProgram::new(&m).unwrap();
    let image = std::fs::read(optimizer_lp_cuda::research::code_object_path()).unwrap();
    for mode in modes() {
        let mut e = engine(&p, mode, 48);
        let op = Operator::new(&e, mode).unwrap();
        e.restrict_step(op.step).unwrap();
        let mut d = diagnostics_for(mode);
        let mut gpu = ResearchExecutor::new(Rc::clone(&context), &e, &op, &image, &mut d).unwrap();
        let mut c = Fp64Controller::new(&e);
        for _ in 0..40 {
            let (x, y) = step(&e, c.state(), &op).unwrap();
            assert_eq!(
                gpu.advance(&mut c, 1, e.step(), d.execution.as_mut().unwrap())
                    .unwrap(),
                None
            );
            c.commit_steps(1).unwrap();
            assert_eq!(c.state().primal, x, "primal {mode:?}");
            assert_eq!(c.state().dual, y, "dual {mode:?}");
            if c.check_pending() {
                c.continue_after_check();
            }
        }
        assert_eq!(
            d.execution.as_ref().unwrap().kernel_launches,
            40 * mode.launches_per_step()
        );
        if mode.components() == 2 {
            assert!(gpu.vector_tail_units > 0 && gpu.vector_tail_units <= 16);
        } else {
            assert_eq!(gpu.vector_tail_units, 0);
        }
        assert_eq!(
            d.execution.as_ref().unwrap().allocated_bytes,
            d.device_buffer_peak_bytes.unwrap()
        );
        println!(
            "research mode {mode:?}: 40 independent steps; {} bytes",
            d.device_buffer_peak_bytes.unwrap()
        );
    }
}
#[test]
fn research_checkpoint_restore_and_exhausted_work_are_respected() {
    let Some(context) = device("research_checkpoint_restore_and_exhausted_work_are_respected")
    else {
        return;
    };
    let m = model();
    let p = LinearProgram::new(&m).unwrap();
    let image = std::fs::read(optimizer_lp_cuda::research::code_object_path()).unwrap();
    let mut e = engine(&p, Mode::Components3Fp32, 8);
    let op = Operator::new(&e, Mode::Components3Fp32).unwrap();
    e.restrict_step(op.step).unwrap();
    let mut d = diagnostics();
    let mut gpu = ResearchExecutor::new(context, &e, &op, &image, &mut d).unwrap();
    let mut c = Fp64Controller::new(&e);
    let cp = c.checkpoint();
    gpu.advance(&mut c, 4, e.step(), d.execution.as_mut().unwrap())
        .unwrap();
    c.commit_steps(4).unwrap();
    let x = c.state().primal.clone();
    let y = c.state().dual.clone();
    c.restore(&cp).unwrap();
    gpu.advance(&mut c, 4, e.step(), d.execution.as_mut().unwrap())
        .unwrap();
    c.commit_steps(4).unwrap();
    assert_eq!(c.state().primal, x);
    assert_eq!(c.state().dual, y);
    assert_eq!(c.remaining(), 0);
    let before = d.execution.as_ref().unwrap().kernel_launches;
    assert!(
        gpu.advance(&mut c, 1, e.step(), d.execution.as_mut().unwrap())
            .is_err()
    );
    assert_eq!(d.execution.as_ref().unwrap().kernel_launches, before);
}
#[test]
fn research_memory_admission_precedes_allocations_and_faults_preserve_state() {
    let Some(context) =
        device("research_memory_admission_precedes_allocations_and_faults_preserve_state")
    else {
        return;
    };
    let m = model();
    let p = LinearProgram::new(&m).unwrap();
    let image = std::fs::read(optimizer_lp_cuda::research::code_object_path()).unwrap();
    let e = engine(&p, Mode::Components3Fp32, 8);
    let mut op = Operator::new(&e, Mode::Components3Fp32).unwrap();
    let mut d = diagnostics();
    d.device_buffer_limit_bytes = Some(1);
    assert!(ResearchExecutor::new(Rc::clone(&context), &e, &op, &image, &mut d).is_err());
    assert_eq!(d.execution.as_ref().unwrap().allocations, 0);
    d.device_buffer_limit_bytes = None;
    op.rows.fill(f64::MAX);
    op.columns.fill(f64::MAX);
    let mut gpu = ResearchExecutor::new(context, &e, &op, &image, &mut d).unwrap();
    let mut c = Fp64Controller::new(&e);
    c.buffers().1.fill(1e300);
    let before = c.state().clone();
    assert!(
        gpu.advance(&mut c, 1, e.step(), d.execution.as_mut().unwrap())
            .unwrap()
            .unwrap()
            .contains("bits_1")
    );
    assert_eq!(c.state(), &before);
    c.charge_extra(1).unwrap();
    assert_eq!(c.physical_iterations(), 1);
    assert_eq!(c.state().iterations, 0);
}
#[test]
fn research_component_device_products_cover_full_exponent_range() {
    use optimizer_cuda_sys::{Argument as A, LaunchConfig, launch};
    use optimizer_lp::research::{component_product, split};
    let Some(context) = device("research_component_device_products_cover_full_exponent_range")
    else {
        return;
    };
    let module = context
        .load_module(&std::fs::read(optimizer_lp_cuda::research::code_object_path()).unwrap())
        .unwrap();
    let stream = context.stream().unwrap();
    let function = module.function("research_components3_cross").unwrap();
    let mut matrix = context.allocate(1).unwrap();
    let mut x = context.allocate::<f64>(1).unwrap();
    let y = context.allocate::<f64>(1).unwrap();
    let mut guard = context.allocate::<u32>(1).unwrap();
    let mut indices = context.allocate::<u32>(1).unwrap();
    let mut offsets = context.allocate::<u32>(2).unwrap();
    let mut scale = context.allocate::<f64>(1).unwrap();
    indices.copy_from(&[0], &stream).unwrap();
    offsets.copy_from(&[0, 1], &stream).unwrap();
    scale.copy_from(&[1.0], &stream).unwrap();
    for (a, b) in [
        (f64::from_bits(1), 1.0),
        (f64::MIN_POSITIVE, 0.5),
        (f64::MAX, 0.5),
        (1.0 / 3.0, 1.0 / 7.0),
        (1e100, -1e-100),
        (f64::MAX, 2.0),
        (f64::from_bits(1), 0.25),
    ] {
        matrix.copy_from(&[split(a).unwrap()], &stream).unwrap();
        x.copy_from(&[b], &stream).unwrap();
        guard.copy_from(&[0], &stream).unwrap();
        let ptr = |v| A::DevicePtr(v);
        launch(
            &function,
            LaunchConfig {
                grid: 1,
                block: 32,
                shared_memory: 0,
            },
            &[
                ptr(matrix.as_device_ptr()),
                ptr(indices.as_device_ptr()),
                ptr(offsets.as_device_ptr()),
                ptr(x.as_device_ptr()),
                ptr(y.as_device_ptr()),
                ptr(guard.as_device_ptr()),
                A::U32(1),
                A::U32(0),
                A::U32(0),
                A::U32(0),
                A::U32(0),
                ptr(scale.as_device_ptr()),
                ptr(scale.as_device_ptr()),
            ],
            &stream,
        )
        .unwrap();
        let mut g = [0];
        guard.copy_to(&mut g, &stream).unwrap();
        let mut value = [0.0];
        y.copy_to(&mut value, &stream).unwrap();
        match component_product(a, b, 3, true) {
            Ok(expected) => {
                assert_eq!(g, [0]);
                assert_eq!(value, [expected]);
            }
            Err(_) => assert_ne!(g, [0]),
        }
    }
}

#[test]
fn research_intguard_fused_and_doublefloat_faults_are_reported_and_state_preserved() {
    let Some(context) =
        device("research_intguard_fused_and_doublefloat_faults_are_reported_and_state_preserved")
    else {
        return;
    };
    let m = model();
    let p = LinearProgram::new(&m).unwrap();
    let image = std::fs::read(optimizer_lp_cuda::research::code_object_path()).unwrap();
    for mode in [Mode::IntguardFp64, Mode::FusedFp64, Mode::DoublefloatFp32] {
        let e = engine(&p, mode, 8);
        let mut op = Operator::new(&e, mode).unwrap();
        let mut d = diagnostics_for(mode);
        d.device_buffer_limit_bytes = Some(1);
        assert!(ResearchExecutor::new(Rc::clone(&context), &e, &op, &image, &mut d).is_err());
        assert_eq!(d.execution.as_ref().unwrap().allocations, 0);
        d.device_buffer_limit_bytes = None;
        // Coefficients stay admissible for the pair representation; the dual is not.
        op.rows.fill(1e30);
        op.columns.fill(1e30);
        let mut gpu = ResearchExecutor::new(Rc::clone(&context), &e, &op, &image, &mut d).unwrap();
        let mut c = Fp64Controller::new(&e);
        c.buffers().1.fill(1e300);
        let before = c.state().clone();
        let reason = gpu
            .advance(&mut c, 1, e.step(), d.execution.as_mut().unwrap())
            .unwrap()
            .unwrap();
        assert!(
            reason.contains("bits_1") || reason.contains("bits_2"),
            "{mode:?}: {reason}"
        );
        assert_eq!(c.state(), &before, "{mode:?}");
        assert_eq!(
            d.execution.as_ref().unwrap().kernel_launches,
            mode.launches_per_step()
        );
        assert_eq!(
            d.execution.as_ref().unwrap().allocated_bytes,
            d.device_buffer_peak_bytes.unwrap()
        );
    }
}
#[test]
fn research_doublefloat_device_products_match_the_pair_oracle_and_flag_loss() {
    use optimizer_cuda_sys::{Argument as A, LaunchConfig, launch};
    use optimizer_lp::research::Pair;
    let Some(context) =
        device("research_doublefloat_device_products_match_the_pair_oracle_and_flag_loss")
    else {
        return;
    };
    let module = context
        .load_module(&std::fs::read(optimizer_lp_cuda::research::code_object_path()).unwrap())
        .unwrap();
    let stream = context.stream().unwrap();
    // One row, one column: the fused dual kernel stores `-dot` into y.
    let function = module.function("research_fused_dual_df").unwrap();
    let mut matrix = context.allocate::<Pair>(1).unwrap();
    let mut bar = context.allocate::<Pair>(1).unwrap();
    let mut y = context.allocate::<f64>(1).unwrap();
    let ydf = context.allocate::<Pair>(1).unwrap();
    let mut lower = context.allocate::<f64>(1).unwrap();
    let mut upper = context.allocate::<f64>(1).unwrap();
    let mut anchor = context.allocate::<f64>(1).unwrap();
    let next = context.allocate::<f64>(1).unwrap();
    let mut guards = context.allocate::<u32>(3).unwrap();
    let mut indices = context.allocate::<u32>(1).unwrap();
    let mut offsets = context.allocate::<u32>(2).unwrap();
    indices.copy_from(&[0], &stream).unwrap();
    offsets.copy_from(&[0, 1], &stream).unwrap();
    // Equality row at zero: the projection clamps `raw/step` to 0, so the
    // stored dual is exactly `raw = 0 - dot`.
    lower.copy_from(&[0.0], &stream).unwrap();
    upper.copy_from(&[0.0], &stream).unwrap();
    anchor.copy_from(&[0.0], &stream).unwrap();
    for (a, b) in [
        (1.0 / 3.0, 1.0 / 7.0),
        (1e30, -1e-30),
        (-1.23456789012345, 0.375),
        (1e-30, 1e-30),
        (1e30, 1e30),
        (f64::from_bits(1), 1.0),
    ] {
        matrix.copy_from(&[Pair::split(a)], &stream).unwrap();
        bar.copy_from(&[Pair::split(b)], &stream).unwrap();
        y.copy_from(&[0.0], &stream).unwrap();
        guards.copy_from(&[0, 0, 0], &stream).unwrap();
        let ptr = |v| A::DevicePtr(v);
        // step 1, toward 1, back 0: y <- 0 - dot under the equality row.
        launch(
            &function,
            LaunchConfig {
                grid: 1,
                block: 32,
                shared_memory: 0,
            },
            &[
                ptr(matrix.as_device_ptr()),
                ptr(indices.as_device_ptr()),
                ptr(offsets.as_device_ptr()),
                ptr(bar.as_device_ptr()),
                ptr(y.as_device_ptr()),
                ptr(ydf.as_device_ptr()),
                ptr(lower.as_device_ptr()),
                ptr(upper.as_device_ptr()),
                ptr(anchor.as_device_ptr()),
                ptr(next.as_device_ptr()),
                ptr(guards.as_device_ptr()),
                ptr(guards.as_device_ptr() + 4),
                ptr(guards.as_device_ptr() + 8),
                A::F64(1.0),
                A::F64(1.0),
                A::F64(0.0),
                A::U32(1),
            ],
            &stream,
        )
        .unwrap();
        let mut g = [0; 3];
        guards.copy_to(&mut g, &stream).unwrap();
        let mut value = [0.0];
        y.copy_to(&mut value, &stream).unwrap();
        // The kernel only sees pairs: subnormal coefficients are refused by
        // `Operator::new`, and an operand whose `hi` underflows is flagged where it
        // is split (bit 2), so product loss is defined on the pair values.
        let (pa, pb) = (Pair::split(a), Pair::split(b));
        let product = pa.times(pb);
        let expected = product.value();
        if pa.hi != 0.0 && pb.hi != 0.0 && product.hi == 0.0 {
            assert_ne!(g[0] & 4, 0, "{a} {b}");
        } else if pa.hi == 0.0 && a != 0.0 {
            assert_eq!(value, [0.0], "{a} {b}");
        } else if !product.hi.is_finite() {
            assert_ne!(g[0] & 1, 0, "{a} {b}");
        } else {
            assert_eq!(g[0], 0, "{a} {b}");
            assert_eq!(value, [-expected], "{a} {b}");
        }
    }
}
