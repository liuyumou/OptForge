//! Finite outward binary64 enclosures for host certification only.
//! Assumes nearest-even, gradual underflow, and no reassociation of additions.

use crate::reduce::tree_reduce;

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
    let values: Vec<_> = values.iter().copied().map(Some).collect();
    tree_reduce(&values, Some(Enclosure::ZERO), |left, right| {
        left?.add(right?)
    })
}

#[cfg(test)]
mod tests {
    use super::*;

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
