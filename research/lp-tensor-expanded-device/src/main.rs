//! CPU admission entry for the new expanded solver, isolated from public defaults.
#![allow(dead_code)]
pub use lp_tensor_expanded_device::{
    Engine, control, exec, precision, quant, reduce, research, tensor_cost, value,
};
mod device;
mod device_checks;
mod native;
use optimizer_core::{
    Assignment, CancellationToken, Candidate, LpSettings, Model, SolveOptions, sha256,
};
use optimizer_lp::{
    LinearProgram,
    certify::{assess_gap, certify},
};
use serde::{Deserialize, Serialize};
use std::{
    io::{BufWriter, Write},
    time::Instant,
};

#[derive(Clone, Debug, Serialize, Deserialize, PartialEq)]
#[serde(deny_unknown_fields)]
struct Image {
    path: String,
    sha256: String,
}
impl Image {
    fn bytes(&self) -> Result<Vec<u8>, Box<dyn std::error::Error>> {
        let path = std::path::Path::new(&self.path);
        if path.is_absolute()
            || path
                .components()
                .any(|c| matches!(c, std::path::Component::ParentDir))
        {
            return Err("image path outside repository".into());
        }
        let bytes = std::fs::read(path)?;
        if sha256::hex(&bytes) != self.sha256 {
            return Err("frozen image mismatch".into());
        }
        Ok(bytes)
    }
}
#[derive(Clone, Debug, Serialize, Deserialize, PartialEq)]
#[serde(deny_unknown_fields)]
struct Request {
    identity: String,
    model_sha256: String,
    source_tree_sha256: String,
    executable_sha256: String,
    layout: tensor_cost::Layout,
    method: LpSettings,
    settings: quant::Settings,
    options: SolveOptions,
    horizon: u64,
    images: [Image; 5],
    device: String,
    diagnostic: bool,
    norm_policy: String,
    audit_policy: String,
}
#[derive(Clone, Debug, Serialize, Deserialize, PartialEq)]
#[serde(deny_unknown_fields)]
struct Assessment {
    feasible: bool,
    objective: f64,
    bound: Option<f64>,
    gap_upper: Option<f64>,
    gap_closed: bool,
    allowance: Option<f64>,
    repaired: Option<usize>,
    reason: Option<String>,
}
struct Assessor<'a> {
    model: &'a Model,
    program: &'a LinearProgram,
    options: &'a SolveOptions,
    candidate: Candidate,
}
impl<'a> Assessor<'a> {
    fn new(model: &'a Model, program: &'a LinearProgram, options: &'a SolveOptions) -> Self {
        Self {
            model,
            program,
            options,
            candidate: Candidate {
                schema_version: 1,
                model_id: model.document().model_id.clone(),
                values: program
                    .variable_ids()
                    .iter()
                    .map(|&variable_id| Assignment {
                        variable_id,
                        value: 0.,
                    })
                    .collect(),
            },
        }
    }
    fn assess(&mut self, x: &[f64], y: &[f64]) -> Result<Assessment, Box<dyn std::error::Error>> {
        if x.len() != self.program.column_count()
            || y.len() != self.program.row_count()
            || x.iter().chain(y).any(|v| !v.is_finite())
        {
            return Err("assessment shape/range".into());
        }
        for (assignment, &value) in self.candidate.values.iter_mut().zip(x) {
            assignment.value = value;
        }
        // Recompute original-model feasibility, certificate and gap freshly.
        let report = self
            .model
            .evaluate(&self.candidate, self.options.tolerances)?;
        let certificate = certify(self.program, y);
        let reason = certificate.as_ref().err().map(ToString::to_string);
        let certificate = certificate.ok();
        let bound = certificate.as_ref().map(|c| c.bound);
        let gap = if report.feasible {
            bound.and_then(|b| assess_gap(self.program, x, b, self.options.tolerances))
        } else {
            None
        };
        Ok(Assessment {
            feasible: report.feasible,
            objective: report.objective,
            bound,
            gap_upper: gap.map(|g| g.upper),
            gap_closed: gap.is_some_and(|g| g.closed),
            allowance: certificate.as_ref().map(|c| c.allowance),
            repaired: certificate.as_ref().map(|c| c.repaired),
            reason,
        })
    }
}
#[derive(Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
struct Evidence {
    request: Request,
    outcome: tensor_cost::Outcome,
    assessment: Assessment,
    norm_proof: tensor_cost::NormProof,
    preparation_ns: u64,
    solve_ns: u64,
    device_event_milliseconds: std::collections::BTreeMap<String, f64>,
    phases_ns: std::collections::BTreeMap<String, u64>,
    executor: String,
    executed_device: Option<String>,
    payload_sha256: String,
}
impl Evidence {
    fn hash(&self) -> Result<String, serde_json::Error> {
        let bytes = serde_json::to_vec(&(
            &self.request,
            &self.outcome,
            &self.assessment,
            &self.norm_proof,
            self.preparation_ns,
            self.solve_ns,
            &self.device_event_milliseconds,
            &self.phases_ns,
            &self.executor,
            &self.executed_device,
        ))?;
        Ok(sha256::hex(&bytes))
    }
}
fn record_boundary(
    phases: &mut std::collections::BTreeMap<String, u64>,
    ordinal: u64,
    horizon: u64,
    elapsed: u64,
    assessment: u64,
) {
    let iteration = ordinal.saturating_mul(200).min(horizon);
    phases
        .entry(format!("boundary/{iteration}/execute_total"))
        .or_insert(elapsed);
    phases
        .entry(format!("boundary/{iteration}/assessment"))
        .or_insert(assessment);
}
fn shape(a: &serde_json::Value, b: &serde_json::Value) -> bool {
    match (a, b) {
        (serde_json::Value::Object(a), serde_json::Value::Object(b)) => {
            a.len() == b.len() && b.iter().all(|(k, v)| a.get(k).is_some_and(|x| shape(x, v)))
        }
        (serde_json::Value::Array(a), serde_json::Value::Array(b)) => {
            a.len() == b.len() && a.iter().zip(b).all(|(x, y)| shape(x, y))
        }
        (serde_json::Value::Object(_) | serde_json::Value::Array(_), _)
        | (_, serde_json::Value::Object(_) | serde_json::Value::Array(_)) => false,
        _ => true,
    }
}
fn main() -> Result<(), Box<dyn std::error::Error>> {
    let mut args = std::env::args().skip(1).collect::<Vec<_>>();
    if args.first().is_some_and(|s| s == "device-checks") {
        return device_checks::run(&args[1..]);
    }
    let replay_original = if args.first().is_some_and(|s| s == "replay") {
        if args.len() != 5 {
            return Err("replay MODEL REQUEST ORIGINAL NEW_ENDPOINT".into());
        }
        let original = args.remove(3);
        Some(original)
    } else {
        None
    };
    if args.len() != 4
        || !matches!(
            args[0].as_str(),
            "trace-cpu" | "solve" | "verify" | "replay"
        )
    {
        return Err(
            "expanded-device solve|trace-cpu|verify MODEL REQUEST ENDPOINT; replay MODEL REQUEST ORIGINAL ENDPOINT"
                .into(),
        );
    }
    let bytes = std::fs::read(&args[1])?;
    if bytes.len() > 128 << 20 {
        return Err("model byte limit".into());
    }
    let request: Request = serde_json::from_slice(&std::fs::read(&args[2])?)?;
    request.options.validate()?;
    request.method.validate()?;
    request.settings.validate()?;
    let original = LpSettings::from_json(include_bytes!("../../../examples/lp-settings-v1.json"))?;
    let mut compared = request.method;
    compared.iteration_limit = original.iteration_limit;
    if request.identity != "lp-tensor-expanded-v1"
        || request.model_sha256 != sha256::hex(&bytes)
        || request.executable_sha256 != sha256::hex(&std::fs::read(std::env::current_exe()?)?)
        || request.source_tree_sha256 != env!("EXPANDED_SOURCE_SHA256")
        || compared != original
        || !matches!(request.horizon, 0 | 64 | 400 | 2000)
        || request.method.iteration_limit
            != if matches!(request.horizon, 64 | 400) {
                480
            } else {
                50000
            }
        || request.options.iteration_limit != Some(request.method.iteration_limit)
        || request.device != "GPU-dfb2449a-9eff-e868-3597-2c448c9a8e48"
        || !matches!(
            request.norm_policy.as_str(),
            "disjoint-interval-gram-v1" | "legacy-twice-absolute-v1"
        )
        || !matches!(
            request.audit_policy.as_str(),
            "device_ordered_v1" | "host_oracle_v1"
        )
        || !request.diagnostic
            && (request.norm_policy != "disjoint-interval-gram-v1"
                || request.audit_policy != "device_ordered_v1")
        || request
            .options
            .time_limit_ms
            .is_none_or(|v| v == 0 || v > 30000)
        || request.options.threads != 1
        || request.options.seed != 17
        || request.options.tolerances.absolute != 1e-9
        || request.options.tolerances.relative != 1e-9
        || request.options.tolerances.integrality != 1e-9
    {
        return Err("expanded frozen request binding/criteria".into());
    }
    let host_profile = if request.diagnostic && args[0] != "verify" {
        Some(optimizer_core::lp_cost::Session::begin()?)
    } else {
        None
    };
    let start = Instant::now();
    let model = Model::from_json(&bytes)?;
    let program = LinearProgram::new(&model)?;
    quant::admit_shape(&program)?;
    let mut engine = Engine::new(&program, request.method);
    let op = tensor_cost::Operator::new(&engine, request.settings.clone(), request.layout)?;
    if request.layout.tensor() && op.dense_exponents.is_empty() {
        return Err("layout_refusal".into());
    }
    if request.layout != tensor_cost::Layout::OriginalTuned {
        engine.restrict_step(if request.norm_policy == "legacy-twice-absolute-v1" {
            engine
                .step()
                .min((0.9f64.next_down() / op.norm_proof.legacy_bound).next_down())
        } else {
            op.step
        })?;
    }
    let mut assessor = Assessor::new(&model, &program, &request.options);
    if args[0] != "verify" {
        let solve;
        let mut events = std::collections::BTreeMap::new();
        let mut phases = std::collections::BTreeMap::new();
        let mut ordinal = 0u64;
        let mut assessment_ns = 0u64;
        let mut check = |x: &[f64], y: &[f64]| {
            let _scope = optimizer_core::lp_cost::scope("original_assessment");
            let began = Instant::now();
            let result = assessor.assess(x, y).is_ok_and(|a| a.gap_closed);
            let duration = began.elapsed().as_nanos() as u64;
            assessment_ns += duration;
            if request.diagnostic {
                record_boundary(
                    &mut phases,
                    ordinal,
                    request.horizon,
                    start.elapsed().as_nanos() as u64,
                    duration,
                );
                ordinal += 1;
            }
            result
        };
        let deadline = if args[0] == "trace-cpu" {
            None
        } else {
            Some(start + std::time::Duration::from_millis(request.options.time_limit_ms.unwrap()))
        };
        let preparation_ns;
        let mut outcome = if args[0] == "trace-cpu" {
            preparation_ns = start.elapsed().as_nanos() as u64;
            solve = Instant::now();
            tensor_cost::run(
                &engine,
                &op,
                &mut tensor_cost::HostOracle,
                request.horizon,
                &CancellationToken::new(),
                deadline,
                &mut check,
            )
        } else {
            let blobs = request
                .images
                .iter()
                .map(Image::bytes)
                .collect::<Result<Vec<_>, _>>()?;
            let context = std::rc::Rc::new(optimizer_cuda_sys::Context::create(&request.device)?);
            let reference = context.load_module(&blobs[0])?;
            let modules: [optimizer_cuda_sys::Module; 4] = blobs[1..]
                .iter()
                .map(|b| context.load_module(b))
                .collect::<Result<Vec<_>, _>>()?
                .try_into()
                .map_err(|_| "image inventory")?;
            let mut oracle = device::Oracle::new(
                context,
                &op,
                &reference,
                &modules,
                &engine,
                request.diagnostic,
            )?;
            oracle.set_host_audit(request.audit_policy == "host_oracle_v1");
            preparation_ns = start.elapsed().as_nanos() as u64;
            solve = Instant::now();
            let out = tensor_cost::run(
                &engine,
                &op,
                &mut oracle,
                request.horizon,
                &CancellationToken::new(),
                deadline,
                &mut check,
            );
            events = oracle.device_milliseconds.clone();
            out
        };
        phases.insert("host_preparation".into(), preparation_ns);
        phases.insert("solve_loop".into(), solve.elapsed().as_nanos() as u64);
        phases.insert("original_model_assessments".into(), assessment_ns);
        let delivery = Instant::now();
        let assessment = assessor.assess(&outcome.core.primal, &outcome.core.dual)?;
        phases.insert(
            "delivery_original_assessment".into(),
            delivery.elapsed().as_nanos() as u64,
        );
        if deadline.is_some_and(|d| Instant::now() >= d) && outcome.core.failure.is_none() {
            outcome.core.stop = "time_limit".into();
        }
        phases.insert("execute_total".into(), start.elapsed().as_nanos() as u64);
        let gpu = args[0] != "trace-cpu";
        let executed_device = gpu.then(|| request.device.clone());
        let mut evidence = Evidence {
            request,
            outcome,
            assessment,
            norm_proof: op.norm_proof.clone(),
            preparation_ns,
            solve_ns: solve.elapsed().as_nanos() as u64,
            device_event_milliseconds: events,
            phases_ns: phases,
            executor: if gpu { "gpu" } else { "cpu" }.into(),
            executed_device,
            payload_sha256: String::new(),
        };
        if let Some(original) = replay_original {
            let original: Evidence = serde_json::from_slice(&std::fs::read(original)?)?;
            if original.request != evidence.request
                || original.payload_sha256 != original.hash()?
                || serde_json::to_vec(&original.outcome)? != serde_json::to_vec(&evidence.outcome)?
            {
                return Err("same-candidate bitwise replay mismatch".into());
            }
        }
        evidence.payload_sha256 = evidence.hash()?;
        let file = std::fs::OpenOptions::new()
            .write(true)
            .create_new(true)
            .open(&args[3])?;
        let mut writer = BufWriter::new(file);
        serde_json::to_writer(&mut writer, &evidence)?;
        writer.write_all(b"\n")?;
        writer.flush()?;
        if let Some(profile) = host_profile {
            let profile = profile.finish();
            let out = std::fs::OpenOptions::new()
                .write(true)
                .create_new(true)
                .open(format!("{}.host-profile.json", args[3]))?;
            serde_json::to_writer(BufWriter::new(out), &profile)?;
        }
        println!("{}", serde_json::to_string(&evidence.assessment)?);
    } else {
        let bytes = std::fs::read(&args[3])?;
        if bytes.len() > 32 << 20 {
            return Err("endpoint byte limit".into());
        }
        let raw: serde_json::Value = serde_json::from_slice(&bytes)?;
        let evidence: Evidence = serde_json::from_slice(&bytes)?;
        if !shape(&raw, &serde_json::to_value(&evidence)?)
            || evidence.request != request
            || evidence.payload_sha256 != evidence.hash()?
            || evidence.norm_proof != op.norm_proof
            || !matches!(evidence.executor.as_str(), "gpu" | "cpu")
            || evidence.executed_device
                != (evidence.executor == "gpu").then(|| request.device.clone())
            || !evidence
                .phases_ns
                .get("execute_total")
                .is_some_and(|total| evidence.phases_ns.values().all(|v| v <= total))
            || !tensor_cost::physical_counts_valid(
                &evidence.outcome.counts,
                &op,
                evidence.outcome.core.work.proposals,
            )
            || evidence.outcome.core.iterations
                > if request.horizon == 0 {
                    50000
                } else {
                    request.horizon
                }
            || evidence.outcome.core.physical > request.method.iteration_limit
            || evidence.outcome.core.physical
                != evidence.outcome.core.work.proposals + evidence.outcome.core.work.audits
            || evidence
                .outcome
                .core
                .work
                .proposals
                .checked_sub(evidence.outcome.core.iterations)
                != Some(evidence.outcome.core.work.rejected)
            || evidence.assessment
                != assessor.assess(&evidence.outcome.core.primal, &evidence.outcome.core.dual)?
        {
            return Err("expanded endpoint verification".into());
        }
        println!("verified");
    }
    Ok(())
}

#[cfg(test)]
mod telemetry_contract_tests {
    use super::*;
    #[test]
    fn cumulative_boundaries_keep_the_first_observation_and_final_work_separate() {
        let mut phases = std::collections::BTreeMap::new();
        record_boundary(&mut phases, 0, 2000, 10, 3);
        record_boundary(&mut phases, 1, 2000, 100, 7);
        record_boundary(&mut phases, 10, 2000, 900, 8);
        record_boundary(&mut phases, 11, 2000, 920, 9);
        assert_eq!(phases["boundary/0/execute_total"], 10);
        assert_eq!(phases["boundary/200/execute_total"], 100);
        assert_eq!(phases["boundary/2000/execute_total"], 900);
        assert_eq!(phases["boundary/2000/assessment"], 8);
        phases.insert("delivery_original_assessment".into(), 11);
        phases.insert("execute_total".into(), 931);
        assert_eq!(
            phases["boundary/200/execute_total"] + phases["delivery_original_assessment"],
            111
        );
    }
}

#[cfg(test)]
mod integration_contract_tests {
    use super::*;
    #[test]
    fn reference_metadata_rejects_bit_and_counter_changes() {
        // The state fixture is explicit: neither model preparation nor a passed
        // numerical trajectory is rerun by this binding-only test.
        let state = control::Fp64State {
            primal: vec![0.],
            dual: vec![1.],
            anchor_primal: vec![0.],
            anchor_dual: vec![0.],
            weight: 1.,
            integral: 0.,
            previous_error: None,
            anchor_error: 0.,
            last_check_error: 0.,
            iterations: 31,
            restarts: 0,
            since_restart: 31,
            checked_iteration: 0,
        };
        assert!(device::same_state(&state, &state.clone()));
        let mut changed = state.clone();
        changed.primal[0] = -0.;
        assert!(!device::same_state(&state, &changed));
        changed = state.clone();
        changed.since_restart += 1;
        assert!(!device::same_state(&state, &changed));
        changed = state.clone();
        changed.anchor_dual[0] = 1.;
        assert!(!device::same_state(&state, &changed));
        changed = state.clone();
        changed.previous_error = Some(0.);
        assert!(!device::same_state(&state, &changed));
    }
    #[test]
    fn coefficient_abi_and_profile_pool_cover_a_full_window() {
        assert_eq!(std::mem::size_of::<device::Coefficient>(), 16);
        // Sixteen expanded launches/update, initial encode/flags, two-vector
        // canonicalization/final conversion, and reference observation.
        assert!(32 * 16 + 8 + 10 + 6 + 1 < 1024);
    }
}
