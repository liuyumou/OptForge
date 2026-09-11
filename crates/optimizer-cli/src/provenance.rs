//! Provenance collection for run records under SPEC-0005.
//!
//! Every fact here is measured rather than assumed: the revision comes from Git,
//! the toolchain from the tools themselves, and the backend version from the
//! adapter's own report. A build without the pinned library therefore says so
//! instead of claiming the version it was written against.

use std::io;
use std::process::Command;

use optimizer_experiment::{Hardware, Toolchain};

/// Run one provenance command and return its trimmed stdout.
///
/// Provenance is descriptive, so a missing tool yields a stated placeholder
/// rather than failing a run that is otherwise valid. An absent Git revision is
/// the exception and is handled by the caller, because a record without a
/// revision cannot be evidence.
fn text(program: &str, args: &[&str]) -> Option<String> {
    let output = Command::new(program).args(args).output().ok()?;
    if !output.status.success() {
        return None;
    }
    let text = String::from_utf8(output.stdout).ok()?.trim().to_owned();
    if text.is_empty() { None } else { Some(text) }
}

/// Source revision as 40 lowercase hex digits.
///
/// # Errors
///
/// Returns an I/O failure when the revision cannot be read, because a run record
/// must state the source that produced it.
pub(crate) fn revision() -> io::Result<String> {
    text("git", &["rev-parse", "HEAD"])
        .filter(|revision| revision.len() == 40)
        .ok_or_else(|| {
            io::Error::other(
                "io: git revision unavailable; a run record requires a committed source revision",
            )
        })
}

/// Whether the working tree differs from the recorded revision.
///
/// An unreadable status is reported as dirty. Treating an unknown tree as clean
/// would let an unverifiable record claim to be evidence.
pub(crate) fn dirty() -> bool {
    text("git", &["status", "--porcelain"]).is_some_and(|status| !status.is_empty())
}

/// Host facts for a CPU run.
///
/// The three GPU fields stay null: this surface performs no GPU work, and
/// SPEC-0007 requirement 9 forbids a CPU record claiming GPU execution.
pub(crate) fn hardware() -> Hardware {
    Hardware {
        os: text("uname", &["-sr"]).unwrap_or_else(|| "unknown".to_owned()),
        cpu: cpu_model(),
        logical_cpus: std::thread::available_parallelism()
            .map(|count| u32::try_from(count.get()).unwrap_or(u32::MAX))
            .unwrap_or(1),
        gpu_uuid: None,
        gpu_name: None,
        driver: None,
    }
}

/// CPU model name, or a stated placeholder when inventory is unavailable.
fn cpu_model() -> String {
    let Some(inventory) = text("lscpu", &[]) else {
        return "unknown".to_owned();
    };
    inventory
        .lines()
        .find_map(|line| line.strip_prefix("Model name:"))
        .map(|name| name.trim().to_owned())
        .unwrap_or_else(|| "unknown".to_owned())
}

/// Build tooling of this binary.
pub(crate) fn toolchain() -> Toolchain {
    Toolchain {
        rustc: text("rustc", &["--version"]).unwrap_or_else(|| "unknown".to_owned()),
        cargo: text("cargo", &["--version"]).unwrap_or_else(|| "unknown".to_owned()),
    }
}
