//! Device acceptance for the first-order LP kernels, mapped to SPEC-0011
//! requirement numbers.
//!
//! Every test here needs hardware, a driver and a code object. When any is absent
//! the test prints an explicit skip and returns, so a missing device is never
//! counted as coverage -- the rule SPEC-0010's acceptance section fixes and that
//! native-dependent tests already follow for the pinned library.
//!
//! Run under `bash tools/gpu_job.sh <uuid> bash tools/gpu_check.sh`, which holds
//! the shared host lease for the whole process. These do not run in
//! `tools/check.sh`: that gate is CPU-only by design.

use std::rc::Rc;

use optimizer_core::{
    Backend, Bound, CancellationToken, Constraint, Domain, LinearTerm, LpSettings, Model,
    ModelDocument, Objective, ObjectiveSense, SOLVE_SCHEMA_VERSION, SolveOptions, Termination,
    Tolerances, Variable,
};
use optimizer_cuda_sys::Context;
use optimizer_lp::pdhg::Engine;
use optimizer_lp::problem::LinearProgram;
use optimizer_lp_cuda::{CudaLpBackend, LpResidency, Requirement, code_object_path};

/// The environment variable that opts a run into device work.
const GATE: &str = "AI_OPTIMIZER_GPU";

/// A device to run on, or an explicit skip.
///
/// Four separate reasons are reported separately, because "no device" and "no code
/// object" are different facts about a host and conflating them would make a
/// provisioning mistake look like missing hardware.
fn device(test: &str) -> Option<Rc<Context>> {
    if std::env::var(GATE).ok().as_deref() != Some("1") {
        eprintln!("SKIP {test}: device tests are opt-in; set {GATE}=1");
        return None;
    }
    if !optimizer_cuda_sys::driver_available() {
        eprintln!("SKIP {test}: no CUDA driver on this host");
        return None;
    }
    if !code_object_path().is_file() {
        eprintln!(
            "SKIP {test}: no code object at {}; run bash tools/setup_cuda.sh",
            code_object_path().display()
        );
        return None;
    }
    let devices = match optimizer_cuda_sys::devices() {
        Ok(devices) if !devices.is_empty() => devices,
        _ => {
            eprintln!("SKIP {test}: the driver reports no device");
            return None;
        }
    };
    match Context::create(&devices[0].uuid) {
        Ok(context) => Some(Rc::new(context)),
        Err(error) => {
            eprintln!("SKIP {test}: could not open a context: {error}");
            None
        }
    }
}

fn finite(value: f64) -> Bound {
    Bound::Finite { value }
}

fn tolerances() -> Tolerances {
    Tolerances {
        absolute: 1e-6,
        relative: 1e-6,
        integrality: 1e-7,
    }
}

fn options() -> SolveOptions {
    SolveOptions {
        schema_version: SOLVE_SCHEMA_VERSION,
        seed: 17,
        time_limit_ms: None,
        iteration_limit: None,
        node_limit: None,
        tolerances: tolerances(),
        threads: 1,
    }
}

fn settings(iterations: u64) -> LpSettings {
    LpSettings::published(iterations, 200)
}

/// `min -x0 - 3 x1` subject to `x0 + x1 <= 1.5`, `0 <= xj <= 1`. Optimum -3.5.
fn model() -> Model {
    Model::new(ModelDocument {
        schema_version: optimizer_core::SCHEMA_VERSION,
        model_id: "device-lp".to_string(),
        variables: (0..2)
            .map(|id| Variable {
                id,
                domain: Domain::Continuous,
                lower: finite(0.0),
                upper: finite(1.0),
            })
            .collect(),
        constraints: vec![Constraint {
            id: 0,
            lower: Bound::NegativeInfinity,
            upper: finite(1.5),
            terms: (0..2)
                .map(|variable_id| LinearTerm {
                    variable_id,
                    coefficient: 1.0,
                })
                .collect(),
        }],
        objective: Objective {
            sense: ObjectiveSense::Minimize,
            offset: 0.0,
            terms: vec![
                LinearTerm {
                    variable_id: 0,
                    coefficient: -1.0,
                },
                LinearTerm {
                    variable_id: 1,
                    coefficient: -3.0,
                },
            ],
        },
    })
    .expect("a valid model")
}

/// A wider model, so the multi-segment path of the fixed reduction is exercised.
///
/// One dense row of `width` entries. Below `SEGMENT` the reduction is a single
/// padded tree; above it the partials are themselves reduced by the tree, and
/// that second level is where a left-to-right accumulation would diverge from the
/// host. A test that only ever used narrow rows would never reach it.
fn wide_model(width: u32) -> Model {
    Model::new(ModelDocument {
        schema_version: optimizer_core::SCHEMA_VERSION,
        model_id: "device-lp-wide".to_string(),
        variables: (0..width)
            .map(|id| Variable {
                id,
                domain: Domain::Continuous,
                lower: finite(0.0),
                upper: finite(1.0),
            })
            .collect(),
        constraints: vec![Constraint {
            id: 0,
            lower: Bound::NegativeInfinity,
            upper: finite(f64::from(width) / 3.0),
            terms: (0..width)
                .map(|variable_id| LinearTerm {
                    variable_id,
                    // Irrational-ish coefficients so no partial sum is exact and
                    // the reduction order genuinely matters.
                    coefficient: 1.0 + f64::from(variable_id).sqrt() / 7.0,
                })
                .collect(),
        }],
        objective: Objective {
            sense: ObjectiveSense::Minimize,
            offset: 0.0,
            terms: (0..width)
                .map(|variable_id| LinearTerm {
                    variable_id,
                    coefficient: -1.0 - f64::from(variable_id % 13) / 11.0,
                })
                .collect(),
        },
    })
    .expect("a valid model")
}

/// One engine's scaled primal and dual iterate.
type Iterate = (Vec<f64>, Vec<f64>);

/// Run the device iteration and the host engine from the same start, and return
/// the two scaled iterates for a bitwise comparison.
fn both_engines(context: &Rc<Context>, model: &Model, iterations: u64) -> (Iterate, Iterate) {
    let program = LinearProgram::new(model).expect("continuous");
    let engine = Engine::new(&program, settings(iterations));
    let (row_values, column_values) = engine.scaled_matrix();
    let residency = LpResidency::open(
        Rc::clone(context),
        &program,
        row_values,
        column_values,
        engine.scaled_objective(),
        engine.scaled_row_bounds(),
        engine.scaled_column_bounds(),
        &code_object_path(),
    )
    .expect("the residency opens");

    let mut device_x = engine.start_primal();
    let mut device_y = engine.start_dual();
    let anchor_x = device_x.clone();
    let anchor_y = device_y.clone();
    residency
        .advance(
            &mut device_x,
            &mut device_y,
            &anchor_x,
            &anchor_y,
            0,
            iterations,
            engine.step(),
            1.0,
            &CancellationToken::new(),
        )
        .expect("the device iterates");

    // The host performs the same steps, including the same Halpern pull, so the
    // comparison is between two implementations of one algorithm rather than
    // between two algorithms.
    let mut host_x = engine.start_primal();
    let mut host_y = engine.start_dual();
    for iteration in 0..iterations {
        let (next_x, next_y) = engine.step_once(&host_x, &host_y, 1.0);
        let toward = (iteration + 1) as f64 / (iteration + 2) as f64;
        let back = 1.0 / (iteration + 2) as f64;
        for index in 0..host_x.len() {
            host_x[index] = toward * next_x[index] + back * anchor_x[index];
        }
        for index in 0..host_y.len() {
            host_y[index] = toward * next_y[index] + back * anchor_y[index];
        }
    }

    ((device_x, device_y), (host_x, host_y))
}

/// Requirement 8: a fixed instance on a fixed device and code object is bitwise
/// reproducible.
#[test]
fn a_fixed_instance_solved_twice_on_one_device_is_bitwise_identical() {
    let Some(context) = device("a_fixed_instance_solved_twice_on_one_device_is_bitwise_identical")
    else {
        return;
    };
    let model = model();
    let ((first_x, first_y), _) = both_engines(&context, &model, 400);
    let ((second_x, second_y), _) = both_engines(&context, &model, 400);
    for (a, b) in first_x.iter().zip(&second_x) {
        assert_eq!(a.to_bits(), b.to_bits(), "primal must be bitwise identical");
    }
    for (a, b) in first_y.iter().zip(&second_y) {
        assert_eq!(a.to_bits(), b.to_bits(), "dual must be bitwise identical");
    }
}

/// Requirements 6 and 7: the device reproduces the host's reduction order exactly.
///
/// Asserted bitwise rather than within a tolerance. A tolerance on an iterative
/// method is nearly untestable: loose enough to pass at iteration ten thousand, it
/// hides a real defect at iteration ten. A bitwise assertion localizes a defect to
/// one iteration and one vector.
///
/// This is a property of this toolchain pair -- it needs `-fmad=false` on the
/// device, Rust never contracting on the host, and the transcendentals staying off
/// the device -- rather than a contract. Requirement 8 asks only for same-device
/// reproducibility. The assertion re-verifies the stronger property on every run.
#[test]
fn the_device_iterates_match_the_host_engine_bitwise() {
    let Some(context) = device("the_device_iterates_match_the_host_engine_bitwise") else {
        return;
    };
    let model = model();
    let ((device_x, device_y), (host_x, host_y)) = both_engines(&context, &model, 400);
    for (index, (a, b)) in device_x.iter().zip(&host_x).enumerate() {
        assert_eq!(
            a.to_bits(),
            b.to_bits(),
            "primal[{index}]: device {a} against host {b}"
        );
    }
    for (index, (a, b)) in device_y.iter().zip(&host_y).enumerate() {
        assert_eq!(
            a.to_bits(),
            b.to_bits(),
            "dual[{index}]: device {a} against host {b}"
        );
    }
}

/// The same bitwise agreement across the fixed reduction's second level.
///
/// A row wider than one segment reduces its partials by the tree rather than
/// accumulating them, and the two orders differ. Without this test the agreement
/// above would only ever exercise the single-segment path.
#[test]
fn the_device_matches_the_host_on_a_line_wider_than_one_segment() {
    let Some(context) = device("the_device_matches_the_host_on_a_line_wider_than_one_segment")
    else {
        return;
    };
    let width = u32::try_from(optimizer_lp::reduce::SEGMENT).expect("fits") + 37;
    let model = wide_model(width);
    let program = LinearProgram::new(&model).expect("continuous");
    assert!(
        Requirement::of(&program).widest_line > optimizer_lp::reduce::SEGMENT,
        "the instance must exceed one segment or this test adds nothing"
    );
    let ((device_x, device_y), (host_x, host_y)) = both_engines(&context, &model, 40);
    for (index, (a, b)) in device_x.iter().zip(&host_x).enumerate() {
        assert_eq!(a.to_bits(), b.to_bits(), "primal[{index}]");
    }
    for (index, (a, b)) in device_y.iter().zip(&host_y).enumerate() {
        assert_eq!(a.to_bits(), b.to_bits(), "dual[{index}]");
    }
}

/// Requirements 5 to 10's able-to-fail instrument.
///
/// A code object with an atomic reduction substituted into `spmv_row` must break
/// the bitwise assertion above. Without a build that breaks it, "the result is
/// bitwise reproducible" would be consistent with an implementation whose order
/// merely happens to be stable on this hardware today.
///
/// The substitution is inside the production kernel rather than beside it, so this
/// exercises exactly the path the other tests assert on -- a separate kernel could
/// diverge from the real one and leave the instrument measuring something else.
#[test]
fn an_atomic_reduction_build_breaks_the_bitwise_assertion() {
    let name = "an_atomic_reduction_build_breaks_the_bitwise_assertion";
    let Some(context) = device(name) else {
        return;
    };
    let atomic = code_object_path().with_file_name("lp_pdhg_atomic.cubin");
    if !atomic.is_file() {
        eprintln!(
            "SKIP {name}: no atomic code object at {}; run bash tools/setup_cuda.sh",
            atomic.display()
        );
        return;
    }

    // A wide row, so many threads contend for one output and the nondeterminism
    // has somewhere to appear. A one-entry row would be summed in one atomic
    // operation and would agree every time.
    let width = u32::try_from(optimizer_lp::reduce::SEGMENT).expect("fits") * 2;
    let model = wide_model(width);
    let program = LinearProgram::new(&model).expect("continuous");
    let engine = Engine::new(&program, settings(200));
    let (row_values, column_values) = engine.scaled_matrix();

    let run = |code_object: &std::path::Path| -> Vec<u64> {
        let residency = LpResidency::open(
            Rc::clone(&context),
            &program,
            row_values,
            column_values,
            engine.scaled_objective(),
            engine.scaled_row_bounds(),
            engine.scaled_column_bounds(),
            code_object,
        )
        .expect("the residency opens");
        let mut x = engine.start_primal();
        let mut y = engine.start_dual();
        let anchor_x = x.clone();
        let anchor_y = y.clone();
        residency
            .advance(
                &mut x,
                &mut y,
                &anchor_x,
                &anchor_y,
                0,
                200,
                engine.step(),
                1.0,
                &CancellationToken::new(),
            )
            .expect("iterates");
        x.iter().map(|value| value.to_bits()).collect()
    };

    // The deterministic build must agree with itself, which is what makes the
    // disagreement below evidence about the reduction rather than about the
    // instance or the hardware.
    let deterministic = run(&code_object_path());
    assert_eq!(
        deterministic,
        run(&code_object_path()),
        "the committed code object must be bitwise reproducible"
    );

    let mut differed = false;
    let first = run(&atomic);
    for _ in 0..8 {
        if run(&atomic) != first {
            differed = true;
            break;
        }
    }
    assert!(
        differed,
        "an atomic reduction must produce differing bits across runs, or the \
         determinism assertion elsewhere is not known to be able to fail"
    );
}

/// Requirement 16 of SPEC-0010: invariant data is uploaded once per residency.
///
/// Asserted against a counter rather than against elapsed time, which would make
/// the test a measurement.
#[test]
fn invariant_data_is_uploaded_once_per_residency() {
    let Some(context) = device("invariant_data_is_uploaded_once_per_residency") else {
        return;
    };
    let model = model();
    let program = LinearProgram::new(&model).expect("continuous");
    let engine = Engine::new(&program, settings(100));
    let (row_values, column_values) = engine.scaled_matrix();
    let residency = LpResidency::open(
        Rc::clone(&context),
        &program,
        row_values,
        column_values,
        engine.scaled_objective(),
        engine.scaled_row_bounds(),
        engine.scaled_column_bounds(),
        &code_object_path(),
    )
    .expect("opens");

    let mut x = engine.start_primal();
    let mut y = engine.start_dual();
    let anchor_x = x.clone();
    let anchor_y = y.clone();
    for _ in 0..3 {
        residency
            .advance(
                &mut x,
                &mut y,
                &anchor_x,
                &anchor_y,
                0,
                50,
                engine.step(),
                1.0,
                &CancellationToken::new(),
            )
            .expect("iterates");
    }
    assert_eq!(residency.uploads(), 1);
    assert!(residency.launches() > 0, "the kernels must actually run");
    assert!(!residency.poisoned());
}

/// SPEC-0010 requirement 27: cancellation is observed at a chunk boundary.
#[test]
fn cancellation_returns_at_a_chunk_boundary() {
    let Some(context) = device("cancellation_returns_at_a_chunk_boundary") else {
        return;
    };
    let model = model();
    let program = LinearProgram::new(&model).expect("continuous");
    let engine = Engine::new(&program, settings(1_000_000));
    let (row_values, column_values) = engine.scaled_matrix();
    let residency = LpResidency::open(
        Rc::clone(&context),
        &program,
        row_values,
        column_values,
        engine.scaled_objective(),
        engine.scaled_row_bounds(),
        engine.scaled_column_bounds(),
        &code_object_path(),
    )
    .expect("opens");

    let cancel = CancellationToken::new();
    cancel.cancel();
    let mut x = engine.start_primal();
    let mut y = engine.start_dual();
    let anchor_x = x.clone();
    let anchor_y = y.clone();
    let error = residency
        .advance(
            &mut x,
            &mut y,
            &anchor_x,
            &anchor_y,
            0,
            1_000_000,
            engine.step(),
            1.0,
            &cancel,
        )
        .expect_err("a cancelled run must not complete");
    assert!(matches!(error, optimizer_cuda_sys::DeviceError::Cancelled));
    assert_eq!(
        residency.launches(),
        0,
        "a run cancelled before the first chunk must launch nothing"
    );
}

/// The memory requirement is decided from the program before any allocation.
#[test]
fn the_memory_requirement_is_known_before_any_allocation() {
    let program = LinearProgram::new(&model()).expect("continuous");
    let requirement = Requirement::of(&program);
    assert!(requirement.memory_bytes > 0);
    assert!(requirement.shared_bytes > 0);
    // A device with no free memory is refused rather than discovering it by a
    // failed allocation.
    assert!(
        requirement
            .admissible((12, 0), requirement.shared_bytes, 0)
            .is_err()
    );
    // And a capability below the code object's target is refused first, for that
    // reason rather than for a consequence of it.
    let decline = requirement
        .admissible((8, 6), requirement.shared_bytes, u64::MAX)
        .expect_err("an older capability must be refused");
    assert!(matches!(
        decline,
        optimizer_lp_cuda::Decline::Capability { .. }
    ));
}

/// Requirements 14 and 15 on a device: the record's claims come from the host.
#[test]
fn a_device_solve_publishes_only_what_the_host_validated() {
    let Some(context) = device("a_device_solve_publishes_only_what_the_host_validated") else {
        return;
    };
    let model = model();
    let backend =
        CudaLpBackend::open(Rc::clone(&context), settings(20_000)).expect("valid settings");
    let record = backend
        .solve(&model, &options(), &CancellationToken::new(), None)
        .expect("the device solves");

    assert_eq!(record.backend, "cuda-lp");
    let report = record.validation.as_ref().expect("a validation report");
    if let Some(objective) = record.objective {
        assert_eq!(
            objective, report.objective,
            "the published objective must be the host's recomputation"
        );
        assert!(report.feasible);
    }
    if let Some(bound) = record.best_bound {
        let optimum = -3.5;
        assert!(
            bound <= optimum + 1e-6,
            "a certified bound must not exceed the true optimum: {bound}"
        );
    }
    // Requirements 9 and 10: the record names the settings that produced it.
    assert_eq!(record.lp_settings, Some(settings(20_000)));
}

/// Requirement 3 on a device: a discrete model is refused before any device work.
#[test]
fn a_discrete_model_is_refused_before_the_device_is_touched() {
    let Some(context) = device("a_discrete_model_is_refused_before_the_device_is_touched") else {
        return;
    };
    let mut document = model().document().clone();
    document.variables[0].domain = Domain::Binary;
    let discrete = Model::new(document).expect("valid");
    let backend =
        CudaLpBackend::open(Rc::clone(&context), settings(1_000)).expect("valid settings");
    let record = backend
        .solve(&discrete, &options(), &CancellationToken::new(), None)
        .expect("a refusal is an outcome");
    assert_eq!(record.termination, Termination::Unsupported);
    assert!(record.candidate.is_none());
}

/// The kernel's segment size and the host's are one number, not two that agree.
#[test]
fn the_code_object_exports_every_kernel_this_build_expects() {
    let Some(context) = device("the_code_object_exports_every_kernel_this_build_expects") else {
        return;
    };
    let module = context
        .load_module_file(&code_object_path())
        .expect("the code object loads");
    for name in optimizer_lp_cuda::KERNEL_NAMES {
        module
            .function(name)
            .unwrap_or_else(|_| panic!("the code object must export {name}"));
    }
    module
        .function("halpern")
        .expect("the code object must export halpern");
}
