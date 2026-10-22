//! ADR-0039 leased device differentials; ordinary CPU gates explicitly skip.
#![cfg(feature = "precision-research")]
use optimizer_core::{CancellationToken, LpSettings, Model};
use optimizer_lp::{
    Engine, LinearProgram,
    assess::{Arithmetic, Policy},
    precision::PrecisionOperator,
};
use std::rc::Rc;
fn context() -> Option<Rc<optimizer_cuda_sys::Context>> {
    if std::env::var("AI_OPTIMIZER_GPU").ok().as_deref() != Some("1") {
        eprintln!("SKIP assessment device acceptance: opt-in required");
        return None;
    }
    assert_eq!(
        std::env::var("AI_OPTIMIZER_GPU_LEASE").unwrap(),
        "inherited"
    );
    Some(Rc::new(
        optimizer_cuda_sys::Context::create(&std::env::var("CUDA_VISIBLE_DEVICES").unwrap())
            .unwrap(),
    ))
}
fn compare(work: u64, smoke: bool) {
    let Some(context) = context() else {
        return;
    };
    let model = Model::from_json(include_bytes!("../../../examples/lp-model-v1.json")).unwrap();
    let p = LinearProgram::new(&model).unwrap();
    for arithmetic in [Arithmetic::TunedFp64, Arithmetic::AccumulationFp32] {
        let mut engine = Engine::new(&p, LpSettings::published(work, 200));
        let operator = if arithmetic == Arithmetic::AccumulationFp32 {
            Some(PrecisionOperator::new(&engine, &arithmetic.precision()).unwrap())
        } else {
            None
        };
        if let Some(op) = &operator {
            engine.restrict_step(op.step).unwrap();
        }
        let path = if arithmetic == Arithmetic::TunedFp64 {
            optimizer_lp_cuda::tuned::code_object_path()
        } else {
            optimizer_lp_cuda::precision::code_object_path()
        };
        let image = std::fs::read(&path).unwrap();
        let mut endpoints = Vec::new();
        for policy in [Policy::Fixed200, Policy::Bounded800] {
            let (device, d) = optimizer_lp_cuda::assess::execute(
                Rc::clone(&context),
                &engine,
                arithmetic,
                operator.as_ref(),
                policy,
                true,
                &image,
                &path,
                1 << 30,
                &CancellationToken::new(),
                None,
                |_| false,
            )
            .unwrap();
            let cpu = optimizer_lp::assess::run_cpu(
                &engine,
                arithmetic,
                policy,
                true,
                &CancellationToken::new(),
                None,
                |_| false,
            );
            assert_eq!(device.frames, cpu.frames);
            assert_eq!(device.point, cpu.point);
            assert_eq!(device.physical_steps, Some(work));
            assert_eq!(device.status, "iteration_limit");
            assert!(d.execution.as_ref().unwrap().kernel_launches > 0);
            endpoints.push(device);
        }
        assert_eq!(endpoints[0].point, endpoints[1].point);
        assert_eq!(endpoints[0].frames, endpoints[1].frames);
        if !smoke {
            assert!(endpoints[0].assessments > endpoints[1].assessments);
        }
    }
}
#[test]
fn assess_sanitizer_smoke() {
    compare(201, true);
}
#[test]
fn assess_policy_and_cpu_trajectories_match() {
    compare(1801, false);
}
#[test]
fn assess_cancelled_and_deadline_paths_launch_no_work() {
    let Some(context) = context() else {
        return;
    };
    let m = Model::from_json(include_bytes!("../../../examples/lp-model-v1.json")).unwrap();
    let p = LinearProgram::new(&m).unwrap();
    let e = Engine::new(&p, LpSettings::published(201, 200));
    let path = optimizer_lp_cuda::tuned::code_object_path();
    let image = std::fs::read(&path).unwrap();
    let cancel = CancellationToken::new();
    cancel.cancel();
    for (token, deadline, stop) in [
        (&cancel, None, "interrupted"),
        (
            &CancellationToken::new(),
            Some(std::time::Instant::now()),
            "time_limit",
        ),
    ] {
        let (o, d) = optimizer_lp_cuda::assess::execute(
            Rc::clone(&context),
            &e,
            Arithmetic::TunedFp64,
            None,
            Policy::Bounded800,
            false,
            &image,
            &path,
            1 << 30,
            token,
            deadline,
            |_| true,
        )
        .unwrap();
        assert_eq!(o.status, stop);
        assert_eq!(o.physical_steps, Some(0));
        assert_eq!(d.execution.unwrap().kernel_launches, 0);
    }
}
