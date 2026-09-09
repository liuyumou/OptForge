//! Extension document and host contracts under SPEC-0004.
//!
//! These tests need no executive: they exercise the declaration documents, the
//! record documents and the guarded host directly, so the version-negotiation,
//! budget and panic-containment rules stay covered independently of any search.

use std::cell::Cell;

use optimizer_core::{
    Assignment, Bound, Candidate, Constraint, Domain, ErrorKind, LinearTerm, Model, ModelDocument,
    Objective, ObjectiveSense, SCHEMA_VERSION, Tolerances, Variable,
};
use optimizer_extension::{
    Advice, Authority, CandidateProducer, Category, DeclaredLimits, EXTENSION_SCHEMA_VERSION,
    Extension, ExtensionDeclaration, ExtensionFailure, ExtensionHost, ExtensionPolicy,
    ExtensionSummary, FailureKind, MAX_FAILURE_MESSAGE_BYTES, MAX_RETAINED_FAILURES, ProblemClass,
    Registration, SearchAdviser, SearchSnapshot, validate_policies,
};

fn tolerances() -> Tolerances {
    Tolerances {
        absolute: 1e-9,
        relative: 0.0,
        integrality: 1e-9,
    }
}

/// One binary variable, so the model's class is discrete.
fn model(model_id: &str) -> Model {
    Model::new(ModelDocument {
        schema_version: SCHEMA_VERSION,
        model_id: model_id.to_string(),
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
    .expect("model")
}

/// A continuous model, for the problem-class refusal.
fn continuous_model() -> Model {
    Model::new(ModelDocument {
        schema_version: SCHEMA_VERSION,
        model_id: "continuous".to_string(),
        variables: vec![Variable {
            id: 0,
            domain: Domain::Continuous,
            lower: Bound::Finite { value: 0.0 },
            upper: Bound::Finite { value: 1.0 },
        }],
        constraints: Vec::new(),
        objective: Objective {
            sense: ObjectiveSense::Maximize,
            offset: 0.0,
            terms: vec![LinearTerm {
                variable_id: 0,
                coefficient: 1.0,
            }],
        },
    })
    .expect("model")
}

fn declaration(id: &str, category: Category) -> ExtensionDeclaration {
    ExtensionDeclaration {
        schema_version: EXTENSION_SCHEMA_VERSION,
        extension_id: id.to_string(),
        version: "1.0.0".to_string(),
        host_contract_version: EXTENSION_SCHEMA_VERSION,
        category,
        problem_classes: vec![ProblemClass::Discrete],
        deterministic: true,
        limits: DeclaredLimits {
            max_invocations: 1_000,
            max_proposals: 1_000,
        },
    }
}

fn policy(id: &str, invocations: u64, proposals: u64) -> ExtensionPolicy {
    ExtensionPolicy {
        schema_version: EXTENSION_SCHEMA_VERSION,
        extension_id: id.to_string(),
        invocation_budget: invocations,
        proposal_budget: proposals,
    }
}

fn snapshot<'a>(model: &'a Model) -> SearchSnapshot<'a> {
    SearchSnapshot {
        model,
        sense: model.document().objective.sense,
        seed: 17,
        tolerances: tolerances(),
        incumbent_objective: None,
        dual_bound: None,
        nodes_explored: 0,
        open_nodes: &[],
        fractional: &[],
    }
}

/// A producer configured by a closure, so one type covers every case.
struct Producer {
    declaration: ExtensionDeclaration,
    behavior: fn(&SearchSnapshot<'_>) -> Vec<Candidate>,
    calls: Cell<u64>,
}

impl Producer {
    fn new(
        declaration: ExtensionDeclaration,
        behavior: fn(&SearchSnapshot<'_>) -> Vec<Candidate>,
    ) -> Self {
        Self {
            declaration,
            behavior,
            calls: Cell::new(0),
        }
    }
}

impl Extension for Producer {
    fn declare(&self) -> ExtensionDeclaration {
        self.declaration.clone()
    }
}

impl CandidateProducer for Producer {
    fn propose(&self, snapshot: &SearchSnapshot<'_>) -> Vec<Candidate> {
        self.calls.set(self.calls.get() + 1);
        (self.behavior)(snapshot)
    }
}

fn one_candidate(snapshot: &SearchSnapshot<'_>) -> Vec<Candidate> {
    vec![Candidate {
        schema_version: SCHEMA_VERSION,
        model_id: snapshot.model.document().model_id.clone(),
        values: vec![Assignment {
            variable_id: 0,
            value: 1.0,
        }],
    }]
}

fn no_candidates(_snapshot: &SearchSnapshot<'_>) -> Vec<Candidate> {
    Vec::new()
}

fn panicking(_snapshot: &SearchSnapshot<'_>) -> Vec<Candidate> {
    panic!("deliberate panic under test");
}

/// An adviser configured by a closure.
struct Adviser {
    declaration: ExtensionDeclaration,
    behavior: fn() -> Advice,
}

impl Extension for Adviser {
    fn declare(&self) -> ExtensionDeclaration {
        self.declaration.clone()
    }
}

impl SearchAdviser for Adviser {
    fn advise(&self, _snapshot: &SearchSnapshot<'_>) -> Advice {
        (self.behavior)()
    }
}

// ---------------------------------------------------------------------------
// Requirement 1: declarations validate before anything is invoked.
// ---------------------------------------------------------------------------

/// A well-formed declaration round trips and sorts its problem classes.
#[test]
fn declarations_round_trip_and_canonicalize() {
    let mut original = declaration("valid", Category::CandidateProducer);
    original.problem_classes = vec![ProblemClass::Discrete, ProblemClass::Continuous];

    let validated = original.validate().expect("valid declaration");
    assert_eq!(
        validated.problem_classes,
        vec![ProblemClass::Continuous, ProblemClass::Discrete],
        "problem classes are canonicalized so two equal declarations compare equal"
    );

    let json = validated.to_json().expect("serializable");
    let parsed = ExtensionDeclaration::from_json(json.as_bytes()).expect("round trip");
    assert_eq!(parsed, validated);
}

/// One malformed-declaration case: a mutation and the category it must fail as.
type DeclarationCase = (fn(&mut ExtensionDeclaration), ErrorKind);

/// Requirement 1: each malformed declaration fails in its own category.
#[test]
fn malformed_declarations_are_categorized() {
    let cases: &[DeclarationCase] = &[
        (
            |d| d.schema_version = EXTENSION_SCHEMA_VERSION + 1,
            ErrorKind::Document,
        ),
        (|d| d.extension_id = String::new(), ErrorKind::Structural),
        (|d| d.extension_id = "a".repeat(65), ErrorKind::Structural),
        (
            |d| d.extension_id = "bad\nname".to_string(),
            ErrorKind::Structural,
        ),
        (|d| d.version = String::new(), ErrorKind::Structural),
        (|d| d.problem_classes = Vec::new(), ErrorKind::Structural),
        (
            |d| d.problem_classes = vec![ProblemClass::Discrete, ProblemClass::Discrete],
            ErrorKind::Structural,
        ),
        (|d| d.limits.max_invocations = 0, ErrorKind::Unsupported),
        (|d| d.limits.max_proposals = 0, ErrorKind::Unsupported),
    ];

    for (mutate, expected) in cases {
        let mut invalid = declaration("case", Category::CandidateProducer);
        mutate(&mut invalid);
        assert_eq!(
            invalid.validate().unwrap_err().kind,
            *expected,
            "declaration {invalid:?} must fail as {expected:?}"
        );
    }
}

/// Requirement 23: documents reject positional arrays, unknown fields and variants.
#[test]
fn extension_documents_require_strict_objects() {
    let positional = b"[1, \"id\", \"1.0.0\", 1, \"candidate_producer\", [], true, {}]";
    assert!(
        serde_json::from_slice::<ExtensionDeclaration>(positional).is_err(),
        "a positional declaration must be rejected"
    );

    let unknown = br#"{"schema_version":1,"extension_id":"id","version":"1.0.0",
        "host_contract_version":1,"category":"candidate_producer",
        "problem_classes":["discrete"],"deterministic":true,
        "limits":{"max_invocations":1,"max_proposals":1},"surprise":true}"#;
    assert!(
        serde_json::from_slice::<ExtensionDeclaration>(unknown).is_err(),
        "an unknown field must be rejected"
    );

    for (name, bytes) in [
        ("category", &b"\"numerical_backend\""[..]),
        ("problem class", &b"\"quadratic\""[..]),
    ] {
        assert!(
            serde_json::from_slice::<Category>(bytes).is_err()
                || serde_json::from_slice::<ProblemClass>(bytes).is_err(),
            "an unknown {name} variant must be rejected"
        );
    }
    assert!(
        serde_json::from_slice::<FailureKind>(b"\"mildly_disappointing\"").is_err(),
        "an unknown failure kind must be rejected"
    );
    assert!(
        serde_json::from_slice::<Authority>(b"\"declare_optimality\"").is_err(),
        "an unknown authority must be rejected"
    );
}

/// Authority is derived from the category, never chosen by the extension.
#[test]
fn authority_follows_the_category() {
    assert_eq!(
        Category::CandidateProducer.authority(),
        Some(Authority::ProposeValidatedCandidate)
    );
    assert_eq!(
        Category::SearchAdviser.authority(),
        Some(Authority::ProposeCheckedAction)
    );
    assert_eq!(
        Category::Transformation.authority(),
        None,
        "a transformation has no admitted authority"
    );
}

/// The model's class comes from its domains, not from any declaration.
#[test]
fn problem_class_is_decided_by_the_model() {
    assert_eq!(ProblemClass::of(&model("discrete")), ProblemClass::Discrete);
    assert_eq!(
        ProblemClass::of(&continuous_model()),
        ProblemClass::Continuous
    );
}

// ---------------------------------------------------------------------------
// Requirements 2-4: registration refusals, each recorded and never invoked.
// ---------------------------------------------------------------------------

/// Requirement 2: an incompatible contract version is refused in both directions.
#[test]
fn incompatible_contract_versions_are_refused_both_ways() {
    let discrete = model("contract");
    for version in [EXTENSION_SCHEMA_VERSION + 1, 0] {
        let mut declared = declaration("mismatch", Category::CandidateProducer);
        declared.host_contract_version = version;
        let producer = Producer::new(declared, one_candidate);

        let mut host = ExtensionHost::register(
            &[Registration::Producer(&producer)],
            &[policy("mismatch", 10, 10)],
            &discrete,
        );

        let summaries = host.summaries();
        let summary = summaries.first().expect("a refusal is still recorded");
        assert!(
            !summary.registered,
            "version {version} must not be admitted"
        );
        assert_eq!(summary.extension_id, "mismatch");
        assert_eq!(
            summary.version, "1.0.0",
            "identity and version are recorded"
        );
        assert_eq!(
            summary.failures.first().map(|failure| failure.kind),
            Some(FailureKind::IncompatibleContract)
        );

        assert!(host.is_empty(), "no extension participates");
        assert!(host.collect_proposals(&snapshot(&discrete)).is_empty());
        assert_eq!(
            producer.calls.get(),
            0,
            "a refused extension is never invoked"
        );
    }
}

/// Requirement 3: the transformation category is refused at registration.
#[test]
fn transformation_category_is_refused_at_registration() {
    let discrete = model("transform");
    let producer = Producer::new(
        declaration("transformer", Category::Transformation),
        one_candidate,
    );

    let mut host = ExtensionHost::register(
        &[Registration::Producer(&producer)],
        &[policy("transformer", 10, 10)],
        &discrete,
    );

    let summaries = host.summaries();
    let summary = summaries.first().expect("recorded");
    assert!(!summary.registered);
    assert_eq!(summary.authority, None, "no authority is granted");
    assert_eq!(
        summary.failures.first().map(|failure| failure.kind),
        Some(FailureKind::UnsupportedCategory)
    );
    assert!(host.collect_proposals(&snapshot(&discrete)).is_empty());
    assert_eq!(producer.calls.get(), 0);
}

/// A declaration disagreeing with the role it was registered in is refused,
/// not silently reinterpreted into an authority nobody intended.
#[test]
fn role_and_category_must_agree() {
    let discrete = model("role");
    let producer = Producer::new(
        declaration("misfiled", Category::SearchAdviser),
        one_candidate,
    );

    let host = ExtensionHost::register(
        &[Registration::Producer(&producer)],
        &[policy("misfiled", 10, 10)],
        &discrete,
    );

    let summaries = host.summaries();
    let summary = summaries.first().expect("recorded");
    assert!(!summary.registered);
    assert_eq!(
        summary.failures.first().map(|failure| failure.kind),
        Some(FailureKind::UnsupportedCategory)
    );
}

/// An extension is not invoked on a class it did not claim.
#[test]
fn unclaimed_problem_classes_are_refused() {
    let continuous = continuous_model();
    let mut declared = declaration("discrete-only", Category::CandidateProducer);
    declared.problem_classes = vec![ProblemClass::Discrete];
    let producer = Producer::new(declared, one_candidate);

    let host = ExtensionHost::register(
        &[Registration::Producer(&producer)],
        &[policy("discrete-only", 10, 10)],
        &continuous,
    );

    let summaries = host.summaries();
    assert_eq!(
        summaries
            .first()
            .and_then(|s| s.failures.first())
            .map(|f| f.kind),
        Some(FailureKind::UnsupportedProblemClass)
    );
    assert_eq!(producer.calls.get(), 0);
}

/// An invalid declaration is refused with its own failure kind.
#[test]
fn invalid_declarations_are_refused_at_registration() {
    let discrete = model("invalid");
    let mut declared = declaration("zero-budget", Category::CandidateProducer);
    declared.limits.max_invocations = 0;
    let producer = Producer::new(declared, one_candidate);

    let host = ExtensionHost::register(
        &[Registration::Producer(&producer)],
        &[policy("zero-budget", 10, 10)],
        &discrete,
    );

    let summaries = host.summaries();
    assert_eq!(
        summaries
            .first()
            .and_then(|s| s.failures.first())
            .map(|f| f.kind),
        Some(FailureKind::DeclarationInvalid)
    );
    assert_eq!(producer.calls.get(), 0);
}

/// An extension the caller never permitted is neither invoked nor recorded.
#[test]
fn unpermitted_extensions_are_not_consulted() {
    let discrete = model("unpermitted");
    let producer = Producer::new(
        declaration("uninvited", Category::CandidateProducer),
        one_candidate,
    );

    let mut host = ExtensionHost::register(&[Registration::Producer(&producer)], &[], &discrete);

    assert!(
        host.summaries().is_empty(),
        "an unpermitted extension is not a failure"
    );
    assert!(host.is_empty());
    assert!(host.collect_proposals(&snapshot(&discrete)).is_empty());
    assert_eq!(producer.calls.get(), 0);
}

/// An extension whose `declare` panics cannot be registered.
#[test]
fn a_panicking_declaration_is_contained() {
    struct Exploding;
    impl Extension for Exploding {
        fn declare(&self) -> ExtensionDeclaration {
            panic!("deliberate panic in declare");
        }
    }
    impl CandidateProducer for Exploding {
        fn propose(&self, _snapshot: &SearchSnapshot<'_>) -> Vec<Candidate> {
            unreachable!("registration must have refused this extension");
        }
    }

    let discrete = model("exploding");
    let host = ExtensionHost::register(
        &[Registration::Producer(&Exploding)],
        &[policy("anything", 10, 10)],
        &discrete,
    );
    assert!(
        host.summaries().is_empty(),
        "an extension that cannot state what it is has no identity to record"
    );
    assert!(host.is_empty());
}

// ---------------------------------------------------------------------------
// Requirements 14, 16, 17: containment, counted budgets, bounded diagnostics.
// ---------------------------------------------------------------------------

/// Requirement 14: a panicking proposal is contained, disabled and recorded.
#[test]
fn a_panicking_proposal_disables_the_extension() {
    let discrete = model("panic");
    let producer = Producer::new(
        declaration("panics", Category::CandidateProducer),
        panicking,
    );

    let mut host = ExtensionHost::register(
        &[Registration::Producer(&producer)],
        &[policy("panics", 10, 10)],
        &discrete,
    );

    assert!(host.collect_proposals(&snapshot(&discrete)).is_empty());
    let summaries = host.summaries();
    let summary = summaries.first().expect("recorded");
    assert!(summary.registered, "it was admitted before it panicked");
    assert!(summary.disabled, "a panicked extension is disabled");
    assert_eq!(summary.invocations, 1);
    assert_eq!(
        summary.failures.first().map(|failure| failure.kind),
        Some(FailureKind::Panicked)
    );

    // Disabling is monotone and required for soundness: an extension that
    // panicked mid-operation may panic on every later call.
    assert!(host.is_empty());
    assert!(host.collect_proposals(&snapshot(&discrete)).is_empty());
    assert_eq!(
        host.summaries().first().expect("recorded").invocations,
        1,
        "a disabled extension is not invoked again"
    );
}

/// Requirement 16: an invocation budget is reached but never exceeded.
#[test]
fn invocation_budgets_are_counted_and_enforced() {
    let discrete = model("invocations");
    let producer = Producer::new(
        declaration("counted", Category::CandidateProducer),
        no_candidates,
    );

    let mut host = ExtensionHost::register(
        &[Registration::Producer(&producer)],
        &[policy("counted", 2, 10)],
        &discrete,
    );

    for _ in 0..5 {
        host.collect_proposals(&snapshot(&discrete));
    }

    let summaries = host.summaries();
    let summary = summaries.first().expect("recorded");
    assert_eq!(summary.invocations, 2, "the budget bounds the invocations");
    assert_eq!(producer.calls.get(), 2);
    assert!(summary.disabled);
    assert_eq!(
        summary.failures.first().map(|failure| failure.kind),
        Some(FailureKind::BudgetExhausted)
    );
}

/// Requirement 16: a proposal budget truncates a flood mid-invocation.
#[test]
fn proposal_budgets_truncate_a_flood() {
    fn flood(snapshot: &SearchSnapshot<'_>) -> Vec<Candidate> {
        (0..50).flat_map(|_| one_candidate(snapshot)).collect()
    }

    let discrete = model("flood");
    let producer = Producer::new(declaration("flooder", Category::CandidateProducer), flood);

    let mut host = ExtensionHost::register(
        &[Registration::Producer(&producer)],
        &[policy("flooder", 10, 3)],
        &discrete,
    );

    let proposals = host.collect_proposals(&snapshot(&discrete));
    assert_eq!(
        proposals.len(),
        3,
        "only the permitted proposals are returned"
    );

    let summaries = host.summaries();
    let summary = summaries.first().expect("recorded");
    assert_eq!(summary.proposals, 3);
    assert!(summary.disabled);
    assert_eq!(
        summary.failures.first().map(|failure| failure.kind),
        Some(FailureKind::BudgetExhausted)
    );
}

/// The narrower of the declared limit and the caller's policy governs.
#[test]
fn the_tighter_of_declaration_and_policy_applies() {
    let discrete = model("tighter");
    let mut declared = declaration("modest", Category::CandidateProducer);
    declared.limits.max_invocations = 1;
    let producer = Producer::new(declared, no_candidates);

    let mut host = ExtensionHost::register(
        &[Registration::Producer(&producer)],
        // The caller is generous; the declaration is not.
        &[policy("modest", 99, 99)],
        &discrete,
    );

    for _ in 0..4 {
        host.collect_proposals(&snapshot(&discrete));
    }
    assert_eq!(producer.calls.get(), 1, "the declared limit is honored too");
}

/// Requirement 17: diagnostics stay bounded however many rejections occur.
#[test]
fn recorded_diagnostics_are_bounded() {
    let discrete = model("bounded");
    let producer = Producer::new(
        declaration("rejected", Category::CandidateProducer),
        no_candidates,
    );

    let mut host = ExtensionHost::register(
        &[Registration::Producer(&producer)],
        &[policy("rejected", 10, 10)],
        &discrete,
    );

    // Stand in for one rejection per node over a large search: each carries a
    // distinct message, which is the case that could grow without a cap.
    for node in 0..10_000 {
        host.reject(
            0,
            FailureKind::InvalidCandidate,
            format!("node {node} proposal refused"),
        );
    }

    let summaries = host.summaries();
    let summary = summaries.first().expect("recorded");
    assert_eq!(summary.rejected, 10_000, "counters stay exact");
    assert_eq!(
        summary.failures.len(),
        MAX_RETAINED_FAILURES,
        "retained messages are capped independently of node count"
    );
    assert!(
        !summary.disabled,
        "a rejected proposal is a normal event, not a disable"
    );
}

/// A long failure message is truncated on a character boundary.
#[test]
fn failure_messages_are_truncated_safely() {
    // Multi-byte characters straddling the cap would panic a byte-wise split.
    let failure = ExtensionFailure::new(FailureKind::InvalidAdvice, "é".repeat(400));
    assert!(failure.message.len() <= MAX_FAILURE_MESSAGE_BYTES);
    assert!(
        failure.message.chars().all(|c| c == 'é'),
        "truncation must not split a character: {:?}",
        failure.message
    );
}

// ---------------------------------------------------------------------------
// Requirements 18, 21, 23: order, policy validation and record round trips.
// ---------------------------------------------------------------------------

/// Requirement 18: invocation order is by identity, not by registry order.
#[test]
fn invocation_order_is_by_extension_identity() {
    let discrete = model("order");
    let first = Producer::new(
        declaration("aaa", Category::CandidateProducer),
        one_candidate,
    );
    let second = Producer::new(
        declaration("zzz", Category::CandidateProducer),
        one_candidate,
    );

    // Registered in reverse identity order deliberately.
    let mut host = ExtensionHost::register(
        &[
            Registration::Producer(&second),
            Registration::Producer(&first),
        ],
        &[policy("zzz", 10, 10), policy("aaa", 10, 10)],
        &discrete,
    );

    let identities: Vec<String> = host
        .summaries()
        .into_iter()
        .map(|summary| summary.extension_id)
        .collect();
    assert_eq!(identities, vec!["aaa".to_string(), "zzz".to_string()]);

    let proposals = host.collect_proposals(&snapshot(&discrete));
    assert_eq!(
        proposals
            .iter()
            .map(|(index, _)| *index)
            .collect::<Vec<_>>(),
        vec![0, 1],
        "proposals arrive in identity order"
    );
}

/// A nondeterministic declaration is visible to the host.
#[test]
fn nondeterminism_is_reported() {
    let discrete = model("determinism");
    let mut declared = declaration("random", Category::CandidateProducer);
    declared.deterministic = false;
    let producer = Producer::new(declared, no_candidates);

    let host = ExtensionHost::register(
        &[Registration::Producer(&producer)],
        &[policy("random", 10, 10)],
        &discrete,
    );
    assert!(!host.is_deterministic());
    assert!(!host.summaries().first().expect("recorded").deterministic);

    let honest = Producer::new(
        declaration("honest", Category::CandidateProducer),
        no_candidates,
    );
    let deterministic = ExtensionHost::register(
        &[Registration::Producer(&honest)],
        &[policy("honest", 10, 10)],
        &discrete,
    );
    assert!(deterministic.is_deterministic());
}

/// Requirement 21: a policy list is validated, including duplicate identities.
#[test]
fn policies_are_validated() {
    assert!(
        validate_policies(&[])
            .expect("an empty policy is valid")
            .is_empty()
    );
    assert!(validate_policies(&[policy("one", 1, 1), policy("two", 1, 1)]).is_ok());

    assert_eq!(
        validate_policies(&[policy("same", 1, 1), policy("same", 2, 2)])
            .unwrap_err()
            .kind,
        ErrorKind::Structural,
        "a duplicate identity makes the summary ambiguous"
    );

    let mut version = policy("versioned", 1, 1);
    version.schema_version = EXTENSION_SCHEMA_VERSION + 1;
    assert_eq!(
        validate_policies(&[version]).unwrap_err().kind,
        ErrorKind::Document
    );

    assert_eq!(
        validate_policies(&[policy("", 1, 1)]).unwrap_err().kind,
        ErrorKind::Structural
    );
    for zero in [policy("zero", 0, 1), policy("zero", 1, 0)] {
        assert_eq!(
            validate_policies(&[zero]).unwrap_err().kind,
            ErrorKind::Unsupported,
            "a zero budget cannot be honored"
        );
    }
}

/// Requirement 23: a summary round trips and rejects a bad version.
#[test]
fn summaries_round_trip_and_reject_bad_versions() {
    let discrete = model("summary");
    let producer = Producer::new(
        declaration("summarized", Category::CandidateProducer),
        no_candidates,
    );
    let host = ExtensionHost::register(
        &[Registration::Producer(&producer)],
        &[policy("summarized", 10, 10)],
        &discrete,
    );

    let summary = host.summaries().into_iter().next().expect("recorded");
    let json = summary.to_json().expect("serializable");
    assert_eq!(
        ExtensionSummary::from_json(json.as_bytes()).expect("round trip"),
        summary
    );

    // An admitted producer has an authority; a refused one omits the field
    // rather than serializing null in place of a real value.
    assert!(json.contains("\"authority\": \"propose_validated_candidate\""));

    let bumped = json.replacen("\"schema_version\": 1", "\"schema_version\": 9", 1);
    assert_eq!(
        ExtensionSummary::from_json(bumped.as_bytes())
            .unwrap_err()
            .kind,
        ErrorKind::Document
    );
}

/// A refused extension's summary omits the authority it was never granted.
#[test]
fn a_refused_summary_omits_its_authority() {
    let discrete = model("omitted");
    let producer = Producer::new(
        declaration("refused", Category::Transformation),
        no_candidates,
    );
    let host = ExtensionHost::register(
        &[Registration::Producer(&producer)],
        &[policy("refused", 10, 10)],
        &discrete,
    );

    let summary = host.summaries().into_iter().next().expect("recorded");
    let json = summary.to_json().expect("serializable");
    assert!(
        !json.contains("\"authority\""),
        "an ungranted authority is absent, not null: {json}"
    );
}

// ---------------------------------------------------------------------------
// Advice dispatch at the host level.
// ---------------------------------------------------------------------------

/// An abstention is not an opinion and is not counted as a proposal.
#[test]
fn abstention_yields_no_advice() {
    let discrete = model("abstain");
    let adviser = Adviser {
        declaration: declaration("quiet", Category::SearchAdviser),
        behavior: || Advice::Abstain,
    };

    let mut host = ExtensionHost::register(
        &[Registration::Adviser(&adviser)],
        &[policy("quiet", 10, 10)],
        &discrete,
    );

    assert!(host.request_advice(&snapshot(&discrete)).is_none());
    let summary = host.summaries().into_iter().next().expect("recorded");
    assert_eq!(summary.invocations, 1, "it was still consulted");
    assert_eq!(summary.proposals, 0, "an abstention is not a proposal");
}

/// The first non-abstaining adviser in identity order supplies the action.
#[test]
fn the_first_opinion_in_identity_order_wins() {
    let discrete = model("first");
    let quiet = Adviser {
        declaration: declaration("aaa-quiet", Category::SearchAdviser),
        behavior: || Advice::Abstain,
    };
    let loud = Adviser {
        declaration: declaration("bbb-loud", Category::SearchAdviser),
        behavior: || Advice::SelectNode(7),
    };

    let mut host = ExtensionHost::register(
        &[Registration::Adviser(&loud), Registration::Adviser(&quiet)],
        &[policy("aaa-quiet", 10, 10), policy("bbb-loud", 10, 10)],
        &discrete,
    );

    let (index, advice) = host
        .request_advice(&snapshot(&discrete))
        .expect("an opinion");
    assert_eq!(advice, Advice::SelectNode(7));
    assert_eq!(
        host.summaries()[index].extension_id,
        "bbb-loud",
        "the returned index attributes the advice to its author"
    );
}

/// Requirement 14: a panicking adviser is contained and disabled.
#[test]
fn a_panicking_adviser_disables_the_extension() {
    let discrete = model("adviser-panic");
    let adviser = Adviser {
        declaration: declaration("panics", Category::SearchAdviser),
        behavior: || panic!("deliberate adviser panic"),
    };

    let mut host = ExtensionHost::register(
        &[Registration::Adviser(&adviser)],
        &[policy("panics", 10, 10)],
        &discrete,
    );

    assert!(host.request_advice(&snapshot(&discrete)).is_none());
    let summary = host.summaries().into_iter().next().expect("recorded");
    assert!(summary.disabled);
    assert_eq!(
        summary.failures.first().map(|failure| failure.kind),
        Some(FailureKind::Panicked)
    );
    assert!(host.is_empty());
}

/// An empty host consults nothing and reports nothing.
#[test]
fn an_empty_host_is_inert() {
    let discrete = model("inert");
    let mut host = ExtensionHost::empty();
    assert!(host.is_empty());
    assert!(host.is_deterministic());
    assert!(host.summaries().is_empty());
    assert!(host.collect_proposals(&snapshot(&discrete)).is_empty());
    assert!(host.request_advice(&snapshot(&discrete)).is_none());
}
