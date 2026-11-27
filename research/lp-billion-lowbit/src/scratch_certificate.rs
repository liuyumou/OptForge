//! Opt-in exact certificate reduction with reusable worker scratch (amendment 91).
//! The original bounded checker remains the default and differential reference.
use crate::outward::Enclosure;
use optimizer_lp::{Certificate, LinearProgram, NoBound, Range};

pub(crate) fn endpoint(z: f64, range: Range, variable: Option<u32>) -> Result<Enclosure, NoBound> {
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

// Compact successive levels in the existing buffer. The destination for a
// completed chunk precedes every unread chunk, so compaction never overwrites
// live input. Arithmetic and padding normalization match outward::sum exactly.
pub(crate) fn sum_in_place(values: &mut [Enclosure]) -> Option<Enclosure> {
    if values.is_empty() {
        return Some(Enclosure::ZERO);
    }
    let mut length = values.len();
    loop {
        let outputs = length.div_ceil(crate::reduce::SEGMENT);
        for output in 0..outputs {
            let start = output * crate::reduce::SEGMENT;
            let end = (start + crate::reduce::SEGMENT).min(length);
            let chunk = &mut values[start..end];
            let mut active = chunk.len();
            let mut stride = crate::reduce::SEGMENT / 2;
            while stride > 0 {
                for index in 0..active.min(stride) {
                    chunk[index] = if index + stride < active {
                        chunk[index].add(chunk[index + stride])?
                    } else {
                        let value = chunk[index];
                        Enclosure {
                            lower: value.lower + 0.0,
                            upper: value.upper + 0.0,
                            rounded: value.rounded + 0.0,
                        }
                    };
                }
                active = active.min(stride);
                stride /= 2;
            }
            values[output] = chunk[0];
        }
        if outputs == 1 {
            return Some(values[0]);
        }
        length = outputs;
    }
}

fn append(
    terms: &mut Vec<Enclosure>,
    count: usize,
    term: impl Fn(usize, &mut Vec<Enclosure>) -> Result<Enclosure, NoBound> + Sync,
) -> Result<(), NoBound> {
    if count < 4096 {
        let mut scratch = Vec::new();
        for i in 0..count {
            terms.push(term(i, &mut scratch)?);
        }
        return Ok(());
    }
    std::thread::scope(|scope| {
        let workers = (0..4)
            .map(|w| {
                let term = &term;
                scope.spawn(move || {
                    let mut scratch = Vec::new();
                    (count * w / 4..count * (w + 1) / 4)
                        .map(|i| term(i, &mut scratch))
                        .collect::<Result<Vec<_>, _>>()
                })
            })
            .collect::<Vec<_>>();
        // Original order preserves both the enclosure tree and first refusal.
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
    append(&mut terms, program.row_count(), |row, _| {
        endpoint(repaired_y[row], program.rows()[row], None)
    })?;
    append(&mut terms, program.column_count(), |column, scratch| {
        let (rows, coefficients) = program.column_major().line(column);
        scratch.clear();
        // Reuse capacity across columns, but never retain coefficient products
        // or assessment results between certificates.
        for (&row, &coefficient) in rows.iter().zip(coefficients) {
            scratch.push(
                Enclosure::product(coefficient, repaired_y[row as usize])
                    .ok_or(NoBound::NonfiniteArithmetic)?,
            );
        }
        let transposed = sum_in_place(scratch).ok_or(NoBound::NonfiniteArithmetic)?;
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
    let total = sum_in_place(&mut terms).ok_or(NoBound::NonfiniteArithmetic)?;
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

    fn bits(value: Option<Enclosure>) -> Option<[u64; 3]> {
        value.map(|v| [v.lower.to_bits(), v.upper.to_bits(), v.rounded.to_bits()])
    }

    #[test]
    fn in_place_reduction_preserves_tree_bits_padding_and_refusals() {
        for length in [
            0,
            1,
            2,
            3,
            18,
            31,
            32,
            33,
            511,
            512,
            513,
            1023,
            1024,
            1025,
            2048,
            2049,
            5000,
            1024 * 1024 + 3,
        ] {
            for kind in 0..6 {
                let values: Vec<_> = (0..length)
                    .map(|i| match kind {
                        0 => Enclosure::point(-0.0).unwrap(),
                        1 => Enclosure::point(
                            f64::from_bits(1 + (i % 4096) as u64)
                                * if i % 2 == 0 { 1.0 } else { -1.0 },
                        )
                        .unwrap(),
                        2 => {
                            Enclosure::point(if i % 2 == 0 { f64::MAX } else { -f64::MAX }).unwrap()
                        }
                        3 => Enclosure::point(f64::MAX).unwrap(),
                        4 => Enclosure::product((i % 19) as f64 / 17.0, 0.1).unwrap(),
                        _ => Enclosure::new(-0.75, 1.25, -0.0).unwrap(),
                    })
                    .collect();
                let expected = crate::outward::sum(&values);
                let mut scratch = values.clone();
                let allocation = scratch.as_ptr();
                assert_eq!(
                    bits(sum_in_place(&mut scratch)),
                    bits(expected),
                    "length {length}, kind {kind}"
                );
                assert_eq!(scratch.as_ptr(), allocation);
            }
        }
    }

    #[test]
    fn scratch_reuse_after_refusal_cannot_contaminate_the_next_column() {
        let mut scratch = vec![Enclosure::point(f64::MAX).unwrap(); 32];
        assert!(sum_in_place(&mut scratch).is_none());
        let allocation = scratch.as_ptr();
        scratch.clear();
        scratch.extend([Enclosure::point(-0.0).unwrap(); 3]);
        assert_eq!(bits(sum_in_place(&mut scratch)), Some([0, 0, 0]));
        assert_eq!(scratch.as_ptr(), allocation);
    }

    #[test]
    fn parallel_refusal_reports_the_first_original_column() {
        let mut terms = Vec::new();
        let result = append(&mut terms, 8192, |index, scratch| {
            scratch.clear();
            if [17, 2048, 4096, 6144].contains(&index) {
                Err(NoBound::UnboundedVariable {
                    variable_id: index as u32 + 7,
                })
            } else {
                Ok(Enclosure::ZERO)
            }
        });
        assert_eq!(result, Err(NoBound::UnboundedVariable { variable_id: 24 }));
    }

    #[test]
    fn scratch_certificates_preserve_all_bits_and_first_refusals() {
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
            (33, 8193),
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
                    let mut workspaces = [
                        crate::certificate_workspace::Workspace::new(1),
                        crate::certificate_workspace::Workspace::new(3),
                        crate::certificate_workspace::Workspace::new(4),
                    ];
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
                        for workspace in &mut workspaces {
                            match (optimizer_lp::certify(&p, &y), workspace.certify(&p, &y)) {
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
                                pair => panic!("workspace certificate difference: {pair:?}"),
                            }
                        }
                        comparisons += 1;
                    }
                }
            }
        }
        assert_eq!(comparisons, 720);
    }
}
