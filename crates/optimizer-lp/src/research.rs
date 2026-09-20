//! ADR-0021 research arithmetic. Exact representation is not mathematical authority.
use crate::{Engine, LinearProgram, outward::Enclosure, precision::norm_bound};
use serde::{Deserialize, Serialize};

/// Frozen research configurations; no runtime backend selector uses this enum.
#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize)]
#[serde(rename_all = "kebab-case")]
pub enum Mode {
    /// Native FP64 control in the research executor.
    DefaultFp64,
    /// Power-of-two scaled FP64 matrix.
    Power2Fp64,
    /// Power-of-two scaled, exactly representable FP32 matrix.
    Power2Fp32,
    /// Factored original FP64 coefficients.
    FactoredFp64,
    /// Factored exactly representable FP32 coefficients.
    FactoredFp32,
    /// Two components reconstructed for FP64 multiplication.
    Components2Fp64,
    /// Three components reconstructed for FP64 multiplication.
    Components3Fp64,
    /// Two components and four FP32 cross-products with residual recovery.
    Components2Fp32,
    /// Three components and nine FP32 cross-products with residual recovery.
    Components3Fp32,
    /// ADR-0022: native FP64 with range guards on the integer pipe, six launches.
    IntguardFp64,
    /// ADR-0022: native FP64, integer guards, sparse product fused with its update.
    FusedFp64,
    /// ADR-0022: unevaluated FP32 pairs for coefficients and operands, fused.
    DoublefloatFp32,
}
impl<'de> Deserialize<'de> for Mode {
    fn deserialize<D: serde::Deserializer<'de>>(d: D) -> Result<Self, D::Error> {
        match String::deserialize(d)?.as_str() {
            "default-fp64" => Ok(Self::DefaultFp64),
            "power2-fp64" => Ok(Self::Power2Fp64),
            "power2-fp32" => Ok(Self::Power2Fp32),
            "factored-fp64" => Ok(Self::FactoredFp64),
            "factored-fp32" => Ok(Self::FactoredFp32),
            "components2-fp64" => Ok(Self::Components2Fp64),
            "components3-fp64" => Ok(Self::Components3Fp64),
            "components2-fp32" => Ok(Self::Components2Fp32),
            "components3-fp32" => Ok(Self::Components3Fp32),
            "intguard-fp64" => Ok(Self::IntguardFp64),
            "fused-fp64" => Ok(Self::FusedFp64),
            "doublefloat-fp32" => Ok(Self::DoublefloatFp32),
            _ => Err(serde::de::Error::custom("unknown research mode")),
        }
    }
}
impl Mode {
    /// Number of stored components, or zero for ordinary storage.
    pub fn components(self) -> usize {
        match self {
            Self::Components2Fp64 | Self::Components2Fp32 => 2,
            Self::Components3Fp64 | Self::Components3Fp32 => 3,
            _ => 0,
        }
    }
    /// Factored diagonal application.
    pub fn factored(self) -> bool {
        matches!(self, Self::FactoredFp64 | Self::FactoredFp32)
    }
    /// Explicit power-of-two preconditioning.
    pub fn power2(self) -> bool {
        matches!(self, Self::Power2Fp64 | Self::Power2Fp32)
    }
    /// Direct FP32 coefficient storage.
    pub fn storage32(self) -> bool {
        matches!(self, Self::Power2Fp32 | Self::FactoredFp32)
    }
    /// FP32 cross-products.
    pub fn cross(self) -> bool {
        matches!(self, Self::Components2Fp32 | Self::Components3Fp32)
    }
    /// ADR-0022 modes require research-v2 requests and evidence.
    pub fn v2(self) -> bool {
        matches!(
            self,
            Self::IntguardFp64 | Self::FusedFp64 | Self::DoublefloatFp32
        )
    }
    /// Sparse product fused with its vector update and store: two launches per step.
    pub fn fused(self) -> bool {
        matches!(self, Self::FusedFp64 | Self::DoublefloatFp32)
    }
    /// Unevaluated FP32 pair arithmetic without FP64 inside the sparse loop.
    pub fn doublefloat(self) -> bool {
        matches!(self, Self::DoublefloatFp32)
    }
    /// Kernel launches charged per proposed step.
    pub fn launches_per_step(self) -> u64 {
        if self.fused() { 2 } else { 6 }
    }
    /// Fused primal/dual entry points, when the mode is fused.
    pub fn fused_kernels(self) -> Option<(&'static str, &'static str)> {
        match self {
            Self::FusedFp64 => Some(("research_fused_primal_64", "research_fused_dual_64")),
            Self::DoublefloatFp32 => Some(("research_fused_primal_df", "research_fused_dual_df")),
            _ => None,
        }
    }
    /// Kernel entry point binding arithmetic to its code identity; the sparse
    /// kernel for separate schedules, the fused primal kernel otherwise.
    pub fn kernel(self) -> &'static str {
        match self {
            Self::DefaultFp64 | Self::Power2Fp64 => "research_native64",
            Self::Power2Fp32 => "research_native32",
            Self::FactoredFp64 => "research_factored64",
            Self::FactoredFp32 => "research_factored32",
            Self::Components2Fp64 => "research_components2_native",
            Self::Components3Fp64 => "research_components3_native",
            Self::Components2Fp32 => "research_components2_cross",
            Self::Components3Fp32 => "research_components3_cross",
            Self::IntguardFp64 => "research_intguard64",
            Self::FusedFp64 => "research_fused_primal_64",
            Self::DoublefloatFp32 => "research_fused_primal_df",
        }
    }
}
/// Unevaluated FP32 pair: `hi + lo` with `|lo| <= ulp(hi) / 2`.
#[repr(C)]
#[derive(Clone, Copy, Debug, Default, PartialEq)]
pub struct Pair {
    /// Nearest-even FP32 of the represented value.
    pub hi: f32,
    /// Nearest-even FP32 of the remaining difference.
    pub lo: f32,
}
impl Pair {
    /// Split a binary64 value; `hi` is the nearest binary32.
    pub fn split(x: f64) -> Self {
        let hi = x as f32;
        let lo = (x - f64::from(hi)) as f32;
        Self { hi, lo }
    }
    /// Exact binary64 value of the pair.
    pub fn value(self) -> f64 {
        f64::from(self.hi) + f64::from(self.lo)
    }
    fn two_sum(a: f32, b: f32) -> Self {
        let s = a + b;
        let bb = s - a;
        Self {
            hi: s,
            lo: (a - (s - bb)) + (b - bb),
        }
    }
    fn quick_two_sum(a: f32, b: f32) -> Self {
        let s = a + b;
        Self {
            hi: s,
            lo: b - (s - a),
        }
    }
    /// Error-free FP32 pair addition in the fixed device order.
    pub fn plus(self, other: Self) -> Self {
        let s = Self::two_sum(self.hi, other.hi);
        let t = Self::two_sum(self.lo, other.lo);
        let s = Self::quick_two_sum(s.hi, s.lo + t.hi);
        Self::quick_two_sum(s.hi, s.lo + t.lo)
    }
    /// One FP32 multiply and three FMAs; the `lo*lo` term is dropped.
    pub fn times(self, other: Self) -> Self {
        let p = self.hi * other.hi;
        let e = self.hi.mul_add(other.hi, -p);
        let e = self.hi.mul_add(other.lo, e);
        let e = self.lo.mul_add(other.hi, e);
        Self::quick_two_sum(p, e)
    }
}
/// Device-compatible exact normalized expansion; exponent is an integer.
#[repr(C)]
#[derive(Clone, Copy, Debug, Default, PartialEq)]
pub struct Parts3 {
    /// Successive nearest-even normalized components.
    pub parts: [f32; 3],
    /// Power-of-two exponent.
    pub exponent: i32,
}
/// Device-compatible truncated expansion.
#[repr(C)]
#[derive(Clone, Copy, Debug, Default, PartialEq)]
pub struct Parts2 {
    /// First two components; omitted third is the recorded approximation.
    pub parts: [f32; 2],
    /// Power-of-two exponent.
    pub exponent: i32,
}
/// Exact binary64 normalization, including subnormals and signed zero.
pub fn normalize(x: f64) -> (f64, i32) {
    if x == 0.0 || !x.is_finite() {
        return (x, 0);
    }
    let (x, adjustment) = if x.abs() < f64::MIN_POSITIVE {
        (x * 18014398509481984.0, -54)
    } else {
        (x, 0)
    };
    let b = x.to_bits();
    (
        f64::from_bits((b & 0x800f_ffff_ffff_ffff) | (1022_u64 << 52)),
        ((b >> 52) & 2047) as i32 - 1022 + adjustment,
    )
}
/// One rounding at subnormal restoration; never form an overflowing 2^1024 factor.
pub fn scale_pow2(x: f64, e: i32) -> f64 {
    if x == 0.0 || !x.is_finite() {
        return x;
    }
    let (m, k) = normalize(x);
    let k = i64::from(k) + i64::from(e);
    if k > 1024 {
        return f64::INFINITY.copysign(x);
    }
    if k < -1074 {
        return 0.0_f64.copysign(x);
    }
    if k == 1024 {
        return (m * f64::from_bits(2046_u64 << 52)) * 2.0;
    }
    if k >= -1021 {
        return m * f64::from_bits(((k + 1023) as u64) << 52);
    }
    (m * f64::from_bits(((k + 1074 + 1023) as u64) << 52)) * f64::from_bits(1)
}
/// Reject every finite coefficient bit lost during exponent adjustment.
pub fn exact_scale(x: f64, e: i32) -> Result<f64, &'static str> {
    let y = scale_pow2(x, e);
    if !x.is_finite()
        || !y.is_finite()
        || e == i32::MIN
        || scale_pow2(y, -e).to_bits() != x.to_bits()
    {
        Err("inexact_power2_scaling")
    } else {
        Ok(y)
    }
}
/// Nearest power in logarithmic distance using an exact integer square comparison.
pub fn power_exponent(x: f64) -> Result<i32, &'static str> {
    if !x.is_finite() || x <= 0.0 {
        return Err("scale_range");
    }
    let (m, e) = normalize(x);
    let significand = u128::from((m.to_bits() & 0x000f_ffff_ffff_ffff) | (1_u64 << 52));
    Ok(if significand * significand > (1_u128 << 105) {
        e
    } else {
        e - 1
    })
}
/// Split all 53 significand bits without depending on the original exponent range.
pub fn split(x: f64) -> Result<Parts3, &'static str> {
    if !x.is_finite() {
        return Err("component_nonfinite");
    }
    let (m, e) = normalize(x);
    let h = m as f32;
    let r = m - f64::from(h);
    let mid = r as f32;
    let low = (r - f64::from(mid)) as f32;
    Ok(Parts3 {
        parts: [h, mid, low],
        exponent: e,
    })
}
/// Reconstruct two or three components before applying the shared exponent.
pub fn reconstruct(p: Parts3, k: usize) -> f64 {
    if p.parts[0] == 0.0 {
        return f64::from(p.parts[0]);
    }
    scale_pow2(p.parts[..k].iter().map(|&v| f64::from(v)).sum(), p.exponent)
}
/// FP64 TwoSum compensation in a fixed order.
fn add_compensated(s: &mut f64, c: &mut f64, v: f64) {
    let t = *s + v;
    let z = t - *s;
    let error = (*s - (t - z)) + (v - z);
    *c += error;
    *s = t;
}
/// Independent scalar component-product oracle, using explicit CPU FMA residuals.
pub fn component_product(a: f64, b: f64, k: usize, cross: bool) -> Result<f64, &'static str> {
    if k != 2 && k != 3 {
        return Err("component_count");
    }
    let a = split(a)?;
    let b = split(b)?;
    let value = if cross {
        let (mut s, mut c) = (0.0, 0.0);
        for &x in &a.parts[..k] {
            for &y in &b.parts[..k] {
                let p = x * y;
                let q = x.mul_add(y, -p);
                add_compensated(&mut s, &mut c, f64::from(p));
                add_compensated(&mut s, &mut c, f64::from(q));
            }
        }
        scale_pow2(s + c, a.exponent + b.exponent)
    } else {
        reconstruct(a, k) * reconstruct(b, k)
    };
    if !value.is_finite() {
        Err("product_nonfinite")
    } else if a.parts[0] != 0.0 && b.parts[0] != 0.0 && value == 0.0 {
        Err("product_lost_nonzero")
    } else {
        Ok(value)
    }
}
/// Permute a canonical coefficient array; neither orientation is recomputed.
pub fn transpose<T: Copy>(p: &LinearProgram, rows: &[T]) -> Vec<T> {
    let mut map = std::collections::BTreeMap::new();
    for ((r, c, _), &v) in p.row_major().entries().zip(rows) {
        map.insert((r, c as usize), v);
    }
    p.column_major()
        .entries()
        .map(|(c, r, _)| map[&(r as usize, c)])
        .collect()
}
/// Admitted immutable research matrix and conservative step information.
///
/// An operator is a pure function of the program's matrix, the preconditioner
/// and the spectral step: every field below derives from coefficients and
/// scales, and none derives from a bound or the objective. Under SPEC-0014
/// requirement 7 it is therefore part of what a repeated-solve session may
/// reuse across solves that differ only in variable bounds, which is what lets
/// the research path admit it once at session open.
pub struct Operator {
    /// Arithmetic identity.
    pub mode: Mode,
    /// Canonical stored coefficient source, before component packing.
    pub rows: Vec<f64>,
    /// Exact permutation of the same source.
    pub columns: Vec<f64>,
    /// Bounds for original/represented operators.
    pub bounds: [f64; 2],
    /// Conservative restricted step.
    pub step: f64,
    /// Maximum discarded matrix component in original scaled units.
    pub matrix_tail_max: f64,
}
impl Operator {
    /// Admit operator and step before any allocation on the device.
    ///
    /// Admission reads only the matrix, the preconditioner and the engine's
    /// step — the scaled matrix values, the diagonals for a factored mode, and
    /// norm bounds of coefficient arrays. It holds no bound- or
    /// objective-derived state, so one admission serves every solve of a
    /// session whose variants differ only in variable bounds.
    pub fn new(engine: &Engine<'_>, mode: Mode) -> Result<Self, &'static str> {
        let p = engine.program();
        let rows = if mode.factored() {
            p.row_major().entries().map(|(_, _, v)| v).collect()
        } else {
            engine.scaled_matrix().0.to_vec()
        };
        if rows.iter().any(|v| !v.is_finite()) {
            return Err("matrix_nonfinite");
        }
        if mode.storage32() && rows.iter().any(|&v| f64::from(v as f32) != v) {
            return Err("matrix_not_exact_fp32");
        }
        if mode.doublefloat()
            && rows.iter().any(|&v| {
                let hi = v as f32;
                !hi.is_finite() || (v != 0.0 && (hi == 0.0 || !hi.is_normal()))
            })
        {
            return Err("matrix_doublefloat_range");
        }
        let columns = transpose(p, &rows);
        let mut represented = Vec::new();
        let mut error = 0.0_f64;
        for ((r, c, _), &v) in p.row_major().entries().zip(&rows) {
            let value = if mode.factored() {
                Enclosure::product(v.abs(), engine.preconditioner().row()[r])
                    .and_then(|a| {
                        Enclosure::product(a.upper, engine.preconditioner().column()[c as usize])
                    })
                    .ok_or("factored_bound_range")?
                    .upper
            } else if mode.components() > 0 {
                let q = reconstruct(split(v)?, mode.components());
                error = error.max((v - q).abs());
                q
            } else if mode.doublefloat() {
                let q = Pair::split(v).value();
                error = error.max((v - q).abs());
                q
            } else {
                v
            };
            represented.push(value);
        }
        let bounds = [
            norm_bound(engine, engine.scaled_matrix().0, engine.scaled_matrix().1)?,
            norm_bound(engine, &represented, &transpose(p, &represented))?,
        ];
        let bound = bounds[0].max(bounds[1]);
        let step = if bound == 0.0 {
            engine.step()
        } else {
            engine.step().min((0.9_f64.next_down() / bound).next_down())
        };
        if !step.is_finite() || step <= 0.0 {
            return Err("operator_step_range");
        }
        Ok(Self {
            mode,
            rows,
            columns,
            bounds,
            step,
            matrix_tail_max: error,
        })
    }
}

fn finite(v: f64) -> Result<f64, &'static str> {
    if v.is_finite() {
        Ok(v)
    } else {
        Err("intermediate_nonfinite")
    }
}
fn mul(a: f64, b: f64, _width: optimizer_core::LpWidth) -> Result<f64, &'static str> {
    let v = finite(a * b)?;
    if a != 0.0 && b != 0.0 && v == 0.0 {
        Err("product_lost_nonzero")
    } else {
        Ok(v)
    }
}
impl Operator {
    /// Independent lane-strided CPU application for device differential checks.
    pub fn apply(
        &self,
        engine: &Engine<'_>,
        transposed: bool,
        vector: &[f64],
    ) -> Result<Vec<f64>, &'static str> {
        use optimizer_core::LpWidth::F64;
        if self.mode.doublefloat() {
            return self.apply_doublefloat(engine, transposed, vector);
        }
        let p = engine.program();
        let (matrix, values, outer, inner) = if transposed {
            (
                p.column_major(),
                &self.columns,
                engine.preconditioner().column(),
                engine.preconditioner().row(),
            )
        } else {
            (
                p.row_major(),
                &self.rows,
                engine.preconditioner().row(),
                engine.preconditioner().column(),
            )
        };
        let mut out = Vec::new();
        for (line, &outer_scale) in outer.iter().enumerate().take(matrix.lines()) {
            let (indices, _) = matrix.line(line);
            let start = matrix.offset(line);
            let mut lanes = [0.0; 32];
            for (lane, sum) in lanes.iter_mut().enumerate() {
                for i in (lane..indices.len()).step_by(32) {
                    let index = indices[i] as usize;
                    let mut x = finite(vector[index])?;
                    if self.mode.factored() {
                        x = mul(x, inner[index], F64)?;
                    }
                    let a = values[start + i];
                    let value = if self.mode.components() > 0 {
                        component_product(a, x, self.mode.components(), self.mode.cross())?
                    } else {
                        mul(a, x, F64)?
                    };
                    *sum = finite(*sum + value)?;
                }
            }
            for offset in [16, 8, 4, 2, 1] {
                for lane in 0..offset {
                    lanes[lane] = finite(lanes[lane] + lanes[lane + offset])?;
                }
            }
            out.push(if self.mode.factored() {
                mul(lanes[0], outer_scale, F64)?
            } else {
                lanes[0]
            });
        }
        Ok(out)
    }
}

impl Operator {
    /// Lane-strided FP32-pair application mirroring the fused double-float kernels.
    fn apply_doublefloat(
        &self,
        engine: &Engine<'_>,
        transposed: bool,
        vector: &[f64],
    ) -> Result<Vec<f64>, &'static str> {
        let p = engine.program();
        let (matrix, values) = if transposed {
            (p.column_major(), &self.columns)
        } else {
            (p.row_major(), &self.rows)
        };
        let split = vector
            .iter()
            .map(|&x| {
                let v = finite(x)?;
                let pair = Pair::split(v);
                if v != 0.0 && pair.hi == 0.0 {
                    Err("operand_lost_nonzero")
                } else {
                    Ok(pair)
                }
            })
            .collect::<Result<Vec<_>, _>>()?;
        let mut out = Vec::new();
        for line in 0..matrix.lines() {
            let (indices, _) = matrix.line(line);
            let start = matrix.offset(line);
            let mut lanes = [Pair::default(); 32];
            for (lane, sum) in lanes.iter_mut().enumerate() {
                for i in (lane..indices.len()).step_by(32) {
                    let a = Pair::split(values[start + i]);
                    let b = split[indices[i] as usize];
                    let product = a.times(b);
                    if !product.hi.is_finite() {
                        return Err("intermediate_nonfinite");
                    }
                    if a.hi != 0.0 && b.hi != 0.0 && product.hi == 0.0 {
                        return Err("product_lost_nonzero");
                    }
                    *sum = sum.plus(product);
                    if !sum.hi.is_finite() {
                        return Err("intermediate_nonfinite");
                    }
                }
            }
            for offset in [16, 8, 4, 2, 1] {
                for lane in 0..offset {
                    lanes[lane] = lanes[lane].plus(lanes[lane + offset]);
                    if !lanes[lane].hi.is_finite() {
                        return Err("intermediate_nonfinite");
                    }
                }
            }
            out.push(finite(lanes[0].value())?);
        }
        Ok(out)
    }
}

/// Independent CPU update with the research operator and fixed FP64 vector arithmetic.
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
    let transposed = op.apply(engine, true, &s.dual)?;
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
    let forward = op.apply(engine, false, &bar)?;
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
