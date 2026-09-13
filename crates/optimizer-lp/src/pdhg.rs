//! Restarted primal-dual hybrid gradient, under SPEC-0011 requirements 5 to 10.
//!
//! The method solves a linear program with repeated matrix-vector products and
//! vector updates, and no factorization. That choice is the one SPEC-0011 argues
//! for from the hardware: a sparse product is bounded by memory bandwidth at this
//! arithmetic intensity, so the compute capability 12.0 FP64 rate does not bind,
//! while factorization and interior-point steps have the opposite intensity and
//! are excluded for that reason rather than by preference.
//!
//! Everything in this module is `f64`, requirement 5, and everything is arranged
//! so the result depends only on the input and the settings:
//!
//! - each product reads the matrix orientation whose major axis it writes, so no
//!   output element is accumulated by more than one reduction and no atomic is
//!   needed anywhere (requirement 6);
//! - every reduction goes through [`crate::reduce`]'s fixed partition and tree,
//!   never a loop whose order depends on a launch shape (requirement 7);
//! - the step size comes from a fixed number of power iterations rather than from
//!   a convergence test, because a count that stopped on a measured criterion
//!   would vary with rounding and take every later iterate with it;
//! - the step size itself is fixed rather than line-searched, which is a
//!   departure from the published method made for the same reason. An adaptive
//!   step retries an input-dependent number of times, each retry is a reduction,
//!   and the trial count would then depend on rounding. The cost is convergence
//!   rate, which requirement 23 forbids claiming anything about in either
//!   direction.
//!
//! The KKT residuals computed here steer the algorithm -- they drive restarts and
//! the primal weight -- and they justify nothing. No bound, status or proof reads
//! them; [`crate::certify::certify`] recomputes everything it needs from the original
//! model. A device that computes these residuals badly converges badly and cannot
//! produce a wrong answer. That distinction is easy to lose at a glance, which is
//! why it is written here rather than assumed.

use optimizer_core::CancellationToken;

use crate::precondition::Preconditioner;
use crate::problem::LinearProgram;
use crate::reduce::tree_sum;
use optimizer_core::LpSettings;

/// Why the iteration stopped.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Stop {
    /// The iteration limit was reached.
    IterationLimit,
    /// Cancellation was observed at a check boundary.
    Cancelled,
    /// The caller's termination check accepted the iterate.
    Accepted,
}

/// One iterate, unscaled into the original model's variables and rows.
#[derive(Clone, Debug, PartialEq)]
pub struct Iterate {
    /// Primal values, in the canonical program's column order.
    pub primal: Vec<f64>,
    /// Dual multipliers, in the canonical program's row order.
    pub dual: Vec<f64>,
    /// Iterations performed.
    pub iterations: u64,
    /// Restarts performed.
    pub restarts: u64,
}

/// What a caller's termination check decided.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Decision {
    /// Keep iterating.
    Continue,
    /// Stop; the iterate is good enough for the caller's purposes.
    Accept,
}

/// The scaled working problem and the iteration state.
pub struct Engine<'a> {
    program: &'a LinearProgram,
    preconditioner: Preconditioner,
    settings: LpSettings,
    /// Scaled matrix values, parallel to the program's own storage.
    scaled_row_values: Vec<f64>,
    scaled_column_values: Vec<f64>,
    scaled_objective: Vec<f64>,
    scaled_row_lower: Vec<f64>,
    scaled_row_upper: Vec<f64>,
    scaled_column_lower: Vec<f64>,
    scaled_column_upper: Vec<f64>,
    step: f64,
}

impl<'a> Engine<'a> {
    /// Build the scaled working problem.
    #[must_use]
    pub fn new(program: &'a LinearProgram, settings: LpSettings) -> Self {
        let preconditioner = Preconditioner::new(program, settings.preconditioner);
        let row_scale = preconditioner.row().to_vec();
        let column_scale = preconditioner.column().to_vec();

        // Â = diag(row) A diag(column), stored in both orientations so each
        // product writes the axis it owns.
        let scaled_row_values: Vec<f64> = program
            .row_major()
            .entries()
            .map(|(row, column, value)| row_scale[row] * value * column_scale[column as usize])
            .collect();
        let scaled_column_values: Vec<f64> = program
            .column_major()
            .entries()
            .map(|(column, row, value)| row_scale[row as usize] * value * column_scale[column])
            .collect();

        // x = diag(column) x̂, so bounds divide and the objective multiplies.
        let scaled_objective: Vec<f64> = program
            .objective()
            .iter()
            .zip(&column_scale)
            .map(|(cost, scale)| cost * scale)
            .collect();
        let scaled_column_lower: Vec<f64> = program
            .columns()
            .iter()
            .zip(&column_scale)
            .map(|(range, scale)| range.lower / scale)
            .collect();
        let scaled_column_upper: Vec<f64> = program
            .columns()
            .iter()
            .zip(&column_scale)
            .map(|(range, scale)| range.upper / scale)
            .collect();
        let scaled_row_lower: Vec<f64> = program
            .rows()
            .iter()
            .zip(&row_scale)
            .map(|(range, scale)| range.lower * scale)
            .collect();
        let scaled_row_upper: Vec<f64> = program
            .rows()
            .iter()
            .zip(&row_scale)
            .map(|(range, scale)| range.upper * scale)
            .collect();

        let mut engine = Self {
            program,
            preconditioner,
            settings,
            scaled_row_values,
            scaled_column_values,
            scaled_objective,
            scaled_row_lower,
            scaled_row_upper,
            scaled_column_lower,
            scaled_column_upper,
            step: 1.0,
        };
        let norm = engine.spectral_norm();
        // 0.9 rather than 1.0 leaves headroom for the norm estimate being low.
        // A step above the convergence threshold does not merely converge slowly,
        // it diverges, so the margin is not a tuning constant.
        engine.step = if norm > 0.0 { 0.9 / norm } else { 1.0 };
        engine
    }

    /// The preconditioner this engine applied, for the record.
    #[must_use]
    pub fn preconditioner(&self) -> &Preconditioner {
        &self.preconditioner
    }

    /// Estimate the largest singular value by a fixed number of power iterations.
    fn spectral_norm(&self) -> f64 {
        let columns = self.program.column_count();
        if columns == 0 || self.program.nonzeros() == 0 {
            return 0.0;
        }
        // A deterministic start rather than a random one. The seed would have to
        // be recorded otherwise, and nothing is gained: the estimate feeds a step
        // size, not a result.
        let mut vector = vec![1.0f64; columns];
        let mut norm = 0.0;
        for _ in 0..self.settings.power_iterations {
            let product = self.multiply(&vector);
            let transposed = self.multiply_transpose(&product);
            let magnitude = self.norm(&transposed);
            if magnitude <= 0.0 {
                return 0.0;
            }
            for value in &mut vector {
                *value /= magnitude;
            }
            for (slot, value) in vector.iter_mut().zip(&transposed) {
                *slot = value / magnitude;
            }
            norm = magnitude.sqrt();
        }
        norm
    }

    /// Euclidean norm through the fixed reduction.
    fn norm(&self, values: &[f64]) -> f64 {
        tree_sum(&values.iter().map(|value| value * value).collect::<Vec<_>>()).sqrt()
    }

    /// `Â x̂`, written row by row from the row-major form.
    fn multiply(&self, x: &[f64]) -> Vec<f64> {
        (0..self.program.row_count())
            .map(|row| {
                let (indices, _) = self.program.row_major().line(row);
                let start = self.program.row_major().offset(row);
                let products: Vec<f64> = indices
                    .iter()
                    .enumerate()
                    .map(|(slot, column)| {
                        self.scaled_row_values[start + slot] * x[*column as usize]
                    })
                    .collect();
                tree_sum(&products)
            })
            .collect()
    }

    /// `Âᵀ ŷ`, written column by column from the column-major form.
    fn multiply_transpose(&self, y: &[f64]) -> Vec<f64> {
        (0..self.program.column_count())
            .map(|column| {
                let (indices, _) = self.program.column_major().line(column);
                let start = self.program.column_major().offset(column);
                let products: Vec<f64> = indices
                    .iter()
                    .enumerate()
                    .map(|(slot, row)| self.scaled_column_values[start + slot] * y[*row as usize])
                    .collect();
                tree_sum(&products)
            })
            .collect()
    }

    /// One primal-dual step.
    fn advance(&self, x: &[f64], y: &[f64], weight: f64) -> (Vec<f64>, Vec<f64>) {
        let primal_step = self.step / weight;
        let dual_step = self.step * weight;

        let transposed = self.multiply_transpose(y);
        let mut next_x = Vec::with_capacity(x.len());
        for column in 0..x.len() {
            let gradient = self.scaled_objective[column] - transposed[column];
            let moved = x[column] - primal_step * gradient;
            next_x.push(
                moved
                    .max(self.scaled_column_lower[column])
                    .min(self.scaled_column_upper[column]),
            );
        }

        // The extrapolated point, which is what makes this a primal-dual method
        // rather than alternating projections.
        let extrapolated: Vec<f64> = (0..x.len())
            .map(|column| 2.0 * next_x[column] - x[column])
            .collect();
        let activity = self.multiply(&extrapolated);

        // The dual update is the proximal operator of the support function of the
        // negated row range, by Moreau decomposition. One expression covers
        // equality, ranged, one-sided and free rows with no branch on row shape.
        //
        // The negation is not cosmetic. This module takes the saddle function
        // `cᵀx − yᵀAx + h(y)`, so that the reduced cost is `c − Aᵀy` -- the
        // ordinary linear-programming convention, and the one [`crate::certify::certify`]
        // recomputes from the original model. Taking the other common convention
        // would produce multipliers of the opposite sign; certification would
        // still be *valid*, because it is valid for any vector, but every bound
        // would be uselessly weak, which is a far harder defect to notice than a
        // wrong answer.
        //
        // A consequence worth stating: this lands the multiplier inside the cone
        // the certification's repair projects onto, so the two agree by
        // construction rather than by coincidence.
        let mut next_y = Vec::with_capacity(y.len());
        for row in 0..y.len() {
            let raw = y[row] - dual_step * activity[row];
            let projected = (raw / dual_step)
                .max(-self.scaled_row_upper[row])
                .min(-self.scaled_row_lower[row]);
            next_y.push(raw - dual_step * projected);
        }

        (next_x, next_y)
    }

    /// A weighted KKT error, used to steer restarts and the primal weight.
    ///
    /// Never used to justify a bound, a status or a proof. See the module header.
    fn kkt_error(&self, x: &[f64], y: &[f64], weight: f64) -> f64 {
        let activity = self.multiply(x);
        let primal_violation: Vec<f64> = (0..y.len())
            .map(|row| {
                let value = activity[row];
                let clamped = value
                    .max(self.scaled_row_lower[row])
                    .min(self.scaled_row_upper[row]);
                let residual = value - clamped;
                residual * residual
            })
            .collect();
        let transposed = self.multiply_transpose(y);
        let dual_violation: Vec<f64> = (0..x.len())
            .map(|column| {
                let reduced = self.scaled_objective[column] - transposed[column];
                // Only the component that cannot be absorbed by a variable bound
                // is a violation.
                let absorbed = if reduced > 0.0 {
                    if self.scaled_column_lower[column].is_finite() {
                        0.0
                    } else {
                        reduced
                    }
                } else if self.scaled_column_upper[column].is_finite() {
                    0.0
                } else {
                    reduced
                };
                absorbed * absorbed
            })
            .collect();
        let primal = tree_sum(&primal_violation).sqrt();
        let dual = tree_sum(&dual_violation).sqrt();
        weight * primal + dual / weight
    }

    /// Run the method, consulting `check` every `check_interval` iterations.
    ///
    /// `check` receives an unscaled iterate. It is where the caller's termination
    /// policy lives -- validating a candidate and certifying a bound -- because
    /// this module deliberately owns no policy about what counts as good enough.
    pub fn run(
        &self,
        cancel: &CancellationToken,
        mut check: impl FnMut(&Iterate) -> Decision,
    ) -> (Iterate, Stop) {
        let columns = self.program.column_count();
        let rows = self.program.row_count();

        // Start from the projection of zero, which is feasible for the bounds and
        // costs nothing to compute.
        let mut x: Vec<f64> = (0..columns)
            .map(|column| {
                0.0f64
                    .max(self.scaled_column_lower[column])
                    .min(self.scaled_column_upper[column])
            })
            .collect();
        let mut y = vec![0.0f64; rows];

        let mut anchor_x = x.clone();
        let mut anchor_y = y.clone();
        let mut weight = 1.0f64;
        let mut integral = 0.0f64;
        let mut previous_error = None::<f64>;
        let mut anchor_error = self.kkt_error(&x, &y, weight);
        let mut last_check_error = anchor_error;

        let mut iterations = 0u64;
        let mut restarts = 0u64;
        let mut since_restart = 0u64;

        let unscale = |x: &[f64], y: &[f64], iterations, restarts| Iterate {
            primal: x
                .iter()
                .zip(self.preconditioner.column())
                .map(|(value, scale)| value * scale)
                .collect(),
            dual: y
                .iter()
                .zip(self.preconditioner.row())
                .map(|(value, scale)| value * scale)
                .collect(),
            iterations,
            restarts,
        };

        while iterations < self.settings.iteration_limit {
            let (next_x, next_y) = self.advance(&x, &y, weight);

            // Halpern: pull each step back toward the anchor by a coefficient
            // that is a pure function of an integer, so the host and the device
            // derive the same number rather than one sending it to the other.
            let numerator = (since_restart + 1) as f64;
            let denominator = (since_restart + 2) as f64;
            let toward = numerator / denominator;
            let back = 1.0 / denominator;
            for column in 0..columns {
                x[column] = toward * next_x[column] + back * anchor_x[column];
            }
            for row in 0..rows {
                y[row] = toward * next_y[row] + back * anchor_y[row];
            }

            iterations += 1;
            since_restart += 1;

            if !iterations.is_multiple_of(self.settings.check_interval) {
                continue;
            }

            // Cancellation is observed here and only here, so its latency is
            // bounded by the interval rather than by the iteration limit. On a
            // device this is also the only synchronization point, which is what
            // makes the interval a real parameter rather than a detail.
            if cancel.is_cancelled() {
                return (unscale(&x, &y, iterations, restarts), Stop::Cancelled);
            }

            let iterate = unscale(&x, &y, iterations, restarts);
            if check(&iterate) == Decision::Accept {
                return (iterate, Stop::Accepted);
            }

            let error = self.kkt_error(&x, &y, weight);
            let rose = last_check_error < error;
            last_check_error = error;

            let sufficient = error <= self.settings.restart.sufficient * anchor_error;
            let necessary = error <= self.settings.restart.necessary * anchor_error && rose;
            let artificial =
                since_restart as f64 >= self.settings.restart.artificial * iterations as f64;

            if sufficient || necessary || artificial {
                weight = self.next_weight(
                    &x,
                    &y,
                    &anchor_x,
                    &anchor_y,
                    weight,
                    &mut integral,
                    &mut previous_error,
                );
                anchor_x.copy_from_slice(&x);
                anchor_y.copy_from_slice(&y);
                anchor_error = self.kkt_error(&x, &y, weight);
                last_check_error = anchor_error;
                since_restart = 0;
                restarts += 1;
            }
        }

        (unscale(&x, &y, iterations, restarts), Stop::IterationLimit)
    }

    /// The primal weight controller, evaluated at a restart.
    ///
    /// Compares how far the primal and dual iterates moved since the anchor and
    /// rebalances the step sizes toward whichever is lagging. With the integral
    /// and derivative gains at zero this is exactly the published smoothed update.
    #[allow(clippy::too_many_arguments)]
    fn next_weight(
        &self,
        x: &[f64],
        y: &[f64],
        anchor_x: &[f64],
        anchor_y: &[f64],
        weight: f64,
        integral: &mut f64,
        previous_error: &mut Option<f64>,
    ) -> f64 {
        let primal_movement = self.norm(
            &x.iter()
                .zip(anchor_x)
                .map(|(value, anchor)| value - anchor)
                .collect::<Vec<_>>(),
        );
        let dual_movement = self.norm(
            &y.iter()
                .zip(anchor_y)
                .map(|(value, anchor)| value - anchor)
                .collect::<Vec<_>>(),
        );
        // Too small to divide by means the restart carried no information about
        // the balance, so the weight is left where it was.
        if primal_movement <= 1.0e-12 || dual_movement <= 1.0e-12 {
            return weight;
        }

        let gains = self.settings.primal_weight;
        let error = (dual_movement / primal_movement).ln() - weight.ln();
        *integral += error;
        let derivative = previous_error.map_or(0.0, |last| error - last);
        *previous_error = Some(error);

        let logarithm = weight.ln()
            + gains.proportional * error
            + gains.integral * *integral
            + gains.derivative * derivative;
        // Clamped so a pathological instance cannot drive the step sizes to zero
        // or to infinity and turn a slow solve into a nonfinite one.
        logarithm.exp().clamp(1.0e-6, 1.0e6)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use optimizer_core::{
        Bound, Constraint, Domain, LinearTerm, Model, ModelDocument, Objective, ObjectiveSense,
        SCHEMA_VERSION, Variable,
    };

    fn finite(value: f64) -> Bound {
        Bound::Finite { value }
    }

    /// `min -x0 - x1` subject to `x0 + x1 <= 1.5`, `0 <= xj <= 1`. Optimum -1.5.
    fn program() -> LinearProgram {
        let model = Model::new(ModelDocument {
            schema_version: SCHEMA_VERSION,
            model_id: "pdhg".to_string(),
            variables: (0..2)
                .map(|id| Variable {
                    id,
                    domain: Domain::Continuous,
                    lower: finite(0.0),
                    upper: finite(1.0),
                })
                .collect(),
            constraints: vec![Constraint {
                id: 0,
                lower: Bound::NegativeInfinity,
                upper: finite(1.5),
                terms: (0..2)
                    .map(|variable_id| LinearTerm {
                        variable_id,
                        coefficient: 1.0,
                    })
                    .collect(),
            }],
            objective: Objective {
                sense: ObjectiveSense::Minimize,
                offset: 0.0,
                terms: (0..2)
                    .map(|variable_id| LinearTerm {
                        variable_id,
                        coefficient: -1.0,
                    })
                    .collect(),
            },
        })
        .expect("valid");
        LinearProgram::new(&model).expect("continuous")
    }

    fn settings() -> LpSettings {
        LpSettings::published(20_000, 50)
    }

    fn run(program: &LinearProgram, settings: LpSettings) -> (Iterate, Stop) {
        Engine::new(program, settings).run(&CancellationToken::new(), |_| Decision::Continue)
    }

    #[test]
    fn the_iteration_approaches_the_known_optimum() {
        let program = program();
        let (iterate, stop) = run(&program, settings());
        assert_eq!(stop, Stop::IterationLimit);
        let objective = program.objective()[0] * iterate.primal[0]
            + program.objective()[1] * iterate.primal[1]
            + program.offset();
        assert!(
            (objective - -1.5).abs() < 1.0e-4,
            "objective {objective} should approach -1.5"
        );
    }

    /// Requirement 8 on the host: a fixed input produces a bitwise identical
    /// result. The device half of this requirement is asserted separately.
    #[test]
    fn a_fixed_instance_solved_twice_is_bitwise_identical() {
        let program = program();
        let (first, _) = run(&program, settings());
        let (second, _) = run(&program, settings());
        for (a, b) in first.primal.iter().zip(&second.primal) {
            assert_eq!(a.to_bits(), b.to_bits());
        }
        for (a, b) in first.dual.iter().zip(&second.dual) {
            assert_eq!(a.to_bits(), b.to_bits());
        }
        assert_eq!(first.iterations, second.iterations);
        assert_eq!(first.restarts, second.restarts);
    }

    /// Requirement 10: the interval is a real parameter, and changing it changes
    /// the work done rather than being a cosmetic setting.
    #[test]
    fn the_check_interval_bounds_how_often_the_caller_is_consulted() {
        let program = program();
        let mut settings = settings();
        settings.iteration_limit = 1_000;
        settings.check_interval = 100;
        let mut checks = 0;
        Engine::new(&program, settings).run(&CancellationToken::new(), |_| {
            checks += 1;
            Decision::Continue
        });
        assert_eq!(checks, 10);
    }

    /// Cancellation latency is bounded by the interval, not the iteration limit.
    #[test]
    fn cancellation_is_observed_at_the_next_check_boundary() {
        let program = program();
        let mut settings = settings();
        settings.iteration_limit = 100_000;
        settings.check_interval = 25;
        let cancel = CancellationToken::new();
        let (iterate, stop) = Engine::new(&program, settings).run(&cancel, |_| {
            cancel.cancel();
            Decision::Continue
        });
        assert_eq!(stop, Stop::Cancelled);
        assert_eq!(
            iterate.iterations, 50,
            "the token is set during the first check, so the second observes it"
        );
    }

    #[test]
    fn a_caller_accepting_an_iterate_stops_the_method() {
        let program = program();
        let (iterate, stop) =
            Engine::new(&program, settings()).run(&CancellationToken::new(), |_| Decision::Accept);
        assert_eq!(stop, Stop::Accepted);
        assert_eq!(iterate.iterations, 50);
    }

    /// The published gains are a special case of the controller, asserted rather
    /// than described, so a later tuning experiment has a known-good baseline.
    #[test]
    fn the_primal_weight_reduces_to_the_smoothed_rule_when_the_other_gains_are_zero() {
        let program = program();
        let mut general = settings();
        general.primal_weight = optimizer_core::PrimalWeightSettings {
            proportional: 0.5,
            integral: 0.0,
            derivative: 0.0,
        };
        let (from_general, _) = run(&program, general);
        let (from_published, _) = run(&program, settings());
        for (a, b) in from_general.primal.iter().zip(&from_published.primal) {
            assert_eq!(a.to_bits(), b.to_bits());
        }
    }

    /// Restarts have to actually happen, or every restart threshold is dead
    /// configuration and the tests above assert nothing about them.
    #[test]
    fn the_method_restarts_at_least_once() {
        let program = program();
        let (iterate, _) = run(&program, settings());
        assert!(iterate.restarts > 0, "adaptive restart must fire");
    }
}
