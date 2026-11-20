//! One canonical FP4 representation shared by both sparse orientations.
//! Memory is O(nonzeros + rows + columns), including rectangular empty axes.
use crate::Result;
use optimizer_lp::{Compressed, Engine};
use serde::{Deserialize, Serialize};
use std::borrow::Cow;

pub const MAX_DIMENSION: usize = 250_000_000;
pub const MAX_NONZEROS: usize = 1_000_000_000;
pub const BLOCK: usize = 32;

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum Format {
    Native,
    Fp32,
    Fp4x1,
    Fp4x2,
    /// Actual Tensor Core backend only; legacy sparse operators reject these.
    Fp4x3,
    Fp4x4,
}
impl Format {
    pub fn components(self) -> usize {
        match self {
            Self::Fp4x1 => 1,
            Self::Fp4x2 => 2,
            Self::Fp4x3 => 3,
            Self::Fp4x4 => 4,
            _ => 0,
        }
    }
    pub fn promote(self) -> Self {
        match self {
            Self::Fp4x1 => Self::Fp4x2,
            Self::Fp4x2 => Self::Fp32,
            _ => Self::Native,
        }
    }
}
#[derive(Clone, Debug, Serialize)]
pub struct Orientation<'a> {
    pub offsets: Vec<u32>,
    pub indices: Cow<'a, [u32]>,
    pub original: Cow<'a, [f64]>,
    /// IDs in the canonical row-major coefficient representation.
    pub ids: Vec<u32>,
}
#[derive(Clone, Debug, Serialize)]
pub struct Operator<'a> {
    pub prepared: Format,
    pub rows: Orientation<'a>,
    pub columns: Orientation<'a>,
    pub codes: Vec<u8>,
    pub exponents: Vec<[i32; 2]>,
    pub fp32: Vec<f32>,
}
#[derive(Clone, Debug, Serialize)]
pub struct Product {
    pub values: Vec<f64>,
    pub bounds: Vec<f64>,
}
pub fn decode(code: u8) -> f64 {
    let x = [0., 0.5, 1., 1.5, 2., 3., 4., 6.][usize::from(code & 7)];
    if code & 8 == 0 { x } else { -x }
}
fn quantize(value: f64) -> u8 {
    let mut best = 0u8;
    let mut error = value.abs();
    // Normal E2M1 only; ties choose the even magnitude code, including zero.
    for c in 2..=7u8 {
        let e = (value.abs() - decode(c)).abs();
        if e < error || (e == error && c % 2 == 0 && !best.is_multiple_of(2)) {
            best = c;
            error = e;
        }
    }
    best | if value < 0. && best != 0 { 8 } else { 0 }
}
fn up_add(a: f64, b: f64) -> f64 {
    (a + b).next_up()
}
fn up_mul(a: f64, b: f64) -> f64 {
    (a * b).next_up()
}
fn gamma(count: usize, unit: f64) -> f64 {
    let x = up_mul(count as f64, unit);
    (x / (1. - x).next_down()).next_up()
}
fn orientation(matrix: &Compressed, values: &[f64]) -> Orientation<'static> {
    Orientation {
        offsets: (0..=matrix.lines())
            .map(|i| matrix.offset(i) as u32)
            .collect(),
        indices: matrix.entries().map(|(_, j, _)| j).collect(),
        original: Cow::Owned(values.to_vec()),
        ids: Vec::new(),
    }
}
impl<'a> Operator<'a> {
    /// Borrow immutable native geometry and scaled values for the array executor.
    /// Only the compact u32 offsets are owned; all coefficient/index arrays remain
    /// alive in the engine/program throughout packing, upload and host checking.
    pub fn borrowed_native(engine: &'a Engine<'_>) -> Result<Self> {
        let p = engine.program();
        if p.row_count().max(p.column_count()) > MAX_DIMENSION || p.nonzeros() > MAX_NONZEROS {
            return Err("operator resource domain".into());
        }
        let (r, c) = engine.scaled_matrix();
        if r.iter()
            .chain(c)
            .any(|v| !v.is_finite() || v.abs() > 2f64.powi(40))
        {
            return Err("scaled coefficient domain".into());
        }
        let view = |matrix: &'a Compressed, values: &'a [f64]| Orientation {
            offsets: matrix.arrays().0.iter().map(|&i| i as u32).collect(),
            indices: Cow::Borrowed(matrix.arrays().1),
            original: Cow::Borrowed(values),
            ids: Vec::new(),
        };
        Ok(Self {
            prepared: Format::Native,
            rows: view(p.row_major(), r),
            columns: view(p.column_major(), c),
            codes: Vec::new(),
            exponents: Vec::new(),
            fp32: Vec::new(),
        })
    }
    pub fn new(engine: &Engine<'_>) -> Result<Self> {
        Self::new_for(engine, Format::Fp4x1)
    }
    pub fn new_for(engine: &Engine<'_>, prepared: Format) -> Result<Self> {
        if prepared.components() > 2 {
            return Err("multi-component format requires tensor backend".into());
        }
        let p = engine.program();
        if p.row_count().max(p.column_count()) > MAX_DIMENSION || p.nonzeros() > MAX_NONZEROS {
            return Err("operator resource domain".into());
        }
        let (r, c) = engine.scaled_matrix();
        if r.iter()
            .chain(c)
            .any(|v| !v.is_finite() || v.abs() > 2f64.powi(40))
        {
            return Err("scaled coefficient domain".into());
        }
        let mut rows = orientation(p.row_major(), r);
        let mut columns = orientation(p.column_major(), c);
        if prepared == Format::Native {
            return Ok(Self {
                prepared,
                rows,
                columns,
                codes: Vec::new(),
                exponents: Vec::new(),
                fp32: Vec::new(),
            });
        }
        rows.ids = (0..r.len() as u32).collect();
        columns.ids = vec![0; r.len()];
        let mut cursor = columns.offsets[..p.column_count()].to_vec();
        for (id, &column) in rows.indices.iter().enumerate() {
            let slot = &mut cursor[column as usize];
            columns.ids[*slot as usize] = id as u32;
            *slot += 1;
        }
        // A transpose is a permutation of the same represented coefficients.
        if columns
            .original
            .iter()
            .zip(&columns.ids)
            .any(|(&v, &i)| v.to_bits() != r[i as usize].to_bits())
        {
            return Err("noncanonical scaled transpose".into());
        }
        if prepared == Format::Fp32 {
            return Ok(Self {
                prepared,
                rows,
                columns,
                codes: Vec::new(),
                exponents: Vec::new(),
                fp32: r.iter().map(|v| *v as f32).collect(),
            });
        }
        let mut codes = vec![0; r.len()];
        let mut exponents = Vec::new();
        for (block, source) in r.chunks(BLOCK).enumerate() {
            let mut residual = source.to_vec();
            let mut scales = [0; 2];
            for (plane, exponent) in scales.iter_mut().enumerate() {
                let max = residual.iter().map(|x| x.abs()).fold(0., f64::max);
                let mut e = if max == 0. {
                    -48
                } else {
                    (max.log2().floor() as i32 - 2).max(-48)
                };
                if max > 6. * 2f64.powi(e) {
                    e += 1;
                }
                if e > 48 {
                    return Err("FP4 exponent domain".into());
                }
                *exponent = e;
                let scale = 2f64.powi(e);
                for (j, v) in residual.iter_mut().enumerate() {
                    let code = quantize(*v / scale);
                    codes[block * BLOCK + j] |= code << (4 * plane);
                    *v -= decode(code) * scale;
                }
            }
            exponents.push(scales);
        }
        Ok(Self {
            prepared,
            rows,
            columns,
            codes,
            exponents,
            fp32: r.iter().map(|v| *v as f32).collect(),
        })
    }
    pub fn supports(&self, format: Format) -> bool {
        match format {
            Format::Native => true,
            Format::Fp32 => self.prepared != Format::Native,
            Format::Fp4x2 => matches!(self.prepared, Format::Fp4x1 | Format::Fp4x2),
            Format::Fp4x1 => self.prepared == Format::Fp4x1,
            Format::Fp4x3 | Format::Fp4x4 => false,
        }
    }
    pub fn orientation(&self, transpose: bool) -> &Orientation<'_> {
        if transpose { &self.columns } else { &self.rows }
    }
    pub fn parts(&self, id: usize, format: Format) -> [f64; 2] {
        match format {
            Format::Fp4x3 | Format::Fp4x4 => {
                panic!("multi-component format requires tensor backend")
            }
            Format::Native => [self.rows.original[id], 0.],
            Format::Fp32 => [f64::from(self.fp32[id]), 0.],
            Format::Fp4x1 | Format::Fp4x2 => {
                let e = self.exponents[id / BLOCK];
                [
                    decode(self.codes[id] & 15) * 2f64.powi(e[0]),
                    if format == Format::Fp4x2 {
                        decode(self.codes[id] >> 4) * 2f64.powi(e[1])
                    } else {
                        0.
                    },
                ]
            }
        }
    }
    pub fn storage_bytes(&self) -> usize {
        [&self.rows, &self.columns]
            .iter()
            .map(|m| {
                m.offsets.len() * 4 + m.indices.len() * 4 + m.original.len() * 8 + m.ids.len() * 4
            })
            .sum::<usize>()
            + self.codes.len()
            + self.exponents.len() * 8
            + self.fp32.len() * 4
    }

    /// Per output: coefficient error L1, component L1, FP32 roundoff factor.
    pub fn metadata(&self, transpose: bool, format: Format) -> Vec<f64> {
        let m = self.orientation(transpose);
        if format == Format::Native {
            return vec![0.; 3 * (m.offsets.len() - 1)];
        }
        let mut out = Vec::with_capacity(3 * (m.offsets.len() - 1));
        for range in m.offsets.windows(2) {
            let (mut error, mut magnitude) = (0.0, 0.0);
            for q in range[0] as usize..range[1] as usize {
                let parts = self.parts(m.ids[q] as usize, format);
                let round = up_add(
                    up_mul(f64::EPSILON / 2.0, up_add(parts[0].abs(), parts[1].abs())),
                    f64::from_bits(1),
                );
                error = up_add(
                    error,
                    up_add(
                        (m.original[q] - (parts[0] + parts[1])).abs().next_up(),
                        round,
                    ),
                );
                magnitude = up_add(magnitude, up_add(parts[0].abs(), parts[1].abs()));
            }
            out.extend([
                error,
                magnitude,
                up_mul(
                    gamma(
                        (range[1] - range[0]) as usize * 4 + 32,
                        f64::from(f32::EPSILON) / 2.0,
                    ),
                    magnitude,
                ),
            ]);
        }
        out
    }
    pub fn native(&self, transpose: bool, vector: &[f64]) -> Result<Vec<f64>> {
        self.check_vector(transpose, vector)?;
        let m = self.orientation(transpose);
        Ok(m.offsets
            .windows(2)
            .map(|range| {
                let terms: Vec<_> = (range[0] as usize..range[1] as usize)
                    .map(|q| m.original[q] * vector[m.indices[q] as usize])
                    .collect();
                optimizer_lp::tree_sum(&terms)
            })
            .collect())
    }
    fn check_vector(&self, transpose: bool, x: &[f64]) -> Result<()> {
        let expected = if transpose {
            self.rows.offsets.len() - 1
        } else {
            self.columns.offsets.len() - 1
        };
        if x.len() != expected || x.iter().any(|v| !v.is_finite() || v.abs() > 2f64.powi(40)) {
            return Err("vector shape/finite domain".into());
        }
        Ok(())
    }
    /// Bound the exact scaled-original A*x, including reference accumulation.
    /// This is a local product contract; the final checker uses the original LP.
    pub fn product(
        &self,
        transpose: bool,
        x: &[f64],
        anchor: &[f64],
        format: Format,
    ) -> Result<Product> {
        self.check_vector(transpose, x)?;
        self.check_vector(transpose, anchor)?;
        if !self.supports(format) {
            return Err("unprepared product format".into());
        }
        if format == Format::Native {
            // Use the original operator; retain an enclosure for differential checks.
            return self.product_native_bound(transpose, x);
        }
        let reference = self.native(transpose, anchor)?;
        let mut delta = Vec::with_capacity(x.len());
        let (mut max_delta, mut max_error, mut max_float, mut max_anchor) =
            (0f64, 0f64, 0f64, 0f64);
        for (&v, &a) in x.iter().zip(anchor) {
            let d = v - a;
            let f = d as f32;
            let round = up_add(
                up_mul(f64::EPSILON / 2., up_add(v.abs(), a.abs())),
                f64::from_bits(1),
            );
            max_delta = max_delta.max(up_add(d.abs(), round));
            max_error = max_error.max(up_add((d - f64::from(f)).abs(), round));
            max_float = max_float.max(f64::from(f).abs());
            max_anchor = max_anchor.max(a.abs());
            delta.push(f);
        }
        let m = self.orientation(transpose);
        let mut values = Vec::new();
        let mut bounds = Vec::new();
        for (row, range) in m.offsets.windows(2).enumerate() {
            let (mut sum, mut magnitude, mut error, mut original) = (0f32, 0f64, 0f64, 0f64);
            let count = (range[1] - range[0]) as usize;
            for q in range[0] as usize..range[1] as usize {
                let parts = self.parts(m.ids[q] as usize, format);
                let represented = parts[0] + parts[1];
                let repr_round = up_add(
                    up_mul(f64::EPSILON / 2., up_add(parts[0].abs(), parts[1].abs())),
                    f64::from_bits(1),
                );
                let coeff_error = up_add((m.original[q] - represented).abs().next_up(), repr_round);
                error = up_add(error, coeff_error);
                magnitude = up_add(magnitude, up_add(parts[0].abs(), parts[1].abs()));
                original = up_add(original, m.original[q].abs());
                for part in parts {
                    sum += (part as f32) * delta[m.indices[q] as usize];
                }
            }
            let value = reference[row] + f64::from(sum);
            let mut bound = up_mul(
                up_mul(gamma(count * 2 + 32, f64::EPSILON / 2.), original),
                max_anchor,
            );
            bound = up_add(bound, up_mul(error, max_delta));
            bound = up_add(bound, up_mul(magnitude, max_error));
            bound = up_add(
                bound,
                up_mul(
                    up_mul(
                        gamma(count * 4 + 32, f64::from(f32::EPSILON) / 2.),
                        magnitude,
                    ),
                    max_float,
                ),
            );
            bound = up_add(bound, up_mul((count * 4 + 32) as f64, 2f64.powi(-149)));
            bound = up_add(
                bound,
                up_add(
                    up_mul(
                        f64::EPSILON / 2.,
                        up_add(reference[row].abs(), f64::from(sum).abs()),
                    ),
                    2f64.powi(-1000),
                ),
            );
            if !value.is_finite() || !bound.is_finite() {
                return Err("nonfinite product".into());
            }
            values.push(value);
            bounds.push(bound);
        }
        Ok(Product { values, bounds })
    }
    fn product_native_bound(&self, transpose: bool, x: &[f64]) -> Result<Product> {
        let values = self.native(transpose, x)?;
        let m = self.orientation(transpose);
        let maximum = x.iter().map(|v| v.abs()).fold(0., f64::max);
        let bounds = m
            .offsets
            .windows(2)
            .map(|r| {
                let norm = m.original[r[0] as usize..r[1] as usize]
                    .iter()
                    .fold(0., |s, v| up_add(s, v.abs()));
                up_add(
                    up_mul(
                        up_mul(
                            gamma((r[1] - r[0]) as usize * 2 + 32, f64::EPSILON / 2.),
                            norm,
                        ),
                        maximum,
                    ),
                    2f64.powi(-1000),
                )
            })
            .collect();
        Ok(Product { values, bounds })
    }
}

#[cfg(test)]
mod borrowed_tests {
    use super::*;
    use crate::tensor::{Config, Packed};
    use optimizer_core::ObjectiveSense;
    use optimizer_lp::{LinearProgram, LpSettings, Range};

    #[test]
    fn borrowed_native_preserves_products_and_packing_without_array_copies() {
        for (m, n) in [(33usize, 65usize), (65, 33)] {
            let mut offsets = vec![0];
            let mut indices = Vec::new();
            let mut values = Vec::new();
            for i in 0..m {
                if i + 1 < m {
                    for j in 0..n - 1 {
                        indices.push(j as u32);
                        values.push(((i * 17 + j * 23) % 31 + 1) as f64 / 16.);
                    }
                }
                offsets.push(indices.len());
            }
            let bound = Range {
                lower: -1.,
                upper: 1.,
            };
            let p = LinearProgram::from_csr(
                (0..n as u32).collect(),
                vec![bound; n],
                vec![bound; m],
                offsets,
                indices,
                values,
                &[],
                &[],
                ObjectiveSense::Minimize,
                0.,
            )
            .unwrap();
            let engine = Engine::new(&p, LpSettings::published(100, 100));
            let owned = Operator::new_for(&engine, Format::Native).unwrap();
            let borrowed = Operator::borrowed_native(&engine).unwrap();
            assert_eq!(
                serde_json::to_value(&owned).unwrap(),
                serde_json::to_value(&borrowed).unwrap()
            );
            for transpose in [false, true] {
                let view = borrowed.orientation(transpose);
                let matrix = if transpose {
                    p.column_major()
                } else {
                    p.row_major()
                };
                let coefficients = if transpose {
                    engine.scaled_matrix().1
                } else {
                    engine.scaled_matrix().0
                };
                assert!(matches!(view.indices, Cow::Borrowed(_)));
                assert!(matches!(view.original, Cow::Borrowed(_)));
                assert_eq!(view.indices.as_ptr(), matrix.arrays().1.as_ptr());
                assert_eq!(view.original.as_ptr(), coefficients.as_ptr());
                let x: Vec<_> = (0..if transpose { m } else { n })
                    .map(|i| (i as f64 - 19.) / 8.)
                    .collect();
                assert_eq!(
                    owned
                        .native(transpose, &x)
                        .unwrap()
                        .iter()
                        .map(|v| v.to_bits())
                        .collect::<Vec<_>>(),
                    borrowed
                        .native(transpose, &x)
                        .unwrap()
                        .iter()
                        .map(|v| v.to_bits())
                        .collect::<Vec<_>>()
                );
            }
            for components in 1..=4 {
                let config = Config {
                    components,
                    ..Config::default()
                };
                let a = Packed::proposal(&owned, &config).unwrap();
                let b = Packed::proposal(&borrowed, &config).unwrap();
                assert!(a.tile_count > 0);
                assert_eq!(
                    serde_json::to_value(a).unwrap(),
                    serde_json::to_value(b).unwrap()
                );
            }
        }
    }
}
