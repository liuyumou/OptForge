//! Exclusive host-wall intervals; nested preparation metrics remain separate.
use serde_json::{Value, json};
use std::time::Instant;

pub const NAMES: [&str; 20] = [
    "preparation_engine",
    "preparation_operator",
    "preparation_packing",
    "preparation_control",
    "device_setup",
    "host_bookkeeping",
    "checkpoint",
    "device_advance",
    "endpoint_download",
    "device_accounting",
    "original_model_control",
    "recovery",
    "endpoint_unscale",
    "strict_certificate",
    "witness_output",
    "restart_weight_control",
    "state_upload",
    "device_teardown",
    "response_assembly",
    "certificate_reuse",
];

#[derive(Clone, Copy)]
#[repr(usize)]
pub enum Phase {
    Engine,
    Operator,
    Packing,
    InitialControl,
    DeviceSetup,
    Bookkeeping,
    Checkpoint,
    Advance,
    Download,
    Accounting,
    Merit,
    Recovery,
    Unscale,
    Certificate,
    Witness,
    Restart,
    Upload,
    Teardown,
    Response,
    CertificateReuse,
}

pub struct Profile {
    enabled: bool,
    origin: Instant,
    last: u128,
    stage: usize,
    durations: [u128; NAMES.len()],
    entries: [u64; NAMES.len()],
}

impl Profile {
    pub fn new(origin: Instant, enabled: bool) -> Self {
        Self {
            enabled,
            origin,
            last: 0,
            stage: 0,
            durations: [0; NAMES.len()],
            entries: [0; NAMES.len()],
        }
    }
    fn charge(&mut self, now: u128) {
        self.durations[self.stage] += now - self.last;
        self.last = now;
    }
    pub fn enter(&mut self, phase: Phase) {
        let stage = phase as usize;
        if self.enabled {
            self.charge(self.origin.elapsed().as_nanos());
            self.stage = stage;
            self.entries[stage] += 1;
        }
    }
    pub fn finish(&mut self) -> Option<Value> {
        if !self.enabled {
            return None;
        }
        self.charge(self.origin.elapsed().as_nanos());
        let phases: serde_json::Map<_, _> = NAMES
            .iter()
            .zip(self.durations)
            .map(|(k, v)| (k.to_string(), json!(v)))
            .collect();
        let entries: serde_json::Map<_, _> = NAMES
            .iter()
            .zip(self.entries)
            .map(|(k, v)| (k.to_string(), json!(v)))
            .collect();
        Some(
            json!({"schema_version":1,"clock":"monotonic_host_wall","total_ns":self.last,
            "exclusive_ns":phases,"phase_entries":entries,
            "timer_overhead_included":true,"kernel_active_time":false}),
        )
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn exact_coverage_including_revisited_phases() {
        let mut p = Profile::new(Instant::now(), true);
        p.charge(7);
        p.stage = 7;
        p.charge(19);
        p.stage = 0;
        p.charge(23);
        assert_eq!(p.durations[0], 11);
        assert_eq!(p.durations[7], 12);
        assert_eq!(p.durations.iter().sum::<u128>(), p.last);
    }
    #[test]
    fn disabled_profile_emits_nothing() {
        let mut p = Profile::new(Instant::now(), false);
        p.enter(Phase::Teardown);
        assert_eq!(p.last, 0);
        assert!(p.finish().is_none());
    }
    #[test]
    fn emitted_phase_total_is_exact() {
        let mut p = Profile::new(Instant::now(), true);
        p.enter(Phase::DeviceSetup);
        p.enter(Phase::Advance);
        p.enter(Phase::Certificate);
        let v = p.finish().unwrap();
        let sum: u64 = v["exclusive_ns"]
            .as_object()
            .unwrap()
            .values()
            .map(|x| x.as_u64().unwrap())
            .sum();
        assert_eq!(sum, v["total_ns"].as_u64().unwrap());
        assert_eq!(v["exclusive_ns"].as_object().unwrap().len(), NAMES.len());
    }
}
