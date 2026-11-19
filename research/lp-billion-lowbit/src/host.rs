//! Original-tree host products with unused zero-padding work removed.
use crate::engine::Engine;
use optimizer_lp::{Compressed, LinearProgram, LpSettings, SEGMENT, tree_sum};
use std::sync::{Arc, RwLock, mpsc};

/// Gather products directly into the original reduction tree. No contraction,
/// reordered sum, or sparse padding is introduced.
fn dot_segment<const N: usize>(indices: &[u32], values: &[f64], vector: &[f64]) -> (f64, bool) {
    let mut buffer = [0.; N];
    let mut finite = true;
    for ((slot, &column), &value) in buffer.iter_mut().zip(indices).zip(values) {
        let product = value * vector[column as usize];
        finite &= product.is_finite();
        *slot = if N < SEGMENT { product + 0. } else { product };
    }
    let mut stride = N / 2;
    while stride > 0 {
        for i in 0..stride {
            buffer[i] += buffer[i + stride];
        }
        stride /= 2;
    }
    (buffer[0], finite)
}

fn dot(indices: &[u32], values: &[f64], vector: &[f64], partial: &mut Vec<f64>) -> f64 {
    if indices.is_empty() {
        return 0.;
    }
    let segment = |i: &[u32], v: &[f64]| match i.len().next_power_of_two() {
        1 => dot_segment::<1>(i, v, vector),
        2 => dot_segment::<2>(i, v, vector),
        4 => dot_segment::<4>(i, v, vector),
        8 => dot_segment::<8>(i, v, vector),
        16 => dot_segment::<16>(i, v, vector),
        32 => dot_segment::<32>(i, v, vector),
        64 => dot_segment::<64>(i, v, vector),
        128 => dot_segment::<128>(i, v, vector),
        256 => dot_segment::<256>(i, v, vector),
        512 => dot_segment::<512>(i, v, vector),
        _ => dot_segment::<1024>(i, v, vector),
    };
    let (sum, finite) = if indices.len() <= SEGMENT {
        segment(indices, values)
    } else {
        partial.clear();
        let mut finite = true;
        for (i, v) in indices.chunks(SEGMENT).zip(values.chunks(SEGMENT)) {
            let (sum, valid) = segment(i, v);
            partial.push(sum);
            finite &= valid;
        }
        (compact_sum(partial), finite)
    };
    if finite {
        sum
    } else {
        // Keep the full original padded tree, including its NaN behavior.
        let products: Vec<_> = indices
            .iter()
            .zip(values)
            .map(|(&i, &v)| v * vector[i as usize])
            .collect();
        tree_sum(&products)
    }
}

#[derive(Clone, Copy)]
struct Matrix<'a> {
    geometry: &'a Compressed,
    values: &'a [f64],
}
impl Matrix<'_> {
    fn multiply(
        self,
        vector: &[f64],
        begin: usize,
        end: usize,
        out: &mut Vec<f64>,
        partial: &mut Vec<f64>,
    ) {
        out.clear();
        out.reserve(end - begin);
        for row in begin..end {
            let (indices, _) = self.geometry.line(row);
            let offset = self.geometry.offset(row);
            out.push(dot(
                indices,
                &self.values[offset..offset + indices.len()],
                vector,
                partial,
            ));
        }
    }
}

struct Worker {
    task: mpsc::Sender<(usize, Vec<f64>)>,
    result: mpsc::Receiver<Vec<f64>>,
    output: Vec<f64>,
}

/// At most three parked helpers plus the caller, owned by one solve. Original
/// matrix storage is borrowed; no matrix copy or cross-solve cache is needed.
pub struct Products<'a> {
    matrices: [Matrix<'a>; 2],
    workers: Vec<Worker>,
    input: Arc<RwLock<Vec<f64>>>,
    partial: Vec<f64>,
}
impl Products<'_> {
    pub fn multiply(&mut self, transpose: bool, vector: &[f64], out: &mut Vec<f64>) {
        let direction = usize::from(transpose);
        let matrix = self.matrices[direction];
        let n = matrix.geometry.lines();
        if n < 4096 || self.workers.is_empty() {
            matrix.multiply(vector, 0, n, out, &mut self.partial);
            return;
        }
        {
            let mut input = self.input.write().expect("host input lock");
            input.clear();
            input.extend_from_slice(vector);
        }
        for worker in &mut self.workers {
            worker
                .task
                .send((direction, std::mem::take(&mut worker.output)))
                .expect("host worker available");
        }
        matrix.multiply(vector, 0, n / 4, out, &mut self.partial);
        for worker in &mut self.workers {
            worker.output = worker.result.recv().expect("host product worker completed");
            out.extend_from_slice(&worker.output);
        }
    }
}

pub fn with_products<T>(
    engine: &Engine<'_>,
    parallel: bool,
    f: impl FnOnce(&mut Products<'_>) -> T,
) -> T {
    let (row, column) = engine.scaled_matrix();
    let matrices = [
        Matrix {
            geometry: engine.program().row_major(),
            values: row,
        },
        Matrix {
            geometry: engine.program().column_major(),
            values: column,
        },
    ];
    std::thread::scope(|scope| {
        let input = Arc::new(RwLock::new(Vec::new()));
        let mut workers = Vec::new();
        if parallel && matrices.iter().any(|m| m.geometry.lines() >= 4096) {
            for index in 1..4 {
                let (task, tasks) = mpsc::channel::<(usize, Vec<f64>)>();
                let (result, results) = mpsc::channel();
                let input = Arc::clone(&input);
                scope.spawn(move || {
                    let mut partial = Vec::new();
                    while let Ok((direction, mut output)) = tasks.recv() {
                        let matrix = matrices[direction];
                        let n = matrix.geometry.lines();
                        matrix.multiply(
                            &input.read().expect("host input lock"),
                            n * index / 4,
                            n * (index + 1) / 4,
                            &mut output,
                            &mut partial,
                        );
                        if result.send(output).is_err() {
                            break;
                        }
                    }
                });
                workers.push(Worker {
                    task,
                    result: results,
                    output: Vec::new(),
                });
            }
        }
        f(&mut Products {
            matrices,
            workers,
            input,
            partial: Vec::new(),
        })
    })
}

#[derive(Default)]
pub struct ResidualWorkspace {
    transposed: Vec<f64>,
    extrapolated: Vec<f64>,
    activity: Vec<f64>,
}
impl ResidualWorkspace {
    pub fn evaluate(
        &mut self,
        products: &mut Products<'_>,
        e: &Engine<'_>,
        x: &[f64],
        y: &[f64],
        weight: f64,
    ) -> f64 {
        if !weight.is_finite() || weight <= 0. {
            return f64::INFINITY;
        }
        let primal_step = e.step() / weight;
        let dual_step = e.step() * weight;
        products.multiply(true, y, &mut self.transposed);
        let (lower, upper) = e.scaled_column_bounds();
        self.extrapolated.clear();
        let mut error = 0f64;
        let difference = |a: f64, b: f64| {
            let d = (a - b).abs();
            if d.is_finite() { d } else { f64::INFINITY }
        };
        for j in 0..x.len() {
            let gradient = e.scaled_objective()[j] - self.transposed[j];
            let moved = x[j] - primal_step * gradient;
            let next = moved.max(lower[j]).min(upper[j]);
            self.extrapolated.push(2.0 * next - x[j]);
            error = error.max(difference(next, x[j]));
        }
        products.multiply(false, &self.extrapolated, &mut self.activity);
        let (lower, upper) = e.scaled_row_bounds();
        for i in 0..y.len() {
            let raw = y[i] - dual_step * self.activity[i];
            let projected = (raw / dual_step).max(-upper[i]).min(-lower[i]);
            error = error.max(difference(raw - dual_step * projected, y[i]));
        }
        error
    }
}

fn segment<const N: usize>(v: &[f64]) -> f64 {
    let mut buffer = [0.; N];
    if N < SEGMENT {
        for (a, &b) in buffer.iter_mut().zip(v) {
            *a = b + 0.;
        }
    } else {
        buffer[..v.len()].copy_from_slice(v);
    }
    let mut stride = N / 2;
    while stride > 0 {
        for i in 0..stride {
            buffer[i] += buffer[i + stride];
        }
        stride /= 2;
    }
    buffer[0]
}

/// Keep the same 1024-leaf partition and butterfly. For a short segment, all
/// omitted upper levels only add +0.0 to each live leaf. Execute that once
/// (including -0.0 normalization), then the exact remaining tree. Nonfinite
/// inputs take the original implementation, including its NaN behavior.
pub fn compact_sum(values: &[f64]) -> f64 {
    if values.is_empty() {
        return 0.;
    }
    if values.iter().any(|x| !x.is_finite()) {
        return tree_sum(values);
    }
    let segment = |v: &[f64]| match v.len().next_power_of_two() {
        1 => segment::<1>(v),
        2 => segment::<2>(v),
        4 => segment::<4>(v),
        8 => segment::<8>(v),
        16 => segment::<16>(v),
        32 => segment::<32>(v),
        64 => segment::<64>(v),
        128 => segment::<128>(v),
        256 => segment::<256>(v),
        512 => segment::<512>(v),
        _ => segment::<1024>(v),
    };
    if values.len() <= SEGMENT {
        return segment(values);
    }
    let level: Vec<_> = values.chunks(SEGMENT).map(segment).collect();
    compact_sum(&level)
}

fn multiply(matrix: &Compressed, coefficients: &[f64], vector: &[f64]) -> Vec<f64> {
    let workers = if matrix.lines() >= 4096 { 4 } else { 1 };
    let chunk = |begin, end| {
        let mut products = Vec::new();
        (begin..end)
            .map(|row| {
                let (indices, _) = matrix.line(row);
                let start = matrix.offset(row);
                products.clear();
                products.extend(
                    indices
                        .iter()
                        .enumerate()
                        .map(|(j, &col)| coefficients[start + j] * vector[col as usize]),
                );
                compact_sum(&products)
            })
            .collect::<Vec<_>>()
    };
    if workers == 1 {
        return chunk(0, matrix.lines());
    }
    std::thread::scope(|scope| {
        let handles: Vec<_> = (0..workers)
            .map(|worker| {
                scope.spawn(move || {
                    let begin = matrix.lines() * worker / workers;
                    let end = matrix.lines() * (worker + 1) / workers;
                    chunk(begin, end)
                })
            })
            .collect();
        handles
            .into_iter()
            .flat_map(|h| h.join().expect("host product worker panicked"))
            .collect()
    })
}

/// Reuse public geometry preparation, then compute the original spectral
/// estimate with exact compact products. The isolated adapter owns this step.
pub fn engine(program: &LinearProgram, settings: LpSettings) -> Engine<'_> {
    let mut engine = Engine::without_spectral(program, settings);
    if program.column_count() == 0 || program.nonzeros() == 0 {
        return engine;
    }
    let step = with_products(&engine, true, |products| {
        let mut vector = vec![1.; program.column_count()];
        let mut product = Vec::new();
        let mut transposed = Vec::new();
        let mut squares = Vec::new();
        let mut norm = 0.;
        for _ in 0..settings.power_iterations {
            products.multiply(false, &vector, &mut product);
            products.multiply(true, &product, &mut transposed);
            squares.clear();
            squares.extend(transposed.iter().map(|v| v * v));
            let magnitude = compact_sum(&squares).sqrt();
            if magnitude <= 0. {
                norm = 0.;
                break;
            }
            for (slot, value) in vector.iter_mut().zip(&transposed) {
                *slot = value / magnitude;
            }
            norm = magnitude.sqrt();
        }
        if norm > 0. { 0.9 / norm } else { 1. }
    });
    engine.assign_exact_step(step);
    engine
}

pub fn step_once(e: &Engine<'_>, x: &[f64], y: &[f64], weight: f64) -> (Vec<f64>, Vec<f64>) {
    let primal_step = e.step() / weight;
    let dual_step = e.step() * weight;
    let (row_values, column_values) = e.scaled_matrix();
    let transposed = multiply(e.program().column_major(), column_values, y);
    let (lower, upper) = e.scaled_column_bounds();
    let next_x: Vec<_> = (0..x.len())
        .map(|j| {
            let gradient = e.scaled_objective()[j] - transposed[j];
            let moved = x[j] - primal_step * gradient;
            moved.max(lower[j]).min(upper[j])
        })
        .collect();
    let extrapolated: Vec<_> = (0..x.len()).map(|j| 2.0 * next_x[j] - x[j]).collect();
    let activity = multiply(e.program().row_major(), row_values, &extrapolated);
    let (lower, upper) = e.scaled_row_bounds();
    let next_y = (0..y.len())
        .map(|i| {
            let raw = y[i] - dual_step * activity[i];
            let projected = (raw / dual_step).max(-upper[i]).min(-lower[i]);
            raw - dual_step * projected
        })
        .collect();
    (next_x, next_y)
}

pub fn projected_residual(e: &Engine<'_>, x: &[f64], y: &[f64], weight: f64) -> f64 {
    if !weight.is_finite() || weight <= 0. {
        return f64::INFINITY;
    }
    let (nx, ny) = step_once(e, x, y, weight);
    x.iter()
        .chain(y)
        .zip(nx.iter().chain(&ny))
        .map(|(old, next)| {
            let d = (next - old).abs();
            if d.is_finite() { d } else { f64::INFINITY }
        })
        .fold(0., f64::max)
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn gathered_products_match_original_tree_bits() {
        let mut state = 387u64;
        let mut partial = Vec::new();
        for n in (0..=1050).chain([2047, 2048, 2049, 4095, 4096, 4097, 65537]) {
            let indices: Vec<_> = (0..n as u32).rev().collect();
            let vector: Vec<_> = (0..n)
                .map(|i| {
                    if i % 7 == 0 {
                        -0.
                    } else {
                        (i % 13) as f64 - 6.
                    }
                })
                .collect();
            let values: Vec<_> = (0..n)
                .map(|i| {
                    state = state.wrapping_mul(6364136223846793005).wrapping_add(1);
                    match i % 11 {
                        0 => -0.,
                        1 => f64::from_bits(1),
                        _ => ((state >> 32) as i32 as f64) * 2f64.powi((i % 101) as i32 - 50),
                    }
                })
                .collect();
            let original: Vec<_> = indices
                .iter()
                .zip(&values)
                .map(|(&i, &v)| v * vector[i as usize])
                .collect();
            assert_eq!(
                dot(&indices, &values, &vector, &mut partial).to_bits(),
                tree_sum(&original).to_bits(),
                "length {n}"
            );
            for value in [
                -0.,
                f64::MAX,
                f64::INFINITY,
                f64::from_bits(0x7ff8_0000_0000_0042),
            ] {
                let values = vec![value; n];
                let original: Vec<_> = indices
                    .iter()
                    .map(|&i| value * vector[i as usize])
                    .collect();
                assert_eq!(
                    dot(&indices, &values, &vector, &mut partial).to_bits(),
                    tree_sum(&original).to_bits(),
                    "special {value} length {n}"
                );
            }
        }
    }
    #[test]
    fn compact_tree_matches_original_bits_across_segments_and_cancellation() {
        let mut state = 991u64;
        for n in (0..=1050).chain([2047, 2048, 2049, 4095, 4096, 4097, 65537, 1_048_576]) {
            let values: Vec<_> = (0..n)
                .map(|i| {
                    state = state.wrapping_mul(6364136223846793005).wrapping_add(1);
                    match i % 11 {
                        0 => -0.,
                        1 => 0.,
                        2 => f64::from_bits(1),
                        3 => -f64::from_bits(1),
                        _ => ((state >> 32) as i32 as f64) * 2f64.powi((i % 101) as i32 - 50),
                    }
                })
                .collect();
            assert_eq!(
                compact_sum(&values).to_bits(),
                tree_sum(&values).to_bits(),
                "length {n}"
            );
            let negative_zeros = vec![-0.; n];
            assert_eq!(
                compact_sum(&negative_zeros).to_bits(),
                tree_sum(&negative_zeros).to_bits(),
                "signed zero {n}"
            );
        }
        for values in [
            vec![f64::MAX, f64::MAX, -f64::MAX],
            vec![f64::INFINITY, 1.],
            vec![f64::NAN, -0.],
        ] {
            assert_eq!(compact_sum(&values).to_bits(), tree_sum(&values).to_bits());
        }
    }
}
