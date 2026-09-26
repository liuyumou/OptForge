//! Bounded file input shared by the model and solve commands.

use std::ffi::OsStr;
use std::fs::File;
use std::io::{self, Read};
use std::path::Path;

/// Largest accepted input document, plus one sentinel byte to detect excess.
pub(crate) const MAX_INPUT_BYTES: u64 = 16 * 1024 * 1024;

/// Read one bounded document, preserving the native path in diagnostics.
pub(crate) fn read(path: &OsStr) -> io::Result<Vec<u8>> {
    read_with_limit(path, MAX_INPUT_BYTES)
}

/// Explicit bounded reader for accepted study inputs only.
pub(crate) fn read_with_limit(path: &OsStr, limit: u64) -> io::Result<Vec<u8>> {
    let _cost = optimizer_core::lp_cost::scope("input_read");
    let path = Path::new(path);
    let read_error =
        |error: io::Error| io::Error::other(format!("io: {}: {error}", path.display()));
    let mut bytes = Vec::new();
    File::open(path)
        .map_err(read_error)?
        .take(limit + 1)
        .read_to_end(&mut bytes)
        .map_err(read_error)?;
    if u64::try_from(bytes.len()).map_err(io::Error::other)? > limit {
        return Err(io::Error::other(format!(
            "document: {}: input exceeds {} MiB",
            path.display(),
            limit / (1024 * 1024)
        )));
    }
    Ok(bytes)
}

/// Categorized argument failure.
pub(crate) fn argument(message: &str) -> io::Error {
    io::Error::new(io::ErrorKind::InvalidInput, format!("argument: {message}"))
}
