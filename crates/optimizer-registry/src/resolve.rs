//! Resolution: from recorded entries to registrations, or a refusal.
//!
//! Three rules carry this module.
//!
//! The declaration is authoritative and the entry is a claim about it. Every
//! field an entry records is checked against what the extension itself reports,
//! and a mismatch is refused in either direction rather than reconciled.
//! Reconciling would mean preferring one untrusted statement over another, and
//! it would let a document grant an extension a category or an authority the
//! code does not implement.
//!
//! Resolution is all-or-nothing. A search must never begin with a subset of the
//! extensions its configuration named, because the resulting record would
//! describe a search the caller did not request. That is the same rule SPEC-0005
//! requirement 14 applied by refusing outright; this module supplies the
//! mechanism instead, and keeps the refusal for everything it cannot check.
//!
//! Nothing here grants authority. Resolution decides which extensions the
//! SPEC-0004 host may consult; that host still validates every candidate against
//! the original model and checks every action against executive state.

use optimizer_core::{ErrorKind, Model, ValidationError};
use optimizer_extension::{
    CandidateProducer, Category, ExtensionDeclaration, ExtensionPolicy, ProblemClass, Registration,
    SearchAdviser,
};

use crate::conformance::ConformanceRecord;
use crate::document::{DataRequirement, HardwareRequirement, Promotion, RegistryEntry, is_hex};

/// Auxiliary input available to a provider when it constructs an extension.
///
/// The model is always present. An instance is present only when the caller has
/// one, which is what makes a `flow_shop_instance` data requirement checkable
/// rather than decorative.
///
/// The instance is carried as parsed bytes rather than as a typed
/// `FlowShopInstance` deliberately: this crate must not depend on
/// optimizer-schedule, or resolution would know about one application's data
/// model and the next application would have to amend it. The provider owns the
/// interpretation, exactly as it owns construction.
#[derive(Clone, Copy)]
pub struct ProviderContext<'a> {
    /// The original model the search will run over.
    pub model: &'a Model,
    /// Auxiliary instance document bytes, when the caller supplied one.
    pub instance: Option<&'a [u8]>,
}

impl<'a> ProviderContext<'a> {
    /// A context carrying only the model.
    pub fn new(model: &'a Model) -> Self {
        Self {
            model,
            instance: None,
        }
    }

    /// A context carrying the model and an auxiliary instance document.
    pub fn with_instance(model: &'a Model, instance: &'a [u8]) -> Self {
        Self {
            model,
            instance: Some(instance),
        }
    }

    /// Whether this context satisfies one data requirement.
    fn satisfies(&self, requirement: DataRequirement) -> bool {
        match requirement {
            DataRequirement::None => true,
            DataRequirement::FlowShopInstance => self.instance.is_some(),
        }
    }
}

/// One constructed extension, tagged by the role it is offered in.
///
/// Owned rather than borrowed, because a provider constructs the extension on
/// demand from the context. [`ResolvedSet`] keeps these alive for the search and
/// lends the SPEC-0004 `Registration` values the executive already accepts.
pub enum Provided {
    /// Constructed as a candidate producer.
    Producer(Box<dyn CandidateProducer>),
    /// Constructed as a search adviser.
    Adviser(Box<dyn SearchAdviser>),
}

impl Provided {
    /// The category this role corresponds to.
    fn category(&self) -> Category {
        match self {
            Self::Producer(_) => Category::CandidateProducer,
            Self::Adviser(_) => Category::SearchAdviser,
        }
    }

    /// What the extension itself reports about itself.
    fn declare(&self) -> ExtensionDeclaration {
        match self {
            Self::Producer(producer) => producer.declare(),
            Self::Adviser(adviser) => adviser.declare(),
        }
    }
}

/// Turns a recorded identity into an extension this build provides.
///
/// This is the seam that keeps the registry from becoming a list of blessed
/// first-party extensions, the same way `&dyn Backend` keeps SPEC-0002 from
/// naming HiGHS. The caller owns the table; this crate owns the checking.
pub trait Provider {
    /// Construct the extension named by `extension_id`, if this build has it.
    ///
    /// Returning `None` means "this build does not provide it", which resolution
    /// reports as unsupported. It does not mean "not permitted": permission is
    /// the caller's policy and is decided before a provider is consulted.
    fn provide(&self, extension_id: &str, context: &ProviderContext<'_>) -> Option<Provided>;
}

/// Reads a conformance record named by a promoted entry.
///
/// A trait rather than a path read directly, so resolution stays free of
/// filesystem access and a test can supply bytes without writing a file. The CLI
/// supplies the filesystem implementation.
pub trait ConformanceSource {
    /// Read the conformance record stored at `path`.
    fn read(&self, path: &str) -> Option<Vec<u8>>;
}

/// A [`ConformanceSource`] that always reports the record absent.
///
/// Resolving a promoted entry against this refuses, which is the correct default:
/// a caller that cannot read a conformance record cannot verify a promotion claim.
pub struct NoConformance;

impl ConformanceSource for NoConformance {
    fn read(&self, _path: &str) -> Option<Vec<u8>> {
        None
    }
}

/// One resolved extension and the declaration it was admitted on.
struct Resolved {
    extension_id: String,
    declaration: ExtensionDeclaration,
    provided: Provided,
}

/// The extensions one search may consult, owned for that search's lifetime.
///
/// Ordered by extension identity, so a registry document's line order is not
/// observable in a record. The SPEC-0004 host sorts by identity again, so this
/// ordering is belt and braces rather than the only guarantee.
pub struct ResolvedSet {
    resolved: Vec<Resolved>,
    warnings: Vec<String>,
}

// Written by hand rather than derived: the set owns boxed trait objects, which
// cannot be `Debug` without imposing that bound on every extension author. The
// identities and warnings are what a diagnostic actually needs.
impl std::fmt::Debug for ResolvedSet {
    fn fmt(&self, formatter: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        formatter
            .debug_struct("ResolvedSet")
            .field("identities", &self.identities())
            .field("warnings", &self.warnings)
            .finish()
    }
}

impl ResolvedSet {
    /// Whether nothing was resolved.
    pub fn is_empty(&self) -> bool {
        self.resolved.is_empty()
    }

    /// How many extensions were resolved.
    pub fn len(&self) -> usize {
        self.resolved.len()
    }

    /// Borrowed registrations for [`optimizer_solver::search_with_extensions`].
    pub fn registrations(&self) -> Vec<Registration<'_>> {
        self.resolved
            .iter()
            .map(|resolved| match &resolved.provided {
                Provided::Producer(producer) => Registration::Producer(producer.as_ref()),
                Provided::Adviser(adviser) => Registration::Adviser(adviser.as_ref()),
            })
            .collect()
    }

    /// The declaration one resolved extension was admitted on.
    pub fn declaration(&self, extension_id: &str) -> Option<&ExtensionDeclaration> {
        self.resolved
            .iter()
            .find(|resolved| resolved.extension_id == extension_id)
            .map(|resolved| &resolved.declaration)
    }

    /// Identities that resolved, in identity order.
    pub fn identities(&self) -> Vec<&str> {
        self.resolved
            .iter()
            .map(|resolved| resolved.extension_id.as_str())
            .collect()
    }

    /// Warnings a record must carry, one per registered experimental extension.
    ///
    /// A record that concealed an unpromoted extension's participation would let
    /// a reader assume conformance evidence exists where none does.
    pub fn warnings(&self) -> &[String] {
        &self.warnings
    }
}

/// Resolve the entries a policy names, or refuse.
///
/// `entries` is the validated registry's entry list, `policies` is the search
/// configuration's extension policy, and `provider` supplies the extensions this
/// build has. Experimental entries are refused unless `allow_experimental`.
///
/// # Errors
///
/// Returns a categorized [`ValidationError`] for a policy naming an entry the
/// registry does not record, an entry the provider does not supply, an entry
/// disagreeing with its extension's own declaration, an unsatisfied data
/// requirement, a device requirement, an unsatisfied `requires`, a declared
/// conflict, an unpermitted experimental entry, or an unverifiable promotion
/// claim.
pub fn resolve(
    entries: &[RegistryEntry],
    policies: &[ExtensionPolicy],
    provider: &dyn Provider,
    context: &ProviderContext<'_>,
) -> Result<ResolvedSet, ValidationError> {
    resolve_with(
        entries,
        policies,
        provider,
        context,
        &NoConformance,
        Options::default(),
    )
}

/// Caller choices that widen what resolution accepts.
///
/// Both default to the restrictive setting, so the permissive case is always
/// something a caller asked for explicitly and is visible in the command that
/// produced a record.
#[derive(Clone, Copy, Debug, Default)]
pub struct Options {
    /// Permit registering an entry with no conformance claim.
    pub allow_experimental: bool,
    /// Resolve a promoted entry without verifying its conformance record.
    ///
    /// Set only by the conformance suite, which produces the very record a
    /// promoted entry cites. Requiring the record there would make the first
    /// conformance run for any extension impossible. No command surface sets this:
    /// a caller cannot ask for a promotion claim to go unchecked.
    pub skip_promotion_check: bool,
}

/// Resolve with an explicit conformance source and caller options.
///
/// # Errors
///
/// As [`resolve`].
pub fn resolve_with(
    entries: &[RegistryEntry],
    policies: &[ExtensionPolicy],
    provider: &dyn Provider,
    context: &ProviderContext<'_>,
    conformance: &dyn ConformanceSource,
    options: Options,
) -> Result<ResolvedSet, ValidationError> {
    let unsupported = |message: String| ValidationError::new(ErrorKind::Unsupported, message);
    let structural = |message: String| ValidationError::new(ErrorKind::Structural, message);

    let mut resolved: Vec<Resolved> = Vec::new();
    let mut warnings: Vec<String> = Vec::new();

    // Policy order is not used. Sorting by identity here means two registries
    // differing only in line order, and two policies differing only in order,
    // resolve identically.
    let mut named: Vec<&ExtensionPolicy> = policies.iter().collect();
    named.sort_by(|left, right| left.extension_id.cmp(&right.extension_id));

    for policy in named {
        let entry = entries
            .iter()
            .find(|entry| entry.extension_id == policy.extension_id)
            .ok_or_else(|| {
                unsupported(format!(
                    "{}: named by the search configuration but absent from the registry",
                    policy.extension_id
                ))
            })?;

        // Checked before the provider is consulted, so an entry requiring a
        // device or missing its data is refused without constructing anything.
        if entry.hardware_requirement == HardwareRequirement::Gpu {
            return Err(unsupported(format!(
                "{}: requires hardware {}; no device selection exists in this build",
                entry.extension_id,
                entry.hardware_requirement.as_str()
            )));
        }
        if !context.satisfies(entry.data_requirement) {
            return Err(unsupported(format!(
                "{}: requires {} which this command did not supply",
                entry.extension_id,
                entry.data_requirement.as_str()
            )));
        }

        // Requirement 12: permission is decided before construction, so an
        // unpermitted experimental entry never runs any provider code.
        match &entry.promotion {
            Promotion::Experimental if !options.allow_experimental => {
                return Err(unsupported(format!(
                    "{}: is experimental and no conformance record is claimed; \
                     pass --allow-experimental to register it anyway",
                    entry.extension_id
                )));
            }
            Promotion::Experimental => warnings.push(format!(
                "registered experimental extension {} version {} with no conformance record",
                entry.extension_id, entry.version
            )),
            Promotion::Promoted { .. } if options.skip_promotion_check => {}
            Promotion::Promoted {
                conformance_path,
                conformance_sha256,
            } => check_promotion(entry, conformance_path, conformance_sha256, conformance)?,
        }

        let provided = provider
            .provide(&entry.extension_id, context)
            .ok_or_else(|| {
                unsupported(format!(
                    "{}: recorded in the registry but not provided by this build",
                    entry.extension_id
                ))
            })?;

        // The declaration is authoritative from here on. Note this is read once
        // and compared; a declaration that disagrees with the entry is refused
        // rather than trusted in either direction.
        let declaration = provided.declare();
        check_declaration(entry, &declaration, &provided)?;

        resolved.push(Resolved {
            extension_id: entry.extension_id.clone(),
            declaration,
            provided,
        });
    }

    // Requirement 10: inter-extension rules are checked over the whole resolved
    // set, because whether a requirement holds depends on what else resolved.
    let identities: Vec<&str> = resolved
        .iter()
        .map(|resolved| resolved.extension_id.as_str())
        .collect();
    for resolved_entry in &resolved {
        let entry = entries
            .iter()
            .find(|entry| entry.extension_id == resolved_entry.extension_id)
            .expect("a resolved entry came from this registry");
        for required in &entry.requires {
            if !identities.contains(&required.as_str()) {
                return Err(structural(format!(
                    "{}: requires {required}, which the search configuration does not register",
                    entry.extension_id
                )));
            }
        }
        for conflicting in &entry.conflicts_with {
            if identities.contains(&conflicting.as_str()) {
                return Err(structural(format!(
                    "{}: conflicts with {conflicting}, which is registered by the same search",
                    entry.extension_id
                )));
            }
        }
    }

    resolved.sort_by(|left, right| left.extension_id.cmp(&right.extension_id));
    warnings.sort_unstable();
    Ok(ResolvedSet { resolved, warnings })
}

/// Refuse an entry whose claims disagree with the extension's own declaration.
fn check_declaration(
    entry: &RegistryEntry,
    declaration: &ExtensionDeclaration,
    provided: &Provided,
) -> Result<(), ValidationError> {
    let unsupported = |field: &str, recorded: String, declared: String| {
        ValidationError::new(
            ErrorKind::Unsupported,
            format!(
                "{}: registry records {field} {recorded} but the extension declares {declared}",
                entry.extension_id
            ),
        )
    };

    // Its own shape first: an invalid declaration says nothing reliable about
    // the fields the later comparisons would read.
    let declaration = declaration.validate()?;

    if declaration.extension_id != entry.extension_id {
        return Err(unsupported(
            "extension_id",
            entry.extension_id.clone(),
            declaration.extension_id,
        ));
    }
    if declaration.version != entry.version {
        return Err(unsupported(
            "version",
            entry.version.clone(),
            declaration.version,
        ));
    }
    if declaration.category != entry.category {
        return Err(unsupported(
            "category",
            entry.category.as_str().to_owned(),
            declaration.category.as_str().to_owned(),
        ));
    }
    // A provider returning the wrong role is refused rather than reinterpreted,
    // for the same reason SPEC-0004 refuses a role/category disagreement:
    // guessing would grant unintended authority.
    if provided.category() != entry.category {
        return Err(unsupported(
            "category",
            entry.category.as_str().to_owned(),
            format!("was constructed as {}", provided.category().as_str()),
        ));
    }
    if declaration.host_contract_version != entry.host_contract_version {
        return Err(unsupported(
            "host_contract_version",
            entry.host_contract_version.to_string(),
            declaration.host_contract_version.to_string(),
        ));
    }
    if declaration.deterministic != entry.deterministic {
        return Err(unsupported(
            "deterministic",
            entry.deterministic.to_string(),
            declaration.deterministic.to_string(),
        ));
    }
    if declaration.limits != entry.limits {
        return Err(unsupported(
            "limits",
            format!(
                "{}/{}",
                entry.limits.max_invocations, entry.limits.max_proposals
            ),
            format!(
                "{}/{}",
                declaration.limits.max_invocations, declaration.limits.max_proposals
            ),
        ));
    }
    // Both lists are sorted and deduplicated by their own validation, so this
    // compares sets rather than orders.
    let mut declared_classes = declaration.problem_classes.clone();
    declared_classes.sort_unstable();
    let mut recorded_classes: Vec<ProblemClass> = entry.problem_classes.clone();
    recorded_classes.sort_unstable();
    if declared_classes != recorded_classes {
        return Err(unsupported(
            "problem_classes",
            format!("{recorded_classes:?}"),
            format!("{declared_classes:?}"),
        ));
    }
    Ok(())
}

/// Refuse a promoted entry whose conformance claim cannot be verified.
fn check_promotion(
    entry: &RegistryEntry,
    path: &str,
    expected_sha256: &str,
    conformance: &dyn ConformanceSource,
) -> Result<(), ValidationError> {
    let unsupported = |message: String| ValidationError::new(ErrorKind::Unsupported, message);

    let bytes = conformance.read(path).ok_or_else(|| {
        unsupported(format!(
            "{}: claims a conformance record at {path}, which could not be read",
            entry.extension_id
        ))
    })?;

    let actual = sha256_hex(&bytes);
    if !is_hex(expected_sha256, 64) || actual != expected_sha256 {
        return Err(unsupported(format!(
            "{}: conformance record {path} has checksum {actual}, not the recorded {expected_sha256}",
            entry.extension_id
        )));
    }

    let record = ConformanceRecord::from_json(&bytes)?;
    if !record.outcome {
        let failed: Vec<&str> = record
            .checks
            .iter()
            .filter(|check| !check.passed)
            .map(|check| check.name.as_str())
            .collect();
        return Err(unsupported(format!(
            "{}: conformance record {path} did not pass; failed checks: {}",
            entry.extension_id,
            failed.join(", ")
        )));
    }
    // A record for another extension, or another version of this one, is not
    // evidence about what is being registered now.
    if record.extension_id != entry.extension_id {
        return Err(unsupported(format!(
            "{}: conformance record {path} describes {} instead",
            entry.extension_id, record.extension_id
        )));
    }
    if record.version != entry.version {
        return Err(unsupported(format!(
            "{}: conformance record {path} describes version {}, not {}",
            entry.extension_id, record.version, entry.version
        )));
    }
    Ok(())
}

/// SHA-256 of `bytes` as 64 lowercase hex digits.
///
/// Delegates to optimizer-experiment's implementation, which is checked against
/// the FIPS 180-4 published vectors and independently against Python's `hashlib`.
/// Reimplementing it here would create a second thing to keep correct.
fn sha256_hex(bytes: &[u8]) -> String {
    optimizer_experiment::sha256::hex(bytes)
}
