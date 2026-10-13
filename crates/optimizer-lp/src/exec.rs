//! ADR-0035 bounded exact binary64 sparse products. No device dependency.
#![allow(missing_docs)]
use crate::{Engine, outward::Enclosure};
use serde::{Deserialize, Serialize};

pub const ID: &str = "lp-exec-v1";
pub const MAX_DIM: usize = 65536;
pub const MAX_NNZ: usize = 1 << 23;
pub const RESIDENT_CAP: u64 = 1 << 30;
pub const PEAK_CAP: u64 = 2 << 30;
pub const INEXACT: u32 = 1;
pub const SUBNORMAL: u32 = 2;
pub const UNDERFLOW: u32 = 4;

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum Mode {
    Cached,
    Uncached,
}

/// ABI: 16 bytes, significand is zero or a normalized 53-bit magnitude.
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
#[repr(C)]
pub struct Decoded {
    pub significand: u64,
    pub exponent: i32,
    pub negative: u32,
}
pub fn decode(bits: u64) -> Result<Decoded, &'static str> {
    let field = ((bits >> 52) & 2047) as i32;
    if field == 2047 {
        return Err("nonfinite_operand");
    }
    let mut m = bits & ((1_u64 << 52) - 1);
    let mut e = -1074;
    if field != 0 {
        m |= 1_u64 << 52;
        e = field - 1075;
    }
    if m != 0 {
        let shift = m.leading_zeros() - 11;
        m <<= shift;
        e -= shift as i32;
    } else {
        e = 0;
    }
    Ok(Decoded {
        significand: m,
        exponent: e,
        negative: (bits >> 63) as u32,
    })
}

#[derive(Clone, Copy, Debug, Default, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Rounded {
    pub bits: u64,
    pub flags: u32,
    pub error_exponent: Option<i32>,
}

#[derive(Clone, Copy, Default)]
struct Acc([u32; 8]);
impl Acc {
    fn add(&mut self, other: Self) {
        let mut carry = 0_u64;
        for (a, b) in self.0.iter_mut().zip(other.0) {
            let v = u64::from(*a) + u64::from(b) + carry;
            *a = v as u32;
            carry = v >> 32;
        }
    }
    fn negate(&mut self) {
        for a in &mut self.0 {
            *a = !*a;
        }
        self.add(Self([1, 0, 0, 0, 0, 0, 0, 0]));
    }
    fn product(a: Decoded, b: Decoded, base: i32) -> Self {
        let product = u128::from(a.significand) * u128::from(b.significand);
        let shift = (a.exponent + b.exponent - base) as usize;
        let mut out = Self::default();
        for i in 0..106 {
            if (product >> i) & 1 != 0 {
                out.0[(i + shift) / 32] |= 1 << ((i + shift) % 32);
            }
        }
        if a.negative != b.negative {
            out.negate();
        }
        out
    }
    fn bit(self, k: i32) -> bool {
        (0..256).contains(&k) && self.0[k as usize / 32] & (1 << (k as usize % 32)) != 0
    }
    fn any_below(self, k: i32) -> bool {
        (0..k.clamp(0, 256)).any(|i| self.bit(i))
    }
    fn rounded(mut self, base: i32) -> Result<Rounded, &'static str> {
        let negative = self.bit(255);
        if negative {
            self.negate();
        }
        let Some(top) = (0..256).rev().find(|&k| self.bit(k)) else {
            return Ok(Rounded::default());
        };
        let unit = (base + top - 52).max(-1074);
        let shift = unit - base;
        let mut m = 0_u64;
        for k in 0..53 {
            if self.bit(shift + k) {
                m |= 1 << k;
            }
        }
        let inexact = self.any_below(shift);
        if self.bit(shift - 1) && (self.any_below(shift - 1) || m & 1 != 0) {
            m += 1;
        }
        let mut unit = unit;
        if m == 1_u64 << 53 {
            m >>= 1;
            unit += 1;
        }
        if unit > 971 {
            return Err("output_overflow");
        }
        let magnitude = if m < 1_u64 << 52 {
            m
        } else {
            (((unit + 1075) as u64) << 52) | (m & ((1_u64 << 52) - 1))
        };
        let tiny = magnitude < 1_u64 << 52;
        let flags = u32::from(inexact) * INEXACT
            + u32::from(tiny && m != 0) * SUBNORMAL
            + u32::from(tiny && inexact) * UNDERFLOW;
        // Match the accepted reference: half an output-lattice ulp when inexact.
        Ok(Rounded {
            bits: magnitude | ((negative as u64) << 63),
            flags,
            error_exponent: inexact.then_some(unit - 1),
        })
    }
}

pub fn dot(left: &[u64], right: &[u64]) -> Result<Rounded, &'static str> {
    if left.len() != right.len() || left.len() > MAX_DIM {
        return Err("dot_dimensions");
    }
    let pairs = left
        .iter()
        .zip(right)
        .map(|(&a, &b)| Ok((decode(a)?, decode(b)?)))
        .collect::<Result<Vec<_>, &str>>()?;
    dot_decoded(&pairs)
}
fn dot_decoded(pairs: &[(Decoded, Decoded)]) -> Result<Rounded, &'static str> {
    let mut lo = i32::MAX;
    let mut hi = i32::MIN;
    for &(a, b) in pairs {
        if a.significand != 0 && b.significand != 0 {
            lo = lo.min(a.exponent + b.exponent);
            hi = hi.max(a.exponent + b.exponent);
        }
    }
    if lo == i32::MAX {
        return Ok(Rounded::default());
    }
    if hi - lo > 128 {
        return Err("product_exponent_window");
    }
    let mut lanes = [Acc::default(); 32];
    for (i, &(a, b)) in pairs.iter().enumerate() {
        if a.significand != 0 && b.significand != 0 {
            lanes[i % 32].add(Acc::product(a, b, lo));
        }
    }
    for step in [16, 8, 4, 2, 1] {
        for i in 0..step {
            let other = lanes[i + step];
            lanes[i].add(other);
        }
    }
    lanes[0].rounded(lo)
}

#[derive(Clone, Debug, PartialEq, Serialize)]
pub struct Receipt {
    pub identity: String,
    pub source: String,
    pub rows: usize,
    pub columns: usize,
    pub nonzeros: usize,
    pub resident_bytes: u64,
    pub peak_bytes: u64,
    pub original_error_infinity: f64,
    pub original_error_one: f64,
}

/// Conservative accounting includes all executor state, guards and vector caches;
/// peak also includes the host engine's two matrix views, packing and hash scratch.
pub fn memory_bytes(m: usize, n: usize, z: usize) -> Result<(u64, u64), &'static str> {
    if m > MAX_DIM || n > MAX_DIM || z > MAX_NNZ {
        return Err("operator_shape");
    }
    let (m, n, z) = (m as u64, n as u64, z as u64);
    let resident = 20 * z + 160 * (m + n) + 4096;
    let peak = resident + 192 * z + 512 * (m + n) + 4096;
    Ok((resident, peak))
}

pub struct Operator {
    source_identity: String,
    scale_identity: String,
    receipt: Receipt,
    coefficients: Vec<u64>,
    row_offsets: Vec<u32>,
    row_indices: Vec<u32>,
    column_offsets: Vec<u32>,
    column_indices: Vec<u32>,
    permutation: Vec<u32>,
    bounds: [f64; 2],
    step: f64,
}

fn quotient_upper(a: f64, b: f64) -> Result<f64, &'static str> {
    if a == 0.0 {
        return Ok(0.0);
    }
    let v = (a / b).next_up();
    if v.is_finite() && b > 0.0 {
        Ok(v)
    } else {
        Err("scaling_error_range")
    }
}
fn add_upper(a: f64, b: f64) -> Result<f64, &'static str> {
    let v = Enclosure::point(a)
        .and_then(|a| a.add(Enclosure::point(b)?))
        .ok_or("scaling_error_range")?
        .upper;
    Ok(v)
}
pub fn prepare_operator(
    engine: &Engine<'_>,
    resident_cap: u64,
    peak_cap: u64,
) -> Result<Operator, &'static str> {
    let p = engine.program();
    let (m, n, z) = (p.row_count(), p.column_count(), p.nonzeros());
    let (resident, peak) = memory_bytes(m, n, z)?;
    if resident > resident_cap.min(RESIDENT_CAP) || peak > peak_cap.min(PEAK_CAP) {
        return Err("operator_memory");
    }
    let r = engine.preconditioner().row();
    let c = engine.preconditioner().column();
    if r.iter().chain(c).any(|x| !x.is_finite() || *x <= 0.0) {
        return Err("invalid_scaling");
    }
    let coefficients = engine
        .scaled_matrix()
        .0
        .iter()
        .map(|x| x.to_bits())
        .collect::<Vec<_>>();
    for &v in &coefficients {
        decode(v)?;
    }
    let row_offsets = (0..=m)
        .map(|i| {
            if i == m {
                z as u32
            } else {
                p.row_major().offset(i) as u32
            }
        })
        .collect::<Vec<_>>();
    let row_indices = p
        .row_major()
        .entries()
        .map(|(_, j, _)| j)
        .collect::<Vec<_>>();
    let column_offsets = (0..=n)
        .map(|i| {
            if i == n {
                z as u32
            } else {
                p.column_major().offset(i) as u32
            }
        })
        .collect::<Vec<_>>();
    let column_indices = p
        .column_major()
        .entries()
        .map(|(_, i, _)| i)
        .collect::<Vec<_>>();
    let mut permutation = vec![0; z];
    let mut next = column_offsets[..n].to_vec();
    let mut row_errors = vec![0.0; m];
    let mut col_errors = vec![0.0; n];
    for (k, (i, j, a)) in p.row_major().entries().enumerate() {
        let j = j as usize;
        permutation[next[j] as usize] = k as u32;
        next[j] += 1;
        // Enclose exact R*A*C, subtract represented coefficient, divide by positive
        // scales outward to bound |R^-1 Ahat C^-1 - A| in original units.
        let ar = Enclosure::product(a, r[i]).ok_or("scaling_error_range")?;
        let lower = Enclosure::product(ar.lower, c[j])
            .ok_or("scaling_error_range")?
            .lower;
        let upper = Enclosure::product(ar.upper, c[j])
            .ok_or("scaling_error_range")?
            .upper;
        let target =
            Enclosure::new(lower, upper, ar.rounded * c[j]).ok_or("scaling_error_range")?;
        let diff = target
            .subtract(
                Enclosure::point(f64::from_bits(coefficients[k])).ok_or("scaling_error_range")?,
            )
            .ok_or("scaling_error_range")?;
        let e = quotient_upper(
            quotient_upper(diff.lower.abs().max(diff.upper.abs()), r[i])?,
            c[j],
        )?;
        row_errors[i] = add_upper(row_errors[i], e)?;
        col_errors[j] = add_upper(col_errors[j], e)?;
    }
    for j in 0..n {
        for k in column_offsets[j] as usize..column_offsets[j + 1] as usize {
            let canonical = permutation[k] as usize;
            if row_indices[canonical] as usize != j
                || canonical < row_offsets[column_indices[k] as usize] as usize
                || canonical >= row_offsets[column_indices[k] as usize + 1] as usize
            {
                return Err("transpose_identity");
            }
        }
    }
    let rows = coefficients
        .iter()
        .map(|&x| f64::from_bits(x))
        .collect::<Vec<_>>();
    let columns = permutation
        .iter()
        .map(|&k| rows[k as usize])
        .collect::<Vec<_>>();
    let norm = crate::precision::norm_bound(engine, &rows, &columns)?;
    let step = if norm == 0.0 {
        engine.step()
    } else {
        engine.step().min((0.9_f64.next_down() / norm).next_down())
    };
    if !step.is_finite() || step <= 0.0 {
        return Err("operator_step_range");
    }
    let mut hasher = Vec::new();
    hasher.extend_from_slice(ID.as_bytes());
    hasher.extend_from_slice(&(m as u64).to_le_bytes());
    hasher.extend_from_slice(&(n as u64).to_le_bytes());
    for values in [
        &row_offsets,
        &row_indices,
        &column_offsets,
        &column_indices,
        &permutation,
    ] {
        for v in values {
            hasher.extend_from_slice(&v.to_le_bytes());
        }
    }
    for &v in &coefficients {
        hasher.extend_from_slice(&v.to_le_bytes());
    }
    for v in r.iter().chain(c) {
        hasher.extend_from_slice(&v.to_bits().to_le_bytes());
    }
    // Original matrix identity distinguishes underflowed/scaled-colliding sources.
    let source_identity = p.matrix_sha256();
    hasher.extend_from_slice(source_identity.as_bytes());
    let scale_bytes = r
        .iter()
        .chain(c)
        .flat_map(|v| v.to_bits().to_le_bytes())
        .collect::<Vec<_>>();
    let scale_identity = optimizer_core::sha256::hex(&scale_bytes);
    let identity = optimizer_core::sha256::hex(&hasher);
    Ok(Operator {
        source_identity,
        scale_identity,
        receipt: Receipt {
            identity,
            source: "rounded_scaled_binary64".into(),
            rows: m,
            columns: n,
            nonzeros: z,
            resident_bytes: resident,
            peak_bytes: peak,
            original_error_infinity: row_errors.into_iter().fold(0.0, f64::max),
            original_error_one: col_errors.into_iter().fold(0.0, f64::max),
        },
        coefficients,
        row_offsets,
        row_indices,
        column_offsets,
        column_indices,
        permutation,
        bounds: [norm, norm],
        step,
    })
}

pub struct PreparedVector {
    identity: String,
    generation: u64,
    transpose: bool,
    values: Vec<Decoded>,
}
pub fn prepare_vector(
    op: &Operator,
    bits: &[u64],
    generation: u64,
    transpose: bool,
) -> Result<PreparedVector, &'static str> {
    let expected = if transpose {
        op.receipt.rows
    } else {
        op.receipt.columns
    };
    if bits.len() != expected {
        return Err("vector_dimension");
    }
    Ok(PreparedVector {
        identity: op.receipt.identity.clone(),
        generation,
        transpose,
        values: bits.iter().map(|&x| decode(x)).collect::<Result<_, _>>()?,
    })
}
impl Operator {
    pub fn apply(&self, v: &PreparedVector, generation: u64) -> Result<Vec<Rounded>, &'static str> {
        self.apply_inner(v, generation, false)
    }
    pub fn apply_transpose(
        &self,
        v: &PreparedVector,
        generation: u64,
    ) -> Result<Vec<Rounded>, &'static str> {
        self.apply_inner(v, generation, true)
    }
    fn apply_inner(
        &self,
        v: &PreparedVector,
        generation: u64,
        transpose: bool,
    ) -> Result<Vec<Rounded>, &'static str> {
        if v.identity != self.receipt.identity
            || v.generation != generation
            || v.transpose != transpose
        {
            return Err("stale_vector");
        }
        let (offsets, indices) = if transpose {
            (&self.column_offsets, &self.column_indices)
        } else {
            (&self.row_offsets, &self.row_indices)
        };
        offsets
            .windows(2)
            .map(|w| {
                let pairs = (w[0]..w[1])
                    .map(|k| {
                        let a = if transpose {
                            self.permutation[k as usize]
                        } else {
                            k
                        };
                        Ok((
                            decode(self.coefficients[a as usize])?,
                            v.values[indices[k as usize] as usize],
                        ))
                    })
                    .collect::<Result<Vec<_>, &str>>()?;
                dot_decoded(&pairs)
            })
            .collect()
    }
}

impl Operator {
    /// Refuse a prepared operator passed with a different engine before allocation.
    pub fn validate_engine(&self, engine: &Engine<'_>) -> Result<(), &'static str> {
        let p = engine.program();
        if (p.row_count(), p.column_count(), p.nonzeros())
            != (
                self.receipt.rows,
                self.receipt.columns,
                self.receipt.nonzeros,
            )
        {
            return Err("operator_engine_identity");
        }
        let scales = engine
            .preconditioner()
            .row()
            .iter()
            .chain(engine.preconditioner().column())
            .flat_map(|v| v.to_bits().to_le_bytes())
            .collect::<Vec<_>>();
        if p.matrix_sha256() != self.source_identity
            || optimizer_core::sha256::hex(&scales) != self.scale_identity
            || !engine
                .scaled_matrix()
                .0
                .iter()
                .map(|v| v.to_bits())
                .eq(self.coefficients.iter().copied())
            || self.step > engine.step()
        {
            return Err("operator_engine_identity");
        }
        Ok(())
    }
    pub fn receipt(&self) -> &Receipt {
        &self.receipt
    }
    pub fn bounds(&self) -> [f64; 2] {
        self.bounds
    }
    pub fn step(&self) -> f64 {
        self.step
    }
    pub fn coefficients(&self) -> &[u64] {
        &self.coefficients
    }
    pub fn row_offsets(&self) -> &[u32] {
        &self.row_offsets
    }
    pub fn row_indices(&self) -> &[u32] {
        &self.row_indices
    }
    pub fn column_offsets(&self) -> &[u32] {
        &self.column_offsets
    }
    pub fn column_indices(&self) -> &[u32] {
        &self.column_indices
    }
    pub fn permutation(&self) -> &[u32] {
        &self.permutation
    }
}

impl<'de> Deserialize<'de> for Mode {
    fn deserialize<D: serde::Deserializer<'de>>(d: D) -> Result<Self, D::Error> {
        match String::deserialize(d)?.as_str() {
            "cached" => Ok(Self::Cached),
            "uncached" => Ok(Self::Uncached),
            _ => Err(serde::de::Error::custom("unknown exec mode")),
        }
    }
}

fn finite(v: f64) -> Result<f64, &'static str> {
    if v.is_finite() {
        Ok(v)
    } else {
        Err("update_nonfinite")
    }
}
fn mul(a: f64, b: f64, _width: optimizer_core::LpWidth) -> Result<f64, &'static str> {
    let p = finite(a * b)?;
    if a != 0.0 && b != 0.0 && p == 0.0 {
        Err("update_lost_nonzero")
    } else {
        Ok(p)
    }
}
fn reference_apply(op: &Operator, transpose: bool, v: &[f64]) -> Result<Vec<f64>, &'static str> {
    let vector = prepare_vector(
        op,
        &v.iter().map(|x| x.to_bits()).collect::<Vec<_>>(),
        0,
        transpose,
    )?;
    let out = if transpose {
        op.apply_transpose(&vector, 0)?
    } else {
        op.apply(&vector, 0)?
    };
    Ok(out.into_iter().map(|x| f64::from_bits(x.bits)).collect())
}
pub fn step(
    engine: &Engine<'_>,
    s: &crate::control::Fp64State,
    op: &Operator,
) -> Result<(Vec<f64>, Vec<f64>), &'static str> {
    use optimizer_core::LpWidth;
    let (xl, xu) = engine.scaled_column_bounds();
    let (yl, yu) = engine.scaled_row_bounds();
    let primal_step = finite(engine.step() / s.weight)?;
    let dual_step = finite(engine.step() * s.weight)?;
    if primal_step == 0.0 || dual_step == 0.0 {
        return Err("update_step_range");
    }
    let toward = (s.since_restart + 1) as f64 / (s.since_restart + 2) as f64;
    let back = 1.0 / (s.since_restart + 2) as f64;
    let mut nx = vec![0.0; s.primal.len()];
    let mut bar = nx.clone();
    let mut ny = vec![0.0; s.dual.len()];
    let transposed = reference_apply(op, true, &s.dual)?;
    for j in 0..nx.len() {
        let dot = transposed[j];
        let diff = finite(engine.scaled_objective()[j] - dot)?;
        let raw = finite(s.primal[j] - mul(primal_step, diff, LpWidth::F64)?)?;
        let next = raw.max(xl[j]).min(xu[j]);
        bar[j] = finite(mul(2.0, next, LpWidth::F64)? - s.primal[j])?;
        nx[j] = finite(
            mul(toward, next, LpWidth::F64)? + mul(back, s.anchor_primal[j], LpWidth::F64)?,
        )?;
    }
    let forward = reference_apply(op, false, &bar)?;
    for (j, out) in ny.iter_mut().enumerate() {
        let dot = forward[j];
        let raw = finite(s.dual[j] - mul(dual_step, dot, LpWidth::F64)?)?;
        let scaled = finite(raw / dual_step)?.max(-yu[j]).min(-yl[j]);
        let next = finite(raw - mul(dual_step, scaled, LpWidth::F64)?)?;
        *out =
            finite(mul(toward, next, LpWidth::F64)? + mul(back, s.anchor_dual[j], LpWidth::F64)?)?;
    }
    Ok((nx, ny))
}

/// Exact device allocation bytes, including zero-length padding and mode-specific caches.
pub fn device_bytes(m: usize, n: usize, z: usize, mode: Mode) -> Result<u64, &'static str> {
    memory_bytes(m, n, z)?;
    let state = [z, 0, n, n, n, m, m, n, m, n, m, n, n, n, m, m]
        .into_iter()
        .map(|n| n.max(1) as u64 * 8)
        .sum::<u64>();
    let indices = [z, z, m + 1, n + 1, 4 * (m + n), z]
        .into_iter()
        .map(|n| n.max(1) as u64 * 4)
        .sum::<u64>();
    let cached = if mode == Mode::Cached {
        (m.max(1) + n.max(1)) as u64 * 16
    } else {
        32
    };
    Ok(state + indices + cached + (m + n).max(1) as u64 * 8)
}

impl<'de> Deserialize<'de> for Receipt {
    fn deserialize<D: serde::Deserializer<'de>>(d: D) -> Result<Self, D::Error> {
        #[derive(Deserialize)]
        #[serde(deny_unknown_fields)]
        struct Fields {
            identity: String,
            source: String,
            rows: usize,
            columns: usize,
            nonzeros: usize,
            resident_bytes: u64,
            peak_bytes: u64,
            original_error_infinity: f64,
            original_error_one: f64,
        }
        struct Visitor;
        impl<'de> serde::de::Visitor<'de> for Visitor {
            type Value = Fields;
            fn expecting(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
                f.write_str("an operator receipt object")
            }
            fn visit_map<M: serde::de::MapAccess<'de>>(self, map: M) -> Result<Fields, M::Error> {
                Fields::deserialize(serde::de::value::MapAccessDeserializer::new(map))
            }
        }
        let f = d.deserialize_map(Visitor)?;
        Ok(Self {
            identity: f.identity,
            source: f.source,
            rows: f.rows,
            columns: f.columns,
            nonzeros: f.nonzeros,
            resident_bytes: f.resident_bytes,
            peak_bytes: f.peak_bytes,
            original_error_infinity: f.original_error_infinity,
            original_error_one: f.original_error_one,
        })
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn exec_fraction_dot_oracle() {
        let fixture: serde_json::Value = serde_json::from_str(include_str!(
            "../../../tests/regression/lp-exec-oracle.json"
        ))
        .unwrap();
        for (i, case) in fixture["cases"].as_array().unwrap().iter().enumerate() {
            let repeat = case["repeat"].as_u64().unwrap() as usize;
            let values = |key: &str| {
                case[key]
                    .as_array()
                    .unwrap()
                    .iter()
                    .map(|v| v.as_u64().unwrap())
                    .collect::<Vec<_>>()
                    .repeat(repeat)
            };
            let actual = dot(&values("left"), &values("right"));
            let expected = &case["expected"];
            if let Some(error) = expected.get("error") {
                assert_eq!(actual.unwrap_err(), error.as_str().unwrap(), "case {i}");
            } else {
                assert_eq!(
                    actual.unwrap(),
                    serde_json::from_value(expected.clone()).unwrap(),
                    "case {i}"
                );
            }
        }
    }
    #[test]
    fn exec_memory_and_decode_boundaries() {
        assert_eq!(std::mem::size_of::<Decoded>(), 16);
        assert!(memory_bytes(MAX_DIM + 1, 0, 0).is_err());
        assert!(memory_bytes(0, 0, MAX_NNZ + 1).is_err());
        let (resident, peak) = memory_bytes(MAX_DIM, MAX_DIM, MAX_NNZ).unwrap();
        assert!(resident < RESIDENT_CAP && peak < PEAK_CAP);
        for b in [0, 1, 1 << 63, u64::MAX >> 1, 0x7fefffffffffffff] {
            if let Ok(d) = decode(b) {
                assert!(d.significand == 0 || (1 << 52..1 << 53).contains(&d.significand));
            }
        }
    }
}
