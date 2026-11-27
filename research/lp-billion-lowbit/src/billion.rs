//! Checkpointed sparse GPU execution with original-model host certification.
use crate::array_input::{Original, Store};
use crate::engine::Engine;
use crate::phase_profile::{Phase, Profile};
use crate::{
    Result,
    operator::{Format, Operator},
    solve::Settings,
    tensor::{Config, Packed},
    tensor_device::Device as LocalDevice,
};
use crate::{control::Fp64Controller, merit::EngineMerit};
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
    fn reset_current(&mut self, s: &crate::control::Fp64State) -> Result<()> {
        match self {
            Self::Fast(d) => d.reset_current(s),
            Self::Local(d) => d.reset(s),
        }
    }
    fn gpu_merit_current(&mut self, step: f64, weight: f64) -> Result<Option<f64>> {
        match self {
            Self::Fast(d) => d.gpu_merit_current(step, weight),
            Self::Local(_) => Ok(None),
        }
    }
    fn gpu_movements_current(
        &mut self,
        s: &crate::control::Fp64State,
    ) -> Result<Option<(f64, f64)>> {
        match self {
            Self::Fast(d) => d.gpu_movements_current(s),
            Self::Local(_) => Ok(None),
        }
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
    fn endpoint_into(&self, x: &mut [f64], y: &mut [f64]) -> Result<()> {
        match self {
            Self::Fast(d) => d.endpoint_into(x, y),
            Self::Local(d) => {
                let (px, py) = d.endpoint()?;
                x.copy_from_slice(&px);
                y.copy_from_slice(&py);
                Ok(())
            }
        }
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
    fn gpu_merit(&mut self, x: &[f64], y: &[f64], step: f64, weight: f64) -> Result<Option<f64>> {
        match self {
            Self::Fast(d) => d.gpu_merit(x, y, step, weight),
            Self::Local(_) => Ok(None),
        }
    }
    fn gpu_movements(&mut self, state: &crate::control::Fp64State) -> Result<Option<(f64, f64)>> {
        match self {
            Self::Fast(d) => d.gpu_movements(state),
            Self::Local(_) => Ok(None),
        }
    }
    fn gpu_feasible(&mut self, x: &[f64], tolerance: f64) -> Result<Option<bool>> {
        match self {
            Self::Fast(d) => d.gpu_feasible(x, tolerance),
            Self::Local(_) => Ok(None),
        }
    }
    fn support_metrics(&self) -> Option<Value> {
        match self {
            Self::Fast(d) => d.support_metrics(),
            Self::Local(_) => None,
        }
    }
}
pub fn solve(
    original: &Original,
    store: &Store,
    settings: &Settings,
    image: &Path,
    config: &Config,
    fast_config: &crate::fast_device::Config,
    detailed_timing: bool,
) -> Result<Value> {
    let fast = Some(fast_config);
    settings.validate()?;
    config.validate()?;
    if let Some(f) = fast {
        f.validate()?;
    }
    let mut control_settings = settings.clone();
    control_settings.check_interval = config.control_interval;
    let started = Instant::now();
    let mut profile = Profile::new(started, detailed_timing);
    profile.enter(Phase::Engine);
    let program = &original.program;
    // No optional bound tightening is applied to this canonical-array path.
    // Certificates continue to use the supplied original bounds, including infinities.
    let mut assessor = crate::array_assessment::Assessor::new(original, store, true)
        .with_certificate_scratch(fast_config.certificate_scratch)
        .with_workspace(
            fast_config.certificate_workspace || fast_config.certificate_overlap,
            if fast_config.certificate_overlap {
                3
            } else {
                4
            },
        );
    let mut residency = None;
    let mut gpu_preparation = None;
    let engine = if fast.is_some_and(|f| f.gpu_preparation) {
        let preparation_image = image.with_file_name("prepare.cubin");
        let (engine, metrics) = crate::gpu_prepare::engine_with_residency(
            program,
            control_settings.lp(),
            &preparation_image,
            fast_config.resident_preparation.then_some(&mut residency),
        )?;
        gpu_preparation = Some(metrics);
        engine
    } else if fast.is_some_and(|f| f.host_preparation) {
        crate::host::engine(program, control_settings.lp())
    } else {
        Engine::new(program, control_settings.lp())
    };
    let engine_end = started.elapsed().as_nanos();
    profile.enter(Phase::Operator);
    let gpu_pack = settings.format.components() > 0 && fast.is_some_and(|f| f.gpu_packing);
    let op = if gpu_pack {
        Operator::borrowed_for_gpu_packing(&engine)?
    } else {
        Operator::borrowed_native(&engine)?
    };
    let operator_end = started.elapsed().as_nanos();
    profile.enter(Phase::Packing);
    let mut gpu_packing = None;
    let packed = if gpu_pack {
        let (packed, metrics) = crate::gpu_packing::prepare_with_residency(
            &op,
            config,
            &image.with_file_name("pack.cubin"),
            fast_config.resident_preparation.then_some(&mut residency),
        )?;
        gpu_packing = Some(metrics);
        packed
    } else if settings.format.components() > 0 {
        crate::tensor_prepare::prepare(&op, config)?
    } else {
        None
    };
    let packing_end = started.elapsed().as_nanos();
    let packed_bytes = packed.as_ref().map_or(0, Packed::storage_bytes);
    let tile_count = packed.as_ref().map_or(0, |p| p.tile_count);
    let selected_combined = fast.is_some_and(|f| f.resolved(packed.as_ref()).combined);
    let selected_format = if settings.format.components() > 0 && packed.is_none() {
        if fast.is_some() {
            Format::Fp32
        } else {
            Format::Native
        }
    } else {
        settings.format
    };
    let setup_started = Instant::now();
    profile.enter(Phase::DeviceSetup);
    let device = if let Some(f) = fast {
        Runtime::Fast(Box::new(crate::fast_device::Device::new_with_residency(
            &engine,
            &op,
            packed.as_ref(),
            image,
            selected_format,
            config,
            f,
            residency,
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
    let avoided_upload_bytes = match &device {
        Runtime::Fast(d) => d.avoided_upload_bytes,
        _ => 0,
    };
    let fast_shapes = match &device {
        Runtime::Fast(d) => Some(d.shapes()),
        _ => None,
    };
    let gpu_control_enabled = device
        .support_metrics()
        .is_some_and(|v| v["control_backend"] == "gpu");
    let device = std::cell::RefCell::new(device);
    let gpu_error = std::cell::RefCell::new(None::<String>);
    // All device constructors complete their uploads before returning. Only
    // logical metadata is needed after this point; release the host arrays before
    // allocating controller, checkpoint, residual and certificate workspace.
    drop(packed);
    let initial_setup_ns = setup_started.elapsed().as_nanos();
    let control_started = Instant::now();
    profile.enter(Phase::InitialControl);
    crate::host::with_products(
        &engine,
        fast.is_some_and(|f| f.host_reductions) && !gpu_control_enabled,
        |products| {
            let workspace =
                std::cell::RefCell::new((products, crate::host::ResidualWorkspace::default()));
            let merit = |x: &[f64], y: &[f64], w| {
                match device.borrow_mut().gpu_merit(x, y, engine.step(), w) {
                    Ok(Some(value)) => return value,
                    Ok(None) => {}
                    Err(error) => {
                        *gpu_error.borrow_mut() = Some(error.to_string());
                        return f64::INFINITY;
                    }
                }
                if fast.is_some_and(|f| f.host_reductions) {
                    let mut workspace = workspace.borrow_mut();
                    let (products, residual) = &mut *workspace;
                    residual.evaluate(products, &engine, x, y, w)
                } else {
                    engine.projected_residual(x, y, w)
                }
            };
            // This closure is used only after endpoint download. Initialization,
            // restoration and reference probes use the original upload path.
            let current_merit_value = |x: &[f64], y: &[f64], weight| {
                if fast_config.resident_control {
                    let result = device.borrow_mut().gpu_merit_current(engine.step(), weight);
                    match result {
                        Ok(Some(value)) => return value,
                        Ok(None) => {}
                        Err(error) => {
                            *gpu_error.borrow_mut() = Some(error.to_string());
                            return f64::INFINITY;
                        }
                    }
                }
                merit(x, y, weight)
            };
            let mut control = Fp64Controller::new_with_merit(&engine, merit);
            if let Some(error) = gpu_error.borrow_mut().take() {
                return Err(error.into());
            }
            control.set_deadline(Some(started + Duration::from_millis(settings.wall_ms)));
            let prepared = packing_end + control_started.elapsed().as_nanos();
            profile.enter(Phase::DeviceSetup);
            let reset_started = Instant::now();
            device.borrow_mut().reset(control.state())?;
            let setup = initial_setup_ns + reset_started.elapsed().as_nanos();
            profile.enter(Phase::Bookkeeping);
            let mut format = selected_format;
            let mut current_merit = control.state().anchor_error;
            let mut accepted = [0u64; 6];
            let mut attempted = [0u64; 6];
            let mut recoveries = Vec::new();
            let mut assessments = Vec::new();
            let mut accepted_work = [0u64; 4];
            let mut work_before = [0u64; 4];
            let mut last_certificate = 0;
            let mut last_assessed_state = None;
            let mut checkpoint_slot = None;
            let mut faulted = false;
            let mut status = "limit";
            let mut execution_ns = 0;
            let mut assessment_ns = 0;
            let mut overlap_timing = crate::assessment_overlap::Timing::default();
            let mut overlap_calls = 0;
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
                profile.enter(Phase::Checkpoint);
                if fast_config.host_state_reuse {
                    control.checkpoint_reusing(&mut checkpoint_slot);
                } else {
                    drop(checkpoint_slot.take());
                    checkpoint_slot = Some(control.checkpoint());
                }
                let checkpoint = checkpoint_slot.as_ref().expect("control snapshot");
                profile.enter(Phase::Bookkeeping);
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
                    profile.enter(Phase::Advance);
                    let valid = device.borrow_mut().advance(
                        count,
                        engine.step(),
                        control.state().weight,
                        control.state().since_restart,
                        limit,
                    )?;
                    profile.enter(Phase::Bookkeeping);
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
                    profile.enter(Phase::Download);
                    if fast_config.host_state_reuse {
                        let (cx, cy, _, _) = control.buffers();
                        device.borrow().endpoint_into(cx, cy)?;
                    } else {
                        let (x, y) = device.borrow().endpoint()?;
                        let (cx, cy, _, _) = control.buffers();
                        cx.copy_from_slice(&x);
                        cy.copy_from_slice(&y);
                    }
                    profile.enter(Phase::Bookkeeping);
                }
                execution_ns += execution_start.elapsed().as_nanos();
                profile.enter(Phase::Accounting);
                let work_after = device.borrow().work()?;
                profile.enter(Phase::Bookkeeping);
                let check_start = Instant::now();
                if !rejected && !interrupted {
                    let s = control.state();
                    profile.enter(Phase::Merit);
                    let error = current_merit_value(&s.primal, &s.dual, s.weight);
                    if let Some(error) = gpu_error.borrow_mut().take() {
                        return Err(error.into());
                    }
                    profile.enter(Phase::Bookkeeping);
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
                    profile.enter(Phase::Recovery);
                    if fast_config.host_state_reuse {
                        control.restore_reusing(checkpoint)?;
                    } else {
                        control.restore(checkpoint)?;
                    }
                    let exact = checkpoint.matches_state(control.state());
                    profile.enter(Phase::Upload);
                    device.borrow_mut().reset(control.state())?;
                    profile.enter(Phase::Recovery);
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
                    profile.enter(Phase::Upload);
                    device.borrow_mut().set_format(next)?;
                    profile.enter(Phase::Bookkeeping);
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
                    profile.enter(Phase::Unscale);
                    let endpoint = control.iterate();
                    profile.enter(Phase::Certificate);
                    let (certificate, witness) = if fast_config.certificate_overlap {
                        let (certificate, witness, timing) = assessor.evaluate_overlapped(
                            &endpoint.primal,
                            &endpoint.dual,
                            settings.tolerance,
                            |x, t| device.borrow_mut().gpu_feasible(x, t),
                        )?;
                        overlap_timing.proof_ns += timing.proof_ns;
                        overlap_timing.witness_ns += timing.witness_ns;
                        overlap_timing.wall_ns += timing.wall_ns;
                        overlap_calls += 1;
                        (certificate, witness)
                    } else {
                        let certificate = assessor.evaluate_with_feasibility(
                            &endpoint.primal,
                            &endpoint.dual,
                            settings.tolerance,
                            |x, t| device.borrow_mut().gpu_feasible(x, t),
                        )?;
                        profile.enter(Phase::Witness);
                        (
                            certificate,
                            store.endpoint(&endpoint.primal, &endpoint.dual)?,
                        )
                    };
                    last_assessed_state = Some((
                        control.generation(),
                        control.physical_iterations(),
                        control.state().iterations,
                    ));
                    if fast_config.certificate_overlap {
                        profile.enter(Phase::Witness);
                    }
                    assessments.push(
            json!({"physical":control.physical_iterations(),"logical":control.state().iterations,
            "endpoint":witness,"certificate":certificate}),
        );
                    profile.enter(Phase::Bookkeeping);
                    if control.expired() {
                        profile.enter(Phase::Recovery);
                        if fast_config.host_state_reuse {
                            control.restore_reusing(checkpoint)?;
                        } else {
                            control.restore(checkpoint)?;
                        }
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
                    profile.enter(Phase::Recovery);
                    if fast_config.host_state_reuse {
                        control.restore_reusing(checkpoint)?;
                    } else {
                        control.restore(checkpoint)?;
                    }
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
                    profile.enter(Phase::Restart);
                    control.continue_after_check_with_movement(
                        |x, y, w| {
                            current_merit = if w.to_bits() == checked_weight.to_bits() {
                                checked_merit
                            } else {
                                current_merit_value(x, y, w)
                            };
                            current_merit
                        },
                        |state| match if fast_config.resident_control {
                            device.borrow_mut().gpu_movements_current(state)
                        } else {
                            device.borrow_mut().gpu_movements(state)
                        } {
                            Ok(value) => value,
                            Err(error) => {
                                *gpu_error.borrow_mut() = Some(error.to_string());
                                Some((0., 0.))
                            }
                        },
                    );
                    if let Some(error) = gpu_error.borrow_mut().take() {
                        return Err(error.into());
                    }
                }
                profile.enter(Phase::Upload);
                if fast_config.resident_control {
                    device.borrow_mut().reset_current(control.state())?;
                } else {
                    device.borrow_mut().reset(control.state())?;
                }
                profile.enter(Phase::Bookkeeping);
                assessment_ns += check_start.elapsed().as_nanos();
            }
            // No rollback can follow the loop. Release all snapshot capacity
            // before final assessment/output, including the all-off path.
            drop(checkpoint_slot);
            let check_start = Instant::now();
            profile.enter(Phase::Unscale);
            let endpoint = control.iterate();
            // The controller's restart only changes anchors/weight, not the
            // assessed primal/dual. Advances change the iteration identity;
            // restoration changes generation even when the iteration matches.
            // Conservatively recompute all deadline/cancellation/failure tails.
            let reuse_final = status == "certified"
                || (fast_config.final_assessment_reuse
                    && status == "limit"
                    && last_assessed_state
                        == Some((
                            control.generation(),
                            control.physical_iterations(),
                            control.state().iterations,
                        )));
            profile.enter(if reuse_final {
                Phase::CertificateReuse
            } else {
                Phase::Certificate
            });
            let certificate = if reuse_final {
                assessments.last().ok_or("missing accepted assessment")?["certificate"].clone()
            } else {
                assessor.evaluate_with_feasibility(
                    &endpoint.primal,
                    &endpoint.dual,
                    settings.tolerance,
                    |x, t| device.borrow_mut().gpu_feasible(x, t),
                )?
            };
            if control.expired() {
                status = "deadline";
            }
            assessment_ns += check_start.elapsed().as_nanos();
            profile.enter(Phase::Accounting);
            let physical_work = device.borrow().work()?;
            let reference_work = device.borrow().reference_work();
            let device_bytes = device.borrow().allocated_bytes();
            let gpu_control = device.borrow().support_metrics();
            let avoided_control_bytes = match &*device.borrow() {
                Runtime::Fast(d) => d.avoided_control_bytes,
                _ => 0,
            };
            let teardown_start = Instant::now();
            profile.enter(Phase::Teardown);
            drop(device);
            let teardown_ns = teardown_start.elapsed().as_nanos();
            let cached_assessments = assessor.cached_calls;
            let retained_workspace_bytes = assessor.retained_workspace_bytes();
            profile.enter(Phase::Witness);
            let final_endpoint = if fast_config.host_state_reuse && reuse_final {
                assessments.last().ok_or("missing final witness")?["endpoint"].clone()
            } else {
                store.endpoint(&endpoint.primal, &endpoint.dual)?
            };
            profile.enter(Phase::Response);
            let mut result = json!({"schema_version":1,"kind":"general-lowbit-solve","execution":"sparse-tensor-local","settings":settings,"tensor_config":config,"selected_initial_format":selected_format,
        "reference_product_nnz":reference_work,
        "physical_product_work":physical_work,"accepted_product_work":accepted_work,
        "product_work_order":["tensor_attempted_nnz","tensor_used_nnz","row_correction_nnz","logical_product_nnz"],
        "tile_count":tile_count,"packed_bytes":packed_bytes,
        "bound_proof":[],"guard_policy":"tile-local-row-replacement-v2",
        "status":status,"certified":status=="certified"&&certificate["accepted"]==true,"certificate":certificate,
        "endpoint":final_endpoint,"physical":control.physical_iterations(),"logical":control.state().iterations,
        "restarts":control.state().restarts,"attempted":attempted,"accepted":accepted,"format_order":["native","fp32","fp4x1","fp4x2","fp4x3","fp4x4"],
        "recoveries":recoveries,"assessments":assessments,"operator_storage_bytes":op.storage_bytes(),"device_bytes_upper":device_bytes,
        "rows":program.row_count(),"columns":program.column_count(),"nonzeros":program.nonzeros(),"elapsed_ns":started.elapsed().as_nanos(),
        "preparation_detail_ns":{"engine":engine_end,"operator":operator_end-engine_end,"packing":packing_end-operator_end,"control_initialization":prepared-packing_end},
        "cost_ns":{"host_preparation":prepared,"device_setup":setup,"execution":execution_ns,"assessment":assessment_ns,"recovery":recovery_ns,"device_teardown":teardown_ns}});
            if fast.is_some() {
                if fast_config.host_state_reuse {
                    result["host_state_reuse"] = json!({"checkpoint_buffers":true,"download_into_controller":true,"final_witness_reused":reuse_final});
                }
                if fast_config.certificate_overlap {
                    result["certificate_overlap"] = json!({"calls":overlap_calls,"proof_worker_ns":overlap_timing.proof_ns,"caller_diagnostic_and_witness_ns":overlap_timing.witness_ns,"wall_ns":overlap_timing.wall_ns,"maximum_pending":1,"cpu_dual_overlaps_gpu_diagnostic":true,"speculative_updates":0,"exclusive_phase":"strict_certificate","nested_timings_not_additive":true});
                }
                if fast_config.certificate_workspace || fast_config.certificate_overlap {
                    result["certificate_workspace"] = json!({"retained_bytes":retained_workspace_bytes,"workers":if fast_config.certificate_overlap {3} else {4}});
                }
                if fast_config.resident_control {
                    result["resident_control"] =
                        json!({"avoided_upload_bytes":avoided_control_bytes});
                }
                if fast_config.resident_preparation {
                    result["resident_preparation"] = json!({"avoided_upload_bytes":avoided_upload_bytes,"host_reference_mirrors_retained":true});
                }
                if let Some(mut metrics) = gpu_control {
                    metrics["cpu_feasibility_confirmations"] =
                        json!(assessor.cpu_feasibility_confirmations);
                    result["gpu_control"] = metrics;
                }
                if let Some(metrics) = &gpu_packing {
                    result["gpu_packing"] = metrics.clone();
                }
                if let Some(metrics) = &gpu_preparation {
                    result["gpu_preparation"] = metrics.clone();
                }
                result["execution"] = json!("sparse-tensor-proposal");
                result["guard_policy"] = json!("original-residual-checkpoint-v1");
                result["fast_config"] = json!(fast);
                result["initial_fast_lanes"] = json!(fast_shapes);
                if fast.is_some_and(|f| f.host_certificates) {
                    result["cached_assessments"] = json!(cached_assessments);
                }
                if fast.is_some_and(|f| f.auto_schedule) {
                    result["selected_schedule"] = json!(if selected_format.components() == 0 {
                        "sparse"
                    } else if selected_combined {
                        "combined"
                    } else {
                        "split"
                    });
                }
            }
            if let Some(timing) = profile.finish() {
                result["solver_profile"] = timing;
                result["elapsed_ns"] = json!(started.elapsed().as_nanos());
            }
            Ok(result)
        },
    )
}
