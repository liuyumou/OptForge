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
    feasibility_workers(a, x, t, if parallel { 4 } else { 1 }, false)
}
fn feasibility_workers(
    a: &Original,
    x: &[f64],
    t: f64,
    workers: usize,
    weighted: bool,
) -> Result<(bool, f64)> {
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
    if workers > 1 && p.nonzeros() >= 65536 {
        let ranges = if weighted {
            crate::work_partition::sparse(p.row_major().arrays().0, workers)
        } else {
            (0..workers)
                .map(|w| p.row_count() * w / workers..p.row_count() * (w + 1) / workers)
                .collect()
        };
        let results = std::thread::scope(|scope| {
            ranges
                .into_iter()
                .map(|range| {
                    let rows = &rows;
                    scope.spawn(move || rows(range.start, range.end))
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
pub(crate) struct DeferredAssessment {
    value: Value,
    repaired_dual: Option<Vec<f64>>,
}
pub struct Assessor<'a> {
    original: &'a Original,
    store: &'a Store,
    parallel: bool,
    certificate_scratch: bool,
    workspace: Option<crate::certificate_workspace::Workspace>,
    fast_workspace: Option<crate::certificate_fast::Workspace>,
    workers: usize,
    pub cached_calls: usize,
    pub cpu_feasibility_confirmations: usize,
}
impl<'a> Assessor<'a> {
    pub fn new(original: &'a Original, store: &'a Store, parallel: bool) -> Self {
        Self {
            original,
            store,
            parallel,
            certificate_scratch: false,
            workspace: None,
            fast_workspace: None,
            workers: if parallel { 4 } else { 1 },
            cached_calls: 0,
            cpu_feasibility_confirmations: 0,
        }
    }
    /// Enable the opt-in scratch candidate for this assessor.
    pub fn with_certificate_scratch(mut self, enabled: bool) -> Self {
        self.certificate_scratch = enabled;
        self
    }
    pub fn with_workspace(mut self, enabled: bool, workers: usize) -> Self {
        assert!((1..=4).contains(&workers));
        self.workers = if self.parallel { workers } else { 1 };
        self.workspace =
            enabled.then(|| crate::certificate_workspace::Workspace::new(self.workers));
        self
    }
    pub fn with_exact_product(mut self, enabled: bool, workers: usize) -> Self {
        assert!((1..=4).contains(&workers));
        if enabled {
            self.workers = if self.parallel { workers } else { 1 };
            self.workspace = None;
            self.fast_workspace = Some(crate::certificate_fast::Workspace::new(self.workers));
        } else {
            self.fast_workspace = None;
        }
        self
    }
    pub fn retained_workspace_bytes(&self) -> usize {
        self.workspace
            .as_ref()
            .map_or(0, crate::certificate_workspace::Workspace::retained_bytes)
            + self
                .fast_workspace
                .as_ref()
                .map_or(0, crate::certificate_fast::Workspace::retained_bytes)
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
        let device_feasible = gpu(x, tolerance)?;
        let (feasible, objective) = match device_feasible {
            Some(feasible) => (feasible, objective(self.original, x)?),
            None => feasibility_workers(
                self.original,
                x,
                tolerance,
                self.workers,
                self.workspace.is_some() || self.fast_workspace.is_some(),
            )?,
        };
        let bound = self.dual_bound(y);
        self.finish(x, tolerance, device_feasible, feasible, objective, bound)
    }
    fn dual_bound(&mut self, y: &[f64]) -> Option<f64> {
        let p = &self.original.program;
        if let Some(workspace) = &mut self.fast_workspace {
            workspace.certify(p, y)
        } else if let Some(workspace) = &mut self.workspace {
            workspace.certify(p, y)
        } else if self.parallel && self.certificate_scratch {
            crate::scratch_certificate::certify(p, y)
        } else if self.parallel {
            crate::bounded_certificate::certify(p, y)
        } else {
            certify(p, y)
        }
        .ok()
        .map(|v| v.bound)
    }
    fn finish(
        &mut self,
        x: &[f64],
        tolerance: f64,
        device_feasible: Option<bool>,
        feasible: bool,
        objective: f64,
        bound: Option<f64>,
    ) -> Result<Value> {
        let p = &self.original.program;
        let t = Tolerances {
            absolute: tolerance,
            relative: tolerance,
            integrality: tolerance,
        };
        let gap = bound.and_then(|b| assess_gap(p, x, b, t));
        // A GPU diagnostic can never grant certificate acceptance on its own.
        if device_feasible.is_some() && feasible && gap.as_ref().is_some_and(|g| g.closed) {
            let (host_feasible, host_objective) = feasibility_workers(
                self.original,
                x,
                tolerance,
                self.workers,
                self.workspace.is_some() || self.fast_workspace.is_some(),
            )?;
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
        gpu: impl FnMut(&[f64], f64) -> Result<Option<bool>>,
    ) -> Result<Value> {
        let result = self.evaluate_deferred(x, y, t, gpu)?;
        self.publish(result)
    }
    pub(crate) fn evaluate_deferred(
        &mut self,
        x: &[f64],
        y: &[f64],
        t: f64,
        mut gpu: impl FnMut(&[f64], f64) -> Result<Option<bool>>,
    ) -> Result<DeferredAssessment> {
        self.cached_calls += 1;
        let mut repaired_dual = None;
        let mut result = self.assess(x, y, t, &mut gpu)?;
        if result["feasible"] == true
            && result["bound"].is_null()
            && let Some((witness, corrections)) = crate::repair::propose(&self.original.program, y)
        {
            result = self.assess(x, &witness, t, &mut gpu)?;
            repaired_dual = Some(witness);
            result["dual_corrections"] = json!(corrections);
        }
        Ok(DeferredAssessment {
            value: result,
            repaired_dual,
        })
    }
    /// GPU calls remain on the caller/context thread. Only the original CPU
    /// dual proof moves to the worker; both use this immutable endpoint.
    pub(crate) fn evaluate_overlapped(
        &mut self,
        x: &[f64],
        y: &[f64],
        t: f64,
        mut gpu: impl FnMut(&[f64], f64) -> Result<Option<bool>>,
    ) -> Result<(Value, Value, crate::assessment_overlap::Timing)> {
        if y.len() != self.original.program.row_count() {
            return Err("dual dimensions".into());
        }
        assert!(self.workers <= 3, "overlap reserves one caller slot");
        self.cached_calls += 1;
        let original = self.original;
        let store = self.store;
        let (bound, (device_feasible, objective, witness), timing) =
            crate::assessment_overlap::run(
                || Ok::<_, String>(self.dual_bound(y)),
                || {
                    let device_feasible = gpu(x, t).map_err(|e| e.to_string())?;
                    let objective = objective(original, x).map_err(|e| e.to_string())?;
                    let witness = store.endpoint(x, y).map_err(|e| e.to_string())?;
                    Ok((device_feasible, objective, witness))
                },
            )?;
        // A CPU fallback begins only after the dual worker joins: never two
        // independent worker teams competing for the same four-slot budget.
        let (feasible, objective) = match device_feasible {
            Some(feasible) => (feasible, objective),
            None => feasibility_workers(
                original,
                x,
                t,
                self.workers,
                self.workspace.is_some() || self.fast_workspace.is_some(),
            )?,
        };
        let mut value = self.finish(x, t, device_feasible, feasible, objective, bound)?;
        let mut repaired_dual = None;
        if feasible
            && bound.is_none()
            && let Some((dual, corrections)) = crate::repair::propose(&original.program, y)
        {
            let bound = self.dual_bound(&dual);
            // Repair changes only y. The original primal diagnostic remains valid.
            value = self.finish(x, t, device_feasible, feasible, objective, bound)?;
            repaired_dual = Some(dual);
            value["dual_corrections"] = json!(corrections);
        }
        let value = self.publish(DeferredAssessment {
            value,
            repaired_dual,
        })?;
        Ok((value, witness, timing))
    }
    pub(crate) fn publish(&self, mut result: DeferredAssessment) -> Result<Value> {
        // One writer: publish repaired-dual arrays only after snapshot output ends.
        if let Some(witness) = result.repaired_dual {
            result.value["certificate_dual_array"] =
                serde_json::to_value(self.store.write(&witness)?)?;
        }
        Ok(result.value)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use optimizer_core::ObjectiveSense;
    use optimizer_lp::{LinearProgram, Range};
    #[test]
    fn overlap_repair_reuses_primal_diagnostic_but_keeps_original_acceptance() {
        let original = Original {
            program: LinearProgram::from_csr(
                vec![7],
                vec![Range {
                    lower: 0.,
                    upper: f64::INFINITY,
                }],
                vec![Range {
                    lower: 1.,
                    upper: 1.,
                }],
                vec![0, 1],
                vec![0],
                vec![1.],
                &[0],
                &[1.],
                ObjectiveSense::Minimize,
                0.,
            )
            .unwrap(),
            row_ids: vec![11],
            model_id: "overlap-repair".into(),
            objective_indices: vec![0],
            objective_values: vec![1.],
            offset: 0.,
            sha256: String::new(),
        };
        let path = std::env::temp_dir().join(format!("overlap-repair-{}", std::process::id()));
        let store = Store::new(&path).unwrap();
        let y = [1. + f64::EPSILON];
        let mut serial = Assessor::new(&original, &store, true).with_workspace(true, 3);
        let mut serial_calls = 0;
        let expected = serial
            .evaluate_with_feasibility(&[1.], &y, 1e-9, |_, _| {
                serial_calls += 1;
                Ok(Some(true))
            })
            .unwrap();
        assert_eq!(serial_calls, 2);
        assert_eq!(expected["accepted"], true);
        assert!(expected["certificate_dual_array"].is_object());
        let mut parallel = Assessor::new(&original, &store, true).with_workspace(true, 3);
        let mut parallel_calls = 0;
        let (actual, _, _) = parallel
            .evaluate_overlapped(&[1.], &y, 1e-9, |_, _| {
                parallel_calls += 1;
                Ok(Some(true))
            })
            .unwrap();
        assert_eq!(parallel_calls, 1);
        assert_eq!(actual, expected);
        assert_eq!(parallel.cpu_feasibility_confirmations, 1);
        std::fs::remove_dir_all(path).unwrap();
    }
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
        let mut scratch_assessor =
            Assessor::new(&original, &store, true).with_certificate_scratch(true);
        assert_eq!(
            scratch_assessor
                .evaluate(&[0.5], &[0.], 1e-9, false)
                .unwrap(),
            expected
        );
        assert!(
            scratch_assessor
                .evaluate_with_feasibility(&[2.], &[0.], 1e-9, |_, _| Ok(Some(true)))
                .is_err()
        );
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
        for diagnostic in [None, Some(true)] {
            let mut overlapped = Assessor::new(&original, &store, true).with_workspace(true, 3);
            let caller = std::thread::current().id();
            let calls = std::rc::Rc::new(std::cell::Cell::new(0));
            let (value, witness, _) = overlapped
                .evaluate_overlapped(&[0.5], &[0.], 1e-9, |_, _| {
                    assert_eq!(std::thread::current().id(), caller);
                    calls.set(calls.get() + 1);
                    Ok(diagnostic)
                })
                .unwrap();
            assert_eq!(calls.get(), 1);
            assert_eq!(value, expected);
            assert!(witness["primal"].is_object());
            assert!(
                overlapped
                    .evaluate_overlapped(&[2.], &[0.], 1e-9, |_, _| Ok(Some(true)))
                    .is_err()
            );
            assert!(
                overlapped
                    .evaluate_overlapped(&[0.5], &[0.], 1e-9, |_, _| Err(
                        "diagnostic failure".into()
                    ))
                    .is_err()
            );
            assert_eq!(
                overlapped.evaluate(&[0.5], &[0.], 1e-9, false).unwrap(),
                expected
            );
        }
        for (workers, exact_product) in [1, 3, 4]
            .into_iter()
            .flat_map(|workers| [(workers, false), (workers, true)])
        {
            let mut workspace = Assessor::new(&original, &store, true)
                .with_workspace(true, workers)
                .with_exact_product(exact_product, workers);
            let (deferred, witness, _) = crate::assessment_overlap::run(
                || {
                    workspace
                        .evaluate_deferred(&[0.5], &[0.], 1e-9, |_, _| Ok(Some(true)))
                        .map_err(|e| e.to_string())
                },
                || store.endpoint(&[0.5], &[0.]).map_err(|e| e.to_string()),
            )
            .unwrap();
            assert_eq!(workspace.publish(deferred).unwrap(), expected);
            assert!(witness["primal"].is_object());
            assert!(
                workspace
                    .evaluate_with_feasibility(&[2.], &[0.], 1e-9, |_, _| Ok(Some(true)))
                    .is_err()
            );
            let retained = workspace.retained_workspace_bytes();
            assert!(retained > 0);
            assert_eq!(
                workspace.evaluate(&[0.5], &[0.], 1e-9, false).unwrap(),
                expected
            );
            assert_eq!(workspace.retained_workspace_bytes(), retained);
        }
        std::fs::remove_dir_all(path).unwrap();
    }
}
