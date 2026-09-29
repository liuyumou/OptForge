use super::*;
use optimizer_core::{Fp64ExecutionSettings, LpAdaptiveSettings, LpDiagnostics};
use optimizer_cuda::setup::{ContextMode, SetupObservation, complete};

#[test]
fn primary_tuned_and_adaptive_match_user_contexts() {
    let Some(control) = device("primary_tuned_and_adaptive_match_user_contexts") else {
        return;
    };
    assert_eq!(
        std::env::var("AI_OPTIMIZER_GPU_LEASE").as_deref(),
        Ok("inherited")
    );
    let uuid = control.device().uuid.clone();
    drop(control);
    let execution = Fp64ExecutionSettings::from_json(include_bytes!(
        "../../../../examples/lp-precision-execution-v1.json"
    ))
    .unwrap();
    for adaptive in [false, true] {
        let mut results = Vec::new();
        for mode in [ContextMode::User, ContextMode::PrimaryExperimental] {
            let observation = SetupObservation::begin().unwrap();
            let context = Rc::new(Context::create_with_mode(&uuid, mode).unwrap());
            let settings = LpSettings::published(80, 10);
            let backend = if adaptive {
                let policy = LpAdaptiveSettings::from_json(include_bytes!(
                    "../../../../examples/lp-adaptive-v1.json"
                ))
                .unwrap();
                CudaLpBackend::open_adaptive(Rc::clone(&context), settings, execution, policy)
            } else {
                CudaLpBackend::open_tuned(Rc::clone(&context), settings, execution)
            }
            .unwrap();
            let mut options = options();
            options.iteration_limit = Some(80);
            let mut diagnostics = LpDiagnostics::new(true, false);
            let mut record = backend
                .solve_with_diagnostics(
                    &model(),
                    &options,
                    &CancellationToken::new(),
                    None,
                    &mut diagnostics,
                )
                .unwrap();
            record.elapsed_ms = 0;
            results.push((
                record.to_json().unwrap(),
                diagnostics.adaptive.clone(),
                diagnostics.iterations,
            ));
            drop(backend);
            drop(context);
            assert!(complete(mode, &observation.finish()));
        }
        assert_eq!(results[0], results[1]);
    }
}

#[test]
fn primary_children_hold_lifetime_owner_until_checked_release() {
    let Some(control) = device("primary_children_hold_lifetime_owner_until_checked_release") else {
        return;
    };
    let uuid = control.device().uuid.clone();
    drop(control);
    use std::sync::{
        Arc,
        atomic::{AtomicBool, Ordering},
    };
    struct Owner(Arc<AtomicBool>);
    impl Drop for Owner {
        fn drop(&mut self) {
            self.0.store(true, Ordering::SeqCst);
        }
    }
    let released = Arc::new(AtomicBool::new(false));
    let additional = Arc::new(AtomicBool::new(false));
    let lock_path = std::env::temp_dir().join(format!(
        "optimizer-primary-owner-{}.lock",
        std::process::id()
    ));
    let cancelled = std::sync::atomic::AtomicBool::new(false);
    let lock = optimizer_cuda::GpuLease::acquire(&lock_path, std::time::Duration::ZERO, &cancelled)
        .unwrap();
    let observation = SetupObservation::begin().unwrap();
    let context = Rc::new(
        Context::create_with_mode(&uuid, ContextMode::PrimaryExperimental)
            .unwrap()
            .with_lifetime_owner(Arc::new(Owner(Arc::clone(&released))))
            .with_lifetime_owner(Arc::new(Owner(Arc::clone(&additional))))
            .with_lifetime_owner(Arc::new(lock)),
    );
    let buffer = context.allocate::<f64>(16).unwrap();
    let stream = context.stream().unwrap();
    let module = context
        .load_module_file(&optimizer_lp_cuda::tuned::code_object_path())
        .unwrap();
    drop(context);
    assert!(!released.load(Ordering::SeqCst));
    assert!(
        optimizer_cuda::GpuLease::acquire(&lock_path, std::time::Duration::ZERO, &cancelled)
            .is_err()
    );
    drop(buffer);
    drop(module);
    assert!(!released.load(Ordering::SeqCst));
    drop(stream);
    assert!(released.load(Ordering::SeqCst));
    assert!(additional.load(Ordering::SeqCst));
    drop(
        optimizer_cuda::GpuLease::acquire(&lock_path, std::time::Duration::ZERO, &cancelled)
            .unwrap(),
    );
    std::fs::remove_file(lock_path).unwrap();
    assert!(complete(
        ContextMode::PrimaryExperimental,
        &observation.finish()
    ));
}

#[test]
fn primary_refuses_live_current_context_without_harming_it() {
    let Some(context) = device("primary_refuses_live_current_context_without_harming_it") else {
        return;
    };
    let uuid = context.device().uuid.clone();
    assert!(Context::create_with_mode(&uuid, ContextMode::PrimaryExperimental).is_err());
    assert!(context.memory_info().is_ok());
}
