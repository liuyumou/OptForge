//! Exact SHA-256 binding; the public implementation and numerical code stay frozen.
use sha2::{Digest, Sha256};

pub fn accelerated(bytes: &[u8]) -> String {
    let _scope = optimizer_core::lp_cost::scope("accelerated_artifact_hash");
    const DIGITS: &[u8; 16] = b"0123456789abcdef";
    let hash = Sha256::digest(bytes);
    let mut output = String::with_capacity(64);
    for value in hash {
        output.push(DIGITS[usize::from(value >> 4)] as char);
        output.push(DIGITS[usize::from(value & 15)] as char);
    }
    output
}

pub fn hex(bytes: &[u8]) -> String {
    if crate::config::get().name == "candidate" {
        accelerated(bytes)
    } else {
        optimizer_experiment::sha256::hex(bytes)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn exact_original_hash_at_padding_and_message_boundaries() {
        for n in [
            0, 1, 2, 55, 56, 57, 63, 64, 65, 119, 120, 127, 128, 129, 4095, 4096, 4097, 65536,
            1048576,
        ] {
            let bytes: Vec<u8> = (0..n).map(|i| ((i * 73 + 19) & 255) as u8).collect();
            assert_eq!(
                accelerated(&bytes),
                optimizer_experiment::sha256::hex(&bytes)
            );
        }
    }
    #[test]
    fn exact_fips_vectors_and_byte_distinction() {
        assert_eq!(
            accelerated(b""),
            "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        );
        assert_eq!(
            accelerated(b"abc"),
            "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
        );
        assert_ne!(accelerated(b"-0.0"), accelerated(b"0.0"));
        assert_ne!(accelerated(b"{}"), accelerated(b"{ }"));
    }
}
