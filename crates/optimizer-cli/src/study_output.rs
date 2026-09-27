//! No-replace publication for new study evidence outputs (SPEC-0015).
use std::fs::{File, OpenOptions};
use std::io::{self, Write};
use std::path::{Path, PathBuf};

pub(crate) struct AtomicOutput {
    destination: PathBuf,
    partial: PathBuf,
}

impl AtomicOutput {
    /// Preflight before solving; publication also refuses races with other writers.
    pub(crate) fn new(destination: &Path) -> io::Result<Self> {
        let partial = destination.with_extension("partial");
        if destination == partial {
            return Err(crate::input::argument(
                "study output must not use the .partial extension",
            ));
        }
        for path in [destination, &partial] {
            match std::fs::symlink_metadata(path) {
                Ok(_) => {
                    return Err(io::Error::new(
                        io::ErrorKind::AlreadyExists,
                        format!("study output already exists: {}", path.display()),
                    ));
                }
                Err(error) if error.kind() == io::ErrorKind::NotFound => (),
                Err(error) => return Err(error),
            }
        }
        Ok(Self {
            destination: destination.into(),
            partial,
        })
    }

    pub(crate) fn publish(self, bytes: &[u8]) -> io::Result<()> {
        self.publish_with(|file| file.write_all(bytes))
    }

    fn publish_with(self, write: impl FnOnce(&mut File) -> io::Result<()>) -> io::Result<()> {
        let mut file = OpenOptions::new()
            .write(true)
            .create_new(true)
            .open(&self.partial)?;
        write(&mut file)?;
        file.sync_all()?;
        // Same-directory hard-link creation is atomic and refuses replacement.
        // Keep the partial after any failed write/publication for diagnosis.
        std::fs::hard_link(&self.partial, &self.destination)?;
        std::fs::remove_file(&self.partial)?;
        let parent = self
            .destination
            .parent()
            .filter(|p| !p.as_os_str().is_empty())
            .unwrap_or(Path::new("."));
        File::open(parent)?.sync_all()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::sync::atomic::{AtomicUsize, Ordering};

    #[test]
    fn failed_writes_and_destination_races_preserve_partial_and_original() {
        static NEXT: AtomicUsize = AtomicUsize::new(0);
        let dir = std::env::temp_dir().join(format!(
            "compact-output-{}-{}",
            std::process::id(),
            NEXT.fetch_add(1, Ordering::SeqCst)
        ));
        std::fs::create_dir(&dir).unwrap();
        let destination = dir.join("evidence.json");
        let output = AtomicOutput::new(&destination).unwrap();
        assert!(
            output
                .publish_with(|f| {
                    f.write_all(b"partial")?;
                    Err(io::Error::other("injected write failure"))
                })
                .is_err()
        );
        assert!(!destination.exists());
        assert_eq!(
            std::fs::read(destination.with_extension("partial")).unwrap(),
            b"partial"
        );
        assert!(AtomicOutput::new(&destination).is_err());
        std::fs::remove_file(destination.with_extension("partial")).unwrap();
        let output = AtomicOutput::new(&destination).unwrap();
        std::fs::write(&destination, b"other writer").unwrap();
        assert!(output.publish(b"new evidence").is_err());
        assert_eq!(std::fs::read(&destination).unwrap(), b"other writer");
        assert_eq!(
            std::fs::read(destination.with_extension("partial")).unwrap(),
            b"new evidence"
        );
        std::fs::remove_dir_all(dir).unwrap();
    }
}
