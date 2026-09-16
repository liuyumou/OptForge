use super::*;
use optimizer_core::{
    Fp64ExecutionSettings as Settings, Fp64Fusion as Fusion, Fp64Reduction as Reduction,
    LpDiagnostics, StateUploads as Uploads, WorkingAllocation as Allocation,
};
use optimizer_lp::control::Fp64Controller;
use optimizer_lp_cuda::tuned::{TunedExecutor, peak_buffer_bytes};

fn variants() -> Vec<Settings> {
    let mut v = Vec::new();
    for allocation in [Allocation::PerCheck, Allocation::Resident] {
        for uploads in [Uploads::EveryCheck, Uploads::Necessary] {
            for reduction in [Reduction::Legacy1024, Reduction::Warp32V1] {
                for fusion in [Fusion::Separate, Fusion::PrimalDual] {
                    let s = Settings {
                        schema_version: 1,
                        allocation,
                        uploads,
                        reduction,
                        fusion,
                    };
                    if s.validate().is_ok() {
                        v.push(s);
                    }
                }
            }
        }
    }
    v
}
fn mirror(values: &[f64], x: &[f64], indices: &[u32], reduction: Reduction) -> f64 {
    let products: Vec<f64> = values
        .iter()
        .zip(indices)
        .map(|(a, i)| a * x[*i as usize])
        .collect();
    if reduction == Reduction::Legacy1024 {
        return optimizer_lp::reduce::tree_sum(&products);
    }
    let mut lanes = [0.0; 32];
    for (lane, out) in lanes.iter_mut().enumerate() {
        for p in products.iter().skip(lane).step_by(32) {
            *out += p;
        }
    }
    for offset in [16, 8, 4, 2, 1] {
        for i in 0..offset {
            lanes[i] += lanes[i + offset];
        }
    }
    lanes[0]
}
fn mirror_step(engine: &Engine<'_>, control: &mut Fp64Controller<'_, '_>, reduction: Reduction) {
    let state = control.state();
    let weight = state.weight;
    let i = state.since_restart;
    let toward = (i + 1) as f64 / (i + 2) as f64;
    let back = 1.0 / (i + 2) as f64;
    let (rows, cols) = engine.scaled_matrix();
    let program = engine.program();
    let (xl, xu) = engine.scaled_column_bounds();
    let (yl, yu) = engine.scaled_row_bounds();
    let old = state.primal.clone();
    let mut nx = old.clone();
    let mut bar = old.clone();
    let mut ny = state.dual.clone();
    for j in 0..old.len() {
        let (indices, _) = program.column_major().line(j);
        let start = program.column_major().offset(j);
        let product = mirror(
            &cols[start..start + indices.len()],
            &state.dual,
            indices,
            reduction,
        );
        let mut next = old[j] - (engine.step() / weight) * (engine.scaled_objective()[j] - product);
        if next < xl[j] {
            next = xl[j];
        }
        if next > xu[j] {
            next = xu[j];
        }
        bar[j] = 2.0 * next - old[j];
        nx[j] = toward * next + back * state.anchor_primal[j];
    }
    for j in 0..ny.len() {
        let (indices, _) = program.row_major().line(j);
        let start = program.row_major().offset(j);
        let product = mirror(
            &rows[start..start + indices.len()],
            &bar,
            indices,
            reduction,
        );
        let step = engine.step() * weight;
        let raw = state.dual[j] - step * product;
        let mut scaled = raw / step;
        if scaled < -yu[j] {
            scaled = -yu[j];
        }
        if scaled > -yl[j] {
            scaled = -yl[j];
        }
        ny[j] = toward * (raw - step * scaled) + back * state.anchor_dual[j];
    }
    let (x, y, _, _) = control.buffers();
    x.copy_from_slice(&nx);
    y.copy_from_slice(&ny);
    control.commit_steps(1).unwrap();
}
fn advance(
    executor: &mut TunedExecutor<'_>,
    control: &mut Fp64Controller<'_, '_>,
    engine: &Engine<'_>,
    n: u64,
    diagnostics: &mut LpDiagnostics,
) -> u64 {
    let generation = control.generation();
    let state = control.state();
    let (restarts, since, weight) = (state.restarts, state.since_restart, state.weight);
    let (x, y, ax, ay) = control.buffers();
    let result = executor
        .advance(
            x,
            y,
            ax,
            ay,
            generation,
            restarts,
            since,
            n,
            engine.step(),
            weight,
            |_| false,
            diagnostics,
        )
        .unwrap();
    control.commit_steps(result.completed).unwrap();
    result.completed
}

#[test]
fn tuned_variants_match_complete_trajectories_and_restored_history() {
    let Some(context) = device("tuned_variants_match_complete_trajectories_and_restored_history")
    else {
        return;
    };
    let mut empty = model().document().clone();
    empty.variables.clear();
    empty.constraints.clear();
    empty.objective.terms.clear();
    for model in [
        model(),
        wide_model(65),
        wide_model(1025),
        Model::new(empty).unwrap(),
    ] {
        let program = LinearProgram::new(&model).unwrap();
        let mut settings = LpSettings::published(96, 7);
        settings.primal_weight.integral = 0.02;
        settings.primal_weight.derivative = 0.1;
        let engine = Engine::new(&program, settings);
        for execution in variants() {
            let mut diagnostics = LpDiagnostics::new(true, false);
            let residency =
                LpResidency::open_tuned(Rc::clone(&context), &engine, execution, &mut diagnostics)
                    .unwrap();
            let mut mismatched = execution;
            mismatched.fusion = if execution.fusion == Fusion::Separate {
                Fusion::PrimalDual
            } else {
                Fusion::Separate
            };
            assert!(TunedExecutor::new(&residency, mismatched).is_err());
            let mut executor = TunedExecutor::new(&residency, execution).unwrap();
            let mut gpu = Fp64Controller::new(&engine);
            let mut reference = Fp64Controller::new(&engine);
            let saved_gpu = gpu.checkpoint();
            let saved_reference = reference.checkpoint();
            for window in 0..5 {
                if window == 2 {
                    gpu.restore(&saved_gpu).unwrap();
                    reference.restore(&saved_reference).unwrap();
                }
                let n = gpu.next_chunk(7);
                assert_eq!(
                    advance(&mut executor, &mut gpu, &engine, n, &mut diagnostics),
                    n
                );
                for _ in 0..n {
                    mirror_step(&engine, &mut reference, execution.reduction);
                }
                assert_eq!(gpu.state(), reference.state(), "{execution:?}");
                for (actual, expected) in [
                    (&gpu.state().dual, &reference.state().dual),
                    (&gpu.state().anchor_primal, &reference.state().anchor_primal),
                    (&gpu.state().anchor_dual, &reference.state().anchor_dual),
                ] {
                    assert_eq!(
                        actual.iter().map(|x| x.to_bits()).collect::<Vec<_>>(),
                        expected.iter().map(|x| x.to_bits()).collect::<Vec<_>>()
                    );
                }
                assert_eq!(
                    gpu.state()
                        .primal
                        .iter()
                        .map(|x| x.to_bits())
                        .collect::<Vec<_>>(),
                    reference
                        .state()
                        .primal
                        .iter()
                        .map(|x| x.to_bits())
                        .collect::<Vec<_>>()
                );
                if gpu.check_pending() {
                    gpu.continue_after_check();
                    reference.continue_after_check();
                }
                assert_eq!(gpu.state(), reference.state());
            }
            let c = diagnostics.execution.unwrap();
            let working = if execution.fusion == Fusion::PrimalDual {
                5
            } else {
                9
            };
            assert_eq!(
                c.allocations,
                11 + working
                    * if execution.allocation == Allocation::Resident {
                        1
                    } else {
                        5
                    }
            );
            assert_eq!(
                c.readback_calls,
                5 * (u64::from(program.column_count() > 0) + u64::from(program.row_count() > 0))
            );
            assert_eq!(
                c.kernel_launches,
                gpu.physical_iterations()
                    * if execution.fusion == Fusion::PrimalDual {
                        2
                    } else {
                        6
                    }
            );
            assert!(c.upload_calls <= 11 + 20);
            assert_eq!(
                residency.requirement().memory_bytes,
                peak_buffer_bytes(&program, execution).unwrap()
            );
        }
    }
}

#[test]
fn tuned_warp32_matches_independent_rational_products() {
    use optimizer_cuda_sys::{Argument as A, LaunchConfig, launch};
    let Some(context) = device("tuned_warp32_matches_independent_rational_products") else {
        return;
    };
    let module = context
        .load_module_file(&optimizer_lp_cuda::tuned::code_object_path())
        .unwrap();
    let function = module.function("spmv_warp32").unwrap();
    let stream = context.stream().unwrap();
    let fixture: serde_json::Value = serde_json::from_str(include_str!(
        "../../../../tests/regression/lp-warp32-oracle.json"
    ))
    .unwrap();
    let number = |v: &serde_json::Value| {
        f64::from_bits(u64::from_str_radix(v.as_str().unwrap(), 16).unwrap())
    };
    let mut cases = fixture["cases"].as_array().unwrap().clone();
    // Nonfinite arithmetic is tested on the device; finite cases above have a
    // separately generated exact-rational error certificate.
    cases.push(serde_json::json!({
        "a": ["7fefffffffffffff", "7fefffffffffffff"],
        "b": ["4000000000000000", "4000000000000000"],
        "result": "7ff0000000000000"
    }));
    for case in &cases {
        let a: Vec<f64> = case["a"].as_array().unwrap().iter().map(number).collect();
        let b: Vec<f64> = case["b"].as_array().unwrap().iter().map(number).collect();
        let n = a.len();
        let indices: Vec<u32> = (0..n as u32).collect();
        let mut av = context.allocate::<f64>(n.max(1)).unwrap();
        let mut bv = context.allocate::<f64>(n.max(1)).unwrap();
        let mut iv = context.allocate::<u32>(n.max(1)).unwrap();
        let mut offsets = context.allocate::<u32>(2).unwrap();
        let out = context.allocate::<f64>(1).unwrap();
        if n > 0 {
            av.copy_from(&a, &stream).unwrap();
            bv.copy_from(&b, &stream).unwrap();
            iv.copy_from(&indices, &stream).unwrap();
        }
        offsets.copy_from(&[0, n as u32], &stream).unwrap();
        for block in [32, 128, 256] {
            launch(
                &function,
                LaunchConfig {
                    grid: 1,
                    block,
                    shared_memory: 0,
                },
                &[
                    A::DevicePtr(av.as_device_ptr()),
                    A::DevicePtr(iv.as_device_ptr()),
                    A::DevicePtr(offsets.as_device_ptr()),
                    A::DevicePtr(bv.as_device_ptr()),
                    A::DevicePtr(out.as_device_ptr()),
                    A::U32(1),
                    A::U32(n as u32),
                ],
                &stream,
            )
            .unwrap();
            let mut result = [0.0];
            out.copy_to(&mut result, &stream).unwrap();
            assert_eq!(
                result[0].to_bits(),
                number(&case["result"]).to_bits(),
                "count {n}, block {block}"
            );
            assert_eq!(
                result[0].to_bits(),
                mirror(&a, &b, &indices, Reduction::Warp32V1).to_bits()
            );
        }
        if n == 65 {
            assert_ne!(
                mirror(&a, &b, &indices, Reduction::Legacy1024),
                number(&case["result"])
            );
        }
    }
}

#[test]
fn tuned_cancellation_limits_memory_and_senses() {
    let Some(context) = device("tuned_cancellation_limits_memory_and_senses") else {
        return;
    };
    let mut execution = variants().pop().unwrap();
    execution.fusion = Fusion::PrimalDual;
    let original = model();
    let program = LinearProgram::new(&original).unwrap();
    let engine = Engine::new(&program, LpSettings::published(300, 200));
    let mut diagnostics = LpDiagnostics::new(true, false);
    let r =
        LpResidency::open_tuned(Rc::clone(&context), &engine, execution, &mut diagnostics).unwrap();
    let mut executor = TunedExecutor::new(&r, execution).unwrap();
    let mut x = engine.start_primal();
    let mut y = engine.start_dual();
    let ax = x.clone();
    let ay = y.clone();
    let done = executor
        .advance(
            &mut x,
            &mut y,
            &ax,
            &ay,
            0,
            0,
            0,
            130,
            engine.step(),
            1.0,
            |n| n >= 64,
            &mut diagnostics,
        )
        .unwrap();
    assert_eq!(done.completed, 64);
    assert!(done.interrupted);
    assert_eq!(diagnostics.execution.as_ref().unwrap().kernel_launches, 128);
    for sense in [ObjectiveSense::Minimize, ObjectiveSense::Maximize] {
        let mut doc = original.document().clone();
        doc.objective.sense = sense;
        let model = Model::new(doc).unwrap();
        let backend = CudaLpBackend::open_tuned(
            Rc::clone(&context),
            LpSettings::published(1000, 7),
            execution,
        )
        .unwrap();
        let run = || {
            let mut d = LpDiagnostics::new(true, false);
            let record = backend
                .solve_with_diagnostics(&model, &options(), &CancellationToken::new(), None, &mut d)
                .unwrap();
            (record, d)
        };
        let (a, ad) = run();
        let (b, bd) = run();
        assert_eq!(a.candidate, b.candidate);
        assert_eq!(a.best_bound, b.best_bound);
        assert_eq!(ad.dual, bd.dual);
        assert_eq!(a.schema_version, 3);
        let mut early = LpDiagnostics::new(true, false);
        let cancelled = CancellationToken::new();
        cancelled.cancel();
        let stopped = backend
            .solve_with_diagnostics(&model, &options(), &cancelled, None, &mut early)
            .unwrap();
        assert_eq!(stopped.termination, Termination::Interrupted);
        let early_execution = early.execution.as_ref().unwrap();
        assert_eq!(early_execution.allocations, 11);
        assert_eq!(early_execution.kernel_launches, 0);
        assert_eq!(
            early.device_buffer_peak_bytes,
            Some(early_execution.allocated_bytes)
        );
        assert!(early.device_buffer_peak_bytes < ad.device_buffer_peak_bytes);
        let mut d = LpDiagnostics::new(true, false);
        d.device_buffer_limit_bytes = Some(1);
        let refused = backend
            .solve_with_diagnostics(&model, &options(), &CancellationToken::new(), None, &mut d)
            .unwrap();
        assert_eq!(refused.termination, Termination::BackendFailure);
        assert_eq!(d.execution.unwrap().allocations, 0);
    }
}
