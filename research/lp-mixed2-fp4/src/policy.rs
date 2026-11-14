pub fn allowance(rho: f64, tolerance: f64, scale: f64) -> f64 {
    rho.clamp(tolerance, 1.) * scale / 8.
}
pub fn audit_interval(rho: f64, _noise: f64, max: u32) -> u32 {
    if rho < 1e-4 { max.min(32) } else { max }
}
pub fn stalled(previous: f64, current: f64, _noise: f64, old: u32) -> u32 {
    if current >= previous * 0.99 {
        old + 1
    } else {
        0
    }
}
pub fn progress(
    previous: &crate::model::Observation,
    current: &crate::model::Observation,
    tolerance: f64,
) -> bool {
    let p = |x: &crate::model::Observation| x.column.max(x.primal_fixed);
    let d = |x: &crate::model::Observation| x.row.max(x.dual_fixed);
    p(current) <= (p(previous) * 0.99).max(tolerance)
        && d(current) <= (d(previous) * 0.99).max(tolerance)
}

#[cfg(test)]
mod tests {
    use super::*;
    fn observation(p: f64, d: f64) -> crate::model::Observation {
        crate::model::Observation {
            rho: p.max(d),
            column: 0.,
            primal_fixed: p,
            row: d,
            dual_fixed: 0.,
            scale: 1.,
        }
    }
    #[test]
    fn both_sides_must_progress_or_reach_tolerance() {
        let old = observation(1., 0.5);
        assert!(progress(&old, &observation(0.98, 0.49), 1e-9));
        assert!(!progress(&old, &observation(0.5, 0.5), 1e-9));
        assert!(!progress(&old, &observation(1., 0.1), 1e-9));
        assert!(progress(
            &observation(0., 0.5),
            &observation(1e-10, 0.49),
            1e-9
        ));
    }
}
