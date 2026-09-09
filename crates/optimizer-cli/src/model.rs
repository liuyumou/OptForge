use std::ffi::{OsStr, OsString};
use std::io::{self, Write};

use optimizer_core::{Candidate, Model, Tolerances};

use crate::input::{argument, read};

pub(crate) fn validate(options: &[OsString]) -> io::Result<u8> {
    let mut model_path = None;
    let mut candidate_path = None;
    let mut absolute = None;
    let mut relative = None;
    let mut integrality = None;
    for pair in options.chunks(2) {
        let [key, value] = pair else {
            return Err(argument("each flag requires a value"));
        };
        let key = key
            .to_str()
            .ok_or_else(|| argument("flag names must be UTF-8 text"))?;
        let slot = match key {
            "--model" => &mut model_path,
            "--candidate" => &mut candidate_path,
            "--absolute-tolerance" => &mut absolute,
            "--relative-tolerance" => &mut relative,
            "--integrality-tolerance" => &mut integrality,
            _ => return Err(argument(&format!("unknown flag {key}"))),
        };
        if slot.replace(value.as_os_str()).is_some() {
            return Err(argument(&format!("duplicate flag {key}")));
        }
    }
    let model_path = model_path.ok_or_else(|| argument("--model is required"))?;
    let tolerances = if candidate_path.is_some() {
        Some(
            Tolerances {
                absolute: number(absolute, "absolute")?,
                relative: number(relative, "relative")?,
                integrality: number(integrality, "integrality")?,
            }
            .validate()
            .map_err(io::Error::other)?,
        )
    } else {
        if absolute.is_some() || relative.is_some() || integrality.is_some() {
            return Err(argument("tolerances require --candidate"));
        }
        None
    };
    let model = Model::from_json(&read(model_path)?).map_err(io::Error::other)?;
    let (output, code) = if let (Some(path), Some(tolerances)) = (candidate_path, tolerances) {
        let candidate = Candidate::from_json(&read(path)?).map_err(io::Error::other)?;
        let report = model
            .evaluate(&candidate, tolerances)
            .map_err(io::Error::other)?;
        let code = u8::from(!report.feasible);
        (serde_json::to_string_pretty(&report)?, code)
    } else {
        (
            serde_json::to_string_pretty(&serde_json::json!({
                "schema_version": 1,
                "model_id": model.document().model_id,
                "status": "structurally_valid"
            }))?,
            0,
        )
    };
    let mut stdout = io::stdout().lock();
    writeln!(stdout, "{output}")
        .and_then(|()| stdout.flush())
        .map_err(|error| io::Error::other(format!("io: stdout: {error}")))?;
    Ok(code)
}

fn number(value: Option<&OsStr>, name: &str) -> io::Result<f64> {
    value
        .ok_or_else(|| argument(&format!("--{name}-tolerance is required")))?
        .to_str()
        .ok_or_else(|| argument(&format!("invalid --{name}-tolerance: expected UTF-8 text")))?
        .parse()
        .map_err(|_| argument(&format!("invalid --{name}-tolerance")))
}
