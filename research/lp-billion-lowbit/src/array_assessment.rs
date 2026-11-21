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
    let objective = objective(a, x)?;
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
fn objective(a: &Original, x: &[f64]) -> Result<f64> {
    if x.len() != a.program.column_count() {
        return Err("candidate domain".into());
    }
    let mut objective = 0.;
    for (&j, &v) in a.objective_indices.iter().zip(&a.objective_values) {
        objective = finite(objective + finite(v * finite(x[j as usize])?)?)?;
    }
    finite(objective + a.offset)
}
pub struct Assessor<'a> {
    original: &'a Original,
    store: &'a Store,
    parallel: bool,
    pub cached_calls: usize,
    pub cpu_feasibility_confirmations: usize,
}
impl<'a> Assessor<'a> {
    pub fn new(original: &'a Original, store: &'a Store, parallel: bool) -> Self {
        Self {
            original,
            store,
            parallel,
            cached_calls: 0,
            cpu_feasibility_confirmations: 0,
        }
    }
    fn assess(
        &mut self,
        x: &[f64],
        y: &[f64],
        tolerance: f64,
        gpu: &mut impl FnMut(&[f64], f64) -> Result<Option<bool>>,
    ) -> Result<Value> {
        if y.len() != self.original.program.row_count() {
            return Err("dual dimensions".into());
        }
        let p = &self.original.program;
        let device_feasible = gpu(x, tolerance)?;
        let (feasible, objective) = match device_feasible {
            Some(feasible) => (feasible, objective(self.original, x)?),
            None => feasibility(self.original, x, tolerance, self.parallel)?,
        };
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
        // A GPU diagnostic can never grant certificate acceptance on its own.
        if device_feasible.is_some() && feasible && gap.as_ref().is_some_and(|g| g.closed) {
            let (host_feasible, host_objective) =
                feasibility(self.original, x, tolerance, self.parallel)?;
            self.cpu_feasibility_confirmations += 1;
            if !host_feasible || host_objective.to_bits() != objective.to_bits() {
                return Err("GPU feasibility disagrees with independent CPU acceptance".into());
            }
        }
        Ok(
            json!({"accepted":feasible && gap.as_ref().is_some_and(|g|g.closed),"feasible":feasible,
            "objective":objective,"bound":bound,"gap_upper":gap.map(|g|g.upper),"tolerance":tolerance}),
        )
    }
    pub fn evaluate(&mut self, x: &[f64], y: &[f64], t: f64, _further: bool) -> Result<Value> {
        self.evaluate_with_feasibility(x, y, t, |_, _| Ok(None))
    }
    pub fn evaluate_with_feasibility(
        &mut self,
        x: &[f64],
        y: &[f64],
        t: f64,
        mut gpu: impl FnMut(&[f64], f64) -> Result<Option<bool>>,
    ) -> Result<Value> {
        self.cached_calls += 1;
        let mut result = self.assess(x, y, t, &mut gpu)?;
        if result["feasible"] == true
            && result["bound"].is_null()
            && let Some((witness, corrections)) = crate::repair::propose(&self.original.program, y)
        {
            result = self.assess(x, &witness, t, &mut gpu)?;
            result["certificate_dual_array"] = serde_json::to_value(self.store.write(&witness)?)?;
            result["dual_corrections"] = json!(corrections);
        }
        Ok(result)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use optimizer_core::ObjectiveSense;
    use optimizer_lp::{LinearProgram, Range};
    #[test]
    fn untrusted_feasibility_cannot_grant_a_false_certificate() {
        let original = Original {
            program: LinearProgram::from_csr(
                vec![7],
                vec![Range {
                    lower: 0.,
                    upper: 1.,
                }],
                vec![Range {
                    lower: 0.,
                    upper: 1.,
                }],
                vec![0, 1],
                vec![0],
                vec![1.],
                &[],
                &[],
                ObjectiveSense::Minimize,
                0.,
            )
            .unwrap(),
            row_ids: vec![11],
            model_id: "acceptance-test".into(),
            objective_indices: vec![],
            objective_values: vec![],
            offset: 0.,
            sha256: String::new(),
        };
        let path = std::env::temp_dir().join(format!(
            "gpu-feasibility-{}-{}",
            std::process::id(),
            std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap()
                .as_nanos()
        ));
        std::fs::create_dir(&path).unwrap();
        let store = Store::new(&path).unwrap();
        let mut assessor = Assessor::new(&original, &store, true);
        let expected = assessor.evaluate(&[0.5], &[0.], 1e-9, false).unwrap();
        assert_eq!(expected["accepted"], true);
        assert_eq!(
            assessor
                .evaluate_with_feasibility(&[0.5], &[0.], 1e-9, |_, _| Ok(Some(true)))
                .unwrap(),
            expected
        );
        assert_eq!(assessor.cpu_feasibility_confirmations, 1);
        assert!(
            assessor
                .evaluate_with_feasibility(&[2.], &[0.], 1e-9, |_, _| Ok(Some(true)))
                .is_err()
        );
        assert_eq!(
            assessor
                .evaluate_with_feasibility(&[0.5], &[0.], 1e-9, |_, _| Ok(Some(false)))
                .unwrap()["accepted"],
            false
        );
        std::fs::remove_dir_all(path).unwrap();
    }
}
