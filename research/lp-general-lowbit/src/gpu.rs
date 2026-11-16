//! Checkpointed sparse GPU execution with original-model host certification.
use crate::{
    Result,
    device::Device,
    operator::{Format, Operator},
    solve::{Settings, assess_repaired, same_state},
};
use crate::{control::Fp64Controller, merit::EngineMerit};
use optimizer_core::Model;
use optimizer_lp::{Engine, LinearProgram};
use serde_json::{Value, json};
use std::{
    path::Path,
    time::{Duration, Instant},
};

pub fn solve(model: &Model, settings: &Settings, image: &Path) -> Result<Value> {
    settings.validate()?;
    let started = Instant::now();
    let program = LinearProgram::new(model)?;
    let certificate_context = crate::implied::Context::new(model, &program)?;
    let engine = Engine::new(&program, settings.lp());
    let op = Operator::new_for(&engine, settings.format)?;
    let mut control =
        Fp64Controller::new_with_merit(&engine, |x, y, w| engine.projected_residual(x, y, w));
    control.set_deadline(Some(started + Duration::from_millis(settings.wall_ms)));
    let prepared = started.elapsed().as_nanos();
    let mut device = Device::new(&engine, &op, image, settings.format)?;
    device.reset(control.state())?;
    let setup = started.elapsed().as_nanos() - prepared;
    let mut format = settings.format;
    let mut accepted = [0u64; 4];
    let mut attempted = [0u64; 4];
    let mut recoveries = Vec::new();
    let mut assessments = Vec::new();
    let mut faulted = false;
    let mut status = "limit";
    let mut execution_ns = 0;
    let mut assessment_ns = 0;
    let mut recovery_ns = 0;
    let index = |f| match f {
        Format::Native => 0,
        Format::Fp32 => 1,
        Format::Fp4x1 => 2,
        Format::Fp4x2 => 3,
    };
    while control.remaining() > 0 {
        if control.expired() {
            status = "deadline";
            break;
        }
        if settings
            .cancel_after
            .is_some_and(|v| control.physical_iterations() >= v)
        {
            status = "cancelled";
            break;
        }
        // Device state is accepted only at a complete host assessment boundary.
        let checkpoint = control.checkpoint();
        let before = control.state().clone();
        let before_error = engine.projected_residual(&before.primal, &before.dual, before.weight);
        let limit = crate::merit::local_budget(before_error);
        let mut done = 0;
        let mut rejected = false;
        let mut interrupted = false;
        let execution_start = Instant::now();
        while !control.check_pending() && control.remaining() > 0 {
            let mut count = control.next_chunk(settings.reference_window);
            if let Some(at) = settings.cancel_after {
                count = count.min(at.saturating_sub(control.physical_iterations()));
            }
            if !faulted && let Some(at) = settings.force_recovery_after {
                count = count.min(at.saturating_sub(control.physical_iterations()).max(1));
            }
            if count == 0 {
                interrupted = true;
                status = "cancelled";
                break;
            }
            let valid = device.advance(
                count,
                engine.step(),
                control.state().weight,
                control.state().since_restart,
                limit,
            )?;
            attempted[index(format)] += count;
            done += count;
            control.commit_steps(count)?;
            if control.expired()
                || settings
                    .cancel_after
                    .is_some_and(|v| control.physical_iterations() >= v)
            {
                interrupted = true;
                status = if control.expired() {
                    "deadline"
                } else {
                    "cancelled"
                };
                break;
            }
            if !valid {
                rejected = true;
                break;
            }
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
        if !rejected && !interrupted {
            let (x, y) = device.endpoint()?;
            let (cx, cy, _, _) = control.buffers();
            cx.copy_from_slice(&x);
            cy.copy_from_slice(&y);
        }
        execution_ns += execution_start.elapsed().as_nanos();
        let check_start = Instant::now();
        if !rejected && !interrupted {
            let s = control.state();
            let error = engine.projected_residual(&s.primal, &s.dual, s.weight);
            rejected = !error.is_finite()
                || (format != Format::Native && error > 2. * before_error.max(settings.tolerance));
        }
        assessment_ns += check_start.elapsed().as_nanos();
        if interrupted || rejected {
            let recovery_start = Instant::now();
            control.restore(&checkpoint)?;
            let exact = same_state(control.state(), &before);
            device.reset(control.state())?;
            if interrupted {
                recovery_ns += recovery_start.elapsed().as_nanos();
                break;
            }
            if format == Format::Native {
                status = "numerical_failure";
                recovery_ns += recovery_start.elapsed().as_nanos();
                break;
            }
            let next = format.promote();
            recoveries.push(json!({"from":format,"to":next,"physical":control.physical_iterations(),
                "logical":control.state().iterations,"generation":control.generation(),"restored_exact":exact}));
            device.set_format(&op, next)?;
            format = next;
            recovery_ns += recovery_start.elapsed().as_nanos();
            continue;
        }
        accepted[index(format)] += done;
        let check_start = Instant::now();
        let endpoint = control.iterate();
        let certificate = assess_repaired(
            model,
            certificate_context.program(&program),
            &endpoint.primal,
            &endpoint.dual,
            settings.tolerance,
        )?;
        assessments.push(
            json!({"physical":control.physical_iterations(),"logical":control.state().iterations,
            "primal":endpoint.primal,"dual":endpoint.dual,"certificate":certificate}),
        );
        if control.expired() {
            control.restore(&checkpoint)?;
            accepted[index(format)] -= done;
            status = "deadline";
            assessment_ns += check_start.elapsed().as_nanos();
            break;
        }
        if certificate["accepted"] == true {
            status = "certified";
            assessment_ns += check_start.elapsed().as_nanos();
            break;
        }
        if control.check_pending() {
            control.continue_after_check_with_merit(|x, y, w| engine.projected_residual(x, y, w));
        }
        device.reset(control.state())?;
        assessment_ns += check_start.elapsed().as_nanos();
    }
    let check_start = Instant::now();
    let endpoint = control.iterate();
    let certificate = assess_repaired(
        model,
        certificate_context.program(&program),
        &endpoint.primal,
        &endpoint.dual,
        settings.tolerance,
    )?;
    assessment_ns += check_start.elapsed().as_nanos();
    let device_bytes = device.allocated_bytes;
    let teardown_start = Instant::now();
    drop(device);
    let teardown_ns = teardown_start.elapsed().as_nanos();
    Ok(
        json!({"schema_version":1,"kind":"general-lowbit-solve","execution":"sparse-gpu","settings":settings,
        "bound_proof":certificate_context.proof,"guard_policy":"relative-projected-displacement-v2",
        "status":status,"certified":status=="certified"&&certificate["accepted"]==true,"certificate":certificate,
        "primal":endpoint.primal,"dual":endpoint.dual,"physical":control.physical_iterations(),"logical":control.state().iterations,
        "restarts":control.state().restarts,"attempted":attempted,"accepted":accepted,"format_order":["native","fp32","fp4x1","fp4x2"],
        "recoveries":recoveries,"assessments":assessments,"operator_storage_bytes":op.storage_bytes(),"device_bytes_upper":device_bytes,
        "rows":program.row_count(),"columns":program.column_count(),"nonzeros":program.nonzeros(),"elapsed_ns":started.elapsed().as_nanos(),
        "cost_ns":{"host_preparation":prepared,"device_setup":setup,"execution":execution_ns,"assessment":assessment_ns,"recovery":recovery_ns,"device_teardown":teardown_ns}}),
    )
}
