//! Original-tree host products with unused zero-padding work removed.
use crate::engine::Engine;
use optimizer_lp::{Compressed, LinearProgram, LpSettings, SEGMENT, tree_sum};

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
    let (row, column) = engine.scaled_matrix();
    let mut vector = vec![1.; program.column_count()];
    let mut norm = 0.;
    for _ in 0..settings.power_iterations {
        let product = multiply(program.row_major(), row, &vector);
        let transposed = multiply(program.column_major(), column, &product);
        let squares: Vec<_> = transposed.iter().map(|v| v * v).collect();
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
    let step = if norm > 0. { 0.9 / norm } else { 1. };
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
