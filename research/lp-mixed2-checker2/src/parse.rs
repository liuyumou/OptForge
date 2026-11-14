//! Parse independent constraint objects concurrently, then use original validation.
//! Any error re-enters the original parser to preserve its exact first error.
use optimizer_core::{Model, ModelDocument, ValidationError};
use serde::Deserialize;
use serde_json::value::RawValue;
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Envelope<'a> {
    schema_version: u32,
    model_id: String,
    #[serde(borrow)]
    variables: &'a RawValue,
    #[serde(borrow)]
    constraints: Vec<&'a RawValue>,
    #[serde(borrow)]
    objective: &'a RawValue,
}
pub fn model(bytes: &[u8]) -> Result<Model, ValidationError> {
    if bytes.len() < 1 << 20 {
        return Model::from_json(bytes);
    }
    match parallel(bytes) {
        Ok(model) => Ok(model),
        Err(_) => Model::from_json(bytes),
    }
}
fn parallel(bytes: &[u8]) -> Result<Model, Box<dyn std::error::Error>> {
    let _cost = optimizer_core::lp_cost::scope("parallel_json_parse_and_validation");
    let envelope: Envelope<'_> = serde_json::from_slice(bytes)?;
    let constraints = std::thread::scope(|scope| {
        let workers: Vec<_> = envelope
            .constraints
            .chunks(envelope.constraints.len().div_ceil(4).max(1))
            .map(|chunk| {
                scope.spawn(move || {
                    chunk
                        .iter()
                        .map(|r| serde_json::from_str(r.get()))
                        .collect::<Result<Vec<_>, _>>()
                })
            })
            .collect();
        let mut constraints = Vec::with_capacity(envelope.constraints.len());
        for worker in workers {
            constraints.extend(worker.join().expect("JSON worker panicked")?);
        }
        Ok::<_, serde_json::Error>(constraints)
    })?;
    Ok(Model::new(ModelDocument {
        schema_version: envelope.schema_version,
        model_id: envelope.model_id,
        variables: serde_json::from_str(envelope.variables.get())?,
        constraints,
        objective: serde_json::from_str(envelope.objective.get())?,
    })?)
}
#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn parallel_matches_original_document_and_first_error() {
        let base = serde_json::json!({"schema_version":1,"model_id":"parse-test","variables":[
            {"id":8,"domain":"continuous","lower":{"kind":"negative_infinity"},"upper":{"kind":"positive_infinity"}},
            {"id":2,"domain":"continuous","lower":{"kind":"finite","value":-0.0},"upper":{"kind":"finite","value":1.0}}],
            "constraints":[{"id":9,"lower":{"kind":"finite","value":0.0},"upper":{"kind":"positive_infinity"},
            "terms":[{"variable_id":8,"coefficient":0.12345678901234567},{"variable_id":2,"coefficient":-0.0}]}],
            "objective":{"sense":"maximize","offset":-0.0,"terms":[]}});
        let bytes = serde_json::to_vec(&base).unwrap();
        assert_eq!(
            parallel(&bytes).unwrap().to_json().unwrap(),
            Model::from_json(&bytes).unwrap().to_json().unwrap()
        );
        for bad in [
            "{",
            "null",
            "{}",
            "{\"schema_version\":1,\"schema_version\":2}",
        ] {
            let mut padded = bad.as_bytes().to_vec();
            padded.resize((1 << 20) + 4, b' ');
            assert_eq!(
                model(&padded).unwrap_err().to_string(),
                Model::from_json(&padded).unwrap_err().to_string()
            );
        }
        let mut large = bytes.clone();
        large.resize((1 << 20) + 4, b' ');
        assert_eq!(
            model(&large).unwrap().to_json().unwrap(),
            Model::from_json(&large).unwrap().to_json().unwrap()
        );
        for variant in 0..6 {
            let mut value = base.clone();
            match variant {
                0 => value["constraints"][0]["terms"][0]["variable_id"] = serde_json::json!(999),
                1 => value["constraints"][0]["terms"][1]["variable_id"] = serde_json::json!(8),
                2 => value["schema_version"] = serde_json::json!(99),
                3 => value["unknown"] = serde_json::json!(true),
                4 => {
                    value["variables"][0]["lower"] = serde_json::json!({"kind":"positive_infinity"})
                }
                _ => value["constraints"][0]["terms"][0]["coefficient"] = serde_json::json!("bad"),
            }
            let mut bytes = serde_json::to_vec(&value).unwrap();
            bytes.resize((1 << 20) + 4, b' ');
            assert_eq!(
                model(&bytes).unwrap_err().to_string(),
                Model::from_json(&bytes).unwrap_err().to_string()
            );
        }
    }
}
