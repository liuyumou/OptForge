//! Shared FP64 solver control; low-bit products never issue certificates.
use crate::engine::Engine;
use crate::{
    Result,
    operator::{Format, Operator},
};
use crate::{
    control::{Fp64Controller, Fp64State},
    merit::EngineMerit,
};
use optimizer_core::{Assignment, Candidate, Model, Tolerances};
use optimizer_lp::{LinearProgram, LpSettings, certify, certify::assess_gap};
use serde::{Deserialize, Serialize};
use serde_json::{Value, json};
use std::time::{Duration, Instant};

pub fn same_state(a: &Fp64State, b: &Fp64State) -> bool {
    fn bits(s: &Fp64State) -> impl Iterator<Item = u64> + '_ {
        s.primal
            .iter()
            .chain(&s.dual)
            .chain(&s.anchor_primal)
            .chain(&s.anchor_dual)
            .chain([&s.weight, &s.integral, &s.anchor_error, &s.last_check_error])
            .map(|v| v.to_bits())
    }
    (
        a.primal.len(),
        a.dual.len(),
        a.anchor_primal.len(),
        a.anchor_dual.len(),
    ) == (
        b.primal.len(),
        b.dual.len(),
        b.anchor_primal.len(),
        b.anchor_dual.len(),
    ) && bits(a).eq(bits(b))
        && a.previous_error.map(f64::to_bits) == b.previous_error.map(f64::to_bits)
        && (
            a.iterations,
            a.restarts,
            a.since_restart,
            a.checked_iteration,
        ) == (
            b.iterations,
            b.restarts,
            b.since_restart,
            b.checked_iteration,
        )
}

#[derive(Clone, Debug, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Settings {
    pub format: Format,
    pub tolerance: f64,
    pub iteration_limit: u64,
    pub check_interval: u64,
    pub reference_window: u64,
    pub wall_ms: u64,
    pub equilibrate: bool,
    /// Admission-only fault, applied once; never part of scientific selection.
    #[serde(default)]
    pub force_recovery_after: Option<u64>,
    #[serde(default)]
    pub cancel_after: Option<u64>,
}
impl Settings {
    pub fn validate(&self) -> Result<()> {
        if ![1e-7, 1e-9].contains(&self.tolerance)
            || self.iteration_limit == 0
            || self.iteration_limit > 1_000_000
            || self.check_interval == 0
            || self.check_interval > 1000
            || self.reference_window == 0
            || self.reference_window > 64
            || self.wall_ms == 0
            || self.wall_ms > 1_800_000
        {
            return Err("invalid solver settings".into());
        }
        Ok(())
    }
    pub fn lp(&self) -> LpSettings {
        let mut s = LpSettings::published(self.iteration_limit, self.check_interval);
        if !self.equilibrate {
            s.preconditioner.ruiz_passes = 0;
            s.preconditioner.pock_chambolle_alpha = 0.;
        }
        s
    }
}
pub fn assess(
    model: &Model,
    program: &LinearProgram,
    x: &[f64],
    y: &[f64],
    tolerance: f64,
) -> Result<Value> {
    let tolerances = Tolerances {
        absolute: tolerance,
        relative: tolerance,
        integrality: tolerance,
    };
    let candidate = Candidate {
        schema_version: 1,
        model_id: model.document().model_id.clone(),
        values: program
            .variable_ids()
            .iter()
            .zip(x)
            .map(|(&variable_id, &value)| Assignment { variable_id, value })
            .collect(),
    };
    let validation = model.evaluate(&candidate, tolerances)?;
    let bound = certify(program, y).ok().map(|v| v.bound);
    let gap = bound.and_then(|b| assess_gap(program, x, b, tolerances));
    Ok(
        json!({"accepted":validation.feasible && gap.as_ref().is_some_and(|v|v.closed),
        "feasible":validation.feasible,"objective":validation.objective,"bound":bound,
        "gap_upper":gap.map(|v|v.upper),"tolerance":tolerance}),
    )
}

pub fn assess_repaired(
    model: &Model,
    program: &LinearProgram,
    x: &[f64],
    y: &[f64],
    tolerance: f64,
) -> Result<Value> {
    let mut result = assess(model, program, x, y, tolerance)?;
    if result["feasible"] == true
        && result["bound"].is_null()
        && let Some((witness, corrections)) = crate::repair::propose(program, y)
    {
        result = assess(model, program, x, &witness, tolerance)?;
        result["certificate_dual"] = json!(witness);
        result["dual_corrections"] = json!(corrections);
    }
    Ok(result)
}

pub fn cpu(model: &Model, settings: &Settings) -> Result<Value> {
    settings.validate()?;
    let started = Instant::now();
    let program = LinearProgram::new(model)?;
    let certificate_context = crate::implied::Context::new(model, &program)?;
    let engine = Engine::new(&program, settings.lp());
    let op = Operator::new_for(&engine, settings.format)?;
    let mut control =
        Fp64Controller::new_with_merit(&engine, |x, y, w| engine.projected_residual(x, y, w));
    control.set_deadline(Some(started + Duration::from_millis(settings.wall_ms)));
    let mut format = settings.format;
    let mut accepted = [0u64; 4];
    let mut attempted = [0u64; 4];
    let mut recoveries = Vec::new();
    let mut faulted = false;
    let mut status = "limit";
    let mut assessments = Vec::new();
    let index = |f| match f {
        Format::Native => 0,
        Format::Fp32 => 1,
        Format::Fp4x1 => 2,
        Format::Fp4x2 | Format::Fp4x3 | Format::Fp4x4 => 3,
    };
    while control.remaining() > 0 {
        if control.expired()
            || settings
                .cancel_after
                .is_some_and(|v| control.physical_iterations() >= v)
        {
            status = if control.expired() {
                "deadline"
            } else {
                "cancelled"
            };
            break;
        }
        if control.check_pending() {
            control.continue_after_check_with_merit(|x, y, w| engine.projected_residual(x, y, w));
        }
        let checkpoint = control.checkpoint();
        let before = control.state().clone();
        let before_error = engine.projected_residual(&before.primal, &before.dual, before.weight);
        let count = control.next_chunk(settings.reference_window).min(
            settings.cancel_after.map_or(u64::MAX, |v| {
                v.saturating_sub(control.physical_iterations())
            }),
        );
        let anchor_x = before.primal.clone();
        let anchor_y = before.dual.clone();
        let mut rejected = false;
        let mut done = 0;
        for _ in 0..count {
            let state = control.state();
            let x = &state.primal;
            let y = &state.dual;
            let tau = engine.step() / state.weight;
            let sigma = engine.step() * state.weight;
            let ay = op.product(true, y, &anchor_y, format)?;
            let (lower, upper) = engine.scaled_column_bounds();
            let next_x: Vec<_> = x
                .iter()
                .enumerate()
                .map(|(j, &old)| {
                    (old - tau * (engine.scaled_objective()[j] - ay.values[j]))
                        .max(lower[j])
                        .min(upper[j])
                })
                .collect();
            let extra: Vec<_> = next_x
                .iter()
                .zip(x)
                .map(|(&next, &old)| 2. * next - old)
                .collect();
            let ax = op.product(false, &extra, &anchor_x, format)?;
            let (lower, upper) = engine.scaled_row_bounds();
            let next_y: Vec<_> = y
                .iter()
                .enumerate()
                .map(|(i, &old)| {
                    let raw = old - sigma * ax.values[i];
                    raw - sigma * (raw / sigma).max(-upper[i]).min(-lower[i])
                })
                .collect();
            let local = ay
                .bounds
                .iter()
                .map(|b| tau * b)
                .chain(ax.bounds.iter().map(|b| sigma * b))
                .fold(0., f64::max);
            let limit = crate::merit::local_budget(before_error);
            // Charge an attempted update even when its guard rejects the endpoint.
            done += 1;
            attempted[index(format)] += 1;
            if !next_x.iter().chain(&next_y).all(|v| v.is_finite())
                || (format != Format::Native && local > limit)
            {
                control.charge_extra(1)?;
                rejected = true;
                break;
            }
            let toward = (state.since_restart + 1) as f64 / (state.since_restart + 2) as f64;
            let back = 1. / (state.since_restart + 2) as f64;
            let (x, y, anchor_x, anchor_y) = control.buffers();
            for ((x, next), anchor) in x.iter_mut().zip(next_x).zip(anchor_x) {
                *x = toward * next + back * anchor;
            }
            for ((y, next), anchor) in y.iter_mut().zip(next_y).zip(anchor_y) {
                *y = toward * next + back * anchor;
            }
            control.commit_steps(1)?;
            if !faulted
                && settings
                    .force_recovery_after
                    .is_some_and(|v| control.physical_iterations() >= v)
            {
                faulted = true;
                rejected = true;
                break;
            }
        }
        if control.expired()
            || settings
                .cancel_after
                .is_some_and(|v| control.physical_iterations() >= v)
        {
            control.restore(&checkpoint)?;
            status = if control.expired() {
                "deadline"
            } else {
                "cancelled"
            };
            break;
        }
        let state = control.state();
        let after_error = engine.projected_residual(&state.primal, &state.dual, state.weight);
        if !after_error.is_finite()
            || (format != Format::Native && after_error > 2. * before_error.max(settings.tolerance))
        {
            rejected = true;
        }
        if rejected {
            control.restore(&checkpoint)?;
            if format == Format::Native {
                status = "numerical_failure";
                break;
            }
            let next = format.promote();
            recoveries.push(json!({"from":format,"to":next,"physical":control.physical_iterations(),
                "logical":control.state().iterations,"generation":control.generation(),"restored_exact":same_state(control.state(),&before)}));
            format = next;
            continue;
        }
        accepted[index(format)] += done;
        if control.check_pending() || control.remaining() == 0 {
            let endpoint = control.iterate();
            let certificate = assess_repaired(
                model,
                certificate_context.program(&program),
                &endpoint.primal,
                &endpoint.dual,
                settings.tolerance,
            )?;
            assessments.push(json!({"physical":control.physical_iterations(),"logical":control.state().iterations,
                "primal":endpoint.primal,"dual":endpoint.dual,"certificate":certificate}));
            if control.expired() {
                control.restore(&checkpoint)?;
                accepted[index(format)] -= done;
                status = "deadline";
                break;
            }
            if certificate["accepted"] == true {
                status = "certified";
                break;
            }
        }
    }
    let endpoint = control.iterate();
    let certificate = assess_repaired(
        model,
        certificate_context.program(&program),
        &endpoint.primal,
        &endpoint.dual,
        settings.tolerance,
    )?;
    Ok(
        json!({"schema_version":1,"kind":"general-lowbit-solve","execution":"cpu-reference","settings":settings,
        "bound_proof":certificate_context.proof,"guard_policy":"relative-projected-displacement-v2",
        "status":status,"certified":status=="certified" && certificate["accepted"]==true,
        "certificate":certificate,"primal":endpoint.primal,"dual":endpoint.dual,
        "physical":control.physical_iterations(),"logical":control.state().iterations,"restarts":control.state().restarts,
        "attempted":attempted,"accepted":accepted,"format_order":["native","fp32","fp4x1","fp4x2"],
        "recoveries":recoveries,"assessments":assessments,"operator_storage_bytes":op.storage_bytes(),
        "rows":program.row_count(),"columns":program.column_count(),"nonzeros":program.nonzeros(),
        "elapsed_ns":started.elapsed().as_nanos()}),
    )
}
