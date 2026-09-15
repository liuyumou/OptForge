//! Resumable FP64 restart/weight control shared by host and matched CUDA execution.
//! Controller residuals steer proposals; only independent certification grants bounds.

use crate::pdhg::{Engine, Iterate};
use optimizer_core::CancellationToken;
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
    /// KKT error at the current anchor and weight.
    pub anchor_error: f64,
    /// KKT error at the last completed control check.
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

/// Opaque in-memory checkpoint bound to the exact immutable engine instance.
#[derive(Clone)]
pub struct Fp64Checkpoint<'e, 'p> {
    engine: &'e Engine<'p>,
    state: Fp64State,
}

/// Controller and physical work/deadline accounting. Checkpoints exclude the latter.
pub struct Fp64Controller<'e, 'p> {
    engine: &'e Engine<'p>,
    state: Fp64State,
    physical_iterations: u64,
    kkt_evaluations: u64,
    deadline: Option<Instant>,
}

impl<'e, 'p> Fp64Controller<'e, 'p> {
    /// Start from the existing projected-zero initialization.
    #[must_use]
    pub fn new(engine: &'e Engine<'p>) -> Self {
        let primal = engine.start_primal();
        let dual = engine.start_dual();
        let error = engine.kkt_error(&primal, &dual, 1.0);
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
            kkt_evaluations: 1,
            deadline: None,
        }
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

    /// Actual KKT evaluations, including recomputation at restarts.
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
        Fp64Checkpoint {
            engine: self.engine,
            state: self.state.clone(),
        }
    }

    /// Restore numerical state on the same immutable problem/settings instance.
    ///
    /// # Errors
    /// Refuses checkpoints belonging to another engine.
    pub fn restore(&mut self, checkpoint: &Fp64Checkpoint<'e, 'p>) -> Result<(), &'static str> {
        if !std::ptr::eq(self.engine, checkpoint.engine) {
            return Err("checkpoint belongs to a different FP64 engine");
        }
        self.state = checkpoint.state.clone();
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
        assert!(self.check_pending());
        let state = &mut self.state;
        let error = self
            .engine
            .kkt_error(&state.primal, &state.dual, state.weight);
        self.kkt_evaluations += 1;
        let rose = state.last_check_error < error;
        state.last_check_error = error;
        let restart = self.engine.settings().restart;
        if error <= restart.sufficient * state.anchor_error
            || (error <= restart.necessary * state.anchor_error && rose)
            || state.since_restart as f64 >= restart.artificial * state.iterations as f64
        {
            state.weight = self.engine.next_weight(
                &state.primal,
                &state.dual,
                &state.anchor_primal,
                &state.anchor_dual,
                state.weight,
                &mut state.integral,
                &mut state.previous_error,
            );
            state.anchor_primal.copy_from_slice(&state.primal);
            state.anchor_dual.copy_from_slice(&state.dual);
            state.anchor_error = self
                .engine
                .kkt_error(&state.primal, &state.dual, state.weight);
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
