//! Cached integer product decomposition and allocation-free original reduction order.
use crate::{outward::Enclosure, reduce::SEGMENT};

#[derive(Clone, Copy)]
pub struct Parts {
    odd: u64,
    exponent: i32,
}
impl Parts {
    pub fn new(value: f64) -> Self {
        let bits = value.to_bits();
        let exponent = ((bits >> 52) & 0x7ff) as i32;
        let significand =
            (bits & ((1_u64 << 52) - 1)) | if exponent == 0 { 0 } else { 1_u64 << 52 };
        if significand == 0 {
            return Self {
                odd: 0,
                exponent: 0,
            };
        }
        let trailing = significand.trailing_zeros();
        Self {
            odd: significand >> trailing,
            exponent: (if exponent == 0 {
                -1074
            } else {
                exponent - 1075
            }) + trailing as i32,
        }
    }
}

pub fn product(left: f64, right: f64, a: Parts, b: Parts) -> Option<Enclosure> {
    if !left.is_finite() || !right.is_finite() {
        return None;
    }
    let rounded = left * right;
    if !rounded.is_finite() {
        return None;
    }
    if left == 0.0 || right == 0.0 {
        return Enclosure::point(rounded);
    }
    // The exact magnitude is the odd integer p times 2^exponent.
    // It is finite binary64 iff p has <=53 bits, its least bit is >=2^-1074,
    // and its highest bit is <=2^1023. This is exactly the original comparison
    // with parts(rounded), without decomposing the rounded product again.
    let p = u128::from(a.odd) * u128::from(b.odd);
    let exponent = a.exponent + b.exponent;
    if p < (1_u128 << 53)
        && exponent >= -1074
        && exponent + (128 - p.leading_zeros()) as i32 <= 1024
    {
        return Enclosure::point(rounded);
    }
    Enclosure::new(rounded.next_down(), rounded.next_up(), rounded)
}

// FastTwoSum is exact after magnitude ordering. This path is restricted to a
// tree of <=2048 leaves whose nonzero fields are in [2^-100,2^100]. There are
// at most 11 live additions along a path: even pessimistic 54-bit cancellation
// per level cannot reach underflow, and magnitude growth cannot overflow.
// The original path handles the entire remaining binary64 domain.
#[inline]
fn fast_add(a: Enclosure, b: Enclosure) -> Enclosure {
    fn directed(a: f64, b: f64, lower: bool) -> f64 {
        let sum = a + b;
        let (large, small) = if a.abs() >= b.abs() { (a, b) } else { (b, a) };
        let error = small - (sum - large);
        if lower && error < 0. {
            sum.next_down()
        } else if !lower && error > 0. {
            sum.next_up()
        } else {
            sum
        }
    }
    Enclosure {
        lower: directed(a.lower, b.lower, true),
        upper: directed(a.upper, b.upper, false),
        rounded: a.rounded + b.rounded,
    }
}
pub fn sum_in_place(values: &mut [Enclosure]) -> Option<Enclosure> {
    let normal = |x: f64| x == 0. || ((2_f64.powi(-100)..=2_f64.powi(100)).contains(&x.abs()));
    let fast = values.len() <= 2048
        && values
            .iter()
            .all(|x| x.lower <= x.upper && normal(x.lower) && normal(x.upper) && normal(x.rounded));
    if fast {
        sum_impl::<true>(values)
    } else {
        sum_impl::<false>(values)
    }
}

/// Compact completed segments only after all their original inputs have been read.
/// Padding additions are retained to preserve all three signed-zero components.
fn sum_impl<const FAST: bool>(values: &mut [Enclosure]) -> Option<Enclosure> {
    if values.is_empty() {
        return Some(Enclosure::ZERO);
    }
    let mut length = values.len();
    loop {
        let next = length.div_ceil(SEGMENT);
        for segment in 0..next {
            let begin = segment * SEGMENT;
            let mut active = (length - begin).min(SEGMENT);
            let mut stride = SEGMENT / 2;
            while stride > 0 {
                for i in 0..active.min(stride) {
                    let at = begin + i;
                    values[at] = if i + stride < active {
                        if FAST {
                            fast_add(values[at], values[at + stride])
                        } else {
                            values[at].add(values[at + stride])?
                        }
                    } else {
                        let v = values[at];
                        Enclosure {
                            lower: v.lower + 0.0,
                            upper: v.upper + 0.0,
                            rounded: v.rounded + 0.0,
                        }
                    };
                }
                active = active.min(stride);
                stride /= 2;
            }
            values[segment] = values[begin];
        }
        if next == 1 {
            return Some(values[0]);
        }
        length = next;
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    fn bits(x: Option<Enclosure>) -> Option<[u64; 3]> {
        x.map(|v| [v.lower.to_bits(), v.upper.to_bits(), v.rounded.to_bits()])
    }
    #[test]
    fn ordered_fast_sum_matches_original_bits() {
        let mut rng = 0x380071_u64;
        for i in 0..100_000 {
            let mut next = || {
                rng ^= rng << 13;
                rng ^= rng >> 7;
                rng ^= rng << 17;
                (rng as i64 as f64) / (i64::MAX as f64) * 2_f64.powi((rng % 181) as i32 - 90)
            };
            let x = next();
            let y = if i % 7 == 0 { -x } else { next() };
            let a = Enclosure {
                lower: x.next_down(),
                upper: x.next_up(),
                rounded: x,
            };
            let b = Enclosure {
                lower: y.next_down(),
                upper: y.next_up(),
                rounded: y,
            };
            let got = fast_add(a, b);
            let want = a.add(b).unwrap();
            assert_eq!(bits(Some(got)), bits(Some(want)));
        }
        for a in [0., -0., 1., -1., 2_f64.powi(-100), 2_f64.powi(100)] {
            for b in [0., -0., a, -a, a * 0.5] {
                let x = Enclosure::point(a).unwrap();
                let y = Enclosure::point(b).unwrap();
                assert_eq!(bits(Some(fast_add(x, y))), bits(x.add(y)));
            }
        }
    }
    #[test]
    fn cached_product_matches_original_full_binary64_domain_samples() {
        let edges = [
            0.0,
            -0.0,
            f64::from_bits(1),
            -f64::from_bits(1),
            f64::MIN_POSITIVE,
            f64::MAX,
            -f64::MAX,
            f64::INFINITY,
            f64::NEG_INFINITY,
            f64::NAN,
            1.0,
            0.5,
            -2.0,
        ];
        for a in edges {
            for b in edges {
                assert_eq!(
                    bits(product(a, b, Parts::new(a), Parts::new(b))),
                    bits(Enclosure::product(a, b))
                );
            }
        }
        let mut seed = 0x74f31b13e26ca905_u64;
        for _ in 0..500_000 {
            seed ^= seed << 13;
            seed ^= seed >> 7;
            seed ^= seed << 17;
            let a = f64::from_bits(seed);
            seed ^= seed << 13;
            seed ^= seed >> 7;
            seed ^= seed << 17;
            let b = f64::from_bits(seed);
            assert_eq!(
                bits(product(a, b, Parts::new(a), Parts::new(b))),
                bits(Enclosure::product(a, b))
            );
        }
    }
    #[test]
    fn compact_tree_preserves_all_bits_and_refusals() {
        for n in [
            0, 1, 2, 7, 31, 32, 33, 511, 512, 513, 1023, 1024, 1025, 2048, 2049, 5000,
        ] {
            for kind in 0..5 {
                let mut v: Vec<_> = (0..n)
                    .map(|i| match kind {
                        0 => Enclosure::point(-0.0).unwrap(),
                        1 => Enclosure::point(f64::from_bits((i + 1) as u64)).unwrap(),
                        2 => Enclosure::point(f64::MAX).unwrap(),
                        3 => {
                            Enclosure::point(if i % 2 == 0 { f64::MAX } else { -f64::MAX }).unwrap()
                        }
                        _ => Enclosure::product((i as f64 - 273.0) / 7.0, 0.1).unwrap(),
                    })
                    .collect();
                let expected = crate::outward::sum(&v);
                assert_eq!(
                    bits(sum_in_place(&mut v)),
                    bits(expected),
                    "n={n} kind={kind}"
                );
            }
        }
    }
}
