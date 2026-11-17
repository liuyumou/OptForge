//! Bounded untrusted proposals for nearly zero reduced costs on infinite bounds.
//! Only the unchanged original certificate algorithm can accept a proposal.
use optimizer_lp::{LinearProgram, certify, certify::NoBound, tree_sum};

pub fn propose(program: &LinearProgram, original: &[f64]) -> Option<(Vec<f64>, usize)> {
    let mut y = original.to_vec();
    // Match the original checker's row-sign projection before estimating any
    // reduced cost. This projection already belongs to the retained checker.
    for (v, r) in y.iter_mut().zip(program.rows()) {
        if (*v > 0. && !r.lower.is_finite()) || (*v < 0. && !r.upper.is_finite()) {
            *v = 0.;
        }
    }
    for attempt in 0..=4 {
        let variable_id = match certify(program, &y) {
            Ok(_) => return Some((y, attempt)),
            Err(NoBound::UnboundedVariable { variable_id }) if attempt < 4 => variable_id,
            _ => return None,
        };
        let j = program.variable_ids().binary_search(&variable_id).ok()?;
        let range = program.columns()[j];
        // A free variable needs exact equality. Inequality nudges cannot prove it.
        if !range.lower.is_finite() && !range.upper.is_finite() {
            return None;
        }
        let (rows, coefficients) = program.column_major().line(j);
        let terms: Vec<_> = rows
            .iter()
            .zip(coefficients)
            .map(|(&i, &a)| a * y[i as usize])
            .collect();
        let c = program.objective()[j];
        let reduced = c - tree_sum(&terms);
        let magnitude = c.abs() + tree_sum(&terms.iter().map(|v| v.abs()).collect::<Vec<_>>());
        // This is a proposal-size cap, not an enclosure or relaxed tolerance.
        let margin = 64. * f64::EPSILON * magnitude.max(1.);
        if !margin.is_finite() || !reduced.is_finite() || reduced.abs() > margin {
            return None;
        }
        let desired = if range.upper.is_finite() {
            -margin
        } else {
            margin
        };
        let correction = desired - reduced;
        let mut choices: Vec<_> = rows
            .iter()
            .zip(coefficients)
            .filter_map(|(&i, &a)| {
                if a == 0. {
                    return None;
                }
                let next = y[i as usize] - correction / a;
                let r = program.rows()[i as usize];
                (next.is_finite()
                    && next.to_bits() != y[i as usize].to_bits()
                    && (next <= 0. || r.lower.is_finite())
                    && (next >= 0. || r.upper.is_finite()))
                .then_some((i as usize, a.abs(), next))
            })
            .collect();
        choices.sort_by(|a, b| b.1.total_cmp(&a.1).then(a.0.cmp(&b.0)));
        let &(i, _, next) = choices.first()?;
        y[i] = next;
    }
    None
}
