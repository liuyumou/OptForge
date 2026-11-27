//! Exact certificate arithmetic with solve-local bounded reusable storage.
use crate::{
    outward::Enclosure,
    scratch_certificate::{endpoint, sum_in_place},
};
use optimizer_lp::{Certificate, LinearProgram, NoBound};

/// Select whole independently validated routines. Balanced work keeps the
/// unchanged staged implementation; heavy/skewed work gets weighted partitions.
pub struct Workspace {
    staged: crate::certificate_staged::Workspace,
    weighted: WeightedWorkspace,
    workers: usize,
    previous_weighted: Option<bool>,
}
impl Workspace {
    pub fn new(workers: usize) -> Self {
        Self {
            staged: crate::certificate_staged::Workspace::new(workers),
            weighted: WeightedWorkspace::new(workers),
            workers,
            previous_weighted: None,
        }
    }
    pub fn retained_bytes(&self) -> usize {
        self.staged.retained_bytes() + self.weighted.retained_bytes()
    }
    pub fn certify(&mut self, program: &LinearProgram, y: &[f64]) -> Result<Certificate, NoBound> {
        let weighted = crate::work_partition::weighted_columns(
            program.column_major().arrays().0,
            self.workers,
        );
        if self.previous_weighted != Some(weighted) {
            // Retain capacity for one strategy only, even if a caller changes model.
            if weighted {
                self.staged = crate::certificate_staged::Workspace::new(self.workers);
            } else {
                self.weighted = WeightedWorkspace::new(self.workers);
            }
            self.previous_weighted = Some(weighted);
        }
        if weighted {
            self.weighted.certify(program, y)
        } else {
            self.staged.certify(program, y)
        }
    }
}

#[derive(Default)]
struct Worker {
    products: Vec<Enclosure>,
}
struct WeightedWorkspace {
    repaired_y: Vec<f64>,
    terms: Vec<Enclosure>,
    workers: [Worker; 4],
    count: usize,
}
impl WeightedWorkspace {
    pub fn new(workers: usize) -> Self {
        assert!((1..=4).contains(&workers));
        Self {
            repaired_y: Vec::new(),
            terms: Vec::new(),
            workers: Default::default(),
            count: workers,
        }
    }
    pub fn retained_bytes(&self) -> usize {
        8 * self.repaired_y.capacity()
            + 24 * (self.terms.capacity()
                + self
                    .workers
                    .iter()
                    .map(|w| w.products.capacity())
                    .sum::<usize>())
    }
    pub fn certify(&mut self, program: &LinearProgram, y: &[f64]) -> Result<Certificate, NoBound> {
        let Self {
            repaired_y,
            terms,
            workers,
            count,
        } = self;
        terms.resize(
            program.row_count() + program.column_count() + 1,
            Enclosure::ZERO,
        );
        assert_eq!(y.len(), program.row_count());
        for (row, value) in y.iter().enumerate() {
            if !value.is_finite() {
                return Err(NoBound::NonfiniteMultiplier { row });
            }
        }
        repaired_y.clear();
        repaired_y.extend_from_slice(y);
        let mut repaired = 0;
        for (row, value) in repaired_y.iter_mut().enumerate() {
            let range = program.rows()[row];
            if (*value > 0. && !range.lower.is_finite())
                || (*value < 0. && !range.upper.is_finite())
            {
                *value = 0.;
                repaired += 1;
            }
        }
        fill(
            &mut terms[..program.row_count()],
            &mut workers[..*count],
            &crate::work_partition::uniform(program.row_count(), *count),
            |row, _| endpoint(repaired_y[row], program.rows()[row], None),
        )?;
        fill(
            &mut terms[program.row_count()..program.row_count() + program.column_count()],
            &mut workers[..*count],
            &crate::work_partition::sparse(program.column_major().arrays().0, *count),
            |column, scratch| {
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
            },
        )?;
        *terms.last_mut().unwrap() =
            Enclosure::point(program.offset()).ok_or(NoBound::NonfiniteArithmetic)?;
        let total = sum_in_place(terms).ok_or(NoBound::NonfiniteArithmetic)?;
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
}
fn fill(
    terms: &mut [Enclosure],
    workers: &mut [Worker],
    ranges: &[std::ops::Range<usize>],
    term: impl Fn(usize, &mut Vec<Enclosure>) -> Result<Enclosure, NoBound> + Sync,
) -> Result<(), NoBound> {
    let run = |worker: &mut Worker, output: &mut [Enclosure], start: usize| {
        for (index, slot) in output.iter_mut().enumerate() {
            *slot = term(start + index, &mut worker.products)?;
        }
        Ok(())
    };
    // Each worker writes its final canonical slice. No per-worker term copy,
    // padding initialization on reuse, shared append, or unordered reduction.
    let mut remaining = terms;
    let mut jobs = Vec::with_capacity(ranges.len());
    for (worker, range) in workers.iter_mut().zip(ranges) {
        let (output, tail) = remaining.split_at_mut(range.len());
        remaining = tail;
        jobs.push((worker, output, range.start));
    }
    std::thread::scope(|scope| -> Result<(), NoBound> {
        let mut jobs = jobs.into_iter();
        let (first, output, start) = jobs.next().expect("worker domain");
        let handles = jobs
            .map(|(worker, output, start)| {
                let run = &run;
                scope.spawn(move || run(worker, output, start))
            })
            .collect::<Vec<_>>();
        let first_result: Result<(), NoBound> = run(first, output, start);
        let results = handles
            .into_iter()
            .map(|h| h.join().expect("certificate workspace worker"))
            .collect::<Vec<_>>();
        first_result?;
        for result in results {
            result?;
        }
        Ok(())
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn weighted_workers_report_first_refusal_and_overwrite_failed_scratch() {
        let mut terms = vec![Enclosure::ZERO; 257];
        let mut workers: [Worker; 4] = Default::default();
        let offsets: Vec<_> = (0..=257).map(|i| i * 4096).collect();
        let ranges = crate::work_partition::sparse(&offsets, 4);
        let result = fill(&mut terms, &mut workers, &ranges, |i, _| {
            if [17, 128, 256].contains(&i) {
                Err(NoBound::UnboundedVariable {
                    variable_id: i as u32,
                })
            } else {
                Ok(Enclosure::point(i as f64).unwrap())
            }
        });
        assert_eq!(result, Err(NoBound::UnboundedVariable { variable_id: 17 }));
        let allocation = terms.as_ptr();
        fill(&mut terms, &mut workers, &ranges, |i, _| {
            Ok(Enclosure::point(-(i as f64)).unwrap())
        })
        .unwrap();
        assert_eq!(allocation, terms.as_ptr());
        for (i, value) in terms.iter().enumerate() {
            assert_eq!(value.rounded.to_bits(), (-(i as f64)).to_bits());
        }
    }
}
