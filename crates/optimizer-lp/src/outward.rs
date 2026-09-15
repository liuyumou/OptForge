//! Finite outward binary64 enclosures for host certification only.
//! Assumes nearest-even, gradual underflow, and no reassociation of additions.

use crate::reduce::SEGMENT;

#[derive(Clone, Copy, Debug)]
pub(crate) struct Enclosure {
    pub lower: f64,
    pub upper: f64,
    pub rounded: f64,
}

impl Enclosure {
    pub const ZERO: Self = Self {
        lower: 0.0,
        upper: 0.0,
        rounded: 0.0,
    };

    pub fn new(lower: f64, upper: f64, rounded: f64) -> Option<Self> {
        (lower.is_finite() && upper.is_finite() && rounded.is_finite() && lower <= upper).then_some(
            Self {
                lower,
                upper,
                rounded,
            },
        )
    }

    pub fn point(value: f64) -> Option<Self> {
        Self::new(value, value, value)
    }

    fn adjacent(value: f64) -> Option<Self> {
        Self::new(value.next_down(), value.next_up(), value)
    }

    pub fn product(left: f64, right: f64) -> Option<Self> {
        if !left.is_finite() || !right.is_finite() {
            return None;
        }
        let rounded = left * right;
        if !rounded.is_finite() {
            return None;
        }
        if left == 0.0 || right == 0.0 {
            return Self::point(rounded);
        }
        if rounded != 0.0 {
            // |v| = significand * 2^exponent with an odd significand.
            // The product is at most 106 bits, so this check is exact even when
            // a floating-point product residual would underflow to zero.
            let (a, ae) = parts(left);
            let (b, be) = parts(right);
            let (r, re) = parts(rounded);
            if a * b == r && ae + be == re {
                return Self::point(rounded);
            }
        }
        Self::adjacent(rounded)
    }

    fn addition(left: f64, right: f64) -> Option<Self> {
        let rounded = left + right;
        if !rounded.is_finite() {
            return None;
        }
        // Knuth TwoSum: exact residual, including gradual underflow, in the
        // absence of overflow. Check all intermediates before trusting zero.
        let right_part = rounded - left;
        let left_part = rounded - right_part;
        let left_error = left - left_part;
        let right_error = right - right_part;
        let error = left_error + right_error;
        if ![right_part, left_part, left_error, right_error, error]
            .iter()
            .all(|value| value.is_finite())
        {
            return Self::adjacent(rounded);
        }
        Self::new(
            if error < 0.0 {
                rounded.next_down()
            } else {
                rounded
            },
            if error > 0.0 {
                rounded.next_up()
            } else {
                rounded
            },
            rounded,
        )
    }

    pub fn add(self, other: Self) -> Option<Self> {
        Self::new(
            Self::addition(self.lower, other.lower)?.lower,
            Self::addition(self.upper, other.upper)?.upper,
            self.rounded + other.rounded,
        )
    }

    pub fn subtract(self, other: Self) -> Option<Self> {
        self.add(Self {
            lower: -other.upper,
            upper: -other.lower,
            rounded: -other.rounded,
        })
    }
}

/// Nonzero finite binary64 magnitude as an odd integer times a power of two.
fn parts(value: f64) -> (u128, i32) {
    let bits = value.to_bits();
    let exponent = ((bits >> 52) & 0x7ff) as i32;
    let fraction = bits & ((1_u64 << 52) - 1);
    let significand = if exponent == 0 {
        fraction
    } else {
        fraction | (1_u64 << 52)
    };
    let trailing = significand.trailing_zeros();
    let exponent = if exponent == 0 {
        -1074
    } else {
        exponent - 1075
    };
    (
        u128::from(significand >> trailing),
        exponent + trailing as i32,
    )
}

pub(crate) fn sum(values: &[Enclosure]) -> Option<Enclosure> {
    sum_using(values, Enclosure::add)
}

/// Prune only known padding subtrees of the documented tree. A live node plus
/// padding still normalizes -0 to +0 in all three components. For finite operands
/// TwoSum with +0 has zero error, so these three additions have exactly the same
/// enclosure and refusal semantics as `add(ZERO)` (including subnormals).
fn sum_using(
    values: &[Enclosure],
    mut add: impl FnMut(Enclosure, Enclosure) -> Option<Enclosure>,
) -> Option<Enclosure> {
    if values.is_empty() {
        return Some(Enclosure::ZERO);
    }
    let mut level = values.to_vec();
    loop {
        let mut next = Vec::with_capacity(level.len().div_ceil(SEGMENT));
        for values in level.chunks(SEGMENT) {
            let mut buffer = values.to_vec();
            let mut active = buffer.len();
            let mut stride = SEGMENT / 2;
            while stride > 0 {
                for index in 0..active.min(stride) {
                    buffer[index] = if index + stride < active {
                        add(buffer[index], buffer[index + stride])?
                    } else {
                        let value = buffer[index];
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
            next.push(buffer[0]);
        }
        if next.len() == 1 {
            return Some(next[0]);
        }
        level = next;
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    // The pre-optimization implementation, retained as a literal padded oracle.
    fn padded(values: &[Enclosure]) -> Option<Enclosure> {
        let values: Vec<_> = values.iter().copied().map(Some).collect();
        crate::reduce::tree_reduce(&values, Some(Enclosure::ZERO), |left, right| {
            left?.add(right?)
        })
    }

    fn bits(value: Option<Enclosure>) -> Option<[u64; 3]> {
        value.map(|v| [v.lower.to_bits(), v.upper.to_bits(), v.rounded.to_bits()])
    }

    #[test]
    fn pruned_padding_matches_every_enclosure_bit_and_refusal() {
        let lengths = [
            0, 1, 2, 3, 4, 7, 18, 31, 32, 33, 63, 64, 255, 256, 511, 512, 513, 1023, 1024, 1025,
            2048, 2049, 5000,
        ];
        for length in lengths {
            for kind in 0..6 {
                let mut seed = 17002_u64;
                let values: Vec<_> = (0..length)
                    .map(|index| {
                        seed ^= seed << 13;
                        seed ^= seed >> 7;
                        seed ^= seed << 17;
                        match kind {
                            0 => Enclosure::point(-0.0).unwrap(),
                            1 => Enclosure::point(
                                f64::from_bits(1 + seed % 4096)
                                    * if index % 2 == 0 { 1.0 } else { -1.0 },
                            )
                            .unwrap(),
                            2 => {
                                Enclosure::point(if index % 2 == 0 { f64::MAX } else { -f64::MAX })
                                    .unwrap()
                            }
                            3 => Enclosure::point(f64::MAX).unwrap(),
                            4 => Enclosure::product((seed as i64) as f64 * 1e-15, 0.1).unwrap(),
                            _ => Enclosure::new(
                                -f64::from_bits(seed & 0x7fefffffffffffff),
                                f64::from_bits(seed & 0x7fefffffffffffff),
                                -0.0,
                            )
                            .unwrap(),
                        }
                    })
                    .collect();
                assert_eq!(
                    bits(sum(&values)),
                    bits(padded(&values)),
                    "length {length}, kind {kind}"
                );
            }
        }
    }

    #[test]
    fn short_columns_do_only_live_enclosure_additions() {
        for length in [1, 4, 18, 32, 1024, 1025, 5000] {
            let values = vec![Enclosure::point(0.5).unwrap(); length];
            let mut additions = 0;
            let actual = sum_using(&values, |a, b| {
                additions += 1;
                a.add(b)
            });
            assert_eq!(bits(actual), bits(padded(&values)));
            assert_eq!(additions, length - 1);
        }
    }

    fn value(raw: &serde_json::Value) -> f64 {
        f64::from_bits(u64::from_str_radix(raw.as_str().unwrap(), 16).unwrap())
    }

    fn check(actual: Option<Enclosure>, case: &serde_json::Value) {
        match actual {
            Some(actual) => {
                assert!(actual.lower.is_finite() && actual.upper.is_finite());
                assert!(
                    actual.lower <= value(&case["lower"]),
                    "lower: {case}: {actual:?}"
                );
                assert!(
                    actual.upper >= value(&case["upper"]),
                    "upper: {case}: {actual:?}"
                );
            }
            None => assert!(!case["required"].as_bool().unwrap(), "refused: {case}"),
        }
    }

    #[test]
    fn primitive_enclosures_cover_independent_exact_rational_results() {
        let fixture: serde_json::Value = serde_json::from_str(include_str!(
            "../../../tests/regression/lp-certification-oracle.json"
        ))
        .unwrap();
        for case in fixture["arithmetic"].as_array().unwrap() {
            let left = value(&case["left"]);
            let right = value(&case["right"]);
            let result = match case["op"].as_str().unwrap() {
                "add" => Enclosure::point(left)
                    .unwrap()
                    .add(Enclosure::point(right).unwrap()),
                "subtract" => Enclosure::point(left)
                    .unwrap()
                    .subtract(Enclosure::point(right).unwrap()),
                "product" => Enclosure::product(left, right),
                _ => panic!("unknown oracle operation"),
            };
            check(result, case);
        }
        for case in fixture["sums"].as_array().unwrap() {
            let values: Vec<_> = case["values"]
                .as_array()
                .unwrap()
                .iter()
                .map(value)
                .collect();
            let enclosures: Vec<_> = values
                .iter()
                .map(|v| Enclosure::point(*v).unwrap())
                .collect();
            let result = sum(&enclosures);
            if let Some(result) = result {
                assert_eq!(result.rounded.to_bits(), crate::tree_sum(&values).to_bits());
            }
            check(result, case);
        }
    }

    #[test]
    fn exact_subnormal_products_and_sums_remain_exact() {
        let tiny = f64::from_bits(1);
        for result in [
            Enclosure::product(tiny, 1.0),
            Enclosure::product(tiny * 2.0, 0.5),
            Enclosure::point(tiny).unwrap().add(Enclosure::ZERO),
        ] {
            let result = result.unwrap();
            assert_eq!(result.lower, tiny);
            assert_eq!(result.upper, tiny);
        }
        let lost = Enclosure::product(tiny, 0.5).unwrap();
        assert!(lost.lower <= 0.0 && lost.upper >= tiny);
    }

    #[test]
    fn nonfinite_inputs_and_overflow_are_refused() {
        for value in [f64::NAN, f64::INFINITY, f64::NEG_INFINITY] {
            assert!(Enclosure::point(value).is_none());
            assert!(Enclosure::product(value, 0.0).is_none());
        }
        assert!(Enclosure::product(f64::MAX, 2.0).is_none());
    }
}
