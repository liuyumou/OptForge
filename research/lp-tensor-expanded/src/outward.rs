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
    /// Identical enclosure to product, with immutable coefficient parts decoded
    /// once per solve. The rounded result still receives a fresh exactness check.
    pub fn product_cached(
        left: f64,
        right: f64,
        lp: Option<(u128, i32)>,
        rp: Option<(u128, i32)>,
    ) -> Option<Self> {
        if !left.is_finite() || !right.is_finite() {
            return None;
        }
        let rounded = left * right;
        if !rounded.is_finite() {
            return None;
        }
        if left == 0. || right == 0. {
            return Self::point(rounded);
        }
        if rounded != 0. {
            let (a, ae) = lp?;
            let (b, be) = rp?;
            let (r, re) = parts(rounded);
            if a * b == r && ae + be == re {
                return Self::point(rounded);
            }
        }
        Self::adjacent(rounded)
    }
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
pub(crate) fn parts(value: f64) -> (u128, i32) {
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
