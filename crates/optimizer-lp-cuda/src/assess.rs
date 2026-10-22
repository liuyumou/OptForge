//! ADR-0039 research scheduling over unchanged leased tuned/precision executors.
#![allow(missing_docs)]
use optimizer_core::{
    CancellationToken, Fp64ExecutionSettings, LpDiagnostics, LpExecutionDiagnostics,
};
use optimizer_cuda_sys::Context;
use optimizer_lp::{
    Engine,
    assess::{Arithmetic, Outcome, Point, Policy},
    precision::PrecisionOperator,
};
use std::{path::Path, rc::Rc, time::Instant};

pub fn execution_settings() -> Fp64ExecutionSettings {
    let mut s =
        Fp64ExecutionSettings::from_json(include_bytes!("../../../examples/lp-execution-v1.json"))
            .expect("published execution settings");
    s.fusion = optimizer_core::Fp64Fusion::Separate;
    s
}
#[allow(clippy::too_many_arguments)]
pub fn execute(
    context: Rc<Context>,
    engine: &Engine<'_>,
    arithmetic: Arithmetic,
    operator: Option<&PrecisionOperator>,
    policy: Policy,
    diagnostic: bool,
    image: &[u8],
    image_path: &Path,
    cap: u64,
    cancel: &CancellationToken,
    deadline: Option<Instant>,
    assess: impl FnMut(&Point) -> bool,
) -> Result<(Outcome, LpDiagnostics), String> {
    if std::env::var("AI_OPTIMIZER_GPU_LEASE").ok().as_deref() != Some("inherited") {
        return Err("shared host lease required".into());
    }
    let settings = execution_settings();
    let mut d = LpDiagnostics::new(true, diagnostic);
    d.execution = Some(LpExecutionDiagnostics::new(settings));
    d.device_buffer_limit_bytes = Some(cap);
    let peak = match arithmetic {
        Arithmetic::TunedFp64 => crate::tuned::peak_buffer_bytes(engine.program(), settings),
        Arithmetic::AccumulationFp32 => {
            crate::precision::peak_buffer_bytes(engine.program(), &arithmetic.precision())
        }
    }
    .map_err(|e| e.to_string())?;
    if peak > cap || peak > context.memory_info().map_err(|e| e.to_string())?.0 {
        return Err("assessment device memory admission".into());
    }
    d.device_buffer_peak_bytes = Some(peak);
    let outcome = match arithmetic {
        Arithmetic::TunedFp64 => {
            let (rows, cols) = engine.scaled_matrix();
            let residency = crate::LpResidency::open_for_execution(
                context,
                engine.program(),
                rows,
                cols,
                engine.scaled_objective(),
                engine.scaled_row_bounds(),
                engine.scaled_column_bounds(),
                image_path,
                Some(settings),
                Some(image),
                d.execution.as_mut(),
            )
            .map_err(|e| format!("device:{e}"))?;
            let mut executor = crate::tuned::TunedExecutor::new(&residency, settings)
                .map_err(|e| format!("device:{e}"))?;
            optimizer_lp::assess::run(
                engine,
                policy,
                diagnostic,
                cancel,
                deadline,
                200,
                |c, chunk| {
                    let (generation, restarts, since, weight) = (
                        c.generation(),
                        c.state().restarts,
                        c.state().since_restart,
                        c.state().weight,
                    );
                    let (x, y, ax, ay) = c.buffers();
                    let result = executor
                        .advance(
                            x,
                            y,
                            ax,
                            ay,
                            generation,
                            restarts,
                            since,
                            chunk,
                            engine.step(),
                            weight,
                            |_| {
                                cancel.is_cancelled()
                                    || deadline.is_some_and(|d| Instant::now() >= d)
                            },
                            &mut d,
                        )
                        .map_err(|e| format!("device:{e}"))?;
                    c.commit_steps(result.completed).map_err(str::to_string)?;
                    Ok(())
                },
                assess,
            )
        }
        Arithmetic::AccumulationFp32 => {
            let op = operator.ok_or("prepared precision operator required")?;
            let mut executor = crate::precision::PrecisionExecutor::new(
                context,
                engine,
                op,
                arithmetic.precision(),
                image,
                &mut d,
            )
            .map_err(|e| format!("device:{e}"))?;
            optimizer_lp::assess::run(
                engine,
                policy,
                diagnostic,
                cancel,
                deadline,
                64,
                |c, chunk| {
                    let primal_step = engine.step() / c.state().weight;
                    let dual_step = engine.step() * c.state().weight;
                    if !primal_step.is_finite()
                        || !dual_step.is_finite()
                        || primal_step == 0.0
                        || dual_step == 0.0
                    {
                        return Err("preflight:update_step_range".into());
                    }
                    let guard = executor
                        .advance(
                            c,
                            chunk,
                            engine.step(),
                            d.execution.as_mut().expect("execution counters"),
                        )
                        .map_err(|e| format!("device:{e}"))?;
                    if let Some(reason) = guard {
                        c.charge_extra(chunk)?;
                        return Err(reason);
                    }
                    c.commit_steps(chunk).map_err(str::to_string)?;
                    Ok(())
                },
                assess,
            )
        }
    };
    if let Some(counters) = &mut d.execution {
        counters.code_object_sha256 = None;
    }
    Ok((outcome, d))
}
