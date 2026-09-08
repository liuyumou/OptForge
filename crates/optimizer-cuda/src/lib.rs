//! GPU discovery and cooperative host-wide ownership without CUDA linkage.

use std::fs::{File, OpenOptions, TryLockError};
use std::io;
use std::path::Path;
use std::process::{Command, Stdio};
use std::sync::atomic::{AtomicBool, Ordering};
use std::thread;
use std::time::{Duration, Instant};

use serde::Serialize;

/// Shared by every project checkout and GPU runner on a host.
pub const DEFAULT_LOCK_PATH: &str = "/tmp/ai-optimizer-gpu.lock";

/// A physical GPU identity from NVIDIA management tooling.
#[derive(Debug, Serialize, PartialEq, Eq)]
pub struct Device {
    /// Stable physical identity; never substitute an enumeration index.
    pub uuid: String,
    /// Driver-reported model name.
    pub name: String,
    /// Total memory in MiB, as reported by nvidia-smi.
    pub memory_mib: u64,
}

/// Discovery has an explicit unavailable state and never launches kernels.
#[derive(Debug, Serialize)]
#[serde(tag = "status", rename_all = "snake_case")]
pub enum Discovery {
    /// At least one physical GPU was found.
    Available {
        /// All reported devices, ordered by UUID.
        devices: Vec<Device>,
    },
    /// Management tooling or hardware is unavailable or malformed.
    Unavailable {
        /// Diagnostic suitable for a result record.
        reason: String,
    },
}

/// Parse the documented CSV output, rejecting partial or ambiguous inventories.
pub fn parse_devices(output: &[u8]) -> Result<Vec<Device>, String> {
    let mut reader = csv::ReaderBuilder::new()
        .has_headers(false)
        .trim(csv::Trim::All)
        .from_reader(output);
    let mut devices = Vec::new();
    for row in reader.records() {
        let row = row.map_err(|error| error.to_string())?;
        if row.len() != 3 || !row[0].starts_with("GPU-") || row[0].len() <= 4 || row[1].is_empty() {
            return Err("invalid GPU inventory row".into());
        }
        let memory_mib = row[2].parse::<u64>().map_err(|_| "invalid GPU memory")?;
        if memory_mib == 0 {
            return Err("GPU memory must be positive".into());
        }
        devices.push(Device {
            uuid: row[0].into(),
            name: row[1].into(),
            memory_mib,
        });
    }
    devices.sort_by(|left, right| left.uuid.cmp(&right.uuid));
    if devices.windows(2).any(|pair| pair[0].uuid == pair[1].uuid) {
        return Err("duplicate GPU UUID".into());
    }
    Ok(devices)
}

/// Query physical devices with a five-second deadline and no CUDA context.
pub fn discover() -> Discovery {
    match query_devices() {
        Ok(devices) if !devices.is_empty() => Discovery::Available { devices },
        Ok(_) => Discovery::Unavailable {
            reason: "no NVIDIA devices reported".into(),
        },
        Err(reason) => Discovery::Unavailable { reason },
    }
}

fn query_devices() -> Result<Vec<Device>, String> {
    let mut child = Command::new("nvidia-smi")
        .args([
            "--query-gpu=uuid,name,memory.total",
            "--format=csv,noheader,nounits",
        ])
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .map_err(|error| format!("cannot execute nvidia-smi: {error}"))?;
    let start = Instant::now();
    loop {
        match child.try_wait() {
            Ok(Some(_)) => break,
            Ok(None) if start.elapsed() < Duration::from_secs(5) => {
                thread::sleep(Duration::from_millis(10))
            }
            outcome => {
                let _ = child.kill();
                let _ = child.wait();
                return Err(match outcome {
                    Err(error) => format!("nvidia-smi wait failed: {error}"),
                    _ => "nvidia-smi exceeded the five-second discovery deadline".into(),
                });
            }
        }
    }
    let output = child
        .wait_with_output()
        .map_err(|error| error.to_string())?;
    if !output.status.success() {
        return Err(format!(
            "nvidia-smi failed ({}): {}",
            output.status,
            String::from_utf8_lossy(&output.stderr).trim()
        ));
    }
    parse_devices(&output.stdout)
}

/// An exclusive advisory lock. The OS releases it on drop or process death.
///
/// All GPU consumers must use the same inode, including consumers of different
/// devices. Never unlink or replace the lock file to recover a stale lease.
pub struct GpuLease {
    _file: File,
}

impl GpuLease {
    /// Wait for ownership, bounded by timeout and cooperative cancellation.
    pub fn acquire(path: &Path, timeout: Duration, cancelled: &AtomicBool) -> io::Result<Self> {
        let file = OpenOptions::new()
            .read(true)
            .write(true)
            .create(true)
            .truncate(false)
            .open(path)?;
        let start = Instant::now();
        loop {
            if cancelled.load(Ordering::SeqCst) {
                return Err(io::Error::new(
                    io::ErrorKind::Interrupted,
                    "GPU lease cancelled",
                ));
            }
            match file.try_lock() {
                Ok(()) => return Ok(Self { _file: file }),
                Err(TryLockError::WouldBlock) if start.elapsed() < timeout => {
                    thread::sleep(Duration::from_millis(10));
                }
                Err(TryLockError::WouldBlock) => {
                    return Err(io::Error::new(
                        io::ErrorKind::TimedOut,
                        "GPU lease timed out",
                    ));
                }
                Err(TryLockError::Error(error)) => return Err(error),
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn inventory_is_sorted_and_csv_quoted_names_work() {
        let devices = parse_devices(b"GPU-b,\"model, B\",32\nGPU-a,model A,64\n").unwrap();
        assert_eq!(devices[0].uuid, "GPU-a");
        assert_eq!(devices[1].name, "model, B");
        assert_eq!(devices[0].memory_mib, 64);
    }

    #[test]
    fn malformed_and_duplicate_inventory_is_rejected() {
        for input in [
            "0,name,32",
            "GPU-a,name,N/A",
            "GPU-a,name,0",
            "GPU-a,name,32,extra",
            "GPU-a,name,32\nGPU-a,name,32",
        ] {
            assert!(parse_devices(input.as_bytes()).is_err(), "{input}");
        }
        assert!(parse_devices(b"").unwrap().is_empty());
    }
}
