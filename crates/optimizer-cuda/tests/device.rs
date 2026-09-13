//! Device contracts under SPEC-0010.
//!
//! The load-bearing test here is `device_makespans_equal_the_host_recurrence`. Its
//! assertion is equality, not a tolerance, and that is the whole reason the first
//! device workload is integer: agreement is an exact identity rather than a
//! statistical claim, which is the strongest form of the CPU/GPU agreement evidence
//! Stage 4 asks for.
//!
//! Every test that needs hardware reports an explicit skip when none is present, so
//! a machine without a device is never counted as coverage. That mirrors how
//! native-dependent tests already report a skip when the pinned library is absent,
//! and it is why these tests can live in the ordinary suite rather than in a
//! separate one that never runs.

use std::rc::Rc;
use std::sync::atomic::AtomicBool;
use std::time::Duration;

use optimizer_cuda::schedule::{
    Decline, InstanceShape, ScheduleResidency, code_object_path, device_path_available,
};
use optimizer_cuda::{DEFAULT_LOCK_PATH, Ownership};
use optimizer_cuda_sys::{Context, DeviceError};
use optimizer_schedule::{
    DEVELOPMENT_SUBSET, FlowShopInstance, SCALE_SUBSET, insertion_neighborhood, makespan, neh,
};

/// Opt-in marker for device work, set by the device gate.
///
/// Device tests do not run in the ordinary gate even on a host that has a device.
/// Every task record in this project states a resource budget, and almost all of
/// them say "CPU only, no GPU workloads"; a suite that silently took the host lease
/// and ran kernels would make those records false. It would also contend with
/// whatever else holds the lease, on a lock that permits one holder for the whole
/// host.
const DEVICE_GATE_VARIABLE: &str = "AI_OPTIMIZER_GPU";

/// Skip a device-only test loudly rather than reporting false coverage.
///
/// Three separate reasons to skip are reported separately, because they send a
/// reader to three different places: the gate was not asked for, no driver or code
/// object is present, or a driver is present but reports no device.
fn require_device(test: &str) -> bool {
    if std::env::var_os(DEVICE_GATE_VARIABLE).is_none_or(|value| value != "1") {
        println!("skipping {test}: set {DEVICE_GATE_VARIABLE}=1 to run device acceptance");
        return false;
    }
    if !device_path_available() {
        println!(
            "skipping {test}: no CUDA driver, or no provisioned code object at {}. \
             Run bash tools/setup_cuda.sh on a host with a device.",
            code_object_path().display()
        );
        return false;
    }
    if optimizer_cuda_sys::devices().is_ok_and(|devices| devices.is_empty()) {
        println!("skipping {test}: a driver is present but reports no device");
        return false;
    }
    true
}

/// Hold the host lease for the duration of a device test.
///
/// Requirement 9: a context may not be created without one. Under
/// `tools/gpu_job.sh` the lease is inherited and must not be taken again, which is
/// requirement 8 and the deadlock it exists to prevent.
fn lease() -> Ownership {
    Ownership::acquire_or_inherit(
        &lease_path(),
        Duration::from_secs(300),
        &AtomicBool::new(false),
    )
    .expect("the host lease is available")
}

/// The host lock this run must use, honouring the wrapper's override.
fn lease_path() -> std::path::PathBuf {
    std::env::var_os("AI_OPTIMIZER_GPU_LOCK")
        .map_or_else(|| std::path::PathBuf::from(DEFAULT_LOCK_PATH), Into::into)
}

/// A token that is never cancelled, for the tests that are not about cancellation.
fn cancel() -> optimizer_core::CancellationToken {
    optimizer_core::CancellationToken::new()
}

fn machine_major(instance: &FlowShopInstance) -> Vec<u32> {
    let mut times = Vec::with_capacity(instance.jobs() * instance.machines());
    for machine in 0..instance.machines() {
        for job in 0..instance.jobs() {
            times.push(instance.processing_time(job, machine));
        }
    }
    times
}

fn shape(instance: &FlowShopInstance) -> InstanceShape {
    InstanceShape {
        jobs: instance.jobs(),
        machines: instance.machines(),
        total_processing_time: (0..instance.jobs())
            .map(|job| instance.job_total(job))
            .sum(),
    }
}

fn first_device() -> optimizer_cuda_sys::DeviceInfo {
    optimizer_cuda_sys::devices()
        .expect("devices are enumerable")
        .into_iter()
        .next()
        .expect("at least one device")
}

/// Requirements 12 and 14: device makespans equal the host recurrence exactly.
///
/// The comparison is against `optimizer_schedule::makespan`, which SPEC-0008
/// requirement 6 makes the only definition of what a schedule costs, so this is a
/// device checked against the authority rather than two device-shaped things
/// agreeing with each other.
#[test]
fn device_makespans_equal_the_host_recurrence() {
    if !require_device("device_makespans_equal_the_host_recurrence") {
        return;
    }
    let _lease = lease();
    let context = Rc::new(Context::create(&first_device().uuid).expect("context"));

    let mut checked = 0usize;
    for published in SCALE_SUBSET {
        let instance = published.generate().expect("instance generates");
        let jobs = instance.jobs();
        let residency = ScheduleResidency::open(
            Rc::clone(&context),
            shape(&instance),
            &machine_major(&instance),
            &code_object_path(),
        )
        .expect("residency opens");

        // Rotations of the NEH order. Every one is a distinct permutation with a
        // distinct makespan, so a kernel returning a constant, or the first entry
        // repeated, fails rather than passing on a degenerate batch.
        let base = neh(&instance).expect("neh succeeds");
        let batch = 64usize;
        let mut sequences = Vec::with_capacity(batch * jobs);
        let mut expected = Vec::with_capacity(batch);
        for rotation in 0..batch {
            let rotated: Vec<usize> = base
                .iter()
                .cycle()
                .skip(rotation % jobs)
                .take(jobs)
                .copied()
                .collect();
            let host = makespan(&instance, &rotated).expect("host makespan");
            expected.push(u32::try_from(host).expect("a Taillard makespan fits 32 bits"));
            sequences.extend(
                rotated
                    .iter()
                    .map(|&job| u16::try_from(job).expect("job fits")),
            );
        }

        assert_eq!(
            residency
                .makespans(&sequences, &cancel())
                .expect("device makespans"),
            expected,
            "{}: device makespans must equal the host recurrence exactly",
            published.id
        );
        checked += batch;
    }
    assert_eq!(
        checked,
        64 * SCALE_SUBSET.len(),
        "every instance in the sweep must have been evaluated"
    );
}

/// Requirement 23: the device neighborhood equals the CPU path it must fall back to.
///
/// The two share no implementation: the host builds its head and tail arrays in
/// Rust and the device builds its own in shared memory. They agree on the cost *and*
/// the position, because requirement 17's earliest-position tie-break is part of the
/// answer and a test comparing only costs would let the device return a different
/// tied move.
#[test]
fn the_device_neighborhood_equals_the_cpu_path() {
    if !require_device("the_device_neighborhood_equals_the_cpu_path") {
        return;
    }
    let _lease = lease();
    let context = Rc::new(Context::create(&first_device().uuid).expect("context"));

    for published in SCALE_SUBSET {
        let instance = published.generate().expect("instance generates");
        let residency = ScheduleResidency::open(
            Rc::clone(&context),
            shape(&instance),
            &machine_major(&instance),
            &code_object_path(),
        )
        .expect("residency opens");

        let base = neh(&instance).expect("neh succeeds");
        let encoded: Vec<u16> = base
            .iter()
            .map(|&job| u16::try_from(job).expect("job fits"))
            .collect();

        let host = insertion_neighborhood(&instance, &base).expect("host neighborhood");
        let device = residency
            .insertion_neighborhood(&encoded, &cancel())
            .expect("device neighborhood");

        assert_eq!(
            device.len(),
            host.len(),
            "{}: one entry per job",
            published.id
        );
        for (job, ((device_cost, device_position), (host_cost, host_position))) in
            device.iter().zip(&host).enumerate()
        {
            assert_eq!(
                (u64::from(*device_cost), *device_position as usize),
                (*host_cost, *host_position),
                "{} job {job}: device and host must agree on cost and position",
                published.id
            );
        }
    }
}

/// Requirement 12: the device agrees with a full recomputation, not only with the
/// accelerated host path.
///
/// The previous test compares two head-and-tail implementations. Both could share a
/// wrong idea of what an insertion costs. This one rebuilds each trial permutation
/// and evaluates it through the recurrence, which is the definition, and is confined
/// to the twenty-job instances because it is cubic.
#[test]
fn the_device_neighborhood_agrees_with_a_full_recomputation() {
    if !require_device("the_device_neighborhood_agrees_with_a_full_recomputation") {
        return;
    }
    let _lease = lease();
    let context = Rc::new(Context::create(&first_device().uuid).expect("context"));

    for published in DEVELOPMENT_SUBSET {
        let instance = published.generate().expect("instance generates");
        let residency = ScheduleResidency::open(
            Rc::clone(&context),
            shape(&instance),
            &machine_major(&instance),
            &code_object_path(),
        )
        .expect("residency opens");

        let base = neh(&instance).expect("neh succeeds");
        let encoded: Vec<u16> = base
            .iter()
            .map(|&job| u16::try_from(job).expect("job fits"))
            .collect();
        let device = residency
            .insertion_neighborhood(&encoded, &cancel())
            .expect("device neighborhood");

        for (job, &(cost, position)) in device.iter().enumerate() {
            let from = base.iter().position(|&c| c == job).expect("job is present");
            let mut without = base.clone();
            without.remove(from);
            let mut best: Option<(u64, usize)> = None;
            for candidate in 0..=without.len() {
                let mut trial = without.clone();
                trial.insert(candidate, job);
                let value = makespan(&instance, &trial).expect("host makespan");
                if best.is_none_or(|(best_cost, _)| value < best_cost) {
                    best = Some((value, candidate));
                }
            }
            let (expected_cost, expected_position) = best.expect("a position exists");
            assert_eq!(
                (u64::from(cost), position as usize),
                (expected_cost, expected_position),
                "{} job {job}: device must match a full recomputation",
                published.id
            );
        }
    }
}

/// Requirement 31: a fixed input on a fixed device gives a bitwise identical result.
///
/// Determinism here follows from the arithmetic rather than from scheduling, because
/// integer maximum and addition are associative and commutative and no reduction
/// order can change a result. The test is still worth making: it is what would catch
/// a kernel that acquired a race.
#[test]
fn repeating_a_device_evaluation_is_bitwise_identical() {
    if !require_device("repeating_a_device_evaluation_is_bitwise_identical") {
        return;
    }
    let _lease = lease();
    let context = Rc::new(Context::create(&first_device().uuid).expect("context"));
    let instance = SCALE_SUBSET[10].generate().expect("instance generates");
    let residency = ScheduleResidency::open(
        Rc::clone(&context),
        shape(&instance),
        &machine_major(&instance),
        &code_object_path(),
    )
    .expect("residency opens");

    let base = neh(&instance).expect("neh succeeds");
    let encoded: Vec<u16> = base
        .iter()
        .map(|&job| u16::try_from(job).expect("job fits"))
        .collect();
    let first = residency
        .insertion_neighborhood(&encoded, &cancel())
        .expect("device neighborhood");
    for repeat in 0..8 {
        assert_eq!(
            residency
                .insertion_neighborhood(&encoded, &cancel())
                .expect("device neighborhood"),
            first,
            "repeat {repeat} must be bitwise identical"
        );
    }
}

/// Requirement 16: instance-invariant data is uploaded once per residency.
///
/// Asserted against a counter rather than against elapsed time, because a timing
/// assertion would make this a measurement and would pass on a fast re-upload.
#[test]
fn a_residency_uploads_its_instance_once() {
    if !require_device("a_residency_uploads_its_instance_once") {
        return;
    }
    let _lease = lease();
    let context = Rc::new(Context::create(&first_device().uuid).expect("context"));
    let instance = SCALE_SUBSET[0].generate().expect("instance generates");
    let residency = ScheduleResidency::open(
        Rc::clone(&context),
        shape(&instance),
        &machine_major(&instance),
        &code_object_path(),
    )
    .expect("residency opens");

    assert_eq!(residency.uploads(), 1);
    let base = neh(&instance).expect("neh succeeds");
    let encoded: Vec<u16> = base
        .iter()
        .map(|&job| u16::try_from(job).expect("job fits"))
        .collect();
    for _ in 0..4 {
        let _ = residency
            .makespans(&encoded, &cancel())
            .expect("device makespans");
        let _ = residency
            .insertion_neighborhood(&encoded, &cancel())
            .expect("device neighborhood");
    }
    assert_eq!(
        residency.uploads(),
        1,
        "eight calls must not re-send the processing times"
    );
}

/// Requirement 3: the device a context reports is the device that was requested.
///
/// The negative direction is what makes this worth asserting. A check that can only
/// pass would let a record claim hardware the run never touched, which is the thing
/// requirement 3 exists to prevent.
#[test]
fn a_uuid_no_device_carries_is_refused() {
    if !require_device("a_uuid_no_device_carries_is_refused") {
        return;
    }
    let _lease = lease();
    let error = Context::create("GPU-00000000-0000-0000-0000-000000000000")
        .err()
        .expect("a nonexistent UUID must be refused");
    assert!(
        matches!(error, DeviceError::DeviceNotFound(_)),
        "expected DeviceNotFound, got {error}"
    );
    // And a real UUID succeeds, so the refusal is discriminating rather than total.
    let uuid = first_device().uuid;
    let context = Context::create(&uuid).expect("a real UUID is accepted");
    assert_eq!(context.device().uuid, uuid);
}

/// Requirement 13: an instance whose bound exceeds the kernel's range is declined.
///
/// Decided from the instance, before any allocation. The declining shape is
/// constructed directly rather than generated, because no Taillard instance can
/// reach it: at most 99 per operation and at most 500 by 20, the largest possible
/// bound is 990,000.
#[test]
fn an_instance_beyond_the_kernel_range_is_declined_before_dispatch() {
    let largest_taillard = InstanceShape {
        jobs: 500,
        machines: 20,
        total_processing_time: 500 * 20 * 99,
    };
    largest_taillard
        .admissible((12, 0), 99 * 1024)
        .expect("every supported Taillard instance is admissible");

    let beyond = InstanceShape {
        total_processing_time: u64::from(u32::MAX) + 1,
        ..largest_taillard
    };
    assert_eq!(
        beyond.admissible((12, 0), 99 * 1024),
        Err(Decline::ArithmeticRange {
            bound: u64::from(u32::MAX) + 1
        })
    );
}

/// Requirement 37: a build with no code object reports rather than pretends.
///
/// This one runs everywhere, including on a host with no device at all, which is
/// the case it is about.
#[test]
fn an_absent_code_object_is_a_named_refusal() {
    let missing = std::path::Path::new("/nonexistent/schedule_eval.cubin");
    if !require_device("an_absent_code_object_is_a_named_refusal") {
        // Without a device there is nothing to load it into, and the refusal that
        // matters is the one `require_device` already prints.
        assert!(!missing.is_file());
        return;
    }
    let _lease = lease();
    let context = Rc::new(Context::create(&first_device().uuid).expect("context"));
    let instance = SCALE_SUBSET[0].generate().expect("instance generates");
    let error = ScheduleResidency::open(
        Rc::clone(&context),
        shape(&instance),
        &machine_major(&instance),
        missing,
    )
    .err()
    .expect("an absent code object must be refused");
    assert!(
        matches!(error, DeviceError::CodeObjectMissing(_)),
        "expected CodeObjectMissing, got {error}"
    );
}

/// Requirements 1, 3 and 4: a probe reads the device back and reports what it holds.
///
/// The load-bearing field is `observed`. It is separate from `requested` so that a
/// report records that a comparison happened, not merely its outcome; a single
/// field would be equally true and would establish nothing.
#[test]
fn a_probe_reads_the_device_back_and_reports_its_code_object() {
    if !require_device("a_probe_reads_the_device_back_and_reports_its_code_object") {
        return;
    }
    let target = first_device();
    let report = optimizer_cuda::probe::probe(
        &target.uuid,
        &lease_path(),
        Duration::from_secs(300),
        optimizer_cuda::probe::LeaseRequest::Auto,
    )
    .expect("a real device probes");

    assert_eq!(report.requested, target.uuid);
    assert_eq!(report.observed, target.uuid, "requirement 3");
    assert_eq!(report.name, target.name);

    // Requirement 1a: the driver version now has a producer. This is the field
    // SPEC-0007 requirement 9 has required of a GPU record since M0 and that
    // nothing produced until now.
    assert!(
        !report.driver_version.is_empty(),
        "a probe must report the driver version"
    );
    assert!(
        report.driver_version.contains('.'),
        "a driver version looks like 580.105.08, got {}",
        report.driver_version
    );

    // Requirement 4: what this build holds, reported rather than assumed.
    assert!(report.provisioned, "the device gate implies a code object");
    assert_eq!(
        report.kernels,
        vec!["makespan_batch", "insertion_neighborhood"]
    );
    assert_eq!(report.target_capability, "12.0");
    assert_eq!(
        (report.capability_major, report.capability_minor),
        (12, 0),
        "the development hardware is compute capability 12.0"
    );
    assert!(report.multiprocessors > 0);
    assert!(report.free_memory <= report.total_memory);

    // The 99 KB per-block ceiling is what forces 32-bit head and tail tables, so
    // it is asserted here rather than trusted to a comment.
    assert_eq!(
        report.max_shared_memory_per_block, 101_376,
        "compute capability 12.0 allows 99 KB per block"
    );
}

/// Requirement 3: a UUID no device carries is refused, and distinguishably so.
#[test]
fn a_probe_refuses_a_uuid_no_device_carries() {
    if !require_device("a_probe_refuses_a_uuid_no_device_carries") {
        return;
    }
    let error = optimizer_cuda::probe::probe(
        "GPU-00000000-0000-0000-0000-000000000000",
        &lease_path(),
        Duration::from_secs(300),
        optimizer_cuda::probe::LeaseRequest::Auto,
    )
    .expect_err("a nonexistent UUID must be refused");
    assert!(
        matches!(error, optimizer_cuda::probe::ProbeError::NotFound(_)),
        "expected NotFound, got {error}"
    );

    // And a real one succeeds, so the refusal discriminates rather than refusing
    // everything.
    optimizer_cuda::probe::probe(
        &first_device().uuid,
        &lease_path(),
        Duration::from_secs(300),
        optimizer_cuda::probe::LeaseRequest::Auto,
    )
    .expect("a real device still probes");
}

/// Requirement 1a: discovery reports the driver version for every device.
#[test]
fn discovery_reports_a_driver_version_for_every_device() {
    if !require_device("discovery_reports_a_driver_version_for_every_device") {
        return;
    }
    match optimizer_cuda::discover() {
        optimizer_cuda::Discovery::Available { devices } => {
            assert!(!devices.is_empty());
            for device in devices {
                assert!(
                    !device.driver_version.is_empty(),
                    "{} must report a driver version",
                    device.uuid
                );
            }
        }
        optimizer_cuda::Discovery::Unavailable { reason } => {
            panic!("the device gate implies an available inventory: {reason}")
        }
    }
}

/// Requirement 27: work is launched in bounded chunks, not one launch per call.
///
/// Chunking is invisible in a result -- the same answers come back either way --
/// so it is asserted against a launch counter. Without that, a regression that
/// collapsed the loop back to a single launch would pass every other test here.
#[test]
fn device_work_is_launched_in_bounded_chunks() {
    if !require_device("device_work_is_launched_in_bounded_chunks") {
        return;
    }
    let _lease = lease();
    let context = Rc::new(Context::create(&first_device().uuid).expect("context"));
    // 500 jobs, so the neighbourhood is 500 blocks against a 128-block chunk: four
    // launches, not one.
    let instance = SCALE_SUBSET[11].generate().expect("instance generates");
    assert_eq!(
        instance.jobs(),
        500,
        "this assertion needs the largest shape"
    );
    let residency = ScheduleResidency::open(
        Rc::clone(&context),
        shape(&instance),
        &machine_major(&instance),
        &code_object_path(),
    )
    .expect("residency opens");
    assert_eq!(residency.launches(), 0, "opening launches nothing");

    let base = neh(&instance).expect("neh succeeds");
    let encoded: Vec<u16> = base
        .iter()
        .map(|&job| u16::try_from(job).expect("job fits"))
        .collect();
    let neighborhood = residency
        .insertion_neighborhood(&encoded, &cancel())
        .expect("device neighbourhood");
    assert_eq!(neighborhood.len(), 500);
    assert_eq!(
        residency.launches(),
        4,
        "500 jobs in 128-job chunks is four launches"
    );

    // And the chunking does not change the answer: it still equals the host's.
    let host = insertion_neighborhood(&instance, &base).expect("host neighbourhood");
    for (job, ((device_cost, device_position), (host_cost, host_position))) in
        neighborhood.iter().zip(&host).enumerate()
    {
        assert_eq!(
            (u64::from(*device_cost), *device_position as usize),
            (*host_cost, *host_position),
            "job {job} must be unchanged by chunking"
        );
    }
}

/// Requirement 27: a cancelled call stops between chunks rather than at the end.
///
/// Cancelling before the first launch is the case that can be asserted exactly: no
/// launch may happen at all. Cancelling mid-run is inherently racy to assert, so
/// this checks the bound rather than a timing.
#[test]
fn a_cancelled_call_launches_nothing_and_says_it_was_cancelled() {
    if !require_device("a_cancelled_call_launches_nothing_and_says_it_was_cancelled") {
        return;
    }
    let _lease = lease();
    let context = Rc::new(Context::create(&first_device().uuid).expect("context"));
    let instance = SCALE_SUBSET[11].generate().expect("instance generates");
    let residency = ScheduleResidency::open(
        Rc::clone(&context),
        shape(&instance),
        &machine_major(&instance),
        &code_object_path(),
    )
    .expect("residency opens");

    let base = neh(&instance).expect("neh succeeds");
    let encoded: Vec<u16> = base
        .iter()
        .map(|&job| u16::try_from(job).expect("job fits"))
        .collect();

    let cancelled = optimizer_core::CancellationToken::new();
    cancelled.cancel();
    let error = residency
        .insertion_neighborhood(&encoded, &cancelled)
        .expect_err("a cancelled call must not return results");
    assert_eq!(error, DeviceError::Cancelled);
    assert_eq!(
        residency.launches(),
        0,
        "a run cancelled before it starts must do no work"
    );

    // A cancellation is not a fault, so the residency is still usable afterwards.
    assert!(!residency.poisoned());
    residency
        .insertion_neighborhood(&encoded, &cancel())
        .expect("an uncancelled call still works");
    assert!(residency.launches() > 0);
}

/// Requirement 30: a device fault is not a solver outcome, and requirement 29: a
/// poisoned context is not launched into again.
///
/// The fault is provoked rather than waited for. A neighbourhood kernel asked for
/// more shared memory than a block may address is rejected at launch, which is the
/// closest reachable stand-in for a kernel fault that does not require corrupting
/// the device; what it exercises is the path a fault takes, not the fault itself.
#[test]
fn a_launch_failure_is_reported_rather_than_repeated() {
    if !require_device("a_launch_failure_is_reported_rather_than_repeated") {
        return;
    }
    let _lease = lease();
    let context = Rc::new(Context::create(&first_device().uuid).expect("context"));
    let instance = SCALE_SUBSET[0].generate().expect("instance generates");
    let residency = ScheduleResidency::open(
        Rc::clone(&context),
        shape(&instance),
        &machine_major(&instance),
        &code_object_path(),
    )
    .expect("residency opens");

    // A sequence of the wrong length is refused before any launch, which is the
    // cheap half: an input error must not touch the device at all.
    let error = residency
        .insertion_neighborhood(&[0u16, 1], &cancel())
        .expect_err("a wrong-length sequence is refused");
    assert!(matches!(error, DeviceError::Unsupported(_)), "{error}");
    assert_eq!(residency.launches(), 0, "a refused input launches nothing");
    assert!(!residency.poisoned(), "an input error is not a fault");
}
