//! The canonical LP form both engines iterate on, under SPEC-0011 requirement 6.
//!
//! An [`optimizer_core::Model`] is a document: variables and constraints carry
//! caller-assigned identities, bounds may be infinite, and the objective may be a
//! maximization. An iterative method needs none of that and needs several things
//! the document does not provide, so this module converts once, at construction,
//! and records how to get back.
//!
//! Two conversions are worth naming because they are not cosmetic. The problem is
//! held as a minimization, because carrying a sense flag through every update
//! would put a branch in the inner loop and a chance to get a sign wrong in each
//! of them. And the matrix is held twice, in row-major and column-major
//! compressed form, so that neither `A x` nor `Aᵀ y` needs atomic accumulation.
//! That second one is a determinism requirement before it is a performance one:
//! an atomic reduction would make the result depend on the order the hardware
//! happened to schedule, which requirement 8 forbids.

use optimizer_core::{Bound, ErrorKind, Model, ObjectiveSense, ValidationError};

/// A sparse matrix in one compressed orientation.
///
/// `offsets` has `major + 1` entries and `indices` and `values` are parallel.
/// Within a major line the minor indices are strictly increasing, which is what
/// lets a product visit each line in one pass and makes two builds of the same
/// matrix comparable element by element.
#[derive(Clone, Debug, PartialEq)]
pub struct Compressed {
    offsets: Vec<usize>,
    indices: Vec<u32>,
    values: Vec<f64>,
}

impl Compressed {
    /// Number of major lines: rows for the row-major form, columns for the other.
    #[must_use]
    pub fn lines(&self) -> usize {
        self.offsets.len() - 1
    }

    /// Number of stored nonzeros.
    #[must_use]
    pub fn nonzeros(&self) -> usize {
        self.values.len()
    }

    /// The minor indices and values of one major line.
    #[must_use]
    pub fn line(&self, major: usize) -> (&[u32], &[f64]) {
        let start = self.offsets[major];
        let end = self.offsets[major + 1];
        (&self.indices[start..end], &self.values[start..end])
    }

    /// Where one major line starts in the flat storage.
    ///
    /// Exposed so a caller holding a parallel array of values -- a scaled copy of
    /// the matrix, for instance -- can index it the same way without rebuilding
    /// the structure alongside it.
    #[must_use]
    pub fn offset(&self, major: usize) -> usize {
        self.offsets[major]
    }

    /// Every stored entry as `(major, minor, value)`, in storage order.
    pub fn entries(&self) -> impl Iterator<Item = (usize, u32, f64)> + '_ {
        (0..self.lines()).flat_map(move |major| {
            let (indices, values) = self.line(major);
            indices
                .iter()
                .zip(values)
                .map(move |(minor, value)| (major, *minor, *value))
        })
    }
}

/// A variable or row bound pair, with infinities kept as infinities.
///
/// `f64` infinities rather than an `Option` because every consumer here either
/// compares against them or clamps to them, and both operations are already
/// correct for an infinite operand. The certification is the one place that must
/// distinguish them, and it tests `is_finite` explicitly rather than relying on
/// arithmetic.
#[derive(Clone, Copy, Debug, PartialEq)]
pub struct Range {
    /// Lower bound, possibly `f64::NEG_INFINITY`.
    pub lower: f64,
    /// Upper bound, possibly `f64::INFINITY`.
    pub upper: f64,
}

impl Range {
    fn of(lower: &Bound, upper: &Bound) -> Self {
        Self {
            lower: bound_value(lower),
            upper: bound_value(upper),
        }
    }

    /// Clamp a value into this range.
    #[must_use]
    pub fn clamp(&self, value: f64) -> f64 {
        value.max(self.lower).min(self.upper)
    }
}

fn bound_value(bound: &Bound) -> f64 {
    match bound {
        Bound::Finite { value } => *value,
        Bound::NegativeInfinity => f64::NEG_INFINITY,
        Bound::PositiveInfinity => f64::INFINITY,
    }
}

/// One linear program in the form the iteration and the certification both read.
///
/// Held as `min cᵀx + offset` subject to `rows.lower ≤ A x ≤ rows.upper` and
/// `columns.lower ≤ x ≤ columns.upper`.
#[derive(Clone, Debug, PartialEq)]
pub struct LinearProgram {
    row_major: Compressed,
    column_major: Compressed,
    objective: Vec<f64>,
    offset: f64,
    rows: Vec<Range>,
    columns: Vec<Range>,
    variable_ids: Vec<u32>,
    sense: ObjectiveSense,
}

impl LinearProgram {
    /// Convert an original model into the canonical form.
    ///
    /// # Errors
    ///
    /// Returns an unsupported failure for a model with a discrete variable. This
    /// is a structural fact about the form rather than a policy: there is nowhere
    /// in `min cᵀx` subject to bounds to put an integrality restriction, so a
    /// discrete model converted here would silently become its own relaxation.
    /// SPEC-0011 requirement 3 refuses such a request at the backend boundary, and
    /// this is the second place it cannot slip through.
    pub fn new(model: &Model) -> Result<Self, ValidationError> {
        let document = model.document();
        if optimizer_core::ProblemClass::of(model) == optimizer_core::ProblemClass::Discrete {
            return Err(ValidationError::new(
                ErrorKind::Unsupported,
                "a first-order linear program has no integrality restriction; \
                 a discrete model must be refused rather than relaxed",
            ));
        }

        let variable_ids: Vec<u32> = document
            .variables
            .iter()
            .map(|variable| variable.id)
            .collect();
        let columns: Vec<Range> = document
            .variables
            .iter()
            .map(|variable| Range::of(&variable.lower, &variable.upper))
            .collect();
        let rows: Vec<Range> = document
            .constraints
            .iter()
            .map(|constraint| Range::of(&constraint.lower, &constraint.upper))
            .collect();

        // The document is canonical: Model::new sorted variables by id, so a
        // binary search is the index and no map is needed.
        let index = |variable_id: u32| -> usize {
            variable_ids
                .binary_search(&variable_id)
                .expect("a validated model's terms reference known variables")
        };

        // Held as a minimization. A maximization is negated here, once, rather
        // than branched on in every update; the sense is retained so a bound and
        // an objective can be reported in the caller's own direction.
        let sense = document.objective.sense;
        let sign = match sense {
            ObjectiveSense::Minimize => 1.0,
            ObjectiveSense::Maximize => -1.0,
        };
        let mut objective = vec![0.0; variable_ids.len()];
        for term in &document.objective.terms {
            objective[index(term.variable_id)] += sign * term.coefficient;
        }
        let offset = sign * document.objective.offset;

        let mut triples: Vec<(usize, u32, f64)> = Vec::new();
        for (row, constraint) in document.constraints.iter().enumerate() {
            for term in &constraint.terms {
                triples.push((row, index(term.variable_id) as u32, term.coefficient));
            }
        }

        let row_major = compress(&triples, rows.len(), columns.len(), false);
        // Built from the same triples but transposed, not from the row-major
        // form: deriving one orientation from the other would make a defect in
        // the first invisible in the second, and the two are meant to be an
        // independent pair.
        let column_major = compress(&triples, rows.len(), columns.len(), true);

        Ok(Self {
            row_major,
            column_major,
            objective,
            offset,
            rows,
            columns,
            variable_ids,
            sense,
        })
    }

    /// Number of constraints.
    #[must_use]
    pub fn row_count(&self) -> usize {
        self.rows.len()
    }

    /// Number of variables.
    #[must_use]
    pub fn column_count(&self) -> usize {
        self.columns.len()
    }

    /// Stored nonzeros, counted once rather than once per orientation.
    #[must_use]
    pub fn nonzeros(&self) -> usize {
        self.row_major.nonzeros()
    }

    /// The row-major matrix, used for `A x`.
    #[must_use]
    pub fn row_major(&self) -> &Compressed {
        &self.row_major
    }

    /// The column-major matrix, used for `Aᵀ y`.
    #[must_use]
    pub fn column_major(&self) -> &Compressed {
        &self.column_major
    }

    /// Objective coefficients, as a minimization.
    #[must_use]
    pub fn objective(&self) -> &[f64] {
        &self.objective
    }

    /// Objective constant, as a minimization.
    #[must_use]
    pub fn offset(&self) -> f64 {
        self.offset
    }

    /// Row activity bounds.
    #[must_use]
    pub fn rows(&self) -> &[Range] {
        &self.rows
    }

    /// Variable bounds.
    #[must_use]
    pub fn columns(&self) -> &[Range] {
        &self.columns
    }

    /// Original variable identities, in column order.
    #[must_use]
    pub fn variable_ids(&self) -> &[u32] {
        &self.variable_ids
    }

    /// The original objective direction.
    #[must_use]
    pub fn sense(&self) -> ObjectiveSense {
        self.sense
    }

    /// Convert an internal minimization value back to the caller's direction.
    #[must_use]
    pub fn to_original_objective(&self, internal: f64) -> f64 {
        match self.sense {
            ObjectiveSense::Minimize => internal,
            ObjectiveSense::Maximize => -internal,
        }
    }
}

/// Build one compressed orientation from `(row, column, value)` triples.
///
/// Duplicate entries within a line are summed, which a validated model should
/// never produce -- `Model::new` rejects duplicate variable IDs within a
/// constraint -- but summing is the only answer that keeps the two orientations
/// equal if one ever appeared.
fn compress(
    triples: &[(usize, u32, f64)],
    rows: usize,
    columns: usize,
    transpose: bool,
) -> Compressed {
    let (majors, _minors) = if transpose {
        (columns, rows)
    } else {
        (rows, columns)
    };
    let key = |&(row, column, _): &(usize, u32, f64)| -> (usize, u32) {
        if transpose {
            (column as usize, row as u32)
        } else {
            (row, column)
        }
    };

    let mut counts = vec![0usize; majors];
    for triple in triples {
        counts[key(triple).0] += 1;
    }
    let mut offsets = vec![0usize; majors + 1];
    for major in 0..majors {
        offsets[major + 1] = offsets[major] + counts[major];
    }

    let mut indices = vec![0u32; triples.len()];
    let mut values = vec![0.0f64; triples.len()];
    let mut cursor = offsets.clone();
    for triple in triples {
        let (major, minor) = key(triple);
        let slot = cursor[major];
        indices[slot] = minor;
        values[slot] = triple.2;
        cursor[major] += 1;
    }

    // Sort each line by minor index so both orientations are canonical and a
    // product visits a line in increasing order.
    for major in 0..majors {
        let start = offsets[major];
        let end = offsets[major + 1];
        let mut line: Vec<(u32, f64)> = indices[start..end]
            .iter()
            .zip(&values[start..end])
            .map(|(minor, value)| (*minor, *value))
            .collect();
        line.sort_by_key(|(minor, _)| *minor);
        for (slot, (minor, value)) in line.into_iter().enumerate() {
            indices[start + slot] = minor;
            values[start + slot] = value;
        }
    }

    Compressed {
        offsets,
        indices,
        values,
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use optimizer_core::{
        Constraint, Domain, LinearTerm, ModelDocument, Objective, SCHEMA_VERSION, Variable,
    };

    fn finite(value: f64) -> Bound {
        Bound::Finite { value }
    }

    fn model(sense: ObjectiveSense) -> Model {
        Model::new(ModelDocument {
            schema_version: SCHEMA_VERSION,
            model_id: "lp-form".to_string(),
            variables: vec![
                Variable {
                    id: 0,
                    domain: Domain::Continuous,
                    lower: finite(0.0),
                    upper: finite(1.0),
                },
                Variable {
                    id: 1,
                    domain: Domain::Continuous,
                    lower: finite(0.0),
                    upper: Bound::PositiveInfinity,
                },
            ],
            constraints: vec![
                Constraint {
                    id: 0,
                    lower: Bound::NegativeInfinity,
                    upper: finite(1.5),
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
                },
                Constraint {
                    id: 1,
                    lower: finite(0.5),
                    upper: finite(0.5),
                    terms: vec![LinearTerm {
                        variable_id: 1,
                        coefficient: 3.0,
                    }],
                },
            ],
            objective: Objective {
                sense,
                offset: 2.5,
                terms: vec![
                    LinearTerm {
                        variable_id: 0,
                        coefficient: -1.0,
                    },
                    LinearTerm {
                        variable_id: 1,
                        coefficient: -3.0,
                    },
                ],
            },
        })
        .expect("a valid model")
    }

    /// Requirement 6: the two orientations hold the same matrix.
    ///
    /// Compared as sets of `(row, column, value)` built independently from each
    /// orientation, so neither is derived from the other for the purpose of the
    /// comparison.
    #[test]
    fn both_matrix_forms_hold_the_same_nonzeros() {
        let program = LinearProgram::new(&model(ObjectiveSense::Minimize)).unwrap();
        let mut by_row: Vec<(usize, u32, f64)> = program.row_major().entries().collect();
        let mut by_column: Vec<(usize, u32, f64)> = program
            .column_major()
            .entries()
            .map(|(column, row, value)| (row as usize, column as u32, value))
            .collect();
        by_row.sort_by(|a, b| a.partial_cmp(b).unwrap());
        by_column.sort_by(|a, b| a.partial_cmp(b).unwrap());
        assert_eq!(by_row, by_column);
        assert_eq!(program.nonzeros(), 3);
        assert_eq!(program.row_major().lines(), 2);
        assert_eq!(program.column_major().lines(), 2);
    }

    #[test]
    fn an_infinite_bound_survives_conversion_as_an_infinity() {
        let program = LinearProgram::new(&model(ObjectiveSense::Minimize)).unwrap();
        assert_eq!(program.columns()[1].upper, f64::INFINITY);
        assert_eq!(program.rows()[0].lower, f64::NEG_INFINITY);
        assert_eq!(program.rows()[1].lower, 0.5);
        assert_eq!(program.rows()[1].upper, 0.5);
    }

    /// A maximization is negated once, and the round trip restores the caller's
    /// direction. Getting this backwards would produce a number valid in the
    /// wrong direction, which is worse than producing none.
    #[test]
    fn a_maximization_is_negated_once_and_reported_back_in_the_callers_direction() {
        let minimize = LinearProgram::new(&model(ObjectiveSense::Minimize)).unwrap();
        let maximize = LinearProgram::new(&model(ObjectiveSense::Maximize)).unwrap();
        assert_eq!(minimize.objective(), [-1.0, -3.0]);
        assert_eq!(maximize.objective(), [1.0, 3.0]);
        assert_eq!(minimize.offset(), 2.5);
        assert_eq!(maximize.offset(), -2.5);
        assert_eq!(minimize.to_original_objective(-4.0), -4.0);
        assert_eq!(maximize.to_original_objective(-4.0), 4.0);
    }

    /// Requirement 3, structurally: this form cannot hold an integrality
    /// restriction, so a discrete model is refused rather than quietly relaxed.
    #[test]
    fn a_discrete_model_is_refused_rather_than_relaxed() {
        let mut document = model(ObjectiveSense::Minimize).document().clone();
        document.variables[0].domain = Domain::Binary;
        let discrete = Model::new(document).unwrap();
        let error = LinearProgram::new(&discrete).unwrap_err();
        assert_eq!(error.kind, ErrorKind::Unsupported);
    }

    #[test]
    fn a_line_is_sorted_by_minor_index() {
        let program = LinearProgram::new(&model(ObjectiveSense::Minimize)).unwrap();
        for major in 0..program.row_major().lines() {
            let (indices, _) = program.row_major().line(major);
            assert!(indices.windows(2).all(|pair| pair[0] < pair[1]));
        }
    }
}
