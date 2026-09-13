//! Registry contracts mapped to SPEC-0009 requirement numbers.
//!
//! The load-bearing cases are the refusals. A registry that could not reject a
//! wrong claim would be a list of names, and its entries' license, authority,
//! determinism and promotion fields would be decorative.
//!
//! The refusals decided *before* construction assert the provider's own
//! construction counter afterwards, which is requirement 14 and is also what keeps
//! those tests from passing vacuously: C3 recorded that three of its acceptance
//! tests were testing an extension that was never consulted. The
//! declaration-mismatch paths cannot assert it, because resolution has to build
//! the extension and call `declare` in order to find the disagreement; that
//! narrowing of requirement 14 is recorded in state/known-failures.md rather than
//! asserted away here.

use std::sync::atomic::{AtomicUsize, Ordering};

use optimizer_core::{
    Assignment, Bound, Candidate, Constraint, Domain, ErrorKind, LinearTerm, Model, ModelDocument,
    Objective, ObjectiveSense, SCHEMA_VERSION, Variable,
};
use optimizer_extension::{
    Advice, Authority, CandidateProducer, Category, DeclaredLimits, EXTENSION_SCHEMA_VERSION,
    Extension, ExtensionDeclaration, ExtensionPolicy, ProblemClass, SearchAdviser, SearchSnapshot,
};
use optimizer_registry::{
    ConformanceRecord, ConformanceSource, DataRequirement, HardwareRequirement, Options, Promotion,
    Provided, Provider, ProviderContext, REGISTRY_SCHEMA_VERSION, RegistryDocument, RegistryEntry,
    resolve, resolve_with,
};

/// Identity every honest fixture in this file uses.
const HONEST: &str = "honest-producer";

/// How a [`TestProvider`] constructs an extension from an identity.
type Build = Box<dyn Fn(&str) -> Option<Provided>>;

/// A named mutation of an entry, paired with the category it must be refused in.
type EntryCase = (&'static str, Box<dyn Fn(&mut RegistryEntry)>, ErrorKind);

/// A named mutation of a declaration, for the per-field mismatch checks.
type DeclarationCase = (&'static str, Box<dyn Fn(&mut ExtensionDeclaration)>);

// The construction counter lives in each provider rather than in a static.
// Tests run in parallel in one process, so a shared static would let one test's
// constructions be counted by another's assertion; that is exactly how a
// requirement-14 check would become both flaky and meaningless.

/// A minimal honest producer proposing each variable at its lower bound.
///
/// It carries no invocation counter. Resolution never runs a search, so an
/// invocation count here would be zero in every test whether or not the rule it
/// claims to check held, and instrumentation that cannot fail reads as evidence
/// without being any. Requirement 14 is asserted against the provider's own
/// construction counter instead, which resolution does reach.
#[derive(Debug)]
struct HonestProducer;

impl Extension for HonestProducer {
    fn declare(&self) -> ExtensionDeclaration {
        ExtensionDeclaration {
            schema_version: EXTENSION_SCHEMA_VERSION,
            extension_id: HONEST.to_owned(),
            version: "1.2.3".to_owned(),
            host_contract_version: EXTENSION_SCHEMA_VERSION,
            category: Category::CandidateProducer,
            problem_classes: vec![ProblemClass::Discrete],
            deterministic: true,
            limits: DeclaredLimits {
                max_invocations: 64,
                max_proposals: 64,
            },
        }
    }
}

impl CandidateProducer for HonestProducer {
    fn propose(&self, snapshot: &SearchSnapshot<'_>) -> Vec<Candidate> {
        let document = snapshot.model.document();
        let values = document
            .variables
            .iter()
            .map(|variable| Assignment {
                variable_id: variable.id,
                value: match variable.lower {
                    Bound::Finite { value } => value,
                    _ => 0.0,
                },
            })
            .collect();
        vec![Candidate {
            schema_version: SCHEMA_VERSION,
            model_id: document.model_id.clone(),
            values,
        }]
    }
}

/// An adviser used only to check role and category disagreement.
#[derive(Debug, Default)]
struct HonestAdviser;

impl Extension for HonestAdviser {
    fn declare(&self) -> ExtensionDeclaration {
        ExtensionDeclaration {
            schema_version: EXTENSION_SCHEMA_VERSION,
            extension_id: "honest-adviser".to_owned(),
            version: "1.0.0".to_owned(),
            host_contract_version: EXTENSION_SCHEMA_VERSION,
            category: Category::SearchAdviser,
            problem_classes: vec![ProblemClass::Discrete],
            deterministic: true,
            limits: DeclaredLimits {
                max_invocations: 64,
                max_proposals: 64,
            },
        }
    }
}

impl SearchAdviser for HonestAdviser {
    fn advise(&self, _snapshot: &SearchSnapshot<'_>) -> Advice {
        Advice::Abstain
    }
}

/// An adviser declaring the honest *producer*'s declaration verbatim.
///
/// This isolates the role check. A provider handing back the wrong role while
/// declaring something else would be refused on the identity or the category
/// first, so the role check would never be reached and a test aimed at it would
/// pass for the wrong reason.
#[derive(Debug, Default)]
struct RoleMismatch;

impl Extension for RoleMismatch {
    fn declare(&self) -> ExtensionDeclaration {
        HonestProducer.declare()
    }
}

impl SearchAdviser for RoleMismatch {
    fn advise(&self, _snapshot: &SearchSnapshot<'_>) -> Advice {
        Advice::Abstain
    }
}

/// A producer whose declaration is overridden, for the mismatch paths.
#[derive(Debug)]
struct Misdeclaring(ExtensionDeclaration);

impl Extension for Misdeclaring {
    fn declare(&self) -> ExtensionDeclaration {
        self.0.clone()
    }
}

impl CandidateProducer for Misdeclaring {
    fn propose(&self, _snapshot: &SearchSnapshot<'_>) -> Vec<Candidate> {
        Vec::new()
    }
}

/// A provider supplying whatever a test asks it to supply.
struct TestProvider {
    /// What to construct, or nothing to report the identity unprovided.
    build: Build,
    /// Construction attempts observed by this provider alone.
    constructions: AtomicUsize,
}

impl TestProvider {
    /// A provider from one construction function.
    fn new(build: impl Fn(&str) -> Option<Provided> + 'static) -> Self {
        Self {
            build: Box::new(build),
            constructions: AtomicUsize::new(0),
        }
    }

    /// A provider supplying the honest producer under its own identity.
    fn honest() -> Self {
        Self::new(|id| (id == HONEST).then(|| Provided::Producer(Box::new(HonestProducer))))
    }

    /// A provider that supplies nothing at all.
    fn empty() -> Self {
        Self::new(|_| None)
    }

    /// A provider supplying a producer with an overridden declaration.
    fn misdeclaring(declaration: ExtensionDeclaration) -> Self {
        Self::new(move |_| {
            Some(Provided::Producer(Box::new(Misdeclaring(
                declaration.clone(),
            ))))
        })
    }

    /// A provider supplying both fixtures, each under its declared identity.
    fn both() -> Self {
        Self::new(|id| {
            Some(if id == HONEST {
                Provided::Producer(Box::new(HonestProducer))
            } else {
                Provided::Adviser(Box::new(HonestAdviser))
            })
        })
    }

    /// Construction attempts this provider observed.
    fn constructions(&self) -> usize {
        self.constructions.load(Ordering::SeqCst)
    }
}

impl Provider for TestProvider {
    fn provide(&self, extension_id: &str, _context: &ProviderContext<'_>) -> Option<Provided> {
        self.constructions.fetch_add(1, Ordering::SeqCst);
        (self.build)(extension_id)
    }
}

/// A conformance source returning fixed bytes for any path.
struct FixedConformance(Option<Vec<u8>>);

impl ConformanceSource for FixedConformance {
    fn read(&self, _path: &str) -> Option<Vec<u8>> {
        self.0.clone()
    }
}

/// A tiny discrete model for resolution tests.
fn model() -> Model {
    Model::new(ModelDocument {
        schema_version: SCHEMA_VERSION,
        model_id: "registry-fixture".to_owned(),
        variables: vec![Variable {
            id: 0,
            domain: Domain::Binary,
            lower: Bound::Finite { value: 0.0 },
            upper: Bound::Finite { value: 1.0 },
        }],
        constraints: vec![Constraint {
            id: 0,
            lower: Bound::NegativeInfinity,
            upper: Bound::Finite { value: 1.0 },
            terms: vec![LinearTerm {
                variable_id: 0,
                coefficient: 1.0,
            }],
        }],
        objective: Objective {
            sense: ObjectiveSense::Maximize,
            offset: 0.0,
            terms: vec![LinearTerm {
                variable_id: 0,
                coefficient: 1.0,
            }],
        },
    })
    .expect("fixture model is valid")
}

/// An entry matching [`HonestProducer`]'s declaration exactly.
fn entry() -> RegistryEntry {
    RegistryEntry {
        schema_version: REGISTRY_SCHEMA_VERSION,
        extension_id: HONEST.to_owned(),
        version: "1.2.3".to_owned(),
        license: "MIT".to_owned(),
        category: Category::CandidateProducer,
        authority_basis: Authority::ProposeValidatedCandidate,
        host_contract_version: EXTENSION_SCHEMA_VERSION,
        problem_classes: vec![ProblemClass::Discrete],
        deterministic: true,
        limits: DeclaredLimits {
            max_invocations: 64,
            max_proposals: 64,
        },
        data_requirement: DataRequirement::None,
        hardware_requirement: HardwareRequirement::Cpu,
        requires: Vec::new(),
        conflicts_with: Vec::new(),
        promotion: Promotion::Experimental,
    }
}

/// A policy naming one identity with generous budgets.
fn policy(extension_id: &str) -> ExtensionPolicy {
    ExtensionPolicy {
        schema_version: EXTENSION_SCHEMA_VERSION,
        extension_id: extension_id.to_owned(),
        invocation_budget: 8,
        proposal_budget: 8,
    }
}

/// Resolve one entry, permitting experimental registration.
fn resolve_one(
    entry: &RegistryEntry,
    provider: &dyn Provider,
) -> Result<optimizer_registry::ResolvedSet, optimizer_core::ValidationError> {
    resolve_one_on(entry, provider, None)
}

/// Resolve one entry, optionally on a device this run is holding.
fn resolve_one_on(
    entry: &RegistryEntry,
    provider: &dyn Provider,
    device: Option<&str>,
) -> Result<optimizer_registry::ResolvedSet, optimizer_core::ValidationError> {
    let model = model();
    let context = match device {
        None => ProviderContext::new(&model),
        Some(uuid) => ProviderContext::new(&model).on_device(uuid),
    };
    resolve_with(
        std::slice::from_ref(entry),
        &[policy(&entry.extension_id)],
        provider,
        &context,
        &optimizer_registry::NoConformance,
        Options {
            allow_experimental: true,
            ..Options::default()
        },
    )
}

// Requirements 1-3: a valid document round-trips through both directions.
#[test]
fn a_registry_document_round_trips() {
    let document = RegistryDocument {
        schema_version: REGISTRY_SCHEMA_VERSION,
        registry_id: "round-trip".to_owned(),
        entries: vec![entry()],
    };
    let json = document.to_json().expect("serialize");
    let parsed = RegistryDocument::from_json(json.as_bytes()).expect("parse");
    assert_eq!(parsed, document);
    assert!(parsed.entry(HONEST).is_some());
    assert!(parsed.entry("absent").is_none());
}

// Requirement 3: unknown fields, positional arrays, unknown variants and wrong
// versions at either level are all refused at parse time.
#[test]
fn malformed_registry_documents_are_refused() {
    let base = RegistryDocument {
        schema_version: REGISTRY_SCHEMA_VERSION,
        registry_id: "strict".to_owned(),
        entries: vec![entry()],
    }
    .to_json()
    .expect("serialize");

    let cases = [
        // An unknown field at the document level.
        base.replace(
            r#""registry_id": "strict""#,
            r#""registry_id": "strict", "unknown": 1"#,
        ),
        // An unknown field inside an entry.
        base.replace(r#""license": "MIT""#, r#""license": "MIT", "extra": true"#),
        // A positional array where the document belongs.
        "[1, \"strict\", []]".to_owned(),
        // An unknown enum variant.
        base.replace(
            r#""hardware_requirement": "cpu""#,
            r#""hardware_requirement": "tpu""#,
        ),
        // A wrong version at the document level.
        base.replace(
            r#""schema_version": 1,
  "registry_id""#,
            r#""schema_version": 2,
  "registry_id""#,
        ),
    ];
    for (index, case) in cases.iter().enumerate() {
        let error = RegistryDocument::from_json(case.as_bytes())
            .expect_err(&format!("case {index} must be refused"));
        assert_eq!(error.kind, ErrorKind::Document, "case {index}: {error}");
    }
}

// Requirement 3: a wrong nested entry version is refused, and by the nested check
// rather than incidentally by the document's own.
#[test]
fn a_wrong_nested_entry_version_is_refused() {
    let mut document = RegistryDocument {
        schema_version: REGISTRY_SCHEMA_VERSION,
        registry_id: "nested".to_owned(),
        entries: vec![entry()],
    };
    document.entries[0].schema_version = 2;
    let json = document.to_json().expect("serialize");
    let error = RegistryDocument::from_json(json.as_bytes()).expect_err("must be refused");
    assert_eq!(error.kind, ErrorKind::Document);
    assert!(
        error.to_string().contains("entries"),
        "the nested field must be named: {error}"
    );
}

// Requirement 4: a repeated identity makes the governing entry ambiguous.
#[test]
fn a_repeated_extension_identity_is_refused() {
    let document = RegistryDocument {
        schema_version: REGISTRY_SCHEMA_VERSION,
        registry_id: "duplicate".to_owned(),
        entries: vec![entry(), entry()],
    };
    let json = document.to_json().expect("serialize");
    let error = RegistryDocument::from_json(json.as_bytes()).expect_err("must be refused");
    assert_eq!(error.kind, ErrorKind::Structural);
    assert!(error.to_string().contains("repeat"), "found {error}");
}

// Requirement 7: authority is derived from the category, never chosen.
#[test]
fn an_authority_not_implied_by_the_category_is_refused() {
    let mut entry = entry();
    entry.authority_basis = Authority::ProposeCheckedAction;
    let error = entry.validate().expect_err("must be refused");
    assert_eq!(error.kind, ErrorKind::Unsupported);
    assert!(
        error.to_string().contains("implies authority"),
        "found {error}"
    );
}

// Requirement 7: the transformation category has no authority and no code path.
#[test]
fn the_transformation_category_is_refused() {
    let mut entry = entry();
    entry.category = Category::Transformation;
    let error = entry.validate().expect_err("must be refused");
    assert_eq!(error.kind, ErrorKind::Unsupported);
    assert!(error.to_string().contains("not admitted"), "found {error}");
}

// Requirement 2: an entry's own malformed fields are refused before anything is
// constructed from it.
#[test]
fn malformed_entry_fields_are_refused() {
    let cases: [EntryCase; 6] = [
        (
            "empty identity",
            Box::new(|entry| entry.extension_id = String::new()),
            ErrorKind::Structural,
        ),
        (
            "control character in license",
            Box::new(|entry| entry.license = "MIT\n".to_owned()),
            ErrorKind::Structural,
        ),
        (
            "empty problem classes",
            Box::new(|entry| entry.problem_classes = Vec::new()),
            ErrorKind::Structural,
        ),
        (
            "repeated problem class",
            Box::new(|entry| {
                entry.problem_classes = vec![ProblemClass::Discrete, ProblemClass::Discrete];
            }),
            ErrorKind::Structural,
        ),
        (
            "zero budget",
            Box::new(|entry| {
                entry.limits = DeclaredLimits {
                    max_invocations: 0,
                    max_proposals: 1,
                };
            }),
            ErrorKind::Unsupported,
        ),
        (
            "self reference",
            Box::new(|entry| entry.requires = vec![HONEST.to_owned()]),
            ErrorKind::Structural,
        ),
    ];
    for (name, mutate, kind) in cases {
        let mut entry = entry();
        mutate(&mut entry);
        let error = entry
            .validate()
            .expect_err(&format!("{name} must be refused"));
        assert_eq!(error.kind, kind, "{name}: {error}");
    }
}

// Requirement 5: an entry the provider does not supply is refused, not skipped.
#[test]
fn an_unprovided_extension_is_refused() {
    let provider = TestProvider::empty();
    let error = resolve_one(&entry(), &provider).expect_err("must be refused");
    assert_eq!(error.kind, ErrorKind::Unsupported);
    assert!(error.to_string().contains("not provided"), "found {error}");
}

// Requirement 5: a policy naming an entry the registry does not record is refused
// too, so the registry cannot be bypassed by naming something absent from it.
#[test]
fn a_policy_naming_an_unrecorded_entry_is_refused() {
    let model = model();
    let provider = TestProvider::honest();
    let error = resolve(
        &[entry()],
        &[policy("not-in-registry")],
        &provider,
        &ProviderContext::new(&model),
    )
    .expect_err("must be refused");
    assert_eq!(error.kind, ErrorKind::Unsupported);
    assert!(
        error.to_string().contains("absent from the registry"),
        "found {error}"
    );
}

// Requirement 6: every recorded claim is checked against the declaration, each
// mismatch individually, so no field is nominally recorded and actually ignored.
#[test]
fn each_declaration_mismatch_is_refused_individually() {
    let honest = HonestProducer.declare();
    let mutations: [DeclarationCase; 6] = [
        (
            "version",
            Box::new(|declaration| declaration.version = "9.9.9".to_owned()),
        ),
        (
            "category",
            Box::new(|declaration| declaration.category = Category::SearchAdviser),
        ),
        (
            "host_contract_version",
            Box::new(|declaration| declaration.host_contract_version = 2),
        ),
        (
            "deterministic",
            Box::new(|declaration| declaration.deterministic = false),
        ),
        (
            "limits",
            Box::new(|declaration| {
                declaration.limits = DeclaredLimits {
                    max_invocations: 1,
                    max_proposals: 1,
                };
            }),
        ),
        (
            "problem_classes",
            Box::new(|declaration| declaration.problem_classes = vec![ProblemClass::Continuous]),
        ),
    ];

    for (field, mutate) in mutations {
        let mut declaration = honest.clone();
        mutate(&mut declaration);
        let provider = TestProvider::misdeclaring(declaration);
        let error = resolve_one(&entry(), &provider)
            .expect_err(&format!("a mismatched {field} must be refused"));
        assert_eq!(error.kind, ErrorKind::Unsupported, "{field}: {error}");
        assert!(
            error.to_string().contains(field),
            "{field}: the diverging field must be named, found {error}"
        );
    }
}

// Requirement 6: a provider returning the wrong role is refused rather than
// reinterpreted, because guessing would grant unintended authority.
#[test]
fn a_provider_returning_the_wrong_role_is_refused() {
    // The declaration matches the entry in every field, so the only thing wrong
    // is the role it was constructed in. Without that the refusal below would
    // come from the identity or category check instead.
    let provider = TestProvider::new(|_| Some(Provided::Adviser(Box::new(RoleMismatch))));
    let error = resolve_one(&entry(), &provider).expect_err("must be refused");
    assert_eq!(error.kind, ErrorKind::Unsupported);
    assert!(
        error.to_string().contains("was constructed as"),
        "the role disagreement must be named: {error}"
    );
}

// Requirement 8: an unsatisfied data requirement is refused before construction.
#[test]
fn an_unsatisfied_data_requirement_is_refused_before_construction() {
    let mut entry = entry();
    entry.data_requirement = DataRequirement::FlowShopInstance;
    let provider = TestProvider::honest();

    let error = resolve_one(&entry, &provider).expect_err("must be refused");
    assert_eq!(error.kind, ErrorKind::Unsupported);
    assert!(
        error.to_string().contains("flow_shop_instance"),
        "found {error}"
    );
    // Requirement 14: the refusal happened before anything was built.
    assert_eq!(
        provider.constructions(),
        0,
        "a refused entry must not be constructed"
    );
}

// Requirement 8: the same entry resolves once the instance is supplied, so the
// refusal above is about the missing input rather than about the entry.
#[test]
fn a_satisfied_data_requirement_resolves() {
    let mut entry = entry();
    entry.data_requirement = DataRequirement::FlowShopInstance;
    let model = model();
    let provider = TestProvider::honest();
    let instance = b"{}";
    let resolved = resolve_with(
        std::slice::from_ref(&entry),
        &[policy(HONEST)],
        &provider,
        &ProviderContext::with_instance(&model, instance),
        &optimizer_registry::NoConformance,
        Options {
            allow_experimental: true,
            ..Options::default()
        },
    )
    .expect("must resolve");
    assert_eq!(resolved.identities(), vec![HONEST]);
}

// Requirement 9, as narrowed by SPEC-0010 requirement 35: a device requirement is
// refused when this run selected no device, and still before construction.
//
// The refusal was unconditional until a device path existed. It is now conditional,
// which is a narrowing rather than a removal: the entry still cannot be resolved by
// a run that has no device, and the decision is still made from the entry and the
// context with nothing built to make it, which is requirement 14a.
#[test]
fn a_gpu_hardware_requirement_is_refused_before_construction() {
    let mut entry = entry();
    entry.hardware_requirement = HardwareRequirement::Gpu;
    let provider = TestProvider::honest();

    let error = resolve_one(&entry, &provider).expect_err("must be refused");
    assert_eq!(error.kind, ErrorKind::Unsupported);
    assert!(
        error.to_string().contains("selected no device"),
        "found {error}"
    );
    assert_eq!(
        provider.constructions(),
        0,
        "a refused entry must not be constructed"
    );
}

// Requirement 35: the same entry resolves when the run holds a device.
//
// Without this the narrowing would be untested in the direction that changed: a
// refusal that never lifts is indistinguishable from the unconditional one it
// replaced.
#[test]
fn a_gpu_hardware_requirement_resolves_when_a_device_is_selected() {
    let mut entry = entry();
    entry.hardware_requirement = HardwareRequirement::Gpu;
    let provider = TestProvider::honest();

    let resolved = resolve_one_on(
        &entry,
        &provider,
        Some("GPU-dfb2449a-9eff-e868-3597-2c448c9a8e48"),
    )
    .expect("a gpu entry resolves on a device");
    assert_eq!(resolved.identities(), vec![HONEST]);
    assert_eq!(
        provider.constructions(),
        1,
        "resolving must construct exactly once"
    );

    // A cpu entry is unaffected by the presence of a device, so the new field
    // gates only what it was added to gate.
    let cpu = self::entry();
    let provider = TestProvider::honest();
    let resolved = resolve_one_on(
        &cpu,
        &provider,
        Some("GPU-dfb2449a-9eff-e868-3597-2c448c9a8e48"),
    )
    .expect("a cpu entry resolves on a device too");
    assert_eq!(resolved.identities(), vec![HONEST]);
}

// Requirement 10: an absent required identity is refused and named.
#[test]
fn an_unsatisfied_requirement_is_refused() {
    let mut entry = entry();
    entry.requires = vec!["absent-dependency".to_owned()];
    let provider = TestProvider::honest();
    let error = resolve_one(&entry, &provider).expect_err("must be refused");
    assert_eq!(error.kind, ErrorKind::Structural);
    assert!(
        error.to_string().contains("absent-dependency"),
        "the unsatisfied requirement must be named: {error}"
    );
}

// Requirement 10: two entries declaring a conflict cannot resolve together.
#[test]
fn a_declared_conflict_is_refused() {
    let mut first = entry();
    first.conflicts_with = vec!["honest-adviser".to_owned()];
    let mut second = entry();
    second.extension_id = "honest-adviser".to_owned();
    second.version = "1.0.0".to_owned();
    second.category = Category::SearchAdviser;
    second.authority_basis = Authority::ProposeCheckedAction;

    let model = model();
    let provider = TestProvider::both();
    let error = resolve_with(
        &[first, second],
        &[policy(HONEST), policy("honest-adviser")],
        &provider,
        &ProviderContext::new(&model),
        &optimizer_registry::NoConformance,
        Options {
            allow_experimental: true,
            ..Options::default()
        },
    )
    .expect_err("must be refused");
    assert_eq!(error.kind, ErrorKind::Structural);
    assert!(
        error.to_string().contains("conflicts with"),
        "found {error}"
    );
}

// Requirement 12: an experimental entry needs explicit permission, and the
// permitted case records a warning naming it.
#[test]
fn an_experimental_entry_needs_permission_and_warns() {
    let model = model();
    let provider = TestProvider::honest();

    let error = resolve(
        &[entry()],
        &[policy(HONEST)],
        &provider,
        &ProviderContext::new(&model),
    )
    .expect_err("must be refused without permission");
    assert_eq!(error.kind, ErrorKind::Unsupported);
    assert!(
        error.to_string().contains("--allow-experimental"),
        "found {error}"
    );

    let resolved = resolve_one(&entry(), &provider).expect("must resolve with permission");
    assert_eq!(resolved.warnings().len(), 1, "the record must be warned");
    assert!(
        resolved.warnings()[0].contains(HONEST),
        "the warning must name the extension: {:?}",
        resolved.warnings()
    );
}

// Requirement 13: resolution is all-or-nothing. One refused entry stops the whole
// set, so a search never begins with a subset of what it was configured with.
#[test]
fn one_refused_entry_refuses_the_whole_set() {
    let mut absent = entry();
    absent.extension_id = "zz-not-provided".to_owned();
    let model = model();
    // Only the honest identity is provided, so the second entry cannot resolve.
    let provider = TestProvider::honest();

    let error = resolve_with(
        &[entry(), absent],
        &[policy(HONEST), policy("zz-not-provided")],
        &provider,
        &ProviderContext::new(&model),
        &optimizer_registry::NoConformance,
        Options {
            allow_experimental: true,
            ..Options::default()
        },
    )
    .expect_err("the whole set must be refused");
    assert_eq!(error.kind, ErrorKind::Unsupported);
}

/// A passing conformance record for the honest producer.
fn passing_record() -> ConformanceRecord {
    ConformanceRecord {
        schema_version: optimizer_registry::CONFORMANCE_SCHEMA_VERSION,
        extension_id: HONEST.to_owned(),
        version: "1.2.3".to_owned(),
        host_contract_version: EXTENSION_SCHEMA_VERSION,
        grid_size: optimizer_registry::GRID_SIZE,
        backend_version: "test".to_owned(),
        checks: vec![optimizer_registry::ConformanceCheck {
            name: "conclusions_invariant".to_owned(),
            passed: true,
            detail: "unchanged".to_owned(),
        }],
        outcome: true,
    }
}

/// A promoted entry citing `bytes` by their true checksum.
fn promoted_entry(bytes: &[u8]) -> RegistryEntry {
    let mut entry = entry();
    entry.promotion = Promotion::Promoted {
        conformance_path: "artifacts/conformance.json".to_owned(),
        conformance_sha256: optimizer_experiment::sha256::hex(bytes),
    };
    entry
}

// Requirement 11: a promoted entry whose record verifies resolves without needing
// experimental permission, which is what promotion is for.
#[test]
fn a_verified_promotion_resolves_without_permission() {
    let json = passing_record().to_json().expect("serialize");
    let entry = promoted_entry(json.as_bytes());
    let model = model();
    let provider = TestProvider::honest();

    let resolved = resolve_with(
        std::slice::from_ref(&entry),
        &[policy(HONEST)],
        &provider,
        &ProviderContext::new(&model),
        &FixedConformance(Some(json.into_bytes())),
        Options::default(),
    )
    .expect("a verified promotion must resolve");
    assert_eq!(resolved.identities(), vec![HONEST]);
    assert!(
        resolved.warnings().is_empty(),
        "a promoted entry needs no warning: {:?}",
        resolved.warnings()
    );
}

// Requirement 11: every way a promotion claim can fail is refused separately.
#[test]
fn each_unverifiable_promotion_is_refused() {
    let json = passing_record().to_json().expect("serialize");
    let entry = promoted_entry(json.as_bytes());
    let model = model();
    let provider = TestProvider::honest();

    let mut failing = passing_record();
    failing.checks[0].passed = false;
    failing.outcome = false;

    let mut other_extension = passing_record();
    other_extension.extension_id = "someone-else".to_owned();

    let mut other_version = passing_record();
    other_version.version = "9.9.9".to_owned();

    let cases: [(&str, Option<Vec<u8>>, &str); 5] = [
        ("absent record", None, "could not be read"),
        (
            "tampered bytes",
            Some(json.replace("unchanged", "tampered!").into_bytes()),
            "checksum",
        ),
        (
            "failing outcome",
            Some(failing.to_json().expect("serialize").into_bytes()),
            "did not pass",
        ),
        (
            "another extension",
            Some(other_extension.to_json().expect("serialize").into_bytes()),
            "describes",
        ),
        (
            "another version",
            Some(other_version.to_json().expect("serialize").into_bytes()),
            "version",
        ),
    ];

    for (name, bytes, expected) in cases {
        // Each replacement record is re-checksummed against the entry's recorded
        // hash, so the tampered case fails on the checksum and the others fail on
        // their content; both are refusals and that is the point.
        let entry = if name == "tampered bytes" {
            entry.clone()
        } else {
            bytes
                .as_ref()
                .map_or_else(|| entry.clone(), |bytes| promoted_entry(bytes))
        };
        let error = resolve_with(
            std::slice::from_ref(&entry),
            &[policy(HONEST)],
            &provider,
            &ProviderContext::new(&model),
            &FixedConformance(bytes),
            Options::default(),
        )
        .expect_err(&format!("{name} must be refused"));
        assert_eq!(error.kind, ErrorKind::Unsupported, "{name}: {error}");
        assert!(
            error.to_string().contains(expected),
            "{name}: expected {expected:?} in {error}"
        );
    }
}

// Requirement 11: a conformance record whose outcome disagrees with its own
// checks is refused at parse time, so a promoted entry cannot cite one.
#[test]
fn a_self_contradicting_conformance_record_is_refused() {
    let mut record = passing_record();
    record.checks[0].passed = false;
    let json = record.to_json().expect("serialize");
    let error = ConformanceRecord::from_json(json.as_bytes()).expect_err("must be refused");
    assert_eq!(error.kind, ErrorKind::Document);
    assert!(error.to_string().contains("disagrees"), "found {error}");
}

// Requirement 15: entry order is not observable. Two registries differing only in
// order resolve to the same identities in the same sequence.
//
// This must resolve *successfully* in both orders to establish anything. An
// earlier version of this test used an adviser entry whose recorded identity
// disagreed with its declaration, so both orders were refused on the first
// policy and the test asserted only that two identical errors were identical —
// it would have passed with the identity sort deleted. The entries below match
// their declarations, so the ordering the host receives is actually produced.
#[test]
fn entry_order_does_not_affect_resolution() {
    let mut adviser = entry();
    adviser.extension_id = "honest-adviser".to_owned();
    adviser.version = "1.0.0".to_owned();
    adviser.category = Category::SearchAdviser;
    adviser.authority_basis = Authority::ProposeCheckedAction;

    let model = model();
    let options = Options {
        allow_experimental: true,
        ..Options::default()
    };
    let policies = [policy(HONEST), policy("honest-adviser")];
    let resolve = |entries: [RegistryEntry; 2]| {
        let provider = TestProvider::both();
        resolve_with(
            &entries,
            &policies,
            &provider,
            &ProviderContext::new(&model),
            &optimizer_registry::NoConformance,
            options,
        )
        .expect("both entries match their declarations")
    };

    let forward = resolve([entry(), adviser.clone()]);
    let reverse = resolve([adviser, entry()]);

    // Identity order, not document order. "honest-adviser" sorts before
    // "honest-producer", so a resolution that echoed its document would put them
    // the other way round in one of these two cases.
    assert_eq!(forward.identities(), ["honest-adviser", HONEST]);
    assert_eq!(
        forward.identities(),
        reverse.identities(),
        "entry order must not reach the host"
    );
    assert_eq!(forward.len(), 2);
    assert_eq!(reverse.len(), 2);

    // The registrations the executive receives carry the same order, which is
    // what SPEC-0004 requirement 18 keys invocation order on. A `Registration`
    // does not expose its identity, so the role sequence stands in for it: the
    // adviser sorts first, so a document-ordered resolution would hand the
    // producer over first in one of these two cases.
    let roles = |resolved: &optimizer_registry::ResolvedSet| {
        resolved
            .registrations()
            .iter()
            .map(|registration| match registration {
                optimizer_extension::Registration::Adviser(_) => "adviser",
                optimizer_extension::Registration::Producer(_) => "producer",
            })
            .collect::<Vec<_>>()
    };
    assert_eq!(roles(&forward), ["adviser", "producer"]);
    assert_eq!(roles(&forward), roles(&reverse));
}

// Requirement 15: a refusal is also order-independent, diagnostic included.
//
// Kept separate from the agreeing case above, because a test that only ever
// observes refusals cannot see the ordering it claims to check.
#[test]
fn entry_order_does_not_affect_a_refusal() {
    let mut misrecorded = entry();
    misrecorded.extension_id = "aa-adviser".to_owned();
    misrecorded.version = "1.0.0".to_owned();
    misrecorded.category = Category::SearchAdviser;
    misrecorded.authority_basis = Authority::ProposeCheckedAction;

    let model = model();
    let options = Options {
        allow_experimental: true,
        ..Options::default()
    };
    let policies = [policy(HONEST), policy("aa-adviser")];
    let resolve = |entries: [RegistryEntry; 2]| {
        let provider = TestProvider::both();
        resolve_with(
            &entries,
            &policies,
            &provider,
            &ProviderContext::new(&model),
            &optimizer_registry::NoConformance,
            options,
        )
        .expect_err("the adviser declares honest-adviser, not aa-adviser")
        .to_string()
    };

    assert_eq!(
        resolve([entry(), misrecorded.clone()]),
        resolve([misrecorded, entry()]),
        "entry order must not change the diagnostic"
    );
}

// Requirement 5 and 16: a resolved set lends registrations the executive accepts,
// and the declaration it was admitted on is retrievable for a record comparison.
#[test]
fn a_resolved_set_lends_registrations_and_its_declaration() {
    let provider = TestProvider::honest();
    let resolved = resolve_one(&entry(), &provider).expect("must resolve");
    assert_eq!(resolved.len(), 1);
    assert!(!resolved.is_empty());
    assert_eq!(resolved.registrations().len(), 1);
    let declaration = resolved
        .declaration(HONEST)
        .expect("declaration is retained");
    assert_eq!(declaration.version, "1.2.3");
    assert!(resolved.declaration("absent").is_none());
}
