//! Operational controller, not a trajectory error proof.
pub fn allowance(rho: f64, tolerance: f64, scale: f64) -> f64 {
    rho.clamp(tolerance, 1.) * scale / 8.
}
pub fn audit_interval(rho: f64, noise: f64, maximum: u32) -> u32 {
    if rho < 1e-4 || noise > rho / 128. {
        32.min(maximum)
    } else {
        maximum
    }
}
pub fn stalled(previous: f64, current: f64, noise: f64, count: u32) -> u32 {
    if current >= 0.99 * previous && noise >= current / 8. {
        count + 1
    } else {
        0
    }
}
#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn slow_monotone_progress_is_not_precision_stagnation() {
        let mut count = 0;
        let mut previous = 0.0010174254050380625;
        for current in [
            0.0009170911282771991,
            0.0008261336312657015,
            0.000743735530080802,
        ] {
            count = stalled(previous, current, 1e-11, count);
            assert_eq!(count, 0);
            previous = current;
        }
    }
    #[test]
    fn noise_limited_plateau_and_near_accuracy_are_observed_early() {
        assert_eq!(stalled(1e-5, 1e-5, 1e-5, 2), 3);
        assert_eq!(stalled(1e-5, 1e-5, 1e-12, 2), 0);
        assert_eq!(audit_interval(1e-8, 1e-12, 200), 32);
        assert_eq!(audit_interval(0.5, 1e-12, 200), 200);
        assert_eq!(allowance(0., 1e-9, 1.), 1.25e-10);
    }
}
