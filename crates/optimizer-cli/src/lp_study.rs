//! Bounded study preparation and independent endpoint verification (SPEC-0013).
use crate::input::{argument, read};
use std::ffi::OsString;
use std::io;

pub(crate) fn run(command: &std::ffi::OsStr, args: &[OsString]) -> io::Result<u8> {
    let mut model = None;
    let mut evidence = None;
    let mut instance = None;
    let mut output = None;
    for pair in args.chunks(2) {
        let [key, value] = pair else {
            return Err(argument("each flag requires a value"));
        };
        let slot = match key.to_str() {
            Some("--model") => &mut model,
            Some("--evidence") => &mut evidence,
            Some("--instance") => &mut instance,
            Some("--output") => &mut output,
            _ => return Err(argument("unknown LP study flag")),
        };
        if slot.replace(value.as_os_str()).is_some() {
            return Err(argument("duplicate flag"));
        }
    }
    if command == "verify" && instance.is_none() && output.is_none() {
        let bytes = read(model.ok_or_else(|| argument("--model is required"))?)?;
        let endpoint = optimizer_experiment::lp::LpEndpoint::from_json(&read(
            evidence.ok_or_else(|| argument("--evidence is required"))?,
        )?)
        .map_err(io::Error::other)?;
        endpoint.verify(&bytes).map_err(io::Error::other)?;
        println!("{}", serde_json::to_string(&endpoint.assessment)?);
    } else if command == "prepare" && model.is_none() && evidence.is_none() {
        let instance = optimizer_schedule::FlowShopInstance::from_json(&read(
            instance.ok_or_else(|| argument("--instance is required"))?,
        )?)
        .map_err(io::Error::other)?;
        let original = optimizer_schedule::model(&instance).map_err(io::Error::other)?;
        let variables = original
            .document()
            .variables
            .iter()
            .cloned()
            .map(|mut v| {
                v.domain = optimizer_core::Domain::Continuous;
                v
            })
            .collect();
        let relaxed = original.rebound(variables).map_err(io::Error::other)?;
        let json = relaxed.to_json().map_err(io::Error::other)?;
        if json.len() as u64 > crate::input::MAX_INPUT_BYTES {
            return Err(argument("prepared model exceeds input byte limit"));
        }
        std::fs::write(
            output.ok_or_else(|| argument("--output is required"))?,
            json,
        )?;
    } else {
        return Err(argument(
            "expected lp-study prepare or verify with matching flags",
        ));
    }
    Ok(0)
}
