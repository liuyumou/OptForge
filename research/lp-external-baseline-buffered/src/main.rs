//! Isolated solver-neutral original-model checker and retained HiGHS producer.
use optimizer_core::{
    Assignment, CancellationToken, Candidate, LpDiagnostics, Model, SolveOptions, Tolerances,
};
use optimizer_experiment::sha256::hex;
mod strict;
use optimizer_lp::{LinearProgram, certify, certify::assess_gap};
use serde::Deserialize;
use serde_json::{Value, json};
use std::{error::Error, fs, io::Write, path::Path};
use strict::unique_json;

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Witness {
    schema_version: u32,
    kind: String,
    model_sha256: String,
    row_ids: Vec<u32>,
    variable_ids: Vec<u32>,
    primal: Option<Vec<f64>>,
    dual: Option<Vec<f64>>,
    transport: String,
    native_status: String,
}

fn read(path: &Path) -> Result<Vec<u8>, Box<dyn Error>> {
    if fs::metadata(path)?.len() > 128 << 20 {
        return Err("input exceeds limit".into());
    }
    let bytes = fs::read(path)?;
    unique_json(&bytes)?;
    Ok(bytes)
}

fn assess(model_bytes: &[u8], witness_bytes: &[u8]) -> Result<Value, Box<dyn Error>> {
    unique_json(witness_bytes)?;
    let w: Witness = serde_json::from_slice(witness_bytes)?;
    // Option fields must be present, even when no vector was returned.
    let raw: Value = serde_json::from_slice(witness_bytes)?;
    if raw.get("primal").is_none() || raw.get("dual").is_none() {
        return Err("missing vector field".into());
    }
    let model = Model::from_json(model_bytes)?;
    let p = LinearProgram::new(&model)?;
    let rows: Vec<_> = model.document().constraints.iter().map(|r| r.id).collect();
    if w.schema_version != 1
        || w.kind != "lp-baseline-candidate"
        || w.model_sha256 != hex(model_bytes)
        || w.row_ids != rows
        || w.variable_ids != p.variable_ids()
        || !["completed", "timeout", "cancelled", "error", "unavailable"]
            .contains(&w.transport.as_str())
        || ![
            "optimal",
            "limit",
            "infeasible",
            "unbounded",
            "infeasible_or_unbounded",
            "numerical_failure",
            "unknown",
            "not_run",
        ]
        .contains(&w.native_status.as_str())
    {
        return Err("candidate identity/status differs".into());
    }
    for (values, size) in [(&w.primal, p.column_count()), (&w.dual, p.row_count())] {
        if values
            .as_ref()
            .is_some_and(|v| v.len() != size || v.iter().any(|x| !x.is_finite()))
        {
            return Err("candidate vector shape/range differs".into());
        }
    }
    let tol = Tolerances {
        absolute: 1e-9,
        relative: 1e-9,
        integrality: 1e-9,
    };
    let validation = w
        .primal
        .as_ref()
        .map(|x| {
            model.evaluate(
                &Candidate {
                    schema_version: 1,
                    model_id: model.document().model_id.clone(),
                    values: w
                        .variable_ids
                        .iter()
                        .zip(x)
                        .map(|(&variable_id, &value)| Assignment { variable_id, value })
                        .collect(),
                },
                tol,
            )
        })
        .transpose()?;
    let bound = w.dual.as_ref().map(|y| certify(&p, y));
    let certificate = bound.as_ref().and_then(|b| b.as_ref().ok());
    let gap = certificate.and_then(|c| {
        w.primal
            .as_ref()
            .and_then(|x| assess_gap(&p, x, c.bound, tol))
    });
    let eligible = w.transport == "completed"
        && ["optimal", "limit", "unknown"].contains(&w.native_status.as_str());
    let accepted = eligible
        && validation.as_ref().is_some_and(|v| v.feasible)
        && gap.as_ref().is_some_and(|g| g.closed);
    Ok(
        json!({"schema_version":1,"kind":"lp-baseline-certificate", "model_sha256":hex(model_bytes),
        "candidate_sha256":hex(witness_bytes),"tolerances":tol,"accepted":accepted,"validation":validation,
        "bound":certificate.map(|c| c.bound),"repaired_row_duals":certificate.map(|c| c.repaired),
        "gap_upper":gap.as_ref().map(|g| g.upper),"gap_closed":gap.as_ref().map(|g| g.closed),
        "refusal":bound.as_ref().and_then(|r|r.as_ref().err()).map(ToString::to_string),
        "eligible_transport_and_status":eligible}),
    )
}

fn write(path: &Path, value: &Value) -> Result<(), Box<dyn Error>> {
    let file = fs::OpenOptions::new()
        .write(true)
        .create_new(true)
        .open(path)?;
    let mut output = std::io::BufWriter::with_capacity(1 << 20, file);
    serde_json::to_writer_pretty(&mut output, value)?;
    output.write_all(b"\n")?;
    output.flush()?;
    output.get_ref().sync_all()?;
    Ok(())
}

fn main() -> Result<(), Box<dyn Error>> {
    let args: Vec<_> = std::env::args().collect();
    if args.len() != 5 {
        return Err(
            "usage: lp-external-baseline check|highs MODEL CANDIDATE|OPTIONS OUTPUT".into(),
        );
    }
    let bytes = read(Path::new(&args[2]))?;
    let input = read(Path::new(&args[3]))?;
    let value = match args[1].as_str() {
        "check" => {
            let mut value = assess(&bytes, &input)?;
            value["checker_binary_sha256"] = json!(hex(&fs::read(std::env::current_exe()?)?));
            value
        }
        "highs" => {
            let model = Model::from_json(&bytes)?;
            let options: SolveOptions = serde_json::from_slice(&input)?;
            let mut d = LpDiagnostics::new(true, false);
            let record = optimizer_highs::HighsBackend::new().solve_with_diagnostics(
                &model,
                &options,
                &CancellationToken::new(),
                None,
                &mut d,
            )?;
            json!({"record":record,"diagnostics":d})
        }
        _ => return Err("unknown command".into()),
    };
    write(Path::new(&args[4]), &value)
}

#[cfg(test)]
mod output_tests {
    use super::*;

    #[test]
    fn buffered_bytes_and_exclusive_output() {
        let path =
            std::env::temp_dir().join(format!("lp-baseline-buffer-{}.json", std::process::id()));
        let value =
            json!({"large": "x".repeat(17 << 20), "numbers": [-0.0, 0.5, f64::MIN_POSITIVE / 2.0]});
        let mut expected = serde_json::to_vec_pretty(&value).unwrap();
        expected.push(b'\n');
        write(&path, &value).unwrap();
        assert_eq!(fs::read(&path).unwrap(), expected);
        assert!(write(&path, &json!(null)).is_err());
        assert_eq!(fs::read(&path).unwrap(), expected);
        fs::remove_file(path).unwrap();
    }
}
