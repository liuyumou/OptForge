//! Lazy reuse of the previously admitted exact checker, without endpoint caching.
use crate::{Result, cached_certificate::Plan, prepared_feasibility::Prepared};
use optimizer_core::{Model, Tolerances};
use optimizer_lp::{LinearProgram, certify::assess_gap};
use serde_json::{Value, json};

pub struct Assessor<'a> {
    model: &'a Model,
    program: &'a LinearProgram,
    enabled: bool,
    cache: Option<(Prepared, Plan)>,
    pub cached_calls: usize,
}
impl<'a> Assessor<'a> {
    pub fn new(model: &'a Model, program: &'a LinearProgram, enabled: bool) -> Self {
        Self {
            model,
            program,
            enabled,
            cache: None,
            cached_calls: 0,
        }
    }
    pub fn prepare(&mut self) {
        if self.cache.is_none() {
            self.cache = Some((Prepared::new(self.model.clone()), Plan::new(self.program)));
        }
    }
    fn cached(&self, x: &[f64], y: &[f64], tolerance: f64) -> Result<Value> {
        let (primal, dual) = self
            .cache
            .as_ref()
            .ok_or("missing exact checker preparation")?;
        let tolerances = Tolerances {
            absolute: tolerance,
            relative: tolerance,
            integrality: tolerance,
        };
        let validation = primal.evaluate(x, tolerances)?;
        let bound = dual.certify(self.program, y).ok().map(|c| c.bound);
        let gap = bound.and_then(|b| assess_gap(self.program, x, b, tolerances));
        Ok(
            json!({"accepted":validation.feasible && gap.as_ref().is_some_and(|g|g.closed),
            "feasible":validation.feasible,"objective":validation.objective,"bound":bound,
            "gap_upper":gap.map(|g|g.upper),"tolerance":tolerance}),
        )
    }
    pub fn evaluate(
        &mut self,
        x: &[f64],
        y: &[f64],
        tolerance: f64,
        further_checks: bool,
    ) -> Result<Value> {
        let result = if self.cache.is_some() {
            self.cached_calls += 1;
            let mut result = self.cached(x, y, tolerance)?;
            if result["feasible"] == true
                && result["bound"].is_null()
                && let Some((witness, corrections)) = crate::repair::propose(self.program, y)
            {
                result = self.cached(x, &witness, tolerance)?;
                result["certificate_dual"] = json!(witness);
                result["dual_corrections"] = json!(corrections);
            }
            result
        } else {
            crate::solve::assess_repaired(self.model, self.program, x, y, tolerance)?
        };
        // A solve that passes its first check pays no cached-checker setup.
        if self.enabled && further_checks && result["accepted"] != true {
            self.prepare();
        }
        Ok(result)
    }
}
