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

use optimizer_core::{Bound, ErrorKind, Model, ObjectiveSense, ValidationError, Variable};

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

/// The column bound pairs of a canonical variable list.
///
/// Shared by [`LinearProgram::new`] and [`LinearProgram::with_variable_bounds`]
/// so the two cannot diverge on what a bound becomes.
fn column_bounds(variables: &[Variable]) -> Vec<Range> {
    variables
        .iter()
        .map(|variable| Range::of(&variable.lower, &variable.upper))
        .collect()
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
        let _component_scope = optimizer_core::lp_cost::scope("sparse_operator_construction");
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
        let columns: Vec<Range> = column_bounds(&document.variables);
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

    /// This program with its variable bounds replaced by a variant model's.
    ///
    /// The variant supplies column bounds and nothing else: the matrix in both
    /// orientations, the objective, the objective constant, the row bounds, the
    /// variable identities and the sense are this program's, cloned. That is
    /// [`Model::rebound`]'s contract one level down — a SPEC-0014 batch variant
    /// changes bounds only, so its canonical form differs from this program
    /// only in `columns`, and rebuilding one through [`LinearProgram::new`]
    /// would redo the compression and the term indexing for data that already
    /// passed them. When the variant differs only in column bounds, the result
    /// is exactly what `LinearProgram::new` of the variant would produce.
    ///
    /// The identity check is the same one `Model::rebound` makes, and it is
    /// load-bearing rather than ceremonial: the cloned matrix's columns are
    /// indexed by position, so a variant naming different variables would apply
    /// its bounds to the wrong columns. Both lists are sorted by id —
    /// `Model::new` canonicalizes — so equal lengths and pairwise-equal ids are
    /// set equality.
    ///
    /// # Errors
    ///
    /// Returns an unsupported failure when the variant's variable IDs are not
    /// exactly this program's.
    pub fn with_variable_bounds(&self, variant: &Model) -> Result<Self, ValidationError> {
        let variables = &variant.document().variables;
        let same_ids = variables.len() == self.variable_ids.len()
            && variables
                .iter()
                .zip(&self.variable_ids)
                .all(|(variable, id)| variable.id == *id);
        if !same_ids {
            return Err(ValidationError::new(
                ErrorKind::Unsupported,
                "a bounds variant must name exactly the program's variable IDs",
            ));
        }
        Ok(Self {
            row_major: self.row_major.clone(),
            column_major: self.column_major.clone(),
            objective: self.objective.clone(),
            offset: self.offset,
            rows: self.rows.clone(),
            columns: column_bounds(variables),
            variable_ids: self.variable_ids.clone(),
            sense: self.sense,
        })
    }

    /// Whether two programs share everything a repeated solve may reuse.
    ///
    /// Field-wise equality of the matrix in both orientations, the objective,
    /// the objective constant, the row bounds, the variable identities and the
    /// sense — every field except `columns`. SPEC-0014 requirement 11 admits a
    /// batch variant by this check: it is the difference between "same solve,
    /// new variable bounds" and a different solve, which a session must refuse.
    #[must_use]
    pub fn same_matrix_objective_rows(&self, other: &Self) -> bool {
        self.row_major == other.row_major
            && self.column_major == other.column_major
            && self.objective == other.objective
            && self.offset == other.offset
            && self.rows == other.rows
            && self.variable_ids == other.variable_ids
            && self.sense == other.sense
    }

    /// A SHA-256 commitment to the whole canonical program.
    ///
    /// Hashed over one canonical little-endian serialization: the row and
    /// column counts as `u64`; each matrix orientation's offsets as `u64`,
    /// minor indices as `u32` and values as their `f64` bit patterns; the
    /// objective coefficients and constant as bit patterns; both bound sets as
    /// bit patterns, lower then upper, rows then columns; the variable
    /// identities as `u32`; and a one-byte sense tag. Lengths need no framing
    /// of their own: the counts fix every vector's length, since each
    /// orientation's offsets end at its nonzero count.
    ///
    /// The name is about identity, not exclusion: the digest commits to the
    /// full program *including* both bound sets, so a bounds-only variant
    /// hashes differently. Evidence names a solve by this digest; the reuse
    /// decision is [`Self::same_matrix_objective_rows`]'s, and the two are
    /// deliberately separate.
    #[must_use]
    pub fn matrix_sha256(&self) -> String {
        let _component_scope = optimizer_core::lp_cost::scope("operator_hash");
        let mut bytes = Vec::new();
        bytes.extend_from_slice(&(self.row_count() as u64).to_le_bytes());
        bytes.extend_from_slice(&(self.column_count() as u64).to_le_bytes());
        for form in [&self.row_major, &self.column_major] {
            for offset in &form.offsets {
                bytes.extend_from_slice(&(*offset as u64).to_le_bytes());
            }
            for index in &form.indices {
                bytes.extend_from_slice(&index.to_le_bytes());
            }
            for value in &form.values {
                bytes.extend_from_slice(&value.to_bits().to_le_bytes());
            }
        }
        for coefficient in &self.objective {
            bytes.extend_from_slice(&coefficient.to_bits().to_le_bytes());
        }
        bytes.extend_from_slice(&self.offset.to_bits().to_le_bytes());
        for range in self.rows.iter().chain(&self.columns) {
            bytes.extend_from_slice(&range.lower.to_bits().to_le_bytes());
            bytes.extend_from_slice(&range.upper.to_bits().to_le_bytes());
        }
        for id in &self.variable_ids {
            bytes.extend_from_slice(&id.to_le_bytes());
        }
        bytes.push(match self.sense {
            ObjectiveSense::Minimize => 0,
            ObjectiveSense::Maximize => 1,
        });
        optimizer_core::sha256::hex(&bytes)
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
    let _component_scope = optimizer_core::lp_cost::scope("sparse_compression");
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

    /// A bounds-only variant converted through the program is exactly a fresh
    /// conversion of the variant model — the construction is a shortcut, not a
    /// different result.
    #[test]
    fn with_variable_bounds_matches_a_fresh_conversion_of_a_bounds_only_variant() {
        let base = model(ObjectiveSense::Minimize);
        let program = LinearProgram::new(&base).unwrap();
        let mut tightened = base.document().variables.clone();
        tightened[0].lower = finite(0.25);
        tightened[1].upper = finite(4.0);
        let variant = base.rebound(tightened).unwrap();
        let rebound = program.with_variable_bounds(&variant).unwrap();
        assert_eq!(rebound, LinearProgram::new(&variant).unwrap());
        assert_eq!(
            rebound.columns(),
            [
                Range {
                    lower: 0.25,
                    upper: 1.0
                },
                Range {
                    lower: 0.0,
                    upper: 4.0
                },
            ]
        );
        assert!(rebound.same_matrix_objective_rows(&program));
    }

    #[test]
    fn with_variable_bounds_accepts_a_model_with_identical_bounds() {
        let base = model(ObjectiveSense::Minimize);
        let program = LinearProgram::new(&base).unwrap();
        assert_eq!(program.with_variable_bounds(&base).unwrap(), program);
    }

    /// The identity check mirrors `Model::rebound`'s: a variant that names
    /// different variables — by membership or by count — is refused, because
    /// the cloned matrix's columns are indexed by position.
    #[test]
    fn with_variable_bounds_refuses_a_different_variable_id_set() {
        let program = LinearProgram::new(&model(ObjectiveSense::Minimize)).unwrap();

        let mut renamed = model(ObjectiveSense::Minimize).document().clone();
        renamed.variables[1].id = 7;
        for constraint in &mut renamed.constraints {
            for term in &mut constraint.terms {
                if term.variable_id == 1 {
                    term.variable_id = 7;
                }
            }
        }
        for term in &mut renamed.objective.terms {
            if term.variable_id == 1 {
                term.variable_id = 7;
            }
        }
        let renamed = Model::new(renamed).unwrap();
        let error = program.with_variable_bounds(&renamed).unwrap_err();
        assert_eq!(error.kind, ErrorKind::Unsupported);

        let mut wider = model(ObjectiveSense::Minimize).document().clone();
        wider.variables.push(Variable {
            id: 2,
            domain: Domain::Continuous,
            lower: finite(0.0),
            upper: finite(1.0),
        });
        let wider = Model::new(wider).unwrap();
        let error = program.with_variable_bounds(&wider).unwrap_err();
        assert_eq!(error.kind, ErrorKind::Unsupported);
    }

    #[test]
    fn same_matrix_objective_rows_ignores_column_bounds_only() {
        let base = model(ObjectiveSense::Minimize);
        let program = LinearProgram::new(&base).unwrap();
        assert!(program.same_matrix_objective_rows(&program));

        let mut tightened = base.document().variables.clone();
        tightened[0].upper = finite(0.5);
        let variant = base.rebound(tightened).unwrap();
        let bounds_only = LinearProgram::new(&variant).unwrap();
        assert!(program.same_matrix_objective_rows(&bounds_only));

        let mut coefficient = base.document().clone();
        coefficient.constraints[0].terms[0].coefficient = 1.5;
        let coefficient = LinearProgram::new(&Model::new(coefficient).unwrap()).unwrap();
        assert!(!program.same_matrix_objective_rows(&coefficient));

        let mut row = base.document().clone();
        row.constraints[0].upper = finite(1.75);
        let row = LinearProgram::new(&Model::new(row).unwrap()).unwrap();
        assert!(!program.same_matrix_objective_rows(&row));

        let mut objective = base.document().clone();
        objective.objective.terms[0].coefficient = -1.5;
        let objective = LinearProgram::new(&Model::new(objective).unwrap()).unwrap();
        assert!(!program.same_matrix_objective_rows(&objective));

        let maximize = LinearProgram::new(&model(ObjectiveSense::Maximize)).unwrap();
        assert!(!program.same_matrix_objective_rows(&maximize));
    }

    /// The digest names the full program: stable across a rebuild of the same
    /// model, changed by a coefficient — and changed by a bounds-only variant,
    /// because it commits to the bounds too. The reuse decision is
    /// `same_matrix_objective_rows`'s; this digest is evidence identity.
    #[test]
    fn matrix_sha256_commits_to_coefficients_and_bounds() {
        let base = model(ObjectiveSense::Minimize);
        let program = LinearProgram::new(&base).unwrap();
        let digest = program.matrix_sha256();
        assert_eq!(digest.len(), 64);
        assert_eq!(
            digest,
            LinearProgram::new(&model(ObjectiveSense::Minimize))
                .unwrap()
                .matrix_sha256()
        );

        let mut coefficient = base.document().clone();
        coefficient.constraints[0].terms[0].coefficient = 1.5;
        let coefficient = LinearProgram::new(&Model::new(coefficient).unwrap()).unwrap();
        assert_ne!(digest, coefficient.matrix_sha256());

        let mut tightened = base.document().variables.clone();
        tightened[0].upper = finite(0.5);
        let variant = base.rebound(tightened).unwrap();
        let bounds_only = program.with_variable_bounds(&variant).unwrap();
        assert!(program.same_matrix_objective_rows(&bounds_only));
        assert_ne!(digest, bounds_only.matrix_sha256());
    }
}
