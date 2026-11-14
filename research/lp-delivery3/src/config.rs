//! Immutable process-wide delivery policy; no lane, outcome or timing dispatch.
use crate::Result;
use std::sync::OnceLock;
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct Config {
    pub name: &'static str,
    pub batch: bool,
    pub overlap: bool,
    pub profile: bool,
}
static CONFIG: OnceLock<Config> = OnceLock::new();
impl Config {
    pub fn parse(name: &str, profile: &str) -> Result<Self> {
        let (name, batch, overlap) = match name {
            "control" => ("control", false, false),
            "batch" => ("batch", true, false),
            "overlap" => ("overlap", false, true),
            "combined" => ("combined", true, true),
            _ => return Err("unknown DELIVERY3 variant".into()),
        };
        let profile = match profile {
            "0" => false,
            "1" => true,
            _ => return Err("invalid DELIVERY3 profiling flag".into()),
        };
        Ok(Self {
            name,
            batch,
            overlap,
            profile,
        })
    }
}
pub fn init() -> Result<()> {
    fn env(name: &str, default: &str) -> Result<String> {
        match std::env::var(name) {
            Ok(value) => Ok(value),
            Err(std::env::VarError::NotPresent) => Ok(default.into()),
            Err(error) => Err(error.into()),
        }
    }
    for name in ["GPUP_DELIVERY2_CONTROL", "GPUP_CHECKER_ORIGINAL"] {
        if std::env::var_os(name).is_some() {
            return Err("conflicting retained delivery/checker override".into());
        }
    }
    let config = Config::parse(
        &env("GPUP_DELIVERY3_VARIANT", "control")?,
        &env("GPUP_DELIVERY3_PROFILE", "0")?,
    )?;
    CONFIG
        .set(config)
        .map_err(|_| "delivery configuration already initialized")?;
    Ok(())
}
pub fn get() -> Config {
    *CONFIG.get().unwrap_or(&Config {
        name: "control",
        batch: false,
        overlap: false,
        profile: false,
    })
}
#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn independent_factorial_switches_and_rejected_unknowns() {
        for (name, batch, overlap) in [
            ("control", false, false),
            ("batch", true, false),
            ("overlap", false, true),
            ("combined", true, true),
        ] {
            for p in ["0", "1"] {
                let c = Config::parse(name, p).unwrap();
                assert_eq!(
                    (c.name, c.batch, c.overlap, c.profile),
                    (name, batch, overlap, p == "1")
                );
            }
        }
        assert!(Config::parse("automatic", "0").is_err());
        assert!(Config::parse("control", "yes").is_err());
    }
}
