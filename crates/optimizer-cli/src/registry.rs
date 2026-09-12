//! The builtin provider table and registry subcommands under SPEC-0009.
//!
//! This module is where the registry meets concrete extensions. optimizer-registry
//! deliberately knows no extension by name, so the table lives here, in the crate
//! that already depends on both example crates. Adding an extension to this table
//! is what makes it resolvable; a registry document alone cannot introduce one.
//!
//! The hostile fixtures from the C3 example crate are deliberately absent. They
//! exist to be refused in tests, and shipping them as resolvable identities would
//! hand a caller a way to register something built to misbehave.

use std::ffi::{OsStr, OsString};
use std::io::{self, Write};

use optimizer_core::Model;
use optimizer_highs::HighsBackend;
use optimizer_registry::{
    ConformanceSource, Options, Provided, Provider, ProviderContext, RegistryDocument,
    RegistryEntry, ResolvedSet, resolve_with,
};
use optimizer_schedule::FlowShopInstance;
use optimizer_schedule_examples::{RefusedKind, RefusedProducer, SchedulingProducer};

use crate::input::{argument, read};

/// Extensions this build provides, keyed by the identity they declare.
///
/// A flow-shop producer needs its instance, which is why the context carries one
/// and why an entry declaring `flow_shop_instance` is refused without it: the
/// producer cannot be constructed from a model alone.
pub(crate) struct Builtin;

impl Provider for Builtin {
    fn provide(&self, extension_id: &str, context: &ProviderContext<'_>) -> Option<Provided> {
        match extension_id {
            SchedulingProducer::ID => {
                // A malformed instance is not this seam's error to report: the
                // caller's document was already parsed before resolution, so
                // failing here means the bytes are not an instance at all, and
                // resolution reports the identity as unprovided.
                let instance = FlowShopInstance::from_json(context.instance?).ok()?;
                Some(Provided::Producer(Box::new(SchedulingProducer::new(
                    instance,
                ))))
            }
            RefusedProducer::ID => {
                let instance = FlowShopInstance::from_json(context.instance?).ok()?;
                Some(Provided::Producer(Box::new(RefusedProducer::new(
                    instance,
                    RefusedKind::RepeatedPosition,
                ))))
            }
            // The C3 example extensions are deliberately absent. That crate is
            // where hostile fixtures live, it takes the executive only as a test
            // dependency, and its honest extensions exist to demonstrate the
            // contract rather than to be shipped. Adding it here would make the
            // CLI depend on a test-fixture crate and would hand a caller
            // resolvable identities built to misbehave.
            _ => None,
        }
    }
}

/// Reads a conformance record from the filesystem.
///
/// Resolution stays free of filesystem access so a test can supply bytes without
/// writing a file; this is the implementation that gives it one.
pub(crate) struct Files;

impl ConformanceSource for Files {
    fn read(&self, path: &str) -> Option<Vec<u8>> {
        read(OsStr::new(path)).ok()
    }
}

/// Everything the registry flags contribute to a command.
#[derive(Default)]
pub(crate) struct RegistryArguments {
    /// The registry document, when the caller named one.
    pub(crate) path: Option<OsString>,
    /// Whether an entry with no conformance claim may be registered.
    pub(crate) allow_experimental: bool,
}

impl RegistryArguments {
    /// Resolve a configuration's extension policy, or refuse.
    ///
    /// Returns `None` when the policy is empty, which is what keeps
    /// requirement 17 exact: the caller then takes the extension-free entry point
    /// and produces byte-identical records whether or not a registry was named.
    ///
    /// # Errors
    ///
    /// Returns a categorized failure when the policy is non-empty and no registry
    /// was named, when the registry cannot be read or parsed, or when resolution
    /// refuses any named entry.
    pub(crate) fn resolve<'a>(
        &self,
        policies: &[optimizer_extension::ExtensionPolicy],
        model: &'a Model,
        instance: Option<&'a [u8]>,
    ) -> io::Result<Option<ResolvedSet>> {
        if policies.is_empty() {
            return Ok(None);
        }
        let Some(path) = self.path.as_ref() else {
            return Err(io::Error::other(
                "unsupported: this configuration names an extension policy but no registry \
                 was given; pass --registry <path> naming the extension it requires",
            ));
        };
        let document = RegistryDocument::from_json(&read(path)?).map_err(io::Error::other)?;
        let context = instance.map_or_else(
            || ProviderContext::new(model),
            |instance| ProviderContext::with_instance(model, instance),
        );
        let resolved = resolve_with(
            &document.entries,
            policies,
            &Builtin,
            &context,
            &Files,
            Options {
                allow_experimental: self.allow_experimental,
                ..Options::default()
            },
        )
        .map_err(io::Error::other)?;
        Ok(Some(resolved))
    }
}

/// Parse `--registry` and `--allow-experimental` out of a flag list.
///
/// Returns the remaining flags so each command keeps parsing its own, and a
/// misspelled flag stays that command's argument error rather than becoming a
/// silently ignored one.
pub(crate) fn take_arguments(
    options: &[OsString],
) -> io::Result<(RegistryArguments, Vec<OsString>)> {
    let mut arguments = RegistryArguments::default();
    let mut rest = Vec::new();
    let mut index = 0;
    while index < options.len() {
        let key = options[index]
            .to_str()
            .ok_or_else(|| argument("flag names must be UTF-8 text"))?;
        match key {
            "--allow-experimental" => {
                if arguments.allow_experimental {
                    return Err(argument("duplicate flag --allow-experimental"));
                }
                arguments.allow_experimental = true;
                index += 1;
            }
            "--registry" => {
                let value = options
                    .get(index + 1)
                    .ok_or_else(|| argument("--registry requires a value"))?;
                if arguments.path.replace(value.clone()).is_some() {
                    return Err(argument("duplicate flag --registry"));
                }
                index += 2;
            }
            _ => {
                rest.push(options[index].clone());
                index += 1;
            }
        }
    }
    Ok((arguments, rest))
}

/// Report every entry a registry records.
pub(crate) fn list(options: &[OsString]) -> io::Result<u8> {
    let (arguments, rest) = take_arguments(options)?;
    if let Some(unexpected) = rest.first() {
        return Err(argument(&format!(
            "unknown flag {}",
            unexpected.to_string_lossy()
        )));
    }
    let path = arguments
        .path
        .as_ref()
        .ok_or_else(|| argument("--registry is required"))?;
    let document = RegistryDocument::from_json(&read(path)?).map_err(io::Error::other)?;

    // Listing reports what a registry claims and, separately, whether this build
    // provides the identity at all. A reader can therefore see an entry that would
    // be refused without having to attempt a search to find out.
    let entries: Vec<serde_json::Value> = document
        .entries
        .iter()
        .map(|entry| {
            serde_json::json!({
                "extension_id": entry.extension_id,
                "version": entry.version,
                "license": entry.license,
                "category": entry.category.as_str(),
                "deterministic": entry.deterministic,
                "data_requirement": entry.data_requirement.as_str(),
                "hardware_requirement": entry.hardware_requirement.as_str(),
                "promoted": entry.promotion.is_promoted(),
                "provided_by_this_build": provides(&entry.extension_id),
            })
        })
        .collect();

    let report = serde_json::to_string_pretty(&serde_json::json!({
        "schema_version": optimizer_registry::REGISTRY_SCHEMA_VERSION,
        "registry_id": document.registry_id,
        "entries": entries,
        "note": "A listed entry is a claim. Resolution checks it against the extension's \
                 own declaration and refuses a mismatch."
    }))?;
    let mut stdout = io::stdout().lock();
    writeln!(stdout, "{report}")
        .and_then(|()| stdout.flush())
        .map_err(|error| io::Error::other(format!("io: stdout: {error}")))?;
    Ok(0)
}

/// Whether this build provides `extension_id` at all.
///
/// Probed with an empty context, so an extension needing auxiliary data reports
/// its identity as known rather than as absent: the two are different facts and a
/// listing should not conflate them.
fn provides(extension_id: &str) -> bool {
    matches!(extension_id, SchedulingProducer::ID | RefusedProducer::ID)
}

/// Run the conformance suite over one entry and write its record.
pub(crate) fn check(options: &[OsString]) -> io::Result<u8> {
    let (arguments, rest) = take_arguments(options)?;
    let mut extension = None;
    let mut instance_path = None;
    let mut output_path = None;
    for pair in rest.chunks(2) {
        let [key, value] = pair else {
            return Err(argument("each flag requires a value"));
        };
        let key = key
            .to_str()
            .ok_or_else(|| argument("flag names must be UTF-8 text"))?;
        let slot = match key {
            "--extension" => &mut extension,
            "--instance" => &mut instance_path,
            "--output" => &mut output_path,
            _ => return Err(argument(&format!("unknown flag {key}"))),
        };
        if slot.replace(value.clone()).is_some() {
            return Err(argument(&format!("duplicate flag {key}")));
        }
    }
    let registry_path = arguments
        .path
        .as_ref()
        .ok_or_else(|| argument("--registry is required"))?;
    let extension = extension.ok_or_else(|| argument("--extension is required"))?;
    let extension = extension
        .to_str()
        .ok_or_else(|| argument("extension identities must be UTF-8 text"))?;

    let document = RegistryDocument::from_json(&read(registry_path)?).map_err(io::Error::other)?;
    let entry: &RegistryEntry = document.entry(extension).ok_or_else(|| {
        io::Error::other(format!(
            "unsupported: {extension} is not recorded in this registry"
        ))
    })?;

    // The instance is read here rather than inside the suite, so a malformed
    // document is an input error before any search runs.
    let instance = match instance_path {
        Some(path) => Some(read(&path)?),
        None => None,
    };

    let backend = HighsBackend::new();
    let record =
        optimizer_registry::conformance::run(entry, &Builtin, &backend, instance.as_deref())
            .map_err(io::Error::other)?;
    let outcome = record.outcome;
    let document = record.to_json().map_err(io::Error::other)?;

    match output_path {
        Some(path) => std::fs::write(&path, format!("{document}\n")).map_err(|error| {
            io::Error::other(format!(
                "io: {}: {error}",
                std::path::Path::new(&path).display()
            ))
        })?,
        None => {
            let mut stdout = io::stdout().lock();
            writeln!(stdout, "{document}")
                .and_then(|()| stdout.flush())
                .map_err(|error| io::Error::other(format!("io: stdout: {error}")))?;
        }
    }

    // A failed conformance run is a result about an extension, not an error about
    // this command, so the record is written either way and only the exit code
    // distinguishes them.
    Ok(u8::from(!outcome))
}
