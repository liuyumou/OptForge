//! Independent original-model checking. No approximate operator or device residual input.
use crate::Result;
use optimizer_core::{Assignment, Candidate, Model, Tolerances};
use optimizer_experiment::sha256::hex;
use optimizer_lp::{LinearProgram, certify, certify::assess_gap};
use serde::{Deserialize, Serialize};
use serde_json::{Value, json};
#[derive(Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub struct Endpoint {
    pub model_sha256: String,
    pub primal: Vec<f64>,
    pub dual: Vec<f64>,
    pub transport: String,
}
pub fn assess(bytes: &[u8], endpoint: &Endpoint, tier: &str) -> Result<Value> {
    let tol = match tier {
        "certified-1e-7" => 1e-7,
        "certified-1e-9" => 1e-9,
        _ => return Err("unknown tier".into()),
    };
    let model = Model::from_json(bytes)?;
    let p = LinearProgram::new(&model)?;
    if endpoint.model_sha256 != hex(bytes)
        || endpoint.primal.len() != p.column_count()
        || endpoint.dual.len() != p.row_count()
        || endpoint
            .primal
            .iter()
            .chain(&endpoint.dual)
            .any(|v| !v.is_finite())
        || !["completed", "cancelled", "limit", "error"].contains(&endpoint.transport.as_str())
    {
        return Err("endpoint identity/shape/range".into());
    }
    let tolerances = Tolerances {
        absolute: tol,
        relative: tol,
        integrality: tol,
    };
    let validation = model.evaluate(
        &Candidate {
            schema_version: 1,
            model_id: model.document().model_id.clone(),
            values: p
                .variable_ids()
                .iter()
                .zip(&endpoint.primal)
                .map(|(&variable_id, &value)| Assignment { variable_id, value })
                .collect(),
        },
        tolerances,
    )?;
    let bound = certify(&p, &endpoint.dual);
    let certificate = bound.as_ref().ok();
    let gap = certificate.and_then(|c| assess_gap(&p, &endpoint.primal, c.bound, tolerances));
    let eligible = endpoint.transport == "completed";
    let accepted = eligible && validation.feasible && gap.as_ref().is_some_and(|g| g.closed);
    Ok(
        json!({"schema_version":1,"kind":"lp-fp4-integrate-certificate","model_sha256":hex(bytes),
        "endpoint_sha256":hex(&serde_json::to_vec(endpoint)?),"tier":tier,"tolerances":tolerances,
        "eligible":eligible,"accepted":accepted,"validation":validation,
        "bound":certificate.map(|c|c.bound),"gap_upper":gap.as_ref().map(|g|g.upper),
        "gap_closed":gap.as_ref().is_some_and(|g|g.closed),"refusal":bound.err().map(|e|e.to_string())}),
    )
}
