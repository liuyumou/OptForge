//! Provenance collection for run records under SPEC-0005.
//!
//! Every fact here is measured rather than assumed: the revision comes from Git,
//! the toolchain from the tools themselves, and the backend version from the
//! adapter's own report. A build without the pinned library therefore says so
//! instead of claiming the version it was written against.

use std::io;
use std::process::Command;

use optimizer_cuda::session::DeviceSession;
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

/// Host facts for a run, naming the device when one was held.
///
/// SPEC-0007 requirement 9 is two rules, and this is the one function that has to
/// satisfy both: a CPU record must not claim GPU execution, and a GPU record must
/// identify the selected UUID, name and driver. The three fields are therefore all
/// null or all populated, and they are populated from a [`DeviceSession`] rather
/// than from a configuration string — holding one means the lease was taken, the
/// context was created and the driver confirmed the identity, so a record cannot
/// name a device the run did not actually open.
pub(crate) fn hardware(device: Option<&DeviceSession>) -> Hardware {
    Hardware {
        os: text("uname", &["-sr"]).unwrap_or_else(|| "unknown".to_owned()),
        cpu: cpu_model(),
        logical_cpus: std::thread::available_parallelism()
            .map(|count| u32::try_from(count.get()).unwrap_or(u32::MAX))
            .unwrap_or(1),
        gpu_uuid: device.map(|session| session.uuid().to_owned()),
        gpu_name: device.map(|session| session.name().to_owned()),
        driver: device.map(|session| session.driver_version().to_owned()),
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

/// Identifier for a run record, derived only from what the record describes.
///
/// SPEC-0005 requirement 1a. `kind` distinguishes the command that produced the
/// record, `model_id` names what was searched, and the digest is taken over the
/// input hashes the record already carries, so a different configuration over the
/// same model yields a different identifier.
///
/// This deliberately depends on nothing measured. An earlier implementation built
/// the identifier as `{kind}-{model_id}-{elapsed_ms}`, which made a record's
/// identity a property of how busy the host happened to be: two runs of the same
/// search got different identifiers, and two unrelated searches that took the same
/// number of milliseconds got the same one. Requirement 12 already excludes
/// elapsed time from meaning, and an identifier is not the place to smuggle it
/// back in.
///
/// Two runs of the same model and configuration therefore share an identifier.
/// That is the intended reading: the identifier names the inputs a record
/// describes, and whether two such runs actually agree is what `optimizer verify`
/// exists to answer. `revision` and `model_fingerprint` remain separate fields,
/// so the identifier does not duplicate the build or the model dimension.
pub(crate) fn record_id(kind: &str, model_id: &str, input_digests: &[&str]) -> String {
    let joined = input_digests.concat();
    let digest = optimizer_experiment::sha256::hex(joined.as_bytes());
    // Sixteen hex digits is 64 bits over inputs that are themselves SHA-256
    // digests, which is ample for distinguishing records a caller holds at once
    // and keeps the identifier readable.
    format!("{kind}-{model_id}-{}", &digest[..16])
}
