//! Bounded resident mixed-precision execution, separate from legacy/tuned FP64.
use optimizer_core::{
    CancellationToken, LpDiagnostics, LpExecutionDiagnostics, LpPrecisionSettings, LpWidth,
};
use optimizer_cuda_sys::{
    Argument as A, Context, DeviceBuffer, DeviceError, LaunchConfig, Module, Stream, launch,
};
use optimizer_lp::{
    LinearProgram, control::Fp64Controller, pdhg::Engine, precision::PrecisionOperator,
};
use std::{path::PathBuf, rc::Rc, time::Instant};

/// Provisioned independently of ordinary Cargo builds.
#[must_use]
pub fn code_object_path() -> PathBuf {
    crate::tuned::code_object_path().with_file_name("lp_pdhg_precision.cubin")
}
enum Buffer {
    F64(DeviceBuffer<f64>),
    F32(DeviceBuffer<f32>),
}
impl Buffer {
    fn ptr(&self) -> A {
        A::DevicePtr(match self {
            Self::F64(b) => b.as_device_ptr(),
            Self::F32(b) => b.as_device_ptr(),
        })
    }
    fn upload(
        &mut self,
        v: &[f64],
        s: &Stream,
        c: &mut LpExecutionDiagnostics,
    ) -> Result<(), DeviceError> {
        if v.is_empty() {
            return Ok(());
        }
        let bytes = match self {
            Self::F64(b) => {
                b.copy_from(v, s)?;
                8
            }
            Self::F32(b) => {
                let data = v.iter().map(|&x| x as f32).collect::<Vec<_>>();
                b.copy_from(&data, s)?;
                4
            }
        };
        c.upload_calls += 1;
        c.upload_bytes += v.len() as u64 * bytes;
        c.synchronizations += 1;
        Ok(())
    }
    fn read(
        &self,
        n: usize,
        s: &Stream,
        c: &mut LpExecutionDiagnostics,
    ) -> Result<Vec<f64>, DeviceError> {
        if n == 0 {
            return Ok(vec![]);
        }
        let (out, bytes) = match self {
            Self::F64(b) => {
                let mut v = vec![0.0; n];
                b.copy_to(&mut v, s)?;
                (v, 8)
            }
            Self::F32(b) => {
                let mut v = vec![0.0_f32; n];
                b.copy_to(&mut v, s)?;
                (v.into_iter().map(f64::from).collect(), 4)
            }
        };
        c.readback_calls += 1;
        c.readback_bytes += n as u64 * bytes;
        c.synchronizations += 1;
        Ok(out)
    }
}
const X: usize = 7;
const Y: usize = 8;
const AX: usize = 9;
const AY: usize = 10;
/// One-solve owned precision residency. All driver interaction uses the existing safe boundary.
pub struct PrecisionExecutor {
    module: Module,
    stream: Stream,
    b: Vec<Buffer>,
    i: Vec<DeviceBuffer<u32>>,
    n: usize,
    m: usize,
    settings: LpPrecisionSettings,
    loaded: Option<(u64, u64)>,
}
fn shape(p: &LinearProgram, s: &LpPrecisionSettings) -> Vec<(usize, LpWidth)> {
    use LpWidth::F64;
    let n = p.column_count();
    let m = p.row_count();
    let z = p.nonzeros();
    vec![
        (z, s.matrix),
        (z, s.matrix),
        (n, F64),
        (n, F64),
        (n, F64),
        (m, F64),
        (m, F64),
        (n, s.working_state),
        (m, s.working_state),
        (n, s.working_state),
        (m, s.working_state),
        (n, F64),
        (n, F64),
        (n, F64),
        (m, F64),
        (m, F64),
    ]
}
/// Exact allocated device bytes, including empty padding, guards and scratch.
pub fn peak_buffer_bytes(p: &LinearProgram, s: &LpPrecisionSettings) -> Result<u64, DeviceError> {
    let mut total = 0_u64;
    let mut add = |n: usize, w: u64| -> Result<(), DeviceError> {
        total = total
            .checked_add(
                (n.max(1) as u64)
                    .checked_mul(w)
                    .ok_or_else(|| DeviceError::Unsupported("precision memory overflow".into()))?,
            )
            .ok_or_else(|| DeviceError::Unsupported("precision memory overflow".into()))?;
        Ok(())
    };
    for (n, w) in shape(p, s) {
        add(n, if w == LpWidth::F32 { 4 } else { 8 })?;
    }
    let guards = p
        .column_count()
        .checked_add(p.row_count())
        .and_then(|v| v.checked_mul(3))
        .ok_or_else(|| DeviceError::Unsupported("guard memory overflow".into()))?;
    for n in [
        p.nonzeros(),
        p.nonzeros(),
        p.row_count() + 1,
        p.column_count() + 1,
        guards,
    ] {
        add(n, 4)?;
    }
    Ok(total)
}
impl PrecisionExecutor {
    /// Admit every buffer before allocation; the code image was identified before opening.
    pub fn new(
        context: Rc<Context>,
        engine: &Engine<'_>,
        op: &PrecisionOperator,
        settings: LpPrecisionSettings,
        image: &[u8],
        d: &mut LpDiagnostics,
    ) -> Result<Self, DeviceError> {
        let p = engine.program();
        let peak = peak_buffer_bytes(p, &settings)?;
        let device = context.device();
        if (device.capability_major, device.capability_minor) < crate::residency::TARGET_CAPABILITY
        {
            return Err(DeviceError::Unsupported(
                "precision code object capability".into(),
            ));
        }
        if p.column_count() > u32::MAX as usize
            || p.row_count() > u32::MAX as usize
            || p.nonzeros() > u32::MAX as usize
        {
            return Err(DeviceError::Unsupported("precision index range".into()));
        }
        let (free, _) = context.memory_info()?;
        if peak > free || d.device_buffer_limit_bytes.is_some_and(|v| peak > v) {
            return Err(DeviceError::Unsupported(format!(
                "precision device memory: {peak} bytes"
            )));
        }
        let module = context.load_module(image)?;
        let stream = context.stream()?;
        let c = d
            .execution
            .as_mut()
            .expect("explicit execution observations");
        let mut b = Vec::new();
        let (xl, xu) = engine.scaled_column_bounds();
        let (yl, yu) = engine.scaled_row_bounds();
        let data = [
            op.rows.as_slice(),
            op.columns.as_slice(),
            engine.scaled_objective(),
            xl,
            xu,
            yl,
            yu,
        ];
        for (idx, (n, w)) in shape(p, &settings).into_iter().enumerate() {
            let mut buffer = if w == LpWidth::F32 {
                Buffer::F32(context.allocate(n.max(1))?)
            } else {
                Buffer::F64(context.allocate(n.max(1))?)
            };
            c.allocations += 1;
            c.allocated_bytes += n.max(1) as u64 * if w == LpWidth::F32 { 4 } else { 8 };
            // Initialized padding and working buffers make whole-buffer sanitizer reads defined.
            let zero = vec![0.0; n.max(1)];
            buffer.upload(
                if idx < data.len() && !data[idx].is_empty() {
                    data[idx]
                } else {
                    &zero
                },
                &stream,
                c,
            )?;
            b.push(buffer);
        }
        let n = p.column_count();
        let m = p.row_count();
        let ints = [
            p.row_major()
                .entries()
                .map(|(_, v, _)| v)
                .collect::<Vec<_>>(),
            p.column_major().entries().map(|(_, v, _)| v).collect(),
            (0..=m).map(|j| p.row_major().offset(j) as u32).collect(),
            (0..=n).map(|j| p.column_major().offset(j) as u32).collect(),
            vec![0; 3 * (n + m)],
        ];
        let mut i = Vec::new();
        for mut v in ints {
            if v.is_empty() {
                v.push(0)
            }
            let mut buf = context.allocate::<u32>(v.len())?;
            c.allocations += 1;
            c.allocated_bytes += v.len() as u64 * 4;
            buf.copy_from(&v, &stream)?;
            c.upload_calls += 1;
            c.upload_bytes += v.len() as u64 * 4;
            c.synchronizations += 1;
            i.push(buf);
        }
        d.device_buffer_peak_bytes = Some(peak);
        Ok(Self {
            module,
            stream,
            b,
            i,
            n,
            m,
            settings,
            loaded: None,
        })
    }
    /// Execute at most 64 steps; only synchronized, range-clean endpoints are committed.
    pub fn advance(
        &mut self,
        control: &mut Fp64Controller<'_, '_>,
        steps: u64,
        step: f64,
        c: &mut LpExecutionDiagnostics,
    ) -> Result<Option<String>, DeviceError> {
        assert!(steps > 0 && steps <= 64);
        let state = control.state();
        let key = (control.generation(), state.restarts);
        let full = self.loaded.is_none_or(|v| v.0 != key.0);
        let anchors = full || self.loaded.is_none_or(|v| v.1 != key.1);
        for (idx, v, needed) in [
            (X, &state.primal, full),
            (Y, &state.dual, full),
            (AX, &state.anchor_primal, anchors),
            (AY, &state.anchor_dual, anchors),
        ] {
            if needed {
                self.b[idx].upload(v, &self.stream, c)?;
            }
        }
        self.loaded = Some(key);
        let sparse = self.module.function("precision_spmv")?;
        let primal = self.module.function("precision_primal")?;
        let dual = self.module.function("precision_dual")?;
        let store = self.module.function("precision_store")?;
        let sparse_launch = |n: usize| LaunchConfig {
            grid: (n.max(1) as u32).div_ceil(8),
            block: 256,
            shared_memory: 0,
        };
        let vector_launch = |n: usize| LaunchConfig {
            grid: (n.max(1) as u32).div_ceil(256),
            block: 256,
            shared_memory: 0,
        };
        let ip = |j: usize| A::DevicePtr(self.i[j].as_device_ptr());
        let gp = |offset: usize| A::DevicePtr(self.i[4].as_device_ptr() + offset as u64 * 4);
        let flag = |w: LpWidth| A::U32(u32::from(w == LpWidth::F32));
        let n = A::U32(self.n as u32);
        let m = A::U32(self.m as u32);
        let primal_step = step / state.weight;
        let dual_step = step * state.weight;
        if !primal_step.is_finite()
            || !dual_step.is_finite()
            || primal_step == 0.0
            || dual_step == 0.0
        {
            return Ok(Some("update_step_range".into()));
        }
        for t in 0..steps {
            let since = state.since_restart + t;
            let toward = A::F64((since + 1) as f64 / (since + 2) as f64);
            let back = A::F64(1.0 / (since + 2) as f64);
            launch(
                &sparse,
                sparse_launch(self.n),
                &[
                    self.b[1].ptr(),
                    ip(1),
                    ip(3),
                    self.b[Y].ptr(),
                    self.b[11].ptr(),
                    gp(0),
                    n,
                    flag(self.settings.matrix),
                    flag(self.settings.working_state),
                    flag(self.settings.products),
                    flag(self.settings.accumulation),
                ],
                &self.stream,
            )?;
            c.kernel_launches += 1;
            launch(
                &primal,
                vector_launch(self.n),
                &[
                    self.b[X].ptr(),
                    self.b[11].ptr(),
                    self.b[2].ptr(),
                    self.b[3].ptr(),
                    self.b[4].ptr(),
                    self.b[12].ptr(),
                    self.b[13].ptr(),
                    gp(self.n),
                    A::F64(primal_step),
                    n,
                    flag(self.settings.working_state),
                ],
                &self.stream,
            )?;
            c.kernel_launches += 1;
            launch(
                &sparse,
                sparse_launch(self.m),
                &[
                    self.b[0].ptr(),
                    ip(0),
                    ip(2),
                    self.b[13].ptr(),
                    self.b[14].ptr(),
                    gp(2 * self.n),
                    m,
                    flag(self.settings.matrix),
                    A::U32(0),
                    flag(self.settings.products),
                    flag(self.settings.accumulation),
                ],
                &self.stream,
            )?;
            c.kernel_launches += 1;
            launch(
                &dual,
                vector_launch(self.m),
                &[
                    self.b[Y].ptr(),
                    self.b[14].ptr(),
                    self.b[5].ptr(),
                    self.b[6].ptr(),
                    self.b[15].ptr(),
                    gp(2 * self.n + self.m),
                    A::F64(dual_step),
                    m,
                    flag(self.settings.working_state),
                ],
                &self.stream,
            )?;
            c.kernel_launches += 1;
            launch(
                &store,
                vector_launch(self.n),
                &[
                    self.b[X].ptr(),
                    self.b[12].ptr(),
                    self.b[AX].ptr(),
                    gp(2 * (self.n + self.m)),
                    toward,
                    back,
                    n,
                    flag(self.settings.working_state),
                ],
                &self.stream,
            )?;
            c.kernel_launches += 1;
            launch(
                &store,
                vector_launch(self.m),
                &[
                    self.b[Y].ptr(),
                    self.b[15].ptr(),
                    self.b[AY].ptr(),
                    gp(3 * self.n + 2 * self.m),
                    toward,
                    back,
                    m,
                    flag(self.settings.working_state),
                ],
                &self.stream,
            )?;
            c.kernel_launches += 1;
        }
        let mut guards = vec![0_u32; (3 * (self.n + self.m)).max(1)];
        self.i[4].copy_to(&mut guards, &self.stream)?;
        c.readback_calls += 1;
        c.readback_bytes += guards.len() as u64 * 4;
        c.synchronizations += 1;
        if let Some((index, bits)) = guards.iter().enumerate().find(|(_, g)| **g != 0) {
            return Ok(Some(format!("range_guard_slot_{index}_bits_{bits}")));
        }
        let x = self.b[X].read(self.n, &self.stream, c)?;
        let y = self.b[Y].read(self.m, &self.stream, c)?;
        let (cx, cy, _, _) = control.buffers();
        cx.copy_from_slice(&x);
        cy.copy_from_slice(&y);
        Ok(None)
    }
}

/// Run shared control with physical correction accounting and bounded observation.
#[allow(clippy::too_many_arguments)]
pub(crate) fn iterate(
    context: Rc<Context>,
    engine: &mut Engine<'_>,
    settings: LpPrecisionSettings,
    image: &[u8],
    cancel: &CancellationToken,
    d: &mut LpDiagnostics,
    mut check: impl FnMut(&[f64], &[f64], &mut LpDiagnostics) -> bool,
    deadline: Option<Instant>,
) -> Result<(Vec<f64>, Vec<f64>, u64), DeviceError> {
    let preparation = d.start();
    let operator = PrecisionOperator::new(engine, &settings);
    let mut control;
    let mut stop = "iteration_limit";
    let mut assessed = None;
    let mut assessments = 0;
    let mut executor = match operator {
        Ok(op) => {
            engine
                .restrict_step(op.step)
                .expect("admitted restricted step");
            let p = d.precision.as_mut().expect("precision observations");
            p.operator_bounds = Some(op.bounds);
            p.step = Some(op.step);
            p.matrix_max_error = op.max_error;
            p.matrix_subnormals = op.subnormals;
            d.finish("precision_preparation", preparation);
            let phase = d.start();
            let exec = PrecisionExecutor::new(context, engine, &op, settings.clone(), image, d)?;
            d.finish("invariant_allocation_upload", phase);
            Some(exec)
        }
        Err(reason) => {
            d.precision.as_mut().expect("precision observations").guard = Some(reason.into());
            stop = "numerical_failure";
            None
        }
    };
    control = Fp64Controller::new(engine);
    control.set_deadline(deadline);
    while control.remaining() > 0 {
        let Some(executor) = executor.as_mut() else {
            break;
        };
        if cancel.is_cancelled() {
            stop = "interrupted";
            break;
        }
        if control.expired() {
            stop = "time_limit";
            break;
        }
        if settings.working_state == LpWidth::F32
            && let Err(reason) = control.round_working()
        {
            d.precision.as_mut().unwrap().guard = Some(reason.into());
            stop = "numerical_failure";
            break;
        }
        let primal_step = engine.step() / control.state().weight;
        let dual_step = engine.step() * control.state().weight;
        if !primal_step.is_finite()
            || !dual_step.is_finite()
            || primal_step == 0.0
            || dual_step == 0.0
        {
            d.precision.as_mut().unwrap().guard = Some("update_step_range".into());
            stop = "numerical_failure";
            break;
        }
        let until = settings
            .correction_interval
            .map(|k| k - control.state().iterations % k)
            .unwrap_or(u64::MAX);
        let correcting = until == 1;
        if correcting && control.remaining() < 2 {
            break;
        }
        let chunk = control.next_chunk(64).min(if correcting {
            1
        } else {
            until.saturating_sub(1)
        });
        let saved = correcting.then(|| control.state().clone());
        let phase = d.start();
        let result = executor.advance(
            &mut control,
            chunk,
            engine.step(),
            d.execution.as_mut().unwrap(),
        );
        d.finish("kernels_and_synchronization", phase);
        match result {
            Err(error) => {
                d.iterations = None;
                d.control = Some(observations(
                    &control,
                    d,
                    assessments,
                    "device_failure",
                    None,
                ));
                return Err(error);
            }
            Ok(guard) => {
                d.precision.as_mut().unwrap().proposed_steps += chunk;
                if let Some(reason) = guard {
                    control.charge_extra(chunk).expect("admitted rejected work");
                    let p = d.precision.as_mut().unwrap();
                    p.guard = Some(reason);
                    p.rejected_steps += chunk;
                    stop = "numerical_failure";
                    break;
                }
                control.commit_steps(chunk).expect("admitted proposal work");
            }
        }
        if let Some(saved) = saved {
            // Admitted before proposal; cancellation cannot manufacture a corrected endpoint.
            if cancel.is_cancelled() || control.expired() {
                stop = if cancel.is_cancelled() {
                    "interrupted"
                } else {
                    "time_limit"
                };
                break;
            }
            let phase = d.start();
            let corrected = optimizer_lp::precision::correction(engine, &saved);
            control.charge_extra(1).expect("admitted correction work");
            d.precision.as_mut().unwrap().correction_steps += 1;
            match corrected {
                Ok((x, y)) => {
                    let low = control.iterate();
                    let highx = engine.unscale_primal(&x);
                    let highy = engine.unscale_dual(&y);
                    let err = low
                        .primal
                        .iter()
                        .chain(&low.dual)
                        .zip(highx.iter().chain(&highy))
                        .map(|(a, b)| (a - b).abs())
                        .fold(0.0, f64::max);
                    if !err.is_finite() {
                        d.precision.as_mut().unwrap().guard =
                            Some("correction_error_nonfinite".into());
                        stop = "numerical_failure";
                        break;
                    }
                    let p = d.precision.as_mut().unwrap();
                    p.correction_max_error = p.correction_max_error.max(err);
                    control.replace_endpoint(x, y).expect("finite correction");
                }
                Err(reason) => {
                    d.precision.as_mut().unwrap().guard = Some(reason.into());
                    stop = "numerical_failure";
                    break;
                }
            }
            d.finish("fp64_correction", phase);
        }
        if control.check_pending() {
            let point = control.iterate();
            assessments += 1;
            let accept = check(&point.primal, &point.dual, d);
            assessed = Some(point);
            if accept {
                stop = "accepted";
                break;
            }
            let phase = d.start();
            control.continue_after_check();
            d.finish("controller", phase);
        }
    }
    d.iterations = Some(control.physical_iterations());
    d.restarts = Some(control.state().restarts);
    d.kernel_launches = Some(d.execution.as_ref().unwrap().kernel_launches);
    d.control = Some(observations(
        &control,
        d,
        assessments,
        stop,
        Some(control.physical_iterations()),
    ));
    let point = assessed.unwrap_or_else(|| control.iterate());
    Ok((point.primal, point.dual, point.iterations))
}
fn observations(
    c: &Fp64Controller<'_, '_>,
    d: &LpDiagnostics,
    assessments: u64,
    stop: &str,
    physical_iterations: Option<u64>,
) -> optimizer_core::LpControlDiagnostics {
    optimizer_core::LpControlDiagnostics {
        controller: "host-restart-weight-v1".into(),
        logical_iterations: c.state().iterations,
        physical_iterations,
        device_kernel_launches: d.execution.as_ref().unwrap().kernel_launches,
        assessments,
        kkt_evaluations: c.kkt_evaluations(),
        restarts: c.state().restarts,
        weight: c.state().weight,
        stop: stop.into(),
    }
}
