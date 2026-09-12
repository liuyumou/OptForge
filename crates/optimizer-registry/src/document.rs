//! The registry document and its entries under SPEC-0009.
//!
//! An entry is a *claim* about an extension, not a grant. Nothing an entry says
//! is trusted: resolution checks every field against the extension's own
//! declaration, and the authority an entry records must be the authority
//! SPEC-0004 derives from its category. An entry that could widen what an
//! extension is permitted to do would defeat the point of having one.
//!
//! The fields SPEC-0004 deliberately parked live here and are checked rather
//! than decorative: a data requirement is refused when the caller supplied no
//! matching input, a hardware requirement naming a device is refused outright,
//! and promotion names a conformance record whose bytes are verified.

use serde::{Deserialize, Serialize};

use optimizer_core::{ErrorKind, ValidationError, nested_version};
use optimizer_extension::{
    Authority, Category, DeclaredLimits, MAX_EXTENSION_ID_BYTES, ProblemClass,
};

use crate::serde_strict::deserialize_object;

/// Current registry document and entry wire version.
pub const REGISTRY_SCHEMA_VERSION: u32 = 1;

/// Longest accepted license identifier, in bytes.
///
/// A license reaches diagnostics and a listing, so its length is bounded rather
/// than caller-controlled, matching the rule already applied to identifiers.
pub const MAX_LICENSE_BYTES: usize = 64;

/// Auxiliary input an extension needs beyond the model.
///
/// This gives SPEC-0004's parked "data needs" field a checked meaning. A
/// producer built from a flow-shop instance cannot be constructed from a model
/// alone, so an entry declaring that need is refused when no instance was
/// supplied rather than being handed a default.
#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum DataRequirement {
    /// The model is sufficient.
    None,
    /// A flow-shop instance document is required.
    FlowShopInstance,
}

impl<'de> Deserialize<'de> for DataRequirement {
    fn deserialize<D: serde::Deserializer<'de>>(deserializer: D) -> Result<Self, D::Error> {
        const NAMES: &[&str] = &["none", "flow_shop_instance"];
        match String::deserialize(deserializer)?.as_str() {
            "none" => Ok(Self::None),
            "flow_shop_instance" => Ok(Self::FlowShopInstance),
            other => Err(serde::de::Error::unknown_variant(other, NAMES)),
        }
    }
}

impl DataRequirement {
    /// Stable lowercase diagnostic name.
    pub fn as_str(self) -> &'static str {
        match self {
            Self::None => "none",
            Self::FlowShopInstance => "flow_shop_instance",
        }
    }
}

/// Device class an extension needs.
///
/// `Gpu` exists so an entry can state the need and be refused for it. Omitting
/// the variant would let a GPU extension misdeclare itself as CPU-only and be
/// admitted; refusing a stated need is a clearer boundary than not being able to
/// state it. No device selection exists before C6.
#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum HardwareRequirement {
    /// Runs on the CPU, like every extension this build can host.
    Cpu,
    /// Requires a GPU, which is refused at resolution.
    Gpu,
}

impl<'de> Deserialize<'de> for HardwareRequirement {
    fn deserialize<D: serde::Deserializer<'de>>(deserializer: D) -> Result<Self, D::Error> {
        const NAMES: &[&str] = &["cpu", "gpu"];
        match String::deserialize(deserializer)?.as_str() {
            "cpu" => Ok(Self::Cpu),
            "gpu" => Ok(Self::Gpu),
            other => Err(serde::de::Error::unknown_variant(other, NAMES)),
        }
    }
}

impl HardwareRequirement {
    /// Stable lowercase diagnostic name.
    pub fn as_str(self) -> &'static str {
        match self {
            Self::Cpu => "cpu",
            Self::Gpu => "gpu",
        }
    }
}

/// Whether an entry claims a passing conformance record, and where it is.
///
/// A promoted entry's claim is checkable: resolution reads the named record,
/// verifies its bytes against the recorded checksum, and requires a passing
/// outcome for this extension's own identity and version. Promotion is
/// deliberately not assertable by prose in an entry alone.
#[derive(Clone, Debug, PartialEq, Eq, Serialize)]
#[serde(tag = "state", rename_all = "snake_case")]
pub enum Promotion {
    /// No conformance claim. Registering one requires explicit permission.
    Experimental,
    /// A conformance record is claimed at this path with these bytes.
    Promoted {
        /// Repository-relative path of the conformance record.
        conformance_path: String,
        /// SHA-256 of that record, as 64 lowercase hex digits.
        conformance_sha256: String,
    },
}

// Serde's internally tagged enums accept an unknown field on a unit variant, the
// same defect the M1 review found on infinite bounds. Deserialize by hand so an
// experimental entry carrying a stray conformance path is refused rather than
// silently ignored, which would let a document look promoted while resolving as
// experimental.
impl<'de> Deserialize<'de> for Promotion {
    fn deserialize<D: serde::Deserializer<'de>>(deserializer: D) -> Result<Self, D::Error> {
        #[derive(Deserialize)]
        #[serde(deny_unknown_fields)]
        struct Fields {
            state: String,
            conformance_path: Option<String>,
            conformance_sha256: Option<String>,
        }

        let fields: Fields = crate::serde_strict::object(deserializer)?;
        match (
            fields.state.as_str(),
            fields.conformance_path,
            fields.conformance_sha256,
        ) {
            ("experimental", None, None) => Ok(Self::Experimental),
            ("experimental", _, _) => Err(serde::de::Error::custom(
                "experimental promotion must not name a conformance record",
            )),
            ("promoted", Some(conformance_path), Some(conformance_sha256)) => Ok(Self::Promoted {
                conformance_path,
                conformance_sha256,
            }),
            ("promoted", _, _) => Err(serde::de::Error::custom(
                "promoted promotion requires conformance_path and conformance_sha256",
            )),
            (other, _, _) => Err(serde::de::Error::unknown_variant(
                other,
                &["experimental", "promoted"],
            )),
        }
    }
}

impl Promotion {
    /// Whether this entry claims a passing conformance record.
    pub fn is_promoted(&self) -> bool {
        matches!(self, Self::Promoted { .. })
    }
}

/// One extension's recorded metadata: what it is claimed to be.
#[derive(Clone, Debug, PartialEq, Eq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct RegistryEntry {
    /// Must equal [`REGISTRY_SCHEMA_VERSION`].
    pub schema_version: u32,
    /// Identity resolution matches against a policy and a record summary.
    pub extension_id: String,
    /// Version this entry claims the extension reports.
    pub version: String,
    /// License identifier, recorded so a caller can audit what it registers.
    pub license: String,
    /// Category this entry claims the extension declares.
    pub category: Category,
    /// Authority the category implies. Checked, never chosen.
    pub authority_basis: Authority,
    /// Host contract version this entry claims the extension declares.
    pub host_contract_version: u32,
    /// Problem classes this entry claims the extension supports.
    pub problem_classes: Vec<ProblemClass>,
    /// Determinism this entry claims the extension declares.
    pub deterministic: bool,
    /// Counted limits this entry claims the extension declares.
    pub limits: DeclaredLimits,
    /// Auxiliary input the extension needs beyond the model.
    pub data_requirement: DataRequirement,
    /// Device class the extension needs.
    pub hardware_requirement: HardwareRequirement,
    /// Extension identities that must also resolve for this one to be used.
    pub requires: Vec<String>,
    /// Extension identities that must not resolve alongside this one.
    pub conflicts_with: Vec<String>,
    /// Whether a passing conformance record is claimed.
    pub promotion: Promotion,
}

deserialize_object!(RegistryEntry {
    schema_version: u32,
    extension_id: String,
    version: String,
    license: String,
    category: Category,
    authority_basis: Authority,
    host_contract_version: u32,
    problem_classes: Vec<ProblemClass>,
    deterministic: bool,
    limits: DeclaredLimits,
    data_requirement: DataRequirement,
    hardware_requirement: HardwareRequirement,
    requires: Vec<String>,
    conflicts_with: Vec<String>,
    promotion: Promotion,
});

impl RegistryEntry {
    /// Validate one entry's own shape, keeping each failure categorized.
    ///
    /// Provider availability, declaration agreement and promotion checking are
    /// deliberately not done here: those are resolution decisions that need the
    /// extension itself and the caller's context.
    ///
    /// # Errors
    ///
    /// Returns a categorized [`ValidationError`] for an unsupported version, a
    /// malformed identifier, version or license, an empty or duplicated
    /// problem-class list, a zero budget, an authority that does not derive from
    /// the category, a self-reference, a malformed conformance checksum, or an
    /// identity appearing in both `requires` and `conflicts_with`.
    pub fn validate(&self) -> Result<Self, ValidationError> {
        let structural = |message: String| ValidationError::new(ErrorKind::Structural, message);

        if self.schema_version != REGISTRY_SCHEMA_VERSION {
            return Err(ValidationError::new(
                ErrorKind::Document,
                format!(
                    "unsupported registry schema_version {}",
                    self.schema_version
                ),
            ));
        }
        for (name, text, limit) in [
            ("extension_id", &self.extension_id, MAX_EXTENSION_ID_BYTES),
            ("version", &self.version, MAX_EXTENSION_ID_BYTES),
            ("license", &self.license, MAX_LICENSE_BYTES),
        ] {
            if text.is_empty() || text.len() > limit {
                return Err(structural(format!("{name} must be 1..={limit} bytes")));
            }
            // These reach records, listings and diagnostics; keep them printable
            // and free of the control characters a log reader cannot see.
            if text.chars().any(char::is_control) {
                return Err(structural(format!(
                    "{name} must not contain control characters"
                )));
            }
        }
        if self.problem_classes.is_empty() {
            return Err(structural("problem_classes must not be empty".to_owned()));
        }
        let mut sorted = self.problem_classes.clone();
        sorted.sort_unstable();
        let unique = sorted.len();
        sorted.dedup();
        if sorted.len() != unique {
            return Err(structural(
                "problem_classes must not repeat a class".to_owned(),
            ));
        }

        // Requirement 7: authority is derived from the category, never selected.
        // A category with no authority cannot be registered at all, which is how
        // SPEC-0004 refuses the transformation category.
        match self.category.authority() {
            Some(authority) if authority == self.authority_basis => {}
            Some(expected) => {
                return Err(ValidationError::new(
                    ErrorKind::Unsupported,
                    format!(
                        "category {} implies authority {}, not {}",
                        self.category.as_str(),
                        describe_authority(expected),
                        describe_authority(self.authority_basis)
                    ),
                ));
            }
            None => {
                return Err(ValidationError::new(
                    ErrorKind::Unsupported,
                    format!(
                        "category {} is not admitted in a proving search",
                        self.category.as_str()
                    ),
                ));
            }
        }

        for (name, identities) in [
            ("requires", &self.requires),
            ("conflicts_with", &self.conflicts_with),
        ] {
            for identity in identities {
                if identity.is_empty() || identity.len() > MAX_EXTENSION_ID_BYTES {
                    return Err(structural(format!(
                        "{name} identities must be 1..={MAX_EXTENSION_ID_BYTES} bytes"
                    )));
                }
                if *identity == self.extension_id {
                    return Err(structural(format!(
                        "{name} must not name this entry's own identity"
                    )));
                }
            }
            let mut sorted: Vec<&str> = identities.iter().map(String::as_str).collect();
            sorted.sort_unstable();
            let unique = sorted.len();
            sorted.dedup();
            if sorted.len() != unique {
                return Err(structural(format!("{name} must not repeat an identity")));
            }
        }
        // An identity both required and conflicting can never resolve, so the
        // entry is unsatisfiable by construction rather than merely unlucky.
        if let Some(identity) = self
            .requires
            .iter()
            .find(|identity| self.conflicts_with.contains(identity))
        {
            return Err(structural(format!(
                "{identity} appears in both requires and conflicts_with"
            )));
        }

        if let Promotion::Promoted {
            conformance_path,
            conformance_sha256,
        } = &self.promotion
        {
            if conformance_path.is_empty() {
                return Err(structural("conformance_path must not be empty".to_owned()));
            }
            if !is_hex(conformance_sha256, 64) {
                return Err(structural(
                    "conformance_sha256 must be 64 lowercase hexadecimal digits".to_owned(),
                ));
            }
        }

        Ok(Self {
            problem_classes: sorted,
            limits: self.limits.validate()?,
            ..self.clone()
        })
    }
}

/// Stable diagnostic name for an authority.
fn describe_authority(authority: Authority) -> &'static str {
    match authority {
        Authority::ProposeValidatedCandidate => "propose_validated_candidate",
        Authority::ProposeCheckedAction => "propose_checked_action",
    }
}

/// Whether `value` is exactly `length` lowercase hexadecimal digits.
pub(crate) fn is_hex(value: &str, length: usize) -> bool {
    value.len() == length
        && value
            .bytes()
            .all(|byte| byte.is_ascii_digit() || (b'a'..=b'f').contains(&byte))
}

/// Every extension a caller has recorded as available to resolve.
#[derive(Clone, Debug, PartialEq, Eq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct RegistryDocument {
    /// Must equal [`REGISTRY_SCHEMA_VERSION`].
    pub schema_version: u32,
    /// Identifier for this registry, recorded in diagnostics.
    pub registry_id: String,
    /// The recorded entries, in the document's own order.
    ///
    /// Order is not observable in a record: resolution orders by identity and
    /// the SPEC-0004 host sorts by identity again.
    pub entries: Vec<RegistryEntry>,
}

deserialize_object!(RegistryDocument {
    schema_version: u32,
    registry_id: String,
    entries: Vec<RegistryEntry>,
});

impl RegistryDocument {
    /// Validate the document and every entry it carries.
    ///
    /// # Errors
    ///
    /// Returns a categorized [`ValidationError`] for an unsupported version, an
    /// empty identifier, an invalid entry, or a repeated extension identity.
    pub fn validate(&self) -> Result<Self, ValidationError> {
        if self.schema_version != REGISTRY_SCHEMA_VERSION {
            return Err(ValidationError::new(
                ErrorKind::Document,
                format!(
                    "unsupported registry schema_version {}",
                    self.schema_version
                ),
            ));
        }
        if self.registry_id.is_empty() {
            return Err(ValidationError::new(
                ErrorKind::Structural,
                "registry_id must not be empty",
            ));
        }
        let entries: Vec<RegistryEntry> = self
            .entries
            .iter()
            .map(RegistryEntry::validate)
            .collect::<Result<_, _>>()?;

        // Requirement 4: a repeated identity would make the entry governing a
        // resolution ambiguous, which is the rule SPEC-0004 already applies to a
        // policy list.
        let mut identities: Vec<&str> = entries
            .iter()
            .map(|entry| entry.extension_id.as_str())
            .collect();
        identities.sort_unstable();
        let total = identities.len();
        identities.dedup();
        if identities.len() != total {
            return Err(ValidationError::new(
                ErrorKind::Structural,
                "registry must not repeat an extension_id",
            ));
        }

        Ok(Self {
            entries,
            ..self.clone()
        })
    }

    /// The entry naming `extension_id`, if this registry records one.
    pub fn entry(&self, extension_id: &str) -> Option<&RegistryEntry> {
        self.entries
            .iter()
            .find(|entry| entry.extension_id == extension_id)
    }

    /// Serialize this registry.
    ///
    /// # Errors
    ///
    /// Returns a document failure when serialization fails.
    pub fn to_json(&self) -> Result<String, ValidationError> {
        serde_json::to_string_pretty(self)
            .map_err(|error| ValidationError::new(ErrorKind::Document, error.to_string()))
    }

    /// Parse one complete versioned registry document.
    ///
    /// Nested entry versions are checked here rather than deferred, so this
    /// parser cannot be laxer than the JSON Schema about a document it accepts.
    ///
    /// # Errors
    ///
    /// Returns a document failure for malformed JSON, an unknown or duplicate
    /// field, a positional array in place of an object, or an unsupported
    /// version at this or any nested level, and a categorized failure for any
    /// invalid entry.
    pub fn from_json(bytes: &[u8]) -> Result<Self, ValidationError> {
        let document: Self = serde_json::from_slice(bytes)
            .map_err(|error| ValidationError::new(ErrorKind::Document, error.to_string()))?;
        if document.schema_version != REGISTRY_SCHEMA_VERSION {
            return Err(ValidationError::new(
                ErrorKind::Document,
                format!(
                    "unsupported registry schema_version {}",
                    document.schema_version
                ),
            ));
        }
        for entry in &document.entries {
            nested_version("entries", entry.schema_version, REGISTRY_SCHEMA_VERSION)?;
        }
        // `host_contract_version` is deliberately not pinned here. It is a claim
        // about the extension, and a registry may legitimately list one built for
        // a different host. Refusing it at parse time would make an
        // incompatibility a *document* error and would conflate "this file is
        // malformed" with "this extension is for another host". Resolution
        // refuses it as unsupported instead, in both directions, which is
        // SPEC-0004 requirement 2's rule.
        document.validate()
    }
}
