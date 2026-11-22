//! Original enclosure arithmetic in canonical order, with bounded worker scratch.
//! Unlike a coefficient-parts cache, this retains no per-nonzero checker graph.
use crate::outward::{self, Enclosure};
use optimizer_lp::{Certificate, LinearProgram, NoBound, Range};

fn endpoint(z: f64, range: Range, variable: Option<u32>) -> Result<Enclosure, NoBound> {
    if z == 0. {
        return Ok(Enclosure::ZERO);
    }
    let bound = if z > 0. { range.lower } else { range.upper };
    if !bound.is_finite() {
        return Err(match variable {
            Some(variable_id) => NoBound::UnboundedVariable { variable_id },
            None => NoBound::NonfiniteArithmetic,
        });
    }
    Enclosure::product(z, bound).ok_or(NoBound::NonfiniteArithmetic)
}

fn append(
    terms: &mut Vec<Enclosure>,
    count: usize,
    term: impl Fn(usize) -> Result<Enclosure, NoBound> + Sync,
) -> Result<(), NoBound> {
    if count < 4096 {
        for i in 0..count {
            terms.push(term(i)?);
        }
        return Ok(());
    }
    std::thread::scope(|scope| {
        let workers = (0..4)
            .map(|w| {
                let term = &term;
                scope.spawn(move || {
                    (count * w / 4..count * (w + 1) / 4)
                        .map(term)
                        .collect::<Result<Vec<_>, _>>()
                })
            })
            .collect::<Vec<_>>();
        // Joining and appending in original order preserves the first refusal
        // as well as every term's position in the final enclosure tree.
        for worker in workers {
            terms.extend(worker.join().expect("certificate worker")?);
        }
        Ok(())
    })
}

pub fn certify(program: &LinearProgram, y: &[f64]) -> Result<Certificate, NoBound> {
    assert_eq!(y.len(), program.row_count());
    for (row, value) in y.iter().enumerate() {
        if !value.is_finite() {
            return Err(NoBound::NonfiniteMultiplier { row });
        }
    }
    let mut repaired_y = y.to_vec();
    let mut repaired = 0;
    for (row, value) in repaired_y.iter_mut().enumerate() {
        let range = program.rows()[row];
        if (*value > 0. && !range.lower.is_finite()) || (*value < 0. && !range.upper.is_finite()) {
            *value = 0.;
            repaired += 1;
        }
    }
    let mut terms = Vec::with_capacity(program.row_count() + program.column_count() + 1);
    append(&mut terms, program.row_count(), |row| {
        endpoint(repaired_y[row], program.rows()[row], None)
    })?;
    append(&mut terms, program.column_count(), |column| {
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
        let upper = if reduced.lower <= 0. && reduced.upper >= 0. {
            low.upper.max(high.upper).max(0.)
        } else {
            low.upper.max(high.upper)
        };
        Enclosure::new(low.lower.min(high.lower), upper, rounded)
            .ok_or(NoBound::NonfiniteArithmetic)
    })?;
    terms.push(Enclosure::point(program.offset()).ok_or(NoBound::NonfiniteArithmetic)?);
    let total = outward::sum(&terms).ok_or(NoBound::NonfiniteArithmetic)?;
    let allowance = Enclosure::point(total.rounded)
        .and_then(|raw| raw.subtract(Enclosure::point(total.lower)?))
        .ok_or(NoBound::NonfiniteArithmetic)?
        .upper
        .max(0.);
    Ok(Certificate {
        bound: program.to_original_objective(total.lower),
        unadjusted: program.to_original_objective(total.rounded),
        allowance,
        repaired,
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    use optimizer_core::ObjectiveSense;
    #[test]
    fn bounded_parallel_certificates_preserve_all_bits_and_first_refusals() {
        let mut comparisons = 0;
        for (n, m) in [
            (0usize, 0usize),
            (0, 17),
            (17, 0),
            (1, 1),
            (7, 33),
            (129, 65),
            (4097, 33),
            (33, 4097),
        ] {
            for mode in 0..4 {
                for sense in [ObjectiveSense::Minimize, ObjectiveSense::Maximize] {
                    let mut offsets = vec![0];
                    let mut indices = Vec::new();
                    let mut values = Vec::new();
                    for i in 0..m {
                        let mut cols = (0..n.min(8)).map(|j| (i + j) % n).collect::<Vec<_>>();
                        cols.sort_unstable();
                        for j in cols {
                            indices.push(j as u32);
                            values.push(match mode {
                                1 => f64::from_bits((i + j + 1) as u64),
                                2 => f64::MAX / 32.,
                                _ => ((i * 7 + j * 11) % 19) as f64 / 17. - 0.5,
                            });
                        }
                        offsets.push(values.len());
                    }
                    let columns = (0..n)
                        .map(|j| Range {
                            lower: if mode == 3 && j % 3 == 0 {
                                f64::NEG_INFINITY
                            } else {
                                -2.
                            },
                            upper: if mode == 3 && j % 4 == 0 {
                                f64::INFINITY
                            } else {
                                3.
                            },
                        })
                        .collect();
                    let rows = (0..m)
                        .map(|i| Range {
                            lower: if i % 3 == 0 { f64::NEG_INFINITY } else { -1. },
                            upper: if i % 4 == 0 { f64::INFINITY } else { 2. },
                        })
                        .collect();
                    let p = LinearProgram::from_csr(
                        (0..n as u32).map(|j| j * 13 + 7).collect(),
                        columns,
                        rows,
                        offsets,
                        indices,
                        values,
                        &(0..n as u32).collect::<Vec<_>>(),
                        &(0..n)
                            .map(|j| (j % 7) as f64 / 17. - 0.125)
                            .collect::<Vec<_>>(),
                        sense,
                        3.25,
                    )
                    .unwrap();
                    for value in [
                        -0.,
                        0.,
                        f64::from_bits(1),
                        -f64::from_bits(1),
                        0.125,
                        -0.75,
                        f64::MAX,
                        -f64::MAX,
                        f64::NAN,
                        f64::INFINITY,
                    ] {
                        let y = vec![value; m];
                        match (optimizer_lp::certify(&p, &y), certify(&p, &y)) {
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
                            pair => panic!("certificate difference: {pair:?}"),
                        }
                        comparisons += 1;
                    }
                }
            }
        }
        assert_eq!(comparisons, 640);
    }
}
