//! Checkpointed sparse GPU execution with original-model host certification.
use crate::engine::Engine;
use crate::{
    Result,
    operator::{Format, Operator},
    solve::{Settings, same_state},
    tensor::{Config, Packed},
    tensor_device::Device as LocalDevice,
};
use crate::{control::Fp64Controller, merit::EngineMerit};
use optimizer_core::Model;
use optimizer_lp::LinearProgram;
use serde_json::{Value, json};
use std::{
    path::Path,
    time::{Duration, Instant},
};

enum Runtime {
    Local(Box<LocalDevice>),
    Fast(Box<crate::fast_device::Device>),
}
macro_rules! dispatch {
    ($s:expr, $d:ident, $body:expr) => {
        match $s {
            Runtime::Local($d) => $body,
            Runtime::Fast($d) => $body,
        }
    };
}
impl Runtime {
    fn reset(&mut self, s: &crate::control::Fp64State) -> Result<()> {
        dispatch!(self, d, d.reset(s))
    }
    fn set_format(&mut self, f: Format) -> Result<()> {
        dispatch!(self, d, d.set_format(f))
    }
    fn advance(&mut self, n: u64, step: f64, w: f64, since: u64, limit: f64) -> Result<bool> {
        dispatch!(self, d, d.advance(n, step, w, since, limit))
    }
    fn endpoint(&self) -> Result<(Vec<f64>, Vec<f64>)> {
        dispatch!(self, d, d.endpoint())
    }
    fn work(&self) -> Result<[u64; 4]> {
        dispatch!(self, d, d.work())
    }
    fn reference_work(&self) -> u64 {
        dispatch!(self, d, d.reference_work)
    }
    fn allocated_bytes(&self) -> usize {
        dispatch!(self, d, d.allocated_bytes)
    }
}
pub fn solve(model: &Model, settings: &Settings, image: &Path, config: &Config) -> Result<Value> {
    solve_with_fast(model, settings, image, config, None)
}
pub fn solve_with_fast(
    model: &Model,
    settings: &Settings,
    image: &Path,
    config: &Config,
    fast: Option<&crate::fast_device::Config>,
) -> Result<Value> {
    settings.validate()?;
    config.validate()?;
    if let Some(f) = fast {
        f.validate()?;
        if f.resident_preparation
            || f.resident_control
            || f.host_state_reuse
            || f.certificate_workspace
            || f.certificate_overlap
        {
            return Err("FP4x2 overhead options require the original-array interface".into());
        }
        if f.certificate_scratch {
            return Err("certificate scratch requires the original-array interface".into());
        }
        if f.final_assessment_reuse {
            return Err("final assessment reuse requires the original-array interface".into());
        }
        if f.gpu_preparation {
            return Err("GPU preparation requires the original-array interface".into());
        }
    }
    let mut control_settings = settings.clone();
    control_settings.check_interval = config.control_interval;
    let started = Instant::now();
    let program = if fast.is_some_and(|f| f.host_preparation) {
        LinearProgram::new_indexed(model)?
    } else {
        LinearProgram::new(model)?
    };
    let certificate_context = crate::implied::Context::new(model, &program)?;
    let mut assessor = crate::assessment::Assessor::new(
        model,
        certificate_context.program(&program),
        fast.is_some_and(|f| f.host_certificates),
    );
    let engine = if fast.is_some_and(|f| f.host_preparation) {
        crate::host::engine(&program, control_settings.lp())
    } else {
        Engine::new(&program, control_settings.lp())
    };
    let op = Operator::new_for(&engine, Format::Native)?;
    let packed = if settings.format.components() > 0 {
        Some(if fast.is_some() {
            Packed::proposal(&op, config)?
        } else {
            Packed::new(&op, config)?
        })
        .filter(|p| p.tile_count > 0)
    } else {
        None
    };
    crate::host::with_products(
        &engine,
        fast.is_some_and(|f| f.host_reductions),
        |products| {
            let workspace =
                std::cell::RefCell::new((products, crate::host::ResidualWorkspace::default()));
            let merit = |x: &[f64], y: &[f64], w| {
                if fast.is_some_and(|f| f.host_reductions) {
                    let mut workspace = workspace.borrow_mut();
                    let (products, residual) = &mut *workspace;
                    residual.evaluate(products, &engine, x, y, w)
                } else {
                    engine.projected_residual(x, y, w)
                }
            };
            let mut control = Fp64Controller::new_with_merit(&engine, merit);
            control.set_deadline(Some(started + Duration::from_millis(settings.wall_ms)));
            let selected_format = if settings.format.components() > 0 && packed.is_none() {
                if fast.is_some() {
                    Format::Fp32
                } else {
                    Format::Native
                }
            } else {
                settings.format
            };
            let prepared = started.elapsed().as_nanos();
            let mut device = if let Some(f) = fast {
                Runtime::Fast(Box::new(crate::fast_device::Device::new(
                    &engine,
                    &op,
                    packed.as_ref(),
                    image,
                    selected_format,
                    config,
                    f,
                )?))
            } else {
                Runtime::Local(Box::new(LocalDevice::new(
                    &engine,
                    &op,
                    packed.as_ref(),
                    image,
                    selected_format,
                    config,
                )?))
            };
            let fast_shapes = match &device {
                Runtime::Fast(d) => Some(d.shapes()),
                _ => None,
            };
            device.reset(control.state())?;
            let setup = started.elapsed().as_nanos() - prepared;
            let mut format = selected_format;
            let mut current_merit = control.state().anchor_error;
            let mut accepted = [0u64; 6];
            let mut attempted = [0u64; 6];
            let mut recoveries = Vec::new();
            let mut assessments = Vec::new();
            let mut accepted_work = [0u64; 4];
            let mut work_before = [0u64; 4];
            let mut last_certificate = 0;
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
                Format::Fp4x3 => 4,
                Format::Fp4x4 => 5,
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
                let checkpoint_work = work_before;
                let checkpoint = control.checkpoint();
                let before = control.state().clone();
                let before_error = current_merit;
                let limit = crate::merit::local_budget(before_error);
                let mut done = 0;
                let mut rejected = false;
                let mut interrupted = false;
                let execution_start = Instant::now();
                while !control.check_pending() && control.remaining() > 0 {
                    let mut count = control.next_chunk(config.control_interval);
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
                let work_after = device.work()?;
                let check_start = Instant::now();
                if !rejected && !interrupted {
                    let s = control.state();
                    let error = merit(&s.primal, &s.dual, s.weight);
                    current_merit = error;
                    rejected = !error.is_finite()
                        || (format != Format::Native
                            && error > 2. * before_error.max(settings.tolerance));
                }
                assessment_ns += check_start.elapsed().as_nanos();
                if interrupted || rejected {
                    current_merit = before_error;
                    work_before = work_after;
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
                    let next = Format::Native;
                    recoveries.push(json!({"from":format,"to":next,"physical":control.physical_iterations(),
                "logical":control.state().iterations,"generation":control.generation(),"restored_exact":exact}));
                    device.set_format(next)?;
                    format = next;
                    recovery_ns += recovery_start.elapsed().as_nanos();
                    continue;
                }
                accepted[index(format)] += done;
                for j in 0..4 {
                    accepted_work[j] += work_after[j] - work_before[j];
                }
                work_before = work_after;
                let check_start = Instant::now();
                let due = control.state().iterations.saturating_sub(last_certificate)
                    >= settings.check_interval
                    || control.remaining() == 0;
                if due {
                    last_certificate = control.state().iterations;
                    let endpoint = control.iterate();
                    let certificate = assessor.evaluate(
                        &endpoint.primal,
                        &endpoint.dual,
                        settings.tolerance,
                        control.remaining() > 0 && !control.expired(),
                    )?;
                    assessments.push(
            json!({"physical":control.physical_iterations(),"logical":control.state().iterations,
            "primal":endpoint.primal,"dual":endpoint.dual,"certificate":certificate}),
        );
                    if control.expired() {
                        control.restore(&checkpoint)?;
                        accepted[index(format)] -= done;
                        // A deadline invalidates this entire control interval, including low-bit work.
                        for j in 0..4 {
                            accepted_work[j] -= work_after[j] - checkpoint_work[j];
                        }
                        status = "deadline";
                        assessment_ns += check_start.elapsed().as_nanos();
                        break;
                    }
                    if certificate["accepted"] == true {
                        status = "certified";
                        assessment_ns += check_start.elapsed().as_nanos();
                        break;
                    }
                }
                if control.expired() {
                    control.restore(&checkpoint)?;
                    accepted[index(format)] -= done;
                    for j in 0..4 {
                        accepted_work[j] -= work_after[j] - checkpoint_work[j];
                    }
                    status = "deadline";
                    break;
                }
                if control.check_pending() {
                    let checked_weight = control.state().weight;
                    let checked_merit = current_merit;
                    control.continue_after_check_with_merit(|x, y, w| {
                        current_merit = if w.to_bits() == checked_weight.to_bits() {
                            checked_merit
                        } else {
                            merit(x, y, w)
                        };
                        current_merit
                    });
                }
                device.reset(control.state())?;
                assessment_ns += check_start.elapsed().as_nanos();
            }
            let check_start = Instant::now();
            let endpoint = control.iterate();
            let certificate = if status == "certified" {
                assessments.last().ok_or("missing accepted assessment")?["certificate"].clone()
            } else {
                assessor.evaluate(&endpoint.primal, &endpoint.dual, settings.tolerance, false)?
            };
            if control.expired() {
                status = "deadline";
            }
            assessment_ns += check_start.elapsed().as_nanos();
            let physical_work = device.work()?;
            let reference_work = device.reference_work();
            let device_bytes = device.allocated_bytes();
            let teardown_start = Instant::now();
            drop(device);
            let teardown_ns = teardown_start.elapsed().as_nanos();
            let cached_assessments = assessor.cached_calls;
            let release_check = Instant::now();
            drop(assessor);
            assessment_ns += release_check.elapsed().as_nanos();
            let mut result = json!({"schema_version":1,"kind":"general-lowbit-solve","execution":"sparse-tensor-local","settings":settings,"tensor_config":config,"selected_initial_format":selected_format,
        "reference_product_nnz":reference_work,
        "physical_product_work":physical_work,"accepted_product_work":accepted_work,
        "product_work_order":["tensor_attempted_nnz","tensor_used_nnz","row_correction_nnz","logical_product_nnz"],
        "tile_count":packed.as_ref().map_or(0,|p|p.tile_count),"packed_bytes":packed.as_ref().map_or(0,Packed::storage_bytes),
        "bound_proof":certificate_context.proof,"guard_policy":"tile-local-row-replacement-v2",
        "status":status,"certified":status=="certified"&&certificate["accepted"]==true,"certificate":certificate,
        "primal":endpoint.primal,"dual":endpoint.dual,"physical":control.physical_iterations(),"logical":control.state().iterations,
        "restarts":control.state().restarts,"attempted":attempted,"accepted":accepted,"format_order":["native","fp32","fp4x1","fp4x2","fp4x3","fp4x4"],
        "recoveries":recoveries,"assessments":assessments,"operator_storage_bytes":op.storage_bytes(),"device_bytes_upper":device_bytes,
        "rows":program.row_count(),"columns":program.column_count(),"nonzeros":program.nonzeros(),"elapsed_ns":started.elapsed().as_nanos(),
        "cost_ns":{"host_preparation":prepared,"device_setup":setup,"execution":execution_ns,"assessment":assessment_ns,"recovery":recovery_ns,"device_teardown":teardown_ns}});
            if fast.is_some() {
                result["execution"] = json!("sparse-tensor-proposal");
                result["guard_policy"] = json!("original-residual-checkpoint-v1");
                result["fast_config"] = json!(fast);
                result["initial_fast_lanes"] = json!(fast_shapes);
                if fast.is_some_and(|f| f.host_certificates) {
                    result["cached_assessments"] = json!(cached_assessments);
                }
                if let Some(f) = fast.filter(|f| f.auto_schedule) {
                    result["selected_schedule"] = json!(if selected_format.components() == 0 {
                        "sparse"
                    } else if f.resolved(packed.as_ref()).combined {
                        "combined"
                    } else {
                        "split"
                    });
                }
            }
            Ok(result)
        },
    )
}
