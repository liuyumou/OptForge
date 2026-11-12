use crate::Result;
use std::sync::OnceLock;
#[derive(Clone, Copy, Debug)]
pub struct Config {
    pub name: &'static str,
    pub batch: bool,
    pub overlap: bool,
    pub profile: bool,
    pub device_profile: bool,
}
static CONFIG: OnceLock<Config> = OnceLock::new();
pub fn parse(value: &str) -> Result<Config> {
    let device_profile = match value {
        "control" => false,
        "profile" => true,
        _ => return Err("unknown MIXED2 pilot configuration".into()),
    };
    Ok(Config {
        name: "candidate",
        batch: true,
        overlap: true,
        profile: false,
        device_profile,
    })
}
pub fn init() -> Result<()> {
    for key in [
        "GPUP_DELIVERY2_CONTROL",
        "GPUP_CHECKER_ORIGINAL",
        "GPUP_DELIVERY3_VARIANT",
        "GPUP_DELIVERY3_PROFILE",
        "GPUP_DELIVERY4_VARIANT",
        "GPUP_DELIVERY4_PROFILE",
    ] {
        if std::env::var_os(key).is_some() {
            return Err("conflicting historical override".into());
        }
    }
    let value = match std::env::var("GPUP_MIXED2_PILOT_VARIANT") {
        Ok(v) => v,
        Err(std::env::VarError::NotPresent) => "control".into(),
        Err(e) => return Err(e.into()),
    };
    CONFIG
        .set(parse(&value)?)
        .map_err(|_| "configuration initialized twice".into())
}
pub fn get() -> Config {
    *CONFIG.get().unwrap_or(&Config {
        name: "candidate",
        batch: true,
        overlap: true,
        profile: false,
        device_profile: false,
    })
}
#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn fixed_delivery_and_strict_profile() {
        for v in ["control", "profile"] {
            let c = parse(v).unwrap();
            assert!(c.batch && c.overlap && !c.profile);
            assert_eq!(c.device_profile, v == "profile");
        }
        assert!(parse("auto").is_err());
    }
}
