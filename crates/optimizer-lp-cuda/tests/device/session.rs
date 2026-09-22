//! SPEC-0014 session device acceptance: bitwise identity against fresh
//! single solves, variant rebind accounting, refusal before allocation,
//! poisoning, cancellation and one-time admission.
//!
//! Every test needs hardware, the driver and the tuned code object; missing
//! pieces are explicit skips, never coverage, exactly as the rest of this
//! suite. The research cases additionally need the precision-research feature
//! and its code object.
//!
//! The tuned cases solve at 64 iterations rather than the wider suite's 400:
//! the batch identity and counter assertions are iteration-count-independent,
//! and the bounded count is what lets every session_ case complete under all
//! four scoped sanitizers — racecheck included — inside SPEC-0014
//! requirement 28's frozen 600-second acceptance cap. Deep trajectory soak is
//! the pre-existing tuned_cases coverage's, unchanged.

use super::*;
use optimizer_core::{
    ErrorKind, Fp64ExecutionSettings, LpDiagnostics, LpExecutionDiagnostics, SolveRecord,
};
use optimizer_lp_cuda::TunedSession;

/// The pinned tuned execution document, as the tuned suite reads it.
fn execution() -> Fp64ExecutionSettings {
    Fp64ExecutionSettings::from_json(include_bytes!("../../../../examples/lp-execution-v1.json"))
        .unwrap()
}

/// One fresh tuned single solve through the ordinary backend path.
fn fresh_tuned(
    context: &Rc<Context>,
    model: &Model,
    settings: LpSettings,
) -> (SolveRecord, LpDiagnostics) {
    let backend = CudaLpBackend::open_tuned(Rc::clone(context), settings, execution()).unwrap();
    let mut diagnostics = LpDiagnostics::new(true, true);
    let record = backend
        .solve_with_diagnostics(
            model,
            &options(),
            &CancellationToken::new(),
            None,
            &mut diagnostics,
        )
        .unwrap();
    (record, diagnostics)
}

/// Diagnostics without the parts a session deliberately reports differently:
/// the phase timings and the execution counters (requirement 9 gives each
/// solve fresh counters; the invariant upload is the session open's).
fn comparable(diagnostics: &LpDiagnostics) -> LpDiagnostics {
    let mut comparable = diagnostics.clone();
    comparable.phases_ns.clear();
    comparable.execution = None;
    comparable
}

/// Per-solve session counters plus the one-time open counters must total the
/// fresh solve's counters: the same device work, attributed once (requirement
/// 12's counting rule). A bound rebind is counted inside this solve's counters
/// by `LpResidency::rebind_column_bounds` and has no fresh-solve counterpart —
/// the fresh solve carries its bounds in its own invariant upload — so the
/// rebind's calls, bytes and synchronizations are added to the fresh side.
fn assert_counter_partition(
    session: &LpExecutionDiagnostics,
    open: &LpExecutionDiagnostics,
    fresh: &LpExecutionDiagnostics,
    rebind_calls: u64,
    rebind_bytes: u64,
) {
    assert_eq!(session.allocations + open.allocations, fresh.allocations);
    assert_eq!(
        session.allocated_bytes + open.allocated_bytes,
        fresh.allocated_bytes
    );
    assert_eq!(
        session.upload_calls + open.upload_calls,
        fresh.upload_calls + rebind_calls
    );
    assert_eq!(
        session.upload_bytes + open.upload_bytes,
        fresh.upload_bytes + rebind_bytes
    );
    assert_eq!(
        session.readback_calls + open.readback_calls,
        fresh.readback_calls
    );
    assert_eq!(
        session.readback_bytes + open.readback_bytes,
        fresh.readback_bytes
    );
    assert_eq!(
        session.synchronizations + open.synchronizations,
        fresh.synchronizations + rebind_calls
    );
    assert_eq!(session.kernel_launches, fresh.kernel_launches);
}

/// Requirement 15: five repeat solves in one session are bitwise the five
/// fresh single solves of the same model, settings and code object.
#[test]
fn session_tuned_batch_matches_fresh_single_solves() {
    let Some(context) = device("session_tuned_batch_matches_fresh_single_solves") else {
        return;
    };
    for model in [model(), wide_model(65), wide_model(1025)] {
        let settings = settings(64);
        let mut open_diagnostics = LpDiagnostics::new(true, true);
        let mut session = TunedSession::open(
            Rc::clone(&context),
            settings,
            execution(),
            model.clone(),
            &mut open_diagnostics,
        )
        .unwrap();
        let open = open_diagnostics.execution.clone().unwrap();
        // The one-time setup phases are the session's; per-solve endpoint
        // diagnostics must not gain them (requirement 24).
        for phase in [
            "preconditioning",
            "module_load",
            "invariant_allocation_upload",
        ] {
            assert!(session.setup().phases_ns.contains_key(phase), "{phase}");
        }
        let mut records = Vec::new();
        let mut observations = Vec::new();
        for _ in 0..5 {
            let mut diagnostics = LpDiagnostics::new(true, true);
            let record = session
                .solve(
                    None,
                    &options(),
                    &CancellationToken::new(),
                    &mut diagnostics,
                )
                .unwrap();
            for banned in ["variant_rebind", "engine_rebind", "bound_upload"] {
                assert!(
                    !diagnostics.phases_ns.contains_key(banned),
                    "session phase {banned} must stay out of the endpoint phases"
                );
            }
            records.push(record);
            observations.push(diagnostics);
        }
        assert_eq!(session.residency().uploads(), 1, "invariant upload once");
        assert_eq!(
            session.residency().bound_rebinds(),
            0,
            "a repeat never rebinds"
        );
        for k in 0..5 {
            let (fresh_record, fresh_diagnostics) = fresh_tuned(&context, &model, settings);
            let mut actual = records[k].clone();
            actual.elapsed_ms = 0;
            let mut expected = fresh_record.clone();
            expected.elapsed_ms = 0;
            assert_eq!(actual, expected, "record {k}");
            assert_eq!(
                comparable(&observations[k]),
                comparable(&fresh_diagnostics),
                "diagnostics {k}"
            );
            // Per-solve upload bytes are the working-state-only bytes: the
            // invariant upload is the open counters', counted once.
            assert_counter_partition(
                observations[k].execution.as_ref().unwrap(),
                &open,
                fresh_diagnostics.execution.as_ref().unwrap(),
                0,
                0,
            );
        }
    }
}

/// Requirements 11, 12 and 15: a variant batch rebinds only the column-bound
/// buffers, only when consecutive bound sets differ, and each variant solve is
/// bitwise the fresh solve of the materialized variant model.
#[test]
fn session_tuned_variant_batch_matches_fresh_materialized_solves() {
    let Some(context) = device("session_tuned_variant_batch_matches_fresh_materialized_solves")
    else {
        return;
    };
    let base = model();
    // (0.5, 1.0) is the base model's optimum; every variant's bounds bracket
    // it, so it stays feasible for each materialized model.
    let tighten = |x0: (f64, f64), x1: (f64, f64)| {
        let mut variables = base.document().variables.clone();
        variables[0].lower = finite(x0.0);
        variables[0].upper = finite(x0.1);
        variables[1].lower = finite(x1.0);
        variables[1].upper = finite(x1.1);
        base.rebound(variables).unwrap()
    };
    let first = tighten((0.25, 1.0), (0.0, 1.0));
    let second = tighten((0.25, 0.75), (0.5, 1.0));
    let batch: [Option<&Model>; 4] = [Some(&first), Some(&first), Some(&second), None];
    // Distinct consecutive bound sets, counting the resident base set:
    // base->first rebinds, first->first does not, first->second and
    // second->base do.
    let expected_rebinds = [1_usize, 1, 2, 3];
    let columns = LinearProgram::new(&base).unwrap().column_count() as u64;

    let settings = settings(64);
    let mut open_diagnostics = LpDiagnostics::new(true, true);
    let mut session = TunedSession::open(
        Rc::clone(&context),
        settings,
        execution(),
        base.clone(),
        &mut open_diagnostics,
    )
    .unwrap();
    let open = open_diagnostics.execution.clone().unwrap();
    let mut previous_variant_record = None;
    for (k, variant) in batch.iter().enumerate() {
        let mut diagnostics = LpDiagnostics::new(true, true);
        let record = session
            .solve(
                *variant,
                &options(),
                &CancellationToken::new(),
                &mut diagnostics,
            )
            .unwrap();
        assert_eq!(
            session.residency().bound_rebinds(),
            expected_rebinds[k],
            "rebinds after solve {k}"
        );
        let rebound_this_solve = k == 0 || expected_rebinds[k] != expected_rebinds[k - 1];
        let solved = variant.unwrap_or(&base);
        let (fresh_record, fresh_diagnostics) = fresh_tuned(&context, solved, settings);
        let mut actual = record.clone();
        actual.elapsed_ms = 0;
        let mut expected = fresh_record.clone();
        expected.elapsed_ms = 0;
        assert_eq!(actual, expected, "record {k}");
        assert_eq!(
            comparable(&diagnostics),
            comparable(&fresh_diagnostics),
            "diagnostics {k}"
        );
        let (rebind_calls, rebind_bytes) = if rebound_this_solve {
            (2, 16 * columns)
        } else {
            (0, 0)
        };
        assert_counter_partition(
            diagnostics.execution.as_ref().unwrap(),
            &open,
            fresh_diagnostics.execution.as_ref().unwrap(),
            rebind_calls,
            rebind_bytes,
        );
        // The variant contract's prefix property starts at bitwise-repeatable
        // solves: two solves of one materialized variant agree exactly.
        if k == 1 {
            let mut repeated = record.clone();
            repeated.elapsed_ms = 0;
            assert_eq!(
                &repeated,
                previous_variant_record
                    .as_ref()
                    .expect("the first variant solve"),
                "repeated solves of one variant are bitwise identical"
            );
        }
        if k == 0 {
            let mut first_record = record;
            first_record.elapsed_ms = 0;
            previous_variant_record = Some(first_record);
        }
    }
    assert_eq!(session.residency().uploads(), 1);
    assert_eq!(session.residency().bound_rebinds(), 3);
}

/// Requirement 11: a variant that is not bounds-only — unknown variable IDs,
/// a perturbed coefficient, a changed domain — is refused before any
/// allocation or upload, and the refusal does not poison the session.
#[test]
fn session_refuses_matrix_mismatch_and_unknown_variable() {
    let Some(context) = device("session_refuses_matrix_mismatch_and_unknown_variable") else {
        return;
    };
    let base = model();
    let mut session = {
        let mut diagnostics = LpDiagnostics::new(true, true);
        TunedSession::open(
            Rc::clone(&context),
            settings(64),
            execution(),
            base.clone(),
            &mut diagnostics,
        )
        .unwrap()
    };
    let mut unknown_document = base.document().clone();
    unknown_document.variables.push(Variable {
        id: 99,
        domain: Domain::Continuous,
        lower: finite(0.0),
        upper: finite(1.0),
    });
    let unknown = Model::new(unknown_document).unwrap();
    let mut perturbed_document = base.document().clone();
    perturbed_document.constraints[0].terms[0].coefficient = 1.0000000000000002;
    let perturbed = Model::new(perturbed_document).unwrap();
    let mut discrete_document = base.document().clone();
    discrete_document.variables[0].domain = Domain::Binary;
    let discrete = Model::new(discrete_document).unwrap();
    for bad in [&unknown, &perturbed, &discrete] {
        let mut diagnostics = LpDiagnostics::new(true, true);
        let error = session
            .solve(
                Some(bad),
                &options(),
                &CancellationToken::new(),
                &mut diagnostics,
            )
            .unwrap_err();
        assert_eq!(error.kind, ErrorKind::Unsupported, "{error}");
        let allocations = diagnostics
            .execution
            .as_ref()
            .map_or(0, |counters| counters.allocations);
        assert_eq!(allocations, 0, "a refused variant must not allocate");
    }
    assert!(session.poisoned().is_none(), "a refusal is not a fault");
    let mut diagnostics = LpDiagnostics::new(true, true);
    session
        .solve(
            None,
            &options(),
            &CancellationToken::new(),
            &mut diagnostics,
        )
        .expect("the session still solves after refusals");
}

/// Requirement 13: a fault poisons the session, later solves are refused so
/// the driver records them `not_attempted`, and completed records are intact.
///
/// The session poisons itself on any device fault `solve` observes; a fault
/// the driver observes between solves is injected through
/// `TunedSession::poison`. Provoking a genuine sticky fault would corrupt the
/// device, which state/known-failures.md records as the standing limit of
/// fault-path coverage; what this test exercises is the poisoning state
/// machine, on both sides of the refusal.
#[test]
fn session_fault_poisons_and_preserves_earlier_records() {
    let Some(context) = device("session_fault_poisons_and_preserves_earlier_records") else {
        return;
    };
    let mut open_diagnostics = LpDiagnostics::new(true, true);
    let mut session = TunedSession::open(
        Rc::clone(&context),
        settings(64),
        execution(),
        model(),
        &mut open_diagnostics,
    )
    .unwrap();
    let mut first_diagnostics = LpDiagnostics::new(true, true);
    let first = session
        .solve(
            None,
            &options(),
            &CancellationToken::new(),
            &mut first_diagnostics,
        )
        .unwrap();
    assert!(first.candidate.is_some());
    let launches = session.residency().launches();

    session.poison("injected fault after solve 1");
    for _ in [2, 3] {
        let mut diagnostics = LpDiagnostics::new(true, true);
        let error = session
            .solve(
                None,
                &options(),
                &CancellationToken::new(),
                &mut diagnostics,
            )
            .unwrap_err();
        assert_eq!(error.kind, ErrorKind::Backend, "{error}");
        assert!(
            error.message.contains("injected fault after solve 1"),
            "the refusal must name the fault: {error}"
        );
        let allocations = diagnostics
            .execution
            .as_ref()
            .map_or(0, |counters| counters.allocations);
        assert_eq!(allocations, 0, "a poisoned session allocates nothing");
    }
    assert_eq!(
        session.residency().launches(),
        launches,
        "a poisoned session is not launched into again"
    );
    assert_eq!(session.poisoned(), Some("injected fault after solve 1"));
    // Solve 1's record is a value the caller holds; nothing about the fault
    // reaches back into it.
    let mut retained = first.clone();
    retained.elapsed_ms = 0;
    let (fresh_record, _) = fresh_tuned(&context, &model(), settings(64));
    let mut expected = fresh_record;
    expected.elapsed_ms = 0;
    assert_eq!(retained, expected, "the completed record is intact");
}

/// Requirement 14: cancellation is observed between solves; records completed
/// before cancellation are retained, and cancellation is not a fault.
#[test]
fn session_cancellation_between_solves_retains_completed_records() {
    let Some(context) = device("session_cancellation_between_solves_retains_completed_records")
    else {
        return;
    };
    let mut open_diagnostics = LpDiagnostics::new(true, true);
    let mut session = TunedSession::open(
        Rc::clone(&context),
        settings(64),
        execution(),
        model(),
        &mut open_diagnostics,
    )
    .unwrap();
    let cancel = CancellationToken::new();
    let mut first_diagnostics = LpDiagnostics::new(true, true);
    let first = session
        .solve(None, &options(), &cancel, &mut first_diagnostics)
        .unwrap();
    assert!(first.candidate.is_some());
    let launches = session.residency().launches();
    assert!(launches > 0);

    cancel.cancel();
    for _ in [2, 3] {
        let mut diagnostics = LpDiagnostics::new(true, true);
        let record = session
            .solve(None, &options(), &cancel, &mut diagnostics)
            .unwrap();
        assert_eq!(record.termination, Termination::Interrupted);
        assert!(record.candidate.is_none());
        assert_eq!(diagnostics.iterations, Some(0));
        assert!(
            session.poisoned().is_none(),
            "cancellation is not a fault (requirement 13)"
        );
    }
    assert_eq!(
        session.residency().launches(),
        launches,
        "a solve cancelled before its first chunk launches nothing"
    );
    assert!(
        first.candidate.is_some(),
        "the completed record is retained"
    );
}

/// Requirements 6, 12 and 13: admission and the invariant upload happen once,
/// at open; solves allocate and upload working state only.
#[test]
fn session_memory_admission_once() {
    let Some(context) = device("session_memory_admission_once") else {
        return;
    };
    // Admission is decided before the code object is read and before any
    // allocation: a budget below the requirement refuses open with the
    // existing message, and no counter has moved.
    let mut refused_diagnostics = LpDiagnostics::new(true, true);
    refused_diagnostics.device_buffer_limit_bytes = Some(1);
    let error = TunedSession::open(
        Rc::clone(&context),
        settings(64),
        execution(),
        model(),
        &mut refused_diagnostics,
    )
    .err()
    .expect("a budget below the requirement refuses open");
    assert_eq!(error.kind, ErrorKind::Backend, "{error}");
    assert!(error.message.contains("buffer budget"), "{error}");
    assert!(
        refused_diagnostics.execution.is_none(),
        "a refused open mints no counters, so none can have moved"
    );

    let mut open_diagnostics = LpDiagnostics::new(true, true);
    let mut session = TunedSession::open(
        Rc::clone(&context),
        settings(64),
        execution(),
        model(),
        &mut open_diagnostics,
    )
    .unwrap();
    let open = open_diagnostics.execution.clone().unwrap();
    let program = LinearProgram::new(&model()).unwrap();
    assert_eq!(
        session.residency().requirement().memory_bytes,
        optimizer_lp_cuda::tuned::peak_buffer_bytes(&program, execution()).unwrap(),
        "the admitted requirement is the exact buffer peak"
    );
    assert_eq!(
        open_diagnostics.device_buffer_peak_bytes,
        Some(open.allocated_bytes)
    );
    // The invariant set: eleven buffers, uploaded once.
    assert_eq!(open.allocations, 11);
    assert_eq!(open.upload_calls, 11);
    // model(): 2 nonzeros, 2 columns, 1 row, everything non-empty. Twelve f64
    // slots (2+2 matrix values, 2 objective, 2+2 column bounds, 1+1 row
    // bounds) plus nine u32 slots (2+2 minor indices, 1+1 row offsets, 2+1
    // column offsets): 12*8 + 9*4 = 132 bytes.
    assert_eq!(open.allocated_bytes, 132);
    assert_eq!(open.upload_bytes, 132);
    for _ in 0..3 {
        let mut diagnostics = LpDiagnostics::new(true, true);
        session
            .solve(
                None,
                &options(),
                &CancellationToken::new(),
                &mut diagnostics,
            )
            .unwrap();
        let counters = diagnostics.execution.unwrap();
        // The fused working set is five buffers of 3 columns' + 2 rows'
        // f64s, freshly allocated per solve; the invariant set is never
        // allocated or uploaded again.
        assert_eq!(counters.allocations, 5);
        assert_eq!(counters.allocated_bytes, 64);
    }
    assert_eq!(session.residency().uploads(), 1);
    assert_eq!(session.residency().bound_rebinds(), 0);
}

/// The pinned research execution identity, as the research suite builds it.
#[cfg(feature = "precision-research")]
fn research_diagnostics(mode: optimizer_lp::research::Mode) -> LpDiagnostics {
    let mut execution = execution();
    execution.fusion = if mode.fused() {
        optimizer_core::Fp64Fusion::PrimalDual
    } else {
        optimizer_core::Fp64Fusion::Separate
    };
    let mut diagnostics = LpDiagnostics::new(true, true);
    diagnostics.execution = Some(LpExecutionDiagnostics::new(execution));
    diagnostics
}

/// One fresh research run of `steps` steps, driven exactly as the existing
/// research suite drives it, returning the final state and the executor's
/// constructor counters.
#[cfg(feature = "precision-research")]
fn fresh_research(
    context: &Rc<Context>,
    program: &LinearProgram,
    mode: optimizer_lp::research::Mode,
    settings: LpSettings,
    image: &[u8],
    steps: u64,
) -> (optimizer_lp::control::Fp64State, LpExecutionDiagnostics) {
    use optimizer_lp::control::Fp64Controller;
    use optimizer_lp::research::{Operator, step};
    use optimizer_lp_cuda::research::ResearchExecutor;
    let mut engine = Engine::new(program, settings);
    let operator = Operator::new(&engine, mode).unwrap();
    engine.restrict_step(operator.step).unwrap();
    let mut diagnostics = research_diagnostics(mode);
    // The constructor counters carry the image identity, as lp_research's do.
    diagnostics.execution.as_mut().unwrap().code_object_sha256 =
        Some(optimizer_core::sha256::hex(image));
    let mut executor = ResearchExecutor::new(
        Rc::clone(context),
        &engine,
        &operator,
        image,
        &mut diagnostics,
    )
    .unwrap();
    let constructor = diagnostics.execution.clone().unwrap();
    let mut control = Fp64Controller::new(&engine);
    for _ in 0..steps {
        let (x, y) = step(&engine, control.state(), &operator).unwrap();
        assert_eq!(
            executor
                .advance(
                    &mut control,
                    1,
                    engine.step(),
                    diagnostics.execution.as_mut().unwrap()
                )
                .unwrap(),
            None
        );
        control.commit_steps(1).unwrap();
        assert_eq!(control.state().primal, x, "primal");
        assert_eq!(control.state().dual, y, "dual");
        if control.check_pending() {
            control.continue_after_check();
        }
    }
    (control.state().clone(), constructor)
}

/// Requirements 5 and 15 for the research path: batch solves with a resident
/// executor are bitwise the fresh research solves, which are the CPU oracle's.
#[cfg(feature = "precision-research")]
#[test]
fn session_research_batch_matches_fresh_and_cpu_oracle() {
    use optimizer_lp::control::Fp64Controller;
    use optimizer_lp::research::Mode;
    use optimizer_lp_cuda::research::{ResearchSession, code_object_path};
    let Some(context) = device("session_research_batch_matches_fresh_and_cpu_oracle") else {
        return;
    };
    let image = std::fs::read(code_object_path()).unwrap();
    let model = model();
    let program = LinearProgram::new(&model).unwrap();
    for mode in [Mode::IntguardFp64, Mode::FusedFp64] {
        let mut open_diagnostics = LpDiagnostics::new(true, false);
        let mut session = ResearchSession::open(
            Rc::clone(&context),
            model.clone(),
            LpSettings::published(64, 8),
            mode,
            image.clone(),
            &mut open_diagnostics,
        )
        .unwrap();
        assert!(
            session
                .setup()
                .phases_ns
                .contains_key("research_preparation"),
            "research preparation is a setup phase"
        );
        let open = open_diagnostics.execution.clone().unwrap();
        let mut states = Vec::new();
        for _ in 0..3 {
            let (fresh_state, constructor) = fresh_research(
                &context,
                &program,
                mode,
                LpSettings::published(64, 8),
                &image,
                40,
            );
            assert_eq!(
                constructor, open,
                "the session open performs exactly the fresh construction"
            );
            let mut counters = session.fresh_counters();
            let solve = session.prepare_solve(None, &mut counters).unwrap();
            let mut control = Fp64Controller::new(&solve.engine);
            for _ in 0..40 {
                assert_eq!(
                    solve
                        .executor
                        .advance(&mut control, 1, solve.engine.step(), &mut counters)
                        .unwrap(),
                    None
                );
                control.commit_steps(1).unwrap();
                if control.check_pending() {
                    control.continue_after_check();
                }
            }
            assert_eq!(
                counters.kernel_launches,
                40 * mode.launches_per_step(),
                "per-solve launch count"
            );
            for (actual, expected) in [
                (&control.state().primal, &fresh_state.primal),
                (&control.state().dual, &fresh_state.dual),
            ] {
                assert_eq!(
                    actual.iter().map(|v| v.to_bits()).collect::<Vec<_>>(),
                    expected.iter().map(|v| v.to_bits()).collect::<Vec<_>>(),
                    "{mode:?} batch solve is bitwise the fresh solve"
                );
            }
            states.push((control.state().primal.clone(), control.state().dual.clone()));
        }
        for later in states.iter().skip(1) {
            assert_eq!(later, &states[0], "{mode:?} repeat solves agree bitwise");
        }
    }
}

/// Requirement 10 for the research path: a tripped guard in one solve is
/// re-zeroed — as a counted upload — before the next, which starts clean and
/// is bitwise unaffected.
///
/// The operator is resident from open, so the existing `fill(f64::MAX)`
/// injection lands on the per-solve controller state instead: a dual of
/// `f64::MAX` against wide_model's greater-than-one coefficients overflows
/// the first sparse product, which is the same guard the fresh-path test
/// trips through the operator.
#[cfg(feature = "precision-research")]
#[test]
fn session_research_guard_slots_rezero_between_solves() {
    use optimizer_lp::control::Fp64Controller;
    use optimizer_lp::research::Mode;
    use optimizer_lp_cuda::research::{ResearchSession, code_object_path};
    let Some(context) = device("session_research_guard_slots_rezero_between_solves") else {
        return;
    };
    let image = std::fs::read(code_object_path()).unwrap();
    let model = wide_model(65);
    let program = LinearProgram::new(&model).unwrap();
    for mode in [Mode::IntguardFp64, Mode::FusedFp64] {
        let mut session = ResearchSession::open(
            Rc::clone(&context),
            model.clone(),
            LpSettings::published(64, 8),
            mode,
            image.clone(),
            &mut LpDiagnostics::new(true, false),
        )
        .unwrap();
        {
            let mut counters = session.fresh_counters();
            let solve = session.prepare_solve(None, &mut counters).unwrap();
            assert_eq!(
                counters.upload_calls, 1,
                "begin_solve re-zeroes the guard slots as one counted upload"
            );
            let mut control = Fp64Controller::new(&solve.engine);
            control.buffers().1.fill(f64::MAX);
            let mut tripped = None;
            for _ in 0..4 {
                match solve
                    .executor
                    .advance(&mut control, 1, solve.engine.step(), &mut counters)
                    .unwrap()
                {
                    Some(reason) => {
                        tripped = Some(reason);
                        break;
                    }
                    None => control.commit_steps(1).unwrap(),
                }
            }
            let reason = tripped.expect("the injected state must trip a guard");
            assert!(reason.contains("bits_"), "{mode:?}: {reason}");
        }
        // The reset's zeroed guard slots are a counted per-solve upload.
        let mut counters = session.fresh_counters();
        let solve = session.prepare_solve(None, &mut counters).unwrap();
        assert_eq!(
            counters.upload_calls, 1,
            "begin_solve re-zeroes the guard slots as one counted upload"
        );
        let mut control = Fp64Controller::new(&solve.engine);
        for _ in 0..40 {
            assert_eq!(
                solve
                    .executor
                    .advance(&mut control, 1, solve.engine.step(), &mut counters)
                    .unwrap(),
                None,
                "{mode:?} solve 2 must start with clean guards"
            );
            control.commit_steps(1).unwrap();
            if control.check_pending() {
                control.continue_after_check();
            }
        }
        assert_eq!(solve.executor.vector_tail_units, 0, "{mode:?}");
        let (fresh_state, _) = fresh_research(
            &context,
            &program,
            mode,
            LpSettings::published(64, 8),
            &image,
            40,
        );
        for (actual, expected) in [
            (&control.state().primal, &fresh_state.primal),
            (&control.state().dual, &fresh_state.dual),
        ] {
            assert_eq!(
                actual.iter().map(|v| v.to_bits()).collect::<Vec<_>>(),
                expected.iter().map(|v| v.to_bits()).collect::<Vec<_>>(),
                "{mode:?} solve 2 is bitwise unaffected by solve 1's tripped guard"
            );
        }
    }
}
