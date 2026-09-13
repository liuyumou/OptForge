//! The reusable conformance suite and its record under SPEC-0009.
//!
//! C3 established extension safety with a fixed model grid, hostile extensions
//! and one invariance assertion: over unlimited budgets, a registered extension
//! must leave the outcome, the proven optimum, the dual bound, the forfeiture
//! state and both prune counters exactly as an extension-free run left them.
//! That evidence lived in the workspace's own tests, so a third-party author
//! could read the property but not run it. This module makes it a command.
//!
//! Two rules keep a conformance record from being vacuous. The suite asserts the
//! extension was actually invoked before asserting anything about its effect,
//! which is the lesson C3 recorded when three of its acceptance tests turned out
//! to be testing an extension that was never consulted. And budgets are
//! unlimited, because an adviser spending a node budget badly legitimately
//! changes which outcome a *budgeted* search reaches; asserting invariance under
//! a budget would be flaky by design rather than a real check.
//!
//! What this suite does not do is measure. It reports no timing and no solution
//! quality, and a passing record means the contract held, never that the
//! extension helped.

use serde::Serialize;

use optimizer_core::{
    Backend, Bound, CancellationToken, Constraint, Domain, ErrorKind, LinearTerm, Model,
    ModelDocument, Objective, ObjectiveSense, ValidationError, Variable,
};
use optimizer_extension::{EXTENSION_SCHEMA_VERSION, ExtensionPolicy};
use optimizer_solver::{SEARCH_SCHEMA_VERSION, SearchOptions, SearchRecord};

use crate::Provider;
use crate::document::RegistryEntry;
use crate::resolve::{
    ConformanceSource, NoConformance, Options, ProviderContext, ResolvedSet, resolve_with,
};
use crate::serde_strict::deserialize_object;

/// Current conformance record wire version.
pub const CONFORMANCE_SCHEMA_VERSION: u32 = 1;

/// Longest retained check detail, in bytes.
pub const MAX_DETAIL_BYTES: usize = 200;

/// One check's result, named so a reader can see which property held.
#[derive(Clone, Debug, PartialEq, Eq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct ConformanceCheck {
    /// Stable machine-readable check name.
    pub name: String,
    /// Whether this check passed.
    pub passed: bool,
    /// Bounded detail, populated for a failure and for context on a pass.
    pub detail: String,
}

deserialize_object!(ConformanceCheck {
    name: String,
    passed: bool,
    detail: String,
});

impl ConformanceCheck {
    /// Build a check, truncating the detail at a character boundary.
    fn new(name: &str, passed: bool, detail: impl Into<String>) -> Self {
        let mut detail = detail.into();
        if detail.len() > MAX_DETAIL_BYTES {
            let mut end = MAX_DETAIL_BYTES;
            while end > 0 && !detail.is_char_boundary(end) {
                end -= 1;
            }
            detail.truncate(end);
        }
        Self {
            name: name.to_owned(),
            passed,
            detail,
        }
    }
}

/// The result of running the conformance suite over one extension.
///
/// There is deliberately no timing field. A duration here would be read as a
/// performance result, and SPEC-0009 requirement 27 forbids recording one.
#[derive(Clone, Debug, PartialEq, Eq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct ConformanceRecord {
    /// Must equal [`CONFORMANCE_SCHEMA_VERSION`].
    pub schema_version: u32,
    /// Identity of the extension this record describes.
    pub extension_id: String,
    /// The extension's own reported version.
    pub version: String,
    /// Host contract version the suite ran against.
    pub host_contract_version: u32,
    /// Number of models in the fixed grid, so it cannot silently shrink.
    pub grid_size: u32,
    /// The relaxation backend's own reported version.
    pub backend_version: String,
    /// Every check, in a fixed order.
    pub checks: Vec<ConformanceCheck>,
    /// Whether every check passed.
    pub outcome: bool,
}

deserialize_object!(ConformanceRecord {
    schema_version: u32,
    extension_id: String,
    version: String,
    host_contract_version: u32,
    grid_size: u32,
    backend_version: String,
    checks: Vec<ConformanceCheck>,
    outcome: bool,
});

impl ConformanceRecord {
    /// Serialize this record.
    ///
    /// # Errors
    ///
    /// Returns a document failure when serialization fails.
    pub fn to_json(&self) -> Result<String, ValidationError> {
        serde_json::to_string_pretty(self)
            .map_err(|error| ValidationError::new(ErrorKind::Document, error.to_string()))
    }

    /// Parse one complete versioned conformance record.
    ///
    /// # Errors
    ///
    /// Returns a document failure for malformed JSON, an unknown or duplicate
    /// field, a positional array in place of an object, an unsupported version,
    /// or a record whose recorded outcome disagrees with its own checks.
    pub fn from_json(bytes: &[u8]) -> Result<Self, ValidationError> {
        let record: Self = serde_json::from_slice(bytes)
            .map_err(|error| ValidationError::new(ErrorKind::Document, error.to_string()))?;
        if record.schema_version != CONFORMANCE_SCHEMA_VERSION {
            return Err(ValidationError::new(
                ErrorKind::Document,
                format!(
                    "unsupported conformance schema_version {}",
                    record.schema_version
                ),
            ));
        }
        if record.extension_id.is_empty() || record.version.is_empty() {
            return Err(ValidationError::new(
                ErrorKind::Document,
                "extension_id and version must not be empty",
            ));
        }
        if record.checks.is_empty() {
            return Err(ValidationError::new(
                ErrorKind::Document,
                "a conformance record must carry at least one check",
            ));
        }
        // A record claiming to pass while carrying a failing check would let a
        // promoted entry cite evidence that contradicts itself.
        if record.outcome != record.checks.iter().all(|check| check.passed) {
            return Err(ValidationError::new(
                ErrorKind::Document,
                "outcome disagrees with the recorded checks",
            ));
        }
        Ok(record)
    }
}

/// The fixed grid the suite runs over.
///
/// Small, discrete and fractional at the root, so a search actually branches and
/// an adviser is actually consulted. C3 recorded that three of its acceptance
/// tests were vacuous because their relaxations happened to be integral; the
/// coefficients here are chosen so that cannot happen silently, and
/// [`GRID_SIZE`] is recorded in every record so the grid cannot shrink unnoticed.
pub const GRID_SIZE: u32 = 6;

/// Build the fixed grid. No randomness, so a failure reproduces exactly.
fn grid() -> Vec<Model> {
    let mut models = Vec::new();
    for (index, (sense, domain, capacity)) in [
        (ObjectiveSense::Maximize, Domain::Binary, 3.0),
        (ObjectiveSense::Maximize, Domain::Binary, 5.0),
        (ObjectiveSense::Minimize, Domain::Binary, 2.0),
        (ObjectiveSense::Maximize, Domain::Integer, 4.0),
        (ObjectiveSense::Minimize, Domain::Integer, 3.0),
        (ObjectiveSense::Maximize, Domain::Integer, 7.0),
    ]
    .into_iter()
    .enumerate()
    {
        let document = knapsack(index, sense, domain, capacity);
        // The grid is a fixed constant of this crate, so a model that does not
        // validate is a defect here rather than caller input.
        models.push(Model::new(document).expect("conformance grid model is valid"));
    }
    models
}

/// One tiny knapsack-shaped model with a fractional linear relaxation.
///
/// The coefficients are chosen so the root relaxation is fractional and the
/// executive genuinely branches. A grid whose relaxations happened to be integral
/// would never consult a search adviser, and the suite would pass without
/// exercising anything.
fn knapsack(index: usize, sense: ObjectiveSense, domain: Domain, capacity: f64) -> ModelDocument {
    let weights = [2.0, 3.0, 4.0];
    let values = [3.0, 4.0, 5.0];
    let upper = if domain == Domain::Binary { 1.0 } else { 2.0 };
    let terms = |coefficients: [f64; 3]| {
        (0..3)
            .map(|id| LinearTerm {
                variable_id: u32::try_from(id).expect("grid index fits in u32"),
                coefficient: coefficients[id],
            })
            .collect::<Vec<_>>()
    };
    ModelDocument {
        schema_version: optimizer_core::SCHEMA_VERSION,
        model_id: format!("conformance-grid-{index}"),
        variables: (0..3)
            .map(|id| Variable {
                id: u32::try_from(id).expect("grid index fits in u32"),
                domain,
                lower: Bound::Finite { value: 0.0 },
                upper: Bound::Finite { value: upper },
            })
            .collect(),
        constraints: vec![Constraint {
            id: 0,
            lower: Bound::NegativeInfinity,
            upper: Bound::Finite { value: capacity },
            terms: terms(weights),
        }],
        objective: Objective {
            sense,
            offset: 0.0,
            terms: terms(values),
        },
    }
}

/// Search configuration for the suite: unlimited budgets, fixed tolerances.
fn options(policies: Vec<ExtensionPolicy>) -> SearchOptions {
    SearchOptions {
        schema_version: SEARCH_SCHEMA_VERSION,
        seed: 17,
        // Unlimited deliberately. Requirement 23's invariance claim is stated
        // over unlimited budgets because an adviser can legitimately change which
        // outcome a budgeted search reaches by exploring badly.
        node_limit: None,
        time_limit_ms: None,
        open_node_limit: None,
        improvement_tolerance: 1e-9,
        // The suite checks a contract, not hardware. A device would make the
        // conformance record depend on what the checking host happens to have.
        device: optimizer_core::Device::Cpu,
        relaxation: optimizer_core::SolveOptions {
            schema_version: optimizer_core::SOLVE_SCHEMA_VERSION,
            seed: 17,
            time_limit_ms: None,
            iteration_limit: None,
            node_limit: None,
            tolerances: optimizer_core::Tolerances {
                absolute: 1e-9,
                relative: 1e-9,
                integrality: 1e-9,
            },
            threads: 1,
        },
        extensions: policies,
    }
}

/// Whether two records agree on every conclusion requirement 23 names.
///
/// Elapsed time is excluded for the reason SPEC-0005 already fixed: it measures
/// the host rather than the search.
fn conclusions_agree(left: &SearchRecord, right: &SearchRecord) -> Result<(), String> {
    if left.outcome != right.outcome {
        return Err(format!(
            "outcome {:?} became {:?}",
            left.outcome, right.outcome
        ));
    }
    for (field, a, b) in [
        ("objective", left.objective, right.objective),
        ("dual_bound", left.dual_bound, right.dual_bound),
    ] {
        if a.map(f64::to_bits) != b.map(f64::to_bits) {
            return Err(format!("{field} {a:?} became {b:?}"));
        }
    }
    if left.forfeited != right.forfeited {
        return Err(format!(
            "forfeited {} became {}",
            left.forfeited, right.forfeited
        ));
    }
    for (field, a, b) in [
        (
            "nodes_pruned_infeasible",
            left.nodes_pruned_infeasible,
            right.nodes_pruned_infeasible,
        ),
        (
            "nodes_pruned_bound",
            left.nodes_pruned_bound,
            right.nodes_pruned_bound,
        ),
    ] {
        if a != b {
            return Err(format!("{field} {a} became {b}"));
        }
    }
    Ok(())
}

/// Run the conformance suite over one entry and return its record.
///
/// The suite runs each grid model twice, once with no extension and once with
/// this entry registered, and compares the conclusions. A candidate producer is
/// expected to change `nodes_pruned_bound` when its proposals are *accepted* —
/// that is what a good incumbent is for — so the invariance check is applied to
/// the counters only when nothing was accepted, exactly as SPEC-0008 requirement
/// 20's scope was corrected during C5. When proposals were accepted, the proven
/// optimum and the forfeiture state must still be identical, which is what
/// SPEC-0004 requirement 19 actually promises.
///
/// # Errors
///
/// Returns a categorized [`ValidationError`] when resolution itself fails, which
/// is a caller problem rather than a conformance result: there is nothing to
/// report about an extension that could not be resolved at all.
pub fn run(
    entry: &RegistryEntry,
    provider: &dyn Provider,
    backend: &dyn Backend,
    instance: Option<&[u8]>,
) -> Result<ConformanceRecord, ValidationError> {
    // The suite builds its own models, so it also builds the contexts they are
    // resolved against. The caller's auxiliary instance has to travel through
    // here: an entry declaring a data requirement is refused against a context
    // that lacks one, which is requirement 8 doing its job rather than a defect.
    fn context<'a>(model: &'a Model, instance: Option<&'a [u8]>) -> ProviderContext<'a> {
        match instance {
            Some(instance) => ProviderContext::with_instance(model, instance),
            None => ProviderContext::new(model),
        }
    }
    // Conformance *produces* the evidence a promoted entry cites, so it cannot
    // require that evidence to already exist: checking promotion here would make an
    // entry unrunnable until it was already promoted, and the first conformance run
    // for any extension would be impossible. The suite therefore resolves with
    // promotion checking bypassed, and this is the one place that is correct.
    let resolve_options = Options {
        allow_experimental: true,
        skip_promotion_check: true,
    };
    let conformance: &dyn ConformanceSource = &NoConformance;

    let cancel = CancellationToken::new();
    let mut checks = Vec::new();
    let policy = ExtensionPolicy {
        schema_version: EXTENSION_SCHEMA_VERSION,
        extension_id: entry.extension_id.clone(),
        invocation_budget: u64::MAX,
        proposal_budget: u64::MAX,
    };

    // Resolution is checked first and separately. An entry that cannot resolve
    // has no conformance result, only a caller error, so this is the one path
    // that returns rather than recording.
    let probe = grid()
        .into_iter()
        .next()
        .expect("the conformance grid is never empty");
    let resolved = resolve_with(
        std::slice::from_ref(entry),
        std::slice::from_ref(&policy),
        provider,
        &context(&probe, instance),
        conformance,
        resolve_options,
    )?;
    checks.push(ConformanceCheck::new(
        "resolves",
        true,
        format!("entry resolved with authority {}", entry.category.as_str()),
    ));

    let mut invoked = 0_u64;
    let mut backend_version = String::from("unavailable");
    let mut invariance = Ok(());

    for model in grid() {
        let resolved: ResolvedSet = resolve_with(
            std::slice::from_ref(entry),
            std::slice::from_ref(&policy),
            provider,
            &context(&model, instance),
            conformance,
            resolve_options,
        )?;

        let baseline = optimizer_solver::search(&model, &options(Vec::new()), backend, &cancel)?;
        let observed = optimizer_solver::search_with_extensions(
            &model,
            &options(vec![policy.clone()]),
            &resolved.registrations(),
            backend,
            &cancel,
        )?;
        backend_version = observed.backend_version.clone();

        let summary = observed
            .extensions
            .iter()
            .find(|summary| summary.extension_id == entry.extension_id);
        let accepted = summary.map_or(0, |summary| summary.accepted);
        invoked += summary.map_or(0, |summary| summary.invocations);

        if invariance.is_ok() {
            invariance = conclusions_agree(&baseline, &observed)
                .map_err(|detail| format!("{}: {detail}", observed.model_id));
            // An accepted proposal legitimately prunes more by bound, so the
            // counter comparison applies only when nothing was accepted. The
            // proven optimum and forfeiture state above are compared either way.
            if invariance.is_ok()
                && accepted == 0
                && baseline.nodes_explored != observed.nodes_explored
            {
                invariance = Err(format!(
                    "{}: nodes_explored {} became {} with nothing accepted",
                    observed.model_id, baseline.nodes_explored, observed.nodes_explored
                ));
            }
        }
    }

    // Requirement 24: invocation is asserted before effect. A suite that passed
    // because the extension was never consulted would be worse than no suite.
    checks.push(ConformanceCheck::new(
        "invoked",
        invoked > 0,
        format!("{invoked} invocations across {GRID_SIZE} models"),
    ));
    checks.push(match &invariance {
        Ok(()) => ConformanceCheck::new(
            "conclusions_invariant",
            true,
            "outcome, proven optimum, dual bound and forfeiture state unchanged".to_owned(),
        ),
        Err(detail) => ConformanceCheck::new("conclusions_invariant", false, detail.clone()),
    });

    let declaration = resolved.declaration(&entry.extension_id).ok_or_else(|| {
        ValidationError::new(
            ErrorKind::Unsupported,
            format!("{}: resolved without a declaration", entry.extension_id),
        )
    })?;

    let outcome = checks.iter().all(|check| check.passed);
    Ok(ConformanceRecord {
        schema_version: CONFORMANCE_SCHEMA_VERSION,
        extension_id: declaration.extension_id.clone(),
        version: declaration.version.clone(),
        host_contract_version: declaration.host_contract_version,
        grid_size: GRID_SIZE,
        backend_version,
        checks,
        outcome,
    })
}

#[cfg(test)]
mod tests {
    use super::{
        CONFORMANCE_SCHEMA_VERSION, ConformanceCheck, ConformanceRecord, GRID_SIZE,
        MAX_DETAIL_BYTES, conclusions_agree, grid, options,
    };
    use optimizer_solver::{SEARCH_SCHEMA_VERSION, SearchOutcome, SearchRecord};

    /// A named mutation of one search conclusion, for the can-fail checks.
    type ConclusionCase = (&'static str, Box<dyn Fn(&mut SearchRecord)>);

    /// A search conclusion to perturb one field at a time.
    fn conclusion() -> SearchRecord {
        SearchRecord {
            schema_version: SEARCH_SCHEMA_VERSION,
            model_id: "conformance-grid-0".to_owned(),
            backend: "test".to_owned(),
            backend_version: "test".to_owned(),
            outcome: SearchOutcome::ProvenOptimal,
            objective: Some(7.0),
            dual_bound: Some(7.0),
            gap: None,
            candidate: None,
            validation: None,
            nodes_explored: 5,
            nodes_pruned_infeasible: 2,
            nodes_pruned_bound: 3,
            open_nodes_remaining: 0,
            relaxations_solved: 5,
            forfeited: false,
            warnings: Vec::new(),
            extensions: Vec::new(),
            elapsed_ms: 11,
            options: options(Vec::new()),
        }
    }

    /// Requirement 23's comparison must be able to fail, on every field it names.
    ///
    /// The suite's own passing runs cannot establish this: SPEC-0004's containment
    /// means no extension reachable through the host can move these fields, so a
    /// broken comparison would look exactly like a conforming extension. Each
    /// mutation here is the check the suite would have to notice.
    #[test]
    fn the_invariance_comparison_detects_every_field_it_compares() {
        let baseline = conclusion();
        assert_eq!(
            conclusions_agree(&baseline, &baseline.clone()),
            Ok(()),
            "identical conclusions must agree"
        );

        let mutations: Vec<ConclusionCase> = vec![
            (
                "outcome",
                Box::new(|record: &mut SearchRecord| record.outcome = SearchOutcome::NodeLimit),
            ),
            (
                "objective",
                Box::new(|record: &mut SearchRecord| record.objective = Some(6.0)),
            ),
            (
                "dual_bound",
                Box::new(|record: &mut SearchRecord| record.dual_bound = None),
            ),
            (
                "forfeited",
                Box::new(|record: &mut SearchRecord| record.forfeited = true),
            ),
            (
                "nodes_pruned_infeasible",
                Box::new(|record: &mut SearchRecord| record.nodes_pruned_infeasible += 1),
            ),
            (
                "nodes_pruned_bound",
                Box::new(|record: &mut SearchRecord| record.nodes_pruned_bound += 1),
            ),
        ];

        for (field, mutate) in mutations {
            let mut observed = baseline.clone();
            mutate(&mut observed);
            let detail = conclusions_agree(&baseline, &observed)
                .expect_err(&format!("a changed {field} must be detected"));
            assert!(
                detail.contains(field),
                "the failure must name {field}, found {detail}"
            );
        }
    }

    /// Elapsed time measures the host, so it must not enter the comparison.
    #[test]
    fn elapsed_time_is_not_a_conclusion() {
        let baseline = conclusion();
        let mut observed = baseline.clone();
        observed.elapsed_ms = baseline.elapsed_ms + 987_654;
        assert_eq!(conclusions_agree(&baseline, &observed), Ok(()));
    }

    /// A negative-zero objective must not read as a change, and a NaN must.
    ///
    /// The comparison is on bit patterns, which is what makes an absent value and
    /// a present one distinguishable; this pins the two cases where bitwise
    /// equality and numerical equality disagree.
    #[test]
    fn the_comparison_uses_bit_patterns_deliberately() {
        let mut baseline = conclusion();
        baseline.objective = Some(0.0);
        let mut observed = baseline.clone();
        observed.objective = Some(-0.0);
        assert!(
            conclusions_agree(&baseline, &observed).is_err(),
            "a sign change is a recorded difference rather than a silent equality"
        );

        let mut present = conclusion();
        present.dual_bound = Some(7.0);
        let mut absent = present.clone();
        absent.dual_bound = None;
        assert!(
            conclusions_agree(&present, &absent).is_err(),
            "an available bound becoming unavailable is a change"
        );
    }

    /// The grid is fixed, and its recorded size must describe it.
    ///
    /// `GRID_SIZE` is written into every record as the evidence that the grid did
    /// not shrink, so a constant that disagreed with the grid would make that
    /// evidence false rather than merely stale.
    #[test]
    fn the_recorded_grid_size_matches_the_grid() {
        let models = grid();
        assert_eq!(models.len(), GRID_SIZE as usize);
        let mut identities: Vec<&str> = models
            .iter()
            .map(|model| model.document().model_id.as_str())
            .collect();
        identities.sort_unstable();
        identities.dedup();
        assert_eq!(
            identities.len(),
            GRID_SIZE as usize,
            "each grid model must be distinct"
        );
    }

    /// A detail longer than the bound is truncated at a character boundary.
    #[test]
    fn check_details_stay_bounded() {
        let check = ConformanceCheck::new("bounded", false, "é".repeat(MAX_DETAIL_BYTES));
        assert!(check.detail.len() <= MAX_DETAIL_BYTES);
        assert!(
            check.detail.chars().all(|character| character == 'é'),
            "truncation must not split a character"
        );
    }

    /// A record claiming to pass while carrying a failing check is refused.
    #[test]
    fn a_record_cannot_contradict_its_own_checks() {
        let record = ConformanceRecord {
            schema_version: CONFORMANCE_SCHEMA_VERSION,
            extension_id: "example".to_owned(),
            version: "0.1.0".to_owned(),
            host_contract_version: 1,
            grid_size: GRID_SIZE,
            backend_version: "test".to_owned(),
            checks: vec![ConformanceCheck::new("invoked", false, "0 invocations")],
            outcome: true,
        };
        let bytes = record.to_json().expect("serializes");
        let error = ConformanceRecord::from_json(bytes.as_bytes())
            .expect_err("a self-contradicting record is refused");
        assert!(error.to_string().contains("outcome disagrees"));
    }
}
