//! Adaptive execution reuses unchanged precision kernels and one active residency.
use optimizer_core::{CancellationToken, LpAdaptiveSettings, LpDiagnostics};
use optimizer_cuda_sys::{Context, DeviceError};
use optimizer_lp::{
    adaptive::{PreparedAdaptive, run},
    pdhg::Engine,
};
use std::{rc::Rc, time::Instant};

#[allow(clippy::too_many_arguments)]
pub(crate) fn iterate(
    context: Rc<Context>,
    engine: &mut Engine<'_>,
    settings: LpAdaptiveSettings,
    image: &[u8],
    cancel: &CancellationToken,
    d: &mut LpDiagnostics,
    check: impl FnMut(&[f64], &[f64], &mut LpDiagnostics) -> bool,
    deadline: Option<Instant>,
) -> Result<(Vec<f64>, Vec<f64>, u64), DeviceError> {
    let phase = d.start();
    let prepared = PreparedAdaptive::new(engine, &settings);
    d.finish("adaptive_preparation", phase);
    let peak = settings
        .ladder
        .iter()
        .map(|r| crate::precision::peak_buffer_bytes(engine.program(), &r.precision()))
        .collect::<Result<Vec<_>, _>>()?
        .into_iter()
        .max()
        .unwrap_or(0);
    let (free, _) = context.memory_info()?;
    if peak > free || d.device_buffer_limit_bytes.is_some_and(|v| peak > v) {
        return Err(DeviceError::Unsupported(format!(
            "adaptive device memory: {peak} bytes"
        )));
    }
    d.device_buffer_peak_bytes = Some(peak);
    let mut active = None;
    let mut executor = None;
    run(
        engine,
        &prepared,
        settings.clone(),
        cancel,
        d,
        deadline,
        |index, control, count, d| {
            if active != Some(index) {
                // Drop the previous residency before admitting the next: allocated_bytes
                // is cumulative, while device_buffer_peak_bytes is the admitted maximum.
                drop(executor.take());
                let phase = d.start();
                executor = Some(crate::precision::PrecisionExecutor::new(
                    Rc::clone(&context),
                    engine,
                    prepared.operators[index].as_ref().expect("executable rung"),
                    settings.ladder[index].precision(),
                    image,
                    d,
                )?);
                d.device_buffer_peak_bytes = Some(peak);
                d.finish("invariant_allocation_upload", phase);
                active = Some(index);
            }
            let phase = d.start();
            let result = executor
                .as_mut()
                .expect("active precision residency")
                .advance(
                    control,
                    count,
                    engine.step(),
                    d.execution.as_mut().expect("explicit execution"),
                );
            d.finish("kernels_and_synchronization", phase);
            result
        },
        check,
    )
}
