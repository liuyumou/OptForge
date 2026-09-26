//! Host precision oracle and conservative represented-operator admission (ADR-0019).
//! None of these iteration diagnostics grants a certificate.
use crate::{control::Fp64State, outward::Enclosure, pdhg::Engine};
use optimizer_core::{LpPrecisionSettings, LpWidth};

/// Canonical represented matrix with a transpose derived from the same values.
pub struct PrecisionOperator {
    /// Row-major represented coefficients, widened exactly for host inspection.
    pub rows: Vec<f64>,
    /// Column-major permutation of the same represented coefficients.
    pub columns: Vec<f64>,
    /// Outward original and represented spectral-norm upper bounds.
    pub bounds: [f64; 2],
    /// Step no larger than the original or the conservative operator limit.
    pub step: f64,
    /// Largest scaled coefficient conversion error.
    pub max_error: f64,
    /// Represented binary32 subnormal coefficients.
    pub subnormals: u64,
}
/// Checked narrowing; finite nonzero input must not disappear.
pub fn narrow(value: f64) -> Result<f64, &'static str> {
    let converted = f64::from(value as f32);
    if !value.is_finite() || !converted.is_finite() {
        Err("conversion_nonfinite")
    } else if value != 0.0 && converted == 0.0 {
        Err("conversion_lost_nonzero")
    } else {
        Ok(converted)
    }
}
fn finite(value: f64) -> Result<f64, &'static str> {
    if value.is_finite() {
        Ok(value)
    } else {
        Err("update_nonfinite")
    }
}
fn mul(a: f64, b: f64, width: LpWidth) -> Result<f64, &'static str> {
    let (a, b) = if width == LpWidth::F32 {
        (narrow(a)?, narrow(b)?)
    } else {
        (a, b)
    };
    let p = if width == LpWidth::F32 {
        f64::from((a as f32) * (b as f32))
    } else {
        a * b
    };
    if !p.is_finite() {
        Err("product_nonfinite")
    } else if a != 0.0 && b != 0.0 && p == 0.0 {
        Err("product_lost_nonzero")
    } else {
        Ok(p)
    }
}
pub(crate) fn norm_bound(
    engine: &Engine<'_>,
    rows: &[f64],
    cols: &[f64],
) -> Result<f64, &'static str> {
    let _component_scope = optimizer_core::lp_cost::scope("conservative_norm_guard");
    let program = engine.program();
    let maximum =
        |matrix: &crate::problem::Compressed, values: &[f64]| -> Result<f64, &'static str> {
            let mut result = 0.0_f64;
            for line in 0..matrix.lines() {
                let (indices, _) = matrix.line(line);
                let begin = matrix.offset(line);
                let mut sum = Enclosure::ZERO;
                for value in &values[begin..begin + indices.len()] {
                    sum = sum
                        .add(Enclosure::point(value.abs()).ok_or("operator_nonfinite")?)
                        .ok_or("operator_bound_overflow")?;
                }
                result = result.max(sum.upper);
            }
            Ok(result)
        };
    let row = maximum(program.row_major(), rows)?;
    let col = maximum(program.column_major(), cols)?;
    if row == 0.0 || col == 0.0 {
        return Ok(0.0);
    }
    // sqrt factors avoid overflowing the product of finite induced norms.
    let result = Enclosure::product(row.sqrt().next_up(), col.sqrt().next_up())
        .ok_or("operator_bound_overflow")?
        .upper;
    finite(result)
}
impl PrecisionOperator {
    /// Convert rows once and permute; never independently quantize the transpose.
    pub fn new(engine: &Engine<'_>, settings: &LpPrecisionSettings) -> Result<Self, &'static str> {
        let _component_scope = optimizer_core::lp_cost::scope("precision_operator_preparation");
        settings.validate().map_err(|_| "invalid_precision")?;
        let (original_rows, original_cols) = engine.scaled_matrix();
        let rows: Vec<f64> = original_rows
            .iter()
            .map(|&v| {
                if settings.matrix == LpWidth::F32 {
                    narrow(v)
                } else {
                    finite(v)
                }
            })
            .collect::<Result<_, _>>()?;
        let p = engine.program();
        let mut canonical = std::collections::BTreeMap::new();
        for ((r, c, _), v) in p.row_major().entries().zip(&rows) {
            canonical.insert((r, c as usize), *v);
        }
        let columns = p
            .column_major()
            .entries()
            .map(|(c, r, _)| canonical[&(r as usize, c)])
            .collect::<Vec<_>>();
        let bounds = [
            norm_bound(engine, original_rows, original_cols)?,
            norm_bound(engine, &rows, &columns)?,
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
        let max_error = rows
            .iter()
            .zip(original_rows)
            .map(|(a, b)| (a - b).abs())
            .fold(0.0, f64::max);
        let subnormals = if settings.matrix == LpWidth::F32 {
            rows.iter()
                .filter(|&&v| v != 0.0 && v.abs() < f64::from(f32::MIN_POSITIVE))
                .count() as u64
        } else {
            0
        };
        Ok(Self {
            rows,
            columns,
            bounds,
            step,
            max_error,
            subnormals,
        })
    }
}
/// Independent scalar mirror of the documented lane-strided, fixed-tree product.
pub fn product(
    values: &[f64],
    indices: &[u32],
    vector: &[f64],
    products: LpWidth,
    accumulation: LpWidth,
) -> Result<f64, &'static str> {
    let mut lanes = [0.0; 32];
    let add = |a: f64, b: f64| {
        finite(if accumulation == LpWidth::F32 {
            f64::from((a as f32) + (b as f32))
        } else {
            a + b
        })
    };
    for (lane, out) in lanes.iter_mut().enumerate() {
        for k in (lane..values.len()).step_by(32) {
            *out = add(*out, mul(values[k], vector[indices[k] as usize], products)?)?;
        }
    }
    for offset in [16, 8, 4, 2, 1] {
        for lane in 0..offset {
            lanes[lane] = add(lanes[lane], lanes[lane + offset])?;
        }
    }
    Ok(lanes[0])
}
/// One FP64 update on the original scaled operator, with fixed warp32 order.
/// The caller owns work accounting and endpoint adoption.
pub fn correction(
    engine: &Engine<'_>,
    state: &Fp64State,
) -> Result<(Vec<f64>, Vec<f64>), &'static str> {
    let _component_scope = optimizer_core::lp_cost::scope("reference_fp64_update");
    let (rows, cols) = engine.scaled_matrix();
    step(engine, state, rows, cols, LpWidth::F64, LpWidth::F64)
}
/// Host differential oracle for a represented sparse step (before state storage).
pub fn step(
    engine: &Engine<'_>,
    s: &Fp64State,
    rows: &[f64],
    cols: &[f64],
    products: LpWidth,
    accumulation: LpWidth,
) -> Result<(Vec<f64>, Vec<f64>), &'static str> {
    let _component_scope = optimizer_core::lp_cost::scope("cpu_arithmetic_update");
    let p = engine.program();
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
    for j in 0..nx.len() {
        let (idx, _) = p.column_major().line(j);
        let start = p.column_major().offset(j);
        let dot = product(
            &cols[start..start + idx.len()],
            idx,
            &s.dual,
            products,
            accumulation,
        )?;
        let diff = finite(engine.scaled_objective()[j] - dot)?;
        let raw = finite(s.primal[j] - mul(primal_step, diff, LpWidth::F64)?)?;
        let next = raw.max(xl[j]).min(xu[j]);
        bar[j] = finite(mul(2.0, next, LpWidth::F64)? - s.primal[j])?;
        nx[j] = finite(
            mul(toward, next, LpWidth::F64)? + mul(back, s.anchor_primal[j], LpWidth::F64)?,
        )?;
    }
    for (j, out) in ny.iter_mut().enumerate() {
        let (idx, _) = p.row_major().line(j);
        let start = p.row_major().offset(j);
        let dot = product(
            &rows[start..start + idx.len()],
            idx,
            &bar,
            products,
            accumulation,
        )?;
        let raw = finite(s.dual[j] - mul(dual_step, dot, LpWidth::F64)?)?;
        let scaled = finite(raw / dual_step)?.max(-yu[j]).min(-yl[j]);
        let next = finite(raw - mul(dual_step, scaled, LpWidth::F64)?)?;
        *out =
            finite(mul(toward, next, LpWidth::F64)? + mul(back, s.anchor_dual[j], LpWidth::F64)?)?;
    }
    Ok((nx, ny))
}
