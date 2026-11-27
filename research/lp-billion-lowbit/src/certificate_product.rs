//! Exact binary64 product classification using bounded 64-bit significands.
//! The original scalar enclosure implementation remains the independent oracle.
use crate::outward::Enclosure;

pub(crate) fn product(left: f64, right: f64) -> Option<Enclosure> {
    if !left.is_finite() || !right.is_finite() {
        return None;
    }
    let rounded = left * right;
    if !rounded.is_finite() {
        return None;
    }
    if left == 0. || right == 0. {
        return Enclosure::point(rounded);
    }
    if rounded != 0. {
        let parts = |value: f64| {
            let bits = value.to_bits();
            let exponent = ((bits >> 52) & 0x7ff) as i32;
            let significand =
                (bits & ((1u64 << 52) - 1)) | if exponent == 0 { 0 } else { 1u64 << 52 };
            let trailing = significand.trailing_zeros();
            (
                significand >> trailing,
                if exponent == 0 {
                    -1074
                } else {
                    exponent - 1075
                } + trailing as i32,
            )
        };
        let (a, ae) = parts(left);
        let (b, be) = parts(right);
        // An odd product with at least 54 significant bits cannot equal any
        // binary64 significand. Otherwise its product fits in 54 bits (u64).
        if (64 - a.leading_zeros()) + (64 - b.leading_zeros()) <= 54 {
            let (r, re) = parts(rounded);
            if a * b == r && ae + be == re {
                return Enclosure::point(rounded);
            }
        }
    }
    Enclosure::new(rounded.next_down(), rounded.next_up(), rounded)
}

#[cfg(test)]
mod tests {
    use super::*;
    fn bits(value: Option<Enclosure>) -> Option<[u64; 3]> {
        value.map(|v| [v.lower.to_bits(), v.upper.to_bits(), v.rounded.to_bits()])
    }
    #[test]
    fn exact_product_matches_original_at_exponent_and_significand_boundaries() {
        let mut values = vec![0., -0., f64::INFINITY, f64::NEG_INFINITY, f64::NAN];
        for exponent in [0u64, 1, 2, 25, 500, 970, 1022, 1023, 1024, 1500, 2045, 2046] {
            for fraction in [
                0,
                1,
                2,
                3,
                (1u64 << 26) - 1,
                1 << 26,
                (1u64 << 51) - 1,
                1 << 51,
                (1u64 << 52) - 1,
            ] {
                for sign in [0, 1u64 << 63] {
                    values.push(f64::from_bits(sign | exponent << 52 | fraction));
                }
            }
        }
        for &a in &values {
            for &b in &values {
                assert_eq!(
                    bits(product(a, b)),
                    bits(Enclosure::product(a, b)),
                    "{a:e} * {b:e}"
                );
            }
        }
        let mut state = 0xcafe_babe_d00d_f00du64;
        for _ in 0..200_000 {
            state ^= state << 13;
            state ^= state >> 7;
            state ^= state << 17;
            let a = f64::from_bits(state);
            state ^= state << 13;
            state ^= state >> 7;
            state ^= state << 17;
            let b = f64::from_bits(state);
            assert_eq!(bits(product(a, b)), bits(Enclosure::product(a, b)));
        }
    }
}
