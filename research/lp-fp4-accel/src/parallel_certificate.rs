//! Independent column scheduling; every enclosure operation and final tree are unchanged.
use crate::outward::{self, Enclosure};
use optimizer_lp::{Certificate, LinearProgram, NoBound};

pub fn parallel(program: &LinearProgram, y: &[f64]) -> Result<Certificate, NoBound> {
    let _component_scope = optimizer_core::lp_cost::scope("dual_certification");
    assert_eq!(
        y.len(),
        program.row_count(),
        "a multiplier vector must have one entry per constraint"
    );

    for (row, value) in y.iter().enumerate() {
        if !value.is_finite() {
            return Err(NoBound::NonfiniteMultiplier { row });
        }
    }

    // Step 1: repair. If a multiplier has the sign whose row bound is infinite,
    // its term would be unbounded below, so it is zeroed. This is a projection
    // onto the multipliers the rows admit; it breaks no identity because the
    // reduced costs below are computed from the repaired vector.
    let mut repaired_y = y.to_vec();
    let mut repaired = 0usize;
    for (row, value) in repaired_y.iter_mut().enumerate() {
        let range = program.rows()[row];
        let unusable = (*value > 0.0 && !range.lower.is_finite())
            || (*value < 0.0 && !range.upper.is_finite());
        if unusable {
            *value = 0.0;
            repaired += 1;
        }
    }

    // Enclose every term from the original data. A zero rounded reduced cost
    // still carries the full interval through the variable's two bound sides.
    let mut terms = Vec::with_capacity(program.row_count() + program.column_count() + 1);
    for (row, value) in repaired_y.iter().enumerate() {
        terms.push(endpoint(*value, program.rows()[row], None)?);
    }
    let columns = std::thread::scope(|scope| {
        let workers: Vec<_> = (0..4)
            .map(|worker| {
                let repaired_y = &repaired_y;
                scope.spawn(move || {
                    let begin = program.column_count() * worker / 4;
                    let end = program.column_count() * (worker + 1) / 4;
                    (begin..end)
                        .map(|column| column_term(program, repaired_y, column))
                        .collect::<Result<Vec<_>, _>>()
                })
            })
            .collect();
        // Join and concatenate in original column order, preserving the first refusal.
        let mut ordered = Vec::with_capacity(program.column_count());
        for worker in workers {
            ordered.extend(worker.join().expect("certificate worker panicked")?);
        }
        Ok::<_, NoBound>(ordered)
    })?;
    terms.extend(columns);
    terms.push(Enclosure::point(program.offset()).ok_or(NoBound::NonfiniteArithmetic)?);
    let total = outward::sum(&terms).ok_or(NoBound::NonfiniteArithmetic)?;
    let allowance = Enclosure::point(total.rounded)
        .and_then(|raw| raw.subtract(Enclosure::point(total.lower)?))
        .ok_or(NoBound::NonfiniteArithmetic)?
        .upper
        .max(0.0);
    Ok(Certificate {
        bound: program.to_original_objective(total.lower),
        unadjusted: program.to_original_objective(total.rounded),
        allowance,
        repaired,
    })
}

/// Enclose phi(z) for one exact endpoint. Zero needs neither infinite side.
fn endpoint(
    z: f64,
    range: optimizer_lp::Range,
    variable: Option<u32>,
) -> Result<Enclosure, NoBound> {
    if z == 0.0 {
        return Ok(Enclosure::ZERO);
    }
    let bound = if z > 0.0 { range.lower } else { range.upper };
    if !bound.is_finite() {
        return Err(match variable {
            Some(variable_id) => NoBound::UnboundedVariable { variable_id },
            None => NoBound::NonfiniteArithmetic,
        });
    }
    Enclosure::product(z, bound).ok_or(NoBound::NonfiniteArithmetic)
}

fn column_term(
    program: &LinearProgram,
    repaired_y: &[f64],
    column: usize,
) -> Result<Enclosure, NoBound> {
    let (rows, coefficients) = program.column_major().line(column);
    let products = rows
        .iter()
        .zip(coefficients)
        .map(|(row, coefficient)| {
            Enclosure::product(*coefficient, repaired_y[*row as usize])
                .ok_or(NoBound::NonfiniteArithmetic)
        })
        .collect::<Result<Vec<_>, _>>()?;
    let transposed = outward::sum(&products).ok_or(NoBound::NonfiniteArithmetic)?;
    let reduced = Enclosure::point(program.objective()[column])
        .and_then(|cost| cost.subtract(transposed))
        .ok_or(NoBound::NonfiniteArithmetic)?;
    let range = program.columns()[column];
    let id = Some(program.variable_ids()[column]);
    let low = endpoint(reduced.lower, range, id)?;
    let high = endpoint(reduced.upper, range, id)?;
    let rounded = endpoint(reduced.rounded, range, id)?.rounded;
    // phi(z) = inf_x z*x is concave. Its minimum over the enclosure is
    // attained at an endpoint; the only possible interior maximum is z=0.
    let upper = if reduced.lower <= 0.0 && reduced.upper >= 0.0 {
        low.upper.max(high.upper).max(0.0)
    } else {
        low.upper.max(high.upper)
    };
    Enclosure::new(low.lower.min(high.lower), upper, rounded).ok_or(NoBound::NonfiniteArithmetic)
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;
    #[test]
    fn parallel_bounds_match_every_original_bit_and_refusal() {
        for n in [1, 2, 7, 33, 128] {
            for variant in 0..5 {
                let finite = |v: f64| json!({"kind":"finite","value":v});
                let variables:Vec<_>=(0..n).map(|j|json!({"id":3*j+7,"domain":"continuous",
                    "lower":if variant==1 && j%3==0 {json!({"kind":"negative_infinity"})} else {finite(-1.)},
                    "upper":if variant==2 && j%3==0 {json!({"kind":"positive_infinity"})} else {finite(1.)}})).collect();
                let constraints:Vec<_>=(0..n).map(|i|json!({"id":5*i+11,
                    "lower":if variant==3 {json!({"kind":"negative_infinity"})} else {finite(-2.)},"upper":finite(2.),
                    "terms":(0..n).map(|j|json!({"variable_id":3*j+7,"coefficient":if variant==4 {1e300} else {((13*i+7*j)%37) as f64/37.+0.01}})).collect::<Vec<_>>()})).collect();
                let model=optimizer_core::Model::from_json(&serde_json::to_vec(&json!({"schema_version":1,"model_id":"parallel-certificate",
                    "variables":variables,"constraints":constraints,"objective":{"sense":if variant%2==0 {"minimize"}else{"maximize"},"offset":3.25,
                    "terms":(0..n).map(|j|json!({"variable_id":3*j+7,"coefficient":(j%7) as f64-3.})).collect::<Vec<_>>()}})).unwrap()).unwrap();
                let program = LinearProgram::new(&model).unwrap();
                for sample in 0..24 {
                    let y: Vec<_> = (0..n)
                        .map(|j| match sample {
                            0 => 0.,
                            1 => -0.,
                            2 => f64::from_bits(1 + j as u64),
                            3 => f64::MAX,
                            4 => f64::INFINITY,
                            _ => (((sample * 17 + j * 13) % 97) as f64 - 48.) / 97.,
                        })
                        .collect();
                    let original = optimizer_lp::certify(&program, &y);
                    let candidate = parallel(&program, &y);
                    match (original, candidate) {
                        (Ok(a), Ok(b)) => assert_eq!(
                            (
                                a.bound.to_bits(),
                                a.unadjusted.to_bits(),
                                a.allowance.to_bits(),
                                a.repaired
                            ),
                            (
                                b.bound.to_bits(),
                                b.unadjusted.to_bits(),
                                b.allowance.to_bits(),
                                b.repaired
                            )
                        ),
                        (Err(a), Err(b)) => assert_eq!(a, b),
                        pair => panic!(
                            "certificate mismatch n={n} variant={variant} sample={sample}: {pair:?}"
                        ),
                    }
                }
            }
        }
    }
}
