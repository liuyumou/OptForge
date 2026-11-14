use crate::Result;
#[derive(Clone, Copy)]
pub struct Config {
    pub name: &'static str,
    pub batch: bool,
    pub overlap: bool,
    pub profile: bool,
}
pub fn init() -> Result<()> {
    if std::env::vars_os().any(|(k, _)| {
        let k = k.to_string_lossy();
        k.starts_with("GPUP_DELIVERY")
            || k.starts_with("GPUP_CHECKER_")
            || k.starts_with("GPUP_MIXED2_PILOT")
    }) {
        return Err("conflicting historical override".into());
    }
    Ok(())
}
pub fn get() -> Config {
    Config {
        name: "candidate",
        batch: true,
        overlap: true,
        profile: false,
    }
}
