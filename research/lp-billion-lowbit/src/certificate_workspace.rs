//! Exact certificate arithmetic with solve-local bounded reusable storage.
use crate::{
    outward::Enclosure,
    scratch_certificate::{endpoint, sum_in_place},
};
use optimizer_lp::{Certificate, LinearProgram, NoBound};

#[derive(Default)]
struct Worker {
    terms: Vec<Enclosure>,
    products: Vec<Enclosure>,
}
pub struct Workspace {
    repaired_y: Vec<f64>,
    terms: Vec<Enclosure>,
    workers: [Worker; 4],
    count: usize,
}
impl Workspace {
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
                    .map(|w| w.terms.capacity() + w.products.capacity())
                    .sum::<usize>())
    }
    pub fn certify(&mut self, program: &LinearProgram, y: &[f64]) -> Result<Certificate, NoBound> {
        let Self {
            repaired_y,
            terms,
            workers,
            count,
        } = self;
        terms.clear();
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
        append(
            terms,
            &mut workers[..*count],
            program.row_count(),
            |row, _| endpoint(repaired_y[row], program.rows()[row], None),
        )?;
        append(
            terms,
            &mut workers[..*count],
            program.column_count(),
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
        terms.push(Enclosure::point(program.offset()).ok_or(NoBound::NonfiniteArithmetic)?);
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
fn append(
    terms: &mut Vec<Enclosure>,
    workers: &mut [Worker],
    count: usize,
    term: impl Fn(usize, &mut Vec<Enclosure>) -> Result<Enclosure, NoBound> + Sync,
) -> Result<(), NoBound> {
    let width = if count < 4096 { 1 } else { workers.len() };
    let run = |worker: &mut Worker, index: usize| {
        worker.terms.clear();
        for i in count * index / width..count * (index + 1) / width {
            worker.terms.push(term(i, &mut worker.products)?);
        }
        Ok(())
    };
    // The calling thread computes the first range. At most width CPU workers,
    // including the caller, are active; ordered joins preserve first refusal.
    std::thread::scope(|scope| -> Result<(), NoBound> {
        let (first, rest) = workers[..width].split_first_mut().expect("worker domain");
        let jobs = rest
            .iter_mut()
            .enumerate()
            .map(|(i, w)| {
                let run = &run;
                scope.spawn(move || run(w, i + 1))
            })
            .collect::<Vec<_>>();
        let first_result: Result<(), NoBound> = run(first, 0);
        let results = jobs
            .into_iter()
            .map(|h| h.join().expect("certificate workspace worker"))
            .collect::<Vec<_>>();
        first_result?;
        for result in results {
            result?;
        }
        Ok(())
    })?;
    for worker in &workers[..width] {
        terms.extend_from_slice(&worker.terms);
    }
    Ok(())
}
