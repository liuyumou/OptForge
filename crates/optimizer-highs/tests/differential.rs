//! Differential acceptance against the standalone pinned HiGHS executable.
//!
//! SPEC-0002 requires comparing the adapter with an independent reference built
//! from the same pinned source. The executable is driven as a separate process
//! over generated LP files, so agreement is evidence about the adapter rather
//! than a restatement of its own code path.
//!
//! Disagreement fails the test; it is never resolved by trusting the adapter.

use std::path::PathBuf;
use std::process::Command;

use optimizer_core::{
    Backend, Bound, Constraint, Domain, LinearTerm, Model, ModelDocument, Objective,
    ObjectiveSense, SOLVE_SCHEMA_VERSION, SolveOptions, Termination, Tolerances, Variable,
};
use optimizer_highs::{HighsBackend, is_native};

/// Absolute install prefix. It must not depend on the current directory,
/// because the reference executable is run inside a sandbox directory.
fn install_prefix() -> PathBuf {
    let prefix = std::env::var_os("AI_OPTIMIZER_HIGHS_DIR").map_or_else(
        || {
            PathBuf::from(env!("CARGO_MANIFEST_DIR"))
                .join("../..")
                .join("target/native/highs-1.11.0/install")
        },
        PathBuf::from,
    );
    prefix.canonicalize().unwrap_or(prefix)
}

fn options() -> SolveOptions {
    SolveOptions {
        schema_version: SOLVE_SCHEMA_VERSION,
        seed: 17,
        time_limit_ms: None,
        iteration_limit: None,
        node_limit: None,
        tolerances: Tolerances {
            absolute: 1e-9,
            relative: 1e-9,
            integrality: 1e-9,
        },
        threads: 1,
    }
}

/// Write the original model as a CPLEX LP file in original ID order.
///
/// Only the constructs these fixtures use are emitted; anything else would make
/// the reference disagree for the wrong reason.
fn write_lp(model: &Model) -> String {
    let document = model.document();
    let mut lp = String::new();
    lp.push_str(match document.objective.sense {
        ObjectiveSense::Minimize => "Minimize\n obj:",
        ObjectiveSense::Maximize => "Maximize\n obj:",
    });
    for term in &document.objective.terms {
        lp.push_str(&format!(" {:+} x{}", term.coefficient, term.variable_id));
    }
    if document.objective.offset != 0.0 {
        lp.push_str(&format!(" {:+}", document.objective.offset));
    }
    lp.push_str("\nSubject To\n");
    for constraint in &document.constraints {
        let mut expression = String::new();
        for term in &constraint.terms {
            expression.push_str(&format!(" {:+} x{}", term.coefficient, term.variable_id));
        }
        match (constraint.lower, constraint.upper) {
            (Bound::Finite { value: lower }, Bound::Finite { value: upper }) => {
                if lower == upper {
                    lp.push_str(&format!(" c{}:{expression} = {lower}\n", constraint.id));
                } else {
                    // Ranged rows are expressed as the two implied inequalities.
                    lp.push_str(&format!(" c{}l:{expression} >= {lower}\n", constraint.id));
                    lp.push_str(&format!(" c{}u:{expression} <= {upper}\n", constraint.id));
                }
            }
            (Bound::Finite { value: lower }, _) => {
                lp.push_str(&format!(" c{}:{expression} >= {lower}\n", constraint.id));
            }
            (_, Bound::Finite { value: upper }) => {
                lp.push_str(&format!(" c{}:{expression} <= {upper}\n", constraint.id));
            }
            _ => {}
        }
    }
    lp.push_str("Bounds\n");
    for variable in &document.variables {
        let lower = match variable.lower {
            Bound::Finite { value } => value.to_string(),
            _ => "-1e30".to_string(),
        };
        let upper = match variable.upper {
            Bound::Finite { value } => value.to_string(),
            _ => "1e30".to_string(),
        };
        lp.push_str(&format!(" {lower} <= x{} <= {upper}\n", variable.id));
    }
    let discrete: Vec<String> = document
        .variables
        .iter()
        .filter(|variable| variable.domain != Domain::Continuous)
        .map(|variable| format!("x{}", variable.id))
        .collect();
    if !discrete.is_empty() {
        lp.push_str(&format!("General\n {}\n", discrete.join(" ")));
    }
    lp.push_str("End\n");
    lp
}

/// Reference outcome parsed from the standalone executable's own output.
struct Reference {
    status: String,
    objective: Option<f64>,
}

fn run_standalone(model: &Model, name: &str) -> Reference {
    let directory = std::env::temp_dir().join(format!(
        "ai-optimizer-differential-{}-{name}",
        std::process::id()
    ));
    std::fs::create_dir_all(&directory).expect("temporary directory");
    let path = directory.join("model.lp");
    std::fs::write(&path, write_lp(model)).expect("write lp");

    // The reference runs single-threaded with the same seed as the adapter.
    // `threads` is not a command-line flag, so it goes through an options file.
    // The log file is redirected into the sandbox because the executable
    // otherwise writes HiGHS.log into the current working directory.
    let options_path = directory.join("highs.opt");
    std::fs::write(
        &options_path,
        format!(
            "threads = 1\nlog_to_console = false\nlog_file = {}\n",
            directory.join("highs.log").display()
        ),
    )
    .expect("write options");
    let solution_path = directory.join("model.sol");

    let output = Command::new(install_prefix().join("bin/highs"))
        .arg("--solver")
        .arg("choose")
        .arg("--random_seed")
        .arg("17")
        .arg("--options_file")
        .arg(&options_path)
        .arg("--solution_file")
        .arg(&solution_path)
        .arg("--model_file")
        .arg(&path)
        // Run in the sandbox so any stray native output stays out of the tree.
        .current_dir(&directory)
        .output()
        .expect("run standalone highs");
    // The written solution file has one stable shape across LP, MILP and
    // infeasible runs, unlike the human-readable log.
    let text = std::fs::read_to_string(&solution_path).unwrap_or_else(|error| {
        panic!(
            "{name}: standalone highs wrote no solution file ({error}):\n{}",
            String::from_utf8_lossy(&output.stdout)
        )
    });
    std::fs::remove_dir_all(&directory).ok();

    let mut lines = text.lines().map(str::trim);
    let status = lines
        .find(|line| *line == "Model status")
        .and_then(|_| lines.next())
        .unwrap_or_else(|| panic!("{name}: no model status in solution file:\n{text}"))
        .to_string();
    let objective = text.lines().find_map(|line| {
        line.trim()
            .strip_prefix("Objective ")
            .and_then(|value| value.trim().parse().ok())
    });
    Reference { status, objective }
}

/// Map the reference status text onto the engine's own termination vocabulary.
fn expected(status: &str) -> Termination {
    match status {
        "Optimal" => Termination::Optimal,
        "Infeasible" => Termination::Infeasible,
        "Unbounded" => Termination::Unbounded,
        "Unbounded or infeasible" => Termination::UnboundedOrInfeasible,
        other => panic!("unexpected reference status {other}"),
    }
}

fn finite(value: f64) -> Bound {
    Bound::Finite { value }
}

fn build(
    model_id: &str,
    domain: Domain,
    upper: Bound,
    row: (Bound, Bound),
    costs: [f64; 2],
    offset: f64,
) -> Model {
    Model::new(ModelDocument {
        schema_version: optimizer_core::SCHEMA_VERSION,
        model_id: model_id.to_string(),
        variables: vec![
            Variable {
                id: 0,
                domain,
                lower: finite(0.0),
                upper,
            },
            Variable {
                id: 1,
                domain,
                lower: finite(0.0),
                upper,
            },
        ],
        constraints: vec![Constraint {
            id: 0,
            lower: row.0,
            upper: row.1,
            terms: vec![
                LinearTerm {
                    variable_id: 0,
                    coefficient: 1.0,
                },
                LinearTerm {
                    variable_id: 1,
                    coefficient: 2.0,
                },
            ],
        }],
        objective: Objective {
            sense: ObjectiveSense::Minimize,
            offset,
            terms: vec![
                LinearTerm {
                    variable_id: 0,
                    coefficient: costs[0],
                },
                LinearTerm {
                    variable_id: 1,
                    coefficient: costs[1],
                },
            ],
        },
    })
    .expect("model")
}

// Requirements 4 and 8: the adapter and the independent reference agree on
// status and objective for every generated case.
#[test]
fn adapter_agrees_with_the_standalone_executable() {
    if !is_native() {
        eprintln!(
            "SKIP adapter_agrees_with_the_standalone_executable: \
             HiGHS not provisioned; run bash tools/setup_highs.sh"
        );
        return;
    }
    assert!(
        install_prefix().join("bin/highs").is_file(),
        "the standalone reference executable is required for differential acceptance"
    );

    let cases = vec![
        (
            "lp-upper",
            build(
                "lp-upper",
                Domain::Continuous,
                finite(1.0),
                (Bound::NegativeInfinity, finite(1.5)),
                [-1.0, -1.0],
                0.0,
            ),
        ),
        (
            "lp-offset",
            build(
                "lp-offset",
                Domain::Continuous,
                finite(1.0),
                (Bound::NegativeInfinity, finite(1.5)),
                [-1.0, -3.0],
                2.5,
            ),
        ),
        (
            "lp-equality",
            build(
                "lp-equality",
                Domain::Continuous,
                finite(1.0),
                (finite(1.0), finite(1.0)),
                [1.0, 1.0],
                0.0,
            ),
        ),
        (
            "lp-ranged",
            build(
                "lp-ranged",
                Domain::Continuous,
                finite(1.0),
                (finite(0.5), finite(1.5)),
                [-2.0, 1.0],
                0.0,
            ),
        ),
        (
            "milp-general",
            build(
                "milp-general",
                Domain::Integer,
                finite(3.0),
                (Bound::NegativeInfinity, finite(4.5)),
                [-1.0, -1.0],
                0.0,
            ),
        ),
        (
            "lp-infeasible",
            build(
                "lp-infeasible",
                Domain::Continuous,
                finite(1.0),
                (finite(7.0), Bound::PositiveInfinity),
                [1.0, 1.0],
                0.0,
            ),
        ),
    ];

    let backend = HighsBackend::new();
    for (name, model) in cases {
        let reference = run_standalone(&model, name);
        let record = backend
            .solve(
                &model,
                &options(),
                &optimizer_core::CancellationToken::new(),
                None,
            )
            .unwrap_or_else(|error| panic!("{name}: adapter failed: {error}"));

        assert_eq!(
            record.termination,
            expected(&reference.status),
            "{name}: adapter and reference disagree on status (reference {})",
            reference.status
        );

        match (record.objective, reference.objective) {
            (Some(adapter), Some(expected)) => assert!(
                (adapter - expected).abs() <= 1e-6 * expected.abs().max(1.0),
                "{name}: objective disagreement, adapter {adapter} vs reference {expected}"
            ),
            (None, _) => assert!(
                !record.termination.is_complete()
                    || matches!(
                        record.termination,
                        Termination::Infeasible
                            | Termination::Unbounded
                            | Termination::UnboundedOrInfeasible
                    ),
                "{name}: a completed solve must publish an objective"
            ),
            (Some(adapter), None) => {
                panic!("{name}: adapter reported {adapter} where the reference reported none")
            }
        }
    }
}
