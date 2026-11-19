//! Original-order feasibility with bounded row scratch; unchanged dual enclosure.
use crate::{
    Result,
    array_input::{Original, Store},
};
use optimizer_core::Tolerances;
use optimizer_lp::{certify, certify::assess_gap};
use serde_json::{Value, json};

fn finite(v: f64) -> Result<f64> {
    if v.is_finite() {
        Ok(if v == 0. { 0. } else { v })
    } else {
        Err("nonfinite original feasibility arithmetic".into())
    }
}
fn bound(b: f64, lower: bool, v: f64, magnitude: f64, t: f64) -> Result<bool> {
    if !b.is_finite() {
        return Ok(true);
    }
    let violation = if lower && v < b {
        finite(b - v)?
    } else if !lower && v > b {
        finite(v - b)?
    } else {
        0.
    };
    let relative = finite(t * v.abs().max(b.abs()).max(magnitude))?;
    Ok(violation <= finite(t + relative)?)
}
pub fn feasibility(a: &Original, x: &[f64], t: f64, parallel: bool) -> Result<(bool, f64)> {
    let p = &a.program;
    if x.len() != p.column_count() || !t.is_finite() || t < 0. || x.iter().any(|v| !v.is_finite()) {
        return Err("candidate domain".into());
    }
    let mut feasible = true;
    for (&v, r) in x.iter().zip(p.columns()) {
        let v = finite(v)?;
        let lo = bound(r.lower, true, v, v.abs(), t)?;
        let hi = bound(r.upper, false, v, v.abs(), t)?;
        feasible &= lo && hi;
    }
    let mut objective = 0.;
    for (&j, &v) in a.objective_indices.iter().zip(&a.objective_values) {
        objective = finite(objective + finite(v * finite(x[j as usize])?)?)?;
    }
    objective = finite(objective + a.offset)?;
    let rows = |start, end| -> std::result::Result<bool, String> {
        (|| -> Result<bool> {
            let mut feasible = true;
            for i in start..end {
                let (indices, coefficients) = p.row_major().line(i);
                let (mut sum, mut magnitude) = (0., 0.);
                for (&j, &c) in indices.iter().zip(coefficients) {
                    let product = finite(c * finite(x[j as usize])?)?;
                    sum = finite(sum + product)?;
                    magnitude = finite(magnitude + product.abs())?;
                }
                let lo = bound(p.rows()[i].lower, true, sum, magnitude, t)?;
                let hi = bound(p.rows()[i].upper, false, sum, magnitude, t)?;
                feasible &= lo && hi;
            }
            Ok(feasible)
        })()
        .map_err(|e| e.to_string())
    };
    if parallel && p.nonzeros() >= 65536 {
        let results = std::thread::scope(|scope| {
            (0..4)
                .map(|w| {
                    let rows = &rows;
                    scope.spawn(move || rows(p.row_count() * w / 4, p.row_count() * (w + 1) / 4))
                })
                .collect::<Vec<_>>()
                .into_iter()
                .map(|h| h.join().expect("feasibility worker"))
                .collect::<Vec<_>>()
        });
        for r in results {
            feasible &= r?;
        }
    } else {
        feasible &= rows(0, p.row_count())?;
    }
    Ok((feasible, objective))
}
pub struct Assessor<'a> {
    original: &'a Original,
    store: &'a Store,
    parallel: bool,
    pub cached_calls: usize,
}
impl<'a> Assessor<'a> {
    pub fn new(original: &'a Original, store: &'a Store, parallel: bool) -> Self {
        Self {
            original,
            store,
            parallel,
            cached_calls: 0,
        }
    }
    fn assess(&self, x: &[f64], y: &[f64], tolerance: f64) -> Result<Value> {
        if y.len() != self.original.program.row_count() {
            return Err("dual dimensions".into());
        }
        let p = &self.original.program;
        let (feasible, objective) = feasibility(self.original, x, tolerance, self.parallel)?;
        let bound = if self.parallel {
            crate::bounded_certificate::certify(p, y)
        } else {
            certify(p, y)
        }
        .ok()
        .map(|v| v.bound);
        let t = Tolerances {
            absolute: tolerance,
            relative: tolerance,
            integrality: tolerance,
        };
        let gap = bound.and_then(|b| assess_gap(p, x, b, t));
        Ok(
            json!({"accepted":feasible && gap.as_ref().is_some_and(|g|g.closed),"feasible":feasible,
            "objective":objective,"bound":bound,"gap_upper":gap.map(|g|g.upper),"tolerance":tolerance}),
        )
    }
    pub fn evaluate(&mut self, x: &[f64], y: &[f64], t: f64, _further: bool) -> Result<Value> {
        self.cached_calls += 1;
        let mut result = self.assess(x, y, t)?;
        if result["feasible"] == true
            && result["bound"].is_null()
            && let Some((witness, corrections)) = crate::repair::propose(&self.original.program, y)
        {
            result = self.assess(x, &witness, t)?;
            result["certificate_dual_array"] = serde_json::to_value(self.store.write(&witness)?)?;
            result["dual_corrections"] = json!(corrections);
        }
        Ok(result)
    }
}
