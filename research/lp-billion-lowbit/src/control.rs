//! SPEC-0045 isolated derivative of the source-bound shared FP64 controller.
//! Resumable FP64 restart/weight control shared by host and matched CUDA execution.
//! Controller residuals steer proposals; only independent certification grants bounds.

use crate::engine::Engine;
use crate::merit::EngineMerit;
use optimizer_core::CancellationToken;
use optimizer_lp::Iterate;
use std::time::Instant;

/// All mutable numerical state that affects future FP64 iterates.
#[derive(Clone, Debug, PartialEq)]
pub struct Fp64State {
    /// Scaled primal iterate.
    pub primal: Vec<f64>,
    /// Scaled dual iterate.
    pub dual: Vec<f64>,
    /// Scaled primal restart anchor.
    pub anchor_primal: Vec<f64>,
    /// Scaled dual restart anchor.
    pub anchor_dual: Vec<f64>,
    /// Current primal weight.
    pub weight: f64,
    /// Accumulated controller error.
    pub integral: f64,
    /// Previous controller error, if a meaningful restart occurred.
    pub previous_error: Option<f64>,
    /// Progress merit at the current anchor and weight.
    pub anchor_error: f64,
    /// Progress merit at the last completed control check.
    pub last_check_error: f64,
    /// Logical iteration index.
    pub iterations: u64,
    /// Completed restart decisions.
    pub restarts: u64,
    /// Iterations since the current restart anchor.
    pub since_restart: u64,
    /// Last iteration whose controller check was processed.
    pub checked_iteration: u64,
}

impl Fp64State {
    fn reuse_from(&mut self, source: &Self) {
        let mut primal = std::mem::take(&mut self.primal);
        let mut dual = std::mem::take(&mut self.dual);
        let mut anchor_primal = std::mem::take(&mut self.anchor_primal);
        let mut anchor_dual = std::mem::take(&mut self.anchor_dual);
        primal.clone_from(&source.primal);
        dual.clone_from(&source.dual);
        anchor_primal.clone_from(&source.anchor_primal);
        anchor_dual.clone_from(&source.anchor_dual);
        *self = Self {
            primal,
            dual,
            anchor_primal,
            anchor_dual,
            ..*source
        };
    }
}

/// Opaque in-memory checkpoint bound to the exact immutable engine instance.
#[derive(Clone)]
pub struct Fp64Checkpoint<'e, 'p> {
    engine: &'e Engine<'p>,
    state: Fp64State,
}

impl Fp64Checkpoint<'_, '_> {
    /// Compare restoration with the already-owned checkpoint, without another
    /// full state copy. Every floating-point bit and controller field is checked.
    pub fn matches_state(&self, state: &Fp64State) -> bool {
        crate::solve::same_state(&self.state, state)
    }
}

/// Controller and physical work/deadline accounting. Checkpoints exclude the latter.
pub struct Fp64Controller<'e, 'p> {
    engine: &'e Engine<'p>,
    state: Fp64State,
    physical_iterations: u64,
    generation: u64,
    kkt_evaluations: u64,
    deadline: Option<Instant>,
}

impl<'e, 'p> Fp64Controller<'e, 'p> {
    /// Start from projected zero with the experimental projected-step merit.
    #[must_use]
    pub fn new(engine: &'e Engine<'p>) -> Self {
        Self::new_with_merit(engine, |x, y, w| engine.projected_residual(x, y, w))
    }

    /// Select a progress diagnostic without giving it certificate authority.
    #[must_use]
    pub fn new_with_merit(
        engine: &'e Engine<'p>,
        merit: impl FnOnce(&[f64], &[f64], f64) -> f64,
    ) -> Self {
        let primal = engine.start_primal();
        let dual = engine.start_dual();
        let error = merit(&primal, &dual, 1.0);
        Self {
            engine,
            state: Fp64State {
                anchor_primal: primal.clone(),
                anchor_dual: dual.clone(),
                primal,
                dual,
                weight: 1.0,
                integral: 0.0,
                previous_error: None,
                anchor_error: error,
                last_check_error: error,
                iterations: 0,
                restarts: 0,
                since_restart: 0,
                checked_iteration: 0,
            },
            physical_iterations: 0,
            generation: 0,
            kkt_evaluations: 1,
            deadline: None,
        }
    }

    /// State replacement generation; does not roll back with checkpoints.
    #[must_use]
    pub fn generation(&self) -> u64 {
        self.generation
    }

    /// Numerical state, read-only outside controlled buffer execution.
    #[must_use]
    pub fn state(&self) -> &Fp64State {
        &self.state
    }

    /// Completed physical steps, including steps later rolled back.
    #[must_use]
    pub fn physical_iterations(&self) -> u64 {
        self.physical_iterations
    }

    /// Actual progress-merit evaluations, including recomputation at restarts.
    #[must_use]
    pub fn kkt_evaluations(&self) -> u64 {
        self.kkt_evaluations
    }

    /// Set the absolute solve deadline; restoration never extends it.
    pub fn set_deadline(&mut self, deadline: Option<Instant>) {
        self.deadline = deadline;
    }

    /// Whether the absolute deadline has expired at this observation boundary.
    #[must_use]
    pub fn expired(&self) -> bool {
        self.expired_at(Instant::now())
    }

    /// Explicit clock observation for deterministic boundary tests.
    #[must_use]
    pub fn expired_at(&self, now: Instant) -> bool {
        self.deadline.is_some_and(|deadline| now >= deadline)
    }

    /// Save every continuation field without saving resource consumption.
    #[must_use]
    pub fn checkpoint(&self) -> Fp64Checkpoint<'e, 'p> {
        let _component_scope = optimizer_core::lp_cost::scope("checkpoint_copy");
        Fp64Checkpoint {
            engine: self.engine,
            state: self.state.clone(),
        }
    }

    /// Reuse snapshot allocations; every numerical field is refreshed exactly.
    pub fn checkpoint_reusing(&self, slot: &mut Option<Fp64Checkpoint<'e, 'p>>) {
        let _component_scope = optimizer_core::lp_cost::scope("checkpoint_copy");
        if let Some(checkpoint) = slot {
            checkpoint.engine = self.engine;
            checkpoint.state.reuse_from(&self.state);
        } else {
            *slot = Some(self.checkpoint());
        }
    }

    /// Restore numerical state on the same immutable problem/settings instance.
    ///
    /// # Errors
    /// Refuses checkpoints belonging to another engine.
    pub fn restore(&mut self, checkpoint: &Fp64Checkpoint<'e, 'p>) -> Result<(), &'static str> {
        let _component_scope = optimizer_core::lp_cost::scope("checkpoint_restore");
        if !std::ptr::eq(self.engine, checkpoint.engine) {
            return Err("checkpoint belongs to a different FP64 engine");
        }
        self.state = checkpoint.state.clone();
        self.generation = self
            .generation
            .checked_add(1)
            .expect("FP64 state generation exhausted");
        Ok(())
    }

    pub fn restore_reusing(
        &mut self,
        checkpoint: &Fp64Checkpoint<'e, 'p>,
    ) -> Result<(), &'static str> {
        if !std::ptr::eq(self.engine, checkpoint.engine) {
            return Err("checkpoint belongs to a different FP64 engine");
        }
        self.state.reuse_from(&checkpoint.state);
        self.generation = self
            .generation
            .checked_add(1)
            .expect("FP64 state generation exhausted");
        Ok(())
    }

    /// Physical iteration allowance; rollback cannot replenish it.
    #[must_use]
    pub fn remaining(&self) -> u64 {
        self.engine
            .settings()
            .iteration_limit
            .saturating_sub(self.physical_iterations)
    }

    /// A global check boundary must be assessed before another step is proposed.
    #[must_use]
    pub fn check_pending(&self) -> bool {
        self.state.iterations > self.state.checked_iteration
            && self
                .state
                .iterations
                .is_multiple_of(self.engine.settings().check_interval)
    }

    /// Number of steps until the next check or exhausted physical allowance.
    #[must_use]
    pub fn next_chunk(&self, maximum: u64) -> u64 {
        if self.check_pending() {
            return 0;
        }
        maximum.min(self.remaining()).min(
            self.engine.settings().check_interval
                - self.state.iterations % self.engine.settings().check_interval,
        )
    }

    /// Device buffer views. The caller commits only successfully completed steps.
    pub fn buffers(&mut self) -> (&mut [f64], &mut [f64], &[f64], &[f64]) {
        (
            &mut self.state.primal,
            &mut self.state.dual,
            &self.state.anchor_primal,
            &self.state.anchor_dual,
        )
    }

    /// Commit actual completed work, never a requested iteration count.
    ///
    /// # Errors
    /// Refuses work crossing an unprocessed check or exceeding the work allowance.
    pub fn commit_steps(&mut self, completed: u64) -> Result<(), &'static str> {
        if completed > self.next_chunk(completed) {
            return Err("invalid completed FP64 work");
        }
        self.state.iterations += completed;
        self.state.since_restart += completed;
        self.physical_iterations += completed;
        Ok(())
    }

    /// Explicitly prepare binary32 state; unchanged representable values retain residency.
    pub fn round_working(&mut self) -> Result<(), &'static str> {
        let _component_scope = optimizer_core::lp_cost::scope("working_state_narrowing");
        let mut changed = false;
        let mut next = self.state.clone();
        for v in next
            .primal
            .iter_mut()
            .chain(&mut next.dual)
            .chain(&mut next.anchor_primal)
            .chain(&mut next.anchor_dual)
        {
            let rounded = optimizer_lp::precision::narrow(*v)?;
            changed |= rounded.to_bits() != v.to_bits();
            *v = rounded;
        }
        if changed {
            self.state = next;
            self.generation += 1;
        }
        Ok(())
    }

    /// Charge reference or rejected work without accepting another logical step.
    pub fn charge_extra(&mut self, count: u64) -> Result<(), &'static str> {
        if count > self.remaining() {
            return Err("reference work exceeds allowance");
        }
        self.physical_iterations += count;
        Ok(())
    }

    /// Replace a corrected endpoint and invalidate resident state, preserving history.
    pub fn replace_endpoint(&mut self, x: Vec<f64>, y: Vec<f64>) -> Result<(), &'static str> {
        let _component_scope = optimizer_core::lp_cost::scope("reference_adoption");
        if x.len() != self.state.primal.len()
            || y.len() != self.state.dual.len()
            || !x.iter().chain(&y).all(|v| v.is_finite())
        {
            return Err("invalid corrected endpoint");
        }
        self.state.primal = x;
        self.state.dual = y;
        self.generation += 1;
        Ok(())
    }

    /// One unchanged host arithmetic step. The driver owns cancellation policy.
    pub(crate) fn host_step(&mut self) {
        assert!(self.next_chunk(1) == 1);
        let (x, y) = self
            .engine
            .step_once(&self.state.primal, &self.state.dual, self.state.weight);
        let toward = (self.state.since_restart + 1) as f64 / (self.state.since_restart + 2) as f64;
        let back = 1.0 / (self.state.since_restart + 2) as f64;
        for ((out, next), anchor) in self
            .state
            .primal
            .iter_mut()
            .zip(x)
            .zip(&self.state.anchor_primal)
        {
            *out = toward * next + back * anchor;
        }
        for ((out, next), anchor) in self
            .state
            .dual
            .iter_mut()
            .zip(y)
            .zip(&self.state.anchor_dual)
        {
            *out = toward * next + back * anchor;
        }
        self.commit_steps(1).expect("one admitted host step");
    }

    /// Bounded matched reference chunk. Cancellation/deadlines are checked before
    /// at most 64 steps; checks remain at global interval boundaries.
    pub fn advance_host(&mut self, maximum: u64, cancel: &CancellationToken) -> u64 {
        if cancel.is_cancelled() || self.expired() {
            return 0;
        }
        let count = self.next_chunk(maximum.min(64));
        for _ in 0..count {
            self.host_step();
        }
        count
    }

    /// Continue after a non-accepting assessment using the original host control.
    pub fn continue_after_check(&mut self) {
        let engine = self.engine;
        self.continue_after_check_with_merit(|x, y, weight| {
            engine.projected_residual(x, y, weight)
        });
    }

    /// Reuse the restart and weight controller with an explicit experimental
    /// progress diagnostic. The caller uses the same merit at initialization.
    pub fn continue_after_check_with_merit(
        &mut self,
        merit: impl FnMut(&[f64], &[f64], f64) -> f64,
    ) {
        self.continue_after_check_with_movement(merit, |_| None);
    }

    /// Optional exact movement norms; the weight recurrence remains on the host.
    pub fn continue_after_check_with_movement(
        &mut self,
        mut merit: impl FnMut(&[f64], &[f64], f64) -> f64,
        mut movement: impl FnMut(&Fp64State) -> Option<(f64, f64)>,
    ) {
        let _cost = optimizer_core::lp_cost::scope("controller_assessment");
        assert!(self.check_pending());
        let state = &mut self.state;
        let error = merit(&state.primal, &state.dual, state.weight);
        self.kkt_evaluations += 1;
        let rose = state.last_check_error < error;
        state.last_check_error = error;
        let restart = self.engine.settings().restart;
        if error <= restart.sufficient * state.anchor_error
            || (error <= restart.necessary * state.anchor_error && rose)
            || state.since_restart as f64 >= restart.artificial * state.iterations as f64
        {
            let _cost = optimizer_core::lp_cost::scope("restart");
            state.weight = if let Some((primal, dual)) = movement(state) {
                crate::merit::next_weight_from_movements(
                    self.engine,
                    primal,
                    dual,
                    state.weight,
                    &mut state.integral,
                    &mut state.previous_error,
                )
            } else {
                self.engine.next_weight(
                    &state.primal,
                    &state.dual,
                    &state.anchor_primal,
                    &state.anchor_dual,
                    state.weight,
                    &mut state.integral,
                    &mut state.previous_error,
                )
            };
            state.anchor_primal.copy_from_slice(&state.primal);
            state.anchor_dual.copy_from_slice(&state.dual);
            state.anchor_error = merit(&state.primal, &state.dual, state.weight);
            self.kkt_evaluations += 1;
            state.last_check_error = state.anchor_error;
            state.since_restart = 0;
            state.restarts += 1;
        }
        state.checked_iteration = state.iterations;
    }

    /// Corresponding primal/dual witness in original model units.
    #[must_use]
    pub fn iterate(&self) -> Iterate {
        Iterate {
            primal: self.engine.unscale_primal(&self.state.primal),
            dual: self.engine.unscale_dual(&self.state.dual),
            iterations: self.state.iterations,
            restarts: self.state.restarts,
        }
    }
}

#[cfg(test)]
mod reuse_tests {
    use super::*;
    use optimizer_core::ObjectiveSense;
    use optimizer_lp::{LinearProgram, LpSettings, Range};
    fn program() -> LinearProgram {
        LinearProgram::from_csr(
            vec![0, 1],
            vec![
                Range {
                    lower: -2.,
                    upper: 3.
                };
                2
            ],
            vec![Range {
                lower: -1.,
                upper: 2.,
            }],
            vec![0, 2],
            vec![0, 1],
            vec![1., -1.],
            &[0, 1],
            &[1., 2.],
            ObjectiveSense::Minimize,
            0.,
        )
        .unwrap()
    }
    fn pointers(s: &Fp64State) -> [*const f64; 4] {
        [
            s.primal.as_ptr(),
            s.dual.as_ptr(),
            s.anchor_primal.as_ptr(),
            s.anchor_dual.as_ptr(),
        ]
    }
    #[test]
    fn reused_snapshots_restore_every_bit_without_allocating_or_refunding_work() {
        let p = program();
        let e = Engine::new(&p, LpSettings::published(100, 10));
        let mut c = Fp64Controller::new(&e);
        let mut slot = None;
        c.checkpoint_reusing(&mut slot);
        let buffers = pointers(&slot.as_ref().unwrap().state);
        c.physical_iterations = 17;
        c.generation = 4;
        let deadline = Instant::now();
        c.set_deadline(Some(deadline));
        for i in 0..5 {
            c.state.primal[0] = -0.;
            c.state.primal[1] = i as f64 + 0.25;
            c.state.dual[0] = -3.25;
            c.state.anchor_primal.fill(8.5);
            c.state.anchor_dual.fill(-0.);
            c.state.weight = 2.;
            c.state.integral = -0.;
            c.state.previous_error = Some(f64::from_bits(1));
            c.state.anchor_error = 5.;
            c.state.last_check_error = 7.;
            c.state.iterations = i;
            c.state.restarts = i + 1;
            c.state.since_restart = i + 2;
            c.state.checked_iteration = i + 3;
            let expected = c.state.clone();
            c.checkpoint_reusing(&mut slot);
            let snapshot = slot.as_ref().unwrap();
            assert!(snapshot.matches_state(&expected));
            assert_eq!(pointers(&snapshot.state), buffers);
            c.state.primal.fill(99.);
            c.state.weight = 11.;
            let destination = pointers(&c.state);
            c.restore_reusing(snapshot).unwrap();
            assert!(snapshot.matches_state(c.state()));
            assert_eq!(destination, pointers(&c.state));
            assert_eq!(c.physical_iterations(), 17);
            assert_eq!(c.generation(), 5 + i);
            assert!(c.expired_at(deadline));
        }
        let other = Engine::new(&p, LpSettings::published(100, 10));
        let foreign = Fp64Controller::new(&other).checkpoint();
        assert!(c.restore_reusing(&foreign).is_err());
        assert_eq!(c.physical_iterations(), 17);
    }
}
