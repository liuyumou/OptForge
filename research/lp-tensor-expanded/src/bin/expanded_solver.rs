//! CPU admission entry for the new expanded solver, isolated from public defaults.
#![allow(dead_code)]
pub use lp_tensor_expanded_research::value;
pub use optimizer_lp::{Engine, control, exec, precision, quant, reduce, research};
#[path = "../outward.rs"]
mod outward;
#[path = "../solver.rs"]
mod tensor_cost;
#[path = "../prepared.rs"]
mod tensor_cost_prepare;
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
        ))?;
        Ok(sha256::hex(&bytes))
    }
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
    let args = std::env::args().skip(1).collect::<Vec<_>>();
    if args.len() != 4 || !matches!(args[0].as_str(), "trace-cpu" | "verify") {
        return Err(
            "expanded_solver trace-cpu|verify MODEL REQUEST EVIDENCE; GPU admission is pending"
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
    let original =
        LpSettings::from_json(include_bytes!("../../../../examples/lp-settings-v1.json"))?;
    let mut compared = request.method;
    compared.iteration_limit = original.iteration_limit;
    if request.identity != "lp-tensor-expanded-v1"
        || request.model_sha256 != sha256::hex(&bytes)
        || request.executable_sha256 != sha256::hex(&std::fs::read(std::env::current_exe()?)?)
        || request.source_tree_sha256.len() != 64
        || compared != original
        || request.horizon != 400
        || request.method.iteration_limit != 480
        || request.options.iteration_limit != Some(480)
        || request.options.threads != 1
        || request.options.seed != 17
        || request.options.tolerances.absolute != 1e-9
        || request.options.tolerances.relative != 1e-9
        || request.options.tolerances.integrality != 1e-9
    {
        return Err("CPU admission request binding/criteria".into());
    }
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
        engine.restrict_step(op.step)?;
    }
    let mut assessor = Assessor::new(&model, &program, &request.options);
    if args[0] == "trace-cpu" {
        let preparation_ns = start.elapsed().as_nanos() as u64;
        let solve = Instant::now();
        let outcome = tensor_cost::run(
            &engine,
            &op,
            &mut tensor_cost::HostOracle,
            request.horizon,
            &CancellationToken::new(),
            None,
            |x, y| assessor.assess(x, y).is_ok_and(|a| a.gap_closed),
        );
        let assessment = assessor.assess(&outcome.core.primal, &outcome.core.dual)?;
        let mut evidence = Evidence {
            request,
            outcome,
            assessment,
            norm_proof: op.norm_proof.clone(),
            preparation_ns,
            solve_ns: solve.elapsed().as_nanos() as u64,
            payload_sha256: String::new(),
        };
        evidence.payload_sha256 = evidence.hash()?;
        let file = std::fs::OpenOptions::new()
            .write(true)
            .create_new(true)
            .open(&args[3])?;
        let mut writer = BufWriter::new(file);
        serde_json::to_writer(&mut writer, &evidence)?;
        writer.write_all(b"\n")?;
        writer.flush()?;
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
            || !tensor_cost::physical_counts_valid(
                &evidence.outcome.counts,
                &op,
                evidence.outcome.core.work.proposals,
            )
            || evidence.outcome.core.iterations > 400
            || evidence.outcome.core.physical > 480
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
            return Err("expanded CPU endpoint verification".into());
        }
        println!("verified");
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use tensor_cost::Oracle;
    fn model() -> Model {
        let variables=(0..32).map(|id|serde_json::json!({"id":id,"domain":"continuous","lower":{"kind":"finite","value":0.},"upper":{"kind":"finite","value":1.}})).collect::<Vec<_>>();
        let constraints=(0..32).map(|id|serde_json::json!({"id":id,"lower":{"kind":"negative_infinity"},"upper":{"kind":"finite","value":16.},"terms":(0..32).map(|j|serde_json::json!({"variable_id":j,"coefficient":if j==id {2.}else{0.125}})).collect::<Vec<_>>()})).collect::<Vec<_>>();
        Model::from_json(&serde_json::to_vec(&serde_json::json!({"schema_version":1,"model_id":"expanded-window-new","variables":variables,"constraints":constraints,"objective":{"sense":"minimize","offset":0.,"terms":(0..32).map(|id|serde_json::json!({"variable_id":id,"coefficient":-1.})).collect::<Vec<_>>()}})).unwrap()).unwrap()
    }
    fn settings() -> quant::Settings {
        serde_json::from_value(serde_json::json!({"audit_absolute":1e-7,"audit_interval":32,"audit_relative":1e-7,"dual_budget":1e-7,"format":"fp64","policy":"uniform","primal_budget":1e-7,"rounding":"nearest_even","tile_size":32})).unwrap()
    }
    #[test]
    fn canonical_penultimate_and_all_window_lengths() {
        let model = model();
        let program = LinearProgram::new(&model).unwrap();
        let method =
            LpSettings::from_json(include_bytes!("../../../../examples/lp-settings-v1.json"))
                .unwrap();
        let mut engine = Engine::new(&program, method);
        let op =
            tensor_cost::Operator::new(&engine, settings(), tensor_cost::Layout::Int8).unwrap();
        engine.restrict_step(op.step).unwrap();
        let generation = op.generation(op.initial()).unwrap();
        let state = control::Fp64Controller::new(&engine).state().clone();
        for length in [1, 2, 8, 31, 32] {
            let mut oracle = tensor_cost::HostOracle;
            let result = oracle
                .window(&engine, &op, &generation, &state, length)
                .unwrap();
            assert!(result.failure.is_none(), "{:?}", result.failure);
            let pre = result.pre.as_ref().unwrap();
            assert_eq!(pre.iterations, length - 1);
            let final_only = oracle.window(&engine, &op, &generation, pre, 1).unwrap();
            assert!(final_only.failure.is_none());
            assert_eq!(
                result
                    .primal
                    .iter()
                    .map(|v| v.to_bits())
                    .collect::<Vec<_>>(),
                final_only
                    .primal
                    .iter()
                    .map(|v| v.to_bits())
                    .collect::<Vec<_>>()
            );
            assert_eq!(
                result.dual.iter().map(|v| v.to_bits()).collect::<Vec<_>>(),
                final_only
                    .dual
                    .iter()
                    .map(|v| v.to_bits())
                    .collect::<Vec<_>>()
            );
            assert_eq!(result.counts.encoded_coordinates, 192);
            assert_eq!(result.counts.decoded_coordinates, 128);
            assert_eq!(
                oracle.reference(&engine, pre).unwrap(),
                precision::correction(&engine, pre).unwrap()
            );
        }
    }
    #[test]
    fn new_serial_preparation_preserves_groups_and_gram_bits() {
        let model = model();
        let program = LinearProgram::new(&model).unwrap();
        let method =
            LpSettings::from_json(include_bytes!("../../../../examples/lp-settings-v1.json"))
                .unwrap();
        let engine = Engine::new(&program, method);
        let old = optimizer_lp::tensor_cost::Operator::new(
            &engine,
            settings(),
            optimizer_lp::tensor_cost::Layout::Int8,
        )
        .unwrap();
        let new =
            tensor_cost::Operator::new(&engine, settings(), tensor_cost::Layout::Int8).unwrap();
        assert_eq!(old.norm.to_bits(), new.norm.to_bits());
        assert_eq!(old.step.to_bits(), new.step.to_bits());
        for (old, new) in old
            .row_groups
            .iter()
            .chain(&old.column_groups)
            .zip(new.row_groups.iter().chain(&new.column_groups))
        {
            assert_eq!(old.len(), new.len());
            for (a, b) in old.iter().zip(new) {
                assert_eq!(a.tile, b.tile);
                assert_eq!(a.ids, b.ids);
                assert_eq!(a.mass.to_bits(), b.mass.to_bits());
                assert_eq!(a.error.to_bits(), b.error.to_bits());
            }
        }
    }
    #[test]
    fn new_counter_formulas_reject_malformed_or_overflowing_counts() {
        let model = model();
        let program = LinearProgram::new(&model).unwrap();
        let engine = Engine::new(
            &program,
            LpSettings::from_json(include_bytes!("../../../../examples/lp-settings-v1.json"))
                .unwrap(),
        );
        for (layout, mma, pairs) in [
            (tensor_cost::Layout::Int8, 32, 80),
            (tensor_cost::Layout::Fp16, 64, 80),
            (tensor_cost::Layout::Bf16, 112, 224),
        ] {
            let op = tensor_cost::Operator::new(&engine, settings(), layout).unwrap();
            let mut c = tensor_cost::Counts {
                mma_instructions: mma,
                component_products: 1024 * pairs,
                padded_products: mma
                    * if layout == tensor_cost::Layout::Int8 {
                        4096
                    } else {
                        2048
                    },
                ..Default::default()
            };
            assert!(tensor_cost::physical_counts_valid(&c, &op, 1));
            c.component_products += 1;
            assert!(!tensor_cost::physical_counts_valid(&c, &op, 1));
            c.mma_instructions = u64::MAX;
            assert!(!tensor_cost::physical_counts_valid(&c, &op, 1));
        }
    }
}
