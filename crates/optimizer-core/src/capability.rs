//! Backend capability declarations under SPEC-0011.
//!
//! With one backend, "what can this solve" was answered by the single
//! implementation. With two, a caller selecting the wrong one must be refused
//! rather than handed a silently wrong answer, so a backend states what it
//! accepts before it is ever called.
//!
//! A declaration carries no mathematical authority. It says what a backend will
//! attempt, never that an attempt succeeded, and a request outside it terminates
//! as [`Termination::Unsupported`] rather than being tried.

use serde::{Deserialize, Serialize};

use crate::{Domain, ErrorKind, Model, SolveOptions, SolveRecord, Termination, ValidationError};

/// Current capability declaration wire version.
///
/// Versioned on its own so a later capability can be added without redefining
/// the existing ones, which is what SPEC-0011's Compatibility section requires.
pub const CAPABILITY_SCHEMA_VERSION: u32 = 1;

/// A model class a backend or an extension states it supports.
///
/// The core checks a declaration against the model's actual domains, so neither
/// a backend nor an extension can be invoked on a class it did not claim.
///
/// This lives beside the solve contract because both consumers need it and
/// [`Backend`](crate::Backend) is defined here. `optimizer-extension` re-exports
/// it, so it remains one type with one wire form rather than two that are meant
/// to agree — the drift SPEC-0008 requirement 8 exists to prevent, which would
/// otherwise let a registry entry and a backend claim `continuous` as two
/// unrelated facts.
#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum ProblemClass {
    /// Every variable is continuous.
    Continuous,
    /// At least one variable is integer or binary.
    Discrete,
}

impl<'de> Deserialize<'de> for ProblemClass {
    fn deserialize<D: serde::Deserializer<'de>>(deserializer: D) -> Result<Self, D::Error> {
        const NAMES: &[&str] = &["continuous", "discrete"];
        match String::deserialize(deserializer)?.as_str() {
            "continuous" => Ok(Self::Continuous),
            "discrete" => Ok(Self::Discrete),
            other => Err(serde::de::Error::unknown_variant(other, NAMES)),
        }
    }
}

impl ProblemClass {
    /// The class of an original model, decided by its variable domains.
    pub fn of(model: &Model) -> Self {
        let discrete = model
            .document()
            .variables
            .iter()
            .any(|variable| variable.domain != Domain::Continuous);
        if discrete {
            Self::Discrete
        } else {
            Self::Continuous
        }
    }
}

/// The arithmetic width a backend iterates in.
///
/// SPEC-0011 requirement 5 admits only `f64`: its certification depends on
/// residuals whose magnitudes are comparable to the caller's tolerances, and a
/// reduced-precision iterate would not have them. The enum exists so that a
/// later width is a declared fact rather than an undocumented change.
#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize)]
#[serde(rename_all = "snake_case")]
#[non_exhaustive]
pub enum Arithmetic {
    /// IEEE-754 binary64 throughout.
    F64,
    /// Explicit binary32/binary64 execution; details in lp-precision-v1.
    MixedF32F64,
}

/// Whether a backend executes on a device.
///
/// This is a declaration, not a selection: SPEC-0010 requirement 5 keeps device
/// selection a caller's explicit configuration, and nothing here promotes a run
/// to a device.
#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize)]
#[serde(rename_all = "snake_case")]
#[non_exhaustive]
pub enum DeviceClass {
    /// Executes entirely on the host.
    Cpu,
    /// Executes kernels on a device SPEC-0010 selected and leased.
    Gpu,
}

/// What a backend states it supports, independently of any request.
///
/// Every field is private and there is no setter, no `&mut` accessor and no
/// public constructor other than [`BackendCapabilities::declare`], which
/// validates. That is SPEC-0011 requirement 4 expressed in the type rather than
/// only in prose: a caller cannot widen a declaration it obtained.
///
/// The type is one of three mechanisms enforcing that requirement, and it is the
/// weakest of them on its own. [`Backend::capabilities`](crate::Backend) takes no
/// argument, so there is no request-shaped input to influence it with; and a
/// backend consults its own declaration inside `solve`, so a caller holding a
/// widened copy is still refused. Requirement 4 is about authority rather than
/// about local mutability, and the last mechanism is the one that establishes it.
///
/// ```compile_fail,E0616
/// # use optimizer_core::{Backend, ProblemClass};
/// fn widen(backend: &dyn Backend) {
///     let mut declared = backend.capabilities();
///     // error[E0616]: field `problem_classes` of struct
///     // `BackendCapabilities` is private
///     declared.problem_classes.push(ProblemClass::Discrete);
/// }
/// ```
///
/// The `E0616` above records which error is expected but does not enforce it:
/// stable rustdoc accepts any compilation failure for a `compile_fail` block,
/// as a wrong code was checked and shown to pass. On its own the block would
/// therefore also pass if the field were merely renamed, so
/// `the_declared_classes_are_readable_under_the_name_the_widening_test_uses`
/// pairs with it and reads that same field through its accessor. A rename
/// breaks the pair.
#[derive(Clone, Debug, PartialEq, Eq, Serialize)]
#[serde(deny_unknown_fields)]
#[non_exhaustive]
pub struct BackendCapabilities {
    /// Legacy FP64 uses [`CAPABILITY_SCHEMA_VERSION`]; explicit mixed arithmetic uses 2.
    schema_version: u32,
    name: &'static str,
    version: String,
    problem_classes: Vec<ProblemClass>,
    arithmetic: Arithmetic,
    warm_start: bool,
    device: DeviceClass,
}

impl BackendCapabilities {
    /// State what a backend accepts.
    ///
    /// `version` is owned rather than `&'static str` because a backend's version
    /// is not always known at compile time: the pinned adapter reports the
    /// version it actually linked, and reports an unavailable version when
    /// nothing was linked. A `&'static str` would force it to name a version it
    /// may never have called.
    ///
    /// # Errors
    ///
    /// Returns a document failure for an empty name or version, or for an empty
    /// or duplicated class list. A declaration accepting nothing is refused
    /// rather than accepted and then refusing every request, because the second
    /// shape would report a configuration error as a solve outcome.
    pub fn declare(
        name: &'static str,
        version: String,
        problem_classes: Vec<ProblemClass>,
        arithmetic: Arithmetic,
        warm_start: bool,
        device: DeviceClass,
    ) -> Result<Self, ValidationError> {
        if name.is_empty() {
            return Err(ValidationError::new(
                ErrorKind::Document,
                "backend capability name must not be empty",
            ));
        }
        if version.is_empty() {
            return Err(ValidationError::new(
                ErrorKind::Document,
                "backend capability version must not be empty",
            ));
        }
        if problem_classes.is_empty() {
            return Err(ValidationError::new(
                ErrorKind::Document,
                "a backend must declare at least one problem class",
            ));
        }
        let mut problem_classes = problem_classes;
        problem_classes.sort_unstable();
        let count = problem_classes.len();
        problem_classes.dedup();
        if problem_classes.len() != count {
            return Err(ValidationError::new(
                ErrorKind::Document,
                "duplicate problem class in a backend declaration",
            ));
        }
        Ok(Self {
            schema_version: if arithmetic == Arithmetic::MixedF32F64 {
                2
            } else {
                CAPABILITY_SCHEMA_VERSION
            },
            name,
            version,
            problem_classes,
            arithmetic,
            warm_start,
            device,
        })
    }

    /// The declaration wire version.
    #[must_use]
    pub fn schema_version(&self) -> u32 {
        self.schema_version
    }

    /// The backend's stable name, as it appears in a solve record.
    #[must_use]
    pub fn name(&self) -> &'static str {
        self.name
    }

    /// The backend's version, as it appears in a solve record.
    #[must_use]
    pub fn version(&self) -> &str {
        &self.version
    }

    /// The model classes this backend accepts, sorted and deduplicated.
    #[must_use]
    pub fn problem_classes(&self) -> &[ProblemClass] {
        &self.problem_classes
    }

    /// The arithmetic width this backend iterates in.
    #[must_use]
    pub fn arithmetic(&self) -> Arithmetic {
        self.arithmetic
    }

    /// Whether this backend accepts a warm start.
    #[must_use]
    pub fn warm_start(&self) -> bool {
        self.warm_start
    }

    /// Whether this backend executes on a device.
    #[must_use]
    pub fn device(&self) -> DeviceClass {
        self.device
    }

    /// Whether this backend accepts the class this model belongs to.
    #[must_use]
    pub fn accepts(&self, model: &Model) -> bool {
        self.problem_classes.contains(&ProblemClass::of(model))
    }

    /// The record a backend returns instead of attempting an out-of-class request.
    ///
    /// A record rather than an `Err`, because SPEC-0011's termination table maps
    /// this to [`Termination::Unsupported`], which is a solve outcome a caller
    /// can act on: the executive already forfeits its proof claim on it. An
    /// error would make a capability boundary indistinguishable from a failure
    /// to configure one.
    #[must_use]
    pub fn refuse(&self, model: &Model, options: &SolveOptions) -> SolveRecord {
        let class = ProblemClass::of(model);
        SolveRecord {
            lp_execution: None,
            lp_precision: None,
            schema_version: crate::SOLVE_RECORD_SCHEMA_VERSION,
            model_id: model.document().model_id.clone(),
            backend: self.name.to_string(),
            backend_version: self.version.clone(),
            termination: Termination::Unsupported,
            native_status: None,
            objective: None,
            best_bound: None,
            gap: None,
            candidate: None,
            validation: None,
            warnings: vec![format!(
                "{} does not accept a {} model; it declares {}",
                self.name,
                class_name(class),
                self.declared_classes(),
            )],
            elapsed_ms: 0,
            options: options.clone(),
            // A refusal is decided before any method runs, so there are no
            // settings to report.
            lp_settings: None,
        }
    }

    fn declared_classes(&self) -> String {
        self.problem_classes
            .iter()
            .map(|class| class_name(*class))
            .collect::<Vec<_>>()
            .join(", ")
    }
}

fn class_name(class: ProblemClass) -> &'static str {
    match class {
        ProblemClass::Continuous => "continuous",
        ProblemClass::Discrete => "discrete",
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn declaration(classes: Vec<ProblemClass>) -> Result<BackendCapabilities, ValidationError> {
        BackendCapabilities::declare(
            "test",
            "1.0".to_string(),
            classes,
            Arithmetic::F64,
            true,
            DeviceClass::Cpu,
        )
    }

    #[test]
    fn a_declaration_sorts_its_classes_so_two_orders_are_one_declaration() {
        let forward = declaration(vec![ProblemClass::Continuous, ProblemClass::Discrete]).unwrap();
        let reverse = declaration(vec![ProblemClass::Discrete, ProblemClass::Continuous]).unwrap();
        assert_eq!(forward, reverse);
    }

    #[test]
    fn a_declaration_accepting_nothing_is_refused() {
        let error = declaration(vec![]).unwrap_err();
        assert_eq!(error.kind, ErrorKind::Document);
    }

    #[test]
    fn a_duplicated_class_is_refused_rather_than_silently_collapsed() {
        let error =
            declaration(vec![ProblemClass::Continuous, ProblemClass::Continuous]).unwrap_err();
        assert_eq!(error.kind, ErrorKind::Document);
    }

    /// The positive half of the widening evidence.
    ///
    /// The `compile_fail` doctest on [`BackendCapabilities`] shows that
    /// `problem_classes` cannot be mutated from outside this module, but stable
    /// rustdoc accepts any compilation failure, so that block alone would keep
    /// passing if the field were renamed out from under it. This reads the same
    /// field through its accessor, so a rename cannot leave both green.
    #[test]
    fn the_declared_classes_are_readable_under_the_name_the_widening_test_uses() {
        let declared = declaration(vec![ProblemClass::Continuous]).unwrap();
        assert_eq!(declared.problem_classes(), [ProblemClass::Continuous]);
    }

    #[test]
    fn an_empty_name_or_version_is_refused() {
        assert!(
            BackendCapabilities::declare(
                "",
                "1.0".to_string(),
                vec![ProblemClass::Continuous],
                Arithmetic::F64,
                false,
                DeviceClass::Cpu,
            )
            .is_err()
        );
        assert!(
            BackendCapabilities::declare(
                "test",
                String::new(),
                vec![ProblemClass::Continuous],
                Arithmetic::F64,
                false,
                DeviceClass::Cpu,
            )
            .is_err()
        );
    }
}
