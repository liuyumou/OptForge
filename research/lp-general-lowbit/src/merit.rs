//! Experimental progress diagnostic and the retained primal-weight formula.
use optimizer_lp::{Engine, tree_sum};

/// Bound an inexact map displacement relative to the exact map displacement.
/// Both quantities already have state units. Capping the residual at one or
/// multiplying it by the state magnitude makes the rule depend on arbitrary
/// units. Invalid or stationary residuals admit no inexact displacement.
pub fn local_budget(projected_residual: f64) -> f64 {
    if projected_residual.is_finite() && projected_residual > 0. {
        projected_residual / 8.
    } else {
        0.
    }
}

pub trait EngineMerit {
    fn projected_residual(&self, x: &[f64], y: &[f64], weight: f64) -> f64;
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
    ) -> f64;
}
impl EngineMerit for Engine<'_> {
    fn projected_residual(&self, x: &[f64], y: &[f64], weight: f64) -> f64 {
        if !weight.is_finite() || weight <= 0. {
            return f64::INFINITY;
        }
        let (next_x, next_y) = self.step_once(x, y, weight);
        x.iter()
            .chain(y)
            .zip(next_x.iter().chain(&next_y))
            .map(|(old, next)| {
                let difference = (next - old).abs();
                if difference.is_finite() {
                    difference
                } else {
                    f64::INFINITY
                }
            })
            .fold(0., f64::max)
    }
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
        let norm = |v: &[f64]| tree_sum(&v.iter().map(|x| x * x).collect::<Vec<_>>()).sqrt();
        let primal_movement = norm(
            &x.iter()
                .zip(anchor_x)
                .map(|(value, anchor)| value - anchor)
                .collect::<Vec<_>>(),
        );
        let dual_movement = norm(
            &y.iter()
                .zip(anchor_y)
                .map(|(value, anchor)| value - anchor)
                .collect::<Vec<_>>(),
        );
        if primal_movement <= 1e-12 || dual_movement <= 1e-12 {
            return weight;
        }
        let gains = self.settings().primal_weight;
        let error = (dual_movement / primal_movement).ln() - weight.ln();
        *integral += error;
        let derivative = previous_error.map_or(0., |last| error - last);
        *previous_error = Some(error);
        let logarithm = weight.ln()
            + gains.proportional * error
            + gains.integral * *integral
            + gains.derivative * derivative;
        logarithm.exp().clamp(1e-6, 1e6)
    }
}
