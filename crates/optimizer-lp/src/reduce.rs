//! The one reduction order both engines use, under SPEC-0011 requirements 6, 7
//! and 27.
//!
//! Floating-point addition is not associative, so the value of a sum depends on
//! the order it was accumulated in. That makes reduction order a correctness
//! concern here rather than a performance one: a result that depends on how many
//! multiprocessors happened to be resident is not reproducible, and requirement 8
//! makes reproducibility a contract.
//!
//! This module is the single definition requirement 27 asks for. The kernel
//! implements the same partition and the same tree, and a device test asserts the
//! segment size on both sides is one number rather than two that agree today.

/// Elements per reduction segment.
///
/// The partition is fixed by this constant alone. It is deliberately not derived
/// from a grid shape, a block shape, or the number of multiprocessors actually
/// resident: requirement 7 forbids all three, because each would make the sum a
/// property of the machine rather than of the input.
pub const SEGMENT: usize = 1024;

/// The order a reduction is accumulated in.
///
/// Two orders exist on purpose, and collapsing them into one would destroy the
/// distinction they are for. [`ReductionOrder::DeviceMirror`] is the kernel's own
/// order, so a host and device result can be compared bit for bit and a drifted
/// index shows up immediately. [`ReductionOrder::Sequential`] shares no order with
/// the kernel at all, so agreeing with it within tolerance is evidence about the
/// method rather than about a copied summation. A single number could not
/// establish both.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum ReductionOrder {
    /// The partition and tree the kernel uses, mirrored exactly.
    DeviceMirror,
    /// Plain left-to-right accumulation, sharing no order with the kernel.
    Sequential,
}

/// Sum `values` in the project's fixed order.
///
/// The order is a pure function of `values.len()` and [`SEGMENT`]:
///
/// 1. partition into `ceil(len / SEGMENT)` segments at fixed offsets;
/// 2. pad each segment to `SEGMENT` with `+0.0` and reduce it by the fixed tree
///    `for stride in SEGMENT/2, SEGMENT/4, .. 1 { a[i] += a[i + stride] }`;
/// 3. reduce the partials by the same rule, recursively, until one value remains.
///
/// Padding with `+0.0` is what makes step 2 independent of `len`: adding `+0.0` is
/// an exact identity in IEEE-754 for every value except a signalling NaN, and it
/// preserves `-0.0 + 0.0 = +0.0` consistently on both sides, so the padding
/// changes no bit of the result while removing the length from the tree shape.
#[must_use]
pub fn tree_sum(values: &[f64]) -> f64 {
    if values.is_empty() {
        return 0.0;
    }
    let mut level: Vec<f64> = values.chunks(SEGMENT).map(reduce_segment).collect();
    while level.len() > 1 {
        level = level.chunks(SEGMENT).map(reduce_segment).collect();
    }
    level[0]
}

/// Reduce one segment of at most [`SEGMENT`] values by the fixed tree.
fn reduce_segment(segment: &[f64]) -> f64 {
    debug_assert!(segment.len() <= SEGMENT);
    let mut buffer = [0.0f64; SEGMENT];
    buffer[..segment.len()].copy_from_slice(segment);
    let mut stride = SEGMENT / 2;
    while stride >= 1 {
        for index in 0..stride {
            buffer[index] += buffer[index + stride];
        }
        stride /= 2;
    }
    buffer[0]
}

/// Sum `values` left to right, sharing no order with the kernel.
///
/// This is the algorithmic oracle. It is deliberately the most naive accumulation
/// available, so that when it agrees with a device result within tolerance, the
/// agreement is evidence the method is right rather than evidence a summation was
/// copied correctly.
#[must_use]
pub fn sequential_sum(values: &[f64]) -> f64 {
    let mut total = 0.0;
    for value in values {
        total += value;
    }
    total
}

/// Sum `values` in the requested order.
#[must_use]
pub fn sum(values: &[f64], order: ReductionOrder) -> f64 {
    match order {
        ReductionOrder::DeviceMirror => tree_sum(values),
        ReductionOrder::Sequential => sequential_sum(values),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn an_empty_sum_is_zero() {
        assert_eq!(tree_sum(&[]), 0.0);
        assert_eq!(sequential_sum(&[]), 0.0);
    }

    /// Requirement 7: the partition and tree are exactly what the doc comment
    /// describes, so the kernel has an unambiguous rule to implement.
    ///
    /// Checked against a literal transcription of the documented steps written
    /// independently of the implementation. Comparing `tree_sum` with itself
    /// would assert only that the function is deterministic, which is a much
    /// weaker claim and one the repeatability test already makes.
    #[test]
    fn a_tree_sum_matches_an_independent_transcription_of_the_documented_rule() {
        fn documented(values: &[f64]) -> f64 {
            if values.is_empty() {
                return 0.0;
            }
            let mut level: Vec<f64> = values.to_vec();
            loop {
                let mut next = Vec::new();
                for segment in level.chunks(SEGMENT) {
                    // Step 2, written out: pad to SEGMENT, then halve the stride.
                    let mut padded = segment.to_vec();
                    padded.resize(SEGMENT, 0.0);
                    let mut width = SEGMENT;
                    while width > 1 {
                        width /= 2;
                        for index in 0..width {
                            padded[index] += padded[index + width];
                        }
                    }
                    next.push(padded[0]);
                }
                if next.len() == 1 {
                    return next[0];
                }
                level = next;
            }
        }

        for length in [1, 2, 7, SEGMENT - 1, SEGMENT, SEGMENT + 1, 5_000] {
            let values: Vec<f64> = (0..length)
                .map(|index| (index as f64).sin() * 1.0e5 + 0.25)
                .collect();
            assert_eq!(
                tree_sum(&values).to_bits(),
                documented(&values).to_bits(),
                "length {length} must follow the documented partition exactly"
            );
        }
    }

    /// The instrument that makes requirement 7 falsifiable.
    ///
    /// If no input distinguished the tree order from a left-to-right sum, every
    /// determinism assertion built on the tree would be vacuous: any order would
    /// satisfy it. This exhibits an input where the two genuinely disagree, so a
    /// later test asserting the tree order is asserting something.
    #[test]
    fn a_tree_sum_differs_from_a_left_to_right_sum_on_a_catastrophic_input() {
        // A large value followed by many small ones. Left to right, each small
        // value is absorbed into the running total and lost. In the tree, the
        // small values are summed together first and survive.
        let mut values = vec![1.0e16];
        values.extend(std::iter::repeat_n(1.0, 2_048));
        let tree = tree_sum(&values);
        let sequential = sequential_sum(&values);
        assert_ne!(
            tree, sequential,
            "the two orders must be distinguishable, or asserting one of them proves nothing"
        );
        // The tree is the more accurate of the two here, which is not the point
        // but is worth pinning: the exact answer is 1.0e16 + 2048.
        assert!(
            (tree - 1.000_000_000_000_204_8e16).abs()
                < (sequential - 1.000_000_000_000_204_8e16).abs()
        );
    }

    /// Padding with `+0.0` must not change a bit, or the tree shape would depend
    /// on the length after all.
    #[test]
    fn padding_a_short_segment_changes_no_bit() {
        let values = [1.5, -2.25, 3.125];
        let padded = {
            let mut full = values.to_vec();
            full.resize(SEGMENT, 0.0);
            tree_sum(&full)
        };
        assert_eq!(tree_sum(&values).to_bits(), padded.to_bits());
    }

    #[test]
    fn a_reduction_is_repeatable_for_a_fixed_input() {
        let values: Vec<f64> = (0..3_333)
            .map(|index| f64::from(index).sin() * 1.0e6)
            .collect();
        assert_eq!(tree_sum(&values).to_bits(), tree_sum(&values).to_bits());
    }

    #[test]
    fn both_orders_agree_on_an_input_where_rounding_cannot_bite() {
        // Small integers are exact in f64 and every partial sum stays exact, so
        // the orders must agree here. A disagreement would mean one of them is
        // not summing the values it was given.
        let values: Vec<f64> = (0..2_000).map(f64::from).collect();
        assert_eq!(tree_sum(&values), sequential_sum(&values));
        assert_eq!(
            sum(&values, ReductionOrder::DeviceMirror),
            tree_sum(&values)
        );
        assert_eq!(
            sum(&values, ReductionOrder::Sequential),
            sequential_sum(&values)
        );
    }
}
