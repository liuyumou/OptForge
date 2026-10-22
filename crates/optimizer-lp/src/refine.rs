//! ADR-0037 CPU admission for original-residual correction problems.
//! Every interval encloses an exact-real operation on the original binary64 data.
#![allow(missing_docs)]
use crate::{LinearProgram, Range, outward::Enclosure};
use serde::{Deserialize, Serialize};

pub const ID: &str = "lp-refine-v1";
pub const MAX_DIM: usize = 65536;
pub const MAX_NNZ: usize = 1 << 23;

#[derive(Clone, Copy, Debug, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Interval {
    pub lower: f64,
    pub upper: f64,
    pub rounded: f64,
}
impl Interval {
    pub fn point(x: f64) -> Result<Self, &'static str> {
        if !x.is_finite() {
            return Err("nonfinite_operand");
        }
        Ok(Self {
            lower: x,
            upper: x,
            rounded: x,
        })
    }
    fn from_inner(x: Option<Enclosure>) -> Result<Self, &'static str> {
        let v = x.ok_or("enclosure_range")?;
        Ok(Self {
            lower: v.lower,
            upper: v.upper,
            rounded: v.rounded,
        })
    }
    fn inner(self) -> Enclosure {
        Enclosure {
            lower: self.lower,
            upper: self.upper,
            rounded: self.rounded,
        }
    }
    pub fn plus(self, rhs: Self) -> Result<Self, &'static str> {
        Self::from_inner(self.inner().add(rhs.inner()))
    }
    pub fn minus(self, rhs: Self) -> Result<Self, &'static str> {
        Self::from_inner(self.inner().subtract(rhs.inner()))
    }
    pub fn times(self, rhs: Self) -> Result<Self, &'static str> {
        let mut low = f64::INFINITY;
        let mut high = f64::NEG_INFINITY;
        for a in [self.lower, self.upper] {
            for b in [rhs.lower, rhs.upper] {
                let v = Enclosure::product(a, b).ok_or("enclosure_range")?;
                low = low.min(v.lower);
                high = high.max(v.upper);
            }
        }
        Self::checked(low, high, self.rounded * rhs.rounded)
    }
    pub fn divide_positive(self, rhs: Self) -> Result<Self, &'static str> {
        if rhs.lower <= 0.0 {
            return Err("division_range");
        }
        let mut low = f64::INFINITY;
        let mut high = f64::NEG_INFINITY;
        for a in [self.lower, self.upper] {
            for b in [rhs.lower, rhs.upper] {
                let v = a / b;
                if !v.is_finite() {
                    return Err("division_range");
                }
                // Exact zero divisions stay exact. Nonzero underflow retains an enclosure.
                low = low.min(if a == 0.0 { v } else { v.next_down() });
                high = high.max(if a == 0.0 { v } else { v.next_up() });
            }
        }
        Self::checked(low, high, self.rounded / rhs.rounded)
    }
    fn checked(lower: f64, upper: f64, rounded: f64) -> Result<Self, &'static str> {
        if !lower.is_finite() || !upper.is_finite() || !rounded.is_finite() || lower > upper {
            return Err("enclosure_range");
        }
        Ok(Self {
            lower,
            upper,
            rounded,
        })
    }
    pub fn absolute(self) -> Self {
        Self {
            lower: if self.lower <= 0.0 && self.upper >= 0.0 {
                0.0
            } else {
                self.lower.abs().min(self.upper.abs())
            },
            upper: self.lower.abs().max(self.upper.abs()),
            rounded: self.rounded.abs(),
        }
    }
    pub fn project(self, b: Range) -> Self {
        let clip = |x: f64| x.max(b.lower).min(b.upper);
        Self {
            lower: clip(self.lower),
            upper: clip(self.upper),
            rounded: clip(self.rounded),
        }
    }
    pub fn error(self) -> f64 {
        {
            let e = (self.rounded - self.lower)
                .abs()
                .max((self.upper - self.rounded).abs());
            if e == 0.0 { 0.0 } else { e.next_up() }
        }
    }
}
fn dot<'a>(entries: impl Iterator<Item = (f64, f64)> + 'a) -> Result<Interval, &'static str> {
    let mut sum = Interval::point(0.0)?;
    for (a, b) in entries {
        sum = sum.plus(Interval::point(a)?.times(Interval::point(b)?)?)?;
    }
    Ok(sum)
}

/// The original canonical operator; activity entries are implicit.
pub struct EqualityBox<'a> {
    pub original: &'a LinearProgram,
    pub bounds: Vec<Range>,
    pub objective: Vec<f64>,
    pub primal_scale: Vec<Interval>,
    pub variable_scale: Vec<f64>,
    pub gradient_scale: Vec<f64>,
}
#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Residuals {
    pub primal: Vec<Interval>,
    pub dual: Vec<Interval>,
}
#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Correction {
    pub primal_exponent: i32,
    pub dual_exponent: i32,
    pub rhs: Vec<Interval>,
    pub objective: Vec<Interval>,
    pub lower: Vec<Option<Interval>>,
    pub upper: Vec<Option<Interval>>,
}
impl<'a> EqualityBox<'a> {
    pub fn new(p: &'a LinearProgram) -> Result<Self, &'static str> {
        let n = p.column_count();
        let m = p.row_count();
        if n > MAX_DIM || m > MAX_DIM || p.row_major().nonzeros() > MAX_NNZ {
            return Err("shape_limit");
        }
        let _ = n.checked_add(m).ok_or("dimension_overflow")?;
        preparation_bytes(m, n, p.nonzeros())?;
        let bounds = p
            .columns()
            .iter()
            .chain(p.rows())
            .copied()
            .collect::<Vec<_>>();
        let objective = p
            .objective()
            .iter()
            .copied()
            .chain(std::iter::repeat_n(0.0, m))
            .collect::<Vec<_>>();
        let variable_scale = bounds
            .iter()
            .map(|r| {
                let l = if r.lower.is_finite() {
                    r.lower.abs()
                } else {
                    0.0
                };
                let u = if r.upper.is_finite() {
                    r.upper.abs()
                } else {
                    0.0
                };
                l.max(u).max(1.0)
            })
            .collect::<Vec<_>>();
        let gradient_scale = objective.iter().map(|x| x.abs().max(1.0)).collect();
        let mut primal_scale = Vec::new();
        for i in 0..m {
            let (cols, values) = p.row_major().line(i);
            let s = dot(cols
                .iter()
                .zip(values)
                .map(|(&j, &a)| (a.abs(), variable_scale[j as usize])))?
            .plus(Interval::point(variable_scale[n + i])?)?;
            primal_scale.push(Interval {
                lower: s.lower.max(1.0),
                upper: s.upper.max(1.0),
                rounded: s.rounded.max(1.0),
            });
        }
        Ok(Self {
            original: p,
            bounds,
            objective,
            primal_scale,
            variable_scale,
            gradient_scale,
        })
    }
    pub fn initial(&self) -> (Vec<f64>, Vec<f64>) {
        (
            self.bounds
                .iter()
                .map(|r| 0.0_f64.max(r.lower).min(r.upper))
                .collect(),
            vec![0.0; self.original.row_count()],
        )
    }
    pub fn residuals(&self, v: &[f64], y: &[f64]) -> Result<Residuals, &'static str> {
        let n = self.original.column_count();
        let m = self.original.row_count();
        if v.len() != n + m || y.len() != m {
            return Err("vector_dimensions");
        }
        if !v.iter().chain(y).all(|x| x.is_finite()) {
            return Err("nonfinite_operand");
        }
        let mut primal = Vec::new();
        for i in 0..m {
            let (cols, values) = self.original.row_major().line(i);
            primal.push(Interval::point(v[n + i])?.minus(dot(
                cols.iter().zip(values).map(|(&j, &a)| (a, v[j as usize])),
            )?)?);
        }
        let mut dual = Vec::new();
        for j in 0..n {
            let (rows, values) = self.original.column_major().line(j);
            dual.push(Interval::point(self.objective[j])?.minus(dot(
                rows.iter().zip(values).map(|(&i, &a)| (a, y[i as usize])),
            )?)?);
        }
        for &x in y {
            dual.push(Interval::point(x)?);
        }
        Ok(Residuals { primal, dual })
    }
    pub fn merit(&self, v: &[f64], y: &[f64]) -> Result<Interval, &'static str> {
        let r = self.residuals(v, y)?;
        let mut result = Interval::point(0.0)?;
        let mut include = |x: Interval| {
            result.lower = result.lower.max(x.lower);
            result.upper = result.upper.max(x.upper);
            result.rounded = result.rounded.max(x.rounded);
        };
        for (r, s) in r.primal.iter().zip(&self.primal_scale) {
            include(r.absolute().divide_positive(*s)?);
        }
        for (j, &value) in v.iter().enumerate() {
            let sv = Interval::point(self.variable_scale[j])?;
            let theta = sv.divide_positive(Interval::point(self.gradient_scale[j])?)?;
            let x = Interval::point(value)?;
            let projected = x.minus(theta.times(r.dual[j])?)?.project(self.bounds[j]);
            include(x.minus(projected)?.absolute().divide_positive(sv)?);
            include(
                x.minus(x.project(self.bounds[j]))?
                    .absolute()
                    .divide_positive(sv)?,
            );
        }
        Ok(result)
    }
    pub fn correction(&self, v: &[f64], y: &[f64]) -> Result<Correction, &'static str> {
        let r = self.residuals(v, y)?;
        let mut primal_exponent = normalizing_exponent(&r.primal)?;
        let mut dual_exponent = normalizing_exponent(&r.dual)?;
        let (rhs, lower, upper) = loop {
            let trial = (|| {
                let rhs = scale_intervals(&r.primal, primal_exponent)?;
                let mut lower = Vec::new();
                let mut upper = Vec::new();
                for (b, &x) in self.bounds.iter().zip(v) {
                    let shifted = |endpoint: f64| -> Result<Option<Interval>, &'static str> {
                        if endpoint.is_infinite() {
                            Ok(None)
                        } else {
                            Ok(Some(scale(
                                Interval::point(endpoint)?.minus(Interval::point(x)?)?,
                                primal_exponent,
                            )?))
                        }
                    };
                    lower.push(shifted(b.lower)?);
                    upper.push(shifted(b.upper)?);
                }
                Ok::<_, &'static str>((rhs, lower, upper))
            })();
            match trial {
                Ok(x) => break x,
                Err(_) if primal_exponent > -1022 => primal_exponent -= 1,
                Err(e) => return Err(e),
            }
        };
        let objective = loop {
            match scale_intervals(&r.dual, dual_exponent) {
                Ok(x) => break x,
                Err(_) if dual_exponent > -1022 => dual_exponent -= 1,
                Err(e) => return Err(e),
            }
        };
        Ok(Correction {
            primal_exponent,
            dual_exponent,
            rhs,
            objective,
            lower,
            upper,
        })
    }
}
fn normalizing_exponent(values: &[Interval]) -> Result<i32, &'static str> {
    let max = values.iter().map(|x| x.rounded.abs()).fold(0.0, f64::max);
    if !max.is_finite() {
        return Err("scale_range");
    }
    if max == 0.0 {
        return Ok(0);
    }
    // ilogb without logarithms, covering gradual underflow.
    let bits = max.to_bits();
    let field = ((bits >> 52) & 2047) as i32;
    let e = if field == 0 {
        63 - bits.leading_zeros() as i32 - 1074
    } else {
        field - 1023
    };
    Ok((-e).clamp(-1022, 1023))
}
fn scale(x: Interval, e: i32) -> Result<Interval, &'static str> {
    let power = crate::research::scale_pow2(1.0, e);
    let result = x.times(Interval::point(power)?)?;
    if x.rounded != 0.0 && result.rounded == 0.0 {
        return Err("scale_lost_nonzero");
    }
    Ok(result)
}
fn scale_intervals(x: &[Interval], e: i32) -> Result<Vec<Interval>, &'static str> {
    x.iter().map(|&v| scale(v, e)).collect()
}

/// Independent admission does not grant a runtime oracle merely because maps fit.
pub fn contracts_progress(anchor: Interval, next: Interval) -> bool {
    anchor.lower > 0.0
        && Interval::point(anchor.lower)
            .and_then(|x| x.times(Interval::point(0.5)?))
            .is_ok_and(|limit| next.upper <= limit.lower)
}

/// Four independent numerical error allocations in original merit units.
#[derive(Clone, Copy, Debug, Default, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ErrorBudget {
    pub representation: f64,
    pub arithmetic: f64,
    pub anchor_transform: f64,
    pub state_update: f64,
}
impl ErrorBudget {
    pub fn accumulate(&mut self, other: Self) -> Result<(), &'static str> {
        let add = |a: f64, b: f64| {
            Interval::point(a)?
                .plus(Interval::point(b)?)
                .map(|x| x.upper)
        };
        self.representation = add(self.representation, other.representation)?;
        self.arithmetic = add(self.arithmetic, other.arithmetic)?;
        self.anchor_transform = add(self.anchor_transform, other.anchor_transform)?;
        self.state_update = add(self.state_update, other.state_update)?;
        Ok(())
    }
    pub fn admits(&self, anchor: Interval) -> bool {
        let limit = (anchor.lower / 32.0).next_down();
        limit >= 0.0
            && [
                self.representation,
                self.arithmetic,
                self.anchor_transform,
                self.state_update,
            ]
            .iter()
            .all(|e| e.is_finite() && *e >= 0.0 && *e <= limit)
    }
}

/// Materialized host reference for the exact equality/box transform.
/// Device implementations must use the original sparse A and implicit activity block.
pub fn correction_program(
    eq: &EqualityBox<'_>,
    c: &Correction,
) -> Result<LinearProgram, &'static str> {
    use optimizer_core::{
        Bound, Constraint, Domain, LinearTerm, Model, ModelDocument, Objective, ObjectiveSense,
        Variable,
    };
    let n = eq.original.column_count();
    let m = eq.original.row_count();
    if c.rhs.len() != m
        || c.objective.len() != n + m
        || c.lower.len() != n + m
        || c.upper.len() != n + m
    {
        return Err("correction_dimensions");
    }
    let endpoint = |x: Option<Interval>, lower: bool| match x {
        Some(x) => Bound::Finite { value: x.rounded },
        None => {
            if lower {
                Bound::NegativeInfinity
            } else {
                Bound::PositiveInfinity
            }
        }
    };
    let variables = (0..n + m)
        .map(|j| Variable {
            id: j as u32,
            domain: Domain::Continuous,
            lower: endpoint(c.lower[j], true),
            upper: endpoint(c.upper[j], false),
        })
        .collect();
    let constraints = (0..m)
        .map(|i| {
            let (cols, values) = eq.original.row_major().line(i);
            let mut terms = cols
                .iter()
                .zip(values)
                .map(|(&j, &a)| LinearTerm {
                    variable_id: j,
                    coefficient: a,
                })
                .collect::<Vec<_>>();
            terms.push(LinearTerm {
                variable_id: (n + i) as u32,
                coefficient: -1.0,
            });
            Constraint {
                id: i as u32,
                lower: Bound::Finite {
                    value: c.rhs[i].rounded,
                },
                upper: Bound::Finite {
                    value: c.rhs[i].rounded,
                },
                terms,
            }
        })
        .collect();
    let objective = Objective {
        sense: ObjectiveSense::Minimize,
        offset: 0.0,
        terms: c
            .objective
            .iter()
            .enumerate()
            .map(|(j, x)| LinearTerm {
                variable_id: j as u32,
                coefficient: x.rounded,
            })
            .collect(),
    };
    let model = Model::new(ModelDocument {
        schema_version: 1,
        model_id: ID.into(),
        variables,
        constraints,
        objective,
    })
    .map_err(|_| "correction_model")?;
    LinearProgram::new(&model).map_err(|_| "correction_program")
}

/// Check that shifted/scaled correction endpoints satisfy their original-unit allowance.
/// Each interval is compared to the representable value the inner solver will receive.
pub fn transform_error(eq: &EqualityBox<'_>, c: &Correction) -> Result<f64, &'static str> {
    let mut error = 0.0_f64;
    let dp = Interval::point(crate::research::scale_pow2(1.0, c.primal_exponent))?;
    let dd = Interval::point(crate::research::scale_pow2(1.0, c.dual_exponent))?;
    for (i, x) in c.rhs.iter().enumerate() {
        error = error.max(
            Interval::point(x.error())?
                .divide_positive(dp)?
                .divide_positive(eq.primal_scale[i])?
                .upper,
        );
    }
    for (j, x) in c.objective.iter().enumerate() {
        error = error.max(
            Interval::point(x.error())?
                .divide_positive(dd)?
                .divide_positive(Interval::point(eq.gradient_scale[j])?)?
                .upper,
        );
    }
    for (j, (lo, hi)) in c.lower.iter().zip(&c.upper).enumerate() {
        for x in [lo, hi].into_iter().flatten() {
            error = error.max(
                Interval::point(x.error())?
                    .divide_positive(dp)?
                    .divide_positive(Interval::point(eq.variable_scale[j])?)?
                    .upper,
            );
        }
    }
    Ok(error)
}

/// Sparse operator handed to the bounded inner oracle.
/// A single canonical coefficient set defines both orientations.
#[derive(Clone, Debug)]
pub struct InnerOperator {
    rows: usize,
    columns: usize,
    original_columns: usize,
    coefficients: Vec<f64>,
    indices: Vec<u32>,
    offsets: Vec<u32>,
    permutation: Vec<u32>,
    column_indices: Vec<u32>,
    column_offsets: Vec<u32>,
    diagonal: Vec<f64>,
    original_coefficients: Vec<Interval>,
    original_diagonal: Vec<Interval>,
    norm: f64,
    generation: String,
}
impl InnerOperator {
    pub fn rows(&self) -> usize {
        self.rows
    }
    pub fn columns(&self) -> usize {
        self.columns
    }
    pub fn original_columns(&self) -> usize {
        self.original_columns
    }
    pub fn norm(&self) -> f64 {
        self.norm
    }
    pub fn coefficients(&self) -> &Vec<f64> {
        &self.coefficients
    }
    pub fn indices(&self) -> &Vec<u32> {
        &self.indices
    }
    pub fn offsets(&self) -> &Vec<u32> {
        &self.offsets
    }
    pub fn permutation(&self) -> &Vec<u32> {
        &self.permutation
    }
    pub fn column_indices(&self) -> &Vec<u32> {
        &self.column_indices
    }
    pub fn column_offsets(&self) -> &Vec<u32> {
        &self.column_offsets
    }
    pub fn diagonal(&self) -> &Vec<f64> {
        &self.diagonal
    }
    pub fn original_coefficients(&self) -> &Vec<Interval> {
        &self.original_coefficients
    }
    pub fn original_diagonal(&self) -> &Vec<Interval> {
        &self.original_diagonal
    }
    pub fn generation(&self) -> String {
        self.generation.clone()
    }
    pub fn new(engine: &crate::Engine<'_>, original_columns: usize) -> Result<Self, &'static str> {
        let p = engine.program();
        let m = p.row_count();
        let n = p.column_count();
        if original_columns > MAX_DIM
            || m > MAX_DIM
            || original_columns.checked_add(m) != Some(n)
            || p.nonzeros() > MAX_NNZ + m
        {
            return Err("activity_dimensions");
        }
        let mut coefficients = Vec::new();
        let mut original_coefficients = Vec::new();
        let mut indices = Vec::new();
        let mut offsets = vec![0];
        let mut diagonal = vec![0.0; m];
        let mut original_diagonal = vec![Interval::point(0.0)?; m];
        let (r, c) = (
            engine.preconditioner().row(),
            engine.preconditioner().column(),
        );
        if !r.iter().chain(c).all(|x| x.is_finite() && *x > 0.0) {
            return Err("preconditioner_range");
        }
        for i in 0..m {
            let (js, vs) = p.row_major().line(i);
            let mut found_identity = false;
            for (&j, &a) in js.iter().zip(vs) {
                let exact = Interval::point(a)?
                    .times(Interval::point(r[i])?)?
                    .times(Interval::point(c[j as usize])?)?;
                if a != 0.0 && exact.rounded == 0.0 {
                    return Err("scaled_coefficient_lost_nonzero");
                }
                if j as usize == original_columns + i {
                    if a != -1.0 {
                        return Err("activity_identity");
                    }
                    found_identity = true;
                    diagonal[i] = exact.rounded;
                    original_diagonal[i] = exact;
                } else if (j as usize) < original_columns {
                    coefficients.push(exact.rounded);
                    original_coefficients.push(exact);
                    indices.push(j);
                } else {
                    return Err("activity_structure");
                }
            }
            if !found_identity {
                return Err("activity_identity");
            }
            offsets.push(coefficients.len() as u32);
        }
        let mut columns = vec![Vec::new(); original_columns];
        for i in 0..m {
            for k in offsets[i] as usize..offsets[i + 1] as usize {
                columns[indices[k] as usize].push((i as u32, k as u32));
            }
        }
        let mut permutation = Vec::new();
        let mut column_indices = Vec::new();
        let mut column_offsets = vec![0];
        for entries in columns {
            for (i, k) in entries {
                column_indices.push(i);
                permutation.push(k);
            }
            column_offsets.push(permutation.len() as u32);
        }
        let mut row_norm = 0.0_f64;
        let mut col_norm = vec![0.0_f64; n];
        for i in 0..m {
            let mut sum = original_diagonal[i].absolute();
            col_norm[original_columns + i] = sum.upper;
            for k in offsets[i] as usize..offsets[i + 1] as usize {
                let mut x = original_coefficients[k].absolute();
                let narrow = f64::from(coefficients[k] as f32).abs();
                if narrow.is_finite() {
                    x.upper = x.upper.max(narrow);
                }
                sum = sum.plus(x)?;
                let j = indices[k] as usize;
                col_norm[j] = Interval::point(col_norm[j])?.plus(x)?.upper;
            }
            row_norm = row_norm.max(sum.upper);
        }
        let col = col_norm.into_iter().fold(0.0, f64::max);
        let norm = if row_norm == 0.0 || col == 0.0 {
            0.0
        } else {
            Interval::point(row_norm.sqrt().next_up())?
                .times(Interval::point(col.sqrt().next_up())?)?
                .upper
        };
        let generation = optimizer_core::sha256::hex(
            &serde_json::to_vec(&(p.row_major().entries().collect::<Vec<_>>(), r, c))
                .map_err(|_| "operator_identity")?,
        );
        Ok(Self {
            rows: m,
            columns: n,
            original_columns,
            coefficients,
            indices,
            offsets,
            permutation,
            column_indices,
            column_offsets,
            diagonal,
            original_coefficients,
            original_diagonal,
            norm,
            generation,
        })
    }
    pub fn accurate(&self, transpose: bool, vector: &[f64]) -> Result<Vec<Interval>, &'static str> {
        let count = if transpose { self.columns } else { self.rows };
        let mut out = vec![Interval::point(0.0)?; count];
        if !transpose {
            for (i, x) in out.iter_mut().enumerate() {
                *x = self.original_diagonal[i]
                    .times(Interval::point(vector[self.original_columns + i])?)?;
                for k in self.offsets[i] as usize..self.offsets[i + 1] as usize {
                    *x = x.plus(
                        self.original_coefficients[k]
                            .times(Interval::point(vector[self.indices[k] as usize])?)?,
                    )?;
                }
            }
        } else {
            for (j, x) in out.iter_mut().take(self.original_columns).enumerate() {
                for t in self.column_offsets[j] as usize..self.column_offsets[j + 1] as usize {
                    let k = self.permutation[t] as usize;
                    *x = x.plus(
                        self.original_coefficients[k]
                            .times(Interval::point(vector[self.column_indices[t] as usize])?)?,
                    )?;
                }
            }
            for i in 0..self.rows {
                out[self.original_columns + i] =
                    self.original_diagonal[i].times(Interval::point(vector[i])?)?;
            }
        }
        Ok(out)
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum ProductWidth {
    F64,
    F32,
}

/// CPU mirror of the sparse CUDA reduction, with the identity applied separately.
pub fn host_product(
    op: &InnerOperator,
    transpose: bool,
    input: &[f64],
    width: ProductWidth,
) -> Result<Vec<f64>, String> {
    let f32mode = width == ProductWidth::F32;
    let count = if transpose { op.columns } else { op.rows };
    let mut output = vec![0.0; count];
    for (line, out) in output.iter_mut().enumerate() {
        let identity = if transpose && line >= op.original_columns {
            Some((line - op.original_columns, line - op.original_columns))
        } else if !transpose {
            Some((line, op.original_columns + line))
        } else {
            None
        };
        if !transpose || line < op.original_columns {
            let (offsets, indices) = if transpose {
                (&op.column_offsets, &op.column_indices)
            } else {
                (&op.offsets, &op.indices)
            };
            let begin = offsets[line] as usize;
            let end = offsets[line + 1] as usize;
            let mut lanes = [0.0; 32];
            for (lane, sum) in lanes.iter_mut().enumerate() {
                for t in (begin + lane..end).step_by(32) {
                    let k = if transpose {
                        op.permutation[t] as usize
                    } else {
                        t
                    };
                    let mut a = op.coefficients[k];
                    let mut b = input[indices[t] as usize];
                    if f32mode {
                        a = crate::precision::narrow(a).map_err(str::to_owned)?;
                        b = crate::precision::narrow(b).map_err(str::to_owned)?;
                    }
                    let p = if f32mode {
                        f64::from((a as f32) * (b as f32))
                    } else {
                        a * b
                    };
                    if !p.is_finite() || (p == 0.0 && a != 0.0 && b != 0.0) {
                        return Err("product_range".into());
                    }
                    *sum = if f32mode {
                        f64::from((*sum as f32) + (p as f32))
                    } else {
                        *sum + p
                    };
                }
            }
            for d in [16, 8, 4, 2, 1] {
                for l in 0..d {
                    lanes[l] = if f32mode {
                        f64::from((lanes[l] as f32) + (lanes[l + d] as f32))
                    } else {
                        lanes[l] + lanes[l + d]
                    };
                }
            }
            *out = lanes[0];
        }
        if let Some((i, j)) = identity {
            let value = op.diagonal[i] * input[j];
            if !value.is_finite() || value == 0.0 && op.diagonal[i] != 0.0 && input[j] != 0.0 {
                return Err("product_range".into());
            }
            *out += value;
        }
        if !out.is_finite() {
            return Err("product_range".into());
        }
    }
    Ok(output)
}

/// Pluggable sparse products; implementation errors never grant original-model authority.
pub trait ProductOracle {
    fn observe(&mut self, _phase: &str, _ns: u64) {}
    fn bind(&mut self, op: &InnerOperator) -> Result<(), String>;
    fn apply(
        &mut self,
        op: &InnerOperator,
        transpose: bool,
        input: &[f64],
        width: ProductWidth,
    ) -> Result<Vec<f64>, String>;
}
pub struct HostOracle;
impl ProductOracle for HostOracle {
    fn bind(&mut self, _: &InnerOperator) -> Result<(), String> {
        Ok(())
    }
    fn apply(
        &mut self,
        op: &InnerOperator,
        t: bool,
        x: &[f64],
        w: ProductWidth,
    ) -> Result<Vec<f64>, String> {
        host_product(op, t, x, w)
    }
}

#[derive(Clone, Debug, Default, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Work {
    /// Charged proposals, including rejected and uncertain device work.
    pub physical_updates: u64,
    pub committed_updates: u64,
    pub corrections: u64,
    pub failed_corrections: u64,
    pub refreshes: u64,
    pub promotions: u64,
    pub certifications: u64,
    pub sparse_products: u64,
    pub guard_products: u64,
    pub anchor_products: u64,
}
#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Progress {
    pub correction: u64,
    pub physical_updates: u64,
    pub width: ProductWidth,
    pub anchor_merit: Interval,
    pub candidate_merit: Option<Interval>,
    pub errors: ErrorBudget,
    pub decision: String,
    pub anchor_v: Vec<f64>,
    pub anchor_y: Vec<f64>,
    pub candidate_v: Option<Vec<f64>>,
    pub candidate_y: Option<Vec<f64>>,
    pub generation: String,
    pub primal_exponent: i32,
    pub dual_exponent: i32,
}
#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Outcome {
    pub v: Vec<f64>,
    pub y: Vec<f64>,
    pub work: Work,
    pub trace: Vec<Progress>,
    pub status: String,
    pub failure: Option<String>,
    pub width: ProductWidth,
}

/// Complete numerical anchor state at an inner checkpoint. Physical consumption is external.
#[derive(Clone, Debug, PartialEq)]
pub struct AnchorState {
    pub generation: String,
    pub base_x: Vec<f64>,
    pub base_y: Vec<f64>,
    pub delta_x: Vec<f64>,
    pub delta_y: Vec<f64>,
    pub restart_x: Vec<f64>,
    pub restart_y: Vec<f64>,
    pub primal_products: Vec<Interval>,
    pub dual_products: Vec<Interval>,
    pub inner: crate::control::Fp64State,
    pub correction: Correction,
    pub assessment_position: u64,
    pub errors: ErrorBudget,
    pub rebase_error: f64,
}
impl AnchorState {
    pub fn validate_generation(&self, op: &InnerOperator) -> Result<(), &'static str> {
        if self.generation != op.generation {
            return Err("stale_generation");
        }
        Ok(())
    }
}
fn represented(
    op: &InnerOperator,
    transpose: bool,
    x: &[f64],
    width: ProductWidth,
) -> Result<Vec<Interval>, String> {
    let mut out = vec![
        Interval::point(0.0).map_err(str::to_owned)?;
        if transpose { op.columns } else { op.rows }
    ];
    let coefficient = |k: usize| -> Result<Interval, String> {
        let a = op.coefficients[k];
        let value = if width == ProductWidth::F32 {
            crate::precision::narrow(a).map_err(str::to_owned)?
        } else {
            a
        };
        Interval::point(value).map_err(str::to_owned)
    };
    if !transpose {
        for (i, value) in out.iter_mut().enumerate() {
            *value = Interval::point(op.diagonal[i])
                .and_then(|a| a.times(Interval::point(x[op.original_columns + i])?))
                .map_err(str::to_owned)?;
            for k in op.offsets[i] as usize..op.offsets[i + 1] as usize {
                *value = value
                    .plus(
                        coefficient(k)?
                            .times(
                                Interval::point(x[op.indices[k] as usize])
                                    .map_err(str::to_owned)?,
                            )
                            .map_err(str::to_owned)?,
                    )
                    .map_err(str::to_owned)?;
            }
        }
    } else {
        for (j, value) in out.iter_mut().take(op.original_columns).enumerate() {
            for t in op.column_offsets[j] as usize..op.column_offsets[j + 1] as usize {
                *value = value
                    .plus(
                        coefficient(op.permutation[t] as usize)?
                            .times(
                                Interval::point(x[op.column_indices[t] as usize])
                                    .map_err(str::to_owned)?,
                            )
                            .map_err(str::to_owned)?,
                    )
                    .map_err(str::to_owned)?;
            }
        }
        for i in 0..op.rows {
            out[op.original_columns + i] = Interval::point(op.diagonal[i])
                .and_then(|a| a.times(Interval::point(x[i])?))
                .map_err(str::to_owned)?;
        }
    }
    Ok(out)
}
fn guarded_product<O: ProductOracle>(
    oracle: &mut O,
    op: &InnerOperator,
    transpose: bool,
    delta: &[f64],
    anchor: &[Interval],
    width: ProductWidth,
    work: &mut Work,
) -> Result<(Vec<f64>, Vec<ErrorBudget>), String> {
    work.sparse_products += 1;
    let actual = oracle.apply(op, transpose, delta, width)?;
    let guard_start = std::time::Instant::now();
    let exact = op.accurate(transpose, delta).map_err(str::to_owned)?;
    let rep = represented(op, transpose, delta, width)?;
    work.guard_products += 2;
    if actual.len() != exact.len() || anchor.len() != actual.len() {
        return Err("oracle_dimensions".into());
    }
    let mut values = Vec::new();
    let mut errors = Vec::new();
    for (((value, original), represented), a) in actual.into_iter().zip(exact).zip(rep).zip(anchor)
    {
        let pv = Interval::point(value).map_err(str::to_owned)?;
        let sum = pv
            .plus(Interval::point(a.rounded).map_err(str::to_owned)?)
            .map_err(str::to_owned)?;
        errors.push(ErrorBudget {
            representation: original
                .minus(represented)
                .map_err(str::to_owned)?
                .absolute()
                .upper,
            arithmetic: pv
                .minus(represented)
                .map_err(str::to_owned)?
                .absolute()
                .upper,
            anchor_transform: a.error(),
            state_update: sum.error(),
        });
        values.push(sum.rounded);
    }
    oracle.observe(
        "product_error_guards",
        guard_start.elapsed().as_nanos() as u64,
    );
    Ok((values, errors))
}
fn mapped_errors(
    eq: &EqualityBox<'_>,
    engine: &crate::Engine<'_>,
    c: &Correction,
    t: bool,
    errors: &[ErrorBudget],
    totals: &mut ErrorBudget,
) -> Result<(), String> {
    let exponent = if t {
        c.dual_exponent
    } else {
        c.primal_exponent
    };
    let d = Interval::point(crate::research::scale_pow2(1.0, exponent)).map_err(str::to_owned)?;
    let mut contribution = ErrorBudget::default();
    for (i, e) in errors.iter().enumerate() {
        let scale = if t {
            engine.preconditioner().column()[i]
        } else {
            engine.preconditioner().row()[i]
        };
        let denom = if t {
            Interval::point(eq.gradient_scale[i])
        } else {
            Ok(eq.primal_scale[i])
        }
        .map_err(str::to_owned)?;
        let norm = |x: f64| {
            Interval::point(x)?
                .divide_positive(Interval::point(scale)?)?
                .divide_positive(d)?
                .divide_positive(denom)
                .map(|v| v.upper)
        };
        contribution.representation = totals
            .representation
            .max(norm(e.representation).map_err(str::to_owned)?);
        contribution.arithmetic = totals
            .arithmetic
            .max(norm(e.arithmetic).map_err(str::to_owned)?);
        contribution.anchor_transform = totals
            .anchor_transform
            .max(norm(e.anchor_transform).map_err(str::to_owned)?);
        contribution.state_update = totals
            .state_update
            .max(norm(e.state_update).map_err(str::to_owned)?);
    }
    totals.accumulate(contribution).map_err(str::to_owned)?;
    Ok(())
}

/// CPU-first bounded inner-oracle admission. Final certification is supplied by the host owner.
/// All failed proposals consume physical work; all published points remain original-model data.
#[allow(clippy::too_many_arguments)]
pub fn run<O: ProductOracle>(
    eq: &EqualityBox<'_>,
    method: optimizer_core::LpSettings,
    width: ProductWidth,
    anchored: bool,
    floor: f64,
    deadline: std::time::Instant,
    cancel: &optimizer_core::CancellationToken,
    oracle: &mut O,
    mut certify: impl FnMut(&[f64], &[f64]) -> bool,
) -> Outcome {
    let (v, y) = eq.initial();
    let mut out = Outcome {
        v,
        y,
        work: Work::default(),
        trace: Vec::new(),
        status: "iteration_limit".into(),
        failure: None,
        width,
    };
    let outcome = (|| -> Result<(), String> {
        if cancel.is_cancelled() {
            out.status = "interrupted".into();
            return Ok(());
        }
        out.work.certifications += 1;
        if certify(&out.v, &out.y) {
            out.status = "accepted".into();
            return Ok(());
        }
        let preparation_start = std::time::Instant::now();
        let initial_c = eq.correction(&out.v, &out.y).map_err(str::to_owned)?;
        let base = correction_program(eq, &initial_c).map_err(str::to_owned)?;
        let prepared = PreparedCorrection::new(&base, method);
        let initial_engine = prepared.bind(&base).map_err(str::to_owned)?;
        let op = InnerOperator::new(&initial_engine, eq.original.column_count())
            .map_err(str::to_owned)?;
        oracle.observe(
            "transformed_preparation",
            preparation_start.elapsed().as_nanos() as u64,
        );
        for _ in 0..32 {
            if out.work.physical_updates >= method.iteration_limit.min(50000) {
                out.failure = Some("physical_update_limit".into());
                return Ok(());
            }
            if cancel.is_cancelled() {
                out.status = "interrupted".into();
                return Ok(());
            }
            if std::time::Instant::now() >= deadline {
                out.status = "time_limit".into();
                return Ok(());
            }
            let merit = eq.merit(&out.v, &out.y).map_err(str::to_owned)?;
            if merit.upper <= floor {
                out.work.certifications += 1;
                if certify(&out.v, &out.y) {
                    out.status = "accepted".into();
                    return Ok(());
                }
                if out.width == ProductWidth::F64 {
                    return Err("certification_rejected_below_floor".into());
                }
                out.width = ProductWidth::F64;
                out.work.promotions += 1;
            }
            let c = eq.correction(&out.v, &out.y).map_err(str::to_owned)?;
            let p = correction_program(eq, &c).map_err(str::to_owned)?;
            let mut engine = prepared.bind(&p).map_err(str::to_owned)?;
            let safe = if op.norm > 0.0 {
                (0.9_f64.next_down() / op.norm).next_down()
            } else {
                engine.step()
            };
            engine
                .restrict_step(safe.min(engine.step()))
                .map_err(str::to_owned)?;
            if cancel.is_cancelled() {
                out.status = "interrupted".into();
                return Ok(());
            }
            if std::time::Instant::now() >= deadline {
                out.status = "time_limit".into();
                return Ok(());
            }
            oracle.bind(&op)?;
            let mut accepted = false;
            loop {
                out.work.corrections += 1;
                let mut control = crate::control::Fp64Controller::new(&engine);
                let mut anchors = AnchorState {
                    generation: op.generation.clone(),
                    base_x: vec![0.0; op.columns],
                    base_y: vec![0.0; op.rows],
                    delta_x: control.state().primal.clone(),
                    delta_y: control.state().dual.clone(),
                    restart_x: control.state().anchor_primal.clone(),
                    restart_y: control.state().anchor_dual.clone(),
                    primal_products: vec![Interval::point(0.0).map_err(str::to_owned)?; op.rows],
                    dual_products: vec![Interval::point(0.0).map_err(str::to_owned)?; op.columns],
                    inner: control.state().clone(),
                    correction: c.clone(),
                    assessment_position: out.work.physical_updates,
                    errors: ErrorBudget::default(),
                    rebase_error: 0.0,
                };
                let mut last_candidate: Option<(Vec<f64>, Vec<f64>, Interval)> = None;
                let mut refreshes = 0;
                let mut failure = "failed_progress".to_owned();
                let mut errors = ErrorBudget {
                    anchor_transform: transform_error(eq, &c).map_err(str::to_owned)?,
                    ..ErrorBudget::default()
                };
                for attempt_update in 0..2000 {
                    if cancel.is_cancelled() {
                        out.status = "interrupted".into();
                        return Ok(());
                    }
                    if std::time::Instant::now() >= deadline {
                        out.status = "time_limit".into();
                        return Ok(());
                    }
                    if out.work.physical_updates >= method.iteration_limit.min(50000) {
                        return Ok(());
                    }
                    out.work.physical_updates += 1;
                    let (gradient, grad_errors) = match guarded_product(
                        oracle,
                        &op,
                        true,
                        &anchors.delta_y,
                        &anchors.dual_products,
                        out.width,
                        &mut out.work,
                    ) {
                        Ok(x) => x,
                        Err(e) if e.starts_with("device:") => return Err(e),
                        Err(e) => {
                            failure = e;
                            break;
                        }
                    };
                    mapped_errors(eq, &engine, &c, true, &grad_errors, &mut errors)?;
                    // Admission before dependent vector work; the actual product is checked.
                    if !errors.admits(merit) {
                        if anchored && refreshes < 8 {
                            let refresh_start = std::time::Instant::now();
                            refresh_anchors(&op, &control, &mut anchors)?;
                            oracle.observe(
                                "anchor_refresh",
                                refresh_start.elapsed().as_nanos() as u64,
                            );
                            out.work.anchor_products += 2;
                            refreshes += 1;
                            out.work.refreshes += 1;
                            errors = ErrorBudget {
                                anchor_transform: transform_error(eq, &c).map_err(str::to_owned)?,
                                ..ErrorBudget::default()
                            };
                            continue;
                        }
                        failure = "operator_error_budget".into();
                        break;
                    }
                    let weight = control.state().weight;
                    let (tau, sigma) =
                        safe_steps(engine.step(), weight, op.norm).map_err(str::to_owned)?;
                    let denominator = Interval::point((control.state().since_restart + 2) as f64)
                        .map_err(str::to_owned)?;
                    let towards_interval =
                        Interval::point((control.state().since_restart + 1) as f64)
                            .and_then(|x| x.divide_positive(denominator))
                            .map_err(str::to_owned)?;
                    let back_interval = Interval::point(1.0)
                        .and_then(|x| x.divide_positive(denominator))
                        .map_err(str::to_owned)?;
                    errors
                        .accumulate(ErrorBudget {
                            anchor_transform: binding_error(eq, &op, &engine, &c, tau, sigma)?,
                            ..ErrorBudget::default()
                        })
                        .map_err(str::to_owned)?;
                    let point = |x: f64| Interval::point(x).map_err(str::to_owned);
                    let (lo, hi) = engine.scaled_column_bounds();
                    let mut trial = Vec::new();
                    let mut state_error = anchors.rebase_error;
                    for j in 0..op.columns {
                        let step = point(tau)?
                            .times(
                                point(engine.scaled_objective()[j])?
                                    .minus(point(gradient[j])?)
                                    .map_err(str::to_owned)?,
                            )
                            .map_err(str::to_owned)?;
                        let moved = point(anchors.delta_x[j])?
                            .minus(step)
                            .map_err(str::to_owned)?;
                        let lower = lo[j] - anchors.base_x[j];
                        let upper = hi[j] - anchors.base_x[j];
                        for bound in [lo[j], hi[j]] {
                            if bound.is_finite() {
                                state_error = state_error.max(
                                    point(bound)?
                                        .minus(point(anchors.base_x[j])?)
                                        .map_err(str::to_owned)?
                                        .error(),
                                );
                            }
                        }
                        if lower.is_nan()
                            || upper.is_nan()
                            || lower > upper
                            || lo[j].is_finite() && !lower.is_finite()
                            || hi[j].is_finite() && !upper.is_finite()
                        {
                            return Err("shifted_projection_range".into());
                        }
                        let clipped = moved.project(Range { lower, upper });
                        trial.push(clipped.rounded);
                        state_error = state_error.max(clipped.error());
                    }
                    let mut extrapolated = Vec::new();
                    for (&a, &b) in trial.iter().zip(&anchors.delta_x) {
                        let x = point(2.0)?
                            .times(point(a)?)
                            .map_err(str::to_owned)?
                            .minus(point(b)?)
                            .map_err(str::to_owned)?;
                        state_error = state_error.max(x.error());
                        extrapolated.push(x.rounded);
                    }
                    let (activity, activity_errors) = match guarded_product(
                        oracle,
                        &op,
                        false,
                        &extrapolated,
                        &anchors.primal_products,
                        out.width,
                        &mut out.work,
                    ) {
                        Ok(x) => x,
                        Err(e) if e.starts_with("device:") => return Err(e),
                        Err(e) => {
                            failure = e;
                            break;
                        }
                    };
                    mapped_errors(eq, &engine, &c, false, &activity_errors, &mut errors)?;
                    propagate_product_errors(
                        eq,
                        &op,
                        &engine,
                        &c,
                        tau,
                        sigma,
                        &grad_errors,
                        &activity_errors,
                        &mut errors,
                    )?;
                    if !errors.admits(merit) {
                        if anchored && refreshes < 8 {
                            let refresh_start = std::time::Instant::now();
                            refresh_anchors(&op, &control, &mut anchors)?;
                            oracle.observe(
                                "anchor_refresh",
                                refresh_start.elapsed().as_nanos() as u64,
                            );
                            out.work.anchor_products += 2;
                            refreshes += 1;
                            out.work.refreshes += 1;
                            errors = ErrorBudget {
                                anchor_transform: transform_error(eq, &c).map_err(str::to_owned)?,
                                ..ErrorBudget::default()
                            };
                            continue;
                        }
                        failure = "operator_error_budget".into();
                        break;
                    }
                    let (rhs, _) = engine.scaled_row_bounds();
                    let mut next_y = Vec::new();
                    for i in 0..op.rows {
                        let updated = point(anchors.delta_y[i])?
                            .minus(
                                point(sigma)?
                                    .times(
                                        point(activity[i])?
                                            .minus(point(rhs[i])?)
                                            .map_err(str::to_owned)?,
                                    )
                                    .map_err(str::to_owned)?,
                            )
                            .map_err(str::to_owned)?;
                        let h = towards_interval
                            .times(updated)
                            .map_err(str::to_owned)?
                            .plus(
                                back_interval
                                    .times(point(anchors.restart_y[i])?)
                                    .map_err(str::to_owned)?,
                            )
                            .map_err(str::to_owned)?;
                        state_error = state_error.max(h.error());
                        next_y.push(h.rounded);
                    }
                    let mut next_x = Vec::new();
                    for (j, &x) in trial.iter().enumerate() {
                        let h = towards_interval
                            .times(point(x)?)
                            .map_err(str::to_owned)?
                            .plus(
                                back_interval
                                    .times(point(anchors.restart_x[j])?)
                                    .map_err(str::to_owned)?,
                            )
                            .map_err(str::to_owned)?;
                        state_error = state_error.max(h.error());
                        next_x.push(h.rounded);
                    }
                    let dp = crate::research::scale_pow2(1.0, c.primal_exponent);
                    let dd = crate::research::scale_pow2(1.0, c.dual_exponent);
                    let mut published_x = Vec::new();
                    let mut published_y = Vec::new();
                    for (j, &x) in next_x.iter().enumerate() {
                        let sum = point(anchors.base_x[j])?
                            .plus(point(x)?)
                            .map_err(str::to_owned)?;
                        state_error = state_error.max(sum.error());
                        published_x.push(sum.rounded);
                    }
                    for (i, &y) in next_y.iter().enumerate() {
                        let sum = point(anchors.base_y[i])?
                            .plus(point(y)?)
                            .map_err(str::to_owned)?;
                        state_error = state_error.max(sum.error());
                        published_y.push(sum.rounded);
                    }
                    // Bound the resulting primal/dual perturbation in all merit blocks,
                    // including equality and projected-stationarity coupling.
                    let row_norm = scaled_row_norm(&op)?;
                    let factor =
                        Interval::point(6.0)
                            .and_then(|x| {
                                x.times(Interval::point(1.0)?.plus(
                                    Interval::point(sigma)?.times(Interval::point(row_norm)?)?,
                                )?)
                            })
                            .map_err(str::to_owned)?
                            .upper;
                    state_error = Interval::point(state_error)
                        .and_then(|x| x.times(Interval::point(factor)?))
                        .map_err(str::to_owned)?
                        .upper;
                    errors
                        .accumulate(ErrorBudget {
                            state_update: mapped_state_error(eq, &engine, dp, dd, state_error)?,
                            ..ErrorBudget::default()
                        })
                        .map_err(str::to_owned)?;
                    if !errors.admits(merit) {
                        failure = "state_error_budget".into();
                        break;
                    }
                    let (px, py, _, _) = control.buffers();
                    px.copy_from_slice(&published_x);
                    py.copy_from_slice(&published_y);
                    control.commit_steps(1).map_err(str::to_owned)?;
                    anchors.delta_x = next_x;
                    anchors.delta_y = next_y;
                    out.work.committed_updates += 1;
                    let boundary = out
                        .work
                        .physical_updates
                        .is_multiple_of(method.check_interval)
                        || attempt_update == 1999
                        || out.work.physical_updates == method.iteration_limit.min(50000);
                    if boundary {
                        let mut candidate_v = Vec::new();
                        let mut candidate_y = Vec::new();
                        let mut reconstruction = 0.0_f64;
                        for ((&v0, &x), &scale) in out
                            .v
                            .iter()
                            .zip(&published_x)
                            .zip(engine.preconditioner().column())
                        {
                            let change = point(x)?
                                .times(point(scale)?)
                                .map_err(str::to_owned)?
                                .divide_positive(point(dp)?)
                                .map_err(str::to_owned)?;
                            let sum = point(v0)?.plus(change).map_err(str::to_owned)?;
                            reconstruction = reconstruction.max(sum.error());
                            candidate_v.push(sum.rounded);
                        }
                        for ((&y0, &y), &scale) in out
                            .y
                            .iter()
                            .zip(&published_y)
                            .zip(engine.preconditioner().row())
                        {
                            let change = point(y)?
                                .times(point(scale)?)
                                .map_err(str::to_owned)?
                                .divide_positive(point(dd)?)
                                .map_err(str::to_owned)?;
                            let sum = point(y0)?.plus(change).map_err(str::to_owned)?;
                            reconstruction = reconstruction.max(sum.error());
                            candidate_y.push(sum.rounded);
                        }
                        // Account for the final master additions in original units,
                        // including coupling through both orientations.
                        errors
                            .accumulate(ErrorBudget {
                                state_update: original_state_error(eq, reconstruction)?,
                                ..ErrorBudget::default()
                            })
                            .map_err(str::to_owned)?;
                        if !errors.admits(merit) {
                            failure = "master_update_error_budget".into();
                            break;
                        }
                        let assessment_start = std::time::Instant::now();
                        let candidate_merit = eq
                            .merit(&candidate_v, &candidate_y)
                            .map_err(str::to_owned)?;
                        out.work.certifications += 1;
                        let closed = certify(&candidate_v, &candidate_y);
                        oracle.observe(
                            "original_assessments",
                            assessment_start.elapsed().as_nanos() as u64,
                        );
                        let progress = contracts_progress(merit, candidate_merit);
                        last_candidate =
                            Some((candidate_v.clone(), candidate_y.clone(), candidate_merit));
                        let decision = if closed {
                            "certified"
                        } else if progress {
                            "contracted"
                        } else {
                            "continue"
                        };
                        if decision != "continue" {
                            out.trace.push(Progress {
                                correction: out.work.corrections,
                                physical_updates: out.work.physical_updates,
                                width: out.width,
                                anchor_merit: merit,
                                candidate_merit: Some(candidate_merit),
                                errors,
                                decision: decision.into(),
                                anchor_v: out.v.clone(),
                                anchor_y: out.y.clone(),
                                candidate_v: Some(candidate_v.clone()),
                                candidate_y: Some(candidate_y.clone()),
                                generation: op.generation.clone(),
                                primal_exponent: c.primal_exponent,
                                dual_exponent: c.dual_exponent,
                            });
                        }
                        if closed || progress {
                            out.v = candidate_v;
                            out.y = candidate_y;
                            accepted = true;
                            if closed {
                                out.status = "accepted".into();
                                return Ok(());
                            }
                            break;
                        }
                    }
                    if control.check_pending() {
                        let restarts = control.state().restarts;
                        control.continue_after_check();
                        if control.state().restarts != restarts {
                            anchors.restart_x = anchors.delta_x.clone();
                            anchors.restart_y = anchors.delta_y.clone();
                        }
                    }
                    anchors.inner = control.state().clone();
                    anchors.assessment_position = out.work.physical_updates;
                    anchors.errors = errors;
                    errors = ErrorBudget {
                        anchor_transform: transform_error(eq, &c).map_err(str::to_owned)?,
                        ..ErrorBudget::default()
                    };
                }
                if accepted {
                    break;
                }
                out.work.failed_corrections += 1;
                out.trace.push(Progress {
                    correction: out.work.corrections,
                    physical_updates: out.work.physical_updates,
                    width: out.width,
                    anchor_merit: merit,
                    candidate_merit: last_candidate.as_ref().map(|x| x.2),
                    errors,
                    decision: failure.clone(),
                    anchor_v: out.v.clone(),
                    anchor_y: out.y.clone(),
                    candidate_v: last_candidate.as_ref().map(|x| x.0.clone()),
                    candidate_y: last_candidate.as_ref().map(|x| x.1.clone()),
                    generation: op.generation.clone(),
                    primal_exponent: c.primal_exponent,
                    dual_exponent: c.dual_exponent,
                });
                if cancel.is_cancelled() {
                    out.status = "interrupted".into();
                    return Ok(());
                }
                if std::time::Instant::now() >= deadline {
                    out.status = "time_limit".into();
                    return Ok(());
                }
                if out.work.physical_updates >= method.iteration_limit.min(50000) {
                    out.failure = Some("physical_update_limit".into());
                    return Ok(());
                }
                if out.width == ProductWidth::F32 {
                    out.width = ProductWidth::F64;
                    out.work.promotions += 1;
                } else {
                    out.status = "unsupported".into();
                    out.failure = Some(failure);
                    return Ok(());
                }
            }
        }
        out.failure = Some("outer_correction_limit".into());
        Ok(())
    })();
    if let Err(e) = outcome {
        out.status = if e.starts_with("device:") {
            "device_failure"
        } else {
            "unsupported"
        }
        .into();
        out.failure = Some(e);
    }
    out.work.certifications += 1;
    let assessment_start = std::time::Instant::now();
    let _ = certify(&out.v, &out.y);
    oracle.observe(
        "final_original_assessment",
        assessment_start.elapsed().as_nanos() as u64,
    );
    out
}

fn refresh_anchors(
    op: &InnerOperator,
    control: &crate::control::Fp64Controller<'_, '_>,
    a: &mut AnchorState,
) -> Result<(), String> {
    a.validate_generation(op).map_err(str::to_owned)?;
    let state = control.state();
    a.base_x = state.primal.clone();
    a.base_y = state.dual.clone();
    a.primal_products = op.accurate(false, &a.base_x).map_err(str::to_owned)?;
    a.dual_products = op.accurate(true, &a.base_y).map_err(str::to_owned)?;
    a.delta_x.fill(0.0);
    a.delta_y.fill(0.0);
    a.rebase_error = 0.0;
    let mut shifts = Vec::new();
    for (restart, base) in [
        (&state.anchor_primal, &a.base_x),
        (&state.anchor_dual, &a.base_y),
    ] {
        let mut v = Vec::new();
        for (&x, &b) in restart.iter().zip(base) {
            let d = Interval::point(x)
                .and_then(|x| x.minus(Interval::point(b)?))
                .map_err(str::to_owned)?;
            a.rebase_error = a.rebase_error.max(d.error());
            v.push(d.rounded);
        }
        shifts.push(v);
    }
    a.restart_y = shifts.pop().unwrap();
    a.restart_x = shifts.pop().unwrap();
    a.inner = state.clone();
    Ok(())
}
fn mapped_state_error(
    eq: &EqualityBox<'_>,
    engine: &crate::Engine<'_>,
    dp: f64,
    dd: f64,
    error: f64,
) -> Result<f64, String> {
    let mut vx = Vec::new();
    let mut yy = Vec::new();
    let mut maximum = 0.0_f64;
    for (j, &s) in engine.preconditioner().column().iter().enumerate() {
        let x = Interval::point(error)
            .and_then(|x| x.times(Interval::point(s)?))
            .and_then(|x| x.divide_positive(Interval::point(dp)?))
            .map_err(str::to_owned)?;
        maximum = maximum.max(
            x.divide_positive(Interval::point(eq.variable_scale[j]).map_err(str::to_owned)?)
                .map_err(str::to_owned)?
                .upper,
        );
        vx.push(x.upper);
    }
    for &s in engine.preconditioner().row() {
        yy.push(
            Interval::point(error)
                .and_then(|x| x.times(Interval::point(s)?))
                .and_then(|x| x.divide_positive(Interval::point(dd)?))
                .map_err(str::to_owned)?
                .upper,
        );
    }
    let n = eq.original.column_count();
    for i in 0..eq.original.row_count() {
        let (js, vs) = eq.original.row_major().line(i);
        let x = dot(js.iter().zip(vs).map(|(&j, &a)| (a.abs(), vx[j as usize])))?
            .plus(Interval::point(vx[n + i]).map_err(str::to_owned)?)
            .map_err(str::to_owned)?;
        maximum = maximum.max(
            x.divide_positive(eq.primal_scale[i])
                .map_err(str::to_owned)?
                .upper,
        );
    }
    for j in 0..n {
        let (is, vs) = eq.original.column_major().line(j);
        let x = dot(is.iter().zip(vs).map(|(&i, &a)| (a.abs(), yy[i as usize])))
            .map_err(str::to_owned)?;
        maximum = maximum.max(
            x.divide_positive(Interval::point(eq.gradient_scale[j]).map_err(str::to_owned)?)
                .map_err(str::to_owned)?
                .upper,
        );
    }
    for &y in &yy {
        maximum = maximum.max(y);
    }
    // Projection is nonexpansive; changing its primal argument twice costs 2*dx.
    Ok(Interval::point(maximum)
        .and_then(|x| x.times(Interval::point(3.0)?))
        .map_err(str::to_owned)?
        .upper)
}

fn scaled_row_norm(op: &InnerOperator) -> Result<f64, String> {
    let mut maximum = 0.0_f64;
    for i in 0..op.rows {
        let mut sum = op.original_diagonal[i].absolute();
        for k in op.offsets[i] as usize..op.offsets[i + 1] as usize {
            sum = sum
                .plus(op.original_coefficients[k].absolute())
                .map_err(str::to_owned)?;
        }
        maximum = maximum.max(sum.upper);
    }
    Ok(maximum)
}
/// Nonexpansive primal projection and the dual equality update propagate both
/// sparse-product errors through the complete coupled update, before publication.
#[allow(clippy::too_many_arguments)]
fn propagate_product_errors(
    eq: &EqualityBox<'_>,
    op: &InnerOperator,
    engine: &crate::Engine<'_>,
    c: &Correction,
    tau: f64,
    sigma: f64,
    q: &[ErrorBudget],
    p: &[ErrorBudget],
    total: &mut ErrorBudget,
) -> Result<(), String> {
    let select = [
        |e: &ErrorBudget| e.representation,
        |e: &ErrorBudget| e.arithmetic,
        |e: &ErrorBudget| e.anchor_transform,
        |e: &ErrorBudget| e.state_update,
    ];
    let mut propagated = [0.0; 4];
    for (category, get) in select.iter().enumerate() {
        let mut primal = 0.0_f64;
        let mut forward = 0.0_f64;
        for x in q {
            primal = primal.max(get(x));
        }
        for x in p {
            forward = forward.max(get(x));
        }
        let dx = Interval::point(primal)
            .and_then(|x| x.times(Interval::point(tau)?))
            .map_err(str::to_owned)?;
        let dy = Interval::point(2.0)
            .and_then(|x| x.times(dx))
            .and_then(|x| {
                x.times(Interval::point(
                    scaled_row_norm(op).map_err(|_| "norm_range")?,
                )?)
            })
            .and_then(|x| x.plus(Interval::point(forward)?))
            .and_then(|x| x.times(Interval::point(sigma)?))
            .map_err(str::to_owned)?;
        propagated[category] = mapped_state_error(
            eq,
            engine,
            crate::research::scale_pow2(1.0, c.primal_exponent),
            crate::research::scale_pow2(1.0, c.dual_exponent),
            dx.upper.max(dy.upper),
        )?;
    }
    total
        .accumulate(ErrorBudget {
            representation: propagated[0],
            arithmetic: propagated[1],
            anchor_transform: propagated[2],
            state_update: propagated[3],
        })
        .map_err(str::to_owned)?;
    Ok(())
}

/// Opaque same-engine checkpoint; deadline and physical counters are not restored.
#[derive(Clone)]
pub struct Checkpoint<'e, 'p> {
    numerical: crate::control::Fp64Checkpoint<'e, 'p>,
    anchors: AnchorState,
    outer: Outcome,
}
pub fn checkpoint<'e, 'p>(
    controller: &crate::control::Fp64Controller<'e, 'p>,
    anchors: &AnchorState,
    outcome: &Outcome,
) -> Checkpoint<'e, 'p> {
    Checkpoint {
        numerical: controller.checkpoint(),
        anchors: anchors.clone(),
        outer: outcome.clone(),
    }
}
/// Restore numerical and logical state, returning discarded progress for retention.
/// Physical counters, the current deadline and sticky promotion are preserved.
///
/// # Errors
/// Refuses a different operator/engine or a trace outside the snapshot's history.
pub fn restore<'e, 'p>(
    controller: &mut crate::control::Fp64Controller<'e, 'p>,
    anchors: &mut AnchorState,
    outcome: &mut Outcome,
    snapshot: &Checkpoint<'e, 'p>,
    op: &InnerOperator,
) -> Result<Vec<Progress>, &'static str> {
    snapshot.anchors.validate_generation(op)?;
    if !outcome.trace.starts_with(&snapshot.outer.trace) {
        return Err("checkpoint_trace_mismatch");
    }
    controller.restore(&snapshot.numerical)?;
    *anchors = snapshot.anchors.clone();
    // Restore the logical history and return discarded progress to the caller
    // for retention. Every charged counter, deadline and sticky promotion survive.
    let discarded = outcome.trace.split_off(snapshot.outer.trace.len());
    outcome.v = snapshot.outer.v.clone();
    outcome.y = snapshot.outer.y.clone();
    outcome.status = snapshot.outer.status.clone();
    outcome.failure = snapshot.outer.failure.clone();
    outcome.width = if outcome.work.promotions > snapshot.outer.work.promotions {
        ProductWidth::F64
    } else {
        snapshot.outer.width
    };
    Ok(discarded)
}

/// Conservative host preparation envelope within the separate 8-GiB RSS cap,
/// including source input, doubled Vec capacities,
/// canonical/transpose copies, interval guards, checkpoint and promotion coexistence.
pub fn preparation_bytes(
    rows: usize,
    columns: usize,
    nonzeros: usize,
) -> Result<u64, &'static str> {
    let vectors = (rows as u64)
        .checked_mul(2)
        .and_then(|x| x.checked_add(columns as u64))
        .ok_or("memory_overflow")?;
    let bytes = (nonzeros as u64)
        .checked_mul(1024)
        .and_then(|x| x.checked_add(vectors.checked_mul(4096)?))
        .and_then(|x| x.checked_add(128 << 20))
        .ok_or("memory_overflow")?;
    if bytes > 8 << 30 {
        return Err("preparation_memory_limit");
    }
    Ok(bytes)
}

fn original_state_error(eq: &EqualityBox<'_>, error: f64) -> Result<f64, String> {
    let mut maximum = error;
    let n = eq.original.column_count();
    for i in 0..eq.original.row_count() {
        let (_, values) = eq.original.row_major().line(i);
        let sum = dot(values.iter().map(|&a| (a.abs(), error)))
            .and_then(|x| x.plus(Interval::point(error)?))
            .and_then(|x| x.divide_positive(eq.primal_scale[i]))
            .map_err(str::to_owned)?;
        maximum = maximum.max(sum.upper);
    }
    for j in 0..n {
        let (_, values) = eq.original.column_major().line(j);
        let sum = dot(values.iter().map(|&a| (a.abs(), error)))
            .and_then(|x| x.divide_positive(Interval::point(eq.gradient_scale[j])?))
            .map_err(str::to_owned)?;
        maximum = maximum.max(sum.upper);
    }
    Interval::point(maximum)
        .and_then(|x| x.times(Interval::point(3.0)?))
        .map(|x| x.upper)
        .map_err(str::to_owned)
}
fn binding_error(
    eq: &EqualityBox<'_>,
    op: &InnerOperator,
    engine: &crate::Engine<'_>,
    c: &Correction,
    tau: f64,
    sigma: f64,
) -> Result<f64, String> {
    let mut objective = 0.0_f64;
    let mut bounds = 0.0_f64;
    let mut rhs = 0.0_f64;
    let point = Interval::point;
    let (lo, hi) = engine.scaled_column_bounds();
    for (j, &scale) in engine.preconditioner().column().iter().enumerate() {
        let exact = c.objective[j].times(point(scale)?).map_err(str::to_owned)?;
        objective = objective.max(
            exact
                .minus(point(engine.scaled_objective()[j])?)
                .map_err(str::to_owned)?
                .absolute()
                .upper,
        );
        for (limit, actual) in [(c.lower[j], lo[j]), (c.upper[j], hi[j])] {
            if let Some(limit) = limit {
                let exact = limit
                    .divide_positive(point(scale)?)
                    .map_err(str::to_owned)?;
                bounds = bounds.max(
                    exact
                        .minus(point(actual)?)
                        .map_err(str::to_owned)?
                        .absolute()
                        .upper,
                );
            }
        }
    }
    let (row_rhs, _) = engine.scaled_row_bounds();
    for (i, &scale) in engine.preconditioner().row().iter().enumerate() {
        rhs = rhs.max(
            c.rhs[i]
                .times(point(scale)?)
                .and_then(|x| x.minus(point(row_rhs[i])?))
                .map_err(str::to_owned)?
                .absolute()
                .upper,
        );
    }
    let dx = point(objective)?
        .times(point(tau)?)
        .and_then(|x| x.plus(point(bounds)?))
        .map_err(str::to_owned)?;
    let dy = point(2.0)?
        .times(dx)
        .and_then(|x| x.times(point(scaled_row_norm(op).map_err(|_| "norm_range")?)?))
        .and_then(|x| x.plus(point(rhs)?))
        .and_then(|x| x.times(point(sigma)?))
        .map_err(str::to_owned)?;
    mapped_state_error(
        eq,
        engine,
        crate::research::scale_pow2(1.0, c.primal_exponent),
        crate::research::scale_pow2(1.0, c.dual_exponent),
        dx.upper.max(dy.upper),
    )
}

/// Matrix-owned correction preparation. A caller cannot pair an unrelated
/// preconditioner/matrix with the base used to check a rebind.
pub struct PreparedCorrection {
    base: LinearProgram,
    prepared: crate::PreparedMatrix,
}
impl PreparedCorrection {
    pub fn new(base: &LinearProgram, method: optimizer_core::LpSettings) -> Self {
        Self {
            base: base.clone(),
            prepared: crate::PreparedMatrix::new(base, &method),
        }
    }
    pub fn bind<'p>(&self, program: &'p LinearProgram) -> Result<crate::Engine<'p>, &'static str> {
        crate::Engine::rebind_correction(program, &self.base, &self.prepared)
    }
}

/// Check the actual rounded primal/dual steps, including gradual underflow.
/// A nominal margin on their common step is insufficient for subnormal division.
pub fn safe_steps(step: f64, weight: f64, norm: f64) -> Result<(f64, f64), &'static str> {
    if !step.is_finite()
        || !weight.is_finite()
        || !norm.is_finite()
        || step <= 0.0
        || weight <= 0.0
        || norm < 0.0
    {
        return Err("update_step_range");
    }
    let tau = step / weight;
    let sigma = step * weight;
    if !tau.is_finite() || !sigma.is_finite() || tau <= 0.0 || sigma <= 0.0 {
        return Err("update_step_range");
    }
    if norm > 0.0 {
        let bound = Interval::point(tau.sqrt().next_up())?
            .times(Interval::point(sigma.sqrt().next_up())?)?
            .times(Interval::point(norm)?)?;
        if bound.upper >= 1.0 {
            return Err("rounded_step_product_guard");
        }
    }
    Ok((tau, sigma))
}
