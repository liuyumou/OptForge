//! Portable branchless encoding with the reference encoder's exact FP64 operations.
#[cfg(test)]
use crate::{operator::decode, tensor::quant};

#[cfg(test)]
fn scalar(values: &mut [f64], codes: &mut [u8], inverse: f64, scale: f64) {
    for (v, code) in values.iter_mut().zip(codes) {
        *code = quant(*v * inverse);
        *v -= decode(*code) * scale;
    }
}

#[inline(always)]
fn component(value: f64) -> (u8, f64) {
    let x = value.abs();
    let magnitude = 2 * u8::from(x > 0.5)
        + u8::from(x > 1.25)
        + u8::from(x >= 1.75)
        + u8::from(x > 2.5)
        + u8::from(x >= 3.5)
        + u8::from(x > 5.);
    let sign = u8::from(value < 0. && magnitude != 0) * 8;
    let code = magnitude | sign;
    let bits = if magnitude == 0 {
        0
    } else {
        ((1022 + u64::from(magnitude >> 1)) << 52)
            | (u64::from(magnitude & 1) << 51)
            | (u64::from(sign) << 60)
    };
    (code, f64::from_bits(bits))
}

pub(crate) fn encode(values: &mut [f64], k: usize) -> (Vec<u8>, Vec<i32>) {
    let len = values.len();
    let mut codes = vec![0; len * k];
    let mut exponents = Vec::with_capacity(k);
    for h in 0..k {
        let max = values.iter().map(|v| v.abs()).fold(0., f64::max);
        let mut e = if max == 0. {
            -48
        } else {
            (max.log2().floor() as i32 - 2).max(-48)
        };
        if max > 6. * 2f64.powi(e) {
            e += 1;
        }
        exponents.push(e);
        let scale = 2f64.powi(e);
        let inverse = 2f64.powi(-e);
        let out = &mut codes[h * len..(h + 1) * len];
        for (value, code) in values.iter_mut().zip(out) {
            let (next, decoded) = component(*value * inverse);
            *code = next;
            *value -= decoded * scale;
        }
    }
    (codes, exponents)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn components_match_reference_at_thresholds_and_vector_tails() {
        let mut values = Vec::new();
        for x in [0f64, 0.5, 1.25, 1.75, 2.5, 3.5, 5., 6.] {
            for v in [x.next_down(), x, x.next_up()] {
                values.extend([v, -v]);
            }
        }
        for i in -4096..=4096 {
            values.push(f64::from(i) / 683.);
        }
        for n in [1, 2, 3, 4, 5, 31, 32, 33, 1023, 1024, 1025, values.len()] {
            for power in [-40, 0, 40] {
                let original: Vec<_> = values[..n].iter().map(|v| v * 2f64.powi(power)).collect();
                for k in 1..=4 {
                    let (codes, exponents, residual) = crate::tensor::encode(&original, k);
                    let mut after = original.clone();
                    let (new_codes, new_exponents) = encode(&mut after, k);
                    assert_eq!(codes, new_codes);
                    assert_eq!(exponents, new_exponents);
                    assert!(
                        residual
                            .iter()
                            .zip(&after)
                            .all(|(a, b)| a.to_bits() == b.to_bits())
                    );
                    // Independently exercise the portable scalar implementation.
                    let mut scalar_values = original.clone();
                    let mut scalar_codes = vec![0; n];
                    let scale = 2f64.powi(exponents[0]);
                    scalar(
                        &mut scalar_values,
                        &mut scalar_codes,
                        2f64.powi(-exponents[0]),
                        scale,
                    );
                    assert_eq!(scalar_codes, codes[..n]);
                }
            }
        }
    }
}
