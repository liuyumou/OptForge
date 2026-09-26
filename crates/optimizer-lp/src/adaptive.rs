//! Device-independent adaptive windows. Audits guide execution, never certification.
use crate::{
    control::{Fp64Checkpoint, Fp64Controller, Fp64State},
    pdhg::Engine,
    precision::{PrecisionOperator, correction, narrow, step},
};
use optimizer_core::{
    CancellationToken, LpAdaptiveDiagnostics, LpAdaptiveRung, LpAdaptiveSettings,
    LpAdaptiveTransition, LpControlDiagnostics, LpDiagnostics,
};
use std::time::Instant;

/// Canonical prepared ladder, sharing one conservative step for the whole solve.
pub struct PreparedAdaptive {
    /// Failed representations remain explicit and are never executed.
    pub operators: Vec<Result<PrecisionOperator, &'static str>>,
}
impl PreparedAdaptive {
    /// Prepare before constructing the controller; never change its engine later.
    pub fn new(engine: &mut Engine<'_>, settings: &LpAdaptiveSettings) -> Self {
        let operators: Vec<_> = settings
            .ladder
            .iter()
            .map(|r| PrecisionOperator::new(engine, &r.precision()))
            .collect();
        let common = operators
            .iter()
            .filter_map(|op| op.as_ref().ok().map(|o| o.step))
            .fold(engine.step(), f64::min);
        engine
            .restrict_step(common)
            .expect("finite conservative common step");
        Self { operators }
    }
}
/// CPU mirror of a prospective rung, including working-state and anchor narrowing.
pub fn proposal(
    engine: &Engine<'_>,
    state: &Fp64State,
    op: &PrecisionOperator,
    rung: LpAdaptiveRung,
) -> Result<(Vec<f64>, Vec<f64>), &'static str> {
    let mut saved = state.clone();
    if rung == LpAdaptiveRung::WorkingFp32 {
        for v in saved
            .primal
            .iter_mut()
            .chain(&mut saved.dual)
            .chain(&mut saved.anchor_primal)
            .chain(&mut saved.anchor_dual)
        {
            *v = narrow(*v)?;
        }
    }
    let p = rung.precision();
    let (mut x, mut y) = step(
        engine,
        &saved,
        &op.rows,
        &op.columns,
        p.products,
        p.accumulation,
    )?;
    if rung == LpAdaptiveRung::WorkingFp32 {
        for v in x.iter_mut().chain(&mut y) {
            *v = narrow(*v)?;
        }
    }
    Ok((x, y))
}
/// Componentwise original-unit audit. Nonfinite arithmetic always fails.
pub fn audit(
    engine: &Engine<'_>,
    settings: &LpAdaptiveSettings,
    pre: &Fp64State,
    low: (&[f64], &[f64]),
    reference: (&[f64], &[f64]),
    margin: f64,
) -> (bool, f64) {
    let pre_x = engine.unscale_primal(&pre.primal);
    let pre_y = engine.unscale_dual(&pre.dual);
    let low_x = engine.unscale_primal(low.0);
    let low_y = engine.unscale_dual(low.1);
    let ref_x = engine.unscale_primal(reference.0);
    let ref_y = engine.unscale_dual(reference.1);
    let mut pass = true;
    let mut maximum: f64 = 0.0;
    for (before, lo, hi, absolute) in [
        (&pre_x, &low_x, &ref_x, settings.primal_absolute),
        (&pre_y, &low_y, &ref_y, settings.dual_absolute),
    ] {
        if before.len() != lo.len() || lo.len() != hi.len() {
            return (false, maximum);
        }
        for ((&b, &l), &h) in before.iter().zip(lo).zip(hi) {
            let error = (l - h).abs();
            let allowance = margin * (absolute + settings.relative * b.abs().max(h.abs()));
            if error.is_finite() {
                maximum = maximum.max(error);
            }
            pass &= b.is_finite()
                && l.is_finite()
                && h.is_finite()
                && error.is_finite()
                && allowance.is_finite()
                && error <= allowance;
        }
    }
    (pass, maximum)
}
fn restore<'e, 'p>(
    control: &mut Fp64Controller<'e, 'p>,
    checkpoint: &Fp64Checkpoint<'e, 'p>,
    start: u64,
    observations: &mut LpAdaptiveDiagnostics,
) {
    observations.rejected_steps += control.state().iterations - start;
    control.restore(checkpoint).expect("same immutable engine");
}
fn transition(
    control: &Fp64Controller<'_, '_>,
    a: &mut LpAdaptiveDiagnostics,
    index: usize,
    next: Option<usize>,
    reason: &str,
) {
    a.transitions.push(LpAdaptiveTransition {
        iteration: control.state().iterations,
        physical_work: control.physical_iterations(),
        from: a.settings.ladder[index],
        to: next.map(|i| a.settings.ladder[i]),
        reason: reason.into(),
    });
    if let Some(next) = next {
        a.final_rung = a.settings.ladder[next];
    }
}
/// Execute the adaptive policy with a supplied bounded proposal executor.
/// The executor writes the endpoint but does not commit or charge work. A guard
/// means the whole requested chunk completed and was rejected. An error means
/// device work is unknown, and is kept unavailable in final observations.
#[allow(clippy::too_many_arguments)]
pub fn run<E>(
    engine: &Engine<'_>,
    prepared: &PreparedAdaptive,
    settings: LpAdaptiveSettings,
    cancel: &CancellationToken,
    d: &mut LpDiagnostics,
    deadline: Option<Instant>,
    mut advance: impl FnMut(
        usize,
        &mut Fp64Controller<'_, '_>,
        u64,
        &mut LpDiagnostics,
    ) -> Result<Option<String>, E>,
    mut check: impl FnMut(&[f64], &[f64], &mut LpDiagnostics) -> bool,
) -> Result<(Vec<f64>, Vec<f64>, u64), E> {
    let mut a = LpAdaptiveDiagnostics::new(settings.clone());
    a.step = Some(engine.step());
    a.unavailable_rungs = prepared
        .operators
        .iter()
        .map(|v| v.as_ref().err().map(|s| (*s).into()))
        .collect();
    let mut c = Fp64Controller::new(engine);
    c.set_deadline(deadline);
    let mut index = 0;
    let mut clean = 0u64;
    let mut assessments = 0;
    let mut assessed = None;
    let mut error = None;
    let mut stop = "iteration_limit";
    'solve: loop {
        if cancel.is_cancelled() {
            stop = "interrupted";
            break;
        }
        if c.expired() {
            stop = "time_limit";
            break;
        }
        while prepared.operators[index].is_err() {
            let next = (index + 1 < settings.ladder.len()).then_some(index + 1);
            transition(&c, &mut a, index, next, "preparation_guard");
            let Some(next) = next else {
                stop = "numerical_failure";
                break 'solve;
            };
            index = next;
            clean = 0;
        }
        if c.remaining() < 2 {
            break;
        }
        let start = c.state().iterations;
        let length = c.next_chunk(settings.audit_interval).min(c.remaining() - 1);
        let end = start + length;
        let checkpoint = c.checkpoint();
        let mut replay = false;
        'attempt: loop {
            let mut failure = None;
            let mut pre = None;
            while c.state().iterations < end {
                if cancel.is_cancelled() || c.expired() {
                    stop = if cancel.is_cancelled() {
                        "interrupted"
                    } else {
                        "time_limit"
                    };
                    restore(&mut c, &checkpoint, start, &mut a);
                    break 'solve;
                }
                let left = end - c.state().iterations;
                let count = c.next_chunk(if left == 1 { 1 } else { (left - 1).min(64) });
                if count == 0 || c.remaining() <= count {
                    restore(&mut c, &checkpoint, start, &mut a);
                    break 'solve;
                }
                if left == 1 {
                    pre = Some(c.state().clone());
                }
                if settings.ladder[index] == LpAdaptiveRung::WorkingFp32
                    && c.round_working().is_err()
                {
                    failure = Some("range_guard");
                    break;
                }
                let ps = engine.step() / c.state().weight;
                let ds = engine.step() * c.state().weight;
                if !ps.is_finite() || !ds.is_finite() || ps == 0.0 || ds == 0.0 {
                    failure = Some("range_guard");
                    break;
                }
                let result = advance(index, &mut c, count, d);
                let guard = match result {
                    Ok(v) => v,
                    Err(e) => {
                        error = Some(e);
                        stop = "device_failure";
                        restore(&mut c, &checkpoint, start, &mut a);
                        break 'solve;
                    }
                };
                a.proposed_steps += count;
                a.rung_proposals[index] += count;
                if replay {
                    a.replay_steps += count;
                }
                if guard.is_some() {
                    c.charge_extra(count).expect("admitted rejected work");
                    a.rejected_steps += count;
                    failure = Some("range_guard");
                    break;
                }
                c.commit_steps(count).expect("bounded proposal chunk");
            }
            let mut reference = None;
            if failure.is_none() {
                if cancel.is_cancelled() || c.expired() {
                    stop = if cancel.is_cancelled() {
                        "interrupted"
                    } else {
                        "time_limit"
                    };
                    restore(&mut c, &checkpoint, start, &mut a);
                    break 'solve;
                }
                let phase = d.start();
                let result = correction(engine, pre.as_ref().expect("isolated final pre-step"));
                c.charge_extra(1).expect("reserved audit work");
                a.audit_steps += 1;
                match result {
                    Ok((x, y)) => {
                        let (pass, maximum) = audit(
                            engine,
                            &settings,
                            pre.as_ref().unwrap(),
                            (&c.state().primal, &c.state().dual),
                            (&x, &y),
                            1.0,
                        );
                        a.max_audit_error = a.max_audit_error.max(maximum);
                        if pass {
                            reference = Some((x, y));
                        } else {
                            failure = Some("audit_failed");
                        }
                    }
                    Err(_) => failure = Some("reference_guard"),
                }
                d.finish("adaptive_audit", phase);
            }
            if let Some(reason) = failure {
                a.rejected_windows += 1;
                restore(&mut c, &checkpoint, start, &mut a);
                clean = 0;
                let next = (index + 1 < settings.ladder.len()).then_some(index + 1);
                transition(&c, &mut a, index, next, reason);
                let Some(next) = next else {
                    stop = "numerical_failure";
                    break 'solve;
                };
                index = next;
                replay = true;
                while prepared.operators[index].is_err() {
                    let next = (index + 1 < settings.ladder.len()).then_some(index + 1);
                    transition(&c, &mut a, index, next, "preparation_guard");
                    let Some(next) = next else {
                        stop = "numerical_failure";
                        break 'solve;
                    };
                    index = next;
                }
                continue 'attempt;
            }
            let (x, y) = reference.expect("passing audit endpoint");
            c.replace_endpoint(x, y).expect("finite reference");
            a.accepted_windows += 1;
            clean = clean.saturating_add(1);
            if let Some(policy) = &settings.demotion
                && index > 0
                && clean >= policy.clean_windows
                && c.remaining() > 0
                && !cancel.is_cancelled()
                && !c.expired()
            {
                clean = 0;
                if let Ok(op) = &prepared.operators[index - 1] {
                    let phase = d.start();
                    let before = pre.as_ref().unwrap();
                    let trial = proposal(engine, before, op, settings.ladder[index - 1]);
                    c.charge_extra(1).expect("admitted demotion probe");
                    a.probe_steps += 1;
                    if let Ok((x, y)) = trial
                        && audit(
                            engine,
                            &settings,
                            before,
                            (&x, &y),
                            (&c.state().primal, &c.state().dual),
                            policy.margin_fraction,
                        )
                        .0
                    {
                        transition(&c, &mut a, index, Some(index - 1), "demotion");
                        index -= 1;
                    }
                    d.finish("adaptive_probe", phase);
                }
            }
            if c.check_pending() {
                if cancel.is_cancelled() || c.expired() {
                    stop = if cancel.is_cancelled() {
                        "interrupted"
                    } else {
                        "time_limit"
                    };
                    break 'solve;
                }
                let point = c.iterate();
                assessments += 1;
                let accept = check(&point.primal, &point.dual, d);
                assessed = Some(point);
                if accept {
                    stop = "accepted";
                    break 'solve;
                }
                let phase = d.start();
                c.continue_after_check();
                d.finish("controller", phase);
            }
            break 'attempt;
        }
    }
    let launches = d.execution.as_ref().map_or(0, |e| e.kernel_launches);
    d.iterations = error.is_none().then_some(c.physical_iterations());
    d.restarts = Some(c.state().restarts);
    d.kernel_launches = Some(launches);
    d.control = Some(LpControlDiagnostics {
        controller: "host-restart-weight-v1".into(),
        logical_iterations: c.state().iterations,
        physical_iterations: d.iterations,
        device_kernel_launches: launches,
        assessments,
        kkt_evaluations: c.kkt_evaluations(),
        restarts: c.state().restarts,
        weight: c.state().weight,
        stop: stop.into(),
    });
    d.adaptive = Some(a);
    if let Some(error) = error {
        d.unavailable
            .push("completed device work after fault is unavailable".into());
        return Err(error);
    }
    let point = assessed.unwrap_or_else(|| c.iterate());
    Ok((point.primal, point.dual, point.iterations))
}
